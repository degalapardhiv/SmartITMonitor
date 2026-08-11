import { useState, useEffect } from "react";
import api from "../../services/api";

function AddDevice({ onAdded }) {

  const [device, setDevice] = useState({
    hostname:"",
    ip:"",
    cpu:"",
    ram:"",
    disk:"",
    status:"Online",
    department:"",
    lab:"",
    location:"",
    os:""
  });

  const [departments, setDepartments] = useState([]);


  useEffect(() => {

    async function sync() {
      try{

        const res = await api.get("/departments");

        setDepartments(res.data || []);

      }
      catch(err){
        console.error(
          "Departments Load Error",
          err
        );
      }
    }

    sync();

  }, []);


  function handleChange(e){
    setDevice({
      ...device,
      [e.target.name]: e.target.value
    });
  }


  async function submit(e){
    e.preventDefault();

    try{

      const res = await api.post("/devices", {
        ...device,
        cpu:Number(device.cpu),
        ram:Number(device.ram),
        disk:Number(device.disk)
      });

      onAdded(res.data);

    }
    catch(err){
      console.error(
        "Add Device Error",
        err
      );
    }
  }


  return (
    <form
      onSubmit={submit}
      className="bg-slate-800 p-6 rounded-xl mb-6"
    >

      <h2 className="text-xl text-cyan-400 mb-4">
        Add Device
      </h2>


      {Object.keys(device).map((key)=>(

        <input
          key={key}
          name={key}
          value={device[key]}
          onChange={handleChange}
          placeholder={key}
          list={key === "department" ? "departments-list" : undefined}
          className="w-full mb-3 bg-slate-700 p-3 rounded text-white"
        />

      ))}

      <datalist id="departments-list">
        {departments.map((dept)=>(
          <option key={dept.id} value={dept.name} />
        ))}
      </datalist>


      <button
        className="bg-green-600 px-5 py-3 rounded-lg"
      >
        Save Device
      </button>

    </form>
  );
}

export default AddDevice;
