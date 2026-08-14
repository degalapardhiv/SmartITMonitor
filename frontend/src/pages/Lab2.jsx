import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import useWebSocket, { useSocketStatus } from "../hooks/useWebSocket";

export default function Lab2() {
  const [devices, setDevices] = useState([]);
  const socketStatus = useSocketStatus();
  const [error, setError] = useState("");
  const [labName] = useState("Lab 2");
  const [departmentName] = useState("CSE");

  const loadDevices = async () => {
    try {
      const response = await api.get("/devices");
      const data = response.data;

      setDevices(Array.isArray(data) ? data : []);
      setError("");
    } catch (err) {
      console.error("Lab 2 device loading failed:", err);
      setError(
        err?.response?.status === 401
          ? "Session expired. Please login again."
          : "Unable to load devices"
      );
    }
  };

  useWebSocket((message) => {
    if (!message || !message.type) return;

    if (
      message.type === "device_update" &&
      message.device
    ) {
      setDevices((previous) =>
        previous.map((device) =>
          device.id === message.device.id
            ? { ...device, ...message.device }
            : device
        )
      );
    }

    if (
      message.type === "device_offline" &&
      message.device
    ) {
      setDevices((previous) =>
        previous.map((device) =>
          device.id === message.device.id
            ? {
                ...device,
                ...message.device,
                status: "offline",
              }
            : device
        )
      );
    }

    if (
      message.type === "device_online" &&
      message.device
    ) {
      setDevices((previous) =>
        previous.map((device) =>
          device.id === message.device.id
            ? {
                ...device,
                ...message.device,
                status: "online",
              }
            : device
        )
      );
    }
  });

  useEffect(() => {
    async function sync() {
      await loadDevices();
    }
    sync();
  }, []);

  const connected = socketStatus === "open";

  const labDevices = useMemo(
    () =>
      devices.filter(
        (device) =>
          String(device.department || "").trim().toLowerCase() ===
            departmentName.trim().toLowerCase() &&
          String(device.lab || "").trim().toLowerCase() ===
            labName.trim().toLowerCase()
      ),
    [devices, departmentName, labName]
  );

  const online = labDevices.filter((device) => {
    const status = String(device.status || "").toLowerCase();
    return status === "online" || status === "up";
  }).length;

  const offline = labDevices.length - online;

  const safeNumber = (value) => {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  };

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">{departmentName} Block — {labName}</h1>
          <p className="ui-page-subtitle">Live computer status for this lab.</p>
        </div>
        <span className={`ui-badge ${connected ? "ui-badge-success" : "ui-badge-danger"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-[#46d369]" : "bg-[#e6797e]"}`} />
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 mb-6" style={{ maxWidth: 720 }}>
        <div className="ui-stat">
          <div className="ui-stat-label">Total Computers</div>
          <div className="ui-stat-value mt-1" style={{ color: "var(--ds-text)" }}>{labDevices.length}</div>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Online</div>
          <div className="ui-stat-value mt-1" style={{ color: "var(--ds-success)" }}>{online}</div>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Offline</div>
          <div className="ui-stat-value mt-1" style={{ color: "var(--ds-danger)" }}>{offline}</div>
        </div>
      </div>

      {labDevices.length === 0 && !error ? (
        <div className="ui-empty">
          No devices are currently assigned to CSE Block / Lab 2.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))",
            gap: "16px",
          }}
        >
          {labDevices.map((device) => {
            const status = String(device.status || "").toLowerCase();

            const isOnline = status === "online" || status === "up";

            return (
              <div key={device.id} className="ui-card p-5">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <h3 className="text-lg font-bold text-white">
                    {device.hostname || `PC-${device.id}`}
                  </h3>
                  <span className={`ui-badge ${isOnline ? "ui-badge-success" : "ui-badge-danger"}`}>
                    {isOnline ? "ONLINE" : "OFFLINE"}
                  </span>
                </div>

                <div className="text-sm text-[var(--ds-text-2)]">
                  <p><span className="text-[var(--ds-text-3)]">IP:</span> {device.ip || "N/A"}</p>
                </div>

                <div className="ui-divider" />

                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">CPU</p>
                    <p className="font-semibold text-green-400">{safeNumber(device.cpu).toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">RAM</p>
                    <p className="font-semibold text-yellow-400">{safeNumber(device.ram).toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-[var(--ds-text-3)] font-semibold">Disk</p>
                    <p className="font-semibold text-purple-400">{safeNumber(device.disk).toFixed(1)}%</p>
                  </div>
                </div>

                <div className="text-xs text-[var(--ds-text-3)] mt-3">
                  Last seen:{" "}
                  {device.last_seen ? new Date(device.last_seen).toLocaleString() : "Never"}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
