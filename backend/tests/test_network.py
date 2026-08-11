from conftest import AGENT_TOKEN


def test_discovery_requires_agent_token(client):
    response = client.post("/network/discovery", json={"devices": []})
    assert response.status_code == 401


def test_discovery_rejects_invalid_agent_token(client):
    response = client.post(
        "/network/discovery",
        headers={"X-Agent-Token": "not-the-right-token"},
        json={"devices": []},
    )
    assert response.status_code == 401


def test_network_devices_listing_requires_auth(client):
    response = client.get("/network/devices")
    assert response.status_code == 401


def test_discovery_with_valid_token_stores_device(
    client, db_conn, created_network_device
):
    device = created_network_device
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT hostname, mac FROM network_devices WHERE id = %s",
        (device["id"],),
    )
    row = cursor.fetchone()
    cursor.close()
    assert row is not None
    assert row[0] == device["hostname"]
    assert row[1] == device["mac"]


def test_network_summary_returns_totals(client, auth_headers):
    response = client.get("/network/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    for key in ("total", "online", "managed", "unknown"):
        assert key in body
    assert body["total"] == body["managed"] + body["unknown"]
