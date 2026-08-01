import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatNumber } from '../utils/format.js';

const DEFAULT_METRICS = [
  'ticket_volume',
  'average_recurrence_seconds',
  'top_topics',
  'resolution_rate',
  'satisfaction_rate',
  'average_first_response_seconds',
];

const DEFAULT_FIELDS = [
  'ticket_id',
  'subject',
  'description',
  'status',
  'priority',
  'requester_id',
  'requester_name',
  'requester_email',
  'assignee_id',
  'assignee_name',
  'created_at',
  'updated_at',
  'first_response_at',
  'tags',
  'satisfaction_rating',
];

function toggleItem(items, value) {
  return items.includes(value)
    ? items.filter((item) => item !== value)
    : [...items, value];
}

function selectedValues(event) {
  return Array.from(event.target.selectedOptions, (option) => option.value);
}

function FilterSelect({ label, value, options, onChange }) {
  return (
    <label className="export-filter-select">
      <span>{label}</span>
      <select multiple value={value.map(String)} onChange={(event) => onChange(selectedValues(event))}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <small>{value.length ? `${value.length} selecionado(s)` : 'Todos'}</small>
    </label>
  );
}

function buildFilters(state) {
  const filters = {};
  if (state.fromAt) filters.from_at = new Date(state.fromAt).toISOString();
  if (state.toAt) filters.to_at = new Date(state.toAt).toISOString();
  if (state.statuses.length) filters.statuses = state.statuses;
  if (state.priorities.length) filters.priorities = state.priorities;
  if (state.tagNames.length) filters.tag_names = state.tagNames;
  if (state.requesterEmails.length) filters.requester_emails = state.requesterEmails;
  if (state.assigneeIds.length) filters.assignee_external_ids = state.assigneeIds.map(Number);
  if (state.satisfactionScores.length) filters.satisfaction_scores = state.satisfactionScores;
  if (state.hasFirstResponse !== '') filters.has_first_response = state.hasFirstResponse === 'true';
  return filters;
}

function ActiveScope({ filters, onClear }) {
  const chips = [];
  if (filters.from_at || filters.to_at) chips.push('Período personalizado');
  chips.push(...(filters.statuses || []).map((item) => `Status: ${item}`));
  chips.push(...(filters.priorities || []).map((item) => `Prioridade: ${item}`));
  chips.push(...(filters.tag_names || []).map((item) => `Tag: ${item}`));
  chips.push(...(filters.requester_emails || []).map((item) => `Cliente: ${item}`));
  chips.push(...(filters.assignee_external_ids || []).map((item) => `Responsável: ${item}`));
  chips.push(...(filters.satisfaction_scores || []).map((item) => `Satisfação: ${item}`));
  if (filters.has_first_response === true) chips.push('Com primeira resposta');
  if (filters.has_first_response === false) chips.push('Sem primeira resposta');
  if (!chips.length) return <p className="export-scope-empty">Nenhum filtro aplicado: a exportação considera todo o conjunto disponível.</p>;
  return (
    <div className="active-filter-row export-active-scope">
      <span>Escopo ativo</span>
      {chips.map((chip) => <i key={chip}>{chip}</i>)}
      <button type="button" className="clear-all" onClick={onClear}>Limpar filtros</button>
    </div>
  );
}

