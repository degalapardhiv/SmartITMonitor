function StatsCard({ title, value, color }) {
  return (
    <div className="ui-stat">
      <div className="ui-stat-label">{title}</div>

      <p
        className={`ui-stat-value ${color || ""}`}
      >
        {value}
      </p>
    </div>
  );
}

export default StatsCard;
