function DeviceTable({ devices }) {
  function getHealth(device) {
    if (
      device.cpu > 90 ||
      device.ram > 90 ||
      device.disk > 90
    ) {
      return {
        text: "Critical",
        color: "bg-red-600",
      };
    }

    if (
      device.cpu > 80 ||
      device.ram > 80 ||
      device.disk > 80
    ) {
      return {
        text: "Warning",
        color: "bg-yellow-500",
      };
    }

    return {
      text: "Healthy",
      color: "bg-green-600",
    };
  }

  return (
    <div className="bg-slate-800 rounded-xl shadow-lg overflow-x-auto">

      <table className="min-w-full">

        <thead className="bg-slate-700">

          <tr>

            <th className="p-4 text-left">Hostname</th>

            <th className="p-4 text-left">
              Department
            </th>

            <th className="p-4 text-left">
              Lab
            </th>

            <th className="p-4 text-left">
              OS
            </th>

            <th className="p-4 text-left">
              IP Address
            </th>

            <th className="p-4 text-center">
              CPU
            </th>

            <th className="p-4 text-center">
              RAM
            </th>

            <th className="p-4 text-center">
              Disk
            </th>

            <th className="p-4 text-center">
              Status
            </th>

            <th className="p-4 text-center">
              Health
            </th>

          </tr>

        </thead>

        <tbody>

          {devices.length === 0 ? (

            <tr>

              <td
                colSpan="10"
                className="text-center p-8 text-gray-400"
              >
                No devices found
              </td>

            </tr>

          ) : (

            devices.map((device) => {

              const health = getHealth(device);

              return (

                <tr
                  key={device.id}
                  className="border-t border-slate-700 hover:bg-slate-700 transition"
                >

                  <td className="p-4 font-semibold">
                    {device.hostname}
                  </td>

                  <td className="p-4">
                    {device.department || "-"}
                  </td>

                  <td className="p-4">
                    {device.lab || "-"}
                  </td>

                  <td className="p-4">
                    {device.os || "-"}
                  </td>

                  <td className="p-4">
                    {device.ip}
                  </td>

                  <td className="text-center">
                    {Number(device.cpu).toFixed(1)}%
                  </td>

                  <td className="text-center">
                    {Number(device.ram).toFixed(1)}%
                  </td>

                  <td className="text-center">
                    {Number(device.disk).toFixed(1)}%
                  </td>

                  <td className="text-center">

                    <span
                      className={`px-3 py-1 rounded-full text-white ${
                        device.status === "Online"
                          ? "bg-green-600"
                          : "bg-red-600"
                      }`}
                    >
                      {device.status}
                    </span>

                  </td>

                  <td className="text-center">

                    <span
                      className={`px-3 py-1 rounded-full text-white ${health.color}`}
                    >
                      {health.text}
                    </span>

                  </td>

                </tr>

              );

            })

          )}

        </tbody>

      </table>

    </div>
  );
}

export default DeviceTable;
