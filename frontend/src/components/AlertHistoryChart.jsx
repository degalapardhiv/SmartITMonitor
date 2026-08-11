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

const TOOLTIP_STYLE = {
    backgroundColor: "#1f1f1f",
    border: "1px solid #333333",
    color: "#ffffff",
    borderRadius: "4px"
};

const TICK_STYLE = { fill: "#a3a3a3", fontSize: 12 };


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

                    <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />

                    <XAxis dataKey="time" tick={TICK_STYLE} stroke="#333333" />

                    <YAxis tick={TICK_STYLE} stroke="#333333" />

                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} />

                    <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#e50914"
                        strokeWidth={3}
                        dot={false}
                    />

                </LineChart>

            </ResponsiveContainer>


        </div>

    );

}
