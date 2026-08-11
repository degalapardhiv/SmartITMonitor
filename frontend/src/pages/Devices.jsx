import { useEffect, useState } from "react";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";
import { useAuth } from "../context/auth-context";
import AddDevice from "../components/devices/AddDevice";



function StatusBadge({status}){

  const online =
    String(status || "").toLowerCase() === "online";

  return (

    <span
      className={
        online
        ? "bg-green-600 px-3 py-1 rounded-full text-sm"
        : "bg-red-600 px-3 py-1 rounded-full text-sm"
      }
    >
      {status || "unknown"}
    </span>

  );

}

function Devices(){

  const { role } = useAuth();

  const isAdmin =
    String(role || "").toLowerCase() === "admin";

  const [devices,setDevices] = useState([]);
  const [search,setSearch] = useState("");
  const [showAdd,setShowAdd] = useState(false);
  const [editDevice,setEditDevice] = useState(null);

  const [message,setMessage] = useState("");


  useWebSocket((message) => {

    if (!message || !message.type) return;

    if (message.type === "device_update" && message.device) {

      setDevices(prev => {

        const exists = prev.find(
          d => d.id === message.device.id
        );

        if(exists){

          return prev.map(d =>
            d.id === message.device.id
            ? { ...d, ...message.device }
            : d
          );

        }

        return [
          ...prev,
          message.device
        ];

      });

      return;

    }

    if (message.type === "device_offline" && message.device) {

      setDevices(prev =>
        prev.map(d =>
          d.id === message.device.id
          ? { ...d, ...message.device, status: "offline" }
          : d
        )
      );

      return;

    }

    if (message.type === "device_online" && message.device) {

      setDevices(prev =>
        prev.map(d =>
          d.id === message.device.id
          ? { ...d, ...message.device, status: "online" }
          : d
        )
      );

    }

  });


  async function loadDevices(){

    try{

      const response = await api.get("/devices");

      setDevices(response.data);

    }
    catch(err){

      console.error(
        "Device Load Error",
        err
      );

    }

  }


  useEffect(()=>{

    async function sync() {
      await loadDevices();
    }

    sync();

  },[]);


async function updateDevice(){

  try{

    const payload = {
      hostname: editDevice.hostname,
      ip: editDevice.ip,
      cpu: Number(editDevice.cpu) || 0,
      ram: Number(editDevice.ram) || 0,
      disk: Number(editDevice.disk) || 0,
      status: String(editDevice.status || "offline").toLowerCase(),
      department: editDevice.department || "",
      lab: editDevice.lab || "",
      location: editDevice.location || "",
      os: editDevice.os || ""
    };

    const response = await api.put(
      `/devices/${editDevice.id}`,
      payload
    );


    setDevices(
      devices.map(d =>
        d.id === response.data.id
        ? response.data
        : d
      )
    );


    setEditDevice(null);

    setMessage("Device updated successfully");

    setTimeout(()=>{
      setMessage("");
    },3000);

  }
  catch(err){

    console.error(
      "Update Error",
      err
    );

    setMessage("Failed to update device");

    setTimeout(()=>{
      setMessage("");
    },3000);

  }

}

async function deleteDevice(id){

  if(!confirm("Delete this device?")) return;

  try{

    await api.delete(`/devices/${id}`);

    setMessage("Device deleted successfully");

    setTimeout(()=>{
      setMessage("");
    },3000);

    setDevices(
      devices.filter(
        d => d.id !== id
      )
    );

  }
  catch(err){

    console.error(
      "Delete Error",
      err
    );

    setMessage("Failed to delete device");

    setTimeout(()=>{
      setMessage("");
    },3000);

  }

  }

  const filtered = devices.filter(
    device =>
    device.hostname
    .toLowerCase()
    .includes(search.toLowerCase())
  );


  return (

    <div>

      {
        message && (
          <div
            className={
              message.startsWith("Failed")
              ? "bg-red-600 text-white p-4 rounded-lg mb-5"
              : "bg-green-600 text-white p-4 rounded-lg mb-5"
            }
          >
            {message}
          </div>
        )
      }

      <div className="flex justify-between items-center mb-6">

        <div>
          <h1 className="text-4xl font-bold text-white">
            Devices
          </h1>

          <p className="text-cyan-400 mt-2">
            Access: {role}
          </p>
        </div>


        {isAdmin && (
          <button
            onClick={() => setShowAdd(true)}
            className="bg-cyan-600 hover:bg-cyan-700 px-5 py-3 rounded-lg font-semibold"
          >
            Add Device
          </button>
        )}

      </div>


      <input

        className="bg-slate-800 text-white p-3 rounded-lg mb-6 w-full"

        placeholder="Search device..."

        value={search}

        onChange={
          e=>setSearch(e.target.value)
        }

      />


{
 showAdd && isAdmin && (
   <AddDevice
    onAdded={(device)=>{
      setDevices([
        ...devices,
        device
      ]);
      setShowAdd(false);
    }}
   />
 )
}


{
 editDevice && (

  <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">

   <div className="bg-slate-900 p-8 rounded-xl w-full max-w-md">

    <h2 className="text-cyan-400 text-2xl font-bold mb-5">
      Edit Device
    </h2>

    <input
      placeholder="Hostname"
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.hostname}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        hostname:e.target.value
      })}
    />

    <input
      placeholder="IP Address"
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.ip || ""}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        ip:e.target.value
      })}
    />

    <input
      placeholder="CPU (%)"
      type="number"
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.cpu ?? 0}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        cpu:e.target.value
      })}
    />

    <input
      placeholder="RAM (%)"
      type="number"
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.ram ?? 0}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        ram:e.target.value
      })}
    />

    <input
      placeholder="Disk (%)"
      type="number"
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.disk ?? 0}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        disk:e.target.value
      })}
    />

    <select
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={String(editDevice.status || "").toLowerCase()}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        status:e.target.value
      })}
    >
      <option value="online">Online</option>
      <option value="offline">Offline</option>
    </select>

    <div className="flex gap-3">

      <button
        onClick={updateDevice}
        className="bg-green-600 hover:bg-green-700 px-5 py-3 rounded-lg font-semibold"
      >
        Save Changes
      </button>


      <button
        onClick={()=>setEditDevice(null)}
        className="bg-red-600 hover:bg-red-700 px-5 py-3 rounded-lg font-semibold"
      >
        Cancel
      </button>

    </div>


   </div>

  </div>

 )
}

