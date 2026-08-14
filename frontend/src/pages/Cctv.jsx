import { useEffect, useState } from "react";
import api from "../services/api";
import { useAuth } from "../context/auth-context";

export default function Cctv() {

  const { role } = useAuth();

  const isAdmin = String(role || "").toLowerCase() === "admin";

  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: "",
    ip: "",
    stream_url: "",
    location: "",
  });
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(null);
  const [success, setSuccess] = useState("");

  const loadCameras = async () => {
    try {
      const response = await api.get("/cameras");
      setCameras(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch (err) {
      setError(err?.response?.status === 401 ? "Please login again." : "Unable to load cameras.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(loadCameras, 0);
    const interval = setInterval(loadCameras, 30000);
    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: "", ip: "", stream_url: "", location: "" });
    setError("");
    setShowForm(true);
  };

  const openEdit = (camera) => {
    setEditing(camera);
    setForm({
      name: camera.name,
      ip: camera.ip,
      stream_url: camera.stream_url || "",
      location: camera.location || "",
    });
    setError("");
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      if (editing) {
        await api.put(`/cameras/${editing.id}`, form);
        setSuccess(`Camera "${form.name}" updated.`);
      } else {
        await api.post("/cameras", form);
        setSuccess(`Camera "${form.name}" added.`);
      }
      setShowForm(false);
      loadCameras();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to save camera.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (camera) => {
    if (!window.confirm(`Delete camera "${camera.name}"?`)) return;

    try {
      await api.delete(`/cameras/${camera.id}`);
      setSuccess(`Camera "${camera.name}" deleted.`);
      loadCameras();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete camera.");
    }
  };

  const handleCheck = async (camera) => {
    setChecking(camera.id);
    try {
      await api.post(`/cameras/${camera.id}/check`);
      loadCameras();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to check camera.");
    } finally {
      setChecking(null);
    }
  };

  const statusBadge = (status) => {
    if (status === "online") {
      return <span className="ui-badge ui-badge-success">● Online</span>;
    }
    if (status === "offline") {
      return <span className="ui-badge ui-badge-danger">● Offline</span>;
    }
    return <span className="ui-badge ui-badge-neutral">● Unknown</span>;
  };

  const StreamView = ({ camera }) => {

    const url = camera.stream_url || "";
    const isHttp = url.match(/^https?:\/\//i);
    const isRtsp = url.match(/^rtsp:\/\//i);

    if (camera.status === "online" && isHttp) {
      return (
        <img
          src={url}
          alt={`${camera.name} live stream`}
          className="w-full h-48 object-cover bg-black"
          onError={(e) => {
            e.target.style.display = "none";
            e.target.nextElementSibling.style.display = "flex";
          }}
        />
      );
    }

    return (
      <div className="w-full h-48 bg-black flex flex-col items-center justify-center text-gray-400">
        <svg className="w-10 h-10 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5"
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <p className="text-sm">
          {isRtsp
            ? "RTSP stream — open in VLC:"
            : camera.status === "offline"
              ? "Camera offline"
              : "No HTTP stream configured"}
        </p>
        {isRtsp && (
          <p className="text-xs text-cyan-400 mt-1 px-4 break-all text-center">{url}</p>
        )}
      </div>
    );
  };

  if (loading) {
    return <div className="text-gray-400 p-6">Loading cameras...</div>;
  }

  return (
    <div>

      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">CCTV Cameras</h1>
          <p className="ui-page-subtitle">Camera registry and live streams</p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreate}
            className="ui-btn ui-btn-primary"
          >
            + Add Camera
          </button>
        )}
      </div>

      {success && (
        <div className="mb-4 rounded-lg border border-green-500/30 bg-green-500/10 text-[#46d369] px-4 py-3">
          {success}
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 text-[#e6797e] px-4 py-3">
          {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="ui-card mb-6 p-6 space-y-4"
        >
          <h2 className="ui-card-title">
            {editing ? `Edit Camera: ${editing.name}` : "Add New Camera"}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="ui-field-label">Name *</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Main Entrance"
                className="ui-input"
              />
            </div>

            <div>
              <label className="ui-field-label">IP Address *</label>
              <input
                required
                value={form.ip}
                onChange={(e) => setForm({ ...form, ip: e.target.value })}
                placeholder="e.g. 192.168.1.101"
                className="ui-input"
              />
            </div>

            <div>
              <label className="ui-field-label">Stream URL</label>
              <input
                value={form.stream_url}
                onChange={(e) => setForm({ ...form, stream_url: e.target.value })}
                placeholder="http://ip/video.mjpg or rtsp://ip:554/stream"
                className="ui-input"
              />
            </div>

            <div>
              <label className="ui-field-label">Location</label>
              <input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="e.g. Building A, Ground Floor"
                className="ui-input"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="ui-btn ui-btn-primary"
            >
              {saving ? "Saving..." : editing ? "Save Changes" : "Add Camera"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="ui-btn ui-btn-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {cameras.length === 0 && !showForm && (
        <div className="ui-empty">
          No cameras registered yet.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {cameras.map((camera) => (
          <div
            key={camera.id}
            className="ui-card overflow-hidden"
          >
            <StreamView camera={camera} />

            <div className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">{camera.name}</h3>
                {statusBadge(camera.status)}
              </div>

              <div className="mt-3 space-y-1 text-sm text-[var(--ds-text-2)]">
                <p><span className="text-[var(--ds-text-3)]">IP:</span> {camera.ip}</p>
                {camera.location && (
                  <p><span className="text-[var(--ds-text-3)]">Location:</span> {camera.location}</p>
                )}
                <p>
                  <span className="text-[var(--ds-text-3)]">Last seen:</span>{" "}
                  {camera.last_seen ? new Date(camera.last_seen).toLocaleString() : "Never"}
                </p>
              </div>

              {isAdmin && (
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleCheck(camera)}
                    disabled={checking === camera.id}
                    className="ui-btn ui-btn-secondary ui-btn-sm"
                  >
                    {checking === camera.id ? "Checking..." : "Check Now"}
                  </button>
                  <button
                    onClick={() => openEdit(camera)}
                    className="ui-btn ui-btn-ghost ui-btn-sm"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(camera)}
                    className="ui-btn ui-btn-danger ui-btn-sm"
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}