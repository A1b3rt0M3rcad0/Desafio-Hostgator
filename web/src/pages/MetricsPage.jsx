import { useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatDuration, formatNumber, formatPercent } from '../utils/format.js';

export function MetricsPage() {
  const [page, setPage] = useState(1);
  const resource = useResource(() => api.listCustomerMetrics({ page, page_size: 25, top_topics_limit: 3 }), [page]);

  if (resource.loading) return <Spinner label="Calculando métricas por cliente" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;

  const data = resource.data || { items: [], page: 1, total: 0, has_next: false, has_previous: false };
  return (
    <>
      <PageHeader eyebrow="Análise por cliente" title="Métricas operacionais" description="Indicadores calculados em lote pelo backend para cada cliente, sem limitar a análise às primeiras linhas da API." />
      <section className="panel report-summary">
        <div><span>Clientes encontrados</span><strong>{formatNumber(data.total)}</strong></div>
        <div><span>Página atual</span><strong>{data.page}</strong></div>
      </section>
      <DataTable
        rowKey="customer_id"
        rows={data.items}
        emptyTitle="Nenhum cliente possui tickets para os filtros atuais"
        columns={[
          { key: 'requester_name', label: 'Cliente' },
          { key: 'requester_email', label: 'E-mail' },
          { key: 'ticket_volume', label: 'Volume', render: (row) => formatNumber(row.ticket_volume) },
          { key: 'average_recurrence_seconds', label: 'Frequência média', render: (row) => formatDuration(row.average_recurrence_seconds) },
          { key: 'resolution_rate', label: 'Resolução', render: (row) => formatPercent(row.resolution_rate) },
          { key: 'satisfaction_rate', label: 'Satisfação', render: (row) => formatPercent(row.satisfaction_rate) },
          { key: 'average_first_response_seconds', label: 'Tempo até 1ª resposta', render: (row) => formatDuration(row.average_first_response_seconds) },
          { key: 'top_topics', label: 'Assuntos principais', render: (row) => row.top_topics?.map((topic) => topic.tag).join(', ') || '—' },
        ]}
      />
      <div className="pagination">
        <button className="button button-secondary" type="button" disabled={!data.has_previous} onClick={() => setPage((current) => Math.max(1, current - 1))}>Anterior</button>
        <span>Página {data.page}</span>
        <button className="button button-secondary" type="button" disabled={!data.has_next} onClick={() => setPage((current) => current + 1)}>Próxima</button>
      </div>
    </>
  );
}
