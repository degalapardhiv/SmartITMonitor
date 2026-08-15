import json
import uuid

import pytest

from conftest import db_execute


def _label():
    return "qa-sc-" + uuid.uuid4().hex[:8]


@pytest.fixture()
def clean_audit(db_conn):
    yield
    db_execute(db_conn, "DELETE FROM settings_audit")


def _settings_keys():
    return [
        "site_name",
        "login_redirect_route",
        "support_url",
        "status_page_url",
        "telegram_bot_token",
        "telegram_chat_id",
        "telegram_enabled",
        "cpu_threshold",
        "ram_threshold",
        "disk_threshold",
        "alert_cooldown_minutes",
        "alert_monitor_interval_seconds",
        "scan_ranges",
        "heartbeat_timeout_seconds",
        "heartbeat_check_interval_seconds",
        "endpoint_activity_interval_seconds",
        "agent_api_url",
        "network_ranges",
        "metrics_interval_seconds",
        "request_timeout_seconds",
        "activity_interval_seconds",
        "software_poll_interval_seconds",
        "web_access_poll_interval_seconds",
        "deployment_poll_interval_seconds",
        "discovery_interval_seconds",
        "agent_reboot_cmd",
        "agent_department",
        "agent_lab",
        "agent_location",
    ]


@pytest.fixture()
def clean_settings(db_conn):
    keys = _settings_keys()

    placeholders = ",".join(["%s"] * len(keys))
    snapshot = db_execute(
        db_conn,
        f"SELECT key, value FROM monitor_settings WHERE key IN ({placeholders})",
        keys,
    )
    telegram_snapshot = db_execute(
        db_conn,
        "SELECT value FROM system_settings WHERE key = 'telegram'",
    )

    db_execute(
        db_conn,
        f"DELETE FROM monitor_settings WHERE key IN ({placeholders})",
        keys,
    )
    db_execute(db_conn, "DELETE FROM system_settings WHERE key = 'telegram'")
    db_execute(db_conn, "DELETE FROM settings_audit")

    yield

    db_execute(
        db_conn,
        f"DELETE FROM monitor_settings WHERE key IN ({placeholders})",
        keys,
    )
    db_execute(db_conn, "DELETE FROM system_settings WHERE key = 'telegram'")
    db_execute(db_conn, "DELETE FROM settings_audit")

    for key, value in snapshot or []:
        db_execute(
            db_conn,
            "INSERT INTO monitor_settings (key, value) VALUES (%s, %s)",
            (key, value),
        )
    for (value,) in telegram_snapshot or []:
        db_execute(
            db_conn,
            "INSERT INTO system_settings (key, value) VALUES ('telegram', %s)",
            (value,),
        )


def test_settings_center_requires_admin(client, viewer_headers):
    response = client.get(
        "/settings-center",
        headers=viewer_headers,
    )
    assert response.status_code in (401, 403)


def test_settings_center_requires_auth(client):
    response = client.get("/settings-center")
    assert response.status_code in (401, 403)


def test_list_sections_contains_all_groups(client, auth_headers):
    response = client.get("/settings-center", headers=auth_headers)
    assert response.status_code == 200, response.text

    keys = [s["key"] for s in response.json()["sections"]]

    for expected in [
        "general",
        "auth_security",
        "telegram",
        "email",
        "monitoring",
        "heartbeat",
        "discovery",
        "usb_security",
        "exam_mode",
        "endpoint_activity",
        "provisioning",
        "cctv",
        "retention",
        "websocket",
        "agent",
    ]:
        assert expected in keys


def test_secrets_masked_in_listing(client, auth_headers):
    response = client.get("/settings-center", headers=auth_headers)
    assert response.status_code == 200

    telegram = next(
        s for s in response.json()["sections"]
        if s["key"] == "telegram"
    )

    assert telegram["values"]["telegram_bot_token"] == ""


def test_unknown_section_404(client, auth_headers):
    response = client.put(
        "/settings-center/not_a_section",
        headers=auth_headers,
        json={"values": {}},
    )
    assert response.status_code == 404


