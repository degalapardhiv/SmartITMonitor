import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

import { Bar } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function UsageChart({ devices = [] }) {
  const data = {
    labels: devices.map((d) => d.hostname),
    datasets: [
      {
        label: "CPU %",
        data: devices.map((d) => d.cpu),
        backgroundColor: "#06b6d4",
      },
      {
        label: "RAM %",
        data: devices.map((d) => d.ram),
        backgroundColor: "#22c55e",
      },
      {
        label: "Disk %",
        data: devices.map((d) => d.disk),
        backgroundColor: "#f59e0b",
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl">
      <h2 className="text-xl font-bold text-white mb-4">
        Resource Usage
      </h2>

      <div className="h-96">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}

export default UsageChart;
