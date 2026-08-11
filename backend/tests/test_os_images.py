import hashlib
import uuid

from conftest import db_execute


def _unique_name():
    return f"qa-img-{uuid.uuid4().hex[:8]}"


def test_os_images_requires_auth(client):
    response = client.get("/os-images")
    assert response.status_code == 401


def test_create_image_admin_only(client, viewer_headers, auth_headers, db_conn):
    name = _unique_name()

    viewer_create = client.post(
        "/os-images",
        headers=viewer_headers,
        json={"name": name, "version": "1.0"},
    )
    assert viewer_create.status_code == 403

    response = client.post(
        "/os-images",
        headers=auth_headers,
        json={
            "name": name,
            "version": "24.04",
            "edition": "LTS",
            "architecture": "x86_64",
            "checksum": "abc123",
            "approved": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == name
    assert body["version"] == "24.04"
    assert body["approved"] is True
    assert body["created_by"] == "admin"

    try:
        duplicate = client.post(
            "/os-images",
            headers=auth_headers,
            json={"name": name, "version": "24.04"},
        )
        assert duplicate.status_code == 409

        missing_name = client.post(
            "/os-images",
            headers=auth_headers,
            json={"name": "  "},
        )
        assert missing_name.status_code == 400
    finally:
        db_execute(
            db_conn,
            "DELETE FROM os_images WHERE name LIKE %s",
            ("qa-img-%",),
        )


def test_os_image_crud_roundtrip(client, auth_headers, db_conn):
    name = _unique_name()

    created = client.post(
        "/os-images",
        headers=auth_headers,
        json={
            "name": name,
            "version": "22.04",
            "architecture": "x86_64",
        },
    )
    assert created.status_code == 200
    image_id = created.json()["id"]

    try:
        listed = client.get("/os-images", headers=auth_headers)
        assert listed.status_code == 200
        names = [i["name"] for i in listed.json()]
        assert name in names

        updated = client.put(
            f"/os-images/{image_id}",
            headers=auth_headers,
            json={
                "name": f"{name}-v2",
                "version": "22.04.1",
                "edition": "Server",
                "architecture": "arm64",
                "checksum": "deadbeef",
                "checksum_type": "sha256",
                "approved": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == f"{name}-v2"
        assert updated.json()["architecture"] == "arm64"
        assert updated.json()["approved"] is True

        missing = client.put(
            "/os-images/999999",
            headers=auth_headers,
            json={"name": "x", "version": "1"},
        )
        assert missing.status_code == 404

        deleted = client.delete(
            f"/os-images/{image_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        gone = client.delete(
            f"/os-images/{image_id}",
            headers=auth_headers,
        )
        assert gone.status_code == 404
    finally:
        db_execute(
            db_conn,
            "DELETE FROM os_images WHERE name LIKE %s",
            ("qa-img-%",),
        )


def test_verify_checksum_endpoint_unconfigured(client, auth_headers, db_conn):
    name = _unique_name()

    created = client.post(
        "/os-images",
        headers=auth_headers,
        json={
            "name": name,
            "version": "1.0",
            "checksum": "a" * 64,
        },
    )
    assert created.status_code == 200
    image_id = created.json()["id"]

    try:
        response = client.post(
            f"/os-images/{image_id}/verify-checksum",
            headers=auth_headers,
        )
        assert response.status_code == 422
    finally:
        db_execute(
            db_conn,
            "DELETE FROM os_images WHERE name LIKE %s",
            ("qa-img-%",),
        )


def test_verify_image_checksum_service(monkeypatch, tmp_path, db_conn, db_session):
    from app.os_image_model import OSImage
    from app.services.provisioning_service import (
        ProvisioningError,
        verify_image_checksum,
    )

    image_file = tmp_path / "image.iso"
    image_file.write_bytes(b"iso-content" * 256)

    checksum = hashlib.sha256(image_file.read_bytes()).hexdigest()

    (tmp_path / checksum).write_bytes(b"iso-content" * 256)

    image = OSImage(
        name=_unique_name(),
        version="1.0",
        checksum=checksum,
    )

    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    try:
        monkeypatch.setenv("SMARTIT_IMAGE_DIR", str(tmp_path))

        assert verify_image_checksum(image) is True

        image.checksum = "0" * 64
        db_session.commit()

        (tmp_path / ("0" * 64)).write_bytes(b"different-content")

        try:
            verify_image_checksum(image)
            assert False, "expected ProvisioningError"
        except ProvisioningError as exc:
            assert "mismatch" in str(exc)

        monkeypatch.delenv("SMARTIT_IMAGE_DIR")

        try:
            verify_image_checksum(image)
            assert False, "expected ProvisioningError"
        except ProvisioningError as exc:
            assert "SMARTIT_IMAGE_DIR" in str(exc)
    finally:
        db_execute(
            db_conn,
            "DELETE FROM os_images WHERE name LIKE %s",
            ("qa-img-%",),
        )