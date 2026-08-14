import uuid

import pytest

from conftest import AGENT_TOKEN, db_execute


def _label():
    return "qa-threat-%s" % uuid.uuid4().hex[:8]


def _report(client, payload):
    return client.post(
        "/threats/agent/report",
        headers={"X-Agent-Token": AGENT_TOKEN},
        json=payload,
    )


@pytest.fixture()
def clean_threats(db_conn):
    db_execute(
        db_conn,
        "DELETE FROM monitor_settings WHERE key IN %s",
        (
            (
                "endpoint_threat_enabled",
                "threat_scan_policy",
                "threat_quarantine_policy",
                "threat_suspicious_handling",
                "threat_notify_critical",
                "threat_retention_days",
                "threat_scan_interval_seconds",
            ),
        ),
    )
    yield
    db_execute(
        db_conn,
        "DELETE FROM alerts WHERE message LIKE %s",
        ("%qa-threat-%",),
    )
    db_execute(
        db_conn,
        """DELETE FROM endpoint_activity
           WHERE application LIKE 'qa-threat-%%'
           OR description LIKE '%%qa-threat-%%'""",
    )
    db_execute(
        db_conn,
        "DELETE FROM threat_events WHERE file_name LIKE %s",
        ("qa-threat-%",),
    )
    db_execute(
        db_conn,
        "DELETE FROM monitor_settings WHERE key IN %s",
        (
            (
                "endpoint_threat_enabled",
                "threat_scan_policy",
                "threat_quarantine_policy",
                "threat_suspicious_handling",
                "threat_notify_critical",
                "threat_retention_days",
                "threat_scan_interval_seconds",
            ),
        ),
    )


@pytest.fixture()
def threat_settings(client, auth_headers):
    section = client.get(
        "/settings-center", headers=auth_headers
    ).json()["sections"]
    snapshot = next(s for s in section if s["key"] == "endpoint_threat")["values"]
    yield client
    client.put(
        "/settings-center/endpoint_threat",
        headers=auth_headers,
        json={"values": snapshot},
    )


def _set_threat_settings(client, auth_headers, **values):
    key_map = {
        "enabled": "endpoint_threat_enabled",
        "scan_policy": "threat_scan_policy",
        "quarantine_policy": "threat_quarantine_policy",
        "suspicious_handling": "threat_suspicious_handling",
        "notify_critical": "threat_notify_critical",
        "retention_days": "threat_retention_days",
        "scan_interval_seconds": "threat_scan_interval_seconds",
    }

    body = {}
    for name, value in values.items():
        key = key_map.get(name, name)
        body[key] = value

    return client.put(
        "/settings-center/endpoint_threat",
        headers=auth_headers,
        json={"values": body},
    )


# ---------------------------------------------------------------------------
# Report ingestion: auth + validation
# ---------------------------------------------------------------------------


def test_report_requires_agent_token(client):
    response = client.post(
        "/threats/agent/report",
        json={"file_name": "x.exe", "category": "malware"},
    )
    assert response.status_code in (401, 422)


def test_report_invalid_token(client):
    response = client.post(
        "/threats/agent/report",
        headers={"X-Agent-Token": "not-a-real-token"},
        json={"file_name": "x.exe", "category": "malware"},
    )
    assert response.status_code == 401


def test_report_unknown_category(client):
    response = _report(
        client,
        {"file_name": "x.exe", "category": "file:///C:/Windows/system32"},
    )
    assert response.status_code == 400


def test_report_invalid_severity(client):
    response = _report(
        client,
        {"file_name": "x.exe", "category": "malware", "severity": "CRITICAL+"},
    )
    assert response.status_code == 400


def test_agent_config_reflects_policy(
    client, auth_headers, threat_settings, clean_threats
):
    config = client.get(
        "/threats/agent/config", headers={"X-Agent-Token": AGENT_TOKEN}
    )
    assert config.status_code == 200
    body = config.json()
    assert "enabled" in body
    assert "scan_policy" in body
    assert "quarantine_policy" in body
    assert "suspicious_handling" in body
    assert "scan_interval_seconds" in body


