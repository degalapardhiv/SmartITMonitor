import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/auth-context";

function Navbar() {

  const [menuOpen,setMenuOpen] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  const { role, username, logoutUser } = useAuth();

  function handleLogout() {
    logoutUser();
    navigate("/login");
  }

  const linkClass = (path) =>
    location.pathname === path
      ? "px-4 py-2 rounded-lg bg-cyan-600 text-white font-semibold"
      : "px-4 py-2 rounded-lg text-gray-300 hover:bg-slate-700 transition";

  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-8 py-4">

      <div className="flex items-center justify-between flex-wrap">

        {/* Logo */}

        <div>

          <h1 className="text-2xl font-bold text-cyan-400">
            Smart IT Monitor
          </h1>

          <p className="text-sm text-gray-400">
            Enterprise Monitoring Dashboard
          </p>

        </div>


        <button
          onClick={()=>setMenuOpen(!menuOpen)}
          className="md:hidden bg-slate-700 px-4 py-2 rounded"
        >
          ☰
        </button>


        {/* Navigation */}

        <div className={`flex items-center gap-2 ${
          menuOpen
          ? "flex"
          : "hidden"
        } md:flex`}>

          <Link
            to="/"
            className={linkClass("/")}
          >
            Dashboard
          </Link>

          <Link
            to="/devices"
            className={linkClass("/devices")}
          >
            Devices
          </Link>

          <Link
            to="/departments"
            className={linkClass("/departments")}
          >
            Departments
          </Link>

          <Link
            to="/alerts"
            className={linkClass("/alerts")}
          >
            Alerts
          </Link>

          <Link
            to="/reports"
            className={linkClass("/reports")}
          >
            Reports
          </Link>

          <Link
            to="/network-discovery"
            className={linkClass("/network-discovery")}
          >
            Network
          </Link>

          <Link
            to="/usb-approval"
            className={linkClass("/usb-approval")}
          >
            USB
          </Link>

          <Link
            to="/exam-mode"
            className={linkClass("/exam-mode")}
          >
            Exam Mode
          </Link>

          <Link
            to="/settings"
            className={linkClass("/settings")}
          >
            Settings
          </Link>

        </div>

        {/* User */}

        <div className="flex items-center gap-4">

          <div className="flex items-center gap-3">

            <div className="w-10 h-10 bg-cyan-600 rounded-full flex items-center justify-center text-white font-bold">

              {
                username
                ? username.charAt(0).toUpperCase()
                : "U"
              }

            </div>


            <div className="text-right">

              <p className="text-white font-semibold">
                {username || "User"}
              </p>

              <p className="text-sm text-cyan-400">
                {role || "Guest"}
              </p>

            </div>

          </div>

          <button
            onClick={handleLogout}
            className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg text-white font-semibold transition"
          >
            Logout
          </button>

        </div>

      </div>

    </nav>
  );
}

export default Navbar;
