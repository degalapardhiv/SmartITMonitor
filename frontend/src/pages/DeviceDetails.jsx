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

      <div className="ui-loading">
        <span className="ui-spinner" /> Loading device...
      </div>

    );

  }


  const isOnline =
    String(device.status || "").toLowerCase() === "online";


  return (

    <div>

      <div className="ui-page-header !mb-6">

        <div>

          <h1 className="ui-page-title">
            Device Details
          </h1>

          <p className="ui-page-subtitle">
            {device.hostname} · {device.department || "Unassigned"}
          </p>

        </div>

        <span className={`ui-badge ${isOnline ? "ui-badge-success" : "ui-badge-danger"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-[#46d369]" : "bg-[#e6797e]"}`} />
          {device.status || "unknown"}
        </span>

      </div>


      <div className="ui-card p-6 mb-6">


        <h2 className="text-2xl font-bold text-white">
          {device.hostname}
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-5 mt-6 text-sm">


          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">IP</div>
            <div className="font-medium text-white">{device.ip}</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">OS</div>
            <div className="text-[var(--ds-text-2)]">{device.os || "—"}</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Status</div>
            <div className={isOnline ? "text-[var(--ds-success)] font-semibold" : "text-[var(--ds-danger)] font-semibold"}>
              {device.status || "unknown"}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">CPU</div>
            <div className="font-semibold text-green-400">{device.cpu ?? 0}%</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">RAM</div>
            <div className="font-semibold text-yellow-400">{device.ram ?? 0}%</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Disk</div>
            <div className="font-semibold text-purple-400">{device.disk ?? 0}%</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Last Seen</div>
            <div className="text-[var(--ds-text-2)]">
              {device.last_seen ? new Date(device.last_seen).toLocaleString() : "Unknown"}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Department</div>
            <div className="text-[var(--ds-text-2)]">{device.department || "—"}</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Lab</div>
            <div className="text-[var(--ds-text-2)]">{device.lab || "—"}</div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-[var(--ds-text-3)] font-semibold mb-1">Location</div>
            <div className="text-[var(--ds-text-2)]">{device.location || "—"}</div>
          </div>

        </div>


      </div>


      <MetricsChart data={history} />


    </div>

  );

}


export default DeviceDetails;