<div className="grid gap-5">


      {
        filtered.map(device=>(


          <div
          key={device.id}
          className="bg-slate-800 rounded-xl p-6"
          >

            <h2 className="text-2xl text-cyan-400">

              {device.hostname}

            </h2>


            <p className="text-gray-400">
              IP: {device.ip}
            </p>

            <p className="text-gray-400 mt-2">
              Last Seen: {
                device.last_seen
                ? new Date(device.last_seen).toLocaleString()
                : "Unknown"
              }
            </p>


            <StatusBadge status={device.status}/>


            <div className="grid grid-cols-3 mt-4">

              <p>
                CPU: {device.cpu ?? 0}%
              </p>

              <p>
                RAM: {device.ram ?? 0}%
              </p>

              <p>
                Disk: {device.disk ?? 0}%
              </p>

            </div>


            {isAdmin && (

              <div className="flex gap-3 mt-5">

                <button
                  onClick={() => setEditDevice(device)}
                  className="bg-yellow-600 px-4 py-2 rounded"
                >
                  Edit
                </button>


                <button
                  onClick={() => deleteDevice(device.id)}
                  className="bg-red-600 px-4 py-2 rounded"
                >
                  Delete
                </button>

              </div>

            )}


          </div>


        ))
      }


      </div>


    </div>

  );

}


export default Devices;
