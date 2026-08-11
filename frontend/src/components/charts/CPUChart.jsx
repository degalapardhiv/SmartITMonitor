import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";

const TOOLTIP_STYLE = {
  backgroundColor: "#1f1f1f",
  border: "1px solid #333333",
  color: "#ffffff",
  borderRadius: "4px"
};

const TICK_STYLE = { fill: "#a3a3a3", fontSize: 12 };

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
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />

          <XAxis dataKey="time" tick={TICK_STYLE} stroke="#333333" />

          <YAxis domain={[0, 100]} tick={TICK_STYLE} stroke="#333333" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} />

          <Line
            type="monotone"
            dataKey="cpu"
            stroke="#e50914"
            strokeWidth={3}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default CPUChart;
