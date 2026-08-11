import { NavLink } from "react-router-dom";

function Sidebar() {
  const menu = [
    { title: "Dashboard", path: "/" },
    { title: "Devices", path: "/devices" },
    { title: "Departments", path: "/departments" },
    { title: "Alerts", path: "/alerts" },
    { title: "Alert Center", path: "/alert-center" },
    { title: "Reports", path: "/reports" },
    { title: "Network Discovery", path: "/network-discovery" },
    { title: "USB Approval", path: "/usb-approval" },
    { title: "Exam Mode", path: "/exam-mode" },
    { title: "Lab 2", path: "/lab2" },
    { title: "Settings", path: "/settings" },
    { title: "Email History", path: "/email-history" },
    { title: "Notification History", path: "/notification-history" },
  ];

  return (
    <div className="w-64 min-h-screen bg-slate-900 text-white">

      <div className="p-6 border-b border-slate-700">

        <h1 className="text-2xl font-bold text-cyan-400">
          Smart IT Monitor
        </h1>

        <p className="text-gray-400 text-sm mt-2">
          Enterprise Dashboard
        </p>

      </div>

      <nav className="p-4 space-y-2">

        {menu.map((item) => (

          <NavLink
            key={item.title}
            to={item.path}
            className={({ isActive }) =>
              `block rounded-lg px-4 py-3 transition ${
                isActive
                  ? "bg-cyan-600 text-white"
                  : "hover:bg-slate-800"
              }`
            }
          >
            {item.title}
          </NavLink>

        ))}

      </nav>

    </div>
  );
}

export default Sidebar;
