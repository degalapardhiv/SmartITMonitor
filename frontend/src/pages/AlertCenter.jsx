import { useEffect, useState } from "react";

import api from "../services/api";

import useWebSocket from "../hooks/useWebSocket";


export default function AlertCenter(){

  const [alerts,setAlerts] = useState([]);

  const [page,setPage] = useState(1);

  const [severity,setSeverity] = useState("ALL");

  const [type,setType] = useState("ALL");


  const liveData = useWebSocket();



  useEffect(()=>{

    loadAlerts(page);

  },[]);



  useEffect(()=>{

    if(
      liveData &&
      liveData.type === "alert"
    ){

      setAlerts(
        prev => [
          liveData.alert,
          ...prev
        ]
      );

    }

  },[liveData]);



  
async function resolveAlert(id){

  await api.patch(
    `/alerts/${id}/resolve`
  );


  loadAlerts(page);

}

async function loadAlerts(currentPage=1){

    const res = await api.get(
      `/alerts/?page=${currentPage}&limit=50`
    );

    setAlerts(
      res.data
    );

  }



  const filteredAlerts = alerts.filter(
    alert => {

      const severityMatch =
        severity === "ALL" ||
        alert.severity === severity;


      const typeMatch =
        type === "ALL" ||
        alert.alert_type === type;


      return severityMatch && typeMatch;

    }
  );



  function badgeColor(level){

    if(level === "HIGH")
      return "bg-red-600";


    if(level === "MEDIUM")
      return "bg-orange-500";


    return "bg-green-600";

  }



  return (

    <div className="text-white">


      <h1 className="text-4xl font-bold mb-8">
        Alert Center
      </h1>


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
            filteredAlerts.map(alert=>(

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
                    alert.status === "RESOLVED"

                    ?

                    <span className="text-green-400">
                      Done
                    </span>

                    :

                    <button
                      onClick={() => resolveAlert(alert.id)}
                      className="bg-red-600 px-3 py-1 rounded"
                    >
                      Resolve
                    </button>
                  }

                </td>


                <td>
                  {alert.message}
                </td>


                <td>
                  {alert.created_at}
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
            className="bg-slate-700 px-4 py-2 rounded"
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
