import { useEffect, useState } from "react";
import api from "../services/api";

export default function NetworkDiscovery() {
  const [devices, setDevices] = useState([]);
  const [summary, setSummary] = useState({
    total: 0,
    online: 0,
    managed: 0,
    unknown: 0,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    try {
      setError("");

      const [devicesResponse, summaryResponse] =
        await Promise.all([
          api.get("/network/devices"),
          api.get("/network/summary"),
        ]);

      setDevices(devicesResponse.data);
      setSummary(summaryResponse.data);
    } catch (err) {
      console.error(err);
      setError("Unable to load network devices.");
    } finally {
      setLoading(false);
    }
  }

  async function markManaged(id) {
    try {
      await api.post(`/network/devices/${id}/managed`);
      await load();
    } catch (err) {
      console.error(err);
      setError("Unable to update device.");
    }
  }

  useEffect(() => {
    async function sync() {
      await load();
    }
    sync();

    const timer = setInterval(sync, 10000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div style={{ padding: "24px" }}>
      <div style={{ marginBottom: "24px" }}>
        <h1>Network Discovery</h1>
        <p>
          Devices discovered on authorized networks.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit,minmax(180px,1fr))",
          gap: "16px",
          marginBottom: "24px",
        }}
      >
        <Metric title="Discovered" value={summary.total} />
        <Metric title="Online" value={summary.online} />
        <Metric title="Managed" value={summary.managed} />
        <Metric title="Unknown" value={summary.unknown} />
      </div>

      {error && (
        <div
          style={{
            padding: "12px",
            marginBottom: "16px",
            borderRadius: "8px",
            background: "rgba(239,68,68,.12)",
          }}
        >
          {error}
        </div>
      )}

      <div className="card">
        <h2>Discovered Devices</h2>

        {loading ? (
          <p>Loading network devices...</p>
        ) : devices.length === 0 ? (
          <p>No network devices discovered yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>IP</th>
                <th>MAC</th>
                <th>Hostname</th>
                <th>Vendor</th>
                <th>Network</th>
                <th>Type</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {devices.map((device) => (
                <tr key={device.id}>
                  <td>
                    <span
                      className={
                        device.status === "online"
                          ? "status-online"
                          : "status-offline"
                      }
                    >
                      ● {device.status}
                    </span>
                  </td>

                  <td>{device.ip || "—"}</td>
                  <td>{device.mac || "—"}</td>
                  <td>{device.hostname || "Unknown"}</td>
                  <td>{device.vendor || "Unknown"}</td>
                  <td>{device.network || "—"}</td>
                  <td>
                    {device.managed ? "Managed" : "Unknown"}
                  </td>

                  <td>
                    {!device.managed && (
                      <button
                        onClick={() =>
                          markManaged(device.id)
                        }
                      >
                        Mark Managed
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Metric({ title, value }) {
  return (
    <div
      className="card"
      style={{
        padding: "20px",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        background: "var(--surface)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "13px",
          marginBottom: "8px",
        }}
      >
        {title}
      </div>

      <div
        style={{
          fontSize: "30px",
          fontWeight: 800,
        }}
      >
        {value}
      </div>
    </div>
  );
}
