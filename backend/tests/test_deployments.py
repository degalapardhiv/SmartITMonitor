import hashlib
import uuid

from conftest import db_execute


def _unique(prefix="qa-dep"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _approved_image(db_session, checksum=None):
    from app.os_image_model import OSImage

    image = OSImage(
        name=_unique("qa-img"),
        version="24.04",
        edition="Server",
        architecture="x86_64",
        checksum=checksum or "",
        checksum_type="sha256",
        approved=True,
    )

    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    return image


def _enrolled_device(db_session, hostname=None, online=True, os="Ubuntu x86_64"):
    from app.models import Device

    device = Device(
        hostname=hostname or _unique("qa-dev"),
        ip="192.168.1.200",
        status="online" if online else "offline",
        department="IT",
        lab="Lab-1",
        location="Building A",
        os=os,
        agent_token=uuid.uuid4().hex[:32],
    )

    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    return device


def test_deployments_requires_auth(client):
    response = client.get("/deployments")
    assert response.status_code == 401


def test_create_deployment_admin_only(client, viewer_headers, auth_headers):
    viewer_create = client.post(
        "/deployments",
        headers=viewer_headers,
        json={"os_image_id": 1, "target_type": "all"},
    )
    assert viewer_create.status_code == 403


def test_create_deployment_rejects_unapproved_image(client, auth_headers, db_conn):
    from app.os_image_model import OSImage

    image = OSImage(
        name=_unique("qa-img"),
        version="1.0",
        approved=False,
    )

    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO os_images (name, version, architecture, checksum_type, approved, created_at)"
        " VALUES (%s, '1.0', 'x86_64', 'sha256', FALSE, now()) RETURNING id",
        (image.name,),
    )
    image_id = cursor.fetchone()[0]
    cursor.close()

    try:
        response = client.post(
            "/deployments",
            headers=auth_headers,
            json={"os_image_id": image_id, "target_type": "all"},
        )
        assert response.status_code == 400
        assert "approved" in response.json()["detail"].lower()
    finally:
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image_id,))


def test_create_deployment_no_targets(client, auth_headers, db_conn):
    from app.os_image_model import OSImage

    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO os_images (name, version, architecture, checksum_type, approved, created_at)"
        " VALUES (%s, '1.0', 'x86_64', 'sha256', TRUE, now()) RETURNING id",
        (_unique("qa-img"),),
    )
    image_id = cursor.fetchone()[0]
    cursor.close()

    try:
        response = client.post(
            "/deployments",
            headers=auth_headers,
            json={
                "os_image_id": image_id,
                "target_type": "department",
                "target_value": "qa-nonexistent-dept",
            },
        )
        assert response.status_code == 400
        assert "No target computers" in response.json()["detail"]

        missing_image = client.post(
            "/deployments",
            headers=auth_headers,
            json={"os_image_id": 999999, "target_type": "all"},
        )
        assert missing_image.status_code == 404

        missing_value = client.post(
            "/deployments",
            headers=auth_headers,
            json={"os_image_id": image_id, "target_type": "lab"},
        )
        assert missing_value.status_code == 400
    finally:
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image_id,))


