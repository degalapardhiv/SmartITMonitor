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
        backgroundColor: "#e50914",
      },
      {
        label: "RAM %",
        data: devices.map((d) => d.ram),
        backgroundColor: "#46d369",
      },
      {
        label: "Disk %",
        data: devices.map((d) => d.disk),
        backgroundColor: "#f5a623",
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: "#ffffff",
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#ffffff",
        },
        grid: {
          color: "rgba(255,255,255,0.08)",
        },
      },
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          color: "#ffffff",
        },
        grid: {
          color: "rgba(255,255,255,0.08)",
        },
      },
    },
  };

  return (
    <div className="bg-slate-800 p-5 rounded-xl">
      <h2 className="text-xl font-bold text-white mb-4">
        Resource Usage
      </h2>

      <Bar data={data} options={options} />
    </div>
  );
}

export default UsageChart;
