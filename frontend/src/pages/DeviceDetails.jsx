import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";
import MetricsChart from "../components/charts/MetricsChart";


function DeviceDetails(){

  const { id } = useParams();

  const [device,setDevice] = useState(null);

  const [history,setHistory] = useState([]);


  useWebSocket((message) => {

    if (!message || !message.type) return;

    if (
      message.type === "device_update" &&
      message.device &&
      Number(message.device.id) === Number(id)
    ) {

      setDevice(
        message.device
      );

      setHistory(prev => [
        ...prev.slice(-29),
        {
          time: new Date().toLocaleTimeString(),
          cpu: message.device.cpu,
          ram: message.device.ram,
          disk: message.device.disk
        }
      ]);

    }

  });


  async function loadMetrics(){

    try{

      const response = await api.get(
        `/devices/${id}/metrics`
      );


      const formatted = response.data.map(
        item => ({
          time: new Date(
            item.created_at
          ).toLocaleTimeString(),

          cpu:item.cpu,
          ram:item.ram,
          disk:item.disk
        })
      );


      setHistory(formatted);

    }
    catch(err){

      console.error(
        "Metrics Error",
        err
      );

    }

  }

  async function loadDevice(){

    try{

      const response = await api.get(
        `/devices/${id}`
      );

      setDevice(
        response.data
      );

    }
    catch(err){

      console.error(
        "Device Details Error",
        err
      );

    }

  }


  useEffect(()=>{

    async function sync() {
      await loadDevice();
      await loadMetrics();
    }

    sync();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);



  if(!device){

    return (

      <div className="text-white">
        Loading device...
      </div>

    );

  }


  const isOnline =
    String(device.status || "").toLowerCase() === "online";


  return (

    <div>

      <h1 className="text-4xl font-bold text-white mb-6">
        Device Details
      </h1>


      <div className="bg-slate-800 rounded-xl p-6">


        <h2 className="text-3xl text-cyan-400">
          {device.hostname}
        </h2>


        <div className="grid grid-cols-2 gap-5 mt-6 text-white">


          <p>
            IP:
            {" "}
            {device.ip}
          </p>


          <p>
            Status:
            {" "}
            <span
              className={
                isOnline
                  ? "text-green-400 font-bold"
                  : "text-red-400 font-bold"
              }
            >
              {device.status}
            </span>
          </p>


          <p>
            CPU:
            {device.cpu ?? 0}%
          </p>


          <p>
            RAM:
            {device.ram ?? 0}%
          </p>


          <p>
            Disk:
            {device.disk ?? 0}%
          </p>


          <p>
            OS:
            {device.os}
          </p>


          <p>
            Last Seen:
            {" "}
            {
              device.last_seen
              ? new Date(
                  device.last_seen
                ).toLocaleString()
              : "Unknown"
            }
          </p>


          <p>
            Department:
            {device.department}
          </p>


          <p>
            Lab:
            {device.lab}
          </p>


          <p>
            Location:
            {device.location}
          </p>


        </div>


      </div>


      <MetricsChart data={history} />


    </div>

  );

}


export default DeviceDetails;
