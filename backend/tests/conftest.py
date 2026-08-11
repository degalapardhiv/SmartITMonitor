import os
import subprocess
import uuid

import httpx
import psycopg2
import pytest

BASE_URL = "http://localhost:8000"


def _load_env_values():
    """Read test/integration credentials from the environment first, then from
    the gitignored `backend/.env` file. No live secrets are committed."""
    values = {}
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_LOCAL_ENV = _load_env_values()


def _cred(name, default=None):
    return os.environ.get(name) or _LOCAL_ENV.get(name) or default


def _cred_from_database_url(field, name, default=None):
    import urllib.parse

    url = _cred("DATABASE_URL", "")
    if not url:
        return default
    try:
        parts = urllib.parse.urlparse(url)
        if field == "user":
            return parts.username or default
        if field == "password":
            return parts.password or default
        if field == "dbname":
            return parts.path.lstrip("/") or default
    except Exception:
        pass
    return default


ADMIN_USERNAME = _cred("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _cred("ADMIN_PASSWORD")

AGENT_TOKEN = _cred("AGENT_TOKEN")

DB_CREDENTIALS = {
    "user": _cred("POSTGRES_USER", "smartadmin"),
    "password": _cred(
        "POSTGRES_PASSWORD",
        _cred_from_database_url("password", "POSTGRES_PASSWORD"),
    ),
    "dbname": _cred("POSTGRES_DB", "smart_monitor"),
}

assert ADMIN_PASSWORD, "set ADMIN_PASSWORD in environment or backend/.env for tests"
assert AGENT_TOKEN, "set AGENT_TOKEN in environment or backend/.env for tests"
assert DB_CREDENTIALS["password"], (
    "set POSTGRES_PASSWORD in environment or backend/.env for tests"
)


def _docker_db_host():
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                "smart-monitor-db",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except Exception:
        pass
    return None


def _db_dsn():
    host = _docker_db_host()
    candidates = []
    if host:
        candidates.append(f"postgresql://{DB_CREDENTIALS['user']}:{DB_CREDENTIALS['password']}@{host}:5432/{DB_CREDENTIALS['dbname']}")
    candidates.append(os.getenv("DATABASE_URL", ""))
    candidates.append(f"postgresql://{DB_CREDENTIALS['user']}:{DB_CREDENTIALS['password']}@localhost:5432/{DB_CREDENTIALS['dbname']}")
    candidates.append(f"postgresql://{DB_CREDENTIALS['user']}:{DB_CREDENTIALS['password']}@localhost:5433/{DB_CREDENTIALS['dbname']}")

    for dsn in candidates:
        if not dsn:
            continue
        try:
            conn = psycopg2.connect(dsn)
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.network_devices') IS NOT NULL")
                has_new_tables = cur.fetchone()[0]
            conn.close()
            if has_new_tables:
                return dsn
        except Exception:
            continue

    for dsn in candidates:
        if not dsn:
            continue
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            return dsn
        except Exception:
            continue

    raise RuntimeError("No reachable database found for test cleanup")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as c:
        yield c


@pytest.fixture(scope="session")
def testclient(client):
    return client


@pytest.fixture(scope="session")
def admin_token(client):
    response = client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(_db_dsn())
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def db_session(db_conn):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(_db_dsn())
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def db_execute(db_conn, sql, params=None):
    cursor = db_conn.cursor()
    try:
        cursor.execute(sql, params or ())
        if cursor.description:
            return cursor.fetchall()
        return None
    finally:
        cursor.close()


@pytest.fixture()
def test_alert_id(db_conn):
    hostname = f"qa-test-alert-{uuid.uuid4().hex[:8]}"
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (device_id, hostname, alert_type, value, severity, status)"
        " VALUES (1, %s, 'CPU', 95, 'HIGH', 'OPEN') RETURNING id",
        (hostname,),
    )
    alert_id = cursor.fetchone()[0]
    cursor.close()
    yield alert_id
    db_execute(db_conn, "DELETE FROM alerts WHERE id = %s", (alert_id,))


@pytest.fixture()
def created_network_device(client, db_conn):
    hostname = f"qa-test-{uuid.uuid4().hex[:8]}"
    mac = f"qa-{uuid.uuid4().hex[:12]}"
    ip = f"192.168.254.{uuid.uuid4().int % 250 + 1}"
    response = client.post(
        "/network/discovery",
        headers={"X-Agent-Token": AGENT_TOKEN},
        json={
            "devices": [
                {
                    "ip": ip,
                    "mac": mac,
                    "hostname": hostname,
                    "network": "qa-test-net",
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    device = body["devices"][0]
    yield {"id": device["id"], "hostname": hostname, "mac": mac, "ip": ip}
    db_execute(db_conn, "DELETE FROM network_devices WHERE id = %s", (device["id"],))


@pytest.fixture()
def restore_exam_mode(client, auth_headers):
    original = client.get("/exam-mode", headers=auth_headers).json()
    yield original
    client.put(
        "/exam-mode",
        headers=auth_headers,
        json={
            "enabled": original["enabled"],
            "usb_policy": original["usb_policy"],
        },
    )
