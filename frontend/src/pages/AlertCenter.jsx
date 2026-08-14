import { useEffect, useState } from "react";
import { FiBell } from "react-icons/fi";

import api from "../services/api";

import useWebSocket from "../hooks/useWebSocket";

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "--";
  return date.toLocaleString();
}

function severityBadge(level) {
  const lvl = String(level || "").toUpperCase();
  if (lvl === "HIGH" || lvl === "CRITICAL") return "ui-badge-danger";
  if (lvl === "MEDIUM" || lvl === "WARNING") return "ui-badge-warning";
  return "ui-badge-success";
}

export default function AlertCenter() {
  const [alerts, setAlerts] = useState([]);
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("ALL");
  const [type, setType] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resolvingId, setResolvingId] = useState(null);

  useWebSocket((message) => {
    if (!message || !message.type) return;

    if (message.type === "alert_resolved" && message.alerts) {
      const ids = new Set(message.alerts.map((a) => a.id));
      setAlerts((prev) =>
        prev.map((a) =>
          ids.has(a.id) && a.status === "OPEN" ? { ...a, status: "RESOLVED" } : a
        )
      );
      return;
    }

    if (message.type !== "alert" || !message.alert) return;

    const alert = message.alert;

    setAlerts((prev) => {
      const exists = prev.some((a) => a.id === alert.id);
      if (exists) {
        return prev.map((a) => (a.id === alert.id ? alert : a));
      }
      return [alert, ...prev];
    });
  });

  async function loadAlerts(currentPage = 1) {
    setLoading(true);
    try {
      const res = await api.get(`/alerts?page=${currentPage}&limit=50`);
      setAlerts(Array.isArray(res.data) ? res.data : []);
      setError("");
    } catch (err) {
      console.error("Load Alerts Error", err);
      setError("Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function sync() {
      await loadAlerts(page);
    }
    sync();
  }, [page]);

  async function resolveAlert(id) {
    setResolvingId(id);
    try {
      await api.patch(`/alerts/${id}/resolve`);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: "RESOLVED" } : a))
      );
    } catch (err) {
      console.error("Resolve Alert Error", err);
      setError("Failed to resolve alert");
      setTimeout(() => setError(""), 4000);
    } finally {
      setResolvingId(null);
    }
  }

  const filteredAlerts = alerts.filter((alert) => {
    const severityMatch =
      severity === "ALL" || String(alert.severity || "").toUpperCase() === severity;

    const typeMatch =
      type === "ALL" || String(alert.alert_type || "").toUpperCase() === type;

    return severityMatch && typeMatch;
  });

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Alert Center</h1>
          <p className="ui-page-subtitle">
            Live alert queue with resolution workflow.
          </p>
        </div>
        <span className="ui-badge ui-badge-warning">
          {alerts.filter((a) => String(a.status || "OPEN").toUpperCase() !== "RESOLVED").length} open
        </span>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-5">
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="ui-input"
          style={{ width: 170 }}
        >
          <option value="ALL">All Severities</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
          <option value="CRITICAL">Critical</option>
        </select>

        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="ui-input"
          style={{ width: 190 }}
        >
          <option value="ALL">All Types</option>
          <option value="CPU">CPU</option>
          <option value="RAM">RAM</option>
          <option value="DISK">Disk</option>
          <option value="USB_PENDING">USB Pending</option>
          <option value="USB_REJECTED">USB Rejected</option>
        </select>
      </div>

      <div className="ui-table-wrap">
        <table className="ui-table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Type</th>
              <th>Value</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Action</th>
              <th>Message</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="8" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading alerts...
                </td>
              </tr>
            ) : filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan="8">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiBell /></div>
                    <p className="ui-empty-title">No alerts found</p>
                    <p className="text-sm">Adjust filters or check back once new alerts arrive.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredAlerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="font-semibold text-white">{alert.hostname}</td>
                  <td>
                    <span className="ui-badge ui-badge-neutral">{alert.alert_type}</span>
                  </td>
                  <td>{alert.value}</td>
                  <td>
                    <span className={`ui-badge ${severityBadge(alert.severity)}`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`ui-badge ${
                        String(alert.status || "").toUpperCase() === "RESOLVED"
                          ? "ui-badge-success"
                          : "ui-badge-warning"
                      }`}
                    >
                      {alert.status || "OPEN"}
                    </span>
                  </td>
                  <td>
                    {String(alert.status || "").toUpperCase() === "RESOLVED" ? (
                      <span className="text-[var(--ds-success)] text-sm font-semibold">Done</span>
                    ) : (
                      <button
                        onClick={() => resolveAlert(alert.id)}
                        disabled={resolvingId === alert.id}
                        className="ui-btn ui-btn-danger ui-btn-sm"
                      >
                        {resolvingId === alert.id ? "Resolving..." : "Resolve"}
                      </button>
                    )}
                  </td>
                  <td className="max-w-[320px] text-[var(--ds-text-2)]">{alert.message}</td>
                  <td className="whitespace-nowrap text-[var(--ds-text-2)]">
                    {formatDateTime(alert.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 mt-6">
        <button
          onClick={() => {
            if (page > 1) {
              setPage(page - 1);
              loadAlerts(page - 1);
            }
          }}
          className="ui-btn ui-btn-secondary ui-btn-sm"
          disabled={page <= 1}
        >
          Previous
        </button>

        <span className="px-4 py-2 text-sm text-[var(--ds-text-2)]">Page {page}</span>

        <button
          onClick={() => {
            setPage(page + 1);
            loadAlerts(page + 1);
          }}
          className="ui-btn ui-btn-primary ui-btn-sm"
        >
          Next
        </button>
      </div>
    </div>
  );
}