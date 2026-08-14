import { useEffect, useState } from "react";
import { FiMessageSquare } from "react-icons/fi";

import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "--";
  return date.toLocaleString();
}

function statusBadge(status) {
  const st = String(status || "").toUpperCase();
  if (st === "SENT" || st === "SUCCESS" || st === "DELIVERED") return "ui-badge-success";
  if (st === "PENDING") return "ui-badge-warning";
  return "ui-badge-danger";
}

export default function NotificationHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useWebSocket((message) => {
    if (message && message.type === "notification") {
      setHistory((prev) => [message, ...prev]);
    }
  });

  async function loadHistory() {
    setLoading(true);
    try {
      const res = await api.get("/alerts/notifications/history");
      setHistory(Array.isArray(res.data) ? res.data : []);
      setError("");
    } catch (err) {
      console.error("Load Notification History Error", err);
      setError("Failed to load notification history");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function sync() {
      await loadHistory();
    }
    sync();
  }, []);

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Notification History</h1>
          <p className="ui-page-subtitle">Notification deliveries across channels.</p>
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
              <th>Alert ID</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Message</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="5" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading notification history...
                </td>
              </tr>
            ) : history.length === 0 ? (
              <tr>
                <td colSpan="5">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiMessageSquare /></div>
                    <p className="ui-empty-title">No notifications yet</p>
                    <p className="text-sm">Notification deliveries will appear here.</p>
                  </div>
                </td>
              </tr>
            ) : (
              history.map((item) => (
                <tr key={item.id}>
                  <td>{item.alert_id}</td>
                  <td>
                    <span className="ui-badge ui-badge-neutral">{item.channel}</span>
                  </td>
                  <td>
                    <span className={`ui-badge ${statusBadge(item.status)}`}>{item.status}</span>
                  </td>
                  <td className="max-w-[360px] text-[var(--ds-text-2)]">{item.message}</td>
                  <td className="whitespace-nowrap text-[var(--ds-text-2)]">
                    {formatDateTime(item.created_at)}
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