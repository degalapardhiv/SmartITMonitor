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
  const labels = devices.map((d) => d.hostname);

  const data = {
    labels,
    datasets: [
      {
        label: "CPU %",
        data: devices.map((d) => d.cpu ?? 0),
        backgroundColor: "rgba(6,182,212,0.8)",
        borderRadius: 6,
      },
      {
        label: "RAM %",
        data: devices.map((d) => d.ram ?? 0),
        backgroundColor: "rgba(34,197,94,0.8)",
        borderRadius: 6,
      },
      {
        label: "Disk %",
        data: devices.map((d) => d.disk ?? 0),
        backgroundColor: "rgba(245,158,11,0.8)",
        borderRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: "System Resource Usage",
        color: "#ffffff",
        font: {
          size: 18,
        },
      },
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
          color: "#334155",
        },
      },
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          color: "#ffffff",
        },
        grid: {
          color: "#334155",
        },
      },
    },
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6 shadow-lg">
      <div className="h-96">
        <Bar data={data} options={options} />
      </div>
    </div>
  );
}

export default UsageChart;