export function ExportsPage() {
  const catalog = useResource(() => api.getExportCatalog(), []);
  const [mode, setMode] = useState('data');
  const [format, setFormat] = useState('csv');
  const [scope, setScope] = useState('overall');
  const [metrics, setMetrics] = useState(DEFAULT_METRICS);
  const [fields, setFields] = useState(DEFAULT_FIELDS);
  const [filterState, setFilterState] = useState({
    fromAt: '',
    toAt: '',
    statuses: [],
    priorities: [],
    tagNames: [],
    requesterEmails: [],
    assigneeIds: [],
    satisfactionScores: [],
    hasFirstResponse: '',
  });
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');

  const filters = useMemo(() => buildFilters(filterState), [filterState]);
  const previewColumns = useMemo(() => (preview?.fields || []).map((field) => ({
    key: field,
    label: catalog.data?.fields?.find((item) => item.code === field)?.label || field.replaceAll('_', ' '),
    render: (row) => typeof row[field] === 'object' && row[field] !== null
      ? JSON.stringify(row[field])
      : row[field],
  })), [catalog.data, preview]);

  function updateFilter(name, value) {
    setFilterState((current) => ({ ...current, [name]: value }));
    setPreview(null);
  }

  function clearFilters() {
    setFilterState({
      fromAt: '',
      toAt: '',
      statuses: [],
      priorities: [],
      tagNames: [],
      requesterEmails: [],
      assigneeIds: [],
      satisfactionScores: [],
      hasFirstResponse: '',
    });
    setPreview(null);
  }

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

  async function previewData() {
    const result = await run(() => api.previewDataExport({ fields, filters, limit: 50 }));
    if (result) setPreview(result);
  }

  function exportCurrent() {
    if (mode === 'data') {
      return run(() => api.exportData({ format, fields, filters }));
    }
    return run(() => api.exportMetrics({
      format,
      scope,
      metrics,
      filters,
      top_topics_limit: 10,
    }));
  }

  if (catalog.loading) return <Spinner label="Carregando opções de exportação" />;
  if (catalog.error) return <ErrorState error={catalog.error} onRetry={catalog.reload} />;

  const data = catalog.data;
  const dynamicOptions = data.filter_options || {};
  const statusOptions = data.statuses.map((item) => ({ value: item.code, label: item.label }));
  const priorityOptions = data.priorities.map((item) => ({ value: item.code, label: item.label }));
  const satisfactionOptions = data.satisfaction_scores.map((item) => ({ value: item.code, label: item.label }));
  const tagOptions = (dynamicOptions.tags || []).map((item) => ({ value: item.name, label: item.name }));
  const customerOptions = (dynamicOptions.customers || []).map((item) => ({ value: item.requester_email, label: `${item.requester_name} — ${item.requester_email}` }));
  const assigneeOptions = (dynamicOptions.assignees || []).map((item) => ({ value: item.external_id, label: `${item.name} — ${item.external_id}` }));

  return (
    <>
      <PageHeader
        eyebrow="Saída de dados"
        title="Exportação de dados"
        description="Selecione o escopo, os campos ou as métricas e retire os dados do sistema em CSV ou XLSX. Nenhuma operação desta tela altera o banco."
      />

      <section className="panel report-builder export-workspace">
        <div className="report-tabs">
          <button type="button" className={`button ${mode === 'data' ? 'button-primary' : 'button-secondary'}`} onClick={() => { setMode('data'); setPreview(null); }}>Dados detalhados</button>
          <button type="button" className={`button ${mode === 'metrics' ? 'button-primary' : 'button-secondary'}`} onClick={() => { setMode('metrics'); setPreview(null); }}>Métricas</button>
        </div>

        <div className="analytics-filters compact-filters export-primary-options">
          <label><span>Formato</span><select value={format} onChange={(event) => setFormat(event.target.value)}>{data.formats.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
          {mode === 'metrics' && <label><span>Escopo</span><select value={scope} onChange={(event) => setScope(event.target.value)}>{data.scopes.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>}
          <label><span>De</span><input type="datetime-local" value={filterState.fromAt} onChange={(event) => updateFilter('fromAt', event.target.value)} /></label>
          <label><span>Até</span><input type="datetime-local" value={filterState.toAt} onChange={(event) => updateFilter('toAt', event.target.value)} /></label>
          <label><span>Primeira resposta</span><select value={filterState.hasFirstResponse} onChange={(event) => updateFilter('hasFirstResponse', event.target.value)}><option value="">Todos</option><option value="true">Com resposta</option><option value="false">Sem resposta</option></select></label>
        </div>

        <div className="export-filter-grid">
          <FilterSelect label="Status" value={filterState.statuses} options={statusOptions} onChange={(value) => updateFilter('statuses', value)} />
          <FilterSelect label="Prioridades" value={filterState.priorities} options={priorityOptions} onChange={(value) => updateFilter('priorities', value)} />
          <FilterSelect label="Tags" value={filterState.tagNames} options={tagOptions} onChange={(value) => updateFilter('tagNames', value)} />
          <FilterSelect label="Clientes" value={filterState.requesterEmails} options={customerOptions} onChange={(value) => updateFilter('requesterEmails', value)} />
          <FilterSelect label="Responsáveis" value={filterState.assigneeIds} options={assigneeOptions} onChange={(value) => updateFilter('assigneeIds', value)} />
          <FilterSelect label="Satisfação" value={filterState.satisfactionScores} options={satisfactionOptions} onChange={(value) => updateFilter('satisfactionScores', value)} />
        </div>

        <ActiveScope filters={filters} onClear={clearFilters} />

        {mode === 'data' ? (
          <fieldset className="option-grid"><legend>Campos exportados</legend>{data.fields.map((item) => <label key={item.code}><input type="checkbox" checked={fields.includes(item.code)} onChange={() => { setFields((current) => toggleItem(current, item.code)); setPreview(null); }} /><span>{item.label}</span></label>)}</fieldset>
        ) : (
          <fieldset className="option-grid"><legend>Métricas exportadas</legend>{data.metrics.map((item) => <label key={item.code}><input type="checkbox" checked={metrics.includes(item.code)} onChange={() => setMetrics((current) => toggleItem(current, item.code))} /><span>{item.label}</span></label>)}</fieldset>
        )}

        {error && <div className="form-error" role="alert">{error.message}</div>}
        {message && <div className="form-success" role="status">{message}</div>}

        <div className="header-actions">
          {mode === 'data' && <button className="button button-secondary" type="button" disabled={busy || !fields.length} onClick={previewData}>Pré-visualizar dados</button>}
          <button className="button button-primary" type="button" disabled={busy || (mode === 'data' ? !fields.length : !metrics.length)} onClick={exportCurrent}>{busy ? 'Processando…' : `Exportar ${format.toUpperCase()}`}</button>
        </div>
      </section>

      {mode === 'data' && preview && (
        <>
          <section className="panel report-summary"><div><span>Registros encontrados</span><strong>{formatNumber(preview.total_matching)}</strong></div><div><span>Registros na prévia</span><strong>{formatNumber(preview.preview_count)}</strong></div></section>
          <DataTable rowKey="ticket_id" rows={preview.items} columns={previewColumns} emptyTitle="Nenhum registro encontrado" />
        </>
      )}
    </>
  );
}
