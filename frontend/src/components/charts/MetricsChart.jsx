import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";


function MetricsChart({data}) {


  return (

    <div className="bg-slate-800 rounded-xl p-6 mt-8">


      <h2 className="text-2xl font-bold text-white mb-5">
        Performance History
      </h2>


      <ResponsiveContainer
        width="100%"
        height={300}
      >

        <LineChart data={data}>


          <XAxis dataKey="time" />

          <YAxis />

          <Tooltip />


          <Line
            dataKey="cpu"
            strokeWidth={3}
          />


          <Line
            dataKey="ram"
            strokeWidth={3}
          />


          <Line
            dataKey="disk"
            strokeWidth={3}
          />


        </LineChart>


      </ResponsiveContainer>


    </div>

  );

}


export default MetricsChart;
