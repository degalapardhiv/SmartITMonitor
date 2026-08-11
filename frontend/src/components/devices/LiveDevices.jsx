import { useState } from "react";
import useWebSocket from "../../hooks/useWebSocket";

function LiveDevices() {

  const [devices, setDevices] = useState([]);


  useWebSocket((message) => {

    if (!message || !message.type) return;

    if (message.type === "device_update" && message.device) {

      const update = message.device;

      setDevices(prev => {

        const exists = prev.some(
          d => d.id === update.id
        );

        if (exists) {

          return prev.map(d =>
            d.id === update.id
              ? { ...d, ...update }
              : d
          );

        }

        return [
          ...prev,
          update
        ];

      });

      return;

    }

    if (message.type === "device_offline" && message.device) {

      setDevices(prev =>
        prev.map(d =>
          d.id === message.device.id
            ? {
                ...d,
                ...message.device,
                status: "offline",
                last_seen: new Date().toISOString()
              }
            : d
        )
      );

      return;

    }

    if (message.type === "device_online" && message.device) {

      setDevices(prev =>
        prev.map(d =>
          d.id === message.device.id
            ? {
                ...d,
                ...message.device,
                status: "online",
                last_seen: new Date().toISOString()
              }
            : d
        )
      );

    }

  });


  return (

    <div className="mt-8">

      <h2 className="text-2xl font-bold text-white mb-4">
        Live Devices
      </h2>


      <div className="bg-slate-800 rounded-xl p-6">

        <table className="w-full text-white">

          <thead>

            <tr className="text-gray-400">

              <th className="text-left">
                Hostname
              </th>

              <th className="text-left">
                IP
              </th>

              <th className="text-left">
                CPU
              </th>

              <th className="text-left">
                RAM
              </th>

              <th className="text-left">
                Status
              </th>

            </tr>

          </thead>


          <tbody>

          {
            devices.map(device => {

              const online =
                String(device.status || "").toLowerCase() === "online";

              return (

                <tr key={device.id}>

                  <td>
                    {device.hostname}
                  </td>

                  <td>
                    {device.ip}
                  </td>

                  <td>
                    {device.cpu ?? 0}%
                  </td>

                  <td>
                    {device.ram ?? 0}%
                  </td>

                  <td className={online ? "text-green-400" : "text-red-400"}>
                    {device.status}
                  </td>

                </tr>

              );

            })
          }

          </tbody>


        </table>


        {
          devices.length === 0 &&
          <p className="text-gray-400 mt-4">
            Waiting for devices...
          </p>
        }


      </div>


    </div>

  );

}


export default LiveDevices;
