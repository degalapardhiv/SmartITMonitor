import { useEffect, useState } from "react";
import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";
import { useAuth } from "../context/AuthContext";
import AddDevice from "../components/devices/AddDevice";



function StatusBadge({status}){

  return (

    <span
      className={
        status === "Online"
        ? "bg-green-600 px-3 py-1 rounded-full text-sm"
        : "bg-red-600 px-3 py-1 rounded-full text-sm"
      }
    >
      {status}
    </span>

  );

}

function Devices(){

  const { role } = useAuth();

  const [devices,setDevices] = useState([]);
  const liveData = useWebSocket();
  const [search,setSearch] = useState("");
  const [showAdd,setShowAdd] = useState(false);
  const [editDevice,setEditDevice] = useState(null);

  const [message,setMessage] = useState("");


  useEffect(()=>{

    loadDevices();

  },[]);


  useEffect(()=>{

    if(
      liveData &&
      liveData.type === "device_update"
    ){

      setDevices(prev => {

        const exists = prev.find(
          d => d.id === liveData.device.id
        );

        if(exists){

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

  },[liveData]);


  

async function updateDevice(){

  try{

    const response = await api.put(
      `/devices/${editDevice.id}`,
      editDevice
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

  }

}

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
          <div className="bg-green-600 text-white p-4 rounded-lg mb-5">
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


        {role === "Admin" && (
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
 showAdd && role === "Admin" && (
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
      className="w-full bg-slate-700 text-white p-3 rounded mb-4"
      value={editDevice.hostname}
      onChange={(e)=>setEditDevice({
        ...editDevice,
        hostname:e.target.value
      })}
    />


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
              Last Seen: {device.last_seen || "Unknown"}
            </p>


            <StatusBadge status={device.status}/>


            <div className="grid grid-cols-3 mt-4">

              <p>
                CPU: {device.cpu}%
              </p>

              <p>
                RAM: {device.ram}%
              </p>

              <p>
                Disk: {device.disk}%
              </p>

            </div>


            {role === "Admin" && (

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
