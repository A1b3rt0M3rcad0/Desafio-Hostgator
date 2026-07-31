import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { ErrorState, Spinner } from '../components/UI.jsx';
import {
  ChartEmptyState,
  HorizontalAnalyticsBars,
  StackedDistribution,
  TimeSeriesChart,
} from '../components/Charts.jsx';
import { formatDate, formatDuration, formatNumber, formatPercent, humanize } from '../utils/format.js';

const STATUS_OPTIONS = ['NEW', 'OPEN', 'PENDING', 'HOLD', 'SOLVED', 'CLOSED'];
const PRIORITY_OPTIONS = ['URGENT', 'HIGH', 'NORMAL', 'LOW'];
const PERIODS = [
  { value: '7d', label: '7 dias', days: 7 },
  { value: '30d', label: '30 dias', days: 30 },
  { value: '90d', label: '90 dias', days: 90 },
  { value: 'custom', label: 'Personalizado' },
];

function localDateTime(value) {
  const date = value instanceof Date ? value : new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function periodRange(period, anchor, customRange) {
  if (period === 'custom') {
    return {
      from_at: customRange.from_at ? new Date(customRange.from_at).toISOString() : undefined,
      to_at: customRange.to_at ? new Date(customRange.to_at).toISOString() : undefined,
    };
  }
  const config = PERIODS.find((item) => item.value === period) || PERIODS[1];
  const end = new Date(anchor);
  const start = new Date(end);
  start.setDate(start.getDate() - config.days);
  return { from_at: start.toISOString(), to_at: end.toISOString() };
}

function MultiSelect({ label, values, options, onChange, searchable = false }) {
  const [search, setSearch] = useState('');
  const visible = options.filter((option) => !searchable || option.label.toLowerCase().includes(search.toLowerCase()));
  const summary = values.length ? `${label}: ${values.length}` : label;

  function toggle(value) {
    onChange(values.includes(value) ? values.filter((item) => item !== value) : [...values, value]);
  }

  return (
    <details className="analytics-select">
      <summary className={values.length ? 'active' : ''}>{summary}<span>⌄</span></summary>
      <div className="analytics-select-menu">
        {searchable ? <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Buscar ${label.toLowerCase()}`} /> : null}
        <div className="analytics-select-options">
          {visible.length ? visible.map((option) => (
            <label key={option.value}>
              <input type="checkbox" checked={values.includes(option.value)} onChange={() => toggle(option.value)} />
              <span>{option.label}</span>
              {option.detail ? <small>{option.detail}</small> : null}
            </label>
          )) : <small className="select-empty">Nenhuma opção encontrada.</small>}
        </div>
        {values.length ? <button type="button" onClick={() => onChange([])}>Limpar seleção</button> : null}
      </div>
    </details>
  );
}

function ActiveFilters({ filters, onRemove, onClear }) {
  const chips = [
    ...filters.statuses.map((value) => ({ type: 'statuses', value, label: `Status: ${humanize(value)}` })),
    ...filters.priorities.map((value) => ({ type: 'priorities', value, label: `Prioridade: ${humanize(value)}` })),
    ...filters.tag_names.map((value) => ({ type: 'tag_names', value, label: `Tag: ${value}` })),
    ...filters.requester_emails.map((value) => ({ type: 'requester_emails', value, label: value })),
  ];
  if (!chips.length) return null;
  return (
    <div className="active-filter-row">
      <span>Escopo ativo</span>
      {chips.map((chip) => (
        <button type="button" key={`${chip.type}-${chip.value}`} onClick={() => onRemove(chip.type, chip.value)}>
          {chip.label}<b>×</b>
        </button>
      ))}
      <button type="button" className="clear-all" onClick={onClear}>Limpar tudo</button>
    </div>
  );
}

function comparisonLabel(metric, key, { points = false, lowerIsBetter = false } = {}) {
  const change = points ? metric?.change_points : metric?.change_percent;
  if (change === null || change === undefined) return { label: 'Sem período anterior comparável', tone: 'neutral' };
  if (Math.abs(change) < 0.05) return { label: 'Estável em relação ao período anterior', tone: 'neutral' };
  const improved = lowerIsBetter ? change < 0 : change > 0;
  const suffix = points ? `${Math.abs(change).toFixed(1)} p.p.` : `${Math.abs(change).toFixed(1)}%`;
  return { label: `${change > 0 ? '↑' : '↓'} ${suffix} vs. período anterior`, tone: improved ? 'positive' : 'negative' };
}

function MetricCard({ label, value, detail, comparison, accent }) {
  return (
    <article className={`analytics-metric-card accent-${accent}`}>
      <div className="metric-card-top"><span>{label}</span><i /></div>
      <strong>{value}</strong>
      <small>{detail}</small>
      <p className={`metric-comparison ${comparison.tone}`}>{comparison.label}</p>
    </article>
  );
}

function OperationalStory({ summary }) {
  return (
    <section className="operational-story">
      <div className="story-main">
        <span className="analytics-kicker">Leitura do período</span>
        <h2>{summary?.headline || 'Ainda não há dados suficientes para interpretar este escopo.'}</h2>
      </div>
      <div className="story-signals">
        <div><span>Atenção</span><strong>{summary?.primary_alert || 'Sem alerta relevante'}</strong></div>
        <div><span>Melhora</span><strong>{summary?.primary_improvement || 'Sem melhora comparável'}</strong></div>
        <div><span>Principal assunto</span><strong>{summary?.top_driver?.label || 'Sem classificação'}</strong><small>{summary?.top_driver ? `${formatNumber(summary.top_driver.ticket_count)} tickets · ${formatPercent(summary.top_driver.share)}` : 'Nenhuma tag no escopo'}</small></div>
      </div>
    </section>
  );
}

function PanelHeader({ kicker, title, description, aside }) {
  return (
    <div className="analytics-panel-header">
      <div><span className="analytics-kicker">{kicker}</span><h2>{title}</h2>{description ? <p>{description}</p> : null}</div>
      {aside}
    </div>
  );
}

function TopicsTable({ topics }) {
  if (!topics.length) return <ChartEmptyState title="Nenhum assunto classificado" description="Os tickets deste escopo não possuem tags." />;
  return (
    <div className="topics-table-wrap">
      <table className="topics-table">
        <thead><tr><th>Assunto</th><th>Tickets</th><th>Participação</th><th>Resolução</th><th>1ª resposta</th><th>Variação</th></tr></thead>
        <tbody>
          {topics.map((topic) => (
            <tr key={topic.tag}>
              <td><div className="topic-name"><span>{topic.rank}</span><strong>{topic.tag}</strong></div></td>
              <td>{formatNumber(topic.ticket_count)}</td>
              <td>{formatPercent(topic.share)}</td>
              <td>{formatPercent(topic.resolution_rate)}</td>
              <td>{formatDuration(topic.average_first_response_seconds)}</td>
              <td><span className={`change-badge ${(topic.change_percent || 0) > 0 ? 'up' : (topic.change_percent || 0) < 0 ? 'down' : ''}`}>{topic.change_percent === null || topic.change_percent === undefined ? '—' : `${topic.change_percent > 0 ? '+' : ''}${topic.change_percent.toFixed(1)}%`}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DashboardPage() {
  const [period, setPeriod] = useState('30d');
  const [anchor, setAnchor] = useState(() => new Date());
  const [customRange, setCustomRange] = useState(() => {
    const now = new Date();
    const start = new Date(now);
    start.setDate(start.getDate() - 30);
    return { from_at: localDateTime(start), to_at: localDateTime(now) };
  });
  const [filters, setFilters] = useState({ statuses: [], priorities: [], tag_names: [], requester_emails: [] });
  const [trendMode, setTrendMode] = useState('opened');

  const query = useMemo(() => ({
    ...periodRange(period, anchor, customRange),
    ...filters,
    top_topics_limit: 8,
    timeline_limit: 90,
  }), [anchor, customRange, filters, period]);

  const resource = useResource(() => api.getDashboard(query), [JSON.stringify(query)]);
  const optionsResource = useResource(async () => {
    const [tags, customers] = await Promise.all([
      api.listTags({ page_size: 100 }),
      api.listCustomers({ page_size: 100 }),
    ]);
    return { tags: tags?.items || [], customers: customers?.items || [] };
  }, []);

  const tagOptions = (optionsResource.data?.tags || []).map((tag) => ({ value: tag.name, label: tag.name }));
  const customerOptions = (optionsResource.data?.customers || []).map((customer) => ({
    value: customer.requester_email,
    label: customer.requester_name,
    detail: customer.requester_email,
  }));

  function updateFilter(name, values) {
    setFilters((current) => ({ ...current, [name]: values }));
  }

  function removeFilter(name, value) {
    updateFilter(name, filters[name].filter((item) => item !== value));
  }

  function clearFilters() {
    setFilters({ statuses: [], priorities: [], tag_names: [], requester_emails: [] });
  }

  if (resource.loading) return <Spinner label="Construindo visão analítica da operação" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;

  const data = resource.data || {};
  const metrics = data.metrics || {};
  const charts = data.charts || {};
  const volume = metrics.ticket_volume || {};
  const resolution = metrics.resolution_rate || {};
  const response = metrics.average_first_response || {};
  const satisfaction = metrics.satisfaction_rate || {};
  const recurrence = metrics.average_recurrence || {};
  const behavior = data.customer_behavior || {};
  const total = Number(volume.value || 0);

  const cards = [
    {
      label: 'Volume de tickets', value: formatNumber(volume.value), detail: 'Tickets abertos no período',
      comparison: comparisonLabel(volume, 'value'), accent: 'blue',
    },
    {
      label: 'Taxa de resolução', value: formatPercent(resolution.rate), detail: `${formatNumber(resolution.resolved)} de ${formatNumber(resolution.total)} tickets`,
      comparison: comparisonLabel(resolution, 'rate', { points: true }), accent: 'green',
    },
    {
      label: 'Tempo até a 1ª resposta', value: formatDuration(response.average_seconds), detail: `${formatNumber(response.responded_tickets)} tickets respondidos`,
      comparison: comparisonLabel(response, 'average_seconds', { lowerIsBetter: true }), accent: 'orange',
    },
    {
      label: 'Índice de satisfação', value: formatPercent(satisfaction.rate), detail: `${formatNumber(satisfaction.good)} boas de ${formatNumber(satisfaction.rated_total)} avaliações`,
      comparison: comparisonLabel(satisfaction, 'rate', { points: true }), accent: 'violet',
    },
  ];

  const trendModes = [
    {
      value: 'opened', label: 'Tickets abertos', read: (point) => point.opened, format: formatNumber,
      details: (point) => [
        { label: 'Abertos', value: formatNumber(point.opened) },
        { label: 'Resolvidos', value: formatNumber(point.resolved) },
        { label: 'Taxa de resolução', value: formatPercent(point.resolution_rate) },
        { label: '1ª resposta', value: formatDuration(point.average_first_response_seconds) },
        { label: 'Satisfação', value: formatPercent(point.satisfaction_rate) },
        { label: 'Avaliações', value: formatNumber(point.rated_tickets) },
      ],
    },
    {
      value: 'resolved', label: 'Resolvidos', read: (point) => point.resolved, format: formatNumber,
      details: (point) => [
        { label: 'Resolvidos', value: formatNumber(point.resolved) },
        { label: 'Abertos', value: formatNumber(point.opened) },
        { label: 'Taxa de resolução', value: formatPercent(point.resolution_rate) },
        { label: '1ª resposta', value: formatDuration(point.average_first_response_seconds) },
      ],
    },
    {
      value: 'resolution', label: 'Resolução', read: (point) => (point.resolution_rate || 0) * 100, format: (value) => `${Number(value || 0).toFixed(1)}%`, aggregate: 'average',
      details: (point) => [
        { label: 'Taxa de resolução', value: formatPercent(point.resolution_rate) },
        { label: 'Resolvidos', value: formatNumber(point.resolved) },
        { label: 'Abertos', value: formatNumber(point.opened) },
        { label: '1ª resposta', value: formatDuration(point.average_first_response_seconds) },
      ],
    },
    {
      value: 'response', label: 'Primeira resposta', read: (point) => point.average_first_response_seconds || 0, format: formatDuration, aggregate: 'average',
      details: (point) => [
        { label: '1ª resposta', value: formatDuration(point.average_first_response_seconds) },
        { label: 'Abertos', value: formatNumber(point.opened) },
        { label: 'Resolvidos', value: formatNumber(point.resolved) },
        { label: 'Satisfação', value: formatPercent(point.satisfaction_rate) },
      ],
    },
    {
      value: 'satisfaction', label: 'Satisfação', read: (point) => (point.satisfaction_rate || 0) * 100, format: (value) => `${Number(value || 0).toFixed(1)}%`, aggregate: 'average',
      details: (point) => [
        { label: 'Satisfação', value: formatPercent(point.satisfaction_rate) },
        { label: 'Avaliações', value: formatNumber(point.rated_tickets) },
        { label: '1ª resposta', value: formatDuration(point.average_first_response_seconds) },
        { label: 'Resolução', value: formatPercent(point.resolution_rate) },
      ],
    },
  ];

  const priorityData = (charts.priority_breakdown || []).map((item) => ({ ...item, label: humanize(item.priority) }));
  const responseData = charts.first_response_distribution || [];

  return (
    <div className="analytics-workspace">
      <header className="analytics-page-header">
        <div>
          <span className="analytics-kicker">Dashboard principal</span>
          <h1>Visão geral da operação</h1>
          <p>Entenda o que mudou, onde a fila se concentra e quais fatores exigem investigação.</p>
          <small>Dados atualizados em {formatDate(data.generated_at)} · Comparação com período anterior de mesma duração</small>
        </div>
        <div className="analytics-header-actions">
          <button type="button" className="button button-secondary" onClick={() => { setAnchor(new Date()); resource.reload(); }}>↻ Atualizar</button>
          <button type="button" className="button button-primary" onClick={() => api.exportMetricsReport({ format: 'xlsx', scope: 'overall', metrics: [], filters: query })}>Exportar análise</button>
        </div>
      </header>

      <section className="analytics-toolbar">
        <div className="period-tabs" role="tablist" aria-label="Período de análise">
          {PERIODS.map((item) => <button type="button" role="tab" aria-selected={period === item.value} className={period === item.value ? 'active' : ''} key={item.value} onClick={() => setPeriod(item.value)}>{item.label}</button>)}
        </div>
        <div className="analytics-filter-controls">
          <MultiSelect label="Status" values={filters.statuses} options={STATUS_OPTIONS.map((value) => ({ value, label: humanize(value) }))} onChange={(values) => updateFilter('statuses', values)} />
          <MultiSelect label="Prioridade" values={filters.priorities} options={PRIORITY_OPTIONS.map((value) => ({ value, label: humanize(value) }))} onChange={(values) => updateFilter('priorities', values)} />
          <MultiSelect label="Tags" values={filters.tag_names} options={tagOptions} onChange={(values) => updateFilter('tag_names', values)} searchable />
          <MultiSelect label="Cliente" values={filters.requester_emails} options={customerOptions} onChange={(values) => updateFilter('requester_emails', values)} searchable />
        </div>
        {period === 'custom' ? (
          <div className="custom-period-row">
            <label><span>De</span><input type="datetime-local" value={customRange.from_at} onChange={(event) => setCustomRange((current) => ({ ...current, from_at: event.target.value }))} /></label>
            <label><span>Até</span><input type="datetime-local" value={customRange.to_at} onChange={(event) => setCustomRange((current) => ({ ...current, to_at: event.target.value }))} /></label>
          </div>
        ) : null}
        <ActiveFilters filters={filters} onRemove={removeFilter} onClear={clearFilters} />
      </section>

      <OperationalStory summary={data.summary} />

      <section className="analytics-metric-grid">{cards.map((card) => <MetricCard key={card.label} {...card} />)}</section>

      <TimeSeriesChart data={charts.operation_timeseries || []} mode={trendMode} modes={trendModes} onModeChange={setTrendMode} />

      <section className="analytics-two-column">
        <article className="analytics-panel">
          <PanelHeader kicker="Estado atual" title="Composição da fila" description="Distribuição dos tickets por status dentro do mesmo escopo." aside={<strong className="panel-total">{formatNumber(total)} tickets</strong>} />
          <StackedDistribution data={charts.status_distribution || []} total={total} labelFormatter={humanize} />
        </article>
        <article className="analytics-panel">
          <PanelHeader kicker="Prioridade" title="Pressão operacional" description="Volume, resolução e tempo de resposta por nível de prioridade." />
          <HorizontalAnalyticsBars
            data={priorityData}
            labelKey="label"
            valueFormatter={formatNumber}
            meta={(item) => <><span>{formatPercent(item.share)} do volume</span><span>{formatPercent(item.resolution_rate)} resolvidos</span><span>{formatDuration(item.average_first_response_seconds)} até 1ª resposta</span></>}
          />
        </article>
      </section>

      <section className="analytics-two-column response-behavior-grid">
        <article className="analytics-panel">
          <PanelHeader kicker="Tempo de resposta" title="Distribuição até a primeira resposta" description="Faixas operacionais; não representam conformidade de SLA." />
          <HorizontalAnalyticsBars
            data={responseData}
            labelKey="label"
            valueFormatter={formatNumber}
            meta={(item) => <span>{formatPercent(item.share)} do volume</span>}
          />
        </article>
        <article className="analytics-panel customer-behavior-panel">
          <PanelHeader kicker="Comportamento" title="Recorrência dos clientes" description="Concentração e frequência de abertura de novos tickets." />
          <div className="behavior-score-grid">
            <div><span>Frequência média</span><strong>{formatDuration(recurrence.average_seconds)}</strong><small>{formatNumber(recurrence.sample_intervals)} intervalos válidos</small></div>
            <div><span>Clientes recorrentes</span><strong>{formatPercent(behavior.repeat_customer_rate)}</strong><small>{formatNumber(behavior.repeat_customers)} de {formatNumber(behavior.unique_customers)}</small></div>
            <div><span>Tickets por cliente</span><strong>{behavior.average_tickets_per_customer?.toFixed(2) || '—'}</strong><small>Média no escopo</small></div>
          </div>
          <div className="top-customers-list">
            <span className="analytics-kicker">Maior volume</span>
            {(behavior.top_customers || []).length ? behavior.top_customers.map((customer, index) => (
              <div key={customer.customer_id}><b>{index + 1}</b><span><strong>{customer.requester_name}</strong><small>{customer.requester_email}</small></span><em>{formatNumber(customer.ticket_count)}</em></div>
            )) : <ChartEmptyState title="Nenhum cliente no escopo" />}
          </div>
        </article>
      </section>

      <section className="analytics-panel topics-panel">
        <PanelHeader kicker="Taxonomia" title="Assuntos principais" description="Volume, participação, desempenho e mudança em relação ao período anterior." aside={<span className="panel-note">Top {Math.min((charts.top_topics || []).length, 8)}</span>} />
        <TopicsTable topics={charts.top_topics || []} />
      </section>
    </div>
  );
}
