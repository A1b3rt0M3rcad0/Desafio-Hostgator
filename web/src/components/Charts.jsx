import { useEffect, useMemo, useState } from 'react';

export function ChartEmptyState({ title = 'Nenhum dado neste escopo', description = 'Amplie o período ou remova alguns filtros.' }) {
  return (
    <div className="chart-empty-state">
      <span aria-hidden="true">⌁</span>
      <strong>{title}</strong>
      <small>{description}</small>
    </div>
  );
}

export function BarChart({ data, valueFormatter = (value) => value }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  if (!data.length) return <ChartEmptyState />;
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
  const total = data.reduce((sum, item) => sum + item.value, 0);
  if (!total) return <ChartEmptyState />;
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

function chartCoordinates(values, width, height, paddingX, paddingY) {
  const max = Math.max(...values, 1);
  const drawableWidth = width - paddingX * 2;
  const drawableHeight = height - paddingY * 2;
  return values.map((value, index) => ({
    x: paddingX + (values.length <= 1 ? drawableWidth / 2 : (index / (values.length - 1)) * drawableWidth),
    y: paddingY + drawableHeight - (Math.max(value || 0, 0) / max) * drawableHeight,
  }));
}

function compactDate(value) {
  if (!value) return '—';
  const parsed = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' }).format(parsed);
}

export function TimeSeriesChart({ data, mode, modes, onModeChange }) {
  const [selectedIndex, setSelectedIndex] = useState(Math.max(data.length - 1, 0));
  const config = modes.find((item) => item.value === mode) || modes[0];

  useEffect(() => setSelectedIndex(Math.max(data.length - 1, 0)), [data]);

  const values = data.map((point) => Number(config.read(point) || 0));
  const width = 1000;
  const height = 240;
  const paddingX = 24;
  const paddingY = 20;
  const coordinates = chartCoordinates(values, width, height, paddingX, paddingY);
  const line = coordinates.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
  const area = coordinates.length
    ? `${line} L ${coordinates[coordinates.length - 1].x} ${height - paddingY} L ${coordinates[0].x} ${height - paddingY} Z`
    : '';
  const selected = data[selectedIndex];
  const total = useMemo(() => values.reduce((sum, value) => sum + value, 0), [values]);
  const peakIndex = values.length ? values.reduce((best, value, index) => value > values[best] ? index : best, 0) : -1;
  const tickIndexes = Array.from(new Set([0, Math.floor((data.length - 1) / 2), data.length - 1])).filter((index) => index >= 0);

  return (
    <section className="analytics-panel trend-panel">
      <div className="analytics-panel-header trend-header">
        <div>
          <span className="analytics-kicker">Evolução</span>
          <h2>O que mudou ao longo do tempo?</h2>
          <p>Selecione uma métrica e clique em um ponto para inspecionar o período.</p>
        </div>
        <div className="metric-tabs" role="tablist" aria-label="Métrica do gráfico">
          {modes.map((item) => (
            <button
              type="button"
              role="tab"
              aria-selected={item.value === mode}
              className={item.value === mode ? 'active' : ''}
              key={item.value}
              onClick={() => onModeChange(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {!data.length ? <ChartEmptyState /> : (
        <div className="trend-layout">
          <div className="trend-canvas">
            <div className="trend-summary-line">
              <span>Período <strong>{config.aggregate === 'average' ? config.format(total / Math.max(values.filter((value) => value > 0).length, 1)) : config.format(total)}</strong></span>
              <span>Pico <strong>{peakIndex >= 0 ? config.format(values[peakIndex]) : '—'}</strong></span>
            </div>
            <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label={`${config.label} ao longo do tempo`}>
              {[0.25, 0.5, 0.75].map((ratio) => (
                <line key={ratio} x1={paddingX} x2={width - paddingX} y1={paddingY + (height - paddingY * 2) * ratio} y2={paddingY + (height - paddingY * 2) * ratio} className="chart-grid-line" vectorEffect="non-scaling-stroke" />
              ))}
              {area && <path d={area} className="trend-area" />}
              {line && <path d={line} className="trend-line" fill="none" vectorEffect="non-scaling-stroke" />}
              {coordinates.map((point, index) => (
                <circle
                  key={`${data[index]?.date}-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r={selectedIndex === index ? 7 : 4}
                  className={selectedIndex === index ? 'trend-point selected' : 'trend-point'}
                  role="button"
                  tabIndex="0"
                  onClick={() => setSelectedIndex(index)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') setSelectedIndex(index);
                  }}
                >
                  <title>{`${compactDate(data[index]?.date)} · ${config.format(values[index])}`}</title>
                </circle>
              ))}
            </svg>
            <div className="chart-axis-labels">
              {tickIndexes.map((index) => <span key={index}>{compactDate(data[index]?.date)}</span>)}
            </div>
          </div>

          <aside className="selected-period-card">
            <span className="analytics-kicker">Período selecionado</span>
            <h3>{selected ? compactDate(selected.date) : 'Nenhum período'}</h3>
            {selected ? (
              <div className="selected-period-grid">
                {config.details(selected).map((item) => (
                  <div key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="period-highlight">
              <span>Pico de {config.label.toLowerCase()}</span>
              <strong>{peakIndex >= 0 ? compactDate(data[peakIndex]?.date) : '—'}</strong>
              <small>{peakIndex >= 0 ? config.format(values[peakIndex]) : 'Sem dados'}</small>
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}

export function StackedDistribution({ data, total, labelFormatter = (value) => value }) {
  if (!total || !data.length) return <ChartEmptyState />;
  return (
    <div className="stacked-distribution">
      <div className="stacked-track" aria-label="Distribuição de status">
        {data.filter((item) => item.value > 0).map((item, index) => (
          <div
            key={item.label}
            className={`stacked-segment chart-tone-${(index % 6) + 1}`}
            style={{ width: `${(item.value / total) * 100}%` }}
            title={`${labelFormatter(item.label)}: ${item.value}`}
          />
        ))}
      </div>
      <div className="stacked-legend">
        {data.map((item, index) => (
          <div key={item.label}>
            <i className={`chart-tone-${(index % 6) + 1}`} />
            <span>{labelFormatter(item.label)}</span>
            <strong>{item.value}</strong>
            <small>{((item.value / total) * 100).toFixed(1)}%</small>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HorizontalAnalyticsBars({ data, valueKey = 'ticket_count', labelKey = 'label', valueFormatter = (value) => value, meta }) {
  const max = Math.max(...data.map((item) => Number(item[valueKey] || 0)), 1);
  if (!data.length || !data.some((item) => item[valueKey])) return <ChartEmptyState />;
  return (
    <div className="horizontal-analytics-bars">
      {data.map((item) => (
        <div className="analytics-bar-item" key={item[labelKey]}>
          <div className="analytics-bar-heading">
            <span>{item[labelKey]}</span>
            <strong>{valueFormatter(item[valueKey])}</strong>
          </div>
          <div className="bar-track"><div className="bar-fill" style={{ width: `${(Number(item[valueKey] || 0) / max) * 100}%` }} /></div>
          {meta ? <div className="analytics-bar-meta">{meta(item)}</div> : null}
        </div>
      ))}
    </div>
  );
}
