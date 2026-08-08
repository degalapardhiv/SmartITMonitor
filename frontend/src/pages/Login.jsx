import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login } from "../services/auth";
import { useAuth } from "../context/AuthContext";

function Login() {
  const navigate = useNavigate();
  const { loginUser } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const data = await login(username, password);

      console.log("Login Success:", data);

      loginUser(
        data.access_token,
        data.role, username
      );

      navigate("/");

    } catch (err) {

      console.error("Login Error:", err);

      if (err.response) {
        setError(
          err.response.data?.detail ||
          `Server Error (${err.response.status})`
        );
      } else if (err.request) {
        setError(
          "Cannot connect to backend server."
        );
      } else {
        setError(err.message);
      }

    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">

      <form
        onSubmit={handleLogin}
        className="w-[420px] bg-slate-800 rounded-xl shadow-xl p-8"
      >

        <h1 className="text-3xl font-bold text-center text-cyan-400 mb-2">
          Smart IT Monitor
        </h1>

        <p className="text-center text-gray-400 mb-8">
          Sign in to continue
        </p>

        {error && (
          <div className="mb-5 rounded bg-red-600 p-3 text-white">
            {error}
          </div>
        )}

        <label className="block mb-2 font-semibold">
          Username
        </label>

        <input
          type="text"
          className="w-full rounded bg-slate-700 p-3 text-white mb-5 outline-none focus:ring-2 focus:ring-cyan-500"
          placeholder="Enter username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />

        <label className="block mb-2 font-semibold">
          Password
        </label>

        <input
          type="password"
          className="w-full rounded bg-slate-700 p-3 text-white mb-8 outline-none focus:ring-2 focus:ring-cyan-500"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-cyan-600 p-3 font-bold hover:bg-cyan-700 disabled:bg-gray-600"
        >
          {loading ? "Logging in..." : "Login"}
        </button>

      </form>

    </div>
  );
}

export default Login;
