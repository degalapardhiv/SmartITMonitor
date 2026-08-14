import { useEffect, useState } from "react";
import {
  FiFileText,
  FiRefreshCw,
  FiDownload,
} from "react-icons/fi";

import api from "../services/api";


function exportCSV(devices){

  const headers = [
    "Hostname",
    "IP",
    "Department",
    "Lab",
    "CPU",
    "RAM",
    "Disk",
    "Status"
  ];


  const rows = devices.map(d => [
    d.hostname,
    d.ip,
    d.department,
    d.lab,
    d.cpu,
    d.ram,
    d.disk,
    d.status
  ]);


  const csv = [
    headers,
    ...rows
  ]
  .map(row => row.join(","))
  .join("\n");


  const blob = new Blob(
    [csv],
    {type:"text/csv"}
  );


  const url = URL.createObjectURL(blob);


  const link = document.createElement("a");

  link.href = url;
  link.download = "smart-it-monitor-report.csv";

  link.click();


  URL.revokeObjectURL(url);

}


async function exportExcel(devices){

  const XLSX = await import("xlsx");

  const worksheet = XLSX.utils.json_to_sheet(
    devices
  );


  const workbook = XLSX.utils.book_new();


  XLSX.utils.book_append_sheet(
    workbook,
    worksheet,
    "Devices"
  );


  XLSX.writeFile(
    workbook,
    "smart-it-monitor-report.xlsx"
  );

}



async function exportPDF(devices){

  const jsPDF = (await import("jspdf")).default;

  const autoTable =
    (await import("jspdf-autotable")).default;

  const doc = new jsPDF();


  doc.setFontSize(18);

  doc.text(
    "Smart IT Monitor Report",
    14,
    20
  );


  doc.setFontSize(11);

  doc.text(
    `Generated: ${new Date().toLocaleString()}`,
    14,
    30
  );


  const rows = devices.map(device => [

    device.hostname,
    device.ip,
    device.status,
    `${device.cpu}%`,
    `${device.ram}%`,
    `${device.disk}%`

  ]);


  autoTable(doc, {

    startY:40,

    head:[
      [
        "Hostname",
        "IP",
        "Status",
        "CPU",
        "RAM",
        "Disk"
      ]
    ],

    body: rows

  });


  doc.save(
    "smart-it-monitor-report.pdf"
  );

}


