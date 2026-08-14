import { useState, useEffect } from "react";
import api from "../services/api";

const SECRET_MARKER = "********";

function Field({ spec, value, onChange, disabled }) {
  const label = spec.label;

  if (spec.type === "bool") {
    return (
      <label className="flex items-center justify-between py-2 cursor-pointer">
        <span className="text-[var(--ds-text-2)]">{label}</span>
        <input
          type="checkbox"
          checked={Boolean(value)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="h-5 w-5 accent-[var(--ds-accent)]"
        />
      </label>
    );
  }

  if (spec.type === "select") {
    return (
      <div className="mb-4">
        <label className="ui-field-label">{label}</label>
        <select
          value={value || ""}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className="ui-input"
        >
          {spec.choices.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (spec.type === "list") {
    return (
      <div className="mb-4">
        <label className="ui-field-label">{label}</label>
        <div className="space-y-2">
          {(value || []).map((item, index) => (
            <div key={index} className="flex gap-2">
              <input
                type="text"
                value={item}
                disabled={disabled}
                onChange={(e) => {
                  const next = [...(value || [])];
                  next[index] = e.target.value;
                  onChange(next);
                }}
                className="ui-input flex-1"
              />
              <button
                type="button"
                disabled={disabled}
                onClick={() => {
                  onChange((value || []).filter((_, i) => i !== index));
                }}
                className="ui-btn ui-btn-danger ui-btn-sm"
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            disabled={disabled}
            onClick={() => onChange([...(value || []), ""])}
            className="ui-btn ui-btn-secondary ui-btn-sm"
          >
            + Add {spec.item_label || "item"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <label className="ui-field-label">{label}</label>
      <input
        type={spec.type === "secret" ? "password" : "text"}
        value={value ?? ""}
        disabled={disabled}
        placeholder={
          spec.type === "secret" && spec.is_set
            ? SECRET_MARKER + " (stored - leave blank to keep)"
            : spec.optional
            ? "(optional)"
            : ""
        }
        onChange={(e) => onChange(e.target.value)}
        className="ui-input"
      />
      {spec.help && (
        <p className="text-[var(--ds-text-3)] text-xs mt-1">{spec.help}</p>
      )}
    </div>
  );
}

function SectionCard({
  section,
  values,
  setValue,
  onSave,
  onTest,
  saving,
  testing,
}) {
  return (
    <div className="ui-card p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="ui-card-title">{section.label}</h2>
        {["telegram", "email"].includes(section.key) && (
          <button
            type="button"
            disabled={testing}
            onClick={() => onTest(section.key)}
            className="ui-btn ui-btn-secondary ui-btn-sm"
          >
            {testing ? "Sending..." : "Test"}
          </button>
        )}
      </div>
      <p className="text-[var(--ds-text-3)] text-sm mb-6">{section.description}</p>
      <div>
        {section.keys.map((spec) => (
          <Field
            key={spec.key}
            spec={spec}
            value={values[spec.key]}
            disabled={saving}
            onChange={(next) => setValue(spec.key, next)}
          />
        ))}
      </div>
      <button
        type="button"
        disabled={saving}
        onClick={() => onSave()}
        className="ui-btn ui-btn-primary mt-2"
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </div>
  );
}

export default function SettingsCenter({ showMessage }) {
  const [sections, setSections] = useState([]);
  const [values, setValues] = useState({});
  const [saving, setSaving] = useState({});
  const [testing, setTesting] = useState({});
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);

  function setValue(sectionKey, key, next) {
    setValues((prev) => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        [key]: next,
      },
    }));
  }

  function refreshAll() {
    return api
      .get("/settings-center")
      .then((response) => {
        const data = response.data.sections || [];
        setSections(data);

        const next = {};
        data.forEach((section) => {
          next[section.key] = { ...(section.values || {}) };
        });
        setValues(next);
      })
      .then(() =>
        api
          .get("/settings-center/audit")
          .then((response) => setAudit(response.data.items || []))
      )
      .catch((err) => {
        if (showMessage) {
          showMessage(
            "error",
            err?.response?.data?.detail || "Failed to reload settings"
          );
        }
      });
  }

  useEffect(() => {
    api
      .get("/settings-center")
      .then((response) => {
        const data = response.data.sections || [];
        setSections(data);

        const next = {};
        data.forEach((section) => {
          next[section.key] = { ...(section.values || {}) };
        });
        setValues(next);
      })
      .catch((err) => {
        if (showMessage) {
          showMessage(
            "error",
            err?.response?.data?.detail || "Failed to load settings"
          );
        }
      })
      .finally(() => setLoading(false));

    api
      .get("/settings-center/audit")
      .then((response) => setAudit(response.data.items || []))
      .catch(() => {});
  }, [showMessage]);

  async function saveSection(section) {
    setSaving((prev) => ({ ...prev, [section.key]: true }));

    const payload = {};
    section.keys.forEach((spec) => {
      if (spec.type === "int") {
        payload[spec.key] = Number(values[section.key][spec.key]);
      } else {
        payload[spec.key] = values[section.key][spec.key];
      }
    });

    try {
      await api.put(`/settings-center/${section.key}`, { values: payload });
      if (showMessage) {
        showMessage("success", `${section.label} settings saved`);
      }
      await refreshAll();
    } catch (err) {
      if (showMessage) {
        showMessage(
          "error",
          err?.response?.data?.detail || `Failed to save ${section.label}`
        );
      }
    } finally {
      setSaving((prev) => ({ ...prev, [section.key]: false }));
    }
  }

  async function testChannel(channel) {
    setTesting((prev) => ({ ...prev, [channel]: true }));

    try {
      await api.post("/settings-center/test", { channel });
      if (showMessage) {
        showMessage("success", `${channel} test message sent`);
      }
      await refreshAll();
    } catch (err) {
      if (showMessage) {
        showMessage(
          "error",
          err?.response?.data?.detail || `${channel} test failed`
        );
      }
    } finally {
      setTesting((prev) => ({ ...prev, [channel]: false }));
    }
  }

  if (loading) {
    return (
      <div className="ui-loading">
        <span className="ui-spinner" /> Loading configuration center...
      </div>
    );
  }

  return (
    <div>
      <div className="grid lg:grid-cols-2 gap-8">
        {sections.map((section) => (
          <SectionCard
            key={section.key}
            section={section}
            values={values[section.key] || {}}
            setValue={(key, next) => setValue(section.key, key, next)}
            onSave={() => saveSection(section)}
            onTest={testChannel}
            saving={Boolean(saving[section.key])}
            testing={Boolean(testing[section.key])}
          />
        ))}
      </div>

      <div className="ui-card p-6 mt-8">
        <h2 className="ui-card-title mb-4">Change Log</h2>
        {audit.length === 0 ? (
          <p className="text-[var(--ds-text-3)] text-sm">
            No configuration changes recorded yet.
          </p>
        ) : (
          <div className="ui-table-wrap">
            <table className="ui-table text-sm">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Section</th>
                  <th>Key</th>
                  <th>Old</th>
                  <th>New</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((entry) => (
                  <tr key={entry.id}>
                    <td className="text-[var(--ds-text-3)]">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="font-medium text-white">{entry.username}</td>
                    <td>{entry.action}</td>
                    <td>{entry.section}</td>
                    <td>{entry.key}</td>
                    <td className="text-[var(--ds-text-3)]">{entry.old_value || "-"}</td>
                    <td className="text-[var(--ds-text-3)]">{entry.new_value || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
