import { useEffect, useState } from "react";
import api from "../services/api";

export default function Alerts(){

    const [alerts,setAlerts] = useState([]);
    const [error,setError] = useState("");

    useEffect(()=>{

        api.get("/alerts/")
        .then((res)=>{

            setAlerts(
                Array.isArray(res.data)
                ? res.data
                : []
            );

        })
        .catch((err)=>{

            console.log(err);
            setError("Failed to load alerts");

        });

    },[]);


    return (

        <div>

            <h1>Alerts</h1>

            {error && (
                <p>{error}</p>
            )}

            <table>

                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Message</th>
                        <th>Severity</th>
                    </tr>
                </thead>

                <tbody>

                {
                    alerts.map((alert)=>(
                        <tr key={alert.id}>

                            <td>
                                {alert.hostname || alert.device_id}
                            </td>

                            <td>
                                {alert.alert_type || "Unknown"}
                            </td>

                            <td>
                                {alert.value || "-"}
                            </td>

                            <td>
                                {alert.message || "-"}
                            </td>

                            <td>
                                {alert.severity || "-"}
                            </td>

                        </tr>
                    ))
                }

                </tbody>

            </table>

        </div>

    );
}
