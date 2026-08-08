import { useEffect, useState } from "react";
import useWebSocket from "../../hooks/useWebSocket";

function LiveDevices() {

  const liveData = useWebSocket();

  const [devices, setDevices] = useState([]);


  useEffect(() => {

    if (
      liveData &&
      liveData.type === "device_update"
    ) {

      setDevices((prev) => {

        const exists = prev.find(
          d => d.id === liveData.device.id
        );


        if (exists) {

          return prev.map(d =>
            d.id === liveData.device.id
              ? liveData.device
              : d
          );

        }


        return [
          ...prev,
          liveData.device
        ];

      });

    }

  }, [liveData]);


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
            devices.map(device => (

              <tr key={device.id}>

                <td>
                  {device.hostname}
                </td>

                <td>
                  {device.ip}
                </td>

                <td>
                  {device.cpu}%
                </td>

                <td>
                  {device.ram}%
                </td>

                <td className="text-green-400">
                  {device.status}
                </td>

              </tr>

            ))
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
