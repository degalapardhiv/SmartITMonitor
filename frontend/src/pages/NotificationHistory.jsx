import { useEffect, useState } from "react";

import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";


function formatDateTime(value){

  if(!value) return "--";

  const date = new Date(value);

  if(isNaN(date.getTime())) return "--";

  return date.toLocaleString();

}


export default function NotificationHistory(){

  const [history,setHistory] = useState([]);


  useWebSocket((message) => {

    if (
      message &&
      message.type === "notification"
    ){

      setHistory(
        prev => [
          message,
          ...prev
        ]
      );

    }

  });


  async function loadHistory(){

    try{

      const res = await api.get(
        "/alerts/notifications/history"
      );

      setHistory(
        Array.isArray(res.data) ? res.data : []
      );

    }
    catch(err){

      console.error(
        "Load Notification History Error",
        err
      );

    }

  }


  useEffect(()=>{

    async function sync() {
      await loadHistory();
    }

    sync();

  },[]);



  return (

    <div className="text-white">

      <h1 className="text-4xl font-bold mb-8">
        Notification History
      </h1>


      <div className="bg-slate-800 rounded-xl p-6">

        <table className="w-full">

          <thead>

            <tr>
              <th>Alert ID</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Message</th>
              <th>Time</th>
            </tr>

          </thead>


          <tbody>

          {
            history.map(item => (

              <tr key={item.id}>

                <td>
                  {item.alert_id}
                </td>

                <td>
                  {item.channel}
                </td>

                <td>
                  {item.status}
                </td>

                <td>
                  {item.message}
                </td>

                <td>
                  {formatDateTime(item.created_at)}
                </td>

              </tr>

            ))
          }

          </tbody>


        </table>

      </div>

    </div>

  );

}
