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