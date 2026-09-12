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
  backgroundColor: "rgba(17, 24, 39, 0.95)",
  border: "1px solid rgba(56, 189, 248, 0.15)",
  color: "#f1f5f9",
  borderRadius: "10px"
};

const TICK_STYLE = { fill: "#64748b", fontSize: 12 };

function RAMChart({ data }) {
  const chartData = data
    .slice()
    .reverse()
    .map((item) => ({
      time: new Date(item.created_at).toLocaleTimeString(),
      ram: item.ram,
    }));

  return (
    <div className="ui-card p-6">
      <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
        RAM Usage
      </h2>

      <ResponsiveContainer
        width="100%"
        height={300}
      >
        <LineChart data={chartData}>
          <CartesianGrid stroke="rgba(56, 189, 248, 0.06)" strokeDasharray="3 3" />

          <XAxis dataKey="time" tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

          <YAxis domain={[0, 100]} tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} />

          <Line
            type="monotone"
            dataKey="ram"
            stroke="#f59e0b"
            strokeWidth={2.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default RAMChart;
