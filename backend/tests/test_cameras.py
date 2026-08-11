import uuid

from conftest import db_execute


def _unique_name():
    return f"qa-cam-{uuid.uuid4().hex[:8]}"


def test_cameras_requires_auth(client):
    response = client.get("/cameras")
    assert response.status_code == 401


def test_create_camera_admin_only(client, viewer_headers, auth_headers, db_conn):
    name = _unique_name()

    viewer_create = client.post(
        "/cameras",
        headers=viewer_headers,
        json={
            "name": name,
            "ip": "192.168.1.101",
        },
    )
    assert viewer_create.status_code == 403

    response = client.post(
        "/cameras",
        headers=auth_headers,
        json={
            "name": name,
            "ip": "192.168.1.101",
            "stream_url": "rtsp://192.168.1.101:554/stream",
            "location": "Test Lab",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == name
    assert body["ip"] == "192.168.1.101"
    assert body["status"] == "unknown"

    try:
        duplicate = client.post(
            "/cameras",
            headers=auth_headers,
            json={"name": name, "ip": "10.0.0.1"},
        )
        assert duplicate.status_code == 409

        missing_name = client.post(
            "/cameras",
            headers=auth_headers,
            json={"name": "  ", "ip": "10.0.0.2"},
        )
        assert missing_name.status_code == 400

        missing_ip = client.post(
            "/cameras",
            headers=auth_headers,
            json={"name": _unique_name(), "ip": ""},
        )
        assert missing_ip.status_code == 400
    finally:
        db_execute(
            db_conn,
            "DELETE FROM cameras WHERE name LIKE %s", ("qa-cam-%",),
        )


def test_camera_crud_roundtrip(client, auth_headers, db_conn):
    name = _unique_name()

    created = client.post(
        "/cameras",
        headers=auth_headers,
        json={
            "name": name,
            "ip": "192.168.1.101",
            "location": "Entrance",
        },
    )
    assert created.status_code == 200
    camera_id = created.json()["id"]

    try:
        listed = client.get("/cameras", headers=auth_headers)
        assert listed.status_code == 200
        names = [c["name"] for c in listed.json()]
        assert name in names

        found = next(c for c in listed.json() if c["name"] == name)
        assert found["location"] == "Entrance"
        assert found["status"] == "unknown"

        updated = client.put(
            f"/cameras/{camera_id}",
            headers=auth_headers,
            json={
                "name": f"{name}-renamed",
                "ip": "192.168.1.102",
                "location": "Exit",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == f"{name}-renamed"
        assert updated.json()["ip"] == "192.168.1.102"

        not_found = client.put(
            "/cameras/999999",
            headers=auth_headers,
            json={"name": "x", "ip": "10.0.0.1"},
        )
        assert not_found.status_code == 404

        deleted = client.delete(
            f"/cameras/{camera_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        gone = client.delete(
            f"/cameras/{camera_id}",
            headers=auth_headers,
        )
        assert gone.status_code == 404
    finally:
        db_execute(
            db_conn,
            "DELETE FROM cameras WHERE name LIKE %s", ("qa-cam-%",),
        )


def test_check_camera_marks_offline(client, auth_headers, db_conn):
    name = _unique_name()

    created = client.post(
        "/cameras",
        headers=auth_headers,
        json={
            "name": name,
            "ip": "192.0.2.1",
            "stream_url": "rtsp://192.0.2.1:554/stream",
        },
    )
    assert created.status_code == 200
    camera_id = created.json()["id"]

    try:
        response = client.post(
            f"/cameras/{camera_id}/check",
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "offline"
        assert body["alert_created"] is False

        missing = client.post(
            "/cameras/999999/check",
            headers=auth_headers,
        )
        assert missing.status_code == 404
    finally:
        db_execute(
            db_conn,
            "DELETE FROM cameras WHERE name LIKE %s", ("qa-cam-%",),
        )


def test_camera_offline_alert_and_resolve(db_conn, db_session):
    from app.camera_model import Camera
    from app.services.camera_service import check_camera, create_camera_alert

    name = _unique_name()

    camera = Camera(
        name=name,
        ip="192.0.2.1",
        stream_url="rtsp://192.0.2.1:554/stream",
        status="online",
        location="Unit",
    )

    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    try:
        alert = create_camera_alert(db_session, camera)
        assert alert is not None
        assert alert.alert_type == "CAMERA_OFFLINE"
        assert alert.severity == "HIGH"
        assert alert.status == "OPEN"

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT alert_type, status, hostname FROM alerts WHERE id = %s",
            (alert.id,),
        )
        row = cursor.fetchone()
        cursor.close()

        assert row == ("CAMERA_OFFLINE", "OPEN", name)

        alert = create_camera_alert(db_session, camera)
        assert alert is None

        camera.status = "online"
        db_session.commit()

        from app.services.camera_service import resolve_camera_alerts

        resolved = resolve_camera_alerts(db_session, camera)
        assert len(resolved) == 1

        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT status, resolved_at FROM alerts WHERE id = %s",
            (resolved[0].id,),
        )
        status, resolved_at = cursor.fetchone()
        cursor.close()

        assert status == "RESOLVED"
        assert resolved_at is not None

        response = check_camera(db_session, camera)
        assert response is not None
        assert response.status == "OPEN"
    finally:
        db_execute(db_conn, "DELETE FROM alerts WHERE hostname = %s", (name,))
        db_execute(db_conn, "DELETE FROM cameras WHERE name = %s", (name,))