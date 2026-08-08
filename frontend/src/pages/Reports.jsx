import { useEffect, useState } from "react";

import Layout from "../components/layout/Layout";
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
    d => d.status === "Online"
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

    <Layout>

      <div className="flex justify-between items-center mb-8">

        <div>

          <h1 className="text-4xl font-bold text-white">
            Reports
          </h1>

          <p className="text-gray-400 mt-2">
            Generate monitoring reports
          </p>

        </div>

        <button
          onClick={loadReports}
          className="bg-cyan-600 hover:bg-cyan-700 px-5 py-2 rounded-lg"
        >
          Refresh
        </button>

      </div>
      <div className="grid md:grid-cols-6 gap-6 mb-8">

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Total Devices
          </h2>

          <p className="text-4xl font-bold text-cyan-400 mt-4">
            {totalDevices}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Online
          </h2>

          <p className="text-4xl font-bold text-green-400 mt-4">
            {onlineDevices}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Offline
          </h2>

          <p className="text-4xl font-bold text-red-400 mt-4">
            {offlineDevices}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Alerts
          </h2>

          <p className="text-4xl font-bold text-yellow-400 mt-4">
            {alertDevices}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Departments
          </h2>

          <p className="text-4xl font-bold text-purple-400 mt-4">
            {departments}
          </p>

        </div>


        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Labs
          </h2>

          <p className="text-4xl font-bold text-blue-400 mt-4">
            {labs}
          </p>

        </div>


      </div>


      <div className="bg-slate-800 rounded-xl p-6 mb-8">

        <h2 className="text-2xl font-bold mb-6">
          Export Reports
        </h2>

        <div className="grid md:grid-cols-3 gap-6">

          <button
            onClick={() => exportCSV(devices)}
            className="bg-green-600 hover:bg-green-700 p-5 rounded-xl font-bold"
          >
            📄 Export CSV
          </button>

          <button
            onClick={() => exportExcel(devices)}
            className="bg-blue-600 hover:bg-blue-700 p-5 rounded-xl font-bold"
          >
            📊 Export Excel
          </button>

          <button
            onClick={() => exportPDF(devices)}
            className="bg-red-600 hover:bg-red-700 p-5 rounded-xl font-bold"
          >
            📑 Export PDF
          </button>

        </div>

      </div>
      <div className="bg-slate-800 rounded-xl shadow-xl overflow-x-auto">

        <div className="p-6 border-b border-slate-700">

          <h2 className="text-2xl font-bold">
            Device Summary Report
          </h2>

        </div>

        <table className="w-full">

          <thead className="bg-slate-900">

            <tr>

              <th className="text-left p-4">
                Hostname
              </th>

              <th className="text-left p-4">
                Department
              </th>

              <th className="text-left p-4">
                Lab
              </th>

              <th className="text-center p-4">
                CPU
              </th>

              <th className="text-center p-4">
                RAM
              </th>

              <th className="text-center p-4">
                Disk
              </th>

              <th className="text-center p-4">
                Status
              </th>

            </tr>

          </thead>

          <tbody>

            {loading ? (

              <tr>

                <td
                  colSpan="7"
                  className="text-center py-8 text-gray-400"
                >
                  Loading report...
                </td>

              </tr>

            ) : devices.length === 0 ? (

              <tr>

                <td
                  colSpan="7"
                  className="text-center py-8 text-gray-400"
                >
                  No devices available.
                </td>

              </tr>

            ) : (

              devices.map((device) => (

                <tr
                  key={device.id}
                  className="border-t border-slate-700 hover:bg-slate-700 transition"
                >

                  <td className="p-4 font-semibold text-cyan-400">
                    {device.hostname}
                  </td>

                  <td className="p-4">
                    {device.department}
                  </td>

                  <td className="p-4">
                    {device.lab}
                  </td>

                  <td className="text-center p-4">
                    {device.cpu.toFixed(1)}%
                  </td>

                  <td className="text-center p-4">
                    {device.ram.toFixed(1)}%
                  </td>

                  <td className="text-center p-4">
                    {device.disk.toFixed(1)}%
                  </td>

                  <td className="text-center p-4">

                    <span
                      className={
                        device.status === "Online"
                          ? "bg-green-600 px-3 py-1 rounded-full text-sm"
                          : "bg-red-600 px-3 py-1 rounded-full text-sm"
                      }
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

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
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

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
            Alert Summary
          </h2>

          <div className="space-y-4">

            <div className="flex justify-between">

              <span>CPU Alerts</span>

              <span className="text-red-400 font-bold">
                {
                  devices.filter(
                    d => d.cpu > 90
                  ).length
                }
              </span>

            </div>

            <div className="flex justify-between">

              <span>RAM Alerts</span>

              <span className="text-yellow-400 font-bold">
                {
                  devices.filter(
                    d => d.ram > 90
                  ).length
                }
              </span>

            </div>

            <div className="flex justify-between">

              <span>Disk Alerts</span>

              <span className="text-orange-400 font-bold">
                {
                  devices.filter(
                    d => d.disk > 90
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

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
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
                    device.status === "Online"
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

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
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
    </Layout>

  );

}

export default Reports;
