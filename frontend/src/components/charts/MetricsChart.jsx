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
  backgroundColor: "#1f1f1f",
  border: "1px solid #333333",
  color: "#ffffff",
  borderRadius: "4px"
};

const TICK_STYLE = { fill: "#a3a3a3", fontSize: 12 };

function MetricsChart({ data }) {
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
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />

          <XAxis dataKey="time" tick={TICK_STYLE} stroke="#333333" />

          <YAxis tick={TICK_STYLE} stroke="#333333" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} />

          <Line
            dataKey="cpu"
            stroke="#e50914"
            strokeWidth={3}
            dot={false}
          />

          <Line
            dataKey="ram"
            stroke="#f5a623"
            strokeWidth={3}
            dot={false}
          />

          <Line
            dataKey="disk"
            stroke="#46d369"
            strokeWidth={3}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MetricsChart;
