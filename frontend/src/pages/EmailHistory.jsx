import { useEffect, useState } from "react";

import api from "../services/api";


export default function EmailHistory(){

  const [history,setHistory] = useState([]);


  useEffect(()=>{

    loadHistory();

  },[]);



  async function loadHistory(){

    const res = await api.get(
      "/settings/email/history"
    );

    setHistory(
      res.data
    );

  }



  return (

    <div className="text-white">

      <h1 className="text-4xl font-bold mb-8">
        Email History
      </h1>


      <div className="bg-slate-800 rounded-xl p-6">


        <table className="w-full">


          <thead>

            <tr>

              <th className="text-left">
                Receiver
              </th>

              <th className="text-left">
                Subject
              </th>

              <th className="text-left">
                Status
              </th>

              <th className="text-left">
                Date
              </th>

            </tr>

          </thead>


          <tbody>


          {
            history.map(item=>(

              <tr key={item.id}>

                <td>
                  {item.receiver}
                </td>


                <td>
                  {item.subject}
                </td>


                <td>
                  {item.status}
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
