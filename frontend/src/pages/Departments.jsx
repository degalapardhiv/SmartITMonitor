import { useEffect, useState } from "react";

import Layout from "../components/layout/Layout";
import api from "../services/api";

function Departments() {

  const [devices, setDevices] = useState([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {

    loadDepartments();

  }, []);

  async function loadDepartments() {

    try {

      const response = await api.get("/devices");

      setDevices(response.data);

    }

    catch (error) {

      console.error(error);

    }

    finally {

      setLoading(false);

    }

  }

  const departments = [...new Set(

    devices.map(
      device => device.department
    )

  )];

  return (

    <Layout>

      <div className="flex justify-between items-center mb-8">

        <div>

          <h1 className="text-4xl font-bold text-white">
            Departments
          </h1>

          <p className="text-gray-400 mt-2">
            Department-wise Device Monitoring
          </p>

        </div>

        <button
          onClick={loadDepartments}
          className="bg-cyan-600 hover:bg-cyan-700 px-5 py-2 rounded-lg"
        >
          Refresh
        </button>

      </div>

      <div className="grid md:grid-cols-4 gap-6 mb-8">

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Departments
          </h2>

          <p className="text-4xl font-bold text-cyan-400 mt-4">
            {departments.length}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Total Devices
          </h2>

          <p className="text-4xl font-bold text-green-400 mt-4">
            {devices.length}
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Online
          </h2>

          <p className="text-4xl font-bold text-green-500 mt-4">
            {
              devices.filter(
                d => String(d.status || "").toLowerCase() === "online"
              ).length
            }
          </p>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-lg font-semibold">
            Offline
          </h2>

          <p className="text-4xl font-bold text-red-500 mt-4">
            {
              devices.filter(
                d => String(d.status || "").toLowerCase() !== "online"
              ).length
            }
          </p>

        </div>

      </div>
      <div className="bg-slate-800 rounded-xl shadow-xl overflow-x-auto">

        <table className="w-full">

          <thead className="bg-slate-900">

            <tr>

              <th className="text-left p-4">
                Department
              </th>

              <th className="text-center p-4">
                Devices
              </th>

              <th className="text-center p-4">
                Online
              </th>

              <th className="text-center p-4">
                Offline
              </th>

              <th className="text-center p-4">
                Alerts
              </th>

              <th className="text-center p-4">
                Labs
              </th>

            </tr>

          </thead>

          <tbody>

            {loading ? (

              <tr>

                <td
                  colSpan="6"
                  className="text-center p-8 text-gray-400"
                >
                  Loading departments...
                </td>

              </tr>

            ) : departments.length === 0 ? (

              <tr>

                <td
                  colSpan="6"
                  className="text-center p-8 text-gray-400"
                >
                  No departments found.
                </td>

              </tr>

            ) : (

              departments.map((department) => {

                const deptDevices = devices.filter(
                  (d) => d.department === department
                );

                const online = deptDevices.filter(
                  (d) => String(d.status || "").toLowerCase() === "online"
                ).length;

                const offline = deptDevices.length - online;

                const alerts = deptDevices.filter(
                  (d) =>
                    (d.cpu ?? 0) > 90 ||
                    (d.ram ?? 0) > 90 ||
                    (d.disk ?? 0) > 90
                ).length;

                const labs = new Set(
                  deptDevices.map((d) => d.lab)
                ).size;

                return (

                  <tr
                    key={department}
                    className="border-t border-slate-700 hover:bg-slate-700"
                  >

                    <td className="p-4 font-semibold text-cyan-400">
                      {department}
                    </td>

                    <td className="text-center p-4">
                      {deptDevices.length}
                    </td>

                    <td className="text-center p-4 text-green-400 font-bold">
                      {online}
                    </td>

                    <td className="text-center p-4 text-red-400 font-bold">
                      {offline}
                    </td>

                    <td className="text-center p-4 text-yellow-400 font-bold">
                      {alerts}
                    </td>

                    <td className="text-center p-4">
                      {labs}
                    </td>

                  </tr>

                );

              })

            )}

          </tbody>

        </table>

      </div>
      <div className="grid lg:grid-cols-3 gap-6 mt-8">

        {departments.map((department) => {

          const deptDevices = devices.filter(
            (d) => d.department === department
          );

          const online = deptDevices.filter(
            (d) => String(d.status || "").toLowerCase() === "online"
          ).length;

          const offline = deptDevices.length - online;

          const alerts = deptDevices.filter(
            (d) =>
              (d.cpu ?? 0) > 90 ||
              (d.ram ?? 0) > 90 ||
              (d.disk ?? 0) > 90
          ).length;

          const percentage =
            deptDevices.length === 0
              ? 0
              : Math.round(
                  (online / deptDevices.length) * 100
                );

          return (

            <div
              key={department}
              className="bg-slate-800 rounded-xl p-6 shadow-lg"
            >

              <h2 className="text-2xl font-bold text-cyan-400 mb-5">
                {department}
              </h2>

              <div className="space-y-3">

                <div className="flex justify-between">
                  <span>Total Devices</span>
                  <span className="font-bold">
                    {deptDevices.length}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Online</span>
                  <span className="text-green-400 font-bold">
                    {online}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Offline</span>
                  <span className="text-red-400 font-bold">
                    {offline}
                  </span>
                </div>

                <div className="flex justify-between">
                  <span>Alerts</span>
                  <span className="text-yellow-400 font-bold">
                    {alerts}
                  </span>
                </div>

              </div>

              <div className="mt-6">

                <div className="flex justify-between mb-2">

                  <span>
                    Availability
                  </span>

                  <span className="font-bold">
                    {percentage}%
                  </span>

                </div>

                <div className="w-full bg-slate-700 rounded-full h-3">

                  <div
                    className="bg-green-500 h-3 rounded-full transition-all duration-500"
                    style={{
                      width: `${percentage}%`
                    }}
                  />

                </div>

              </div>

            </div>

          );

        })}

      </div>
    </Layout>

  );

}

export default Departments;
