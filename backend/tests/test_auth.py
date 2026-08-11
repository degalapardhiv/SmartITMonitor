import uuid

import pytest

from conftest import ADMIN_PASSWORD, ADMIN_USERNAME


def test_login_valid_admin_returns_token(client):
    response = client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"


def test_login_wrong_password_returns_401(client):
    response = client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": "wrong-password-123"},
    )
    assert response.status_code == 401


def test_login_unknown_user_returns_401(client):
    response = client.post(
        "/login",
        data={"username": "qa-test-nobody", "password": "whatever-123"},
    )
    assert response.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    response = client.get("/devices")
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/devices",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.fixture()
def viewer_headers(client, db_conn):
    from conftest import db_execute

    username = f"qa_viewer_{uuid.uuid4().hex[:8]}"
    admin_login = client.post(
        "/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    register = client.post(
        "/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"username": username, "password": "ViewerPass123", "role": "viewer"},
    )
    assert register.status_code == 200, register.text

    viewer_login = client.post(
        "/login",
        data={"username": username, "password": "ViewerPass123"},
    )
    assert viewer_login.status_code == 200
    headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}
    yield headers
    db_execute(db_conn, "DELETE FROM users WHERE username = %s", (username,))


def test_viewer_can_read_devices(client, viewer_headers):
    response = client.get("/devices", headers=viewer_headers)
    assert response.status_code == 200


def test_viewer_cannot_create_device(client, viewer_headers):
    response = client.post(
        "/devices",
        headers=viewer_headers,
        json={"hostname": "viewer-x", "ip": "10.0.0.9"},
    )
    assert response.status_code == 403


def test_viewer_cannot_change_exam_mode(client, viewer_headers):
    response = client.put(
        "/exam-mode",
        headers=viewer_headers,
        json={"enabled": False, "usb_policy": "allow"},
    )
    assert response.status_code == 403


def test_viewer_cannot_resolve_alert(client, viewer_headers):
    response = client.patch(
        "/alerts/1/resolve",
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_viewer_cannot_decide_usb(client, viewer_headers):
    response = client.post(
        "/usb/requests/1/decision",
        headers=viewer_headers,
        json={"decision": "approved"},
    )
    assert response.status_code == 403


def test_viewer_cannot_mark_network_managed(client, viewer_headers):
    response = client.post(
        "/network/devices/1/managed",
        headers=viewer_headers,
    )
    assert response.status_code == 403
