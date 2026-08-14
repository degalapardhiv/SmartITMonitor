import uuid

import pytest

from conftest import AGENT_TOKEN, db_execute


def _label():
    return "qa-activity-" + uuid.uuid4().hex[:8]


def _submit_events(client, events):
    return client.post(
        "/endpoint-activity",
        headers={"X-Agent-Token": AGENT_TOKEN},
        json={"events": events},
    )


@pytest.fixture()
def clean_activity(db_conn):
    yield
    db_execute(
        db_conn,
        "DELETE FROM endpoint_activity WHERE description LIKE %s",
        ("qa-activity-%",),
    )


@pytest.fixture()
def activity_settings(client, auth_headers):
    original = client.get(
        "/endpoint-activity/settings",
        headers=auth_headers,
    ).json()["settings"]
    yield original
    client.put(
        "/endpoint-activity/settings",
        headers=auth_headers,
        json={
            "url_auditing": original["url_auditing"],
            "retention_days": original["retention_days"],
        },
    )


def test_submit_requires_agent_token(client):
    response = client.post(
        "/endpoint-activity",
        json={"events": [{"event_type": "system_boot"}]},
    )
    assert response.status_code in (401, 422)


def test_submit_invalid_token(client):
    response = client.post(
        "/endpoint-activity",
        headers={"X-Agent-Token": "not-a-real-token"},
        json={"events": [{"event_type": "system_boot"}]},
    )
    assert response.status_code == 401


