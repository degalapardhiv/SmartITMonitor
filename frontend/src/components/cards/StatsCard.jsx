function StatsCard({ title, value, color }) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 shadow-lg">
      <h3 className="text-gray-400">{title}</h3>

      <h1
        className={`text-4xl font-bold ${color}`}
      >
        {value}
      </h1>
    </div>
  );
}

export default StatsCard;
