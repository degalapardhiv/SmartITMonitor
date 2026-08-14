import hashlib
import uuid

from conftest import db_execute


def _unique(prefix="qa-sw"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _file_bytes(name="agent-setup.exe"):
    return f"qa-installer-{uuid.uuid4().hex}".encode()


def _create_package(client, auth_headers, data=None, bytes_=None):
    name = _unique("qa-pkg")
    version = "1.2.3"
    payload = {
        "name": name,
        "version": version,
        "publisher": "QA Corp",
        "os": "windows",
        "architecture": "x64",
        "install_command": "setup.exe /S",
        "uninstall_command": "setup.exe /uninstall",
        "verify_command": "setup.exe --version",
        "notes": "created by tests",
        **(data or {}),
    }
    file_bytes = bytes_ if bytes_ is not None else _file_bytes()
    response = client.post(
        "/software/packages",
        headers=auth_headers,
        data=payload,
        files={"file": ("agent-setup.exe", file_bytes, "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checksum"] == hashlib.sha256(file_bytes).hexdigest()
    return body, file_bytes


def _cleanup_package(client, auth_headers, db_conn, package_id):
    db_execute(
        db_conn,
        "DELETE FROM software_deployments WHERE package_id = %s",
        (package_id,),
    )
    client.delete(
        f"/software/packages/{package_id}",
        headers=auth_headers,
    )


def _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64", token=True):
    from app.models import Device

    device = Device(
        hostname=_unique("qa-sw-dev"),
        ip="10.9.9.10",
        status="online",
        department="IT",
        lab="Lab-1",
        location="Building A",
        os=os,
        architecture=arch,
        agent_token=uuid.uuid4().hex[:32] if token else None,
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def _approved_package(client, auth_headers, data=None):
    package, _ = _create_package(client, auth_headers, data=data)
    approve = client.post(
        f"/software/packages/{package['id']}/approve",
        headers=auth_headers,
        json={"approval_status": "approved"},
    )
    assert approve.status_code == 200, approve.text
    return package


def _deploy_to(client, auth_headers, package, device):
    response = client.post(
        "/software/deployments",
        headers=auth_headers,
        json={
            "package_id": package["id"],
            "action": "install",
            "scope": "selected",
            "device_ids": [device.id],
            "confirm": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Auth and RBAC
# ---------------------------------------------------------------------------


def test_software_endpoints_require_auth(client):
    assert client.get("/software/packages").status_code == 401
    assert client.get("/software/groups").status_code == 401
    assert client.get("/software/deployments").status_code == 401
    assert client.get("/software/inventory").status_code == 401


def test_software_admin_only(client, viewer_headers, auth_headers):
    viewer_list = client.get("/software/packages", headers=viewer_headers)
    assert viewer_list.status_code == 403

    viewer_create = client.post(
        "/software/packages",
        headers=viewer_headers,
        data={"name": _unique("qa-pkg"), "version": "1.0"},
        files={"file": ("x.exe", b"x", "application/octet-stream")},
    )
    assert viewer_create.status_code == 403

    viewer_deploy = client.post(
        "/software/deployments",
        headers=viewer_headers,
        json={"package_id": 1, "scope": "all", "confirm": True},
    )
    assert viewer_deploy.status_code == 403


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------


def test_package_create_list_update_delete(client, auth_headers, db_conn):
    package, file_bytes = _create_package(client, auth_headers)
    package_id = package["id"]

    try:
        assert package["approval_status"] == "pending"
        assert package["created_by"] == "admin"
        assert package["file_size"] == len(file_bytes)
        assert package["os"] == "windows"
        assert package["architecture"] == "x64"

        listed = client.get(
            "/software/packages",
            headers=auth_headers,
        )
        assert listed.status_code == 200
        ids = [p["id"] for p in listed.json()["packages"]]
        assert package_id in ids

        pending = client.get(
            "/software/packages?approval=pending",
            headers=auth_headers,
        )
        assert all(p["approval_status"] == "pending" for p in pending.json()["packages"])

        updated = client.put(
            f"/software/packages/{package_id}",
            headers=auth_headers,
            json={"notes": "updated notes", "install_timeout_seconds": 900},
        )
        assert updated.status_code == 200
        assert updated.json()["notes"] == "updated notes"
        assert updated.json()["install_timeout_seconds"] == 900

        missing = client.put(
            "/software/packages/999999",
            headers=auth_headers,
            json={"notes": "x"},
        )
        assert missing.status_code == 404
    finally:
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_package_duplicate_and_validation(client, auth_headers, db_conn):
    package, _ = _create_package(client, auth_headers)
    package_id = package["id"]

    try:
        duplicate = client.post(
            "/software/packages",
            headers=auth_headers,
            data={"name": package["name"], "version": package["version"]},
            files={"file": ("dup.exe", b"dup", "application/octet-stream")},
        )
        assert duplicate.status_code == 409

        bad_os = client.post(
            "/software/packages",
            headers=auth_headers,
            data={"name": _unique("qa-pkg"), "version": "1.0", "os": "solaris"},
            files={"file": ("x.exe", b"x", "application/octet-stream")},
        )
        assert bad_os.status_code == 400

        bad_arch = client.post(
            "/software/packages",
            headers=auth_headers,
            data={"name": _unique("qa-pkg"), "version": "1.0", "architecture": "mips"},
            files={"file": ("x.exe", b"x", "application/octet-stream")},
        )
        assert bad_arch.status_code == 400

        empty = client.post(
            "/software/packages",
            headers=auth_headers,
            data={"name": "  ", "version": "1.0"},
            files={"file": ("x.exe", b"x", "application/octet-stream")},
        )
        assert empty.status_code == 400
    finally:
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_package_approve_reject_flow(client, auth_headers, db_conn):
    package, _ = _create_package(client, auth_headers)
    package_id = package["id"]

    try:
        invalid = client.post(
            f"/software/packages/{package_id}/approve",
            headers=auth_headers,
            json={"approval_status": "maybe"},
        )
        assert invalid.status_code == 400

        missing = client.post(
            "/software/packages/999999/approve",
            headers=auth_headers,
            json={"approval_status": "approved"},
        )
        assert missing.status_code == 404

        approved = client.post(
            f"/software/packages/{package_id}/approve",
            headers=auth_headers,
            json={"approval_status": "approved"},
        )
        assert approved.status_code == 200
        assert approved.json()["approval_status"] == "approved"
        assert approved.json()["approved_by"] == "admin"

        rejected = client.post(
            f"/software/packages/{package_id}/approve",
            headers=auth_headers,
            json={"approval_status": "rejected"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["approval_status"] == "rejected"
    finally:
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_package_download_and_delete(client, auth_headers, db_conn):
    package, file_bytes = _create_package(client, auth_headers)
    package_id = package["id"]

    try:
        downloaded = client.get(
            f"/software/packages/{package_id}/download",
            headers=auth_headers,
        )
        assert downloaded.status_code == 200
        assert downloaded.content == file_bytes

        gone = client.get(
            "/software/packages/999999/download",
            headers=auth_headers,
        )
        assert gone.status_code == 404

        deleted = client.delete(
            f"/software/packages/{package_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        after_delete = client.get(
            f"/software/packages/{package_id}/download",
            headers=auth_headers,
        )
        assert after_delete.status_code == 404
    finally:
        _cleanup_package(client, auth_headers, db_conn, package_id)


# ---------------------------------------------------------------------------
# Device groups
# ---------------------------------------------------------------------------


def test_group_lifecycle(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session)
    group_name = _unique("qa-group")

    try:
        created = client.post(
            "/software/groups",
            headers=auth_headers,
            json={"name": group_name},
        )
        assert created.status_code == 200
        group_id = created.json()["id"]
        assert created.json()["device_count"] == 0

        duplicate = client.post(
            "/software/groups",
            headers=auth_headers,
            json={"name": group_name},
        )
        assert duplicate.status_code == 409

        renamed = client.put(
            f"/software/groups/{group_id}",
            headers=auth_headers,
            json={"name": f"{group_name}-v2"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["name"] == f"{group_name}-v2"

        members = client.post(
            f"/software/groups/{group_id}/members",
            headers=auth_headers,
            json={"device_ids": [device.id]},
        )
        assert members.status_code == 200
        assert members.json()["member_count"] == 1

        listed = client.get("/software/groups", headers=auth_headers)
        group = next(g for g in listed.json()["groups"] if g["id"] == group_id)
        assert group["device_count"] == 1

        member_ids = client.get(
            f"/software/groups/{group_id}/members",
            headers=auth_headers,
        )
        assert member_ids.json()["device_ids"] == [device.id]

        missing = client.get(
            "/software/groups/999999/members",
            headers=auth_headers,
        )
        assert missing.status_code == 404

        deleted = client.delete(
            f"/software/groups/{group_id}",
            headers=auth_headers,
        )
        assert deleted.status_code == 200

        gone = client.delete(
            f"/software/groups/{group_id}",
            headers=auth_headers,
        )
        assert gone.status_code == 404
    finally:
        db_execute(
            db_conn,
            "DELETE FROM device_groups WHERE name LIKE %s",
            (f"{group_name}%",),
        )
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))


def test_group_rename_conflict(client, auth_headers, db_conn):
    name_a = _unique("qa-group")
    name_b = _unique("qa-group")

    a = client.post("/software/groups", headers=auth_headers, json={"name": name_a})
    b = client.post("/software/groups", headers=auth_headers, json={"name": name_b})
    assert a.status_code == 200
    assert b.status_code == 200

    try:
        conflict = client.put(
            f"/software/groups/{a.json()['id']}",
            headers=auth_headers,
            json={"name": name_b},
        )
        assert conflict.status_code == 409
    finally:
        db_execute(
            db_conn,
            "DELETE FROM device_groups WHERE name IN (%s, %s)",
            (name_a, name_b),
        )


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


def test_preview_requires_approved_package(client, auth_headers, db_conn):
    package, _ = _create_package(client, auth_headers)
    package_id = package["id"]

    try:
        unapproved = client.get(
            "/software/preview",
            headers=auth_headers,
            params={"package_id": package_id},
        )
        assert unapproved.status_code == 400

        bad_scope = client.get(
            "/software/preview",
            headers=auth_headers,
            params={"package_id": package_id, "scope": "bogus"},
        )
        assert bad_scope.status_code == 400

        missing = client.get(
            "/software/preview",
            headers=auth_headers,
            params={"package_id": 999999},
        )
        assert missing.status_code == 404
    finally:
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_preview_compatibility_summary(client, auth_headers, db_conn, db_session):
    compatible = _enrolled_device(db_session)
    incompatible = _enrolled_device(
        db_session,
        os="Ubuntu 22.04",
        arch="x86_64",
    )
    offline = _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64")
    offline.last_seen = None
    db_session.commit()

    package = _approved_package(client, auth_headers)
    package_id = package["id"]

    try:
        preview = client.get(
            "/software/preview",
            headers=auth_headers,
            params={
                "package_id": package_id,
                "scope": "selected",
                "device_ids": f"{compatible.id},{incompatible.id},{offline.id}",
            },
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body["summary"]["total"] == 3
        assert body["summary"]["compatible"] == 2
        assert body["summary"]["incompatible"] == 1
        assert body["summary"]["offline"] == 1

        device_entries = {d["hostname"]: d for d in body["devices"]}
        assert device_entries[incompatible.hostname]["compatible"] is False
        assert "OS mismatch" in device_entries[incompatible.hostname]["reason"]

        target_ids = [t["device_id"] for t in body["targets"]]
        assert compatible.id in target_ids
        assert offline.id in target_ids
        assert incompatible.id not in target_ids
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id IN (%s, %s, %s)", (compatible.id, incompatible.id, offline.id))
        _cleanup_package(client, auth_headers, db_conn, package_id)


# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------


def test_deployment_validation(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session)
    package = _approved_package(client, auth_headers)
    package_id = package["id"]

    try:
        no_confirm = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": package_id,
                "scope": "selected",
                "device_ids": [device.id],
                "confirm": False,
            },
        )
        assert no_confirm.status_code == 400

        bad_action = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": package_id,
                "action": "dance",
                "scope": "selected",
                "device_ids": [device.id],
                "confirm": True,
            },
        )
        assert bad_action.status_code == 400

        missing_package = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": 999999,
                "scope": "selected",
                "device_ids": [device.id],
                "confirm": True,
            },
        )
        assert missing_package.status_code == 404

        no_targets = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": package_id,
                "scope": "group",
                "scope_ref": "999999",
                "confirm": True,
            },
        )
        assert no_targets.status_code == 400
        assert "No compatible" in no_targets.json()["detail"]

        bad_group = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": package_id,
                "scope": "group",
                "scope_ref": "not-a-number",
                "confirm": True,
            },
        )
        assert bad_group.status_code == 400
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_deployment_requires_commands(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session)

    no_cmd_package = _approved_package(
        client,
        auth_headers,
        data={"install_command": "", "uninstall_command": ""},
    )
    no_cmd_id = no_cmd_package["id"]

    uninstall_package = _approved_package(
        client,
        auth_headers,
        data={"install_command": "setup.exe /S", "uninstall_command": ""},
    )
    uninstall_id = uninstall_package["id"]

    try:
        install_without_cmd = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": no_cmd_id,
                "scope": "selected",
                "device_ids": [device.id],
                "confirm": True,
            },
        )
        assert install_without_cmd.status_code == 400
        assert "install command" in install_without_cmd.json()["detail"]

        uninstall_without_cmd = client.post(
            "/software/deployments",
            headers=auth_headers,
            json={
                "package_id": uninstall_id,
                "action": "uninstall",
                "scope": "selected",
                "device_ids": [device.id],
                "confirm": True,
            },
        )
        assert uninstall_without_cmd.status_code == 400
        assert "uninstall command" in uninstall_without_cmd.json()["detail"]
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        _cleanup_package(client, auth_headers, db_conn, no_cmd_id)
        _cleanup_package(client, auth_headers, db_conn, uninstall_id)


