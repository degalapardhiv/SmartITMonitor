import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import { useAuth } from "../context/auth-context";
import useWebSocket from "../hooks/useWebSocket";

const STATUS_STYLES = {
  PENDING: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  INSTALLING: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  COMPLETED: "bg-green-500/20 text-green-400 border-green-500/40",
  FAILED: "bg-red-500/20 text-red-400 border-red-500/40",
  OFFLINE: "bg-gray-500/20 text-gray-400 border-gray-500/40",
};

const TARGET_TYPES = [
  { value: "all", label: "All managed computers" },
  { value: "department", label: "Department" },
  { value: "lab", label: "Lab" },
  { value: "location", label: "Location" },
  { value: "selected", label: "Selected computers" },
];

export default function OsDeployment() {

  const { role, username } = useAuth();

  const isAdmin = String(role || "").toLowerCase() === "admin";

  const [images, setImages] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [summary, setSummary] = useState({});
  const [audit, setAudit] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [imageId, setImageId] = useState("");
  const [targetType, setTargetType] = useState("all");
  const [targetValue, setTargetValue] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [deploying, setDeploying] = useState(false);

  const [showImageForm, setShowImageForm] = useState(false);
  const [editingImage, setEditingImage] = useState(null);
  const [imageForm, setImageForm] = useState({
    name: "",
    version: "",
    edition: "",
    architecture: "x86_64",
    checksum: "",
    checksum_type: "sha256",
    kernel_path: "",
    initrd_path: "",
    kickstart_url: "",
    approved: false,
  });
  const [savingImage, setSavingImage] = useState(false);

  const loadAll = async () => {
    try {
      const [imagesRes, deployRes, summaryRes, auditRes, devicesRes] =
        await Promise.all([
          api.get("/os-images"),
          api.get("/deployments"),
          api.get("/deployments/summary"),
          api.get("/deployments/audit"),
          api.get("/devices"),
        ]);

      setImages(Array.isArray(imagesRes.data) ? imagesRes.data : []);
      setDeployments(Array.isArray(deployRes.data) ? deployRes.data : []);
      setSummary(summaryRes.data || {});
      setAudit(Array.isArray(auditRes.data) ? auditRes.data : []);
      setDevices(Array.isArray(devicesRes.data) ? devicesRes.data : []);
      setError("");
    } catch (err) {
      setError(err?.response?.status === 401 ? "Please login again." : "Unable to load deployment data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(loadAll, 0);
    return () => clearTimeout(timer);
  }, []);

  useWebSocket((msg) => {
    if (msg?.type === "deployment_update") {
      setDeployments((prev) => {
        const next = prev.filter((d) => d.id !== msg.deployment.id);
        return [msg.deployment, ...next];
      });
      loadAll();
    }
  });

  const departments = useMemo(
    () => [...new Set(devices.map((d) => d.department).filter(Boolean))].sort(),
    [devices]
  );

  const labs = useMemo(
    () => [...new Set(devices.map((d) => d.lab).filter(Boolean))].sort(),
    [devices]
  );

  const locations = useMemo(
    () => [...new Set(devices.map((d) => d.location).filter(Boolean))].sort(),
    [devices]
  );

  const targetCount = useMemo(() => {
    if (targetType === "department") {
      return devices.filter((d) => d.department === targetValue).length;
    }
    if (targetType === "lab") {
      return devices.filter((d) => d.lab === targetValue).length;
    }
    if (targetType === "location") {
      return devices.filter((d) => d.location === targetValue).length;
    }
    if (targetType === "selected") {
      return selectedIds.length;
    }
    return devices.length;
  }, [targetType, targetValue, selectedIds, devices]);

  const selectedImage = images.find((image) => image.id === Number(imageId));

  const canDeploy = isAdmin && imageId && targetCount > 0 && selectedImage?.approved;

  const openConfirm = () => {
    setConfirmChecked(false);
    setConfirmOpen(true);
  };

  const runDeploy = async () => {
    setDeploying(true);
    setError("");
    setMessage("");

    try {
      const res = await api.post("/deployments", {
        os_image_id: Number(imageId),
        target_type: targetType,
        target_value: targetValue,
        device_ids: targetType === "selected" ? selectedIds : [],
      });

      const data = res.data || {};

      const parts = [];
      if ((data.created || []).length) {
        parts.push(`${data.created.length} deployment(s) started`);
      }
      if ((data.offline || []).length) {
        parts.push(`${data.offline.length} target(s) offline — queued`);
      }
      if ((data.rejected || []).length) {
        parts.push(`${data.rejected.length} target(s) rejected`);
      }

      setMessage(parts.length ? parts.join(", ") : "Deployment request processed.");
      setConfirmOpen(false);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Deployment failed.");
    } finally {
      setDeploying(false);
    }
  };

  const retryDeployment = async (deployment) => {
    if (!window.confirm(`Retry deployment for "${deployment.hostname}"?`)) return;

    try {
      await api.post(`/deployments/${deployment.id}/retry`);
      setMessage(`Retrying deployment for ${deployment.hostname}.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Retry failed.");
    }
  };

  const resetImageForm = () => {
    setImageForm({
      name: "",
      version: "",
      edition: "",
      architecture: "x86_64",
      checksum: "",
      checksum_type: "sha256",
      kernel_path: "",
      initrd_path: "",
      kickstart_url: "",
      approved: false,
    });
  };

  const openCreateImage = () => {
    setEditingImage(null);
    resetImageForm();
    setShowImageForm(true);
  };

  const openEditImage = (image) => {
    setEditingImage(image);
    setImageForm({
      name: image.name || "",
      version: image.version || "",
      edition: image.edition || "",
      architecture: image.architecture || "x86_64",
      checksum: image.checksum || "",
      checksum_type: image.checksum_type || "sha256",
      kernel_path: image.kernel_path || "",
      initrd_path: image.initrd_path || "",
      kickstart_url: image.kickstart_url || "",
      approved: Boolean(image.approved),
    });
    setShowImageForm(true);
  };

  const saveImage = async (e) => {
    e.preventDefault();
    setSavingImage(true);
    setError("");

    try {
      if (editingImage) {
        await api.put(`/os-images/${editingImage.id}`, imageForm);
        setMessage(`OS image "${imageForm.name}" updated.`);
      } else {
        await api.post("/os-images", imageForm);
        setMessage(`OS image "${imageForm.name}" added.`);
      }
      setShowImageForm(false);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to save OS image.");
    } finally {
      setSavingImage(false);
    }
  };

  const deleteImage = async (image) => {
    if (!window.confirm(`Delete OS image "${image.name}"?`)) return;

    try {
      await api.delete(`/os-images/${image.id}`);
      setMessage(`OS image "${image.name}" deleted.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete OS image.");
    }
  };

  const verifyImage = async (image) => {
    try {
      await api.post(`/os-images/${image.id}/verify-checksum`);
      setMessage(`Checksum verified for "${image.name}".`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Checksum verification failed.");
    }
  };

  const statusBadge = (status) => (
    <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${STATUS_STYLES[status] || STATUS_STYLES.OFFLINE}`}>
      {status}
    </span>
  );

  const progressBar = (deployment) => {
    const color =
      deployment.status === "FAILED"
        ? "bg-red-500"
        : deployment.status === "COMPLETED"
          ? "bg-green-500"
          : "bg-cyan-500";

    return (
      <div className="w-24 bg-slate-700 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full`}
          style={{ width: `${deployment.progress || 0}%` }}
        />
      </div>
    );
  };

  const verificationFlags = (deployment) => {
    const flags = [
      ["agent", deployment.verified_agent],
      ["heartbeat", deployment.verified_heartbeat],
      ["metrics", deployment.verified_metrics],
      ["os", deployment.verified_os],
    ];
    return (
      <div className="flex gap-1">
        {flags.map(([label, ok]) => (
          <span
            key={label}
            title={ok ? `${label} verified` : `${label} not verified`}
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              ok ? "bg-green-500/20 text-green-400" : "bg-slate-700 text-gray-500"
            }`}
          >
            {label}
          </span>
        ))}
      </div>
    );
  };

  if (loading) {
    return <div className="text-gray-400 p-6">Loading OS Deployment...</div>;
  }

  return (
    <div className="space-y-8">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">OS Deployment</h1>
          <p className="text-gray-400 mt-1">Provision operating systems to managed computers</p>
        </div>
      </div>

      {message && (
        <div className="bg-green-500/10 border border-green-500/40 text-green-400 px-4 py-3 rounded-lg">
          {message}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-400 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {!isAdmin && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-gray-400">
          Viewing OS deployment status. Only administrators can start deployments.
        </div>
      )}

      {/* ============ Deployment Form ============ */}

      {isAdmin && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold mb-4">New Deployment</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">OS Image *</label>
              <select
                value={imageId}
                onChange={(e) => setImageId(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              >
                <option value="">Select an approved OS image</option>
                {images.map((image) => (
                  <option key={image.id} value={image.id}>
                    {image.name} {image.version} {image.edition} ({image.architecture})
                    {image.approved ? "" : " — NOT APPROVED"}
                  </option>
                ))}
              </select>
              {selectedImage && (
                <p className="text-xs text-gray-500 mt-1">
                  Checksum: {selectedImage.checksum_type} {selectedImage.checksum || "—"}
                </p>
              )}
              {selectedImage && !selectedImage.approved && (
                <p className="text-xs text-yellow-400 mt-1">
                  This image is not approved for deployment — approve it in the OS Images section first.
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Target *</label>
              <select
                value={targetType}
                onChange={(e) => {
                  setTargetType(e.target.value);
                  setTargetValue("");
                  setSelectedIds([]);
                }}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
              >
                {TARGET_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {targetType === "department" && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Department</label>
                <select
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                >
                  <option value="">Select department</option>
                  {departments.map((department) => (
                    <option key={department} value={department}>{department}</option>
                  ))}
                </select>
              </div>
            )}

            {targetType === "lab" && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Lab</label>
                <select
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                >
                  <option value="">Select lab</option>
                  {labs.map((lab) => (
                    <option key={lab} value={lab}>{lab}</option>
                  ))}
                </select>
              </div>
            )}

            {targetType === "location" && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Location</label>
                <select
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                >
                  <option value="">Select location</option>
                  {locations.map((location) => (
                    <option key={location} value={location}>{location}</option>
                  ))}
                </select>
              </div>
            )}

            {targetType === "selected" && (
              <div className="md:col-span-2">
                <label className="block text-sm text-gray-400 mb-1">
                  Selected computers ({selectedIds.length} selected)
                </label>
                <div className="max-h-48 overflow-y-auto bg-slate-700 border border-slate-600 rounded-lg p-2 grid grid-cols-1 md:grid-cols-2 gap-1">
                  {devices.map((device) => (
                    <label key={device.id} className="flex items-center gap-2 px-2 py-1 hover:bg-slate-600 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(device.id)}
                        onChange={(e) => {
                          setSelectedIds((prev) =>
                            e.target.checked
                              ? [...prev, device.id]
                              : prev.filter((id) => id !== device.id)
                          );
                        }}
                        className="accent-cyan-500"
                      />
                      <span className="text-sm">{device.hostname}</span>
                      <span className={`text-xs ${device.status === "online" ? "text-green-400" : "text-gray-500"}`}>
                        {device.status}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={openConfirm}
              disabled={!canDeploy || deploying}
              className="bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white font-semibold px-6 py-2 rounded-lg transition"
            >
              Deploy
            </button>
            <span className="text-sm text-gray-400">
              {targetCount} target computer{targetCount === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      )}

      {/* ============ Confirmation Modal ============ */}

      {confirmOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-lg w-full space-y-4">
            <h2 className="text-xl font-bold">Confirm OS Deployment</h2>

            <div className="bg-red-500/10 border border-red-500/40 text-red-400 px-4 py-3 rounded-lg text-sm">
              This will reinstall the operating system on {targetCount} computer{targetCount === 1 ? "" : "s"}.
              The machines will reboot into provisioning and their current OS will be replaced.
            </div>

            <div className="text-sm space-y-1 text-gray-300">
              <p><span className="text-gray-500">Image:</span> {selectedImage?.name} {selectedImage?.version} {selectedImage?.edition} ({selectedImage?.architecture})</p>
              <p><span className="text-gray-500">Target:</span> {TARGET_TYPES.find((t) => t.value === targetType)?.label} {targetValue && `— ${targetValue}`}</p>
              <p><span className="text-gray-500">Checksum:</span> {selectedImage?.checksum_type} {selectedImage?.checksum || "—"}</p>
              <p><span className="text-gray-500">Initiator:</span> {username}</p>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={confirmChecked}
                onChange={(e) => setConfirmChecked(e.target.checked)}
                className="accent-red-500"
              />
              I understand this will reinstall the OS on the selected computers
            </label>

            <div className="flex gap-3">
              <button
                onClick={runDeploy}
                disabled={!confirmChecked || deploying}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold px-5 py-2 rounded-lg transition"
              >
                {deploying ? "Deploying..." : "Confirm Deployment"}
              </button>
              <button
                onClick={() => setConfirmOpen(false)}
                className="bg-slate-600 hover:bg-slate-700 text-white font-semibold px-5 py-2 rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============ Status Board ============ */}

      <div>
        <h2 className="text-xl font-bold mb-4">Deployment Status</h2>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {Object.entries(summary).map(([status, count]) => (
            <div key={status} className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
              <p className={`text-2xl font-bold ${STATUS_STYLES[status] ? "text-white" : "text-white"}`}>{count}</p>
              <p className="text-sm text-gray-400">{status}</p>
            </div>
          ))}
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          {deployments.length === 0 ? (
            <div className="text-center text-gray-400 py-10">
              No deployments yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-gray-400">
                  <tr>
                    <th className="px-4 py-3">Computer</th>
                    <th className="px-4 py-3">OS Image</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Progress</th>
                    <th className="px-4 py-3">Verification</th>
                    <th className="px-4 py-3">Started</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {deployments.map((deployment) => (
                    <tr key={deployment.id} className="hover:bg-slate-700/30">
                      <td className="px-4 py-3">
                        <p className="font-semibold">{deployment.hostname}</p>
                        <p className="text-xs text-gray-500">{deployment.ip}</p>
                      </td>
                      <td className="px-4 py-3">
                        <p>{deployment.image_name} {deployment.image_version}</p>
                        <p className="text-xs text-gray-500">{deployment.image_edition} · {deployment.image_architecture}</p>
                      </td>
                      <td className="px-4 py-3">{statusBadge(deployment.status)}</td>
                      <td className="px-4 py-3">{progressBar(deployment)}</td>
                      <td className="px-4 py-3">{verificationFlags(deployment)}</td>
                      <td className="px-4 py-3 text-gray-400">
                        {deployment.created_at ? new Date(deployment.created_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {isAdmin && ["FAILED", "OFFLINE"].includes(deployment.status) && (
                          <button
                            onClick={() => retryDeployment(deployment)}
                            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                          >
                            Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {deployments.some((d) => d.error) && (
            <div className="px-4 py-3 border-t border-slate-700 space-y-1">
              {deployments.filter((d) => d.error).map((d) => (
                <p key={d.id} className="text-xs text-red-400">
                  {d.hostname}: {d.error}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ============ Audit Log ============ */}

      <div>
        <h2 className="text-xl font-bold mb-4">Deployment Audit Log</h2>
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          {audit.length === 0 ? (
            <div className="text-center text-gray-400 py-6 text-sm">No audit events yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-gray-400">
                  <tr>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Action</th>
                    <th className="px-4 py-3">Actor</th>
                    <th className="px-4 py-3">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {audit.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-700/30">
                      <td className="px-4 py-3 text-gray-400">
                        {entry.created_at ? new Date(entry.created_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{entry.action}</td>
                      <td className="px-4 py-3">{entry.actor}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{entry.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ============ OS Images (admin) ============ */}

      {isAdmin && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">OS Images</h2>
            <button
              onClick={openCreateImage}
              className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold px-4 py-2 rounded-lg transition"
            >
              + Add OS Image
            </button>
          </div>

          {showImageForm && (
            <form
              onSubmit={saveImage}
              className="bg-slate-800 border border-slate-700 rounded-xl p-6 mb-4 space-y-4"
            >
              <h3 className="font-bold">
                {editingImage ? `Edit: ${editingImage.name}` : "Add OS Image"}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Name *</label>
                  <input
                    required
                    value={imageForm.name}
                    onChange={(e) => setImageForm({ ...imageForm, name: e.target.value })}
                    placeholder="e.g. Ubuntu Server"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Version</label>
                  <input
                    value={imageForm.version}
                    onChange={(e) => setImageForm({ ...imageForm, version: e.target.value })}
                    placeholder="e.g. 24.04"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Edition</label>
                  <input
                    value={imageForm.edition}
                    onChange={(e) => setImageForm({ ...imageForm, edition: e.target.value })}
                    placeholder="e.g. LTS"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Architecture</label>
                  <select
                    value={imageForm.architecture}
                    onChange={(e) => setImageForm({ ...imageForm, architecture: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  >
                    <option value="x86_64">x86_64</option>
                    <option value="arm64">arm64</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Checksum</label>
                  <input
                    value={imageForm.checksum}
                    onChange={(e) => setImageForm({ ...imageForm, checksum: e.target.value })}
                    placeholder="sha256 hex digest"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Checksum Type</label>
                  <select
                    value={imageForm.checksum_type}
                    onChange={(e) => setImageForm({ ...imageForm, checksum_type: e.target.value })}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  >
                    <option value="sha256">sha256</option>
                    <option value="sha1">sha1</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Kernel Path (PXE)</label>
                  <input
                    value={imageForm.kernel_path}
                    onChange={(e) => setImageForm({ ...imageForm, kernel_path: e.target.value })}
                    placeholder="/images/vmlinuz"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Initrd Path (PXE)</label>
                  <input
                    value={imageForm.initrd_path}
                    onChange={(e) => setImageForm({ ...imageForm, initrd_path: e.target.value })}
                    placeholder="/images/initrd.img"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Kickstart URL</label>
                  <input
                    value={imageForm.kickstart_url}
                    onChange={(e) => setImageForm({ ...imageForm, kickstart_url: e.target.value })}
                    placeholder="http://provisioner/kickstart.cfg"
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={imageForm.approved}
                  onChange={(e) => setImageForm({ ...imageForm, approved: e.target.checked })}
                  className="accent-cyan-500"
                />
                Approved for deployment
              </label>

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={savingImage}
                  className="bg-cyan-600 hover:bg-cyan-700 text-white font-semibold px-5 py-2 rounded-lg transition disabled:opacity-50"
                >
                  {savingImage ? "Saving..." : editingImage ? "Save Changes" : "Add Image"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowImageForm(false)}
                  className="bg-slate-600 hover:bg-slate-700 text-white font-semibold px-5 py-2 rounded-lg transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-gray-400">
                  <tr>
                    <th className="px-4 py-3">OS</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Edition</th>
                    <th className="px-4 py-3">Arch</th>
                    <th className="px-4 py-3">Checksum</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {images.map((image) => (
                    <tr key={image.id} className="hover:bg-slate-700/30">
                      <td className="px-4 py-3 font-semibold">{image.name}</td>
                      <td className="px-4 py-3">{image.version || "—"}</td>
                      <td className="px-4 py-3">{image.edition || "—"}</td>
                      <td className="px-4 py-3">{image.architecture}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400" title={image.checksum}>
                        {image.checksum ? `${image.checksum.slice(0, 12)}…` : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {image.approved ? (
                          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-500/20 text-green-400 border border-green-500/40">Approved</span>
                        ) : (
                          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-yellow-500/20 text-yellow-400 border border-yellow-500/40">Not Approved</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => verifyImage(image)}
                            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-2.5 py-1.5 rounded-lg transition"
                          >
                            Verify Checksum
                          </button>
                          <button
                            onClick={() => openEditImage(image)}
                            className="bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-semibold px-2.5 py-1.5 rounded-lg transition"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => deleteImage(image)}
                            className="bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-2.5 py-1.5 rounded-lg transition"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}