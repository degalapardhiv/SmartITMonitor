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
      return <span className="px-3 py-1 rounded-full text-sm font-semibold bg-green-500/20 text-green-400 border border-green-500/40">● Online</span>;
    }
    if (status === "offline") {
      return <span className="px-3 py-1 rounded-full text-sm font-semibold bg-red-500/20 text-red-400 border border-red-500/40">● Offline</span>;
    }
    return <span className="px-3 py-1 rounded-full text-sm font-semibold bg-gray-500/20 text-gray-400 border border-gray-500/40">● Unknown</span>;
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
    <div className="p-6">

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">CCTV Cameras</h1>
          <p className="text-gray-400 mt-1">Camera registry and live streams</p>
        </div>

        {isAdmin && (
          <button
            onClick={openCreate}
            className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold px-5 py-2 rounded-lg transition"
          >
            + Add Camera
          </button>
        )}
      </div>

      {success && (
        <div className="mb-4 bg-green-500/10 border border-green-500/40 text-green-400 px-4 py-3 rounded-lg">
          {success}
        </div>
      )}

      {error && (
        <div className="mb-4 bg-red-500/10 border border-red-500/40 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4"
        >
          <h2 className="text-xl font-bold">
            {editing ? `Edit Camera: ${editing.name}` : "Add New Camera"}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name *</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Main Entrance"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">IP Address *</label>
              <input
                required
                value={form.ip}
                onChange={(e) => setForm({ ...form, ip: e.target.value })}
                placeholder="e.g. 192.168.1.101"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Stream URL</label>
              <input
                value={form.stream_url}
                onChange={(e) => setForm({ ...form, stream_url: e.target.value })}
                placeholder="http://ip/video.mjpg or rtsp://ip:554/stream"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Location</label>
              <input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="e.g. Building A, Ground Floor"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold px-5 py-2 rounded-lg transition disabled:opacity-50"
            >
              {saving ? "Saving..." : editing ? "Save Changes" : "Add Camera"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="bg-slate-600 hover:bg-slate-700 text-white font-semibold px-5 py-2 rounded-lg transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {cameras.length === 0 && !showForm && (
        <div className="text-center text-gray-400 py-16 bg-slate-800/50 border border-slate-700 rounded-xl">
          No cameras registered yet.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {cameras.map((camera) => (
          <div
            key={camera.id}
            className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden"
          >
            <StreamView camera={camera} />

            <div className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold">{camera.name}</h3>
                {statusBadge(camera.status)}
              </div>

              <div className="mt-3 space-y-1 text-sm text-gray-400">
                <p><span className="text-gray-500">IP:</span> {camera.ip}</p>
                {camera.location && (
                  <p><span className="text-gray-500">Location:</span> {camera.location}</p>
                )}
                <p>
                  <span className="text-gray-500">Last seen:</span>{" "}
                  {camera.last_seen ? new Date(camera.last_seen).toLocaleString() : "Never"}
                </p>
              </div>

              {isAdmin && (
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleCheck(camera)}
                    disabled={checking === camera.id}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                  >
                    {checking === camera.id ? "Checking..." : "Check Now"}
                  </button>
                  <button
                    onClick={() => openEdit(camera)}
                    className="bg-yellow-600 hover:bg-yellow-700 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(camera)}
                    className="bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition"
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