# ---------------------------------------------------------------------------
# Policy behaviour
# ---------------------------------------------------------------------------


def test_safe_file_records_allowed(client, auth_headers, clean_threats):
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "/opt/bin/safe-tool",
            "file_hash": label,
            "category": "safe_file",
            "detection_name": "known-good-hash",
            "action": "allowed",
        },
    )
    assert response.status_code == 200, response.text
    threat = response.json()["threat"]

    assert threat["status"] == "ALLOWED"
    assert threat["category"] == "Safe File"
    assert threat["action_required"] is False


def test_suspicious_file_blocked_by_policy(
    client, auth_headers, clean_threats
):
    _set_threat_settings(
        client,
        auth_headers,
        suspicious_handling="block",
    )
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "/tmp/%s.zip" % label,
            "file_hash": label,
            "category": "suspicious_file",
            "detection_name": "heuristic-match",
            "severity": "WARNING",
            "action": "blocked",
        },
    )
    assert response.status_code == 200, response.text
    threat = response.json()["threat"]

    assert threat["status"] == "BLOCKED"
    assert threat["action_required"] is True
    assert threat["severity"] == "WARNING"


def test_suspicious_file_held_for_review(
    client, auth_headers, clean_threats
):
    _set_threat_settings(
        client, auth_headers, suspicious_handling="review"
    )
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "/tmp/%s.ps1" % label,
            "file_hash": label,
            "category": "suspicious_file",
            "detection_name": "heuristic-match",
            "action": "blocked",
        },
    )
    assert response.status_code == 200, response.text
    threat = response.json()["threat"]

    assert threat["status"] == "UNDER_REVIEW"
    assert threat["action_required"] is True


def test_suspicious_file_notify_only(
    client, auth_headers, clean_threats
):
    _set_threat_settings(
        client, auth_headers, suspicious_handling="notify"
    )
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "/tmp/%s.pua" % label,
            "file_hash": label,
            "category": "suspicious_file",
            "detection_name": "heuristic-match",
            "action": "none",
        },
    )
    assert response.status_code == 200, response.text
    threat = response.json()["threat"]

    assert threat["status"] == "DETECTED"
    assert threat["action_required"] is False


def test_confirmed_malware_auto_quarantined(
    client, auth_headers, clean_threats
):
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "C:\\Windows\\Temp\\%s.exe" % label,
            "file_hash": label,
            "category": "malware",
            "detection_name": "malware.gen",
            "severity": "HIGH",
            "action": "block_and_quarantine",
            "quarantine_path": "/quarantine/%s" % label,
            "quarantine_method": "agent_isolated",
        },
    )
    assert response.status_code == 200, response.text
    threat = response.json()["threat"]

    assert threat["status"] == "QUARANTINED"
    assert threat["action_required"] is False
    assert threat["quarantine_method"] == "agent_isolated"
    assert threat["quarantine_path"]
    assert threat["severity"] == "HIGH"


def test_dedup_repeated_report_same_hash(
    client, auth_headers, clean_threats
):
    label = _label()
    payload = {
        "file_name": label,
        "file_path": "/tmp/%s.bin" % label,
        "file_hash": label,
        "category": "trojan",
        "detection_name": "trojan.agent",
        "action": "block",
    }

    first = _report(client, payload)
    assert first.status_code == 200, first.text
    first_id = first.json()["threat"]["id"]

    second = _report(client, payload)
    assert second.status_code == 200, second.text
    assert second.json()["threat"]["id"] == first_id

    listing = client.get(
        "/threats",
        headers=auth_headers,
        params={"search": label},
    ).json()
    assert sum(1 for t in listing["items"] if t["file_name"] == label) == 1


