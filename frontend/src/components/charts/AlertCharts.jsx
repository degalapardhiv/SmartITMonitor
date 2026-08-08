import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip
} from "recharts";


export default function AlertCharts({data}){


return (

<div className="grid lg:grid-cols-2 gap-6">


<div className="bg-slate-800 rounded-xl p-6">

<h2 className="text-xl font-bold mb-4">
Severity Distribution
</h2>


<PieChart width={350} height={300}>

<Pie
data={data.severity}
dataKey="value"
nameKey="name"
outerRadius={100}
>

{
data.severity.map(
(entry,index)=>(
<Cell key={index}/>
)
)
}

</Pie>

<Tooltip/>

</PieChart>


</div>




<div className="bg-slate-800 rounded-xl p-6">

<h2 className="text-xl font-bold mb-4">
Alert Types
</h2>


<BarChart
width={400}
height={300}
data={data.types}
>

<XAxis dataKey="name"/>

<YAxis/>

<Tooltip/>

<Bar dataKey="value"/>


</BarChart>


</div>


</div>

);

}
