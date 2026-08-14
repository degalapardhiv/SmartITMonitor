import { useCallback, useEffect, useState } from "react";
import {
  FiAlertOctagon,
  FiDownload,
  FiInfo,
  FiRefreshCw,
  FiSearch,
  FiShield,
  FiX,
} from "react-icons/fi";

import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";

const SEVERITIES = ["CRITICAL", "HIGH", "WARNING", "INFO"];
const STATUSES = [
  "DETECTED",
  "BLOCKED",
  "QUARANTINED",
  "UNDER_REVIEW",
  "ALLOWED",
  "RESTORED",
  "RESOLVED",
];

const ADMIN_ACTIONS = [
  { key: "keep_blocked", label: "Keep Blocked", confirm: "BLOCKED" },
  { key: "quarantine", label: "Quarantine", confirm: "QUARANTINED" },
  { key: "mark_safe", label: "Mark Safe", confirm: "ALLOWED" },
  { key: "restore", label: "Restore", confirm: "RESTORED" },
  { key: "resolve", label: "Resolve", confirm: "RESOLVED" },
];

const CATEGORY_LABELS = {
  trojan: "Trojan",
  ransomware: "Ransomware",
  spyware: "Spyware",
  malware: "Malware",
  malicious_script: "Malicious Script",
  suspicious_file: "Suspicious File",
  pua: "Potentially Unwanted App",
  safe_file: "Safe File",
};

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return date.toLocaleString();
}

function severityBadge(severity) {
  const lvl = String(severity || "").toUpperCase();
  if (lvl === "CRITICAL") return "ui-badge-danger";
  if (lvl === "HIGH") return "ui-badge-accent";
  if (lvl === "WARNING") return "ui-badge-warning";
  return "ui-badge-neutral";
}

function statusBadge(status) {
  const st = String(status || "").toUpperCase();
  if (st === "RESOLVED" || st === "RESTORED" || st === "ALLOWED")
    return "ui-badge-success";
  if (st === "QUARANTINED" || st === "UNDER_REVIEW") return "ui-badge-warning";
  if (st === "BLOCKED") return "ui-badge-accent";
  return "ui-badge-danger";
}

function categoryLabel(category) {
  return CATEGORY_LABELS[String(category || "").toLowerCase()] || category || "--";
}

function stripPath(path) {
  const parts = String(path || "").split(/[\\/]/);
  return parts[parts.length - 1];
}

