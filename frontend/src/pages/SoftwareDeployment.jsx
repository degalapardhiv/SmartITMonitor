import { useEffect, useMemo, useState } from "react";
import api from "../services/api";
import { useAuth } from "../context/auth-context";
import useWebSocket from "../hooks/useWebSocket";
import {
  FiCheck,
  FiDownload,
  FiEdit2,
  FiPlus,
  FiTrash2,
  FiUpload,
  FiX,
} from "react-icons/fi";

const PACKAGE_STATUS_STYLES = {
  pending: "ui-badge-warning",
  approved: "ui-badge-success",
  rejected: "ui-badge-danger",
};

const DEPLOYMENT_STATUS_STYLES = {
  pending: "ui-badge-warning",
  running: "ui-badge-info",
  completed: "ui-badge-success",
  failed: "ui-badge-danger",
  cancelled: "ui-badge-neutral",
};

const TARGET_STATUS_STYLES = {
  pending: "ui-badge-warning",
  downloading: "ui-badge-info",
  installing: "ui-badge-accent",
  completed: "ui-badge-success",
  failed: "ui-badge-danger",
  offline: "ui-badge-neutral",
  cancelled: "ui-badge-neutral",
};

const OS_OPTIONS = ["windows", "linux", "macos", ""];
const ARCH_OPTIONS = ["x64", "x86", "arm64", "arm", ""];

const SCOPES = [
  { value: "all", label: "All compatible computers" },
  { value: "department", label: "Department" },
  { value: "lab", label: "Lab" },
  { value: "location", label: "Location" },
  { value: "selected", label: "Selected computers" },
];

