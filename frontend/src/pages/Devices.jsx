import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FiEdit, FiPlus, FiSearch, FiTrash2, FiHardDrive, FiX } from "react-icons/fi";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";
import { useAuth } from "../context/auth-context";
import AddDevice from "../components/devices/AddDevice";

function StatusBadge({ status }) {
  const online = String(status || "").toLowerCase() === "online";

  return (
    <span className={`ui-badge ${online ? "ui-badge-success" : "ui-badge-danger"}`}>
      <span
        className={`w-1.5 h-1.5 rounded-full ${online ? "bg-[#46d369]" : "bg-[#e6797e]"}`}
      />
      {status || "unknown"}
    </span>
  );
}

function Devices() {
  const { role } = useAuth();

  const isAdmin = String(role || "").toLowerCase() === "admin";

  const [devices, setDevices] = useState([]);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editDevice, setEditDevice] = useState(null);
  const [departments, setDepartments] = useState([]);

  const [message, setMessage] = useState("");

  useWebSocket((message) => {
    if (!message || !message.type) return;

    if (message.type === "device_update" && message.device) {
      setDevices((prev) => {
        const exists = prev.find((d) => d.id === message.device.id);

        if (exists) {
          return prev.map((d) =>
            d.id === message.device.id ? { ...d, ...message.device } : d
          );
        }

        return [...prev, message.device];
      });

      return;
    }

    if (message.type === "device_offline" && message.device) {
      setDevices((prev) =>
        prev.map((d) =>
          d.id === message.device.id
            ? { ...d, ...message.device, status: "offline" }
            : d
        )
      );

      return;
    }

    if (message.type === "device_online" && message.device) {
      setDevices((prev) =>
        prev.map((d) =>
          d.id === message.device.id
            ? { ...d, ...message.device, status: "online" }
            : d
        )
      );
    }
  });

  async function loadDevices() {
    try {
      const response = await api.get("/devices");
      setDevices(response.data);
    } catch (err) {
      console.error("Device Load Error", err);
    }
  }

  async function loadDepartments() {
    try {
      const response = await api.get("/departments");
      setDepartments(response.data || []);
    } catch (err) {
      console.error("Departments Load Error", err);
    }
  }

  useEffect(() => {
    async function sync() {
      await loadDevices();
      await loadDepartments();
    }

    sync();
  }, []);

  async function updateDevice() {
    try {
      const payload = {
        hostname: editDevice.hostname,
        ip: editDevice.ip,
        cpu: Number(editDevice.cpu) || 0,
        ram: Number(editDevice.ram) || 0,
        disk: Number(editDevice.disk) || 0,
        status: String(editDevice.status || "offline").toLowerCase(),
        department: editDevice.department || "",
        lab: editDevice.lab || "",
        location: editDevice.location || "",
        os: editDevice.os || "",
      };

      const response = await api.put(`/devices/${editDevice.id}`, payload);

      setDevices(
        devices.map((d) =>
          d.id === response.data.id ? response.data : d
        )
      );

      setEditDevice(null);

      setMessage("Device updated successfully");
      setTimeout(() => setMessage(""), 3000);
    } catch (err) {
      console.error("Update Error", err);
      setMessage("Failed to update device");
      setTimeout(() => setMessage(""), 3000);
    }
  }

  async function deleteDevice(id) {
    if (!confirm("Delete this device?")) return;

    try {
      await api.delete(`/devices/${id}`);

      setMessage("Device deleted successfully");
      setTimeout(() => setMessage(""), 3000);

      setDevices(devices.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Delete Error", err);
      setMessage("Failed to delete device");
      setTimeout(() => setMessage(""), 3000);
    }
  }

  const filtered = devices.filter((device) =>
    device.hostname.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      {message && (
        <div
          className={`mb-5 rounded-lg border p-4 ${
            message.startsWith("Failed")
              ? "bg-red-600/15 border-red-600/40 text-[#e6797e]"
              : "bg-green-500/10 border-green-500/30 text-[#46d369]"
          }`}
        >
          {message}
        </div>
      )}

      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Devices</h1>
          <p className="ui-page-subtitle">
            Monitored endpoints ·{" "}
            <span className="capitalize text-[var(--ds-text-2)]">{role}</span> access
          </p>
        </div>

        {isAdmin && (
          <button className="ui-btn ui-btn-primary" onClick={() => setShowAdd(true)}>
            <FiPlus /> Add Device
          </button>
        )}
      </div>

      <div className="relative mb-6">
        <FiSearch
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-3)]"
          size={16}
        />
        <input
          className="ui-input !pl-9"
          placeholder="Search device..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {showAdd && isAdmin && (
        <div className="mb-6">
          <AddDevice
            onAdded={(device) => {
              setDevices([...devices, device]);
              setShowAdd(false);
            }}
          />
        </div>
      )}

      {editDevice && (
        <div className="ui-modal-overlay" onClick={() => setEditDevice(null)}>
          <div className="ui-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ui-modal-header">
              <h3 className="ui-modal-title">Edit Device</h3>
              <button className="ui-btn ui-btn-ghost ui-btn-sm" onClick={() => setEditDevice(null)}>
                <FiX />
              </button>
            </div>
            <div className="ui-modal-body">
              <label className="ui-field-label">Hostname</label>
              <input
                placeholder="Hostname"
                className="ui-input mb-4"
                value={editDevice.hostname}
                onChange={(e) => setEditDevice({ ...editDevice, hostname: e.target.value })}
              />

              <label className="ui-field-label">IP Address</label>
              <input
                placeholder="IP Address"
                className="ui-input mb-4"
                value={editDevice.ip || ""}
                onChange={(e) => setEditDevice({ ...editDevice, ip: e.target.value })}
              />

              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <label className="ui-field-label">CPU (%)</label>
                  <input
                    placeholder="CPU %"
                    type="number"
                    className="ui-input"
                    value={editDevice.cpu ?? 0}
                    onChange={(e) => setEditDevice({ ...editDevice, cpu: e.target.value })}
                  />
                </div>
                <div>
                  <label className="ui-field-label">RAM (%)</label>
                  <input
                    placeholder="RAM %"
                    type="number"
                    className="ui-input"
                    value={editDevice.ram ?? 0}
                    onChange={(e) => setEditDevice({ ...editDevice, ram: e.target.value })}
                  />
                </div>
                <div>
                  <label className="ui-field-label">Disk (%)</label>
                  <input
                    placeholder="Disk %"
                    type="number"
                    className="ui-input"
                    value={editDevice.disk ?? 0}
                    onChange={(e) => setEditDevice({ ...editDevice, disk: e.target.value })}
                  />
                </div>
              </div>

              <label className="ui-field-label">Status</label>
              <select
                className="ui-input mb-4"
                value={String(editDevice.status || "").toLowerCase()}
                onChange={(e) => setEditDevice({ ...editDevice, status: e.target.value })}
              >
                <option value="online">Online</option>
                <option value="offline">Offline</option>
              </select>

              <label className="ui-field-label">Department</label>
              <input
                placeholder="Department"
                list="departments-list"
                className="ui-input"
                value={editDevice.department || ""}
                onChange={(e) => setEditDevice({ ...editDevice, department: e.target.value })}
              />

              <datalist id="departments-list">
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.name} />
                ))}
              </datalist>
            </div>
            <div className="ui-modal-footer">
              <button className="ui-btn ui-btn-secondary ui-btn-sm" onClick={() => setEditDevice(null)}>
                Cancel
              </button>
              <button className="ui-btn ui-btn-primary ui-btn-sm" onClick={updateDevice}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="ui-empty">
          <div className="ui-empty-icon"><FiHardDrive /></div>
          <p className="ui-empty-title">{devices.length === 0 ? "No devices found" : "No matching devices"}</p>
          <p className="text-sm">
            {devices.length === 0 ? "Refresh or check back once agents connect." : "Try a different search term."}
          </p>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((device) => (
            <div key={device.id} className="ui-card p-6">
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <h2 className="text-xl font-bold text-white leading-tight">
                    {device.hostname}
                  </h2>
                  {device.department && (
                    <p className="text-xs text-[var(--ds-text-3)] mt-1 capitalize">
                      {device.department}
                    </p>
                  )}
                </div>
                <StatusBadge status={device.status} />
              </div>

              <p className="text-sm text-[var(--ds-text-2)]">
                IP: <span className="text-white font-medium">{device.ip}</span>
              </p>

              <p className="text-xs text-[var(--ds-text-3)] mt-2">
                Last Seen:{" "}
                {device.last_seen ? new Date(device.last_seen).toLocaleString() : "Unknown"}
              </p>

              <div className="flex items-center gap-4 mt-4 pt-4 border-t border-[var(--ds-border)]">
                <div className="flex-1">
                  <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">CPU</p>
                  <p className="text-lg font-semibold text-green-400">{device.cpu ?? 0}%</p>
                </div>
                <div className="flex-1">
                  <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">RAM</p>
                  <p className="text-lg font-semibold text-yellow-400">{device.ram ?? 0}%</p>
                </div>
                <div className="flex-1">
                  <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">Disk</p>
                  <p className="text-lg font-semibold text-purple-400">{device.disk ?? 0}%</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3 mt-5">
                <Link
                  to={`/devices/${device.id}`}
                  className="ui-btn ui-btn-secondary ui-btn-sm"
                >
                  Details
                </Link>

                {isAdmin && (
                  <>
                    <button
                      onClick={() => setEditDevice(device)}
                      className="ui-btn ui-btn-ghost ui-btn-sm"
                    >
                      <FiEdit /> Edit
                    </button>

                    <button
                      onClick={() => deleteDevice(device.id)}
                      className="ui-btn ui-btn-danger ui-btn-sm ml-auto"
                    >
                      <FiTrash2 /> Delete
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Devices;