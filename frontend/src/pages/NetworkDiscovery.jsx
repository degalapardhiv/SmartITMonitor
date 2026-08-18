import { useEffect, useState } from "react";
import { FiRadio, FiRefreshCw } from "react-icons/fi";
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
      setLoading(true);

      const [devicesResponse, summaryResponse] = await Promise.all([
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

  const metrics = [
    { title: "Discovered", value: summary.total },
    { title: "Online", value: summary.online },
    { title: "Managed", value: summary.managed },
    { title: "Unknown", value: summary.unknown },
  ];

  return (
    <div>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Network Discovery</h1>
          <p className="ui-page-subtitle">Devices discovered on authorized networks.</p>
        </div>
        <button
          className="ui-btn ui-btn-secondary ui-btn-sm"
          onClick={load}
          disabled={loading}
        >
          <FiRefreshCw /> {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {metrics.map((m) => (
          <div className="ui-stat" key={m.title}>
            <div className="ui-stat-label">{m.title}</div>
            <div className="ui-stat-value mt-1" style={{ color: "var(--ds-text)" }}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="ui-table-wrap">
        <div className="p-6 border-b border-[var(--ds-border)]">
          <h2 className="ui-card-title">Discovered Devices</h2>
        </div>

        {loading ? (
          <div className="ui-loading">
            <span className="ui-spinner" /> Loading network devices...
          </div>
        ) : devices.length === 0 ? (
          <div className="ui-empty">
            <div className="ui-empty-icon"><FiRadio /></div>
            <p className="ui-empty-title">No network devices discovered yet.</p>
          </div>
        ) : (
          <table className="ui-table">
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
                      className={`ui-badge ${device.status === "online" ? "ui-badge-success" : "ui-badge-danger"}`}
                    >
                      {device.status}
                    </span>
                  </td>

                  <td className="font-medium text-white">{device.ip || "—"}</td>
                  <td className="font-mono text-[var(--ds-text-2)]">{device.mac || "—"}</td>
                  <td>{device.hostname || "Unknown"}</td>
                  <td className="text-[var(--ds-text-2)]">{device.vendor || "Unknown"}</td>
                  <td>{device.network || "—"}</td>
                  <td>
                    <span className={`ui-badge ${device.managed ? "ui-badge-success" : "ui-badge-warning"}`}>
                      {device.managed ? "Managed" : "Unknown"}
                    </span>
                  </td>

                  <td>
                    {!device.managed && (
                      <button
                        className="ui-btn ui-btn-secondary ui-btn-sm"
                        onClick={() => markManaged(device.id)}
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