import uuid

from conftest import db_execute


def _unique(prefix="qa-wa"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _enrolled_device(
    db_session,
    department="IT",
    lab="Lab-1",
    location="Building A",
):
    from app.models import Device

    device = Device(
        hostname=_unique("qa-wa-dev"),
        ip="10.9.9.11",
        status="online",
        department=department,
        lab=lab,
        location=location,
        os="Windows 10 Pro x64",
        architecture="x64",
        agent_token=uuid.uuid4().hex[:32],
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def _create_policy(client, auth_headers, data=None):
    payload = {
        "name": _unique("qa-pol"),
        "description": "created by tests",
        "action": "blocklist",
        "enabled": True,
        "domains": ["facebook.com"],
        "include_subdomains": True,
        "targets": [{"target_type": "all", "target_ref": ""}],
        **(data or {}),
    }
    response = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Auth and RBAC
# ---------------------------------------------------------------------------


def test_web_access_requires_auth(client):
    assert client.get("/web-access/policies").status_code == 401
    assert client.get("/web-access/stats").status_code == 401
    assert client.get("/web-access/sync-logs").status_code == 401
    assert client.get("/web-access/agent/policy").status_code == 401

    sync = client.post("/web-access/agent/sync-result", json={})
    assert sync.status_code == 401


def test_web_access_admin_only(client, viewer_headers, auth_headers):
    assert client.get("/web-access/policies", headers=viewer_headers).status_code == 403

    viewer_create = client.post(
        "/web-access/policies",
        headers=viewer_headers,
        json={"name": _unique("qa-pol"), "action": "blocklist"},
    )
    assert viewer_create.status_code == 403

    viewer_stats = client.get("/web-access/stats", headers=viewer_headers)
    assert viewer_stats.status_code == 403


# ---------------------------------------------------------------------------
# Policy lifecycle
# ---------------------------------------------------------------------------


def test_policy_lifecycle(client, auth_headers):
    policy = _create_policy(client, auth_headers)
    policy_id = policy["id"]
    other = _create_policy(client, auth_headers)
    other_id = other["id"]

    try:
        assert policy["action"] == "blocklist"
        assert policy["enabled"] is True
        assert policy["version"] == 1
        assert policy["domains"][0]["domain"] == "facebook.com"
        assert policy["domains"][0]["include_subdomains"] is True
        assert policy["targets"][0]["target_type"] == "all"

        duplicate = client.post(
            "/web-access/policies",
            headers=auth_headers,
            json={"name": policy["name"], "action": "blocklist"},
        )
        assert duplicate.status_code == 400
        assert "already exists" in duplicate.json()["detail"]

        listed = client.get("/web-access/policies", headers=auth_headers)
        ids = [p["id"] for p in listed.json()["policies"]]
        assert policy_id in ids

        detail = client.get(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        assert detail.status_code == 200
        assert detail.json()["name"] == policy["name"]

        missing = client.get(
            "/web-access/policies/999999",
            headers=auth_headers,
        )
        assert missing.status_code == 404

        updated = client.put(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
            json={
                "name": f"{policy['name']}-v2",
                "description": "updated",
                "action": "allowlist",
                "enabled": False,
            },
        )
        assert updated.status_code == 200
        body = updated.json()
        assert body["name"] == f"{policy['name']}-v2"
        assert body["action"] == "allowlist"
        assert body["enabled"] is False
        assert body["version"] == 2

        conflict = client.put(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
            json={"name": other["name"]},
        )
        assert conflict.status_code == 400
        assert "already exists" in conflict.json()["detail"]

        deleted = client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        gone = client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        assert gone.status_code == 404
    finally:
        client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        client.delete(
            f"/web-access/policies/{other_id}",
            headers=auth_headers,
        )


def test_policy_validation(client, auth_headers):
    before = len(client.get("/web-access/policies", headers=auth_headers).json()["policies"])

    empty = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={"name": "   ", "action": "blocklist"},
    )
    assert empty.status_code == 400

    bad_action = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={"name": _unique("qa-pol"), "action": "dance"},
    )
    assert bad_action.status_code == 400

    bad_domain = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={
            "name": _unique("qa-pol"),
            "action": "blocklist",
            "domains": ["bad domain"],
        },
    )
    assert bad_domain.status_code == 400

    bad_target_type = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={
            "name": _unique("qa-pol"),
            "action": "blocklist",
            "targets": [{"target_type": "planet", "target_ref": "x"}],
        },
    )
    assert bad_target_type.status_code == 400

    missing_ref = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={
            "name": _unique("qa-pol"),
            "action": "blocklist",
            "targets": [{"target_type": "department", "target_ref": ""}],
        },
    )
    assert missing_ref.status_code == 400

    after = len(client.get("/web-access/policies", headers=auth_headers).json()["policies"])
    assert after == before, "rejected policy must not leave an orphaned row"


