import api from "../services/api";

import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";


export default function ExportAlertsPDF(){


async function exportPDF(){

    const res = await api.get("/alerts");


    const doc = new jsPDF();


    doc.setFontSize(18);

    doc.text(
        "Smart IT Monitor - Alert Report",
        14,
        20
    );


    const rows = res.data.map(alert => [

        alert.hostname,

        alert.alert_type,

        alert.value,

        alert.severity,

        alert.message,

        alert.created_at

    ]);


    autoTable(doc,{

        startY:30,

        head:[[
            "Device",
            "Type",
            "Value",
            "Severity",
            "Message",
            "Time"
        ]],

        body:rows

    });


    doc.save(
        "smart-monitor-alert-report.pdf"
    );

}



return (

<button

onClick={exportPDF}

className="px-4 py-2 rounded-lg bg-red-600 text-white"

>

Export PDF

</button>

);


}
