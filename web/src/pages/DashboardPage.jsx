import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { ErrorState, KpiCard, PageHeader, Spinner } from '../components/UI.jsx';
import { BarChart, DonutChart } from '../components/Charts.jsx';
import { formatDuration, formatNumber, formatPercent, humanize } from '../utils/format.js';

const EMPTY_FILTERS = { from_at: '', to_at: '', statuses: '', priorities: '', tag_names: '', requester_emails: '' };

function cleanFilters(filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== ''));
}

export function DashboardPage() {
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState({});
  const resource = useResource(() => api.getDashboard(appliedFilters), [JSON.stringify(appliedFilters)]);

  const cards = useMemo(() => {
    const metrics = resource.data?.metrics;
    if (!metrics) return [];
    return [
      { label: 'Volume de tickets', value: formatNumber(metrics.ticket_volume.value), detail: 'Todos os tickets dentro dos filtros' },
      { label: 'Frequência média', value: formatDuration(metrics.average_recurrence.average_seconds), detail: `${formatNumber(metrics.average_recurrence.sample_intervals)} intervalos válidos` },
      { label: 'Taxa de resolução', value: formatPercent(metrics.resolution_rate.rate), detail: `${formatNumber(metrics.resolution_rate.resolved)} de ${formatNumber(metrics.resolution_rate.total)}` },
      { label: 'Índice de satisfação', value: formatPercent(metrics.satisfaction_rate.rate), detail: `${formatNumber(metrics.satisfaction_rate.good)} boas / ${formatNumber(metrics.satisfaction_rate.rated_total)} avaliadas` },
      { label: 'Tempo até a 1ª resposta', value: formatDuration(metrics.average_first_response.average_seconds), detail: `${formatNumber(metrics.average_first_response.responded_tickets)} tickets respondidos` },
    ];
  }, [resource.data]);

  function updateFilter(name, value) {
    setDraftFilters((current) => ({ ...current, [name]: value }));
  }

  function applyFilters(event) {
    event.preventDefault();
    setAppliedFilters(cleanFilters(draftFilters));
  }

  function clearFilters() {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters({});
  }

  if (resource.loading) return <Spinner label="Calculando indicadores no banco" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;

  const charts = resource.data?.charts || {};
  const statusData = (charts.status_distribution || []).map((item, index) => ({ ...item, label: humanize(item.label), color: `var(--chart-${(index % 5) + 1})` }));
  const priorityData = (charts.priority_distribution || []).map((item) => ({ ...item, label: humanize(item.label) }));
  const timelineData = (charts.tickets_over_time || []).map((item) => ({ label: item.date, value: item.value }));
  const topicsData = (charts.top_topics || []).map((item) => ({ label: item.tag, value: item.ticket_count }));

  return (
    <>
      <PageHeader eyebrow="Dashboard principal" title="Visão geral da operação" description="Indicadores calculados pelo backend sobre o conjunto completo de tickets, com os mesmos filtros em todos os cards e gráficos." />
      <form className="panel analytics-filters" onSubmit={applyFilters}>
        <label><span>De</span><input type="datetime-local" value={draftFilters.from_at} onChange={(event) => updateFilter('from_at', event.target.value)} /></label>
        <label><span>Até</span><input type="datetime-local" value={draftFilters.to_at} onChange={(event) => updateFilter('to_at', event.target.value)} /></label>
        <label><span>Status</span><input value={draftFilters.statuses} onChange={(event) => updateFilter('statuses', event.target.value.toUpperCase())} placeholder="OPEN,SOLVED" /></label>
        <label><span>Prioridade</span><input value={draftFilters.priorities} onChange={(event) => updateFilter('priorities', event.target.value.toUpperCase())} placeholder="HIGH,URGENT" /></label>
        <label><span>Tags</span><input value={draftFilters.tag_names} onChange={(event) => updateFilter('tag_names', event.target.value)} placeholder="login,pagamento" /></label>
        <label><span>E-mails</span><input value={draftFilters.requester_emails} onChange={(event) => updateFilter('requester_emails', event.target.value)} placeholder="cliente@exemplo.com" /></label>
        <div className="filter-actions"><button className="button button-primary" type="submit">Aplicar filtros</button><button className="button button-secondary" type="button" onClick={clearFilters}>Limpar</button></div>
      </form>
      <section className="kpi-grid">{cards.map((card) => <KpiCard key={card.label} {...card} />)}</section>
      <section className="dashboard-grid">
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Evolução</span><h2>Tickets por dia</h2></div></div><BarChart data={timelineData} valueFormatter={formatNumber} /></article>
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Distribuição</span><h2>Status dos tickets</h2></div></div><DonutChart centerLabel="tickets" data={statusData} /></article>
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Prioridade</span><h2>Composição da fila</h2></div></div><BarChart data={priorityData} valueFormatter={formatNumber} /></article>
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Taxonomia</span><h2>Assuntos principais</h2></div></div><BarChart data={topicsData} valueFormatter={formatNumber} /></article>
      </section>
    </>
  );
}
