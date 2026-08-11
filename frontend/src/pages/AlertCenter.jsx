import { useEffect, useState } from "react";

import api from "../services/api";

import useWebSocket from "../hooks/useWebSocket";


function formatDateTime(value){

  if(!value) return "--";

  const date = new Date(value);

  if(isNaN(date.getTime())) return "--";

  return date.toLocaleString();

}


export default function AlertCenter(){

  const [alerts,setAlerts] = useState([]);

  const [page,setPage] = useState(1);

  const [severity,setSeverity] = useState("ALL");

  const [type,setType] = useState("ALL");

  const [loading,setLoading] = useState(true);

  const [error,setError] = useState("");

  const [resolvingId,setResolvingId] = useState(null);


  useWebSocket((message) => {

    if (!message || !message.type) return;

    if (message.type === "alert_resolved" && message.alerts) {

      const ids = new Set(message.alerts.map(a => a.id));

      setAlerts(prev =>
        prev.map(a =>
          ids.has(a.id) && a.status === "OPEN"
          ? { ...a, status: "RESOLVED", resolved_at: a.resolved_at }
          : a
        )
      );

      return;

    }

    if (message.type !== "alert" || !message.alert) return;

    const alert = message.alert;

    setAlerts(prev => {

      const exists = prev.some(a => a.id === alert.id);

      if (exists) {

        return prev.map(a => a.id === alert.id ? alert : a);

      }

      return [
        alert,
        ...prev
      ];

    });

  });


async function loadAlerts(currentPage=1){

  setLoading(true);

  try{

    const res = await api.get(
      `/alerts/?page=${currentPage}&limit=50`
    );

    setAlerts(
      Array.isArray(res.data) ? res.data : []
    );

    setError("");

  }
  catch(err){

    console.error(
      "Load Alerts Error",
      err
    );

    setError("Failed to load alerts");

  }
  finally{

    setLoading(false);

  }

}


  useEffect(()=>{

    async function sync() {
      await loadAlerts(page);
    }

    sync();

  },[page]);



async function resolveAlert(id){

  setResolvingId(id);

  try{

    await api.patch(
      `/alerts/${id}/resolve`
    );

    setAlerts(prev =>
      prev.map(a =>
        a.id === id
        ? { ...a, status: "RESOLVED" }
        : a
      )
    );

  }
  catch(err){

    console.error(
      "Resolve Alert Error",
      err
    );

    setError("Failed to resolve alert");

    setTimeout(()=>setError(""), 4000);

  }
  finally{

    setResolvingId(null);

  }

}


  const filteredAlerts = alerts.filter(
    alert => {

      const severityMatch =
        severity === "ALL" ||
        String(alert.severity || "").toUpperCase() === severity;


      const typeMatch =
        type === "ALL" ||
        String(alert.alert_type || "").toUpperCase() === type;


      return severityMatch && typeMatch;

    }
  );



  function badgeColor(level){

    const lvl = String(level || "").toUpperCase();

    if(lvl === "HIGH")
      return "bg-red-600";


    if(lvl === "MEDIUM")
      return "bg-orange-500";


    return "bg-green-600";

  }



  return (

    <div className="text-white">


      <h1 className="text-4xl font-bold mb-8">
        Alert Center
      </h1>


      {error && (
        <div className="mb-4 bg-red-600 text-white p-4 rounded-lg">
          {error}
        </div>
      )}


      <div className="flex gap-4 mb-6">


        <select
          value={severity}
          onChange={
            e=>setSeverity(e.target.value)
          }
          className="bg-slate-800 p-3 rounded"
        >

          <option>ALL</option>
          <option>HIGH</option>
          <option>MEDIUM</option>
          <option>LOW</option>

        </select>



        <select
          value={type}
          onChange={
            e=>setType(e.target.value)
          }
          className="bg-slate-800 p-3 rounded"
        >

          <option>ALL</option>
          <option>CPU</option>
          <option>RAM</option>
          <option>DISK</option>
          <option>USB_PENDING</option>
          <option>USB_REJECTED</option>

        </select>


      </div>



      <div className="bg-slate-800 rounded-xl p-6">


        <table className="w-full">


          <thead>

          <tr>

            <th>Device</th>
            <th>Type</th>
            <th>Value</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Action</th>
            <th>Message</th>
            <th>Time</th>

          </tr>

          </thead>



          <tbody>


          {
            loading ? (

              <tr>
                <td
                  colSpan="8"
                  className="text-center py-8 text-gray-400"
                >
                  Loading alerts...
                </td>
              </tr>

            ) : filteredAlerts.length === 0 ? (

              <tr>
                <td
                  colSpan="8"
                  className="text-center py-8 text-gray-400"
                >
                  No alerts found.
                </td>
              </tr>

            ) : filteredAlerts.map(alert=>(
              <tr key={alert.id}>


                <td>
                  {alert.hostname}
                </td>


                <td>
                  {alert.alert_type}
                </td>


                <td>
                  {alert.value}
                </td>


                <td>

                  <span
                    className={
                      `px-3 py-1 rounded-full text-sm ${badgeColor(alert.severity)}`
                    }
                  >
                    {alert.severity}
                  </span>

                </td>


                <td>
                  {alert.status || "OPEN"}
                </td>


                <td>

                  {
                    String(alert.status || "").toUpperCase() === "RESOLVED"

                    ?

                    <span className="text-green-400">
                      Done
                    </span>

                    :

                    <button
                      onClick={() => resolveAlert(alert.id)}
                      disabled={resolvingId === alert.id}
                      className="bg-red-600 px-3 py-1 rounded disabled:bg-slate-600"
                    >
                      {resolvingId === alert.id ? "Resolving..." : "Resolve"}
                    </button>
                  }

                </td>


                <td>
                  {alert.message}
                </td>


                <td>
                  {formatDateTime(alert.created_at)}
                </td>


              </tr>
            ))
          }


          </tbody>


        </table>
        <div className="flex gap-4 mt-6">

          <button
            onClick={()=>{
              if(page>1){
                setPage(page-1);
                loadAlerts(page-1);
              }
            }}
            className="bg-slate-700 px-4 py-2 rounded disabled:opacity-50"
            disabled={page <= 1}
          >
            Previous
          </button>


          <span className="px-4 py-2">
            Page {page}
          </span>


          <button
            onClick={()=>{
              setPage(page+1);
              loadAlerts(page+1);
            }}
            className="bg-cyan-600 px-4 py-2 rounded"
          >
            Next
          </button>

        </div>



      </div>


    </div>

  );

}
