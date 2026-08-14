import uuid


def test_alerts_requires_auth(client):
    response = client.get("/alerts")
    assert response.status_code == 401


def test_get_alerts_returns_list(client, auth_headers):
    response = client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    assert len(alerts) > 0


def test_resolve_alert(client, auth_headers, test_alert_id):
    response = client.patch(
        f"/alerts/{test_alert_id}/resolve",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["id"] == test_alert_id


def test_auto_resolve_on_recovery(db_conn, db_session):
    from conftest import db_execute
    from app.models import Device
    from app.services.alert_service import resolve_recovered_alert

    hostname = f"qa-test-recovery-{uuid.uuid4().hex[:8]}"
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (device_id, hostname, alert_type, value, severity, status)"
        " VALUES (1, %s, 'CPU', 95, 'HIGH', 'OPEN') RETURNING id",
        (hostname,),
    )
    alert_id = cursor.fetchone()[0]
    cursor.close()

    try:
        device = db_session.query(Device).filter(Device.id == 1).first()
        resolved = resolve_recovered_alert(
            db_session,
            device,
            "CPU",
            10,
            f"CPU usage recovered: 10%",
        )

        assert resolved is not None

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT status, resolved_at FROM alerts WHERE id = %s",
            (alert_id,),
        )
        status, resolved_at = cursor.fetchone()
        cursor.close()

        assert status == "RESOLVED"
        assert resolved_at is not None
    finally:
        db_execute(db_conn, "DELETE FROM alerts WHERE id = %s", (alert_id,))