def test_critical_threat_raises_alert(client, db_conn, clean_threats):
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "file_path": "/tmp/evil-%s.dll" % label,
            "file_hash": label,
            "category": "ransomware",
            "detection_name": "ransom.crypt",
            "severity": "CRITICAL",
            "action": "block_and_quarantine",
        },
    )
    assert response.status_code == 200, response.text

    rows = db_execute(
        db_conn,
        "SELECT alert_type, severity FROM alerts WHERE message LIKE %s",
        ("%" + label + "%",),
    )
    assert rows, "no alert created for critical threat"
    assert rows[0][0] == "RANSOMWARE_DETECTED"


# ---------------------------------------------------------------------------
# Admin listing / analytics / review
# ---------------------------------------------------------------------------


def test_list_requires_auth(client):
    response = client.get("/threats")
    assert response.status_code == 401


def test_list_viewer_forbidden(client, viewer_headers):
    response = client.get("/threats", headers=viewer_headers)
    assert response.status_code == 403


def test_list_and_filter_threats(
    client, auth_headers, clean_threats
):
    label = _label()

    _report(client, {"file_name": label, "category": "spyware"})
    _report(client, {"file_name": label + "-b", "category": "safe_file"})

    listing = client.get(
        "/threats",
        headers=auth_headers,
        params={"search": label, "include_allowed": True},
    )
    body = listing.json()
    assert body["total"] >= 2

    active = client.get(
        "/threats",
        headers=auth_headers,
        params={"search": label},
    ).json()
    names = [t["file_name"] for t in active["items"]]
    assert label in names
    assert label + "-b" not in names  # ALLOWED excluded by default


def test_analytics_reports_counts(
    client, auth_headers, clean_threats
):
    label = _label()

    response = _report(
        client,
        {
            "file_name": label,
            "category": "trojan",
            "severity": "CRITICAL",
            "action": "block",
        },
    )
    assert response.status_code == 200

    analytics = client.get(
        "/threats/analytics", headers=auth_headers
    ).json()
    assert analytics["active"] >= 1
    assert analytics["critical"] >= 1
    assert "by_severity" in analytics
    assert "recent_critical" in analytics


