export function BarChart({ data, valueFormatter = (value) => value }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  return (
    <div className="bar-chart">
      {data.map((item) => (
        <div className="bar-row" key={item.label}>
          <span>{item.label}</span>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(item.value / max) * 100}%` }} /></div>
          <strong>{valueFormatter(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

export function DonutChart({ data, centerLabel }) {
  const total = data.reduce((sum, item) => sum + item.value, 0) || 1;
  let offset = 0;
  const segments = data.map((item, index) => {
    const start = offset;
    const size = (item.value / total) * 100;
    offset += size;
    return `${item.color || `var(--chart-${(index % 5) + 1})`} ${start}% ${offset}%`;
  }).join(', ');
  return (
    <div className="donut-group">
      <div className="donut" style={{ background: `conic-gradient(${segments})` }}><div><strong>{total}</strong><span>{centerLabel}</span></div></div>
      <div className="legend">{data.map((item) => <span key={item.label}><i style={{ background: item.color }} />{item.label}: {item.value}</span>)}</div>
    </div>
  );
}
