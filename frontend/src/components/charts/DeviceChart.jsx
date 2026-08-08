import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";


function DeviceChart({ data }) {

  return (

    <div className="bg-slate-800 rounded-xl p-6 mt-6">

      <h2 className="text-xl text-cyan-400 mb-4">
        Live Performance
      </h2>


      <ResponsiveContainer
        width="100%"
        height={300}
      >

        <LineChart data={data}>

          <CartesianGrid />

          <XAxis dataKey="time" />

          <YAxis />

          <Tooltip />


          <Line
            type="monotone"
            dataKey="cpu"
            name="CPU %"
          />

          <Line
            type="monotone"
            dataKey="ram"
            name="RAM %"
          />

          <Line
            type="monotone"
            dataKey="disk"
            name="Disk %"
          />

        </LineChart>

      </ResponsiveContainer>

    </div>

  );

}


export default DeviceChart;
