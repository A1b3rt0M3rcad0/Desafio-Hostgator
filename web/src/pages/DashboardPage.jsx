import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Badge, ErrorState, KpiCard, PageHeader, Spinner } from '../components/UI.jsx';
import { BarChart, DonutChart } from '../components/Charts.jsx';
import { formatDuration, formatNumber, formatPercent, minutesBetween } from '../utils/format.js';

function buildDashboard([ticketsPage, customersPage, ratingsPage, tagsPage]) {
  const tickets = ticketsPage.items || [];
  const customers = customersPage.items || [];
  const ratings = ratingsPage.items || [];
  const statuses = Object.entries(tickets.reduce((acc, ticket) => ({ ...acc, [ticket.status]: (acc[ticket.status] || 0) + 1 }), {}));
  const priorities = Object.entries(tickets.reduce((acc, ticket) => ({ ...acc, [ticket.priority]: (acc[ticket.priority] || 0) + 1 }), {}));
  const resolved = tickets.filter((ticket) => ['SOLVED', 'CLOSED'].includes(ticket.status)).length;
  const responseTimes = tickets.map((ticket) => minutesBetween(ticket.source_created_at, ticket.first_response_at)).filter((value) => value !== null);
  const goodRatings = ratings.filter((rating) => rating.score === 'GOOD').length;
  return {
    tickets,
    customers,
    ratings,
    tags: tagsPage.items || [],
    statuses,
    priorities,
    resolved,
    resolutionRate: tickets.length ? resolved / tickets.length : 0,
    averageResponse: responseTimes.length ? Math.round(responseTimes.reduce((sum, value) => sum + value, 0) / responseTimes.length) : null,
    satisfactionRate: ratings.length ? goodRatings / ratings.length : 0,
  };
}

export function DashboardPage() {
  const { data, loading, error, reload } = useResource(
    () => Promise.all([
      api.listTickets({ page_size: 100 }),
      api.listCustomers({ page_size: 100 }),
      api.listRatings({ page_size: 100 }),
      api.listTags({ page_size: 100 }),
    ]).then(buildDashboard),
    [],
  );

  if (loading) return <Spinner label="Carregando indicadores" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const chartColors = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)'];
  return (
    <>
      <PageHeader eyebrow="Dashboard principal" title="Visão geral da operação" description="Indicadores calculados sobre os registros disponíveis na API." />
      <section className="kpi-grid">
        <KpiCard label="Tickets carregados" value={formatNumber(data.tickets.length)} detail="Amostra da consulta atual" />
        <KpiCard label="Clientes carregados" value={formatNumber(data.customers.length)} detail="Solicitantes únicos persistidos" />
        <KpiCard label="Taxa de resolução" value={formatPercent(data.resolutionRate)} detail={`${data.resolved} tickets resolvidos`} />
        <KpiCard label="Primeira resposta média" value={formatDuration(data.averageResponse)} detail="Calculada quando disponível" />
        <KpiCard label="Satisfação positiva" value={formatPercent(data.satisfactionRate)} detail={`${data.ratings.length} avaliações carregadas`} />
      </section>
      <section className="dashboard-grid">
        <article className="panel panel-wide"><div className="panel-header"><div><span className="eyebrow">Distribuição</span><h2>Status dos tickets</h2></div></div><BarChart data={data.statuses.map(([label, value]) => ({ label, value }))} /></article>
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Prioridade</span><h2>Composição da fila</h2></div></div><DonutChart centerLabel="tickets" data={data.priorities.map(([label, value], index) => ({ label, value, color: chartColors[index % chartColors.length] }))} /></article>
        <article className="panel"><div className="panel-header"><div><span className="eyebrow">Taxonomia</span><h2>Tags disponíveis</h2></div></div><div className="tag-cloud">{data.tags.slice(0, 16).map((tag) => <Badge key={tag.id} value={tag.name} variant="neutral" />)}{!data.tags.length && <span>Nenhuma tag encontrada.</span>}</div></article>
      </section>
    </>
  );
}
