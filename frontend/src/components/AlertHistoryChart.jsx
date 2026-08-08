import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer
} from "recharts";

import api from "../services/api";


export default function AlertHistoryChart(){

    const [data,setData] = useState([]);


    useEffect(()=>{

        api.get("/alerts/history")
        .then(res=>{

            setData(
                res.data.map(item=>({
                    time: new Date(item.created_at)
                    .toLocaleTimeString(),

                    value:item.value || 0
                }))
            );

        });

    },[]);


    return (

        <div className="mt-6">

            <h2 className="text-xl font-bold mb-4">
                Alert History
            </h2>


            <ResponsiveContainer width="100%" height={300}>

                <LineChart data={data}>

                    <CartesianGrid />

                    <XAxis dataKey="time" />

                    <YAxis />

                    <Tooltip />

                    <Line
                        type="monotone"
                        dataKey="value"
                    />

                </LineChart>

            </ResponsiveContainer>


        </div>

    );

}