def test_policy_target_validation(client, auth_headers):
    before = len(client.get("/web-access/policies", headers=auth_headers).json()["policies"])

    bad_group = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={
            "name": _unique("qa-pol"),
            "action": "blocklist",
            "targets": [{"target_type": "group", "target_ref": _unique("no-group")}],
        },
    )
    assert bad_group.status_code == 400
    assert "group" in bad_group.json()["detail"]

    bad_device = client.post(
        "/web-access/policies",
        headers=auth_headers,
        json={
            "name": _unique("qa-pol"),
            "action": "blocklist",
            "targets": [{"target_type": "device", "target_ref": _unique("no-dev")}],
        },
    )
    assert bad_device.status_code == 400
    assert "device" in bad_device.json()["detail"]

    after = len(client.get("/web-access/policies", headers=auth_headers).json()["policies"])
    assert after == before, "rejected policy must not leave an orphaned row"


# ---------------------------------------------------------------------------
# Domains and targets
# ---------------------------------------------------------------------------


def test_domain_lifecycle(client, auth_headers):
    policy = _create_policy(client, auth_headers, data={"domains": []})
    policy_id = policy["id"]

    try:
        added = client.post(
            f"/web-access/policies/{policy_id}/domains",
            headers=auth_headers,
            json={
                "domains": [
                    "HTTPS://www.Example.com/some/path",
                    "youtube.com",
                ],
                "include_subdomains": False,
            },
        )
        assert added.status_code == 200
        added_names = {d["domain"] for d in added.json()["added"]}
        assert added_names == {"example.com", "youtube.com"}

        duplicate = client.post(
            f"/web-access/policies/{policy_id}/domains",
            headers=auth_headers,
            json={"domains": ["example.com"]},
        )
        assert duplicate.status_code == 400
        assert "No new domains" in duplicate.json()["detail"]

        bad = client.post(
            f"/web-access/policies/{policy_id}/domains",
            headers=auth_headers,
            json={"domains": ["not a domain"]},
        )
        assert bad.status_code == 400

        detail = client.get(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        entry = next(
            d for d in detail.json()["domains"] if d["domain"] == "example.com"
        )
        assert detail.json()["version"] == 2  # create(empty) + 1 add call

        removed = client.delete(
            f"/web-access/policies/{policy_id}/domains/{entry['id']}",
            headers=auth_headers,
        )
        assert removed.status_code == 200

        after = client.get(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        assert after.json()["version"] == 3
        assert all(d["domain"] != "example.com" for d in after.json()["domains"])

        missing = client.delete(
            f"/web-access/policies/{policy_id}/domains/999999",
            headers=auth_headers,
        )
        assert missing.status_code == 404
    finally:
        client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )


def test_target_lifecycle(client, auth_headers, db_session, db_conn):
    device = _enrolled_device(db_session)
    group_name = _unique("qa-wa-group")

    try:
        group = client.post(
            "/software/groups",
            headers=auth_headers,
            json={"name": group_name},
        )
        assert group.status_code == 200
        group_id = group.json()["id"]

        member = client.post(
            f"/software/groups/{group_id}/members",
            headers=auth_headers,
            json={"device_ids": [device.id]},
        )
        assert member.status_code == 200

        policy = _create_policy(
            client,
            auth_headers,
            data={"targets": []},
        )
        policy_id = policy["id"]

        dept_target = client.post(
            f"/web-access/policies/{policy_id}/targets",
            headers=auth_headers,
            json={"target_type": "department", "target_ref": device.department},
        )
        assert dept_target.status_code == 200

        group_target = client.post(
            f"/web-access/policies/{policy_id}/targets",
            headers=auth_headers,
            json={"target_type": "group", "target_ref": group_name},
        )
        assert group_target.status_code == 200

        assigned = client.get(
            f"/web-access/policies/{policy_id}/devices",
            headers=auth_headers,
        )
        hostnames = [d["hostname"] for d in assigned.json()["devices"]]
        assert device.hostname in hostnames
        match = next(d for d in assigned.json()["devices"] if d["hostname"] == device.hostname)
        assert match["status"] == "pending"

        dup_target = client.post(
            f"/web-access/policies/{policy_id}/targets",
            headers=auth_headers,
            json={"target_type": "group", "target_ref": group_name},
        )
        assert dup_target.status_code == 400

        removed = client.delete(
            f"/web-access/policies/{policy_id}/targets/{group_target.json()['id']}",
            headers=auth_headers,
        )
        assert removed.status_code == 200

        missing = client.delete(
            f"/web-access/policies/{policy_id}/targets/999999",
            headers=auth_headers,
        )
        assert missing.status_code == 404
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM device_groups WHERE id = %s", (group_id,))
        client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )


# ---------------------------------------------------------------------------
# Agent flow
# ---------------------------------------------------------------------------


def test_agent_policy_and_sync(client, auth_headers, db_session, db_conn):
    device = _enrolled_device(db_session)
    token = device.agent_token

    try:
        policy = _create_policy(
            client,
            auth_headers,
            data={
                "targets": [{"target_type": "department", "target_ref": device.department}],
                "domains": ["facebook.com", "youtube.com"],
            },
        )
        policy_id = policy["id"]

        disabled = _create_policy(
            client,
            auth_headers,
            data={
                "enabled": False,
                "targets": [{"target_type": "department", "target_ref": device.department}],
            },
        )
        disabled_id = disabled["id"]

        other_dept = _create_policy(
            client,
            auth_headers,
            data={
                "targets": [{"target_type": "department", "target_ref": "Finance"}],
            },
        )
        other_id = other_dept["id"]

        bad_token = client.get(
            "/web-access/agent/policy",
            headers={"X-Agent-Token": "wrong-token"},
        )
        assert bad_token.status_code == 401

        payload = client.get(
            "/web-access/agent/policy",
            headers={"X-Agent-Token": token},
        )
        assert payload.status_code == 200
        body = payload.json()
        assert body["enabled"] is True
        names = {p["name"] for p in body["policies"]}
        assert policy["name"] in names
        assert disabled["name"] not in names
        assert other_dept["name"] not in names

        mine = next(p for p in body["policies"] if p["name"] == policy["name"])
        assert mine["version"] == 1
        assert {d["domain"] for d in mine["domains"]} == {"facebook.com", "youtube.com"}

        sync = client.post(
            "/web-access/agent/sync-result",
            headers={"X-Agent-Token": token},
            json={
                "device_version": 0,
                "applied": [
                    {
                        "policy_id": policy_id,
                        "version": 1,
                        "detail": "Applied via hosts file",
                    }
                ],
                "failed": [],
            },
        )
        assert sync.status_code == 200
        assert sync.json()["summary"][0]["status"] == "synced"

        assigned = client.get(
            f"/web-access/policies/{policy_id}/devices",
            headers=auth_headers,
        )
        match = next(
            d for d in assigned.json()["devices"] if d["hostname"] == device.hostname
        )
        assert match["status"] == "synced"
        assert match["applied_version"] == 1

        fail_sync = client.post(
            "/web-access/agent/sync-result",
            headers={"X-Agent-Token": token},
            json={
                "failed": [
                    {"policy_id": policy_id, "version": 1, "detail": "Permission denied"}
                ]
            },
        )
        assert fail_sync.status_code == 200

        assigned_after = client.get(
            f"/web-access/policies/{policy_id}/devices",
            headers=auth_headers,
        )
        match = next(
            d for d in assigned_after.json()["devices"] if d["hostname"] == device.hostname
        )
        assert match["status"] == "failed"

        logs = client.get(
            "/web-access/sync-logs",
            headers=auth_headers,
            params={"policy_id": policy_id},
        )
        actions = [log["action"] for log in logs.json()["logs"]]
        assert "policy_synced" in actions
        assert "sync_failed" in actions
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        for pid in (policy_id, disabled_id, other_id):
            client.delete(
                f"/web-access/policies/{pid}",
                headers=auth_headers,
            )


def test_stats_reflect_policy_devices(client, auth_headers, db_session, db_conn):
    device = _enrolled_device(db_session)

    try:
        policy = _create_policy(
            client,
            auth_headers,
            data={
                "targets": [{"target_type": "department", "target_ref": device.department}],
            },
        )
        policy_id = policy["id"]

        stats = client.get("/web-access/stats", headers=auth_headers)
        assert stats.status_code == 200
        body = stats.json()
        assert body["total_policies"] >= 1
        assert body["devices"]["total"] >= 1
        assert body["devices"]["pending"] >= 1

        summary = client.get(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )
        assert summary.json()["device_summary"]["pending"] >= 1
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        client.delete(
            f"/web-access/policies/{policy_id}",
            headers=auth_headers,
        )