def test_deploy_validation_rejects_non_enrolled_and_offline(client, auth_headers, db_conn):
    from app.os_image_model import OSImage

    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO os_images (name, version, architecture, checksum_type, approved, created_at)"
        " VALUES (%s, '1.0', 'x86_64', 'sha256', TRUE, now()) RETURNING id",
        (_unique("qa-img"),),
    )
    image_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO devices (hostname, ip, status, department, lab, location, os)"
        " VALUES (%s, '10.0.0.1', 'offline', 'IT', 'Lab-1', 'Building A', 'Ubuntu x86_64')"
        " RETURNING id, hostname",
        (_unique("qa-dev"),),
    )
    offline_id, offline_hostname = cursor.fetchone()

    cursor.execute(
        "INSERT INTO devices (hostname, ip, status, department, lab, location, os)"
        " VALUES (%s, '10.0.0.2', 'online', 'IT', 'Lab-1', 'Building A', 'Ubuntu x86_64')"
        " RETURNING id, hostname",
        (_unique("qa-dev"),),
    )
    unenrolled_id, unenrolled_hostname = cursor.fetchone()
    cursor.close()

    try:
        response = client.post(
            "/deployments",
            headers=auth_headers,
            json={
                "os_image_id": image_id,
                "target_type": "lab",
                "target_value": "Lab-1",
            },
        )
        assert response.status_code == 200
        body = response.json()

        assert any(
            d["hostname"] == offline_hostname
            for d in body.get("offline", [])
        )

        assert any(
            d["hostname"] == unenrolled_hostname
            for d in body.get("rejected", [])
        )

        rejected = next(
            d for d in body["rejected"] if d["hostname"] == unenrolled_hostname
        )
        assert any("enrolled" in reason.lower() for reason in rejected["reasons"])
    finally:
        db_execute(db_conn, "DELETE FROM deployments WHERE os_image_id = %s", (image_id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id IN (%s, %s)", (offline_id, unenrolled_id))
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image_id,))


def test_deployment_lifecycle_service(monkeypatch, tmp_path, db_conn, db_session):
    from app.services.deployment_service import (
        check_deployment,
        create_deployments,
    )

    checksum = hashlib.sha256(b"deploy-content" * 64).hexdigest()

    (tmp_path / checksum).write_bytes(b"deploy-content" * 64)

    image = _approved_image(db_session, checksum=checksum)

    device = _enrolled_device(db_session)

    try:
        monkeypatch.setenv("SMARTIT_IMAGE_DIR", str(tmp_path))
        monkeypatch.setenv("SMARTIT_PXE_DIR", str(tmp_path / "pxe"))
        (tmp_path / "pxe").mkdir()

        result = create_deployments(
            db_session,
            image,
            [device],
            "admin",
        )

        created = result["created"]

        assert len(created) == 1
        deployment_id = created[0]["id"]
        assert created[0]["status"] == "INSTALLING"
        assert created[0]["progress"] >= 40

        pxe_files = list((tmp_path / "pxe").glob("*"))
        assert len(pxe_files) == 1
        config = pxe_files[0].read_text()
        assert "default smartit-" in config
        assert image.kernel_path or "/images/vmlinuz" in config

        from app.deployment_model import Deployment

        deployment = (
            db_session.query(Deployment)
            .filter(Deployment.id == deployment_id)
            .first()
        )

        assert deployment is not None
        assert deployment.status == "INSTALLING"
        assert deployment.progress == 40

        device.status = "offline"
        db_session.commit()

        check_deployment(db_session, deployment)

        db_session.refresh(deployment)
        assert deployment.progress == 60

        from datetime import datetime

        device.status = "online"
        device.os = f"{image.name} {image.version}"
        device.last_seen = datetime.utcnow()
        db_session.commit()

        from app.metric_model import DeviceMetric

        db_session.add(
            DeviceMetric(
                device_id=device.id,
                cpu=5.0,
                ram=50.0,
                disk=20.0,
            )
        )
        db_session.commit()

        check_deployment(db_session, deployment)

        db_session.refresh(deployment)
        assert deployment.status == "COMPLETED"
        assert deployment.progress == 100
        assert deployment.verified_agent is True
        assert deployment.verified_heartbeat is True
        assert deployment.verified_metrics is True
        assert deployment.verified_os is True
        assert deployment.verified_at is not None
    finally:
        db_execute(db_conn, "DELETE FROM deployments WHERE hostname = %s", (device.hostname,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image.id,))


