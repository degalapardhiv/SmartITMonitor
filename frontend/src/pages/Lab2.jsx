import { useEffect, useMemo, useState } from "react";
import api from "../services/api";

export default function Lab2() {
  const [devices, setDevices] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [labName, setLabName] = useState("Lab 2");
  const [departmentName, setDepartmentName] = useState("CSE");

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

  useEffect(() => {
    loadDevices();

    const protocol =
      window.location.protocol === "https:" ? "wss" : "ws";

    const socket = new WebSocket(
      `${protocol}://${window.location.host}/ws`
    );

    socket.onopen = () => setConnected(true);

    socket.onclose = () => setConnected(false);

    socket.onerror = () => setConnected(false);

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

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
      } catch (err) {
        console.error("Invalid WebSocket message:", err);
      }
    };

    return () => socket.close();
  }, []);

  const labDevices = useMemo(
    () =>
      devices.filter(
        (device) =>
          String(device.department || "").trim().toLowerCase() ===
            departmentName.trim().toLowerCase() &&
          String(device.lab || "").trim().toLowerCase() ===
            labName.trim().toLowerCase()
      ),
    [devices]
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
    <div style={{ padding: "24px" }}>
      <h1>{departmentName} Block — {labName}</h1>

      <div style={{ marginBottom: "20px" }}>
        <strong>Real-Time Connection: </strong>
        {connected ? "🟢 Connected" : "🔴 Disconnected"}
      </div>

      {error && (
        <div style={{ marginBottom: "20px" }}>
          {error}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit,minmax(180px,1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <div>
          <strong>Total Computers</strong>
          <div>{labDevices.length}</div>
        </div>

        <div>
          <strong>Online</strong>
          <div>🟢 {online}</div>
        </div>

        <div>
          <strong>Offline</strong>
          <div>🔴 {offline}</div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fill,minmax(260px,1fr))",
          gap: "16px",
        }}
      >
        {labDevices.map((device) => {
          const status =
            String(device.status || "").toLowerCase();

          const isOnline =
            status === "online" || status === "up";

          return (
            <div
              key={device.id}
              style={{
                border: "1px solid #333",
                borderRadius: "12px",
                padding: "18px",
              }}
            >
              <h3>
                {device.hostname || `PC-${device.id}`}
              </h3>

              <div>
                Status:{" "}
                {isOnline ? "🟢 ONLINE" : "🔴 OFFLINE"}
              </div>

              <div>
                IP: {device.ip || "N/A"}
              </div>

              <hr />

              <div>
                CPU: {safeNumber(device.cpu).toFixed(1)}%
              </div>

              <div>
                RAM: {safeNumber(device.ram).toFixed(1)}%
              </div>

              <div>
                Disk: {safeNumber(device.disk).toFixed(1)}%
              </div>

              <div>
                Last seen:{" "}
                {device.last_seen
                  ? new Date(
                      device.last_seen
                    ).toLocaleString()
                  : "Never"}
              </div>
            </div>
          );
        })}
      </div>

      {!labDevices.length && !error && (
        <p>
          No devices are currently assigned to CSE Block / Lab 2.
        </p>
      )}
    </div>
  );
}