function Reports() {

  const [devices, setDevices] = useState([]);

  const [alerts, setAlerts] = useState([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {

    loadReports();

  }, []);

  async function loadReports() {

    try {

      const response = await api.get("/devices");

      setDevices(response.data);


      const alertResponse = await api.get("/alerts");

      setAlerts(alertResponse.data);

    }

    catch (error) {

      console.error(error);

    }

    finally {

      setLoading(false);

    }

  }

  const totalDevices = devices.length;

  const onlineDevices = devices.filter(
    d => String(d.status || "").toLowerCase() === "online"
  ).length;

  const offlineDevices =
    totalDevices - onlineDevices;

  const alertDevices = alerts.length;


  const departments = [
    ...new Set(
      devices.map(d => d.department)
    )
  ].length;


  const labs = [
    ...new Set(
      devices.map(d => d.lab)
    )
  ].length;

  return (
    <>
      <div className="ui-page-header !mb-6">

        <div>

          <h1 className="ui-page-title">
            Reports
          </h1>

          <p className="ui-page-subtitle">
            Generate monitoring reports
          </p>

        </div>

        <button
          onClick={loadReports}
          className="ui-btn ui-btn-secondary ui-btn-sm"
        >
          <FiRefreshCw /> Refresh
        </button>

      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">

        <div className="ui-stat">
          <div className="ui-stat-label">Total Devices</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-text)" }}>{totalDevices}</p>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Online</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-success)" }}>{onlineDevices}</p>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Offline</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-danger)" }}>{offlineDevices}</p>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Alerts</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-warning)" }}>{alertDevices}</p>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Departments</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-text-2)" }}>{departments}</p>
        </div>

        <div className="ui-stat">
          <div className="ui-stat-label">Labs</div>
          <p className="ui-stat-value mt-1" style={{ color: "var(--ds-text-2)" }}>{labs}</p>
        </div>

      </div>


      <div className="ui-card p-6 mb-6">

        <h2 className="ui-card-title mb-4">
          Export Reports
        </h2>

        <div className="grid md:grid-cols-3 gap-4">

          <button
            onClick={() => exportCSV(devices)}
            className="ui-btn ui-btn-secondary !py-4"
          >
            <FiFileText /> Export CSV
          </button>

          <button
            onClick={() => exportExcel(devices)}
            className="ui-btn ui-btn-secondary !py-4"
          >
            <FiDownload /> Export Excel
          </button>

          <button
            onClick={() => exportPDF(devices)}
            className="ui-btn ui-btn-danger !py-4"
          >
            <FiFileText /> Export PDF
          </button>

        </div>

      </div>
      <div className="ui-table-wrap shadow-xl">

        <div className="p-6 border-b border-[var(--ds-border)]">

          <h2 className="ui-card-title">
            Device Summary Report
          </h2>

        </div>

        <table className="ui-table">

          <thead>

            <tr>

              <th>Hostname</th>
              <th>Department</th>
              <th>Lab</th>
              <th>CPU</th>
              <th>RAM</th>
              <th>Disk</th>
              <th>Status</th>

            </tr>

          </thead>

          <tbody>

            {loading ? (

              <tr>

                <td
                  colSpan="7"
                  className="text-center py-10 text-[var(--ds-text-3)]"
                >
                  <span className="ui-spinner" /> Loading report...
                </td>

              </tr>

            ) : devices.length === 0 ? (

              <tr>

                <td
                  colSpan="7"
                  className="text-center py-10 text-[var(--ds-text-3)]"
                >
                  No devices available.
                </td>

              </tr>

            ) : (

              devices.map((device) => (

                <tr key={device.id}>

                  <td className="font-semibold text-white">
                    {device.hostname}
                  </td>

                  <td>{device.department}</td>

                  <td>{device.lab}</td>

                  <td>{(device.cpu ?? 0).toFixed(1)}%</td>

                  <td>{(device.ram ?? 0).toFixed(1)}%</td>

                  <td>{(device.disk ?? 0).toFixed(1)}%</td>

                  <td>

                    <span
                      className={`ui-badge ${
                        String(device.status || "").toLowerCase() === "online"
                          ? "ui-badge-success"
                          : "ui-badge-danger"
                      }`}
                    >
                      {device.status}
                    </span>

                  </td>

                </tr>

              ))

            )}

          </tbody>

        </table>

      </div>
      <div className="grid lg:grid-cols-2 gap-8 mt-8">

        {/* Department Report */}

        <div className="ui-card p-6">

          <h2 className="ui-card-title mb-5">
            Department Report
          </h2>

          <table className="w-full">

            <thead>

              <tr className="border-b border-slate-700">

                <th className="text-left py-3">
                  Department
                </th>

                <th className="text-center py-3">
                  Devices
                </th>

              </tr>

            </thead>

            <tbody>

              {[...new Set(devices.map(d => d.department))].map((dept) => {

                const total = devices.filter(
                  d => d.department === dept
                ).length;

                return (

                  <tr
                    key={dept}
                    className="border-b border-slate-700"
                  >

                    <td className="py-3">
                      {dept}
                    </td>

                    <td className="text-center">
                      {total}
                    </td>

                  </tr>

                );

              })}

            </tbody>

          </table>

        </div>


        {/* Alert Summary */}

        <div className="ui-card p-6">

          <h2 className="ui-card-title mb-5">
            Alert Summary
          </h2>

          <div className="space-y-4">

            <div className="flex justify-between">

              <span>CPU Alerts</span>

              <span className="text-red-400 font-bold">
                {
                  devices.filter(
                    d => (d.cpu ?? 0) > 90
                  ).length
                }
              </span>

            </div>

            <div className="flex justify-between">

              <span>RAM Alerts</span>

              <span className="text-yellow-400 font-bold">
                {
                  devices.filter(
                    d => (d.ram ?? 0) > 90
                  ).length
                }
              </span>

            </div>

            <div className="flex justify-between">

              <span>Disk Alerts</span>

              <span className="text-orange-400 font-bold">
                {
                  devices.filter(
                    d => (d.disk ?? 0) > 90
                  ).length
                }
              </span>

            </div>

            <hr className="border-slate-700" />

            <div className="flex justify-between text-lg font-bold">

              <span>Total Alerts</span>

              <span className="text-cyan-400">
                {alertDevices}
              </span>

            </div>

          </div>

        </div>

      </div>
      <div className="grid lg:grid-cols-2 gap-8 mt-8">

        {/* Recent Activity */}

        <div className="ui-card p-6">

          <h2 className="ui-card-title mb-5">
            Recent Activity
          </h2>

          <div className="space-y-4">

            {devices.slice(0, 5).map((device) => (

              <div
                key={device.id}
                className="flex justify-between items-center border-b border-slate-700 pb-3"
              >

                <div>

                  <p className="font-semibold text-cyan-400">
                    {device.hostname}
                  </p>

                  <p className="text-sm text-gray-400">
                    {device.department}
                  </p>

                </div>

                <span
                  className={
                    String(device.status || "").toLowerCase() === "online"
                      ? "text-green-400"
                      : "text-red-400"
                  }
                >
                  {device.status}
                </span>

              </div>

            ))}

            {devices.length === 0 && (

              <div className="text-gray-400">
                No recent activity available.
              </div>

            )}

          </div>

        </div>

        {/* System Health */}

        <div className="ui-card p-6">

          <h2 className="ui-card-title mb-5">
            System Health
          </h2>

          <div className="space-y-5">

            <div>

              <div className="flex justify-between mb-2">

                <span>Online Availability</span>

                <span className="font-bold">

                  {totalDevices === 0
                    ? 0
                    : Math.round(
                        (onlineDevices / totalDevices) * 100
                      )
                  }%

                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-green-500 h-3 rounded-full"
                  style={{
                    width: `${
                      totalDevices === 0
                        ? 0
                        : (onlineDevices / totalDevices) * 100
                    }%`
                  }}
                />

              </div>

            </div>

            <div>

              <div className="flex justify-between mb-2">

                <span>Devices with Alerts</span>

                <span className="font-bold">

                  {totalDevices === 0
                    ? 0
                    : Math.round(
                        (alertDevices / totalDevices) * 100
                      )
                  }%

                </span>

              </div>

              <div className="w-full bg-slate-700 rounded-full h-3">

                <div
                  className="bg-red-500 h-3 rounded-full"
                  style={{
                    width: `${
                      totalDevices === 0
                        ? 0
                        : (alertDevices / totalDevices) * 100
                    }%`
                  }}
                />

              </div>

            </div>

            <div className="pt-4 border-t border-slate-700">

              <p className="text-gray-400">
                Report Generated
              </p>

              <p className="font-semibold mt-2">
                {new Date().toLocaleString()}
              </p>

            </div>

          </div>

        </div>

      </div>
    </>

  );

}

export default Reports;