def test_create_deployment_and_cancel(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session)
    package = _approved_package(client, auth_headers)
    package_id = package["id"]

    try:
        deployment = _deploy_to(client, auth_headers, package, device)
        deployment_id = deployment["id"]
        assert deployment["status"] == "running"
        assert deployment["summary"]["total"] == 1
        assert deployment["summary"]["pending"] == 1

        details = client.get(
            f"/software/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert details.status_code == 200
        assert details.json()["targets"][0]["hostname"] == device.hostname
        assert details.json()["targets"][0]["status"] == "pending"

        listed = client.get("/software/deployments", headers=auth_headers)
        ids = [d["id"] for d in listed.json()["deployments"]]
        assert deployment_id in ids

        events = client.get(
            f"/software/deployments/{deployment_id}/events",
            headers=auth_headers,
        )
        assert events.status_code == 200
        messages = " | ".join(e["message"] for e in events.json()["events"])
        assert "Deployment created by admin" in messages

        cancelled = client.post(
            f"/software/deployments/{deployment_id}/cancel",
            headers=auth_headers,
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["summary"]["cancelled"] == 1

        again = client.post(
            f"/software/deployments/{deployment_id}/cancel",
            headers=auth_headers,
        )
        assert again.status_code == 400

        missing = client.post(
            "/software/deployments/999999/cancel",
            headers=auth_headers,
        )
        assert missing.status_code == 404
    finally:
        db_execute(
            db_conn,
            "DELETE FROM software_deployments WHERE id = %s",
            (deployment_id,),
        )
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_delete_package_blocked_by_active_deployment(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session)
    package = _approved_package(client, auth_headers)
    package_id = package["id"]

    try:
        deployment = _deploy_to(client, auth_headers, package, device)
        deployment_id = deployment["id"]

        blocked = client.delete(
            f"/software/packages/{package_id}",
            headers=auth_headers,
        )
        assert blocked.status_code == 409
        assert "active deployment" in blocked.json()["detail"]
    finally:
        db_execute(
            db_conn,
            "DELETE FROM software_deployments WHERE id = %s",
            (deployment_id,),
        )
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        _cleanup_package(client, auth_headers, db_conn, package_id)


# ---------------------------------------------------------------------------
# Agent flow
# ---------------------------------------------------------------------------


def test_agent_full_install_cycle(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64")
    token = device.agent_token
    package, file_bytes = _create_package(client, auth_headers)
    package_id = package["id"]
    deployment_id = None

    try:
        approved = client.post(
            f"/software/packages/{package_id}/approve",
            headers=auth_headers,
            json={"approval_status": "approved"},
        )
        assert approved.status_code == 200

        deployment = _deploy_to(client, auth_headers, package, device)
        deployment_id = deployment["id"]
        assert deployment["summary"]["pending"] == 1

        info = client.post(
            "/software/agent/device-info",
            headers={"X-Agent-Token": token},
            json={"os": "Windows 10 Pro x64", "architecture": "x64"},
        )
        assert info.status_code == 200

        work = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        assert work.status_code == 200
        jobs = work.json()["jobs"]
        assert len(jobs) == 1
        job = jobs[0]
        assert job["action"] == "install"
        assert job["package"]["name"] == package["name"]
        assert job["package"]["checksum"] == package["checksum"]
        assert job["package"]["install_command"] == "setup.exe /S"
        target_id = job["target_id"]

        no_work = client.get(
            "/software/agent/work",
            headers={"X-Agent-Token": "wrong-token"},
        )
        assert no_work.status_code == 401

        download = client.get(
            f"/software/agent/download/{target_id}",
            headers={"X-Agent-Token": token},
        )
        assert download.status_code == 200
        assert download.content == file_bytes

        downloading = client.post(
            "/software/agent/status",
            headers={"X-Agent-Token": token},
            json={
                "target_id": target_id,
                "status": "downloading",
                "progress": 40,
                "detail": "Downloading package",
            },
        )
        assert downloading.status_code == 200
        assert downloading.json()["status"] == "downloading"

        installing = client.post(
            "/software/agent/status",
            headers={"X-Agent-Token": token},
            json={
                "target_id": target_id,
                "status": "installing",
                "progress": 70,
                "detail": "Running installer",
            },
        )
        assert installing.status_code == 200
        assert installing.json()["progress"] == 70

        bad_status = client.post(
            "/software/agent/status",
            headers={"X-Agent-Token": token},
            json={"target_id": target_id, "status": "dancing"},
        )
        assert bad_status.status_code == 400

        result = client.post(
            "/software/agent/result",
            headers={"X-Agent-Token": token},
            json={
                "target_id": target_id,
                "success": True,
                "version": "1.2.3",
                "detail": "Installed successfully",
            },
        )
        assert result.status_code == 200
        assert result.json()["status"] == "completed"
        assert result.json()["progress"] == 100

        details = client.get(
            f"/software/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert details.json()["status"] == "completed"
        target = details.json()["targets"][0]
        assert target["status"] == "completed"
        assert target["attempt_count"] == 1

        inventory = client.get("/software/inventory", headers=auth_headers)
        items = inventory.json()["items"]
        match = [i for i in items if i["device_id"] == device.id]
        assert len(match) == 1
        assert match[0]["name"] == package["name"]
        assert match[0]["version"] == "1.2.3"

        no_more_work = client.get(
            "/software/agent/work",
            headers={"X-Agent-Token": token},
        )
        assert no_more_work.json()["jobs"] == []
    finally:
        db_execute(db_conn, "DELETE FROM software_inventory WHERE device_id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(
            db_conn,
            "DELETE FROM software_deployments WHERE id = %s",
            (deployment_id,),
        )
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_agent_failure_retry_logic(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64")
    token = device.agent_token
    package = _approved_package(client, auth_headers)
    package_id = package["id"]
    deployment_id = None

    try:
        deployment = _deploy_to(client, auth_headers, package, device)
        deployment_id = deployment["id"]

        work = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        target_id = work.json()["jobs"][0]["target_id"]

        failed = client.post(
            "/software/agent/result",
            headers={"X-Agent-Token": token},
            json={
                "target_id": target_id,
                "success": False,
                "detail": "Installer returned exit code 1",
            },
        )
        assert failed.status_code == 200
        assert failed.json()["status"] == "failed"
        assert failed.json()["attempt_count"] == 1

        target = db_conn.cursor()
        target.execute(
            "SELECT status, next_retry_at, attempt_count FROM software_deployment_targets WHERE id = %s",
            (target_id,),
        )
        row = target.fetchone()
        target.close()
        assert row[0] == "failed"
        assert row[1] is not None
        assert row[2] == 1

        not_yet = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        assert not_yet.json()["jobs"] == []

        retry = db_conn.cursor()
        retry.execute(
            "UPDATE software_deployment_targets SET next_retry_at = now() - interval '1 minute' WHERE id = %s",
            (target_id,),
        )
        retry.close()

        claimed = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        jobs = claimed.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["target_id"] == target_id

        succeed = client.post(
            "/software/agent/result",
            headers={"X-Agent-Token": token},
            json={"target_id": target_id, "success": True},
        )
        assert succeed.status_code == 200
        assert succeed.json()["status"] == "completed"
        assert succeed.json()["attempt_count"] == 2
    finally:
        db_execute(db_conn, "DELETE FROM software_inventory WHERE device_id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(
            db_conn,
            "DELETE FROM software_deployments WHERE id = %s",
            (deployment_id,),
        )
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_agent_max_retries_stops_claiming(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64")
    token = device.agent_token
    package = _approved_package(client, auth_headers)
    package_id = package["id"]
    deployment_id = None

    try:
        deployment = _deploy_to(client, auth_headers, package, device)
        deployment_id = deployment["id"]

        work = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        target_id = work.json()["jobs"][0]["target_id"]

        exhausted = db_conn.cursor()
        exhausted.execute(
            "UPDATE software_deployment_targets SET status = 'failed', attempt_count = 3, next_retry_at = now() - interval '1 minute' WHERE id = %s",
            (target_id,),
        )
        exhausted.close()

        no_job = client.get("/software/agent/work", headers={"X-Agent-Token": token})
        assert no_job.json()["jobs"] == []

        details = client.get(
            f"/software/deployments/{deployment_id}",
            headers=auth_headers,
        )
        assert details.json()["targets"][0]["status"] == "failed"
    finally:
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
        db_execute(
            db_conn,
            "DELETE FROM software_deployments WHERE id = %s",
            (deployment_id,),
        )
        _cleanup_package(client, auth_headers, db_conn, package_id)


def test_agent_inventory_report_and_filter(client, auth_headers, db_conn, db_session):
    device = _enrolled_device(db_session, os="Windows 10 Pro x64", arch="x64")
    token = device.agent_token

    try:
        reported = client.post(
            "/software/agent/inventory",
            headers={"X-Agent-Token": token},
            json={
                "items": [
                    {"name": "Chrome", "version": "126.0", "publisher": "Google"},
                    {"name": "Git", "version": "2.45", "publisher": "Git Foundation"},
                ]
            },
        )
        assert reported.status_code == 200
        assert reported.json()["status"] == "saved"

        resubmit = client.post(
            "/software/agent/inventory",
            headers={"X-Agent-Token": token},
            json={"items": [{"name": "Chrome", "version": "127.0", "publisher": "Google"}]},
        )
        assert resubmit.status_code == 200

        inventory = client.get(
            "/software/inventory",
            headers=auth_headers,
            params={"device_id": device.id},
        )
        assert inventory.status_code == 200
        items = {i["name"]: i for i in inventory.json()["items"]}
        assert items["Chrome"]["version"] == "127.0"
        assert items["Git"]["publisher"] == "Git Foundation"

        searched = client.get(
            "/software/inventory",
            headers=auth_headers,
            params={"search": "chro"},
        )
        names = [i["name"].lower() for i in searched.json()["items"]]
        assert "chrome" in names

        missing_device = client.get(
            "/software/inventory",
            headers={"X-Agent-Token": "bad"},
        )
        assert missing_device.status_code == 401
    finally:
        db_execute(db_conn, "DELETE FROM software_inventory WHERE device_id = %s", (device.id,))
        db_execute(db_conn, "DELETE FROM devices WHERE id = %s", (device.id,))
