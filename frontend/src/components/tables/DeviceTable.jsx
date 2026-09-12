function DeviceTable({ devices }) {
  function getHealth(device) {
    if (
      device.cpu > 90 ||
      device.ram > 90 ||
      device.disk > 90
    ) {
      return {
        text: "Critical",
        color: "bg-red-500",
      };
    }

    if (
      device.cpu > 80 ||
      device.ram > 80 ||
      device.disk > 80
    ) {
      return {
        text: "Warning",
        color: "bg-amber-500",
      };
    }

    return {
      text: "Healthy",
      color: "bg-emerald-500",
    };
  }

  return (
    <div className="ui-table-wrap overflow-x-auto">

      <table className="ui-table min-w-full">

        <thead>

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
                className="text-center p-8 text-slate-500"
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
                  className="border-t border-cyan-500/8 hover:bg-cyan-500/5 transition"
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
                      className={`px-3 py-1 rounded-full text-white text-xs font-semibold ${
                        String(device.status || "").toLowerCase() === "online"
                          ? "bg-emerald-500"
                          : "bg-red-500"
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
