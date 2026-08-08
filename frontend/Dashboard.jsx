import Layout from "../components/layout/Layout";
import UsageChart from "../components/charts/UsageChart";

function Dashboard() {
  const devices = [
    {
      hostname: "LAB-PC-001",
      cpu: 25,
      ram: 40,
      disk: 60,
    },
    {
      hostname: "LAB-PC-002",
      cpu: 70,
      ram: 55,
      disk: 45,
    },
  ];

  return (
    <Layout>
      <h1 className="text-4xl font-bold mb-6">
        Usage Chart Test
      </h1>

      <UsageChart devices={devices} />
    </Layout>
  );
}

export default Dashboard;
