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
          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />

          <XAxis dataKey="time" tick={TICK_STYLE} stroke="#333333" />

          <YAxis tick={TICK_STYLE} stroke="#333333" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} />

          <Line
            type="monotone"
            dataKey="cpu"
            name="CPU %"
            stroke="#e50914"
            strokeWidth={3}
            dot={false}
          />

          <Line
            type="monotone"
            dataKey="ram"
            name="RAM %"
            stroke="#f5a623"
            strokeWidth={3}
            dot={false}
          />

          <Line
            type="monotone"
            dataKey="disk"
            name="Disk %"
            stroke="#46d369"
            strokeWidth={3}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DeviceChart;
