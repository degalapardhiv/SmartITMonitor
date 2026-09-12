import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiShield, FiUser, FiLock, FiEye, FiEyeOff, FiActivity, FiServer, FiWifi, FiZap } from "react-icons/fi";

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
    <div className="min-h-screen flex bg-[var(--ds-bg)]">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0c4a6e]/60 via-[#0b0f1a] to-[#064e3b]/40" />
        <div className="absolute inset-0" style={{
          backgroundImage: "radial-gradient(circle at 30% 40%, rgba(6, 182, 212, 0.12), transparent 60%), radial-gradient(circle at 70% 80%, rgba(16, 185, 129, 0.08), transparent 50%)"
        }} />

        <div className="relative z-10 flex flex-col justify-center px-16 max-w-lg">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0891b2] to-[#06b6d4] flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <FiShield className="text-xl" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">SmartITMonitor</h1>
              <p className="text-sm text-cyan-300/60">Security Operations Center</p>
            </div>
          </div>

          <h2 className="text-4xl font-bold text-white leading-tight mb-4">
            Enterprise IT Monitoring &amp; Security
          </h2>

          <p className="text-lg text-slate-300/70 mb-10 leading-relaxed">
            Real-time device monitoring, threat detection, endpoint protection, and SOC-grade alerting — all from a single dashboard.
          </p>

          <div className="space-y-4">
            {[
              { icon: FiServer, text: "Real-time device monitoring" },
              { icon: FiWifi, text: "Network discovery & protection" },
              { icon: FiZap, text: "Instant threat response" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 text-slate-300/80">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                  <Icon className="text-cyan-400 text-sm" />
                </div>
                <span className="text-sm font-medium">{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Decorative grid */}
        <div className="absolute bottom-0 right-0 w-96 h-96 opacity-[0.03]" style={{
          backgroundImage: "linear-gradient(rgba(6, 182, 212, 1) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 1) 1px, transparent 1px)",
          backgroundSize: "40px 40px"
        }} />
      </div>

      {/* Right Panel - Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 relative">
        <div className="absolute inset-0" style={{
          backgroundImage: "radial-gradient(circle at 50% 0%, rgba(6, 182, 212, 0.06), transparent 50%)"
        }} />

        <div className="w-full max-w-[420px] relative z-10">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#0891b2] to-[#06b6d4] flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <FiShield className="text-lg" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">SmartITMonitor</h1>
              <p className="text-xs text-cyan-300/60">Security Operations Center</p>
            </div>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white mb-1">Welcome back</h2>
            <p className="text-sm text-slate-400">Sign in to your security dashboard</p>
          </div>

          {error && (
            <div className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-300 text-sm backdrop-blur-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <label className="block text-[13px] font-semibold mb-2 text-slate-400">
              Username
            </label>

            <div className="relative mb-4">
              <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
              <input
                type="text"
                className="ui-input !pl-10 !bg-[#111827]/80"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            <label className="block text-[13px] font-semibold mb-2 text-slate-400">
              Password
            </label>

            <div className="relative mb-6">
              <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
              <input
                type={showPassword ? "text" : "password"}
                className="ui-input !pl-10 !pr-10 !bg-[#111827]/80"
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
                className="absolute right-0 top-0 h-full px-3 flex items-center text-slate-500 hover:text-slate-300 bg-transparent shadow-none"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="ui-btn ui-btn-primary w-full !py-3 !text-[15px]"
            >
              {loading ? (
                <>
                  <span className="ui-spinner !w-4 !h-4 !border-2" style={{ borderTopColor: "#fff" }} />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <div className="flex items-center justify-center gap-2 mt-8 text-slate-500 text-xs">
            <FiActivity size={14} />
            <span>Live monitoring · Endpoint protection · SOC alerts</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