def test_submit_stores_events(client, auth_headers, db_conn, clean_activity):
    label = _label()

    response = _submit_events(
        client,
        [
            {
                "event_type": "app_launched",
                "application": "firefox",
                "username": "qa-user",
                "description": label,
            },
            {
                "event_type": "system_boot",
                "description": label,
            },
        ],
    )
    assert response.status_code == 200, response.text
    assert response.json()["stored"] == 2

    listing = client.get("/endpoint-activity", headers=auth_headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    matched = [e for e in items if e["description"] == label]
    assert len(matched) == 2
    assert {e["event_type"] for e in matched} == {"app_launched", "system_boot"}
    assert all(e["hostname"] for e in matched)


def test_submit_unsupported_event_type(client):
    response = _submit_events(
        client,
        [{"event_type": "totally_made_up"}],
    )
    assert response.status_code == 400


def test_submit_batch_too_large(client):
    events = [
        {"event_type": "system_boot", "description": f"evt-{i}"}
        for i in range(101)
    ]
    response = _submit_events(client, events)
    assert response.status_code == 400


def test_submit_scrubs_sensitive_metadata(
    client, auth_headers, db_conn, clean_activity
):
    label = _label()

    response = _submit_events(
        client,
        [
            {
                "event_type": "system_boot",
                "description": label,
                "metadata": {
                    "password": "hunter2",
                    "token": "abc123",
                    "device": "sensor-01",
                },
            }
        ],
    )
    assert response.status_code == 200

    listing = client.get("/endpoint-activity", headers=auth_headers)
    item = next(e for e in listing.json()["items"] if e["description"] == label)
    assert item["metadata"]["device"] == "sensor-01"
    assert "password" not in item["metadata"]
    assert "token" not in item["metadata"]


def test_url_events_stripped_when_auditing_disabled(
    client, auth_headers, activity_settings, clean_activity
):
    if activity_settings["url_auditing"]:
        client.put(
            "/endpoint-activity/settings",
            headers=auth_headers,
            json={"url_auditing": False},
        )

    label = _label()

    response = _submit_events(
        client,
        [
            {
                "event_type": "url_visited",
                "url": f"https://{label}.example.com/page",
                "description": label,
            }
        ],
    )
    assert response.status_code == 200

    listing = client.get("/endpoint-activity", headers=auth_headers)
    item = next(e for e in listing.json()["items"] if e["description"] == label)
    assert item["url"] == ""
    assert item["domain"] == ""


def test_url_events_stored_when_auditing_enabled(
    client, auth_headers, activity_settings, clean_activity
):
    client.put(
        "/endpoint-activity/settings",
        headers=auth_headers,
        json={"url_auditing": True},
    )

    label = _label()

    response = _submit_events(
        client,
        [
            {
                "event_type": "url_visited",
                "url": f"https://{label}.example.com/page",
                "description": label,
            }
        ],
    )
    assert response.status_code == 200

    listing = client.get("/endpoint-activity", headers=auth_headers)
    item = next(e for e in listing.json()["items"] if e["description"] == label)
    assert item["url"] == f"https://{label}.example.com/page"
    assert item["domain"] == f"{label}.example.com"


def test_list_requires_auth(client):
    response = client.get("/endpoint-activity")
    assert response.status_code == 401


def test_list_viewer_forbidden(client, viewer_headers):
    response = client.get("/endpoint-activity", headers=viewer_headers)
    assert response.status_code == 403


def test_list_filters(
    client, auth_headers, db_conn, clean_activity
):
    label = _label()

    response = _submit_events(
        client,
        [
            {
                "event_type": "app_launched",
                "application": "gimp",
                "username": "qa-alice",
                "description": f"{label} gimp",
            },
            {
                "event_type": "user_login",
                "username": "qa-bob",
                "description": f"{label} login",
            },
        ],
    )
    assert response.status_code == 200

    by_type = client.get(
        "/endpoint-activity",
        headers=auth_headers,
        params={"event_type": "user_login"},
    )
    items = by_type.json()["items"]
    assert all(e["event_type"] == "user_login" for e in items)
    assert any(e["description"] == f"{label} login" for e in items)

    by_search = client.get(
        "/endpoint-activity",
        headers=auth_headers,
        params={"search": "qa-alice"},
    )
    items = by_search.json()["items"]
    assert any(e["username"] == "qa-alice" for e in items)

    by_type_and_search = client.get(
        "/endpoint-activity",
        headers=auth_headers,
        params={"event_type": "app_launched", "search": "gimp"},
    )
    items = by_type_and_search.json()["items"]
    assert any(e["description"] == f"{label} gimp" for e in items)
    assert all(e["event_type"] == "app_launched" for e in items)


def test_devices_and_types_endpoints(client, auth_headers, clean_activity):
    label = _label()

    response = _submit_events(
        client,
        [{"event_type": "software_installed", "description": label}],
    )
    assert response.status_code == 200

    devices = client.get("/endpoint-activity/devices", headers=auth_headers)
    assert devices.status_code == 200
    assert any(
        d["event_count"] > 0 and d["hostname"]
        for d in devices.json()["devices"]
    )

    types = client.get("/endpoint-activity/types", headers=auth_headers)
    assert types.status_code == 200
    assert "software_installed" in types.json()["types"]


def test_export_csv(client, auth_headers, clean_activity):
    label = _label()

    response = _submit_events(
        client,
        [{"event_type": "network_connected", "description": label}],
    )
    assert response.status_code == 200

    export = client.get(
        "/endpoint-activity/export",
        headers=auth_headers,
        params={"search": label},
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "network_connected" in export.text
    assert label in export.text
    assert export.headers["content-disposition"].startswith("attachment")


def test_export_requires_admin(client, viewer_headers):
    response = client.get("/endpoint-activity/export", headers=viewer_headers)
    assert response.status_code == 403


def test_settings_updated_and_audited(
    client, auth_headers, activity_settings
):
    response = client.put(
        "/endpoint-activity/settings",
        headers=auth_headers,
        json={"retention_days": 60},
    )
    assert response.status_code == 200, response.text
    assert response.json()["settings"]["retention_days"] == 60

    audit = response.json()["audit"]
    assert any(
        entry["action"] == "SETTINGS_UPDATED"
        and "retention_days" in entry["detail"]
        for entry in audit
    )


def test_settings_viewed_is_audited(client, auth_headers):
    response = client.get("/endpoint-activity/settings", headers=auth_headers)
    assert response.status_code == 200
    audit = response.json()["audit"]
    assert any(entry["action"] == "SETTINGS_VIEWED" for entry in audit)


def test_settings_require_admin(client, viewer_headers):
    response = client.put(
        "/endpoint-activity/settings",
        headers=viewer_headers,
        json={"retention_days": 10},
    )
    assert response.status_code == 403


def test_retention_cleanup_removes_old_events(
    client, auth_headers, activity_settings, db_conn, db_session
):
    client.put(
        "/endpoint-activity/settings",
        headers=auth_headers,
        json={"retention_days": 1},
    )

    label = _label()

    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO endpoint_activity (
            device_id, hostname, username, event_type, application,
            domain, url, description, metadata, timestamp
        )
        VALUES (
            1, 'qa-old-host', 'qa-user', 'system_boot', '',
            '', '', %s, '', NOW() - INTERVAL '30 days'
        )
        """,
        (label,),
    )
    cursor.close()

    rows = db_execute(
        db_conn,
        "SELECT id FROM endpoint_activity WHERE description = %s",
        (label,),
    )
    assert len(rows) == 1, "old event fixture was not inserted"

    from app.services.endpoint_activity_service import retention_cleanup

    deleted = retention_cleanup(db_session)

    assert deleted >= 1

    rows = db_execute(
        db_conn,
        "SELECT id FROM endpoint_activity WHERE description = %s",
        (label,),
    )
    assert rows == []
