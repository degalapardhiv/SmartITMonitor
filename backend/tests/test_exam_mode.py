def test_get_exam_mode_returns_policy(client, auth_headers):
    response = client.get("/exam-mode", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "enabled" in body
    assert "usb_policy" in body
    assert body["usb_policy"] in ("approval_required", "allow", "block")


def test_update_exam_mode(client, auth_headers, restore_exam_mode):
    original = restore_exam_mode
    new_policy = "block" if original["usb_policy"] != "block" else "allow"
    response = client.put(
        "/exam-mode",
        headers=auth_headers,
        json={"enabled": True, "usb_policy": new_policy},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["usb_policy"] == new_policy
    current = client.get("/exam-mode", headers=auth_headers).json()
    assert current["enabled"] is True
    assert current["usb_policy"] == new_policy


def test_update_exam_mode_invalid_policy(client, auth_headers):
    response = client.put(
        "/exam-mode",
        headers=auth_headers,
        json={"enabled": True, "usb_policy": "bogus"},
    )
    assert response.status_code == 400
