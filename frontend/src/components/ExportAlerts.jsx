import api from "../services/api";
import * as XLSX from "xlsx";


export default function ExportAlerts(){

async function exportAlerts(){

    const res = await api.get("/alerts/");

    const worksheet = XLSX.utils.json_to_sheet(
        res.data.map(alert => ({
            Device: alert.hostname,
            Type: alert.alert_type,
            Value: alert.value,
            Message: alert.message,
            Severity: alert.severity,
            Time: alert.created_at
        }))
    );


    const workbook = XLSX.utils.book_new();

    XLSX.utils.book_append_sheet(
        workbook,
        worksheet,
        "Alerts"
    );


    XLSX.writeFile(
        workbook,
        "smart-monitor-alerts.xlsx"
    );

}


return (

<button
onClick={exportAlerts}
className="px-4 py-2 rounded-lg bg-blue-600 text-white"
>
Export Alerts
</button>

);

}
