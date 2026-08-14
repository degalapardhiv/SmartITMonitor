import { useCallback, useEffect, useState } from "react";
import {
  FiDownload,
  FiInbox,
  FiRefreshCw,
  FiSettings,
  FiX,
} from "react-icons/fi";
import api from "../services/api";
import { useAuth } from "../context/auth-context";
import useWebSocket from "../hooks/useWebSocket";

const TYPE_STYLES = {
  app_launched: "ui-badge-neutral",
  app_closed: "ui-badge-neutral",
  browser_opened: "ui-badge-info",
  browser_closed: "ui-badge-info",
  url_visited: "ui-badge-accent",
  user_login: "ui-badge-success",
  user_logout: "ui-badge-success",
  usb_connected: "ui-badge-info",
  usb_removed: "ui-badge-info",
  software_installed: "ui-badge-warning",
  software_removed: "ui-badge-warning",
  system_boot: "ui-badge-neutral",
  system_event: "ui-badge-neutral",
  network_connected: "ui-badge-success",
  network_disconnected: "ui-badge-warning",
  security_failed_auth: "ui-badge-danger",
  security_privilege_escalation: "ui-badge-danger",
  security_usb_rejected: "ui-badge-danger",
};

const DEFAULT_TYPE_STYLE = "ui-badge-neutral";

function typeBadge(type) {
  const style = TYPE_STYLES[type] || DEFAULT_TYPE_STYLE;
  return <span className={`ui-badge ${style}`}>{type}</span>;
}

function formatTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function EventDetailsModal({ event, onClose }) {
  if (!event) return null;

  const metadata = event.metadata;

  return (
    <div className="ui-modal-overlay">
      <div className="ui-modal">
        <div className="ui-modal-header">
          <h3 className="ui-modal-title">Event Details</h3>
          <button onClick={onClose} className="ui-btn ui-btn-ghost ui-btn-sm">
            <FiX />
          </button>
        </div>

        <div className="ui-modal-body space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">Time</span>
            <span className="text-[var(--ds-text)] text-right">
              {formatTime(event.timestamp)}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">Device</span>
            <span className="text-[var(--ds-text)] text-right">
              {event.hostname || "-"} (#{event.device_id})
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">User</span>
            <span className="text-[var(--ds-text)] text-right">
              {event.username || "-"}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">Type</span>
            <span className="text-right">{typeBadge(event.event_type)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">Application</span>
            <span className="text-[var(--ds-text)] text-right">
              {event.application || "-"}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">Domain</span>
            <span className="text-[var(--ds-text)] text-right break-all">
              {event.domain || "-"}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-[var(--ds-text-3)]">URL</span>
            <span className="text-[var(--ds-text)] text-right break-all">
              {event.url || "-"}
            </span>
          </div>
          <div>
            <p className="text-[var(--ds-text-3)] mb-1">Description</p>
            <p className="text-[var(--ds-text)] bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-3">
              {event.description || "-"}
            </p>
          </div>
          {metadata && (
            <div>
              <p className="text-[var(--ds-text-3)] mb-1">Metadata</p>
              <pre className="text-xs text-[var(--ds-text)] bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-3 overflow-x-auto">
                {JSON.stringify(metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="ui-modal-footer">
          <button onClick={onClose} className="ui-btn ui-btn-primary w-full">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingsModal({ onClose, onSaved }) {
  const [urlAuditing, setUrlAuditing] = useState(false);
  const [retentionDays, setRetentionDays] = useState(30);
  const [audit, setAudit] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api
      .get("/endpoint-activity/settings")
      .then((res) => {
        setUrlAuditing(res.data.settings.url_auditing);
        setRetentionDays(res.data.settings.retention_days);
        setAudit(res.data.audit || []);
      })
      .catch(() => setError("Failed to load settings"));
  }, []);

  async function handleSave() {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const res = await api.put("/endpoint-activity/settings", {
        url_auditing: urlAuditing,
        retention_days: Number(retentionDays),
      });
      setAudit(res.data.audit || []);
      setMessage("Settings saved");
      onSaved(res.data.settings);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="ui-modal-overlay">
      <div className="ui-modal">
        <div className="ui-modal-header">
          <h3 className="ui-modal-title">Activity Settings</h3>
          <button onClick={onClose} className="ui-btn ui-btn-ghost ui-btn-sm">
            <FiX />
          </button>
        </div>

        <div className="ui-modal-body space-y-4">
          <label className="flex items-center justify-between gap-4 bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-3 cursor-pointer">
            <div>
              <p className="text-[var(--ds-text)] font-semibold">URL Auditing</p>
              <p className="text-sm text-[var(--ds-text-2)]">
                Collect visited URLs and domains from browser history
              </p>
            </div>
            <input
              type="checkbox"
              checked={urlAuditing}
              onChange={(e) => setUrlAuditing(e.target.checked)}
              className="w-5 h-5 accent-[var(--ds-accent)]"
            />
          </label>

          <div>
            <label className="ui-field-label">
              Retention (days)
            </label>
            <input
              type="number"
              min="1"
              max="3650"
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
              className="ui-input"
            />
          </div>
        </div>

        {error && <p className="px-6 text-sm text-[var(--ds-danger)]">{error}</p>}
        {message && (
          <p className="px-6 text-sm text-[var(--ds-success)]">{message}</p>
        )}

        <div className="ui-modal-footer">
          <button
            onClick={handleSave}
            disabled={saving}
            className="ui-btn ui-btn-primary w-full"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>

        {audit.length > 0 && (
          <div className="px-6 pb-6">
            <p className="text-sm text-[var(--ds-text-2)] mb-2 font-semibold">
              Audit Trail
            </p>
            <div className="max-h-48 overflow-y-auto space-y-1.5">
              {audit.map((entry) => (
                <div
                  key={entry.id}
                  className="bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-2.5 text-xs"
                >
                  <span className="text-[var(--ds-accent)] font-semibold">
                    {entry.username}
                  </span>
                  <span className="text-[var(--ds-text-2)]">
                    {" "}· {entry.action}
                  </span>
                  <span className="text-[var(--ds-text-3)]">
                    {" "}· {formatTime(entry.created_at)}
                  </span>
                  {entry.detail && (
                    <p className="text-[var(--ds-text-3)]">{entry.detail}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function EndpointActivity() {
  const { role } = useAuth();
  const isAdmin = String(role || "").toLowerCase() === "admin";

  const [events, setEvents] = useState([]);
  const [devices, setDevices] = useState([]);
  const [types, setTypes] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [eventType, setEventType] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [sort, setSort] = useState("newest");
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);

  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showSettings, setShowSettings] = useState(false);

  function loadOptions() {
    api.get("/endpoint-activity/devices").then((res) => {
      setDevices(res.data.devices || []);
    });

    api.get("/endpoint-activity/types").then((res) => {
      setTypes(res.data.types || []);
    });
  }

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = {
        search,
        device_id: deviceId,
        event_type: eventType,
        from: fromDate,
        to: toDate,
        sort,
        limit,
        offset,
      };

      Object.keys(params).forEach(
        (key) => params[key] === "" && delete params[key]
      );

      const res = await api.get("/endpoint-activity", { params });
      setEvents(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load events");
      setEvents([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [search, deviceId, eventType, fromDate, toDate, sort, limit, offset]);

  useEffect(() => {
    if (!isAdmin) return;

    const timer = setTimeout(() => {
      loadOptions();
      loadEvents();
    }, 0);

    return () => clearTimeout(timer);
  }, [isAdmin, loadEvents]);

  useWebSocket((msg) => {
    if (msg?.type === "endpoint_activity" && msg.event) {
      setEvents((prev) => {
        const next = [msg.event, ...prev.filter((e) => e.id !== msg.event.id)];
        return next.slice(0, 200);
      });
      setTotal((prev) => prev + 1);
    }
  });

  async function handleExport() {
    setError("");

    try {
      const token = localStorage.getItem("token");

      const params = {
        search,
        device_id: deviceId,
        event_type: eventType,
        from: fromDate,
        to: toDate,
      };

      Object.keys(params).forEach(
        (key) => params[key] === "" && delete params[key]
      );

      const res = await fetch(
        `/api/endpoint-activity/export?${new URLSearchParams(params).toString()}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );

      if (!res.ok) {
        throw new Error("Export failed");
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "endpoint-activity.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message || "Export failed");
    }
  }

  function resetFilters() {
    setSearch("");
    setDeviceId("");
    setEventType("");
    setFromDate("");
    setToDate("");
    setOffset(0);
  }

  if (!isAdmin) {
    return (
      <div>
        <div className="ui-card p-10 text-center">
          <h2 className="text-xl font-bold text-white mb-2">
            Endpoint Activity
          </h2>
          <p className="text-[var(--ds-text-2)]">
            Viewing endpoint activity requires administrator access.
          </p>
        </div>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">
            Endpoint Activity
          </h1>
          <p className="ui-page-subtitle">
            Security and usage events reported by managed devices
          </p>
        </div>

        <div className="ui-page-actions">
          <button
            onClick={handleExport}
            className="ui-btn ui-btn-secondary"
          >
            <FiDownload /> Export CSV
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="ui-btn ui-btn-primary"
          >
            <FiSettings /> Settings
          </button>
        </div>
      </div>

      <div className="ui-card mb-5">
        <div className="ui-card-body flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <input
              type="text"
              placeholder="Search device, user, app, URL..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="ui-input"
              style={{ width: 256 }}
            />

            <select
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              className="ui-input"
              style={{ width: 220 }}
            >
              <option value="">All devices</option>
              {devices.map((device) => (
                <option key={device.device_id} value={device.device_id}>
                  {device.hostname || `#${device.device_id}`}
                </option>
              ))}
            </select>

            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="ui-input"
              style={{ width: 200 }}
            >
              <option value="">All event types</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-[var(--ds-text-2)]">From</span>
            <input
              type="datetime-local"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="ui-input text-sm"
              style={{ width: 220 }}
            />

            <span className="text-sm text-[var(--ds-text-2)]">To</span>
            <input
              type="datetime-local"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="ui-input text-sm"
              style={{ width: 220 }}
            />

            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="ui-input"
              style={{ width: 160 }}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>

            <button
              onClick={resetFilters}
              className="ui-btn ui-btn-ghost ui-btn-sm"
            >
              <FiRefreshCw /> Reset
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="ui-table-wrap">
        <div className="p-6 border-b border-[var(--ds-border)] flex items-center justify-between gap-3">
          <h2 className="ui-card-title">Activity Events</h2>
          <span className="ui-badge ui-badge-neutral">{total} total</span>
        </div>

        <table className="ui-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Device</th>
              <th>User</th>
              <th>Type</th>
              <th>Application / Domain</th>
              <th>Description</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="text-center py-10 text-[var(--ds-text-3)]">
                  <span className="ui-spinner" /> Loading events...
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan="7">
                  <div className="ui-empty">
                    <div className="ui-empty-icon"><FiInbox /></div>
                    <p className="ui-empty-title">No activity events found</p>
                    <p className="text-sm">Agents report events automatically.</p>
                  </div>
                </td>
              </tr>
            ) : (
              events.map((event) => (
                <tr key={event.id || event.timestamp}>
                  <td className="text-[var(--ds-text-2)] whitespace-nowrap">
                    {formatTime(event.timestamp)}
                  </td>
                  <td className="text-[var(--ds-text)] font-medium">
                    {event.hostname || `#${event.device_id}`}
                  </td>
                  <td className="text-[var(--ds-text-2)]">
                    {event.username || "-"}
                  </td>
                  <td className="whitespace-nowrap">
                    {typeBadge(event.event_type)}
                  </td>
                  <td className="text-[var(--ds-text-2)]">
                    {event.application || "-"}
                    {event.domain && (
                      <span className="text-[var(--ds-text-3)] block text-xs">
                        {event.domain}
                      </span>
                    )}
                  </td>
                  <td className="text-[var(--ds-text-2)] max-w-xs truncate">
                    {event.description || "-"}
                  </td>
                  <td>
                    <button
                      onClick={() => setSelectedEvent(event)}
                      className="ui-btn ui-btn-secondary ui-btn-sm"
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        <div className="flex items-center justify-between px-5 py-4 border-t border-[var(--ds-border)]">
          <p className="text-sm text-[var(--ds-text-2)]">
            {total} events · page {currentPage} of {totalPages}
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={offset === 0}
              className="ui-btn ui-btn-secondary ui-btn-sm"
            >
              Previous
            </button>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={offset + limit >= total}
              className="ui-btn ui-btn-secondary ui-btn-sm"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {selectedEvent && (
        <EventDetailsModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onSaved={() => loadEvents()}
        />
      )}
    </div>
  );
}
