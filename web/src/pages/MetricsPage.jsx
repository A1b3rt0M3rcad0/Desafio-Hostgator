import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { BarChart } from '../components/Charts.jsx';
import { ErrorState, KpiCard, PageHeader, Spinner } from '../components/UI.jsx';
import { formatDuration, formatPercent, minutesBetween } from '../utils/format.js';

export function MetricsPage() {
  const { data, loading, error, reload } = useResource(async () => {
    const [ticketsPage, ratingsPage] = await Promise.all([api.listTickets({ page_size: 100 }), api.listRatings({ page_size: 100 })]);
    const tickets = ticketsPage.items || [];
    const ratings = ratingsPage.items || [];
    const byPriority = Object.entries(tickets.reduce((acc, item) => ({ ...acc, [item.priority]: (acc[item.priority] || 0) + 1 }), {}));
    const byAssignee = Object.entries(tickets.reduce((acc, item) => ({ ...acc, [item.assignee_name || 'Sem atendente']: (acc[item.assignee_name || 'Sem atendente'] || 0) + 1 }), {})).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const responseTimes = tickets.map((ticket) => minutesBetween(ticket.source_created_at, ticket.first_response_at)).filter((value) => value !== null);
    const resolved = tickets.filter((item) => ['SOLVED', 'CLOSED'].includes(item.status)).length;
    return { tickets, ratings, byPriority, byAssignee, resolution: tickets.length ? resolved / tickets.length : 0, response: responseTimes.length ? Math.round(responseTimes.reduce((sum, value) => sum + value, 0) / responseTimes.length) : null, satisfaction: ratings.length ? ratings.filter((item) => item.score === 'GOOD').length / ratings.length : 0 };
  }, []);
  if (loading) return <Spinner label="Calculando métricas" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  return <><PageHeader eyebrow="Análise" title="Métricas operacionais" description="Métricas derivadas dos registros disponibilizados pela API." /><section className="kpi-grid"><KpiCard label="Resolução" value={formatPercent(data.resolution)} /><KpiCard label="Primeira resposta" value={formatDuration(data.response)} /><KpiCard label="Satisfação positiva" value={formatPercent(data.satisfaction)} /></section><section className="dashboard-grid"><article className="panel"><div className="panel-header"><div><span className="eyebrow">Prioridade</span><h2>Volume por prioridade</h2></div></div><BarChart data={data.byPriority.map(([label, value]) => ({ label, value }))} /></article><article className="panel panel-wide"><div className="panel-header"><div><span className="eyebrow">Equipe</span><h2>Tickets por atendente</h2></div></div><BarChart data={data.byAssignee.map(([label, value]) => ({ label, value }))} /></article></section></>;
}
