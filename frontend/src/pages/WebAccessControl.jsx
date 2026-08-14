import { useEffect, useState } from "react";
import {
  FiGlobe,
  FiPlus,
  FiTrash2,
  FiEdit3,
  FiCheck,
  FiX,
  FiRefreshCw,
  FiShield,
  FiShieldOff,
  FiCpu,
  FiActivity,
} from "react-icons/fi";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";

function formatDateTime(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "N/A";
  return date.toLocaleString();
}

function actionBadge(action) {
  if (action === "allowlist") return "ui-badge-success";
  return "ui-badge-danger";
}

function statusBadge(status) {
  const st = String(status || "").toLowerCase();
  if (st === "synced") return "ui-badge-success";
  if (st === "failed") return "ui-badge-danger";
  if (st === "not_applicable") return "ui-badge-neutral";
  return "ui-badge-warning";
}

const TARGET_TYPES = [
  { value: "all", label: "All devices" },
  { value: "department", label: "Department" },
  { value: "lab", label: "Lab" },
  { value: "location", label: "Location" },
  { value: "group", label: "Device group" },
  { value: "device", label: "Specific device" },
];

export default function WebAccessControl() {
  const [policies, setPolicies] = useState([]);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    description: "",
    action: "blocklist",
    enabled: true,
    domains: "",
    include_subdomains: false,
    target_type: "all",
    target_ref: "",
  });
  const [creating, setCreating] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [devices, setDevices] = useState([]);

  const [domainForm, setDomainForm] = useState({
    domains: "",
    include_subdomains: false,
  });
  const [targetForm, setTargetForm] = useState({
    target_type: "all",
    target_ref: "",
  });
  const [busy, setBusy] = useState(null);

  const loadOverview = async () => {
    try {
      const [policiesRes, statsRes, logsRes] = await Promise.all([
        api.get("/web-access/policies"),
        api.get("/web-access/stats"),
        api.get("/web-access/sync-logs", { params: { limit: 50 } }),
      ]);

      setPolicies(policiesRes.data?.policies || []);
      setStats(statsRes.data || null);
      setLogs(logsRes.data?.logs || []);
      setError("");
    } catch (err) {
      console.error("Web access load failed:", err);
      setError(
        err?.response?.status === 401
          ? "Please login again."
          : "Unable to load Web Access Control data."
      );
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id) => {
    try {
      const [policyRes, devicesRes] = await Promise.all([
        api.get(`/web-access/policies/${id}`),
        api.get(`/web-access/policies/${id}/devices`),
      ]);

      setDetail(policyRes.data);
      setDevices(devicesRes.data?.devices || []);
      setError("");
    } catch (err) {
      console.error("Web access detail load failed:", err);
      setError("Unable to load policy details.");
    }
  };

  useEffect(() => {
    async function sync() {
      await loadOverview();
    }
    sync();

    const timer = setInterval(sync, 8000);

    return () => clearInterval(timer);
  }, []);

  useWebSocket((message) => {
    if (!message || message.type !== "web_access_update") return;

    loadOverview();
    if (selectedId) loadDetail(selectedId);
  });

  useEffect(() => {
    if (!selectedId) return;

    async function sync() {
      await loadDetail(selectedId);
    }
    sync();
  }, [selectedId]);

  const selectPolicy = (id) => {
    if (id === selectedId) {
      setSelectedId(null);
      setDetail(null);
      setDevices([]);
      return;
    }
    setSelectedId(id);
    setDetail(null);
    setDevices([]);
  };

  const refreshAll = async (id) => {
    await loadOverview();
    if (id) await loadDetail(id);
  };

  // ----- create policy -----

  const openCreate = () => {
    setCreateForm({
      name: "",
      description: "",
      action: "blocklist",
      enabled: true,
      domains: "",
      include_subdomains: false,
      target_type: "all",
      target_ref: "",
    });
    setCreateOpen(true);
  };

  const submitCreate = async () => {
    if (!createForm.name.trim()) {
      setError("Policy name is required.");
      setTimeout(() => setError(""), 4000);
      return;
    }

    setCreating(true);
    try {
      const domains = createForm.domains
        .split(/[\n,;]+/)
        .map((d) => d.trim())
        .filter(Boolean);

      const targets =
        createForm.target_type === "all"
          ? [{ target_type: "all", target_ref: "" }]
          : createForm.target_ref.trim()
          ? [
              {
                target_type: createForm.target_type,
                target_ref: createForm.target_ref.trim(),
              },
            ]
          : [];

      const response = await api.post("/web-access/policies", {
        name: createForm.name.trim(),
        description: createForm.description.trim(),
        action: createForm.action,
        enabled: createForm.enabled,
        domains,
        include_subdomains: createForm.include_subdomains,
        targets,
      });

      setCreateOpen(false);
      selectPolicy(response.data.id);
      await refreshAll(response.data.id);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create policy.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setCreating(false);
    }
  };

  // ----- toggle enable -----

  const toggleEnabled = async (policy) => {
    setBusy(`toggle-${policy.id}`);
    try {
      await api.put(`/web-access/policies/${policy.id}`, {
        enabled: !policy.enabled,
      });
      await refreshAll(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update policy.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  // ----- delete policy -----

  const deletePolicy = async (policy) => {
    if (!window.confirm(`Delete policy "${policy.name}"? This cannot be undone.`)) {
      return;
    }
    setBusy(`delete-${policy.id}`);
    try {
      await api.delete(`/web-access/policies/${policy.id}`);
      if (selectedId === policy.id) {
        setSelectedId(null);
        setDetail(null);
        setDevices([]);
      }
      await refreshAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete policy.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  // ----- domains -----

  const submitDomains = async () => {
    const domains = domainForm.domains
      .split(/[\n,;]+/)
      .map((d) => d.trim())
      .filter(Boolean);

    if (domains.length === 0) return;

    setBusy("domains");
    try {
      await api.post(`/web-access/policies/${selectedId}/domains`, {
        domains,
        include_subdomains: domainForm.include_subdomains,
      });
      setDomainForm({ domains: "", include_subdomains: false });
      await refreshAll(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to add domains.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  const removeDomain = async (entry) => {
    setBusy(`domain-${entry.id}`);
    try {
      await api.delete(
        `/web-access/policies/${selectedId}/domains/${entry.id}`
      );
      await refreshAll(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to remove domain.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  // ----- targets -----

  const submitTarget = async () => {
    if (targetForm.target_type !== "all" && !targetForm.target_ref.trim()) {
      setError("Target reference is required for this target type.");
      setTimeout(() => setError(""), 4000);
      return;
    }

    setBusy("target");
    try {
      await api.post(`/web-access/policies/${selectedId}/targets`, {
        target_type: targetForm.target_type,
        target_ref: targetForm.target_ref.trim(),
      });
      setTargetForm({ target_type: "all", target_ref: "" });
      await refreshAll(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to add target.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  const removeTarget = async (target) => {
    setBusy(`target-${target.id}`);
    try {
      await api.delete(
        `/web-access/policies/${selectedId}/targets/${target.id}`
      );
      await refreshAll(selectedId);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to remove target.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setBusy(null);
    }
  };

  const targetLabel = (target) => {
    if (target.target_type === "all") return "All devices";
    if (target.target_type === "device") return `Device: ${target.target_ref}`;
    return `${target.target_type}: ${target.target_ref}`;
  };

  const deviceSummary = (policy) => policy?.device_summary || {};
  const summary = stats?.devices || {};

  return (
    <div className="ui-page">
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Web Access Control</h1>
          <p className="ui-page-subtitle">
            Enforce allow/block domain policies across managed devices.
          </p>
        </div>
        <div className="ui-page-actions">
          <span className="ui-badge ui-badge-info">
            {summary.synced || 0}/{summary.total || 0} devices synced
          </span>
          <button className="ui-btn ui-btn-primary ui-btn-sm" onClick={openCreate}>
            <FiPlus /> New Policy
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="ui-card p-4">
          <div className="ui-stat-value">{stats?.total_policies ?? "—"}</div>
          <div className="ui-stat-label">Policies</div>
          <div className="ui-stat-hint">
            {stats?.enabled_policies ?? 0} enabled
          </div>
        </div>
        <div className="ui-card p-4">
          <div className="ui-stat-value">{summary.synced ?? "—"}</div>
          <div className="ui-stat-label">Synced</div>
          <div className="ui-stat-hint">Devices applied</div>
        </div>
        <div className="ui-card p-4">
          <div className="ui-stat-value">{summary.pending ?? "—"}</div>
          <div className="ui-stat-label">Pending</div>
          <div className="ui-stat-hint">Awaiting agent</div>
        </div>
        <div className="ui-card p-4">
          <div className="ui-stat-value">{summary.failed ?? "—"}</div>
          <div className="ui-stat-label">Failed</div>
          <div className="ui-stat-hint">Apply errors</div>
        </div>
      </div>

      {loading ? (
        <div className="ui-loading">
          <span className="ui-spinner" /> Loading policies...
        </div>
      ) : (
        <>
          {/* Policy list */}
          <div className="ui-card mb-6">
            <div className="ui-card-header">
              <h2 className="ui-card-title">Policies</h2>
            </div>
            <div className="ui-table-wrap">
              <table className="ui-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Action</th>
                    <th>Domains</th>
                    <th>Targets</th>
                    <th>Sync</th>
                    <th>Status</th>
                    <th style={{ textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {policies.length === 0 && (
                    <tr>
                      <td colSpan={7} className="text-center text-[var(--ds-text-3)] py-6">
                        No policies yet. Create one to start enforcing web access.
                      </td>
                    </tr>
                  )}
                  {policies.map((policy) => {
                    const ds = deviceSummary(policy);
                    return (
                      <tr
                        key={policy.id}
                        className={selectedId === policy.id ? "ui-row-active" : ""}
                        style={
                          selectedId === policy.id
                            ? { background: "rgba(220,38,38,0.08)" }
                            : undefined
                        }
                      >
                        <td>
                          <div className="font-medium text-white">{policy.name}</div>
                          <div className="text-xs text-[var(--ds-text-3)]">
                            {policy.description || "No description"} · v{policy.version}
                          </div>
                        </td>
                        <td>
                          <span className={`ui-badge ${actionBadge(policy.action)}`}>
                            {policy.action}
                          </span>
                        </td>
                        <td>{policy.domains.length}</td>
                        <td>{policy.targets.length}</td>
                        <td className="whitespace-nowrap">
                          <span className="ui-badge ui-badge-success">{ds.synced}</span>{" "}
                          <span className="ui-badge ui-badge-warning">{ds.pending}</span>{" "}
                          <span className="ui-badge ui-badge-danger">{ds.failed}</span>
                        </td>
                        <td>
                          <span
                            className={`ui-badge ${
                              policy.enabled ? "ui-badge-success" : "ui-badge-neutral"
                            }`}
                          >
                            {policy.enabled ? "Enabled" : "Disabled"}
                          </span>
                        </td>
                        <td>
                          <div className="flex justify-end gap-2">
                            <button
                              className="ui-btn ui-btn-secondary ui-btn-sm"
                              disabled={busy === `toggle-${policy.id}`}
                              onClick={() => toggleEnabled(policy)}
                            >
                              {policy.enabled ? <FiShieldOff /> : <FiShield />}
                              {policy.enabled ? "Disable" : "Enable"}
                            </button>
                            <button
                              className="ui-btn ui-btn-ghost ui-btn-sm"
                              onClick={() => selectPolicy(policy.id)}
                            >
                              <FiEdit3 /> Manage
                            </button>
                            <button
                              className="ui-btn ui-btn-danger ui-btn-sm"
                              disabled={busy === `delete-${policy.id}`}
                              onClick={() => deletePolicy(policy)}
                            >
                              <FiTrash2 />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Detail panel */}
          {selectedId && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
              <div className="xl:col-span-2 space-y-6">
                <div className="ui-card">
                  <div className="ui-card-header">
                    <h2 className="ui-card-title">
                      {detail ? detail.name : "Policy details"}
                    </h2>
                    {detail && detail.id !== selectedId && (
                      <span className="text-sm text-[var(--ds-text-3)]">
                        Loading...
                      </span>
                    )}
                  </div>

                  {detail && (
                    <div className="p-5 space-y-6">
                      {/* Domains */}
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-semibold text-white">
                            Managed Domains ({detail.domains.length})
                          </h3>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-2 mb-3">
                          <input
                            className="ui-input flex-1"
                            placeholder="example.com, blocked.com"
                            value={domainForm.domains}
                            onChange={(e) =>
                              setDomainForm({ ...domainForm, domains: e.target.value })
                            }
                          />
                          <label className="flex items-center gap-2 text-sm text-[var(--ds-text-2)] whitespace-nowrap">
                            <input
                              type="checkbox"
                              checked={domainForm.include_subdomains}
                              onChange={(e) =>
                                setDomainForm({
                                  ...domainForm,
                                  include_subdomains: e.target.checked,
                                })
                              }
                            />
                            Include subdomains
                          </label>
                          <button
                            className="ui-btn ui-btn-primary ui-btn-sm"
                            disabled={busy === "domains"}
                            onClick={submitDomains}
                          >
                            <FiPlus /> Add
                          </button>
                        </div>

                        {detail.domains.length === 0 ? (
                          <div className="ui-empty">
                            <div className="ui-empty-icon">
                              <FiGlobe />
                            </div>
                            <p className="ui-empty-title">No domains yet</p>
                          </div>
                        ) : (
                          <div className="ui-table-wrap">
                            <table className="ui-table">
                              <thead>
                                <tr>
                                  <th>Domain</th>
                                  <th>Subdomains</th>
                                  <th style={{ textAlign: "right" }}></th>
                                </tr>
                              </thead>
                              <tbody>
                                {detail.domains.map((entry) => (
                                  <tr key={entry.id}>
                                    <td className="font-medium text-white">
                                      {entry.domain}
                                    </td>
                                    <td>
                                      {entry.include_subdomains ? (
                                        <span className="ui-badge ui-badge-info">
                                          Yes
                                        </span>
                                      ) : (
                                        <span className="ui-badge ui-badge-neutral">
                                          Exact only
                                        </span>
                                      )}
                                    </td>
                                    <td style={{ textAlign: "right" }}>
                                      <button
                                        className="ui-btn ui-btn-danger ui-btn-sm"
                                        disabled={busy === `domain-${entry.id}`}
                                        onClick={() => removeDomain(entry)}
                                      >
                                        <FiX />
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>

                      {/* Targets */}
                      <div className="border-t border-[var(--ds-border)] pt-5">
                        <h3 className="text-sm font-semibold text-white mb-3">
                          Target Devices ({detail.targets.length})
                        </h3>

                        <div className="flex flex-col sm:flex-row gap-2 mb-3">
                          <select
                            className="ui-input"
                            style={{ width: 180 }}
                            value={targetForm.target_type}
                            onChange={(e) =>
                              setTargetForm({
                                ...targetForm,
                                target_type: e.target.value,
                              })
                            }
                          >
                            {TARGET_TYPES.map((t) => (
                              <option key={t.value} value={t.value}>
                                {t.label}
                              </option>
                            ))}
                          </select>
                          {targetForm.target_type !== "all" && (
                            <input
                              className="ui-input flex-1"
                              placeholder={
                                targetForm.target_type === "device"
                                  ? "hostname or device id"
                                  : targetForm.target_type === "group"
                                  ? "group name"
                                  : "name"
                              }
                              value={targetForm.target_ref}
                              onChange={(e) =>
                                setTargetForm({
                                  ...targetForm,
                                  target_ref: e.target.value,
                                })
                              }
                            />
                          )}
                          <button
                            className="ui-btn ui-btn-primary ui-btn-sm"
                            disabled={busy === "target"}
                            onClick={submitTarget}
                          >
                            <FiPlus /> Add target
                          </button>
                        </div>

                        {detail.targets.length === 0 ? (
                          <div className="ui-empty">
                            <div className="ui-empty-icon">
                              <FiCpu />
                            </div>
                            <p className="ui-empty-title">No targets yet</p>
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-2">
                            {detail.targets.map((target) => (
                              <span
                                key={target.id}
                                className="inline-flex items-center gap-2 rounded-lg border border-[var(--ds-border)] bg-[var(--ds-bg)] px-3 py-1.5 text-sm text-white"
                              >
                                {targetLabel(target)}
                                <button
                                  className="text-[var(--ds-text-3)] hover:text-red-400"
                                  disabled={busy === `target-${target.id}`}
                                  onClick={() => removeTarget(target)}
                                >
                                  <FiX />
                                </button>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Device assignments */}
              <div className="ui-card">
                <div className="ui-card-header">
                  <h2 className="ui-card-title">
                    <FiActivity /> Assigned Devices
                  </h2>
                </div>
                <div className="ui-table-wrap">
                  <table className="ui-table">
                    <thead>
                      <tr>
                        <th>Hostname</th>
                        <th>Status</th>
                        <th>Version</th>
                      </tr>
                    </thead>
                    <tbody>
                      {devices.length === 0 && (
                        <tr>
                          <td colSpan={3} className="text-center text-[var(--ds-text-3)] py-6">
                            {detail && detail.id === selectedId
                              ? "No assigned devices"
                              : "Loading..."}
                          </td>
                        </tr>
                      )}
                      {devices.map((device) => (
                        <tr key={device.id}>
                          <td className="font-medium text-white">
                            {device.hostname || `Device #${device.device_id}`}
                          </td>
                          <td>
                            <span
                              className={`ui-badge ${statusBadge(device.status)}`}
                            >
                              {device.status}
                            </span>
                          </td>
                          <td className="text-[var(--ds-text-2)]">
                            {device.applied_version || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Sync logs */}
          <div className="ui-card">
            <div className="ui-card-header">
              <h2 className="ui-card-title">Recent Activity</h2>
              <button
                className="ui-btn ui-btn-ghost ui-btn-sm"
                onClick={() => loadOverview()}
              >
                <FiRefreshCw /> Refresh
              </button>
            </div>
            <div className="ui-table-wrap">
              <table className="ui-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Policy</th>
                    <th>Device</th>
                    <th>Action</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center text-[var(--ds-text-3)] py-6">
                        No activity recorded yet.
                      </td>
                    </tr>
                  )}
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="whitespace-nowrap text-[var(--ds-text-2)]">
                        {formatDateTime(log.created_at)}
                      </td>
                      <td className="text-[var(--ds-text-2)]">
                        {log.policy_id ? `#${log.policy_id}` : "—"}
                      </td>
                      <td className="text-[var(--ds-text-2)]">
                        {log.hostname || (log.device_id ? `Device #${log.device_id}` : "—")}
                      </td>
                      <td>
                        <span className="ui-badge ui-badge-info">{log.action}</span>
                      </td>
                      <td className="text-[var(--ds-text-2)]">{log.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Create policy modal */}
      {createOpen && (
        <div className="ui-modal-overlay" onClick={() => setCreateOpen(false)}>
          <div className="ui-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ui-modal-header">
              <h3 className="ui-modal-title">New Web Access Policy</h3>
              <button
                className="text-[var(--ds-text-3)] hover:text-white"
                onClick={() => setCreateOpen(false)}
              >
                <FiX />
              </button>
            </div>
            <div className="ui-modal-body">
              <label className="ui-field-label">Name</label>
              <input
                className="ui-input mb-4"
                placeholder="e.g. Social Media Blocklist"
                value={createForm.name}
                onChange={(e) =>
                  setCreateForm({ ...createForm, name: e.target.value })
                }
              />

              <label className="ui-field-label">Description</label>
              <input
                className="ui-input mb-4"
                placeholder="Optional description"
                value={createForm.description}
                onChange={(e) =>
                  setCreateForm({ ...createForm, description: e.target.value })
                }
              />

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="ui-field-label">Action</label>
                  <select
                    className="ui-input"
                    value={createForm.action}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, action: e.target.value })
                    }
                  >
                    <option value="blocklist">Blocklist</option>
                    <option value="allowlist">Allowlist</option>
                  </select>
                </div>
                <div>
                  <label className="ui-field-label">Status</label>
                  <select
                    className="ui-input"
                    value={createForm.enabled ? "enabled" : "disabled"}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        enabled: e.target.value === "enabled",
                      })
                    }
                  >
                    <option value="enabled">Enabled</option>
                    <option value="disabled">Disabled</option>
                  </select>
                </div>
              </div>

              <label className="ui-field-label">
                Domains (comma or newline separated)
              </label>
              <textarea
                className="ui-input mb-2"
                rows={3}
                placeholder="facebook.com&#10;youtube.com&#10;www.example.com"
                value={createForm.domains}
                onChange={(e) =>
                  setCreateForm({ ...createForm, domains: e.target.value })
                }
              />
              <label className="flex items-center gap-2 text-sm text-[var(--ds-text-2)] mb-4">
                <input
                  type="checkbox"
                  checked={createForm.include_subdomains}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      include_subdomains: e.target.checked,
                    })
                  }
                />
                Include subdomains
              </label>

              <label className="ui-field-label">Target</label>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <select
                  className="ui-input"
                  value={createForm.target_type}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      target_type: e.target.value,
                    })
                  }
                >
                  {TARGET_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
                {createForm.target_type !== "all" && (
                  <input
                    className="ui-input"
                    placeholder="reference"
                    value={createForm.target_ref}
                    onChange={(e) =>
                      setCreateForm({
                        ...createForm,
                        target_ref: e.target.value,
                      })
                    }
                  />
                )}
              </div>
            </div>
            <div className="ui-modal-footer">
              <button
                className="ui-btn ui-btn-ghost"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </button>
              <button
                className="ui-btn ui-btn-primary"
                disabled={creating}
                onClick={submitCreate}
              >
                <FiCheck /> {creating ? "Creating..." : "Create Policy"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}