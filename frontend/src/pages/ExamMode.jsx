import { useEffect, useState } from "react";
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
      setUsbPolicy(
        response.data?.usb_policy || "approval_required"
      );

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
      setUsbPolicy(
        response.data?.usb_policy || "approval_required"
      );

      setMessage("Exam Mode settings saved.");
    } catch (err) {
      console.error("Exam Mode save failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Unable to save Exam Mode settings."
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "24px" }}>
        <h1>Exam Mode</h1>
        <p>Loading settings...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px", maxWidth: "900px" }}>
      <h1>Exam Mode</h1>

      <p>
        Configure the security policy for authorized managed
        lab computers during examinations.
      </p>

      {message && (
        <div style={{ marginBottom: "16px" }}>
          {message}
        </div>
      )}

      {error && (
        <div style={{ marginBottom: "16px" }}>
          {error}
        </div>
      )}

      <section
        style={{
          border: "1px solid #333",
          borderRadius: "12px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <h2>Exam Mode Status</h2>

        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) =>
              setEnabled(event.target.checked)
            }
          />

          <strong>
            {enabled
              ? "Exam Mode Enabled"
              : "Exam Mode Disabled"}
          </strong>
        </label>
      </section>

      <section
        style={{
          border: "1px solid #333",
          borderRadius: "12px",
          padding: "20px",
          marginBottom: "20px",
        }}
      >
        <h2>USB Policy</h2>

        <div
          style={{
            display: "grid",
            gap: "12px",
          }}
        >
          {POLICIES.map((policy) => (
            <label
              key={policy.value}
              style={{
                display: "flex",
                gap: "12px",
                padding: "14px",
                border: "1px solid #444",
                borderRadius: "8px",
                cursor: "pointer",
              }}
            >
              <input
                type="radio"
                name="usb-policy"
                value={policy.value}
                checked={usbPolicy === policy.value}
                onChange={(event) =>
                  setUsbPolicy(event.target.value)
                }
              />

              <span>
                <strong>{policy.label}</strong>
                <br />
                <small>{policy.description}</small>
              </span>
            </label>
          ))}
        </div>
      </section>

      <button
        type="button"
        disabled={saving}
        onClick={saveSettings}
      >
        {saving ? "Saving..." : "Save Policy"}
      </button>
    </div>
  );
}
