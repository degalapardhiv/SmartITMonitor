import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Layout from "../components/layout/Layout";
import api from "../services/api";

import CPUChart from "../components/charts/CPUChart";
import RAMChart from "../components/charts/RAMChart";
import DiskChart from "../components/charts/DiskChart";

function DeviceDetails() {

  const { id } = useParams();

  const [device, setDevice] = useState(null);

  const [metrics, setMetrics] = useState([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {

    loadData();

  }, [id]);

  async function loadData() {

    try {

      const [deviceResponse, metricResponse] =
        await Promise.all([

          api.get(`/devices/${id}`),

          api.get(`/devices/${id}/metrics`)

        ]);

      setDevice(deviceResponse.data);

      setMetrics(metricResponse.data);

    }

    catch (error) {

      console.error(error);

    }

    finally {

      setLoading(false);

    }

  }

  if (loading) {

    return (

      <Layout>

        <div className="flex items-center justify-center h-[70vh]">

          <div className="text-center">

            <h2 className="text-3xl font-bold text-cyan-400">
              Loading Device...
            </h2>

            <p className="text-gray-400 mt-3">
              Please wait while we fetch device information.
            </p>

          </div>

        </div>

      </Layout>

    );

  }

  if (!device) {

    return (

      <Layout>

        <div className="flex items-center justify-center h-[70vh]">

          <div className="text-center">

            <h2 className="text-3xl font-bold text-red-500">
              Device Not Found
            </h2>

            <Link
              to="/devices"
              className="inline-block mt-6 bg-cyan-600 hover:bg-cyan-700 px-6 py-3 rounded-lg"
            >
              Back to Devices
            </Link>

          </div>

        </div>

      </Layout>

    );

  }

  return (

    <Layout>

      <div className="flex justify-between items-center mb-8">

        <div>

          <h1 className="text-4xl font-bold text-white">
            {device.hostname}
          </h1>

          <p className="text-gray-400 mt-2">
            Device Details
          </p>

        </div>

        <Link
          to="/devices"
          className="bg-cyan-600 hover:bg-cyan-700 px-5 py-3 rounded-lg text-white"
        >
          ← Back
        </Link>

      </div>

      <div className="grid lg:grid-cols-2 gap-6">

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
            Device Information
          </h2>

          <div className="space-y-4">

            <div className="flex justify-between">
              <span className="text-gray-400">Hostname</span>
              <span>{device.hostname}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">IP Address</span>
              <span>{device.ip}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">Department</span>
              <span>{device.department}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">Lab</span>
              <span>{device.lab}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">Location</span>
              <span>{device.location}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">Operating System</span>
              <span>{device.os}</span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-400">Status</span>

              <span
                className={
                  device.status === "Online"
                    ? "text-green-400 font-bold"
                    : "text-red-400 font-bold"
                }
              >
                {device.status}
              </span>

            </div>

          </div>

        </div>

        <div className="bg-slate-800 rounded-xl p-6">

          <h2 className="text-2xl font-bold mb-6">
            Resource Usage
          </h2>

          {/* CPU */}

          <div className="mb-8">

            <div className="flex justify-between mb-2">

              <span className="font-semibold">
                CPU Usage
              </span>

              <span className="text-green-400 font-bold">
                {device.cpu.toFixed(1)}%
              </span>

            </div>

            <div className="w-full bg-slate-700 rounded-full h-4">

              <div
                className="bg-green-500 h-4 rounded-full transition-all duration-500"
                style={{
                  width: `${device.cpu}%`
                }}
              />

            </div>

          </div>

          {/* RAM */}

          <div className="mb-8">

            <div className="flex justify-between mb-2">

              <span className="font-semibold">
                RAM Usage
              </span>

              <span className="text-blue-400 font-bold">
                {device.ram.toFixed(1)}%
              </span>

            </div>

            <div className="w-full bg-slate-700 rounded-full h-4">

              <div
                className="bg-blue-500 h-4 rounded-full transition-all duration-500"
                style={{
                  width: `${device.ram}%`
                }}
              />

            </div>

          </div>

          {/* Disk */}

          <div>

            <div className="flex justify-between mb-2">

              <span className="font-semibold">
                Disk Usage
              </span>

              <span className="text-yellow-400 font-bold">
                {device.disk.toFixed(1)}%
              </span>

            </div>

            <div className="w-full bg-slate-700 rounded-full h-4">

              <div
                className="bg-yellow-500 h-4 rounded-full transition-all duration-500"
                style={{
                  width: `${device.disk}%`
                }}
              />

            </div>

          </div>

        </div>

      </div>


      <div className="grid lg:grid-cols-3 gap-6 mt-8">

        <CPUChart data={metrics} />

        <RAMChart data={metrics} />

        <DiskChart data={metrics} />

      </div>

      <div className="bg-slate-800 rounded-xl p-6 mt-8">

        <h2 className="text-2xl font-bold mb-6">
          Metrics History
        </h2>

        <div className="overflow-x-auto">

          <table className="w-full">

            <thead className="border-b border-slate-700">

              <tr>

                <th className="text-left py-3">
                  Timestamp
                </th>

                <th className="text-center py-3">
                  CPU
                </th>

                <th className="text-center py-3">
                  RAM
                </th>

                <th className="text-center py-3">
                  Disk
                </th>

              </tr>

            </thead>

            <tbody>

              {metrics.length === 0 ? (

                <tr>

                  <td
                    colSpan="4"
                    className="text-center py-8 text-gray-400"
                  >
                    No metrics available.
                  </td>

                </tr>

              ) : (

                metrics.map((metric) => (

                  <tr
                    key={metric.id}
                    className="border-b border-slate-700 hover:bg-slate-700"
                  >

                    <td className="py-3">

                      {new Date(
                        metric.created_at
                      ).toLocaleString()}

                    </td>

                    <td className="text-center">
                      {metric.cpu.toFixed(1)}%
                    </td>

                    <td className="text-center">
                      {metric.ram.toFixed(1)}%
                    </td>

                    <td className="text-center">
                      {metric.disk.toFixed(1)}%
                    </td>

                  </tr>

                ))

              )}

            </tbody>

          </table>

        </div>

      </div>

    </Layout>
  );
}

export default DeviceDetails;
