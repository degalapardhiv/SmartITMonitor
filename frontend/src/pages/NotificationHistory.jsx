import { useEffect, useState } from "react";

import api from "../services/api";
import useWebSocket from "../hooks/useWebSocket";


export default function NotificationHistory(){

  const [history,setHistory] = useState([]);

const liveData = useWebSocket();


  useEffect(()=>{

    loadHistory();

  },[]);


useEffect(()=>{

    if(
      liveData &&
      liveData.type === "notification"
    ){

      setHistory(
        prev => [
          liveData,
          ...prev
        ]
      );

    }

},[liveData]);



  async function loadHistory(){

    const res = await api.get(
      "/alerts/notifications/history"
    );

    setHistory(
      res.data
    );

  }



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
            history.map(item=>(

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
                  {item.created_at}
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
