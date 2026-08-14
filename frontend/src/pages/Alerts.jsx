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

function severityBadge(severity) {
  const lvl = String(severity || "").toUpperCase();
  if (lvl === "CRITICAL" || lvl === "HIGH") return "ui-badge-danger";
  if (lvl === "MEDIUM" || lvl === "WARNING") return "ui-badge-warning";
  return "ui-badge-neutral";
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  useEffect(() => {
    let active = true;
    let timer = null;

    async function loadAlerts() {
      try {
        const res = await api.get("/alerts");
        if (!active) return;
        setAlerts(Array.isArray(res.data) ? res.data : []);
        setError("");
      } catch (err) {
        console.log(err);
        if (active) setError("Failed to load alerts");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadAlerts();

    timer = setInterval(loadAlerts, 15000);

    return () => {
      active = false;
      if (timer) clearInterval(timer);
    };
  }, []);

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Alerts</h1>
          <p className="ui-page-subtitle">All recorded alert events across endpoints.</p>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="ui-table-wrap">
        <table className="ui-table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Type</th>
              <th>Value</th>
              <th>Message</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading alerts...
                </td>
              </tr>
            ) : alerts.length === 0 ? (
              <tr>
                <td colSpan="7">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiBell /></div>
                    <p className="ui-empty-title">No alerts found</p>
                    <p className="text-sm">Alert events will appear here as they are generated.</p>
                  </div>
                </td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.id}>
                  <td className="font-semibold text-white">
                    {alert.hostname || alert.device_id}
                  </td>
                  <td>
                    <span className="ui-badge ui-badge-neutral">{alert.alert_type || "Unknown"}</span>
                  </td>
                  <td>{alert.value ?? "-"}</td>
                  <td className="text-[var(--ds-text-2)] max-w-[380px]">{alert.message || "-"}</td>
                  <td>
                    <span className={`ui-badge ${severityBadge(alert.severity)}`}>
                      {alert.severity || "-"}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`ui-badge ${
                        String(alert.status || "OPEN").toUpperCase() === "RESOLVED"
                          ? "ui-badge-success"
                          : "ui-badge-warning"
                      }`}
                    >
                      {alert.status || "OPEN"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap text-[var(--ds-text-2)]">
                    {formatDateTime(alert.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}