def test_admin_review_audited(
    client, auth_headers, clean_threats
):
    label = _label()

    created = _report(
        client,
        {
            "file_name": label,
            "file_path": "/tmp/%s.tmp" % label,
            "file_hash": label,
            "category": "suspicious_file",
            "action": "blocked",
            "severity": "WARNING",
        },
    )
    assert created.status_code == 200, created.text
    threat_id = created.json()["threat"]["id"]

    detail = client.get(
        "/threats/%s" % threat_id, headers=auth_headers
    )
    assert detail.status_code == 200

    decision = client.post(
        "/threats/%s/action" % threat_id,
        headers=auth_headers,
        json={"action": "mark_safe", "note": "false positive"},
    )
    assert decision.status_code == 200, decision.text
    updated = decision.json()

    assert updated["status"] == "ALLOWED"
    assert updated["action_required"] is False
    assert updated["reviewed_by"]
    assert any(
        entry["action"] == "mark_safe"
        for entry in updated["audit"]
    )

    resolved = _report(
        client,
        {
            "file_name": label + "-b",
            "file_path": "/tmp/%s.tmp" % label,
            "file_hash": label,
            "category": "suspicious_file",
            "action": "blocked",
        },
    )
    assert resolved.status_code == 200

    decision = client.post(
        "/threats/%s/action" % resolved.json()["threat"]["id"],
        headers=auth_headers,
        json={"action": "restore", "note": "safe to restore"},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "RESTORED"
    assert decision.json()["quarantine_path"] == ""
    assert any(
        entry["action"] == "restore"
        for entry in decision.json()["audit"]
    )


def test_admin_review_unknown_action(client, auth_headers, clean_threats):
    label = _label()
    created = _report(client, {"file_name": label, "category": "pua"})
    threat_id = created.json()["threat"]["id"]

    response = client.post(
        "/threats/%s/action" % threat_id,
        headers=auth_headers,
        json={"action": "defenestrate"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Abuse / social engineering resistance
# ---------------------------------------------------------------------------


def test_agent_cannot_disable_protection(
    client, auth_headers, viewer_headers, db_conn, clean_threats
):
    label = _label()

    # An agent trying to weaken policy must not be able to reach the
    # admin settings API at all.
    response = client.put(
        "/settings-center/endpoint_threat",
        headers={"X-Agent-Token": AGENT_TOKEN},
        json={"values": {"endpoint_threat_enabled": False}},
    )
    assert response.status_code == 401

    # Non-admin users cannot change threat policy either.
    response = client.put(
        "/settings-center/endpoint_threat",
        headers=viewer_headers,
        json={"values": {"endpoint_threat_enabled": False}},
    )
    assert response.status_code == 403

    # An escalated threat stays visible to admins regardless.
    _report(
        client,
        {
            "file_name": label,
            "category": "trojan",
            "severity": "CRITICAL",
            "action": "block",
        },
    )
    critical = client.get(
        "/threats",
        headers=auth_headers,
        params={"critical_only": True, "search": label},
    ).json()
    assert any(t["file_name"] == label for t in critical["items"])


def test_disable_protection_is_audited(client, auth_headers, clean_threats):
    # Legitimate admin disabling is allowed, but it is visibly audited.
    response = client.put(
        "/settings-center/endpoint_threat",
        headers=auth_headers,
        json={"values": {"endpoint_threat_enabled": False}},
    )
    assert response.status_code == 200, response.text

    now = client.get(
        "/settings-center/audit", headers=auth_headers
    ).json()["items"]
    assert any(
        entry["section"] == "endpoint_threat"
        and entry["key"] == "endpoint_threat_enabled"
        and "false" in str(entry["new_value"]).lower()
        for entry in now
    )

    config = client.get(
        "/threats/agent/config", headers={"X-Agent-Token": AGENT_TOKEN}
    ).json()
    assert config["enabled"] is False

    # Re-enable for other tests.
    client.put(
        "/settings-center/endpoint_threat",
        headers=auth_headers,
        json={"values": {"endpoint_threat_enabled": True}},
    )


def test_invalid_policy_value_rejected(client, auth_headers):
    response = client.put(
        "/settings-center/endpoint_threat",
        headers=auth_headers,
        json={"values": {"threat_quarantine_policy": "maybe"}},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def test_retention_cleanup_removes_old_events(
    client, auth_headers, threat_settings, db_conn, db_session
):
    _set_threat_settings(client, auth_headers, retention_days=1)
    label = _label()

    cursor = db_conn.cursor()
    cursor.execute(
        """
        INSERT INTO threat_events (
            device_id, hostname, file_name, file_path, file_hash,
            category, severity, detection_source, action, status,
            username, source, quarantine_path, quarantine_method,
            escalated, reviewed_by, action_required, notes,
            created_at, detected_at, updated_at
        )
        VALUES (
            1, 'qa-old-host', %s, '', %s, 'Suspicious File',
            'WARNING', 'test', 'blocked', 'BLOCKED', '', '', '',
            '', FALSE, '', FALSE, '',
            NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days',
            NOW()
        )
        """,
        (label, label),
    )
    cursor.close()

    rows = db_execute(
        db_conn,
        "SELECT id FROM threat_events WHERE file_name = %s",
        (label,),
    )
    assert len(rows) == 1, "old event fixture was not inserted"

    from app.threat_service import retention_cleanup

    deleted = retention_cleanup(db_session)

    assert deleted >= 1

    rows = db_execute(
        db_conn,
        "SELECT id FROM threat_events WHERE file_name = %s",
        (label,),
    )
    assert rows == []