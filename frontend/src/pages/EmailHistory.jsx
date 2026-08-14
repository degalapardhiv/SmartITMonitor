import { useEffect, useState } from "react";
import { FiMail } from "react-icons/fi";

import api from "../services/api";

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

export default function EmailHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadHistory() {
    setLoading(true);
    try {
      const res = await api.get("/settings/email/history");
      setHistory(res.data || []);
      setError("");
    } catch (err) {
      console.error("Email history load error", err);
      setError("Failed to load email history");
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
          <h1 className="ui-page-title">Email History</h1>
          <p className="ui-page-subtitle">Outbound email records sent by the platform.</p>
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
              <th>Receiver</th>
              <th>Subject</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="4" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading email history...
                </td>
              </tr>
            ) : history.length === 0 ? (
              <tr>
                <td colSpan="4">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiMail /></div>
                    <p className="ui-empty-title">No emails sent yet</p>
                    <p className="text-sm">Outbound email records will appear here.</p>
                  </div>
                </td>
              </tr>
            ) : (
              history.map((item) => (
                <tr key={item.id}>
                  <td className="font-semibold text-white">{item.receiver}</td>
                  <td className="text-[var(--ds-text-2)]">{item.subject}</td>
                  <td>
                    <span className={`ui-badge ${statusBadge(item.status)}`}>{item.status}</span>
                  </td>
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