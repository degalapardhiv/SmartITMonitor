import { useEffect, useState } from "react";
import { FiLock } from "react-icons/fi";
import api from "../services/api";

const POLICIES = [
  {
    value: "approval_required",
    label: "Approval Required",
    description: "New USB devices require administrator approval.",
  },
  {
    value: "allow",
    label: "Allow",
    description: "USB connections are allowed during Exam Mode.",
  },
  {
    value: "block",
    label: "Block",
    description: "USB connections are blocked by policy.",
  },
];

export default function ExamMode() {
  const [enabled, setEnabled] = useState(false);
  const [usbPolicy, setUsbPolicy] = useState("approval_required");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadSettings = async () => {
    try {
      const response = await api.get("/exam-mode");

      setEnabled(Boolean(response.data?.enabled));
      setUsbPolicy(response.data?.usb_policy || "approval_required");

      setError("");
    } catch (err) {
      console.error("Exam Mode load failed:", err);
      setError(
        err?.response?.status === 401
          ? "Please login again."
          : "Unable to load Exam Mode settings."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    async function sync() {
      await loadSettings();
    }
    sync();
  }, []);

  const saveSettings = async () => {
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const response = await api.put("/exam-mode", {
        enabled,
        usb_policy: usbPolicy,
      });

      setEnabled(Boolean(response.data?.enabled));
      setUsbPolicy(response.data?.usb_policy || "approval_required");

      setMessage("Exam Mode settings saved.");
    } catch (err) {
      console.error("Exam Mode save failed:", err);
      setError(err?.response?.data?.detail || "Unable to save Exam Mode settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="ui-page-header !mb-6">
          <div>
            <h1 className="ui-page-title">Exam Mode</h1>
            <p className="ui-page-subtitle">Security policy for lab computers during examinations.</p>
          </div>
        </div>
        <div className="ui-loading">
          <span className="ui-spinner" /> Loading settings...
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "900px" }}>
      <div className="ui-page-header !mb-6">
        <div>
          <h1 className="ui-page-title">Exam Mode</h1>
          <p className="ui-page-subtitle">
            Configure the security policy for authorized managed lab computers during examinations.
          </p>
        </div>
      </div>

      {message && (
        <div className="mb-5 rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-[#46d369]">
          {message}
        </div>
      )}

      {error && (
        <div className="mb-5 rounded-lg border border-red-600/40 bg-red-600/15 p-4 text-[#e6797e]">
          {error}
        </div>
      )}

      <div className="ui-card p-6 mb-5">
        <h2 className="ui-card-title mb-4">Exam Mode Status</h2>

        <label className="flex items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
            className="w-4 h-4 accent-[var(--ds-accent)]"
          />
          <strong className="text-white">
            {enabled ? "Exam Mode Enabled" : "Exam Mode Disabled"}
          </strong>
          <span className={`ui-badge ${enabled ? "ui-badge-success" : "ui-badge-neutral"}`}>
            {enabled ? "Active" : "Inactive"}
          </span>
        </label>
      </div>

      <div className="ui-card p-6 mb-5">
        <h2 className="ui-card-title mb-4">USB Policy</h2>

        <div className="grid gap-3">
          {POLICIES.map((policy) => (
            <label
              key={policy.value}
              className={`flex gap-3 items-start p-4 rounded-lg border cursor-pointer transition ${
                usbPolicy === policy.value
                  ? "border-[var(--ds-border-strong)] bg-[var(--ds-surface-3)]"
                  : "border-[var(--ds-border)] bg-transparent hover:bg-white/[0.03]"
              }`}
            >
              <input
                type="radio"
                name="usb-policy"
                value={policy.value}
                checked={usbPolicy === policy.value}
                onChange={(event) => setUsbPolicy(event.target.value)}
                className="mt-1 accent-[var(--ds-accent)]"
              />

              <span>
                <strong className="text-white">{policy.label}</strong>
                <br />
                <small className="text-[var(--ds-text-3)]">{policy.description}</small>
              </span>
            </label>
          ))}
        </div>
      </div>

      <button
        type="button"
        className="ui-btn ui-btn-primary"
        disabled={saving}
        onClick={saveSettings}
      >
        <FiLock /> {saving ? "Saving..." : "Save Policy"}
      </button>
    </div>
  );
}