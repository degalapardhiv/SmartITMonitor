import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";
import MetricsChart from "../components/charts/MetricsChart";


function DeviceDetails(){

  const { id } = useParams();

  const liveData = useWebSocket();

  const [device,setDevice] = useState(null);

  const [history,setHistory] = useState([]);


  useEffect(()=>{

    loadDevice();

    loadMetrics();

  },[]);


  useEffect(()=>{

    if(
      liveData &&
      liveData.type === "device_update"
    ){

      if(
        liveData.device.id === Number(id)
      ){

        setDevice(
          liveData.device
        );

        setHistory(prev => [
          ...prev.slice(-29),
          {
            time: new Date().toLocaleTimeString(),
            cpu: liveData.device.cpu,
            ram: liveData.device.ram,
            disk: liveData.device.disk
          }
        ]);

      }

    }

  },[liveData,id]);






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



  if(!device){

    return (

      <div className="text-white">
        Loading device...
      </div>

    );

  }



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
                device.status === "Online"
                  ? "text-green-400 font-bold"
                  : "text-red-400 font-bold"
              }
            >
              {device.status}
            </span>
          </p>


          <p>
            CPU:
            {device.cpu}%
          </p>


          <p>
            RAM:
            {device.ram}%
          </p>


          <p>
            Disk:
            {device.disk}%
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
