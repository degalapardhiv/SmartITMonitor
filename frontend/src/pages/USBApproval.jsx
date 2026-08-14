import { useEffect, useState } from "react";
import { FiHardDrive, FiCheck, FiX } from "react-icons/fi";
import api from "../services/api";

function formatDateTime(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  if (isNaN(date.getTime())) return "N/A";
  return date.toLocaleString();
}

function statusBadge(status) {
  const st = String(status || "").toLowerCase();
  if (st === "approved") return "ui-badge-success";
  if (st === "rejected") return "ui-badge-danger";
  return "ui-badge-warning";
}

export default function USBApproval() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deciding, setDeciding] = useState(null);

  const loadRequests = async () => {
    try {
      const response = await api.get("/usb/requests");
      setRequests(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      console.error("USB request loading failed:", err);
      setError(
        err?.response?.status === 401
          ? "Please login again."
          : "Unable to load USB requests."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    async function sync() {
      await loadRequests();
    }
    sync();

    const timer = setInterval(sync, 5000);

    return () => clearInterval(timer);
  }, []);

  const decide = async (id, decision) => {
    setDeciding(id);
    try {
      await api.post(`/usb/requests/${id}/decision`, {
        decision,
      });

      await loadRequests();
    } catch (err) {
      console.error("USB decision failed:", err);
      setError(err?.response?.data?.detail || "Unable to process USB decision.");
      setTimeout(() => setError(""), 4000);
    } finally {
      setDeciding(null);
    }
  };

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">USB Approval Center</h1>
          <p className="ui-page-subtitle">
            Review USB connection requests from authorized managed lab computers.
          </p>
        </div>
        <span className="ui-badge ui-badge-warning">
          {requests.filter((r) => String(r.status || "").toLowerCase() === "pending").length} pending
        </span>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="ui-loading">
          <span className="ui-spinner" /> Loading USB requests...
        </div>
      ) : requests.length === 0 ? (
        <div className="ui-empty">
          <div className="ui-empty-icon"><FiHardDrive /></div>
          <p className="ui-empty-title">No USB requests</p>
          <p className="text-sm">Requests from lab computers will appear here.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {requests.map((request) => (
            <div key={request.id} className="ui-card p-5">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h3 className="text-lg font-bold text-white">
                  USB Request #{request.id}
                </h3>
                <span className={`ui-badge ${statusBadge(request.status)}`}>
                  {request.status}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2 text-sm">
                <div>
                  <span className="text-[var(--ds-text-3)]">Device:</span>{" "}
                  <span className="font-medium text-white">{request.device_id}</span>
                </div>
                <div>
                  <span className="text-[var(--ds-text-3)]">USB ID:</span> {request.usb_id || "N/A"}
                </div>
                <div>
                  <span className="text-[var(--ds-text-3)]">Vendor:</span> {request.vendor || "N/A"}
                </div>
                <div>
                  <span className="text-[var(--ds-text-3)]">Product:</span> {request.product || "N/A"}
                </div>
                <div className="sm:col-span-2">
                  <span className="text-[var(--ds-text-3)]">Description:</span>{" "}
                  <span className="text-[var(--ds-text-2)]">{request.description || "N/A"}</span>
                </div>
                <div>
                  <span className="text-[var(--ds-text-3)]">Requested:</span>{" "}
                  {formatDateTime(request.requested_at)}
                </div>
                {request.reviewed_at && (
                  <div>
                    <span className="text-[var(--ds-text-3)]">Reviewed:</span>{" "}
                    {formatDateTime(request.reviewed_at)}
                  </div>
                )}
                {request.reviewed_by && (
                  <div>
                    <span className="text-[var(--ds-text-3)]">Reviewed by:</span> {request.reviewed_by}
                  </div>
                )}
              </div>

              {String(request.status || "").toLowerCase() === "pending" && (
                <div className="flex gap-3 mt-5 pt-4 border-t border-[var(--ds-border)]">
                  <button
                    className="ui-btn ui-btn-primary ui-btn-sm"
                    disabled={deciding === request.id}
                    onClick={() => decide(request.id, "approved")}
                  >
                    <FiCheck /> Approve
                  </button>

                  <button
                    className="ui-btn ui-btn-danger ui-btn-sm"
                    disabled={deciding === request.id}
                    onClick={() => decide(request.id, "rejected")}
                  >
                    <FiX /> Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}