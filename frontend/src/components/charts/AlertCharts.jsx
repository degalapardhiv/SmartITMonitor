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

const PALETTE = ["#ef4444", "#f59e0b", "#10b981", "#64748b"];

const TOOLTIP_STYLE = {
  backgroundColor: "rgba(17, 24, 39, 0.95)",
  border: "1px solid rgba(56, 189, 248, 0.15)",
  color: "#f1f5f9",
  borderRadius: "10px",
  backdropFilter: "blur(8px)",
  boxShadow: "0 8px 25px rgba(0, 0, 0, 0.3)",
};

const TICK_STYLE = { fill: "#64748b", fontSize: 12 };

export default function AlertCharts({ data }) {
  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="ui-card p-6">
        <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
          Severity Distribution
        </h2>

        <PieChart width={350} height={300}>
          <Pie
            data={data.severity}
            dataKey="value"
            nameKey="name"
            outerRadius={100}
          >
            {data.severity.map((entry, index) => (
              <Cell
                key={index}
                fill={PALETTE[index % PALETTE.length]}
              />
            ))}
          </Pie>

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} />
        </PieChart>
      </div>

      <div className="ui-card p-6">
        <h2 className="text-lg font-bold text-white mb-4 tracking-tight">
          Alert Types
        </h2>

        <BarChart
          width={400}
          height={300}
          data={data.types}
        >
          <XAxis dataKey="name" tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />
          <YAxis tick={TICK_STYLE} stroke="rgba(56, 189, 248, 0.1)" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} cursor={{ fill: "rgba(6, 182, 212, 0.04)" }} />

          <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} />
        </BarChart>
      </div>
    </div>
  );
}
