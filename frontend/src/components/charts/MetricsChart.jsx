import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const TOOLTIP_STYLE = {
  backgroundColor: "rgba(17, 24, 39, 0.95)",
  border: "1px solid rgba(56, 189, 248, 0.15)",
  color: "#f1f5f9",
  borderRadius: "10px",
  backdropFilter: "blur(8px)",
  boxShadow: "0 8px 25px rgba(0, 0, 0, 0.3)",
};

const TICK_STYLE = { fill: "#64748b", fontSize: 12 };

function MetricsChart({ data }) {
  return (
    <div className="ui-card p-6">
      <h2 className="text-xl font-bold text-white mb-4 tracking-tight">
        Performance History
      </h2>

      <ResponsiveContainer
        width="100%"
        height={300}
      >
        <LineChart data={data}>
          <CartesianGrid stroke="rgba(56, 189, 248, 0.06)" strokeDasharray="3 3" />

          <XAxis dataKey="time" tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

          <YAxis tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} />

          <Line
            dataKey="cpu"
            stroke="#06b6d4"
            strokeWidth={2.5}
            dot={false}
          />

          <Line
            dataKey="ram"
            stroke="#f59e0b"
            strokeWidth={2.5}
            dot={false}
          />

          <Line
            dataKey="disk"
            stroke="#10b981"
            strokeWidth={2.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MetricsChart;
