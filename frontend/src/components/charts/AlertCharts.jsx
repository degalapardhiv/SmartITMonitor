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

const PALETTE = ["#e50914", "#f5a623", "#46d369", "#a3a3a3"];

const TOOLTIP_STYLE = {
  backgroundColor: "#1f1f1f",
  border: "1px solid #333333",
  color: "#ffffff",
  borderRadius: "4px"
};

const TICK_STYLE = { fill: "#a3a3a3", fontSize: 12 };

export default function AlertCharts({ data }) {
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
            {data.severity.map((entry, index) => (
              <Cell
                key={index}
                fill={PALETTE[index % PALETTE.length]}
              />
            ))}
          </Pie>

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} />
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
          <XAxis dataKey="name" tick={TICK_STYLE} stroke="#333333" />
          <YAxis tick={TICK_STYLE} stroke="#333333" />

          <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#ffffff" }} cursor={{ fill: "rgba(255,255,255,0.05)" }} />

          <Bar dataKey="value" fill="#e50914" />
        </BarChart>
      </div>
    </div>
  );
}
