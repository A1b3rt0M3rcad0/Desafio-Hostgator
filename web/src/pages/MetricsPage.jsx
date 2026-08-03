import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatDuration, formatNumber, formatPercent } from '../utils/format.js';

const EMPTY_METRIC_FILTERS = {
  volumeMin: '',
  volumeMax: '',
  satisfactionMin: '',
  satisfactionMax: '',
};

function optionalNumber(value) {
  return value === '' ? undefined : Number(value);
}

export function MetricsPage() {
  const [page, setPage] = useState(1);
  const [filterDraft, setFilterDraft] = useState(EMPTY_METRIC_FILTERS);
  const [filters, setFilters] = useState(EMPTY_METRIC_FILTERS);
  const [filterError, setFilterError] = useState(null);
  const query = useMemo(() => ({
    page,
    page_size: 25,
    top_topics_limit: 3,
    ticket_volume_min: optionalNumber(filters.volumeMin),
    ticket_volume_max: optionalNumber(filters.volumeMax),
    satisfaction_rate_min: filters.satisfactionMin === '' ? undefined : Number(filters.satisfactionMin) / 100,
    satisfaction_rate_max: filters.satisfactionMax === '' ? undefined : Number(filters.satisfactionMax) / 100,
  }), [filters, page]);
  const queryKey = JSON.stringify(query);
  const resource = useResource(() => api.listCustomerMetrics(query), [queryKey]);

  const updateFilter = (field, value) => {
    setFilterDraft((current) => ({ ...current, [field]: value }));
  };

  const applyFilters = (event) => {
    event.preventDefault();
    const volumeMin = optionalNumber(filterDraft.volumeMin);
    const volumeMax = optionalNumber(filterDraft.volumeMax);
    const satisfactionMin = optionalNumber(filterDraft.satisfactionMin);
    const satisfactionMax = optionalNumber(filterDraft.satisfactionMax);

    if (volumeMin !== undefined && volumeMax !== undefined && volumeMin > volumeMax) {
      setFilterError('O volume mínimo não pode ser maior que o volume máximo.');
      return;
    }
    if (
      satisfactionMin !== undefined
      && satisfactionMax !== undefined
      && satisfactionMin > satisfactionMax
    ) {
      setFilterError('A satisfação mínima não pode ser maior que a satisfação máxima.');
      return;
    }
    setFilterError(null);
    setPage(1);
    setFilters(filterDraft);
  };

  const clearFilters = () => {
    setFilterDraft(EMPTY_METRIC_FILTERS);
    setFilters(EMPTY_METRIC_FILTERS);
    setFilterError(null);
    setPage(1);
  };

  if (resource.loading) return <Spinner label="Calculando métricas por cliente" />;
  if (resource.error) return <ErrorState error={resource.error} onRetry={resource.reload} />;

  const data = resource.data || { items: [], page: 1, total: 0, has_next: false, has_previous: false };
  return (
    <>
      <PageHeader eyebrow="Análise por cliente" title="Métricas operacionais" description="Indicadores calculados em lote pelo backend para cada cliente, sem limitar a análise às primeiras linhas da API." />
      <form className="data-filters metric-filters" onSubmit={applyFilters}>
        <label><span>Volume mínimo</span><input type="number" min="0" step="1" value={filterDraft.volumeMin} onChange={(event) => updateFilter('volumeMin', event.target.value)} /></label>
        <label><span>Volume máximo</span><input type="number" min="0" step="1" value={filterDraft.volumeMax} onChange={(event) => updateFilter('volumeMax', event.target.value)} /></label>
        <label><span>Satisfação mínima (%)</span><input type="number" min="0" max="100" step="0.1" value={filterDraft.satisfactionMin} onChange={(event) => updateFilter('satisfactionMin', event.target.value)} /></label>
        <label><span>Satisfação máxima (%)</span><input type="number" min="0" max="100" step="0.1" value={filterDraft.satisfactionMax} onChange={(event) => updateFilter('satisfactionMax', event.target.value)} /></label>
        <div className="data-filter-actions"><button className="button button-secondary" type="button" onClick={clearFilters}>Limpar</button><button className="button button-primary" type="submit">Aplicar filtros</button></div>
        {filterError && <div className="form-error data-filter-error" role="alert">{filterError}</div>}
      </form>
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
