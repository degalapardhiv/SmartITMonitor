import uuid
from conftest import db_execute


def _first_device(client, auth_headers):
    response = client.get("/devices", headers=auth_headers)
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) > 0
    return devices[0]


def test_devices_requires_auth(client):
    response = client.get("/devices")
    assert response.status_code == 401


def test_delete_device_cleans_orphan_prone_tables(client, auth_headers, db_conn):
    payload = {
        "hostname": f"qa-delete-cleanup-{uuid.uuid4().hex[:8]}",
        "ip": "10.99.99.99",
        "cpu": 5.0,
        "ram": 20.0,
        "disk": 10.0,
        "status": "online",
        "department": "QA",
        "lab": "cleanup",
        "location": "test",
        "os": "linux",
    }
    created = client.post("/devices", json=payload, headers=auth_headers)
    assert created.status_code == 200, created.text
    device_id = created.json()["id"]

    package_id = db_execute(
        db_conn,
        "INSERT INTO software_packages (name, version) VALUES (%s, %s) RETURNING id",
        (f"qa-cleanup-pkg-{uuid.uuid4().hex[:8]}", "1.0"),
    )[0][0]
    deployment_id = db_execute(
        db_conn,
        "INSERT INTO software_deployments (package_id, action, status) VALUES (%s, %s, %s) RETURNING id",
        (package_id, "install", "running"),
    )[0][0]

    inserts = {
        "alerts": (f"INSERT INTO alerts (device_id, hostname, alert_type, severity, status) VALUES (%s, %s, %s, %s, 'OPEN')", (device_id, "qa-cleanup", "CPU", "HIGH")),
        "deployments": (f"INSERT INTO deployments (device_id, os_image_id) VALUES (%s, %s)", (device_id, 1)),
        "endpoint_activity": (f"INSERT INTO endpoint_activity (device_id, hostname) VALUES (%s, %s)", (device_id, "qa-cleanup")),
        "software_deployment_events": (f"INSERT INTO software_deployment_events (deployment_id, device_id) VALUES (%s, %s)", (deployment_id, device_id)),
        "usb_requests": (f"INSERT INTO usb_requests (device_id, status) VALUES (%s, 'pending')", (device_id,)),
        "web_access_sync_logs": (f"INSERT INTO web_access_sync_logs (device_id, hostname) VALUES (%s, %s)", (device_id, "qa-cleanup")),
    }
    for sql, params in inserts.values():
        db_execute(db_conn, sql, params)

    deleted = client.delete(f"/devices/{device_id}", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text

    for table in inserts:
        with db_conn.cursor() as cursor:
            cursor.execute(f"SELECT count(*) FROM {table} WHERE device_id = %s", (device_id,))
            assert cursor.fetchone()[0] == 0, f"orphan rows left in {table}"


def test_devices_returns_list(client, auth_headers):
    device = _first_device(client, auth_headers)
    assert device["hostname"]


def test_devices_do_not_leak_agent_token(client, auth_headers):
    response = client.get("/devices", headers=auth_headers)
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    assert all("agent_token" not in device for device in devices)
    assert all("password_hash" not in device for device in devices)


def test_get_device_by_id(client, auth_headers):
    device = _first_device(client, auth_headers)

    response = client.get(f"/devices/{device['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["hostname"] == device["hostname"]


def test_get_device_does_not_leak_agent_token(client, auth_headers):
    device = _first_device(client, auth_headers)

    response = client.get(f"/devices/{device['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert "agent_token" not in response.json()
    assert "password_hash" not in response.json()


def test_get_device_returns_404_for_unknown(client, auth_headers):
    response = client.get("/devices/99999999", headers=auth_headers)
    assert response.status_code == 404


def test_device_metrics_history(client, auth_headers):
    device = _first_device(client, auth_headers)

    response = client.get(f"/devices/{device['id']}/metrics", headers=auth_headers)
    assert response.status_code == 200
    metrics = response.json()
    assert isinstance(metrics, list)
    assert len(metrics) > 0
    for key in ("cpu", "ram", "disk", "created_at"):
        assert key in metrics[0]


def test_dashboard_summary(client, auth_headers):
    response = client.get("/dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    for key in ("total", "online", "offline", "alerts", "departments", "labs"):
        assert key in body
    assert body["total"] == body["online"] + body["offline"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"