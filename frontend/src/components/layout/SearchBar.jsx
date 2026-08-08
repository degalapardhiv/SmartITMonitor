function SearchBar({ value, onChange }) {
  return (
    <input
      className="w-full p-3 rounded-lg bg-slate-800 text-white"
      placeholder="Search hostname or IP..."
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export default SearchBar;