export default function Threats() {
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [severity, setSeverity] = useState("ALL");
  const [status, setStatus] = useState("ALL");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [searchInput, setSearchInput] = useState("");

  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [note, setNote] = useState("");

  const loadStats = useCallback(async () => {
    try {
      const res = await api.get("/threats/analytics");
      setStats(res.data);
    } catch (err) {
      console.error("Load threat analytics error", err);
    }
  }, []);

  const loadThreats = useCallback(
    async (override = {}) => {
      setLoading(true);
      try {
        const params = {
          limit: 100,
          sort,
        };
        if (severity !== "ALL") params.severity = severity;
        if (status !== "ALL") params.status = status;
        if (search) params.search = search;
        const res = await api.get("/threats", { params: { ...params, ...override } });
        setItems(Array.isArray(res.data.items) ? res.data.items : []);
        setTotal(res.data.total || 0);
        setError("");
      } catch (err) {
        console.error("Load threats error", err);
        setError("Failed to load threats");
      } finally {
        setLoading(false);
      }
    },
    [severity, status, search, sort]
  );

  useWebSocket((message) => {
    if (!message || !message.type) return;

    if (message.type === "threat_detected" && message.threat) {
      setItems((prev) => {
        const exists = prev.some((t) => t.id === message.threat.id);
        if (exists) return prev.map((t) => (t.id === message.threat.id ? message.threat : t));
        return [message.threat, ...prev];
      });
      setTotal((prev) => prev + 1);
      loadStats();
      return;
    }

    if (message.type === "threat_update" && message.threat) {
      const updated = message.threat;
      setItems((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setDetail((prev) => (prev && prev.id === updated.id ? updated : prev));
      loadStats();
    }
  });

  useEffect(() => {
    async function sync() {
      await loadStats();
    }
    sync();
  }, [loadStats]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    async function sync() {
      await loadThreats();
    }
    sync();
  }, [loadThreats]);

  async function openDetail(threat) {
    setSelected(threat);
    setDetail(threat);
    setNote("");
    setDetailLoading(true);
    try {
      const res = await api.get(`/threats/${threat.id}`);
      setDetail(res.data);
    } catch (err) {
      console.error("Load threat detail error", err);
      setError("Failed to load threat detail");
      setTimeout(() => setError(""), 4000);
    } finally {
      setDetailLoading(false);
    }
  }

  async function applyAction(action) {
    if (!detail) return;
    setActionLoading(action.key);
    try {
      const res = await api.post(`/threats/${detail.id}/action`, {
        action: action.key,
        note,
      });
      const updated = res.data || { ...detail, status: action.confirm };
      if (!updated.id) {
        updated.id = detail.id;
        updated.status = action.confirm;
        updated.action_required = false;
      }
      setDetail(updated);
      setItems((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setNote("");
      loadStats();
      loadThreats();
    } catch (err) {
      console.error("Threat action error", err);
      setError(err.response?.data?.detail || "Failed to apply action");
      setTimeout(() => setError(""), 4000);
    } finally {
      setActionLoading(null);
    }
  }

  async function exportCsv() {
    try {
      const params = {};
      if (severity !== "ALL") params.severity = severity;
      if (status !== "ALL") params.status = status;
      if (search) params.search = search;
      const res = await api.get("/threats/export", {
        params,
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `threats-${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export CSV error", err);
      setError("Failed to export threats");
      setTimeout(() => setError(""), 4000);
    }
  }

  const distribution = [...(stats?.by_severity || [])].sort(
    (a, b) => (b.value || 0) - (a.value || 0)
  );
  const distTotal = distribution.reduce((sum, d) => sum + (d.value || 0), 0);

  const statCards = [
    { label: "Active Threats", value: stats?.active ?? "--", hint: "Detected, blocked, quarantined or under review", tone: "danger" },
    { label: "Critical", value: stats?.critical ?? "--", hint: "Active critical severity", tone: "danger" },
    { label: "Under Review", value: stats?.under_review ?? "--", hint: "Awaiting admin decision", tone: "warning" },
    { label: "Quarantined", value: stats?.quarantined ?? "--", hint: "Files isolated from endpoints", tone: "warning" },
    { label: "Devices Affected", value: stats?.devices_affected ?? "--", hint: "Distinct hosts with active threats", tone: "neutral" },
    { label: "Resolved", value: stats?.resolved ?? "--", hint: "Resolved, restored or allowed", tone: "success" },
  ];

  return (
    <div className="ui-page">
      <div className="ui-page-header">
        <div>
          <h1 className="ui-page-title">Threat Protection</h1>
          <p className="ui-page-subtitle">
            Detected malware, quarantined files and pending remediation across all endpoints.
          </p>
        </div>
        <div className="ui-page-actions">
          <button className="ui-btn ui-btn-secondary ui-btn-sm" onClick={exportCsv}>
            <FiDownload /> Export CSV
          </button>
          <button
            className="ui-btn ui-btn-secondary ui-btn-sm"
            onClick={() => {
              loadThreats();
              loadStats();
            }}
          >
            <FiRefreshCw /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-red-600/20 text-[#e6797e] border border-red-600/40 p-4 rounded-lg">
          {error}
        </div>
      )}

      {loading && !stats ? (
        <div className="ui-loading">
          <span className="ui-spinner" />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          {statCards.map((card) => (
            <div className="ui-stat" key={card.label}>
              <div className="ui-stat-label">{card.label}</div>
              <div
                className="ui-stat-value"
                style={{
                  color:
                    card.tone === "danger"
                      ? "var(--ds-danger)"
                      : card.tone === "warning"
                        ? "var(--ds-warning)"
                        : card.tone === "success"
                          ? "var(--ds-success)"
                          : "var(--ds-text)",
                }}
              >
                {card.value}
              </div>
              <div className="ui-stat-hint">{card.hint}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative">
          <FiSearch
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-3)]"
            size={16}
          />
          <input
            className="ui-input !pl-9"
            style={{ width: 260 }}
            placeholder="Search hostname, file or path..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>

        <select className="ui-input" style={{ width: 170 }} value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="ALL">All Severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select className="ui-input" style={{ width: 170 }} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="ALL">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select className="ui-input" style={{ width: 160 }} value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="severity">Most severe</option>
        </select>

        <span className="text-sm text-[var(--ds-text-3)] ml-auto">
          {total} threat{total === 1 ? "" : "s"}
        </span>
      </div>

      <div className="ui-table-wrap">
        <table className="ui-table">
          <thead>
            <tr>
              <th style={{ cursor: "pointer" }} onClick={() => loadThreats()}>Severity</th>
              <th>Hostname</th>
              <th>File</th>
              <th>Category</th>
              <th>Detection</th>
              <th>Status</th>
              <th>Detected</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading threats...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan="7">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiShield /></div>
                    <p className="ui-empty-title">No threats found</p>
                    <p className="text-sm">Adjust the filters or check back later.</p>
                  </div>
                </td>
              </tr>
            ) : (
              items.map((t) => (
                <tr
                  key={t.id}
                  style={{ cursor: "pointer" }}
                  onDoubleClick={() => openDetail(t)}
                >
                  <td>
                    <span
                      className={`ui-badge ${severityBadge(t.severity)}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        openDetail(t);
                      }}
                    >
                      {t.severity || "INFO"}
                    </span>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{t.hostname || "--"}</div>
                    {t.username && (
                      <div className="text-xs text-[var(--ds-text-3)]">{t.username}</div>
                    )}
                  </td>
                  <td>
                    <div style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={t.file_path || ""}>
                      {t.file_name || "--"}
                    </div>
                    <div className="text-xs text-[var(--ds-text-3)]">{stripPath(t.file_path)}</div>
                  </td>
                  <td>{categoryLabel(t.category)}</td>
                  <td>
                    <div>{t.detection_name || "--"}</div>
                    <div className="text-xs text-[var(--ds-text-3)]">{t.detection_source || ""}</div>
                  </td>
                  <td>
                    <span className={`ui-badge ${statusBadge(t.status)}`}>
                      {t.status || "DETECTED"}
                    </span>
                    {t.action_required && (
                      <div className="text-xs text-[var(--ds-warning)] mt-1">Action required</div>
                    )}
                  </td>
                  <td className="whitespace-nowrap">{formatDateTime(t.detected_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="ui-card">
          <div className="ui-card-header">
            <h3 className="ui-card-title">Threats by severity</h3>
          </div>
          <div className="ui-card-body">
            {distribution.length === 0 ? (
              <p className="text-sm text-[var(--ds-text-3)]">No threat data yet.</p>
            ) : (
              distribution.map((d) => {
                const pct = distTotal ? Math.round((d.value / distTotal) * 100) : 0;
                const barColor =
                  String(d.name).toUpperCase() === "CRITICAL"
                    ? "var(--ds-danger)"
                    : String(d.name).toUpperCase() === "HIGH"
                      ? "var(--ds-accent)"
                      : String(d.name).toUpperCase() === "WARNING"
                        ? "var(--ds-warning)"
                        : "var(--ds-text-2)";
                return (
                  <div key={d.name} className="mb-4">
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-[var(--ds-text-2)]">{d.name || "INFO"}</span>
                      <span className="font-semibold">{d.value}</span>
                    </div>
                    <div className="ui-progress">
                      <div className="ui-progress-bar" style={{ width: `${pct}%`, background: barColor }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="ui-card">
          <div className="ui-card-header">
            <h3 className="ui-card-title">Recent critical threats</h3>
          </div>
          <div className="ui-card-body">
            {!stats?.recent_critical?.length ? (
              <p className="text-sm text-[var(--ds-text-3)]">No critical threats detected.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {stats.recent_critical.map((t) => (
                  <button
                    key={t.id}
                    className="ui-btn ui-btn-ghost ui-btn-sm !justify-start text-left"
                    onClick={() => openDetail(t)}
                  >
                    <span className={`ui-badge ${severityBadge(t.severity)}`}>{t.severity}</span>
                    <span className="flex-1" style={{ minWidth: 0 }}>
                      <span className="block truncate">{t.file_name}</span>
                      <span className="block text-xs text-[var(--ds-text-3)] truncate">{t.hostname}</span>
                    </span>
                    <span className="text-xs text-[var(--ds-text-3)] whitespace-nowrap">
                      {formatDateTime(t.detected_at)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {selected && (
        <div className="ui-modal-overlay" onClick={() => setSelected(null)}>
          <div className="ui-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ui-modal-header">
              <h3 className="ui-modal-title">Threat #{selected.id}</h3>
              <button className="ui-btn ui-btn-ghost ui-btn-sm" onClick={() => setSelected(null)}>
                <FiX />
              </button>
            </div>
            <div className="ui-modal-body">
              {detailLoading ? (
                <div className="ui-loading">
                  <span className="ui-spinner" />
                </div>
              ) : detail ? (
                <>
                  <div className="flex flex-wrap items-center gap-2 mb-4">
                    <span className={`ui-badge ${severityBadge(detail.severity)}`}>
                      {detail.severity || "INFO"}
                    </span>
                    <span className={`ui-badge ${statusBadge(detail.status)}`}>
                      {detail.status || "DETECTED"}
                    </span>
                    <span className="ui-badge ui-badge-neutral">{categoryLabel(detail.category)}</span>
                    {detail.action_required && (
                      <span className="ui-badge ui-badge-warning">
                        <FiAlertOctagon /> Action required
                      </span>
                    )}
                  </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm mb-5">
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Hostname</div>
                          <div className="font-semibold">{detail.hostname || "--"}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">User</div>
                          <div>{detail.username || "--"}</div>
                        </div>
                        <div style={{ gridColumn: "1 / -1" }}>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">File path</div>
                          <div className="break-all">{detail.file_path || "--"}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Detection name</div>
                          <div>{detail.detection_name || "--"}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Source</div>
                          <div>{detail.detection_source || detail.source || "--"}</div>
                        </div>
                        <div style={{ gridColumn: "1 / -1" }}>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">File hash</div>
                          <div className="break-all font-mono text-xs">{detail.file_hash || "--"}</div>
                        </div>
                        {detail.quarantine_path && (
                          <div style={{ gridColumn: "1 / -1" }}>
                            <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Quarantine path</div>
                            <div className="break-all">{detail.quarantine_path}</div>
                          </div>
                        )}
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Detected</div>
                          <div>{formatDateTime(detail.detected_at)}</div>
                        </div>
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Reviewed by</div>
                          <div>{detail.reviewed_by || "--"} {detail.reviewed_at ? `(${formatDateTime(detail.reviewed_at)})` : ""}</div>
                        </div>
                        {detail.notes && (
                          <div style={{ gridColumn: "1 / -1" }}>
                            <div className="text-xs uppercase tracking-wide text-[var(--ds-text-3)] mb-0.5">Notes</div>
                            <div className="whitespace-pre-wrap text-[var(--ds-text-2)]">{detail.notes}</div>
                          </div>
                        )}
                      </div>

                      {detail.action_required && (
                        <>
                          <textarea
                            className="ui-input mb-3"
                            rows={2}
                            placeholder="Optional note for the audit log..."
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                          />
                          <div className="flex flex-wrap gap-2 mb-4">
                            {ADMIN_ACTIONS.map((action) => (
                              <button
                                key={action.key}
                                className={`ui-btn ui-btn-sm ${
                                  action.key === "quarantine" || action.key === "keep_blocked"
                                    ? "ui-btn-danger"
                                    : "ui-btn-secondary"
                                }`}
                                disabled={actionLoading !== null}
                                onClick={() => applyAction(action)}
                              >
                                {actionLoading === action.key ? "Applying..." : action.label}
                              </button>
                            ))}
                          </div>
                        </>
                      )}

                      {detail.audit?.length > 0 && (
                        <div className="mt-4">
                          <h4 className="text-sm font-semibold mb-2">Audit trail</h4>
                          <div className="flex flex-col gap-2">
                            {[...detail.audit]
                              .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
                              .map((entry, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-sm">
                                  <FiInfo className="mt-0.5 text-[var(--ds-text-3)]" size={14} />
                                  <div>
                                    <span className="font-medium">{entry.username || "--"}</span>{" "}
                                    <span className="text-[var(--ds-text-2)]">{entry.action || ""}</span>
                                    {entry.detail ? (
                                      <span className="text-[var(--ds-text-3)]"> — {entry.detail}</span>
                                    ) : null}
                                    <div className="text-xs text-[var(--ds-text-3)]">
                                      {formatDateTime(entry.created_at)}
                                    </div>
                                  </div>
                                </div>
                              ))}
                          </div>
                        </div>
                      )}
                </>
              ) : (
                <p className="text-sm text-[var(--ds-text-3)]">No details available.</p>
              )}
            </div>
            <div className="ui-modal-footer">
              <button className="ui-btn ui-btn-secondary ui-btn-sm" onClick={() => setSelected(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}