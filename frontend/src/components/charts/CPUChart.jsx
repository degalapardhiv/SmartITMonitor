import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";

function CPUChart({ data }) {

  const chartData = data
    .slice()
    .reverse()
    .map((item) => ({
      time: new Date(item.created_at).toLocaleTimeString(),
      cpu: item.cpu,
    }));

  return (
    <div className="bg-slate-800 rounded-xl p-6">

      <h2 className="text-2xl font-bold mb-4">
        CPU Usage
      </h2>

      <ResponsiveContainer
        width="100%"
        height={300}
      >

        <LineChart data={chartData}>

          <CartesianGrid strokeDasharray="3 3" />

          <XAxis dataKey="time" />

          <YAxis domain={[0, 100]} />

          <Tooltip />

          <Line
            type="monotone"
            dataKey="cpu"
            stroke="#22c55e"
            strokeWidth={3}
          />

        </LineChart>

      </ResponsiveContainer>

    </div>
  );
}

export default CPUChart;