function StatusBadge({ status }) {
  const style =
    PACKAGE_STATUS_STYLES[status] ||
    DEPLOYMENT_STATUS_STYLES[status] ||
    TARGET_STATUS_STYLES[status] ||
    "ui-badge-neutral";

  return (
    <span className={`ui-badge ${style}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

function ProgressBar({ progress, status }) {
  const color =
    status === "failed"
      ? "bg-[var(--ds-danger)]"
      : status === "completed"
        ? "bg-[var(--ds-success)]"
        : "bg-[var(--ds-accent)]";

  return (
    <div className="flex items-center gap-2">
      <div className="ui-progress w-24">
        <div
          className={`ui-progress-bar ${color}`}
          style={{ width: `${Math.min(100, progress || 0)}%` }}
        />
      </div>
      <span className="text-xs text-[var(--ds-text-3)]">{progress || 0}%</span>
    </div>
  );
}

export default function SoftwareDeployment() {
  const { role } = useAuth();
  const isAdmin = String(role || "").toLowerCase() === "admin";

  const [tab, setTab] = useState("deployments");

  const [packages, setPackages] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [groups, setGroups] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [showPackageForm, setShowPackageForm] = useState(false);
  const [savingPackage, setSavingPackage] = useState(false);
  const [packageFile, setPackageFile] = useState(null);
  const [packageForm, setPackageForm] = useState({
    name: "",
    version: "",
    publisher: "",
    os: "windows",
    architecture: "x64",
    install_command: "",
    uninstall_command: "",
    verify_command: "",
    install_timeout_seconds: 600,
    notes: "",
  });

  const [showDeployForm, setShowDeployForm] = useState(false);
  const [packageId, setPackageId] = useState("");
  const [action, setAction] = useState("install");
  const [scope, setScope] = useState("all");
  const [scopeRef, setScopeRef] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [description, setDescription] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [confirmChecked, setConfirmChecked] = useState(false);

  const [selectedDeployment, setSelectedDeployment] = useState(null);
  const [deploymentDetail, setDeploymentDetail] = useState(null);
  const [deploymentEvents, setDeploymentEvents] = useState([]);

  const [showGroupForm, setShowGroupForm] = useState(false);
  const [groupForm, setGroupForm] = useState({ name: "" });
  const [savingGroup, setSavingGroup] = useState(false);
  const [editingGroup, setEditingGroup] = useState(null);
  const [groupDevices, setGroupDevices] = useState([]);

  const [inventorySearch, setInventorySearch] = useState("");
  const [inventoryFilter, setInventoryFilter] = useState("");

  const loadAll = async () => {
    try {
      const [pkgRes, depRes, groupRes, invRes, devRes] = await Promise.all([
        api.get("/software/packages"),
        api.get("/software/deployments"),
        api.get("/software/groups"),
        api.get("/software/inventory"),
        api.get("/devices"),
      ]);

      setPackages(pkgRes.data.packages || []);
      setDeployments(depRes.data.deployments || []);
      setGroups(groupRes.data.groups || []);
      setInventory(invRes.data.items || []);
      setDevices(Array.isArray(devRes.data) ? devRes.data : []);
      setError("");
    } catch (err) {
      setError(
        err?.response?.status === 401
          ? "Please login again."
          : "Unable to load software deployment data."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(loadAll, 0);
    return () => clearTimeout(timer);
  }, []);

  useWebSocket((msg) => {
    if (msg?.type === "software_deployment_update") {
      loadAll();
    }
  });

  const pendingCount = packages.filter(
    (p) => p.approval_status === "pending"
  ).length;

  const activeDeployments = deployments.filter(
    (d) => d.status === "running" || d.status === "pending"
  ).length;

  const installedCount = inventory.filter(
    (i) => inventoryFilter === "" || i.name === inventoryFilter
  ).length;

  const filterInventory = useMemo(() => {
    const query = inventorySearch.toLowerCase();
    return inventory.filter(
      (item) =>
        item.name.toLowerCase().includes(query) ||
        (item.device || "").toLowerCase().includes(query) ||
        (item.version || "").toLowerCase().includes(query)
    );
  }, [inventory, inventorySearch]);

  const inventoryNames = useMemo(
    () => [...new Set(inventory.map((i) => i.name))].sort(),
    [inventory]
  );

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

  const scopeValues = {
    department: departments,
    lab: labs,
    location: locations,
  };

  const resetPackageForm = () => {
    setPackageForm({
      name: "",
      version: "",
      publisher: "",
      os: "windows",
      architecture: "x64",
      install_command: "",
      uninstall_command: "",
      verify_command: "",
      install_timeout_seconds: 600,
      notes: "",
    });
    setPackageFile(null);
  };

  const submitPackage = async (e) => {
    e.preventDefault();
    setSavingPackage(true);
    setError("");

    try {
      const data = new FormData();
      Object.entries(packageForm).forEach(([key, value]) => {
        data.append(key, String(value));
      });
      if (packageFile) {
        data.append("file", packageFile);
      }

      const res = await api.post("/software/packages", data, {
        headers: { "Content-Type": undefined },
      });

      setMessage(
        `Package "${res.data.name} ${res.data.version}" uploaded (pending approval).`
      );
      setShowPackageForm(false);
      resetPackageForm();
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to upload package.");
    } finally {
      setSavingPackage(false);
    }
  };

  const setApproval = async (pkg, approvalStatus) => {
    try {
      await api.post(`/software/packages/${pkg.id}/approve`, {
        approval_status: approvalStatus,
      });
      setMessage(`Package "${pkg.name}" ${approvalStatus}.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update approval.");
    }
  };

  const downloadPackage = async (pkg) => {
    try {
      const res = await api.get(`/software/packages/${pkg.id}/download`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = pkg.file_name || `${pkg.name}.bin`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to download package.");
    }
  };

  const deletePackage = async (pkg) => {
    if (!window.confirm(`Delete package "${pkg.name} ${pkg.version}"?`)) return;

    try {
      await api.delete(`/software/packages/${pkg.id}`);
      setMessage(`Package "${pkg.name}" deleted.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete package.");
    }
  };

  const openDeployForm = () => {
    setPackageId("");
    setAction("install");
    setScope("all");
    setScopeRef("");
    setSelectedIds([]);
    setDescription("");
    setPreview(null);
    setConfirmChecked(false);
    setShowDeployForm(true);
  };

  const runPreview = async () => {
    if (!packageId) return;

    setPreviewing(true);
    setPreview(null);
    setError("");

    try {
      const params = {
        package_id: packageId,
        scope,
        scope_ref: scopeRef,
        device_ids:
          scope === "selected" ? selectedIds.join(",") : "",
      };

      const res = await api.get("/software/preview", { params });
      setPreview(res.data);
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Unable to preview targets."
      );
    } finally {
      setPreviewing(false);
    }
  };

  const runDeployment = async () => {
    setDeploying(true);
    setError("");

    try {
      const res = await api.post("/software/deployments", {
        package_id: Number(packageId),
        action,
        scope,
        scope_ref: scopeRef,
        device_ids: scope === "selected" ? selectedIds : [],
        confirm: true,
        description,
      });

      const data = res.data || {};
      const parts = [];
      if (data.summary?.total !== undefined) {
        parts.push(`${data.summary.total} target(s)`);
      }
      if ((data.summary?.offline || 0) > 0) {
        parts.push(`${data.summary.offline} offline (queued)`);
      }

      setMessage(
        `Deployment ${data.id} started: ${parts.length ? parts.join(", ") : ""}`
      );
      setShowDeployForm(false);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Deployment failed.");
    } finally {
      setDeploying(false);
    }
  };

  const openDeployment = async (deployment) => {
    setSelectedDeployment(deployment);
    setDeploymentDetail(null);
    setDeploymentEvents([]);

    try {
      const [detailRes, eventsRes] = await Promise.all([
        api.get(`/software/deployments/${deployment.id}`),
        api.get(`/software/deployments/${deployment.id}/events`),
      ]);
      setDeploymentDetail(detailRes.data);
      setDeploymentEvents(eventsRes.data.events || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load deployment.");
    }
  };

  const cancelDeployment = async (deployment) => {
    if (!window.confirm(`Cancel deployment ${deployment.id}?`)) return;

    try {
      await api.post(`/software/deployments/${deployment.id}/cancel`);
      setMessage(`Deployment ${deployment.id} cancelled.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to cancel deployment.");
    }
  };

  const openCreateGroup = () => {
    setEditingGroup(null);
    setGroupForm({ name: "" });
    setGroupDevices([]);
    setShowGroupForm(true);
  };

  const openEditGroup = (group) => {
    setEditingGroup(group);
    setGroupForm({ name: group.name });
    setShowGroupForm(true);

    api
      .get(`/software/groups/${group.id}/members`)
      .then((res) => setGroupDevices(res.data.device_ids || []))
      .catch(() => setGroupDevices([]));
  };

  const submitGroup = async (e) => {
    e.preventDefault();
    setSavingGroup(true);
    setError("");

    try {
      if (editingGroup) {
        await api.put(`/software/groups/${editingGroup.id}`, groupForm);
        await api.post(`/software/groups/${editingGroup.id}/members`, {
          device_ids: groupDevices,
        });
        setMessage(`Group "${groupForm.name}" updated.`);
      } else {
        const res = await api.post("/software/groups", groupForm);
        await api.post(`/software/groups/${res.data.id}/members`, {
          device_ids: groupDevices,
        });
        setMessage(`Group "${groupForm.name}" created.`);
      }
      setShowGroupForm(false);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to save group.");
    } finally {
      setSavingGroup(false);
    }
  };

  const deleteGroup = async (group) => {
    if (!window.confirm(`Delete group "${group.name}"?`)) return;

    try {
      await api.delete(`/software/groups/${group.id}`);
      setMessage(`Group "${group.name}" deleted.`);
      loadAll();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete group.");
    }
  };

  const toggleDevice = (deviceId) => {
    setSelectedIds((prev) =>
      prev.includes(deviceId)
        ? prev.filter((id) => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const toggleGroupDevice = (deviceId) => {
    setGroupDevices((prev) =>
      prev.includes(deviceId)
        ? prev.filter((id) => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const tabButton = (key, label) => (
    <button
      onClick={() => setTab(key)}
      className={`ui-tab ${tab === key ? "ui-tab-active" : ""}`}
    >
      {label}
    </button>
  );

  if (loading) {
    return (
      <div className="ui-loading flex items-center justify-center gap-3 text-[var(--ds-text-2)]">
        <span className="ui-spinner" />
        Loading Software Deployment...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="ui-page-header">
        <div>
          <h1 className="ui-page-title">Software Deployment</h1>
          <p className="ui-page-subtitle">
            Manage software packages, groups and push installs to managed
            computers
          </p>
        </div>
        {isAdmin && (
          <div className="ui-page-actions">
            <button
              onClick={openDeployForm}
              className="ui-btn ui-btn-primary"
            >
              <FiPlus /> New Deployment
            </button>
            <button
              onClick={() => {
                resetPackageForm();
                setShowPackageForm(true);
              }}
              className="ui-btn ui-btn-secondary"
            >
              <FiUpload /> Upload Package
            </button>
          </div>
        )}
      </div>

      {message && (
        <div className="border border-[rgba(70,211,105,0.3)] bg-[rgba(70,211,105,0.1)] text-[var(--ds-success)] px-4 py-3 rounded-lg">
          {message}
        </div>
      )}

      {error && (
        <div className="border border-[rgba(214,69,77,0.3)] bg-[rgba(214,69,77,0.1)] text-[var(--ds-danger)] px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="ui-stat">
          <p className="ui-stat-label">Packages</p>
          <p className="ui-stat-value">{packages.length}</p>
        </div>
        <div className="ui-stat">
          <p className="ui-stat-label">Pending Approval</p>
          <p className="ui-stat-value text-[var(--ds-warning)]">{pendingCount}</p>
        </div>
        <div className="ui-stat">
          <p className="ui-stat-label">Active Deployments</p>
          <p className="ui-stat-value text-[var(--ds-accent)]">
            {activeDeployments}
          </p>
        </div>
        <div className="ui-stat">
          <p className="ui-stat-label">Software Installed</p>
          <p className="ui-stat-value text-[var(--ds-success)]">{installedCount}</p>
        </div>
      </div>

      <div className="ui-tabs">
        {tabButton("deployments", "Deployments")}
        {tabButton("packages", "Packages")}
        {tabButton("groups", "Groups")}
        {tabButton("inventory", "Inventory")}
      </div>

      {tab === "deployments" && (
        <div className="ui-table-wrap">
          <table className="ui-table text-left">
            <thead>
              <tr>
                <th className="px-4">#</th>
                <th className="px-4">Package</th>
                <th className="px-4">Action</th>
                <th className="px-4">Scope</th>
                <th className="px-4">Status</th>
                <th className="px-4">Progress</th>
                <th className="px-4">Created</th>
                <th className="px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {deployments.length === 0 && (
                <tr>
                  <td colSpan="8" className="ui-empty">
                    No deployments yet — click "New Deployment" to push software.
                  </td>
                </tr>
              )}
              {deployments.map((deployment) => {
                const summary = deployment.summary || {};
                const total = summary.total || 0;
                const done = summary.completed || 0;
                const progress = total ? Math.round((done / total) * 100) : 0;

                return (
                  <tr
                    key={deployment.id}
                    className="hover:cursor-pointer"
                    onClick={() => openDeployment(deployment)}
                  >
                    <td className="px-4 text-[var(--ds-text-2)]">
                      {deployment.id}
                    </td>
                    <td className="px-4">
                      {deployment.package
                        ? `${deployment.package.name} ${deployment.package.version}`
                        : "Package deleted"}
                    </td>
                    <td className="px-4 capitalize">{deployment.action}</td>
                    <td className="px-4 text-[var(--ds-text-2)]">
                      {deployment.scope}
                      {deployment.scope_ref ? `: ${deployment.scope_ref}` : ""}
                    </td>
                    <td className="px-4">
                      <StatusBadge status={deployment.status} />
                    </td>
                    <td className="px-4">
                      <ProgressBar
                        progress={progress}
                        status={deployment.status}
                      />
                      {total > 0 && (
                        <span className="text-xs text-[var(--ds-text-3)]">
                          {done}/{total} done
                        </span>
                      )}
                    </td>
                    <td className="px-4 text-[var(--ds-text-2)] text-sm">
                      {deployment.created_at
                        ? new Date(deployment.created_at).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-4">
                      <div className="flex gap-2">
                        {isAdmin &&
                          ["pending", "running"].includes(deployment.status) && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                cancelDeployment(deployment);
                              }}
                              className="ui-btn ui-btn-danger ui-btn-sm"
                            >
                              Cancel
                            </button>
                          )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === "packages" && (
        <div className="ui-table-wrap">
          <table className="ui-table text-left">
            <thead>
              <tr>
                <th className="px-4">Name</th>
                <th className="px-4">Version</th>
                <th className="px-4">Publisher</th>
                <th className="px-4">OS</th>
                <th className="px-4">Size</th>
                <th className="px-4">Approval</th>
                <th className="px-4">Uploaded By</th>
                <th className="px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {packages.length === 0 && (
                <tr>
                  <td colSpan="8" className="ui-empty">
                    No packages yet — upload an installer to get started.
                  </td>
                </tr>
              )}
              {packages.map((pkg) => (
                <tr key={pkg.id}>
                  <td className="px-4 font-semibold">
                    {pkg.name}
                    {pkg.notes && (
                      <p className="text-xs text-[var(--ds-text-3)]">{pkg.notes}</p>
                    )}
                  </td>
                  <td className="px-4">{pkg.version}</td>
                  <td className="px-4 text-[var(--ds-text-2)]">
                    {pkg.publisher || "-"}
                  </td>
                  <td className="px-4 text-[var(--ds-text-2)]">
                    {pkg.os || "any"}
                    {pkg.architecture ? ` / ${pkg.architecture}` : ""}
                  </td>
                  <td className="px-4 text-[var(--ds-text-2)]">
                    {pkg.file_size
                      ? `${(pkg.file_size / 1024).toFixed(1)} KB`
                      : "-"}
                  </td>
                  <td className="px-4">
                    <StatusBadge status={pkg.approval_status} />
                  </td>
                  <td className="px-4 text-[var(--ds-text-2)]">{pkg.created_by}</td>
                  <td className="px-4">
                    <div className="flex gap-2 flex-wrap">
                      {isAdmin && pkg.approval_status === "pending" && (
                        <>
                          <button
                            onClick={() => setApproval(pkg, "approved")}
                            className="ui-btn ui-btn-secondary ui-btn-sm"
                          >
                            <FiCheck /> Approve
                          </button>
                          <button
                            onClick={() => setApproval(pkg, "rejected")}
                            className="ui-btn ui-btn-danger ui-btn-sm"
                          >
                            <FiX /> Reject
                          </button>
                        </>
                      )}
                      {isAdmin && pkg.approval_status === "rejected" && (
                        <button
                          onClick={() => setApproval(pkg, "approved")}
                          className="ui-btn ui-btn-secondary ui-btn-sm"
                        >
                          <FiCheck /> Approve
                        </button>
                      )}
                      <button
                        onClick={() => downloadPackage(pkg)}
                        className="ui-btn ui-btn-secondary ui-btn-sm"
                      >
                        <FiDownload /> Download
                      </button>
                      {isAdmin && (
                        <button
                          onClick={() => deletePackage(pkg)}
                          className="ui-btn ui-btn-danger ui-btn-sm"
                        >
                          <FiTrash2 /> Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "groups" && (
        <div className="ui-card">
          <div className="ui-card-header">
            <h2 className="ui-card-title">Device Groups</h2>
            {isAdmin && (
              <button
                onClick={openCreateGroup}
                className="ui-btn ui-btn-primary ui-btn-sm"
              >
                <FiPlus /> New Group
              </button>
            )}
          </div>
          <div className="ui-card-body">
            {groups.length === 0 && (
              <div className="ui-empty">
                No groups yet — create a group to target a subset of computers.
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groups.map((group) => (
                <div
                  key={group.id}
                  className="bg-[var(--ds-surface-3)] rounded-xl p-5 border border-[var(--ds-border)]"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-white">{group.name}</h3>
                    <span className="text-sm text-[var(--ds-text-2)]">
                      {group.device_count} device(s)
                    </span>
                  </div>
                  {isAdmin && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEditGroup(group)}
                        className="ui-btn ui-btn-secondary ui-btn-sm"
                      >
                        <FiEdit2 /> Manage
                      </button>
                      <button
                        onClick={() => deleteGroup(group)}
                        className="ui-btn ui-btn-danger ui-btn-sm"
                      >
                        <FiTrash2 /> Delete
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "inventory" && (
        <div className="ui-card">
          <div className="ui-card-header">
            <h2 className="ui-card-title">Software Inventory</h2>
          </div>
          <div className="ui-card-body">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <input
                type="text"
                placeholder="Search software or device..."
                value={inventorySearch}
                onChange={(e) => setInventorySearch(e.target.value)}
                className="ui-input flex-1 min-w-48"
              />
              <select
                value={inventoryFilter}
                onChange={(e) => setInventoryFilter(e.target.value)}
                className="ui-input !w-auto"
              >
                <option value="">All software</option>
                {inventoryNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            {filterInventory.length === 0 && (
              <div className="ui-empty">
                No software inventory reported by agents yet.
              </div>
            )}

            <div className="ui-table-wrap">
              <table className="ui-table text-left">
                <thead>
                  <tr>
                    <th className="px-4">Software</th>
                    <th className="px-4">Version</th>
                    <th className="px-4">Publisher</th>
                    <th className="px-4">Device</th>
                    <th className="px-4">Installed</th>
                  </tr>
                </thead>
                <tbody>
                  {filterInventory
                    .filter(
                      (item) =>
                        inventoryFilter === "" || item.name === inventoryFilter
                    )
                    .map((item) => (
                      <tr key={item.id}>
                        <td className="px-4 font-semibold">{item.name}</td>
                        <td className="px-4">{item.version || "-"}</td>
                        <td className="px-4 text-[var(--ds-text-2)]">
                          {item.publisher || "-"}
                        </td>
                        <td className="px-4 text-[var(--ds-text-2)]">
                          {item.device}
                        </td>
                        <td className="px-4 text-[var(--ds-text-2)]">
                          {item.install_date
                            ? new Date(item.install_date).toLocaleDateString()
                            : "-"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {showPackageForm && (
        <div className="ui-modal-overlay">
          <form onSubmit={submitPackage} className="ui-modal !max-w-xl">
            <div className="ui-modal-header">
              <h2 className="ui-modal-title">Upload Software Package</h2>
              <button
                type="button"
                onClick={() => setShowPackageForm(false)}
                className="ui-btn ui-btn-ghost ui-btn-sm"
              >
                <FiX />
              </button>
            </div>

            <div className="ui-modal-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="ui-field-label">Name *</label>
                  <input
                    required
                    value={packageForm.name}
                    onChange={(e) =>
                      setPackageForm({ ...packageForm, name: e.target.value })
                    }
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Version *</label>
                  <input
                    required
                    value={packageForm.version}
                    onChange={(e) =>
                      setPackageForm({
                        ...packageForm,
                        version: e.target.value,
                      })
                    }
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Publisher</label>
                  <input
                    value={packageForm.publisher}
                    onChange={(e) =>
                      setPackageForm({ ...packageForm, publisher: e.target.value })
                    }
                    className="ui-input"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Installer file *</label>
                  <input
                    required
                    type="file"
                    onChange={(e) => setPackageFile(e.target.files[0])}
                    className="ui-input text-[var(--ds-text-2)]"
                  />
                </div>
                <div>
                  <label className="ui-field-label">Target OS</label>
                  <select
                    value={packageForm.os}
                    onChange={(e) =>
                      setPackageForm({ ...packageForm, os: e.target.value })
                    }
                    className="ui-input"
                  >
                    {OS_OPTIONS.map((os) => (
                      <option key={os || "any"} value={os}>
                        {os || "Any"}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="ui-field-label">Architecture</label>
                  <select
                    value={packageForm.architecture}
                    onChange={(e) =>
                      setPackageForm({
                        ...packageForm,
                        architecture: e.target.value,
                      })
                    }
                    className="ui-input"
                  >
                    {ARCH_OPTIONS.map((arch) => (
                      <option key={arch || "any"} value={arch}>
                        {arch || "Any"}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4">
                <label className="ui-field-label">
                  Install command * (runs on the target computer)
                </label>
                <input
                  required
                  value={packageForm.install_command}
                  onChange={(e) =>
                    setPackageForm({
                      ...packageForm,
                      install_command: e.target.value,
                    })
                  }
                  placeholder="installer.exe /silent /install"
                  className="ui-input font-mono text-sm"
                />
              </div>

              <div className="mt-4">
                <label className="ui-field-label">Uninstall command</label>
                <input
                  value={packageForm.uninstall_command}
                  onChange={(e) =>
                    setPackageForm({
                      ...packageForm,
                      uninstall_command: e.target.value,
                    })
                  }
                  className="ui-input font-mono text-sm"
                />
              </div>

              <div className="mt-4">
                <label className="ui-field-label">
                  Verify command (used to confirm install and detect version)
                </label>
                <input
                  value={packageForm.verify_command}
                  onChange={(e) =>
                    setPackageForm({
                      ...packageForm,
                      verify_command: e.target.value,
                    })
                  }
                  placeholder="app --version"
                  className="ui-input font-mono text-sm"
                />
              </div>

              <div className="mt-4">
                <label className="ui-field-label">
                  Install timeout (seconds)
                </label>
                <input
                  type="number"
                  min="30"
                  value={packageForm.install_timeout_seconds}
                  onChange={(e) =>
                    setPackageForm({
                      ...packageForm,
                      install_timeout_seconds: Number(e.target.value),
                    })
                  }
                  className="ui-input"
                />
              </div>

              <div className="mt-4">
                <label className="ui-field-label">Notes</label>
                <textarea
                  value={packageForm.notes}
                  onChange={(e) =>
                    setPackageForm({ ...packageForm, notes: e.target.value })
                  }
                  className="ui-input"
                  rows="2"
                />
              </div>
            </div>

            <div className="ui-modal-footer">
              <button
                type="button"
                onClick={() => setShowPackageForm(false)}
                className="ui-btn ui-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingPackage}
                className="ui-btn ui-btn-primary"
              >
                {savingPackage ? "Uploading..." : "Upload"}
              </button>
            </div>
          </form>
        </div>
      )}

      {showDeployForm && (
        <div className="ui-modal-overlay">
          <div className="ui-modal !max-w-2xl">
            <div className="ui-modal-header">
              <h2 className="ui-modal-title">New Software Deployment</h2>
              <button
                onClick={() => setShowDeployForm(false)}
                className="ui-btn ui-btn-ghost ui-btn-sm"
              >
                <FiX />
              </button>
            </div>

            <div className="ui-modal-body">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="ui-field-label">Package *</label>
                  <select
                    value={packageId}
                    onChange={(e) => {
                      setPackageId(e.target.value);
                      setPreview(null);
                      setConfirmChecked(false);
                    }}
                    className="ui-input"
                  >
                    <option value="">Select an approved package</option>
                    {packages
                      .filter((pkg) => pkg.approval_status === "approved")
                      .map((pkg) => (
                        <option key={pkg.id} value={pkg.id}>
                          {pkg.name} {pkg.version} ({pkg.os || "any"})
                        </option>
                      ))}
                  </select>
                  {packages.filter((p) => p.approval_status === "approved")
                    .length === 0 && (
                    <p className="text-xs text-[var(--ds-warning)] mt-1">
                      No approved packages — approve a package first.
                    </p>
                  )}
                </div>

                <div>
                  <label className="ui-field-label">Action</label>
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    className="ui-input"
                  >
                    <option value="install">Install</option>
                    <option value="uninstall">Uninstall</option>
                  </select>
                </div>

                <div>
                  <label className="ui-field-label">Target scope</label>
                  <select
                    value={scope}
                    onChange={(e) => {
                      setScope(e.target.value);
                      setScopeRef("");
                      setSelectedIds([]);
                      setPreview(null);
                    }}
                    className="ui-input"
                  >
                    {SCOPES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                {scope !== "all" && scope !== "selected" && (
                  <div>
                    <label className="ui-field-label">
                      {scope === "department"
                        ? "Department"
                        : scope === "lab"
                          ? "Lab"
                          : "Location"}
                    </label>
                    <select
                      value={scopeRef}
                      onChange={(e) => {
                        setScopeRef(e.target.value);
                        setPreview(null);
                      }}
                      className="ui-input"
                    >
                      <option value="">Select...</option>
                      {(scopeValues[scope] || []).map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {scope === "selected" && (
                <div className="mt-4">
                  <label className="ui-field-label">Select computers</label>
                  <div className="max-h-48 overflow-y-auto bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-2">
                    {devices.map((device) => (
                      <label
                        key={device.id}
                        className="flex items-center gap-2 px-2 py-1 hover:bg-[var(--ds-surface-3)] cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(device.id)}
                          onChange={() => toggleDevice(device.id)}
                          className="accent-[var(--ds-accent)]"
                        />
                        <span className="text-sm">
                          {device.hostname}
                          <span className="text-[var(--ds-text-3)] text-xs ml-2">
                            {device.os || "Unknown OS"}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-4">
                <label className="ui-field-label">Description</label>
                <input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Push Chrome to Sales laptops"
                  className="ui-input"
                />
              </div>

              <div className="mt-4 flex gap-2">
                <button
                  onClick={runPreview}
                  disabled={!packageId || previewing}
                  className="ui-btn ui-btn-secondary"
                >
                  {previewing ? "Previewing..." : "Preview Targets"}
                </button>
              </div>

              {preview && (
                <div className="mt-4 bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-4">
                  <h3 className="font-semibold mb-2 text-white">
                    Preview: {preview.package_name}
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                    <div className="ui-stat !p-3">
                      <p className="text-2xl font-bold">
                        {preview.summary.total}
                      </p>
                      <p className="ui-stat-label">Total</p>
                    </div>
                    <div className="ui-stat !p-3">
                      <p className="text-2xl font-bold text-[var(--ds-success)]">
                        {preview.summary.compatible}
                      </p>
                      <p className="ui-stat-label">Compatible</p>
                    </div>
                    <div className="ui-stat !p-3">
                      <p className="text-2xl font-bold text-[var(--ds-warning)]">
                        {preview.summary.offline}
                      </p>
                      <p className="ui-stat-label">Offline (queued)</p>
                    </div>
                    <div className="ui-stat !p-3">
                      <p className="text-2xl font-bold text-[var(--ds-danger)]">
                        {preview.summary.incompatible}
                      </p>
                      <p className="ui-stat-label">Incompatible</p>
                    </div>
                  </div>

                  {preview.devices.length > 0 && (
                    <div className="mt-3 max-h-40 overflow-y-auto">
                      {preview.devices.map((device) => (
                        <div
                          key={device.device_id}
                          className="flex items-center justify-between py-1 text-sm border-b border-[var(--ds-border)]"
                        >
                          <span>
                            {device.hostname}
                            <span className="text-[var(--ds-text-3)] text-xs ml-2">
                              {device.os || "Unknown OS"}
                            </span>
                          </span>
                          <span
                            className={
                              device.compatible
                                ? "text-[var(--ds-success)] text-xs"
                                : "text-[var(--ds-danger)] text-xs"
                            }
                          >
                            {device.reason || "Compatible"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  <label className="flex items-center gap-2 mt-4 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={confirmChecked}
                      onChange={(e) => setConfirmChecked(e.target.checked)}
                      className="accent-[var(--ds-accent)] h-5 w-5"
                    />
                    <span className="text-sm text-[var(--ds-text-2)]">
                      I understand this will install software on{" "}
                      {preview.summary.compatible} computer(s)
                    </span>
                  </label>

                  <div className="flex justify-end gap-2 mt-4">
                    <button
                      onClick={() => setShowDeployForm(false)}
                      className="ui-btn ui-btn-secondary"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={runDeployment}
                      disabled={deploying || !confirmChecked}
                      className="ui-btn ui-btn-primary"
                    >
                      {deploying ? "Deploying..." : "Start Deployment"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedDeployment && (
        <div className="ui-modal-overlay">
          <div className="ui-modal !max-w-3xl">
            <div className="ui-modal-header">
              <h2 className="ui-modal-title">
                Deployment #{selectedDeployment.id}
                <span className="ml-3 align-middle">
                  <StatusBadge status={selectedDeployment.status} />
                </span>
              </h2>
              <button
                onClick={() => setSelectedDeployment(null)}
                className="ui-btn ui-btn-ghost ui-btn-sm"
              >
                <FiX />
              </button>
            </div>

            {deploymentDetail && (
              <div className="ui-modal-body">
                <p className="text-[var(--ds-text-2)]">
                  {deploymentDetail.package
                    ? `${deploymentDetail.package.name} ${deploymentDetail.package.version}`
                    : "Package deleted"}{" "}
                  — {deploymentDetail.action} — scope{" "}
                  {deploymentDetail.scope}
                  {deploymentDetail.scope_ref
                    ? `: ${deploymentDetail.scope_ref}`
                    : ""}
                </p>
                <p className="text-sm text-[var(--ds-text-3)] mt-1">
                  Created by {deploymentDetail.created_by} at{" "}
                  {deploymentDetail.created_at
                    ? new Date(deploymentDetail.created_at).toLocaleString()
                    : "-"}
                  {deploymentDetail.completed_at
                    ? ` · Completed ${new Date(
                        deploymentDetail.completed_at
                      ).toLocaleString()}`
                    : ""}
                </p>

                {(deploymentDetail.summary?.total || 0) > 0 && (
                  <div className="flex gap-3 mt-3 flex-wrap">
                    {Object.entries(deploymentDetail.summary).map(
                      ([key, value]) => (
                        <span
                          key={key}
                          className="text-xs bg-[var(--ds-surface-3)] px-2 py-1 rounded"
                        >
                          {key}: <b>{value}</b>
                        </span>
                      )
                    )}
                  </div>
                )}

                <h3 className="font-semibold mt-5 mb-2 text-white">Targets</h3>
                <div className="ui-table-wrap">
                  <table className="ui-table text-left">
                    <thead>
                      <tr>
                        <th className="px-3">Computer</th>
                        <th className="px-3">Status</th>
                        <th className="px-3">Progress</th>
                        <th className="px-3">Attempts</th>
                        <th className="px-3">Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(deploymentDetail.targets || []).map((target) => (
                        <tr key={target.id}>
                          <td className="px-3">{target.hostname}</td>
                          <td className="px-3">
                            <StatusBadge status={target.status} />
                          </td>
                          <td className="px-3">
                            <ProgressBar
                              progress={target.progress}
                              status={target.status}
                            />
                          </td>
                          <td className="px-3 text-[var(--ds-text-2)]">
                            {target.attempt_count}
                          </td>
                          <td className="px-3 text-[var(--ds-text-2)] text-sm">
                            {target.detail || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <h3 className="font-semibold mt-5 mb-2 text-white">Events</h3>
                <div className="space-y-2">
                  {deploymentEvents.length === 0 && (
                    <p className="text-[var(--ds-text-3)] text-sm">
                      No events recorded.
                    </p>
                  )}
                  {deploymentEvents.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-3 bg-[var(--ds-surface-3)] rounded-lg px-3 py-2 text-sm"
                    >
                      <span
                        className={`ui-badge ${
                          event.level === "audit"
                            ? "ui-badge-info"
                            : event.level === "warning"
                              ? "ui-badge-warning"
                              : event.level === "error"
                                ? "ui-badge-danger"
                                : "ui-badge-neutral"
                        }`}
                      >
                        {event.level}
                      </span>
                      <div>
                        <p className="text-[var(--ds-text)]">{event.message}</p>
                        <p className="text-xs text-[var(--ds-text-3)]">
                          {event.actor} ·{" "}
                          {event.created_at
                            ? new Date(event.created_at).toLocaleString()
                            : "-"}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {showGroupForm && (
        <div className="ui-modal-overlay">
          <form onSubmit={submitGroup} className="ui-modal !max-w-lg">
            <div className="ui-modal-header">
              <h2 className="ui-modal-title">
                {editingGroup
                  ? `Manage Group: ${editingGroup.name}`
                  : "New Device Group"}
              </h2>
              <button
                type="button"
                onClick={() => setShowGroupForm(false)}
                className="ui-btn ui-btn-ghost ui-btn-sm"
              >
                <FiX />
              </button>
            </div>

            <div className="ui-modal-body">
              <label className="ui-field-label">Group name</label>
              <input
                required
                value={groupForm.name}
                onChange={(e) => setGroupForm({ name: e.target.value })}
                className="ui-input mb-4"
              />

              <label className="ui-field-label">Computers in group</label>
              <div className="max-h-64 overflow-y-auto bg-[var(--ds-surface)] border border-[var(--ds-border)] rounded-lg p-2">
                {devices.length === 0 && (
                  <p className="text-[var(--ds-text-3)] text-sm p-2">
                    No devices discovered yet.
                  </p>
                )}
                {devices.map((device) => (
                  <label
                    key={device.id}
                    className="flex items-center gap-2 px-2 py-1 hover:bg-[var(--ds-surface-3)] cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={groupDevices.includes(device.id)}
                      onChange={() => toggleGroupDevice(device.id)}
                      className="accent-[var(--ds-accent)]"
                    />
                    <span className="text-sm">
                      {device.hostname}
                      <span className="text-[var(--ds-text-3)] text-xs ml-2">
                        {device.os || "Unknown OS"}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="ui-modal-footer">
              <button
                type="button"
                onClick={() => setShowGroupForm(false)}
                className="ui-btn ui-btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingGroup}
                className="ui-btn ui-btn-primary"
              >
                {savingGroup ? "Saving..." : "Save"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
