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
    backgroundColor: "rgba(17, 24, 39, 0.95)",
    border: "1px solid rgba(56, 189, 248, 0.15)",
    color: "#f1f5f9",
    borderRadius: "10px"
};

const TICK_STYLE = { fill: "#64748b", fontSize: 12 };


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

        <div className="ui-card p-6">

            <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
                Alert History
            </h2>


            <ResponsiveContainer width="100%" height={300}>

                <LineChart data={data}>

                    <CartesianGrid stroke="rgba(56, 189, 248, 0.06)" strokeDasharray="3 3" />

                    <XAxis dataKey="time" tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

                    <YAxis tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} />

                    <Line
                        type="monotone"
                        dataKey="value"
                        stroke="#06b6d4"
                        strokeWidth={2.5}
                        dot={false}
                    />

                </LineChart>

            </ResponsiveContainer>


        </div>

    );

}
