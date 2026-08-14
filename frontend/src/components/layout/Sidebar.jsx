import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  FiGrid,
  FiMonitor,
  FiActivity,
  FiRadio,
  FiShield,
  FiBell,
  FiAlertOctagon,
  FiHardDrive,
  FiDownload,
  FiCpu,
  FiLock,
  FiVideo,
  FiBriefcase,
  FiTerminal,
  FiFileText,
  FiSettings,
  FiMail,
  FiMessageSquare,
  FiChevronDown,
  FiChevronLeft,
  FiChevronRight,
  FiShieldOff,
  FiGlobe,
} from "react-icons/fi";
import { useAuth } from "../../context/auth-context";

const NAV_GROUPS = [
  {
    title: "Operations",
    items: [
      { to: "/", label: "Dashboard", icon: FiGrid },
      { to: "/devices", label: "Devices", icon: FiMonitor },
      { to: "/endpoint-activity", label: "Endpoint Activity", icon: FiActivity },
      { to: "/network-discovery", label: "Network Discovery", icon: FiRadio },
    ],
  },
  {
    title: "Security",
    accent: true,
    items: [
      { to: "/threats", label: "Threat Protection", icon: FiShield },
      { to: "/web-access", label: "Web Access Control", icon: FiGlobe, admin: true },
      { to: "/alert-center", label: "Alert Center", icon: FiAlertOctagon },
      { to: "/alerts", label: "Alerts", icon: FiBell },
      { to: "/usb-approval", label: "USB Approval", icon: FiHardDrive, admin: true },
    ],
  },
  {
    title: "Deployments",
    admin: true,
    items: [
      { to: "/software-deployment", label: "Software Deployment", icon: FiDownload, admin: true },
      { to: "/os-deployment", label: "OS Deployment", icon: FiCpu, admin: true },
      { to: "/exam-mode", label: "Exam Mode", icon: FiLock, admin: true },
    ],
  },
  {
    title: "Facilities",
    items: [
      { to: "/cctv", label: "CCTV", icon: FiVideo },
      { to: "/departments", label: "Departments", icon: FiBriefcase },
      { to: "/lab2", label: "Labs", icon: FiTerminal },
    ],
  },
  {
    title: "Reports & Admin",
    items: [
      { to: "/reports", label: "Reports", icon: FiFileText },
      { to: "/settings", label: "Settings", icon: FiSettings, admin: true },
      { to: "/email-history", label: "Email History", icon: FiMail, admin: true },
      { to: "/notification-history", label: "Notification History", icon: FiMessageSquare, admin: true },
    ],
  },
];

function Sidebar({ mobileOpen, onClose }) {
  const { role } = useAuth();
  const isAdmin = role === "admin";
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState(() =>
    new Set(NAV_GROUPS.map((g) => g.title))
  );

  function toggleGroup(title) {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });
  }

  const content = (
    <aside
      className={`h-full flex flex-col bg-slate-900 border-r border-slate-700/60 transition-all ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      <div
        className={`flex items-center gap-2.5 px-4 py-5 border-b border-slate-700/60 ${
          collapsed ? "justify-center" : ""
        }`}
      >
        <span className="w-9 h-9 shrink-0 rounded-lg bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
          <FiShieldOff className="text-lg" />
        </span>
        {!collapsed && (
          <div className="leading-tight min-w-0">
            <p className="font-bold text-[15px] tracking-tight truncate">
              SmartITMonitor
            </p>
            <p className="text-[11px] text-slate-500">Security & IT Ops</p>
          </div>
        )}
      </div>

      <button
        onClick={() => setCollapsed((c) => !c)}
        className="hidden lg:flex items-center justify-center gap-1 mx-3 mt-3 py-1.5 text-xs text-slate-500 hover:text-slate-300 rounded-md hover:bg-white/5"
      >
        {collapsed ? <FiChevronRight /> : <FiChevronLeft />}
        {!collapsed && "Collapse"}
      </button>

      <nav className="flex-1 overflow-y-auto px-2.5 py-4 space-y-4">
        {NAV_GROUPS.map((group) => {
          if (group.admin && !isAdmin) return null;
          const visible = group.items.filter((it) => !it.admin || isAdmin);
          if (visible.length === 0) return null;

          const open = !collapsed && openGroups.has(group.title);

          return (
            <div key={group.title}>
              {!collapsed && (
                <button
                  onClick={() => toggleGroup(group.title)}
                  className="w-full flex items-center justify-between px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500 hover:text-slate-300"
                >
                  {group.title}
                  <FiChevronDown
                    className={`transition-transform ${
                      open ? "" : "-rotate-90"
                    }`}
                  />
                </button>
              )}

              {open && (
                <div className="mt-1 space-y-0.5">
                  {visible.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        end={item.to === "/"}
                        onClick={onClose}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-2.5 py-2 rounded-lg text-[13.5px] font-medium transition ${
                            collapsed ? "justify-center" : ""
                          } ${
                            isActive
                              ? "bg-red-600/15 text-red-300 border border-red-500/30"
                              : "text-slate-400 hover:bg-white/5 hover:text-slate-100 border border-transparent"
                          }`
                        }
                      >
                        <Icon
                          className={`text-[17px] shrink-0 ${
                            item.accent ? "text-red-400" : ""
                          }`}
                        />
                        {!collapsed && item.label}
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="px-4 py-4 border-t border-slate-700/60">
          <p className="text-[11px] text-slate-600 leading-relaxed">
            Signed in as {role === "admin" ? "Administrator" : "Viewer"}
          </p>
        </div>
      )}
    </aside>
  );

  if (!mobileOpen) return content;

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute inset-y-0 left-0 w-64">{content}</div>
      <button
        onClick={onClose}
        className="absolute top-4 left-[17rem] text-white/70 hover:text-white text-2xl"
        aria-label="Close menu"
      >
        <FiChevronRight />
      </button>
    </div>
  );
}

export default Sidebar;