def test_update_validation_rejects_bad_route(
    client, auth_headers, clean_settings
):
    response = client.put(
        "/settings-center/general",
        headers=auth_headers,
        json={"values": {"login_redirect_route": "https://evil.example"}},
    )
    assert response.status_code == 400


def test_update_validation_rejects_bad_cidr(
    client, auth_headers, clean_settings
):
    response = client.put(
        "/settings-center/discovery",
        headers=auth_headers,
        json={"values": {"scan_ranges": ["not-a-network"]}},
    )
    assert response.status_code == 400


def test_update_validation_rejects_bad_int(
    client, auth_headers, clean_settings
):
    response = client.put(
        "/settings-center/heartbeat",
        headers=auth_headers,
        json={"values": {"heartbeat_timeout_seconds": 99999}},
    )
    assert response.status_code == 400


def test_update_monitoring_writes_kv(
    client, auth_headers, db_conn, clean_settings
):
    response = client.put(
        "/settings-center/monitoring",
        headers=auth_headers,
        json={
            "values": {
                "cpu_threshold": 55,
                "ram_threshold": 66,
                "disk_threshold": 77,
                "alert_cooldown_minutes": 9,
                "alert_monitor_interval_seconds": 40,
            }
        },
    )
    assert response.status_code == 200, response.text

    rows = db_execute(
        db_conn,
        "SELECT key, value FROM monitor_settings "
        "WHERE key IN "
        "('cpu_threshold','alert_monitor_interval_seconds') "
        "ORDER BY key",
    )
    assert dict(rows) == {
        "cpu_threshold": "55",
        "alert_monitor_interval_seconds": "40",
    }


