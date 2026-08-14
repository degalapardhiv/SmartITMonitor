import { useEffect, useMemo, useState } from "react";
import {
  FiAlertTriangle,
  FiCheck,
  FiEdit,
  FiPlus,
  FiRefreshCw,
  FiTrash2,
  FiX,
} from "react-icons/fi";
import api from "../services/api";
import { useAuth } from "../context/auth-context";
import useWebSocket from "../hooks/useWebSocket";

const STATUS_STYLES = {
  PENDING: "ui-badge-warning",
  INSTALLING: "ui-badge-info",
  COMPLETED: "ui-badge-success",
  FAILED: "ui-badge-danger",
  OFFLINE: "ui-badge-neutral",
};

const STATUS_VALUE_COLORS = {
  PENDING: "text-[var(--ds-warning)]",
  INSTALLING: "text-[var(--ds-text)]",
  COMPLETED: "text-[var(--ds-success)]",
  FAILED: "text-[var(--ds-danger)]",
  OFFLINE: "text-[var(--ds-text-2)]",
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
    <span className={`ui-badge ${STATUS_STYLES[status] || "ui-badge-neutral"}`}>
      {status}
    </span>
  );

  const progressBar = (deployment) => {
    const color =
      deployment.status === "FAILED"
        ? "bg-[var(--ds-danger)]"
        : deployment.status === "COMPLETED"
          ? "bg-[var(--ds-success)]"
          : "bg-[var(--ds-accent)]";

    return (
      <div className="ui-progress w-24">
        <div
          className={`ui-progress-bar ${color}`}
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
    return (
      <div className="ui-loading">
        <span className="ui-spinner" />
        <p className="mt-3 text-[var(--ds-text-2)]">Loading OS Deployment...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      <div className="ui-page-header">
        <div>
          <h1 className="ui-page-title">OS Deployment</h1>
          <p className="ui-page-subtitle">Provision operating systems to managed computers</p>
        </div>
      </div>

      {message && (
        <div className="rounded-lg border p-4 bg-green-500/10 border-green-500/30 text-[#46d369]">
          {message}
        </div>
      )}

      {error && (
        <div className="rounded-lg border p-4 bg-red-500/10 border-red-500/40 text-[#e6797e]">
          {error}
        </div>
      )}

      {!isAdmin && (
        <div className="ui-card p-4 text-sm text-[var(--ds-text-2)]">
          Viewing OS deployment status. Only administrators can start deployments.
        </div>
      )}

      {/* ============ Deployment Form ============ */}

      {isAdmin && (
        <div className="ui-card">
          <div className="ui-card-header">
            <h2 className="ui-card-title">New Deployment</h2>
          </div>
          <div className="ui-card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="ui-field-label">OS Image *</label>
                <select
                  value={imageId}
                  onChange={(e) => setImageId(e.target.value)}
                  className="ui-input"
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
                  <p className="text-xs text-[var(--ds-text-3)] mt-1">
                    Checksum: {selectedImage.checksum_type} {selectedImage.checksum || "—"}
                  </p>
                )}
                {selectedImage && !selectedImage.approved && (
                  <p className="text-xs text-[var(--ds-warning)] mt-1">
                    This image is not approved for deployment — approve it in the OS Images section first.
                  </p>
                )}
              </div>

              <div>
                <label className="ui-field-label">Target *</label>
                <select
                  value={targetType}
                  onChange={(e) => {
                    setTargetType(e.target.value);
                    setTargetValue("");
                    setSelectedIds([]);
                  }}
                  className="ui-input"
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
                  <label className="ui-field-label">Department</label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="ui-input"
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
                  <label className="ui-field-label">Lab</label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="ui-input"
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
                  <label className="ui-field-label">Location</label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="ui-input"
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
                  <label className="ui-field-label">
                    Selected computers ({selectedIds.length} selected)
                  </label>
                  <div className="max-h-48 overflow-y-auto bg-[var(--ds-surface-3)] border border-[var(--ds-border)] rounded-lg p-2 grid grid-cols-1 md:grid-cols-2 gap-1">
                    {devices.map((device) => (
                      <label key={device.id} className="flex items-center gap-2 px-2 py-1 hover:bg-white/5 rounded cursor-pointer">
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
                          className="accent-[var(--ds-accent)]"
                        />
                        <span className="text-sm">{device.hostname}</span>
                        <span className={`text-xs ${device.status === "online" ? "text-[#46d369]" : "text-[var(--ds-text-3)]"}`}>
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
                className="ui-btn ui-btn-primary"
              >
                Deploy
              </button>
              <span className="text-sm text-[var(--ds-text-2)]">
                {targetCount} target computer{targetCount === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ============ Confirmation Modal ============ */}

      {confirmOpen && (
        <div className="ui-modal-overlay">
          <div className="ui-modal">
            <div className="ui-modal-header">
              <h3 className="ui-modal-title">Confirm OS Deployment</h3>
              <button className="ui-btn ui-btn-ghost ui-btn-sm" onClick={() => setConfirmOpen(false)}>
                <FiX />
              </button>
            </div>

            <div className="ui-modal-body">
              <div className="mb-4 rounded-lg border p-4 text-sm bg-red-500/10 border-red-500/40 text-[#e6797e]">
                <FiAlertTriangle className="inline mr-1 -mt-0.5" />
                This will reinstall the operating system on {targetCount} computer{targetCount === 1 ? "" : "s"}.
                The machines will reboot into provisioning and their current OS will be replaced.
              </div>

              <div className="text-sm space-y-1 text-[var(--ds-text)]">
                <p><span className="text-[var(--ds-text-3)]">Image:</span> {selectedImage?.name} {selectedImage?.version} {selectedImage?.edition} ({selectedImage?.architecture})</p>
                <p><span className="text-[var(--ds-text-3)]">Target:</span> {TARGET_TYPES.find((t) => t.value === targetType)?.label} {targetValue && `— ${targetValue}`}</p>
                <p><span className="text-[var(--ds-text-3)]">Checksum:</span> {selectedImage?.checksum_type} {selectedImage?.checksum || "—"}</p>
                <p><span className="text-[var(--ds-text-3)]">Initiator:</span> {username}</p>
              </div>

              <label className="flex items-center gap-2 mt-4 text-sm text-[var(--ds-text)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={confirmChecked}
                  onChange={(e) => setConfirmChecked(e.target.checked)}
                  className="accent-[var(--ds-accent)]"
                />
                I understand this will reinstall the OS on the selected computers
              </label>
            </div>

            <div className="ui-modal-footer">
              <button
                onClick={() => setConfirmOpen(false)}
                className="ui-btn ui-btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={runDeploy}
                disabled={!confirmChecked || deploying}
                className="ui-btn ui-btn-primary"
              >
                <FiCheck /> {deploying ? "Deploying..." : "Confirm Deployment"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============ Status Board ============ */}

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Deployment Status</h2>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {Object.entries(summary).map(([status, count]) => (
            <div key={status} className="ui-stat text-center">
              <p className="ui-stat-label">{status}</p>
              <p className={`ui-stat-value ${STATUS_VALUE_COLORS[status] || "text-[var(--ds-text)]"}`}>{count}</p>
            </div>
          ))}
        </div>

        {deployments.length === 0 ? (
          <div className="ui-table-wrap">
            <div className="ui-empty">
              <p className="ui-empty-title">No deployments yet.</p>
            </div>
          </div>
        ) : (
          <div className="ui-table-wrap">
            <table className="ui-table">
              <thead>
                <tr>
                  <th>Computer</th>
                  <th>OS Image</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Verification</th>
                  <th>Started</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {deployments.map((deployment) => (
                  <tr key={deployment.id}>
                    <td>
                      <p className="font-semibold">{deployment.hostname}</p>
                      <p className="text-xs text-[var(--ds-text-3)]">{deployment.ip}</p>
                    </td>
                    <td>
                      <p>{deployment.image_name} {deployment.image_version}</p>
                      <p className="text-xs text-[var(--ds-text-3)]">{deployment.image_edition} · {deployment.image_architecture}</p>
                    </td>
                    <td>{statusBadge(deployment.status)}</td>
                    <td>{progressBar(deployment)}</td>
                    <td>{verificationFlags(deployment)}</td>
                    <td className="text-[var(--ds-text-2)]">
                      {deployment.created_at ? new Date(deployment.created_at).toLocaleString() : "—"}
                    </td>
                    <td>
                      {isAdmin && ["FAILED", "OFFLINE"].includes(deployment.status) && (
                        <button
                          onClick={() => retryDeployment(deployment)}
                          className="ui-btn ui-btn-secondary ui-btn-sm"
                        >
                          <FiRefreshCw /> Retry
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
          <div className="mt-3 rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] px-4 py-3 space-y-1">
            {deployments.filter((d) => d.error).map((d) => (
              <p key={d.id} className="text-xs text-[var(--ds-danger)]">
                {d.hostname}: {d.error}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* ============ Audit Log ============ */}

      <div>
        <h2 className="text-lg font-bold text-white mb-4">Deployment Audit Log</h2>
        {audit.length === 0 ? (
          <div className="ui-table-wrap">
            <div className="ui-empty">
              <p className="ui-empty-title">No audit events yet.</p>
            </div>
          </div>
        ) : (
          <div className="ui-table-wrap">
            <table className="ui-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Actor</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((entry) => (
                  <tr key={entry.id}>
                    <td className="text-[var(--ds-text-2)]">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="font-mono text-xs">{entry.action}</td>
                    <td>{entry.actor}</td>
                    <td className="text-[var(--ds-text-2)] text-xs">{entry.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ============ OS Images (admin) ============ */}

      {isAdmin && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">OS Images</h2>
            <button
              onClick={openCreateImage}
              className="ui-btn ui-btn-primary"
            >
              <FiPlus /> Add OS Image
            </button>
          </div>

          {showImageForm && (
            <form
              onSubmit={saveImage}
              className="ui-card p-6 mb-4 space-y-4"
            >
              <h3 className="font-bold text-white">
                {editingImage ? `Edit: ${editingImage.name}` : "Add OS Image"}
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="ui-field-label">Name *</label>
                  <input
                    required
                    value={imageForm.name}
                    onChange={(e) => setImageForm({ ...imageForm, name: e.target.value })}
                    placeholder="e.g. Ubuntu Server"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Version</label>
                  <input
                    value={imageForm.version}
                    onChange={(e) => setImageForm({ ...imageForm, version: e.target.value })}
                    placeholder="e.g. 24.04"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Edition</label>
                  <input
                    value={imageForm.edition}
                    onChange={(e) => setImageForm({ ...imageForm, edition: e.target.value })}
                    placeholder="e.g. LTS"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Architecture</label>
                  <select
                    value={imageForm.architecture}
                    onChange={(e) => setImageForm({ ...imageForm, architecture: e.target.value })}
                    className="ui-input"
                  >
                    <option value="x86_64">x86_64</option>
                    <option value="arm64">arm64</option>
                  </select>
                </div>
                <div>
                  <label className="ui-field-label">Checksum</label>
                  <input
                    value={imageForm.checksum}
                    onChange={(e) => setImageForm({ ...imageForm, checksum: e.target.value })}
                    placeholder="sha256 hex digest"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Checksum Type</label>
                  <select
                    value={imageForm.checksum_type}
                    onChange={(e) => setImageForm({ ...imageForm, checksum_type: e.target.value })}
                    className="ui-input"
                  >
                    <option value="sha256">sha256</option>
                    <option value="sha1">sha1</option>
                  </select>
                </div>
                <div>
                  <label className="ui-field-label">Kernel Path (PXE)</label>
                  <input
                    value={imageForm.kernel_path}
                    onChange={(e) => setImageForm({ ...imageForm, kernel_path: e.target.value })}
                    placeholder="/images/vmlinuz"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Initrd Path (PXE)</label>
                  <input
                    value={imageForm.initrd_path}
                    onChange={(e) => setImageForm({ ...imageForm, initrd_path: e.target.value })}
                    placeholder="/images/initrd.img"
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Kickstart URL</label>
                  <input
                    value={imageForm.kickstart_url}
                    onChange={(e) => setImageForm({ ...imageForm, kickstart_url: e.target.value })}
                    placeholder="http://provisioner/kickstart.cfg"
                    className="ui-input"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-[var(--ds-text)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={imageForm.approved}
                  onChange={(e) => setImageForm({ ...imageForm, approved: e.target.checked })}
                  className="accent-[var(--ds-accent)]"
                />
                Approved for deployment
              </label>

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={savingImage}
                  className="ui-btn ui-btn-primary"
                >
                  {savingImage ? "Saving..." : editingImage ? "Save Changes" : "Add Image"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowImageForm(false)}
                  className="ui-btn ui-btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="ui-table-wrap">
            <table className="ui-table">
              <thead>
                <tr>
                  <th>OS</th>
                  <th>Version</th>
                  <th>Edition</th>
                  <th>Arch</th>
                  <th>Checksum</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {images.map((image) => (
                  <tr key={image.id}>
                    <td className="font-semibold">{image.name}</td>
                    <td>{image.version || "—"}</td>
                    <td>{image.edition || "—"}</td>
                    <td>{image.architecture}</td>
                    <td className="font-mono text-xs text-[var(--ds-text-2)]" title={image.checksum}>
                      {image.checksum ? `${image.checksum.slice(0, 12)}…` : "—"}
                    </td>
                    <td>
                      {image.approved ? (
                        <span className="ui-badge ui-badge-success">Approved</span>
                      ) : (
                        <span className="ui-badge ui-badge-warning">Not Approved</span>
                      )}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          onClick={() => verifyImage(image)}
                          className="ui-btn ui-btn-secondary ui-btn-sm"
                        >
                          <FiRefreshCw /> Verify Checksum
                        </button>
                        <button
                          onClick={() => openEditImage(image)}
                          className="ui-btn ui-btn-secondary ui-btn-sm"
                        >
                          <FiEdit /> Edit
                        </button>
                        <button
                          onClick={() => deleteImage(image)}
                          className="ui-btn ui-btn-danger ui-btn-sm"
                        >
                          <FiTrash2 /> Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
