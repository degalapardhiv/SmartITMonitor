function StatsCard({ title, value, color }) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 shadow-lg hover:scale-105 transition">
      <p className="text-gray-400">{title}</p>

      <h1 className={`text-4xl font-bold mt-2 ${color}`}>
        {value}
      </h1>
    </div>
  );
}

export default StatsCard;
