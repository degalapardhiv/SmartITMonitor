import { useEffect, useState, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { FiMenu, FiBell, FiLogOut, FiUser, FiShield, FiChevronDown } from "react-icons/fi";
import { useAuth } from "../../context/auth-context";
import { useSocketStatus } from "../../hooks/useWebSocket";
import api from "../../services/api";

const PAGE_TITLES = {
  "/": "Dashboard",
  "/devices": "Devices",
  "/threats": "Threat Protection",
  "/alert-center": "Alert Center",
  "/alerts": "Alerts",
  "/endpoint-activity": "Endpoint Activity",
  "/network-discovery": "Network Discovery",
  "/software-deployment": "Software Deployment",
  "/os-deployment": "OS Deployment",
  "/exam-mode": "Exam Mode",
  "/usb-approval": "USB Approval",
  "/cctv": "CCTV",
  "/departments": "Departments",
  "/lab2": "Labs",
  "/reports": "Reports",
  "/settings": "Settings",
  "/email-history": "Email History",
  "/notification-history": "Notification History",
};

const WS_META = {
  open: { label: "LIVE", cls: "text-[#46d369] border-green-500/30 bg-green-500/10", dot: "bg-[#46d369]", pulse: true },
  connected: { label: "LIVE", cls: "text-[#46d369] border-green-500/30 bg-green-500/10", dot: "bg-[#46d369]", pulse: true },
  connecting: { label: "CONNECTING", cls: "text-[#e3b341] border-yellow-500/30 bg-yellow-500/10", dot: "bg-[#e3b341]" },
  reconnecting: { label: "RECONNECTING", cls: "text-[#e3b341] border-yellow-500/30 bg-yellow-500/10", dot: "bg-[#e3b341]" },
  error: { label: "CONNECTION ERROR", cls: "text-[#e6797e] border-red-500/30 bg-red-500/10", dot: "bg-[#e6797e]" },
  disconnected: { label: "OFFLINE", cls: "text-[#e6797e] border-red-500/30 bg-red-500/10", dot: "bg-[#e6797e]" },
  idle: { label: "STANDBY", cls: "text-[#5b6b80] border-white/10 bg-white/5", dot: "bg-[#5b6b80]" },
};

function Navbar({ onMenuClick }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { role, username, logoutUser } = useAuth();
  const wsStatus = useSocketStatus();

  const [notifCount, setNotifCount] = useState(0);
  const [userOpen, setUserOpen] = useState(false);
  const userRef = useRef(null);

  useEffect(() => {
    let active = true;
    api
      .get("/alerts", { params: { limit: 100 } })
      .then((res) => {
        if (!active) return;
        const alerts = Array.isArray(res.data) ? res.data : [];
        setNotifCount(
          alerts.filter(
            (a) => !a.status || String(a.status).toUpperCase() !== "RESOLVED"
          ).length
        );
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [location.pathname]);

  useEffect(() => {
    function onClick(e) {
      if (userRef.current && !userRef.current.contains(e.target)) {
        setUserOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function handleLogout() {
    logoutUser();
    navigate("/login");
  }

  const meta = WS_META[wsStatus] || WS_META.idle;
  const title =
    PAGE_TITLES[location.pathname] ||
    (location.pathname.startsWith("/devices/")
      ? "Device Details"
      : "Operations Dashboard");

  return (
    <header className="h-16 flex-none sticky top-0 z-30 flex items-center justify-between gap-4 px-4 sm:px-6 bg-[#0f1319]/85 backdrop-blur border-b border-white/10">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-md text-[#a5b2c4] hover:text-white hover:bg-white/5"
          aria-label="Open menu"
        >
          <FiMenu className="text-xl" />
        </button>

        <div className="min-w-0">
          <h1 className="text-[17px] sm:text-[19px] font-bold tracking-tight truncate">
            {title}
          </h1>
          <p className="text-[11px] text-[#8a98ac] hidden sm:block">
            SmartITMonitor · Security Operations Center
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div
          className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border ${meta.cls}`}
          title={`WebSocket: ${wsStatus}`}
        >
          <span className={`relative flex h-2 w-2 ${meta.dot} rounded-full`}>
            {meta.pulse && (
              <span className={`absolute inline-flex h-full w-full ${meta.dot} rounded-full opacity-60 animate-ping`} />
            )}
          </span>
          <span className="text-[11px] font-semibold tracking-wide">{meta.label}</span>
        </div>

        <Link
          to="/alert-center"
          className="relative p-2 rounded-md text-[#a5b2c4] hover:text-white hover:bg-white/5"
          title="Active alerts"
        >
          <FiBell className="text-xl" />
          {notifCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[17px] h-[17px] px-1 rounded-full bg-[#c22a32] text-white text-[10px] font-bold flex items-center justify-center border border-black/40">
              {notifCount > 99 ? "99+" : notifCount}
            </span>
          )}
        </Link>

        <div className="relative" ref={userRef}>
          <button
            onClick={() => setUserOpen((v) => !v)}
            className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-white/5"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#a4232a] to-[#d6454d] flex items-center justify-center text-white font-bold text-sm">
              {(username || "U").charAt(0).toUpperCase()}
            </div>
            <div className="hidden sm:block text-left leading-tight">
              <p className="text-[13px] font-semibold text-white max-w-[120px] truncate">
                {username || "User"}
              </p>
              <p className="text-[11px] text-[#e6797e] capitalize">{role || "viewer"}</p>
            </div>
            <FiChevronDown className="text-sm text-[#5b6b80] hidden sm:block" />
          </button>

          {userOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border border-white/10 bg-[#141922] shadow-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-white/10">
                <p className="text-sm font-semibold text-white">{username || "User"}</p>
                <p className="text-[11px] text-[#8a98ac] capitalize">
                  {role === "admin" ? "Administrator" : "Viewer"}
                </p>
              </div>

              <div className="px-2 py-2">
                <Link
                  to="/settings"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] text-[#a5b2c4] hover:text-white hover:bg-white/5"
                >
                  <FiUser className="text-[15px]" /> Profile & Settings
                </Link>
                <Link
                  to="/threats"
                  className="flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] text-[#a5b2c4] hover:text-white hover:bg-white/5"
                >
                  <FiShield className="text-[15px]" /> Threat Protection
                </Link>
              </div>

              <div className="border-t border-white/10 px-2 py-2">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] text-[#e6797e] hover:bg-red-600/10"
                >
                  <FiLogOut className="text-[15px]" /> Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Navbar;