import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatNumber } from '../utils/format.js';

const DEFAULT_METRICS = ['ticket_volume', 'average_recurrence_seconds', 'top_topics', 'resolution_rate', 'satisfaction_rate', 'average_first_response_seconds'];
const DEFAULT_RAW_FIELDS = ['ticket_id', 'subject', 'description', 'status', 'priority', 'requester_id', 'requester_name', 'requester_email', 'assignee_id', 'assignee_name', 'created_at', 'updated_at', 'first_response_at', 'tags', 'satisfaction_rating'];

function toggleItem(items, value) {
  return items.includes(value) ? items.filter((item) => item !== value) : [...items, value];
}

function buildFilters(fromAt, toAt) {
  const filters = {};
  if (fromAt) filters.from_at = fromAt;
  if (toAt) filters.to_at = toAt;
  return filters;
}

export function ReportsPage() {
  const catalog = useResource(() => api.getReportCatalog(), []);
  const [mode, setMode] = useState('metrics');
  const [format, setFormat] = useState('csv');
  const [scope, setScope] = useState('overall');
  const [metrics, setMetrics] = useState(DEFAULT_METRICS);
  const [rawFields, setRawFields] = useState(DEFAULT_RAW_FIELDS);
  const [fromAt, setFromAt] = useState('');
  const [toAt, setToAt] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');

  const previewColumns = useMemo(() => (preview?.fields || []).map((field) => ({
    key: field,
    label: field.replaceAll('_', ' '),
    render: (row) => typeof row[field] === 'object' && row[field] !== null ? JSON.stringify(row[field]) : row[field],
  })), [preview]);

  async function run(action) {
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      const result = await action();
      if (typeof result === 'string') setMessage(`Arquivo gerado: ${result}`);
      return result;
    } catch (requestError) {
      setError(requestError);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function previewRaw() {
    const result = await run(() => api.previewRawReport({
      fields: rawFields,
      filters: buildFilters(fromAt, toAt),
      limit: 50,
    }));
    if (result) setPreview(result);
  }

  function exportCurrent() {
    const filters = buildFilters(fromAt, toAt);
    if (mode === 'raw') {
      return run(() => api.exportRawReport({ format, preset: 'mock_complete', fields: rawFields, filters }));
    }
    return run(() => api.exportMetricsReport({ format, scope, metrics, filters, top_topics_limit: 10 }));
  }

  if (catalog.loading) return <Spinner label="Carregando catálogo de relatórios" />;
  if (catalog.error) return <ErrorState error={catalog.error} onRetry={catalog.reload} />;

  return (
    <>
      <PageHeader eyebrow="Exportação" title="Relatórios" description="Exporte métricas agregadas ou reconstrua o contrato RAW do mock. Os dados são consultados no backend e não se limitam à página carregada no navegador." />
      <section className="panel report-builder">
        <div className="report-tabs">
          <button type="button" className={`button ${mode === 'metrics' ? 'button-primary' : 'button-secondary'}`} onClick={() => setMode('metrics')}>Métricas</button>
          <button type="button" className={`button ${mode === 'raw' ? 'button-primary' : 'button-secondary'}`} onClick={() => setMode('raw')}>RAW</button>
        </div>
        <div className="analytics-filters compact-filters">
          <label><span>Formato</span><select value={format} onChange={(event) => setFormat(event.target.value)}>{catalog.data.formats.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
          {mode === 'metrics' && <label><span>Escopo</span><select value={scope} onChange={(event) => setScope(event.target.value)}><option value="overall">Visão geral</option><option value="customer">Por cliente</option></select></label>}
          <label><span>De</span><input type="datetime-local" value={fromAt} onChange={(event) => setFromAt(event.target.value)} /></label>
          <label><span>Até</span><input type="datetime-local" value={toAt} onChange={(event) => setToAt(event.target.value)} /></label>
        </div>
        {mode === 'metrics' ? (
          <fieldset className="option-grid"><legend>Métricas exportadas</legend>{catalog.data.metrics.map((item) => <label key={item.code}><input type="checkbox" checked={metrics.includes(item.code)} onChange={() => setMetrics((current) => toggleItem(current, item.code))} /><span>{item.label}</span></label>)}</fieldset>
        ) : (
          <fieldset className="option-grid"><legend>Campos RAW exportados</legend>{catalog.data.raw_fields.map((item) => <label key={item.code}><input type="checkbox" checked={rawFields.includes(item.code)} onChange={() => setRawFields((current) => toggleItem(current, item.code))} /><span>{item.label}</span></label>)}</fieldset>
        )}
        {error && <div className="form-error" role="alert">{error.message}</div>}
        {message && <div className="form-success" role="status">{message}</div>}
        <div className="header-actions">
          {mode === 'raw' && <button className="button button-secondary" type="button" disabled={busy || !rawFields.length} onClick={previewRaw}>Pré-visualizar RAW</button>}
          <button className="button button-primary" type="button" disabled={busy || (mode === 'metrics' ? !metrics.length : !rawFields.length)} onClick={exportCurrent}>{busy ? 'Processando…' : `Exportar ${format.toUpperCase()}`}</button>
        </div>
      </section>
      {mode === 'raw' && preview && (
        <>
          <section className="panel report-summary"><div><span>Registros encontrados</span><strong>{formatNumber(preview.total_matching)}</strong></div><div><span>Registros na prévia</span><strong>{formatNumber(preview.preview_count)}</strong></div></section>
          <DataTable rowKey="ticket_id" rows={preview.items} columns={previewColumns} emptyTitle="Nenhum registro encontrado" />
        </>
      )}
    </>
  );
}
