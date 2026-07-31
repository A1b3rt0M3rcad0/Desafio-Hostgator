import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatDate } from '../utils/format.js';

export function ReportsPage() {
  const { data, loading, error, reload } = useResource(() => api.listTickets({ page_size: 100 }), []);
  if (loading) return <Spinner label="Preparando relatório" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const rows = data.items || [];
  function exportCsv() {
    const headers = ['external_ticket_id', 'subject', 'status', 'priority', 'assignee_name', 'source_created_at', 'source_updated_at'];
    const escape = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const content = [headers.join(','), ...rows.map((row) => headers.map((header) => escape(row[header])).join(','))].join('\n');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'relatorio-tickets.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return <><PageHeader eyebrow="Exportação" title="Relatórios" description="Relatório consolidado e somente leitura dos tickets carregados." action={<div className="header-actions"><button className="button button-secondary" type="button" onClick={exportCsv}>Exportar CSV</button><button className="button button-primary" type="button" onClick={() => window.print()}>Imprimir / PDF</button></div>} /><section className="panel report-summary"><div><span>Registros no relatório</span><strong>{rows.length}</strong></div><div><span>Gerado em</span><strong>{formatDate(new Date())}</strong></div></section><DataTable rows={rows} columns={[
    { key: 'external_ticket_id', label: 'Ticket' }, { key: 'subject', label: 'Assunto' }, { key: 'status', label: 'Status' }, { key: 'priority', label: 'Prioridade' }, { key: 'assignee_name', label: 'Atendente' }, { key: 'source_created_at', label: 'Criado', render: (row) => formatDate(row.source_created_at) },
  ]} /></>;
}
