import uuid

from conftest import db_execute


def _unique_name():
    return "qa-dept-" + uuid.uuid4().hex[:8]


def test_departments_list_requires_auth(client):
    response = client.get("/departments")
    assert response.status_code == 401


def test_departments_seeded(client, auth_headers):
    response = client.get("/departments", headers=auth_headers)
    assert response.status_code == 200, response.text
    names = [item["name"] for item in response.json()]
    assert "IT" in names


def test_create_department_admin_only(client, viewer_headers, auth_headers, db_conn):
    name = _unique_name()

    response = client.post(
        "/departments",
        headers=viewer_headers,
        json={"name": name},
    )
    assert response.status_code == 403

    response = client.post(
        "/departments",
        headers=auth_headers,
        json={"name": name},
    )
    assert response.status_code == 200, response.text
    department_id = response.json()["id"]

    try:
        duplicate = client.post(
            "/departments",
            headers=auth_headers,
            json={"name": name},
        )
        assert duplicate.status_code == 409

        empty = client.post(
            "/departments",
            headers=auth_headers,
            json={"name": "   "},
        )
        assert empty.status_code == 400

        updated = client.put(
            f"/departments/{department_id}",
            headers=auth_headers,
            json={"name": name + "-v2"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == name + "-v2"

        listing = client.get("/departments", headers=auth_headers)
        assert listing.status_code == 200
        assert name + "-v2" in [item["name"] for item in listing.json()]

        deleted = client.delete(
            f"/departments/{department_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        missing = client.delete(
            f"/departments/{department_id}",
            headers=auth_headers,
        )
        assert missing.status_code == 404
    finally:
        db_execute(db_conn, "DELETE FROM departments WHERE name LIKE %s", (name + "%",))


def test_delete_department_resets_devices_to_unknown(
    client, auth_headers, db_conn
):
    name = _unique_name()
    department_id = None

    try:
        created = client.post(
            "/departments",
            headers=auth_headers,
            json={"name": name},
        )
        assert created.status_code == 200, created.text
        department_id = created.json()["id"]

        cursor = db_conn.cursor()
        cursor.execute(
            "UPDATE devices SET department = %s WHERE id = 1",
            (name,),
        )
        cursor.close()

        deleted = client.delete(
            f"/departments/{department_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        cursor = db_conn.cursor()
        cursor.execute("SELECT department FROM devices WHERE id = 1")
        department = cursor.fetchone()[0]
        cursor.close()
        assert department == "Unknown"
    finally:
        if department_id is not None:
            db_execute(db_conn, "DELETE FROM departments WHERE id = %s", (department_id,))


def test_monitor_settings_get_and_update_admin_only(
    client, viewer_headers, auth_headers, db_conn
):
    original = client.get(
        "/settings/monitor",
        headers=auth_headers,
    )
    assert original.status_code == 200, original.text
    original_thresholds = {
        "cpu_threshold": original.json()["cpu_threshold"],
        "ram_threshold": original.json()["ram_threshold"],
        "disk_threshold": original.json()["disk_threshold"],
        "alert_cooldown_minutes": original.json()["alert_cooldown_minutes"],
    }

    try:
        viewer_put = client.put(
            "/settings/monitor",
            headers=viewer_headers,
            json={
                "cpu_threshold": 5,
                "ram_threshold": 5,
                "disk_threshold": 5,
                "alert_cooldown_minutes": 1,
            },
        )
        assert viewer_put.status_code == 403

        updated = client.put(
            "/settings/monitor",
            headers=auth_headers,
            json={
                "cpu_threshold": 81,
                "ram_threshold": 91,
                "disk_threshold": 92,
                "alert_cooldown_minutes": 7,
            },
        )
        assert updated.status_code == 200, updated.text
        thresholds = updated.json()["thresholds"]
        assert thresholds["cpu_threshold"] == 81
        assert thresholds["ram_threshold"] == 91
        assert thresholds["disk_threshold"] == 92
        assert thresholds["alert_cooldown_minutes"] == 7

        fetched = client.get(
            "/settings/monitor",
            headers=auth_headers,
        )
        assert fetched.json()["cpu_threshold"] == 81

        invalid = client.put(
            "/settings/monitor",
            headers=auth_headers,
            json={
                "cpu_threshold": 0,
                "ram_threshold": 91,
                "disk_threshold": 92,
                "alert_cooldown_minutes": 7,
            },
        )
        assert invalid.status_code == 400

        with_ranges = client.put(
            "/settings/monitor",
            headers=auth_headers,
            json={
                "cpu_threshold": 82,
                "ram_threshold": 91,
                "disk_threshold": 92,
                "alert_cooldown_minutes": 7,
                "scan_ranges": ["192.168.50.0/24"],
            },
        )
        assert with_ranges.status_code == 200, with_ranges.text
        assert with_ranges.json()["scan_ranges"] == ["192.168.50.0/24"]

        bad_range = client.put(
            "/settings/monitor",
            headers=auth_headers,
            json={
                "cpu_threshold": 82,
                "ram_threshold": 91,
                "disk_threshold": 92,
                "alert_cooldown_minutes": 7,
                "scan_ranges": ["nope"],
            },
        )
        assert bad_range.status_code == 400

        cleared = client.put(
            "/settings/monitor",
            headers=auth_headers,
            json={
                "cpu_threshold": 82,
                "ram_threshold": 91,
                "disk_threshold": 92,
                "alert_cooldown_minutes": 7,
                "scan_ranges": [],
            },
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["scan_ranges"] == []
    finally:
        for key, value in original_thresholds.items():
            db_execute(
                db_conn,
                "DELETE FROM monitor_settings WHERE key = %s",
                (key,),
            )
            db_execute(
                db_conn,
                "INSERT INTO monitor_settings (key, value) VALUES (%s, %s)",
                (key, str(value)),
            )


def test_scan_ranges_admin_only_and_validation(
    client, viewer_headers, auth_headers, db_conn
):
    original = client.get(
        "/settings/monitor",
        headers=auth_headers,
    ).json()["scan_ranges"]

    try:
        viewer_put = client.put(
            "/settings/monitor/ranges",
            headers=viewer_headers,
            json={"ranges": ["10.0.0.0/24"]},
        )
        assert viewer_put.status_code == 403

        invalid = client.put(
            "/settings/monitor/ranges",
            headers=auth_headers,
            json={"ranges": ["not-a-cidr"]},
        )
        assert invalid.status_code == 400

        updated = client.put(
            "/settings/monitor/ranges",
            headers=auth_headers,
            json={"ranges": ["10.0.0.0/24", "172.16.0.0/16"]},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["scan_ranges"] == ["10.0.0.0/24", "172.16.0.0/16"]

        fetched = client.get(
            "/settings/monitor",
            headers=auth_headers,
        )
        assert fetched.json()["scan_ranges"] == ["10.0.0.0/24", "172.16.0.0/16"]
    finally:
        db_execute(
            db_conn,
            "DELETE FROM monitor_settings WHERE key = 'scan_ranges'",
        )
        if original:
            import json

            db_execute(
                db_conn,
                "INSERT INTO monitor_settings (key, value) VALUES ('scan_ranges', %s)",
                (json.dumps(original),),
            )


def test_email_config_json_save_keep_password_and_reset(
    client, auth_headers, db_conn
):
    db_execute(db_conn, "DELETE FROM email_settings")

    try:
        saved = client.post(
            "/settings/email/config",
            headers=auth_headers,
            json={
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "alerts@example.com",
                "receiver": "ops@example.com",
                "password": "super-secret",
            },
        )
        assert saved.status_code == 200, saved.text

        cursor = db_conn.cursor()
        cursor.execute("SELECT password FROM email_settings LIMIT 1")
        assert cursor.fetchone()[0] == "super-secret"
        cursor.close()

        updated = client.post(
            "/settings/email/config",
            headers=auth_headers,
            json={
                "smtp_server": "smtp2.example.com",
                "smtp_port": 465,
                "username": "alerts@example.com",
                "receiver": "ops@example.com",
                "password": "",
            },
        )
        assert updated.status_code == 200, updated.text

        cursor = db_conn.cursor()
        cursor.execute("SELECT smtp_server, smtp_port, password FROM email_settings LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        assert row[0] == "smtp2.example.com"
        assert row[1] == 465
        assert row[2] == "super-secret", "blank password must keep existing"

        config = client.get(
            "/settings/email/config",
            headers=auth_headers,
        )
        assert config.status_code == 200
        assert config.json()["configured"] is True
        assert "password" not in config.json()

        reset = client.delete(
            "/settings/email/config",
            headers=auth_headers,
        )
        assert reset.status_code == 200
        assert reset.json()["configured"] is False

        config = client.get(
            "/settings/email/config",
            headers=auth_headers,
        )
        assert config.json()["configured"] is False
    finally:
        db_execute(db_conn, "DELETE FROM email_settings")


def test_test_email_returns_502_without_config(client, auth_headers, db_conn):
    db_execute(db_conn, "DELETE FROM email_settings")

    try:
        response = client.post(
            "/settings/test-email",
            headers=auth_headers,
        )
        assert response.status_code == 502
    finally:
        db_execute(db_conn, "DELETE FROM email_settings")