def test_legacy_monitor_endpoint_reflects_new_values(
    client, auth_headers, clean_settings
):
    client.put(
        "/settings-center/monitoring",
        headers=auth_headers,
        json={
            "values": {
                "cpu_threshold": 42,
                "ram_threshold": 66,
                "disk_threshold": 77,
                "alert_cooldown_minutes": 9,
                "alert_monitor_interval_seconds": 40,
            }
        },
    )

    response = client.get("/settings/monitor", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["cpu_threshold"] == 42


def test_scan_ranges_survive_roundtrip(
    client, auth_headers, clean_settings
):
    client.put(
        "/settings-center/discovery",
        headers=auth_headers,
        json={"values": {"scan_ranges": ["192.168.1.0/24"]}},
    )

    response = client.get("/settings-center", headers=auth_headers)
    discovery = next(
        s for s in response.json()["sections"]
        if s["key"] == "discovery"
    )
    assert discovery["values"]["scan_ranges"] == ["192.168.1.0/24"]


def test_telegram_secret_encrypted_at_rest(
    client, auth_headers, db_conn, clean_settings
):
    marker = _label()

    response = client.put(
        "/settings-center/telegram",
        headers=auth_headers,
        json={
            "values": {
                "telegram_enabled": False,
                "telegram_bot_token": f"secret-{marker}",
                "telegram_chat_id": marker,
            }
        },
    )
    assert response.status_code == 200, response.text

    rows = db_execute(
        db_conn,
        "SELECT key, value FROM monitor_settings "
        "WHERE key = 'telegram_bot_token'",
    )
    assert len(rows) == 1
    stored = rows[0][1]
    assert f"secret-{marker}" not in stored
    assert stored.startswith("gAAAAA")


def test_telegram_secret_masked_in_response(
    client, auth_headers, clean_settings
):
    client.put(
        "/settings-center/telegram",
        headers=auth_headers,
        json={
            "values": {
                "telegram_enabled": False,
                "telegram_bot_token": "super-secret-token",
                "telegram_chat_id": "12345",
            }
        },
    )

    response = client.get("/settings-center", headers=auth_headers)
    telegram = next(
        s for s in response.json()["sections"]
        if s["key"] == "telegram"
    )
    assert telegram["values"]["telegram_bot_token"] == "********"
    assert "super-secret-token" not in response.text


def test_secret_blank_keeps_existing(
    client, auth_headers, db_conn, clean_settings
):
    client.put(
        "/settings-center/telegram",
        headers=auth_headers,
        json={
            "values": {
                "telegram_enabled": False,
                "telegram_bot_token": "first-token",
                "telegram_chat_id": "1",
            }
        },
    )

    before = db_execute(
        db_conn,
        "SELECT value FROM monitor_settings "
        "WHERE key = 'telegram_bot_token'",
    )[0][0]

    client.put(
        "/settings-center/telegram",
        headers=auth_headers,
        json={
            "values": {
                "telegram_enabled": False,
                "telegram_bot_token": "********",
                "telegram_chat_id": "1",
            }
        },
    )

    after = db_execute(
        db_conn,
        "SELECT value FROM monitor_settings "
        "WHERE key = 'telegram_bot_token'",
    )[0][0]

    assert after == before


def test_exam_mode_section_partial_update_keeps_policy(
    client, auth_headers
):
    client.put(
        "/settings-center/exam_mode",
        headers=auth_headers,
        json={"values": {"enabled": True, "usb_policy": "block"}},
    )

    response = client.put(
        "/settings-center/exam_mode",
        headers=auth_headers,
        json={"values": {"enabled": False}},
    )
    assert response.status_code == 200, response.text

    current = client.get("/exam-mode", headers=auth_headers).json()
    assert current["enabled"] is False
    assert current["usb_policy"] == "block"

    client.put(
        "/settings-center/exam_mode",
        headers=auth_headers,
        json={"values": {"enabled": False, "usb_policy": "approval_required"}},
    )


def test_updates_are_audited(client, auth_headers, clean_audit):
    response = client.put(
        "/settings-center/general",
        headers=auth_headers,
        json={"values": {"site_name": _label()}},
    )
    assert response.status_code == 200

    audit = client.get(
        "/settings-center/audit",
        headers=auth_headers,
    ).json()["items"]

    assert any(
        entry["section"] == "general"
        and entry["key"] == "site_name"
        and entry["action"] == "UPDATE"
        for entry in audit
    )


def test_audit_requires_admin(client, viewer_headers):
    response = client.get(
        "/settings-center/audit",
        headers=viewer_headers,
    )
    assert response.status_code in (401, 403)


def test_test_telegram_unconfigured_400(client, auth_headers, clean_settings):
    response = client.post(
        "/settings-center/test",
        headers=auth_headers,
        json={"channel": "telegram"},
    )
    assert response.status_code == 400


def test_test_unknown_channel_400(client, auth_headers):
    response = client.post(
        "/settings-center/test",
        headers=auth_headers,
        json={"channel": "slack"},
    )
    assert response.status_code == 400


def test_test_email_unconfigured_400(client, auth_headers, db_conn):
    db_execute(db_conn, "DELETE FROM email_settings")
    db_execute(
        db_conn,
        "DELETE FROM system_settings WHERE key = 'email'",
    )

    response = client.post(
        "/settings-center/test",
        headers=auth_headers,
        json={"channel": "email"},
    )
    assert response.status_code in (400, 502)


def test_email_section_roundtrip(
    client, auth_headers, db_conn, clean_settings
):
    db_execute(db_conn, "DELETE FROM email_settings")

    marker = f"qa-{uuid.uuid4().hex[:8]}@example.com"

    response = client.put(
        "/settings-center/email",
        headers=auth_headers,
        json={
            "values": {
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": marker,
                "receiver": marker,
                "password": "",
            }
        },
    )
    assert response.status_code == 200, response.text

    fetched = client.get(
        "/settings/email/config",
        headers=auth_headers,
    ).json()
    assert fetched["configured"] is True
    assert fetched["username"] == marker
    assert "password" not in fetched

    listing = client.get("/settings-center", headers=auth_headers).json()
    email = next(
        s for s in listing["sections"] if s["key"] == "email"
    )
    assert email["values"]["smtp_server"] == "smtp.example.com"
    assert email["values"]["password"] == ""


def test_agent_config_returns_interval(
    client, auth_headers, clean_settings
):
    from conftest import AGENT_TOKEN

    response = client.get(
        "/endpoint-activity/agent/config",
        headers={"X-Agent-Token": AGENT_TOKEN},
    )
    assert response.status_code == 200, response.text
    assert response.json()["interval_seconds"] == 30

    client.put(
        "/settings-center/endpoint_activity",
        headers=auth_headers,
        json={"values": {"endpoint_activity_interval_seconds": 120}},
    )

    response = client.get(
        "/endpoint-activity/agent/config",
        headers={"X-Agent-Token": AGENT_TOKEN},
    )
    assert response.status_code == 200
    assert response.json()["interval_seconds"] == 120


def test_agent_config_requires_agent_token(client):
    response = client.get("/agent/config")
    assert response.status_code == 401


def test_agent_config_returns_defaults(client, clean_settings):
    from conftest import AGENT_TOKEN

    response = client.get(
        "/agent/config",
        headers={"X-Agent-Token": AGENT_TOKEN},
    )
    assert response.status_code == 200, response.text

    values = response.json()

    assert values["metrics_interval_seconds"] == 5
    assert values["discovery_interval_seconds"] == 60
    assert values["deployment_poll_interval_seconds"] == 15
    assert values["software_poll_interval_seconds"] == 30
    assert values["web_access_poll_interval_seconds"] == 15
    assert values["network_ranges"] == []


def test_agent_config_reflects_admin_settings(
    client, auth_headers, clean_settings
):
    from conftest import AGENT_TOKEN

    response = client.put(
        "/settings-center/agent",
        headers=auth_headers,
        json={
            "values": {
                "agent_api_url": "http://10.20.30.40:8000",
                "network_ranges": ["10.20.0.0/24", "192.168.5.0/24"],
                "metrics_interval_seconds": 7,
                "discovery_interval_seconds": 90,
                "agent_department": "QA Dept",
                "agent_lab": "Lab 9",
                "agent_location": "Block C",
            }
        },
    )
    assert response.status_code == 200, response.text

    response = client.get(
        "/agent/config",
        headers={"X-Agent-Token": AGENT_TOKEN},
    )
    assert response.status_code == 200, response.text

    values = response.json()

    assert values["agent_api_url"] == "http://10.20.30.40:8000"
    assert values["network_ranges"] == ["10.20.0.0/24", "192.168.5.0/24"]
    assert values["metrics_interval_seconds"] == 7
    assert values["discovery_interval_seconds"] == 90
    assert values["agent_department"] == "QA Dept"
    assert values["agent_lab"] == "Lab 9"
    assert values["agent_location"] == "Block C"


def test_agent_attributes_requires_agent_token(client):
    response = client.post("/agent/attributes", json={})
    assert response.status_code == 401


def test_agent_attributes_updates_device(
    client, db_conn, clean_settings
):
    from conftest import AGENT_TOKEN

    hostname = "qa-attrs-" + uuid.uuid4().hex[:8]

    registered = client.post(
        "/agent/register",
        json={"hostname": hostname, "ip": "10.99.0.50", "os": "Linux"},
    )
    assert registered.status_code == 200, registered.text

    device_id = registered.json()["device_id"]
    token = registered.json()["agent_token"]

    try:
        response = client.post(
            "/agent/attributes",
            headers={"X-Agent-Token": token},
            json={
                "department": "QA Dept",
                "lab": "Lab 9",
                "location": "Block C",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["updated"] == {
            "department": "QA Dept",
            "lab": "Lab 9",
            "location": "Block C",
        }

        row = db_execute(
            db_conn,
            "SELECT department, lab, location FROM devices WHERE id = %s",
            (device_id,),
        )
        assert row[0] == ("QA Dept", "Lab 9", "Block C")
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device_id,))


def test_agent_attributes_ignores_wrong_token(client, db_conn):
    hostname = "qa-attrs-wrong-" + uuid.uuid4().hex[:8]

    registered = client.post(
        "/agent/register",
        json={"hostname": hostname, "ip": "10.99.0.51", "os": "Linux"},
    )
    device_id = registered.json()["device_id"]

    try:
        response = client.post(
            "/agent/attributes",
            headers={"X-Agent-Token": "not-the-real-token"},
            json={"department": "Nope"},
        )
        assert response.status_code == 401
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device_id,))
