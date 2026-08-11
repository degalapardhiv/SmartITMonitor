import uuid

from conftest import db_execute


def test_usb_events_require_agent_token(client):
    response = client.post(
        "/usb/events",
        json={"device_id": 1, "description": "no-token"},
    )
    assert response.status_code in (401, 422)


def test_usb_requests_requires_auth(client):
    response = client.get("/usb/requests")
    assert response.status_code == 401


def test_usb_decision_auto_resolves_pending_alert(client, auth_headers, db_conn):
    from conftest import AGENT_TOKEN

    label = f"verify-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/usb/events",
        headers={"X-Agent-Token": AGENT_TOKEN},
        json={
            "device_id": 1,
            "usb_id": f"USB-{label}",
            "description": label,
        },
    )
    assert response.status_code == 200, response.text
    request_id = response.json()["id"]

    alert_id = None
    try:
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT id FROM alerts WHERE device_id = 1 AND alert_type = 'USB_PENDING'"
            " AND status = 'OPEN' AND message LIKE %s ORDER BY id DESC LIMIT 1",
            (f"%{label}%",),
        )
        row = cursor.fetchone()
        cursor.close()
        assert row is not None, "USB_PENDING alert was not created"
        alert_id = row[0]

        response = client.post(
            f"/usb/requests/{request_id}/decision",
            headers=auth_headers,
            json={"decision": "approved"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "approved"

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT status, resolved_at FROM alerts WHERE id = %s",
            (alert_id,),
        )
        status, resolved_at = cursor.fetchone()
        cursor.close()

        assert status == "RESOLVED", "USB_PENDING alert not resolved after approval"
        assert resolved_at is not None
    finally:
        if alert_id is not None:
            db_execute(db_conn, "DELETE FROM alerts WHERE id = %s", (alert_id,))
        db_execute(db_conn, "DELETE FROM usb_requests WHERE id = %s", (request_id,))