def test_deployment_offline_to_pending_service(monkeypatch, tmp_path, db_conn, db_session):
    from app.deployment_model import Deployment
    from app.services.deployment_service import (
        check_deployment,
        create_deployments,
    )

    checksum = hashlib.sha256(b"offline-content" * 64).hexdigest()

    (tmp_path / checksum).write_bytes(b"offline-content" * 64)

    image = _approved_image(db_session, checksum=checksum)

    device = _enrolled_device(db_session, online=False)

    try:
        monkeypatch.setenv("SMARTIT_IMAGE_DIR", str(tmp_path))
        monkeypatch.setenv("SMARTIT_PXE_DIR", str(tmp_path / "pxe"))
        (tmp_path / "pxe").mkdir()

        result = create_deployments(db_session, image, [device], "admin")

        assert len(result["offline"]) == 1
        assert result["created"] == []

        deployment = (
            db_session.query(Deployment)
            .filter(Deployment.device_id == device.id)
            .first()
        )
        assert deployment.status == "OFFLINE"

        device.status = "online"
        db_session.commit()

        check_deployment(db_session, deployment)

        db_session.refresh(deployment)
        assert deployment.status == "INSTALLING"
        assert deployment.progress >= 40
    finally:
        db_execute(db_conn, "DELETE FROM deployments WHERE device_id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image.id,))


def test_deployment_fails_without_pxe(monkeypatch, tmp_path, db_conn, db_session):
    from app.services.deployment_service import create_deployments

    checksum = hashlib.sha256(b"nopxe-content" * 64).hexdigest()

    (tmp_path / checksum).write_bytes(b"nopxe-content" * 64)

    image = _approved_image(db_session, checksum=checksum)

    device = _enrolled_device(db_session)

    try:
        monkeypatch.setenv("SMARTIT_IMAGE_DIR", str(tmp_path))
        monkeypatch.delenv("SMARTIT_PXE_DIR", raising=False)

        result = create_deployments(db_session, image, [device], "admin")

        assert len(result["created"]) == 1
        assert result["created"][0]["status"] == "FAILED"
        assert "PXE" in result["created"][0]["error"]
    finally:
        db_execute(db_conn, "DELETE FROM deployments WHERE device_id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image.id,))


def test_agent_pending_and_ack(client, auth_headers, db_conn):
    from app.os_image_model import OSImage

    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO os_images (name, version, architecture, checksum_type, approved, created_at)"
        " VALUES (%s, '1.0', 'x86_64', 'sha256', TRUE, now()) RETURNING id",
        (_unique("qa-img"),),
    )
    image_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO devices (hostname, ip, status, department, lab, location, os, agent_token)"
        " VALUES (%s, '10.0.0.9', 'online', 'IT', 'Lab-9', 'Building A', 'Ubuntu x86_64', %s)"
        " RETURNING id",
        (_unique("qa-dev"), _unique("tok")),
    )
    device_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO deployments (device_id, os_image_id, hostname, ip, status, progress, created_by, created_at)"
        " VALUES (%s, %s, %s, '10.0.0.9', 'PENDING', 0, 'admin', now()) RETURNING id",
        (device_id, image_id, "agent-test-host"),
    )
    deployment_id = cursor.fetchone()[0]
    cursor.close()

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT agent_token FROM devices WHERE id = %s",
        (device_id,),
    )
    token = cursor.fetchone()[0]
    cursor.close()

    try:
        no_auth = client.get("/deployments/agent/pending")
        assert no_auth.status_code == 401

        pending = client.get(
            "/deployments/agent/pending",
            headers={"X-Agent-Token": token},
        )
        assert pending.status_code == 200
        assert pending.json()["id"] == deployment_id

        wrong_deployment = client.post(
            f"/deployments/{deployment_id}/agent-ack",
            headers={"X-Agent-Token": _unique("tok")},
        )
        assert wrong_deployment.status_code == 401

        ack = client.post(
            f"/deployments/{deployment_id}/agent-ack",
            headers={"X-Agent-Token": token},
        )
        assert ack.status_code == 200
        assert ack.json()["id"] == deployment_id
    finally:
        db_execute(db_conn, "DELETE FROM deployments WHERE id = %s", (deployment_id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device_id,))
        db_execute(db_conn, "DELETE FROM os_images WHERE id = %s", (image_id,))