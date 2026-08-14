import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiShield, FiUser, FiLock, FiEye, FiEyeOff, FiActivity } from "react-icons/fi";

import { login } from "../services/auth";
import { useAuth } from "../context/auth-context";

function Login() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const data = await login(username, password);

      loginUser(data.access_token, data.role, username);

      navigate("/");
    } catch (err) {
      console.error("Login Error:", err);

      if (err.response) {
        setError(
          err.response.data?.detail ||
            `Server Error (${err.response.status})`
        );
      } else if (err.request) {
        setError("Cannot connect to backend server.");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-[#0a0d12]"
      style={{
        backgroundImage:
          "radial-gradient(circle at 20% -10%, rgba(165, 178, 196, 0.05), transparent 40%), radial-gradient(circle at 90% 110%, rgba(214, 69, 77, 0.08), transparent 45%)",
      }}
    >
      <form
        onSubmit={handleLogin}
        className="w-full max-w-[420px] ui-card p-8"
      >
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#a4232a] to-[#d6454d] flex items-center justify-center text-white shadow-lg mb-5">
            <FiShield className="text-2xl" />
          </div>

          <h1 className="text-2xl font-bold text-white text-center">
            Smart IT Monitor
          </h1>

          <p className="text-sm text-[var(--ds-text-2)] text-center mt-1">
            Security Operations Center
          </p>
        </div>

        {error && (
          <div className="mb-5 rounded-lg border border-[var(--ds-accent)]/40 bg-[var(--ds-accent-soft)] p-3 text-[#e6797e] text-sm">
            {error}
          </div>
        )}

        <label className="block text-[13px] font-semibold mb-2 text-[var(--ds-text-2)]">
          Username
        </label>

        <div className="relative mb-5">
          <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-3)]" size={16} />
          <input
            type="text"
            className="ui-input !pl-10"
            placeholder="Enter username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </div>

        <label className="block text-[13px] font-semibold mb-2 text-[var(--ds-text-2)]">
          Password
        </label>

        <div className="relative mb-8">
          <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ds-text-3)]" size={16} />
          <input
            type={showPassword ? "text" : "password"}
            className="ui-input !pl-10 !pr-10"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-0 top-0 h-full px-3 flex items-center text-[var(--ds-text-3)] hover:text-[var(--ds-text-2)] bg-transparent shadow-none"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="ui-btn ui-btn-primary w-full !py-3"
        >
          {loading ? (
            <>
              <span className="ui-spinner !w-4 !h-4 !border-2" style={{ borderTopColor: "#fff" }} />
              Logging in...
            </>
          ) : (
            "Sign in"
          )}
        </button>

        <div className="flex items-center gap-2 mt-8 text-[var(--ds-text-3)] text-xs">
          <FiActivity size={14} />
          <span>Live monitoring · Endpoint protection · SOC alerts</span>
        </div>
      </form>
    </div>
  );
}

export default Login;