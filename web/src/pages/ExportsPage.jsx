import { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { DataTable } from '../components/DataTable.jsx';
import { ErrorState, PageHeader, Spinner } from '../components/UI.jsx';
import { formatNumber } from '../utils/format.js';

const PERIODS = [
  { value: '7d', label: '7 dias', days: 7 },
  { value: '30d', label: '30 dias', days: 30 },
  { value: '90d', label: '90 dias', days: 90 },
  { value: 'all', label: 'Todo o período' },
  { value: 'custom', label: 'Personalizado' },
];

function toggleItem(items, value) {
  return items.includes(value)
    ? items.filter((item) => item !== value)
    : [...items, value];
}

function localDateInput(date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function initialCustomPeriod() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 30);
  return { from: localDateInput(start), to: localDateInput(end) };
}

function periodRange(period, customPeriod) {
  if (period === 'all') return {};
  if (period === 'custom') {
    const range = {};
    if (customPeriod.from) range.from_at = new Date(`${customPeriod.from}T00:00:00`).toISOString();
    if (customPeriod.to) range.to_at = new Date(`${customPeriod.to}T23:59:59.999`).toISOString();
    return range;
  }

  const selected = PERIODS.find((item) => item.value === period) || PERIODS[1];
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - selected.days);
  start.setHours(0, 0, 0, 0);
  return { from_at: start.toISOString(), to_at: end.toISOString() };
}

function buildFilters(period, customPeriod, state) {
  const filters = { ...periodRange(period, customPeriod) };
  if (state.statuses.length) filters.statuses = state.statuses;
  if (state.priorities.length) filters.priorities = state.priorities;
  if (state.tagNames.length) filters.tag_names = state.tagNames;
  if (state.requesterEmails.length) filters.requester_emails = state.requesterEmails;
  if (state.assigneeIds.length) filters.assignee_external_ids = state.assigneeIds.map(Number);
  if (state.satisfactionScores.length) filters.satisfaction_scores = state.satisfactionScores;
  if (state.hasFirstResponse !== '') filters.has_first_response = state.hasFirstResponse === 'true';
  return filters;
}

function FilterMenu({ label, values, options, onChange, searchable = false }) {
  const [search, setSearch] = useState('');
  const normalizedSearch = search.trim().toLowerCase();
  const visibleOptions = options.filter((option) => (
    !normalizedSearch
    || `${option.label} ${option.detail || ''}`.toLowerCase().includes(normalizedSearch)
  ));
  const selectedOptions = options.filter((option) => values.includes(option.value));
  const summary = selectedOptions.length === 0
    ? 'Todos'
    : selectedOptions.length === 1
      ? selectedOptions[0].label
      : `${selectedOptions.length} selecionados`;

  function toggle(value) {
    const next = toggleItem(values, value);
    onChange(next.length === options.length ? [] : next);
  }

  return (
    <details className="export-filter-menu">
      <summary className={values.length ? 'restricted' : ''}>
        <span><small>{label}</small><strong>{summary}</strong></span>
        <i>⌄</i>
      </summary>
      <div className="export-filter-popover">
        {searchable && (
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`Buscar ${label.toLowerCase()}`}
          />
        )}
        <div className="export-filter-options">
          {visibleOptions.length ? visibleOptions.map((option) => (
            <label key={option.value}>
              <input
                type="checkbox"
                checked={values.includes(option.value)}
                onChange={() => toggle(option.value)}
              />
              <span>{option.label}</span>
              {option.detail && <small>{option.detail}</small>}
            </label>
          )) : <p>Nenhuma opção encontrada.</p>}
        </div>
        {values.length > 0 && <button type="button" onClick={() => onChange([])}>Voltar para todos</button>}
      </div>
    </details>
  );
}

function selectedLabel(label, values, options) {
  const names = values.map((value) => options.find((option) => option.value === value)?.label || value);
  if (names.length <= 2) return `${label}: ${names.join(', ')}`;
  return `${label}: ${names.slice(0, 2).join(', ')} +${names.length - 2}`;
}

function ActiveFilters({ items, onClear }) {
  if (!items.length) return null;
  return (
    <div className="export-active-filters">
      <span>Filtros aplicados</span>
      <div>
        {items.map((item) => (
          <button type="button" key={item.key} onClick={item.onRemove}>
            {item.label}<b>×</b>
          </button>
        ))}
      </div>
      <button type="button" className="export-clear-filters" onClick={onClear}>Limpar filtros</button>
    </div>
  );
}

export function ExportsPage() {
  const catalog = useResource(() => api.getExportCatalog(), []);
  const [initialized, setInitialized] = useState(false);
  const [mode, setMode] = useState('data');
  const [format, setFormat] = useState('csv');
  const [scope, setScope] = useState('overall');
  const [period, setPeriod] = useState('30d');
  const [customPeriod, setCustomPeriod] = useState(initialCustomPeriod);
  const [fieldPreset, setFieldPreset] = useState('essential');
  const [metrics, setMetrics] = useState([]);
  const [fields, setFields] = useState([]);
  const [filterState, setFilterState] = useState({
    statuses: [],
    priorities: [],
    tagNames: [],
    requesterEmails: [],
    assigneeIds: [],
    satisfactionScores: [],
    hasFirstResponse: '',
  });
  const [preview, setPreview] = useState(null);
  const [matchingCount, setMatchingCount] = useState(null);
  const [countLoading, setCountLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!catalog.data || initialized) return;
    const defaults = catalog.data.defaults || {};
    const defaultPreset = (catalog.data.field_presets || []).find((item) => item.code === defaults.field_preset)
      || catalog.data.field_presets?.[0];
    setFormat(defaults.data_format || 'csv');
    setScope(defaults.scope || 'overall');
    setPeriod(`${defaults.period_days || 30}d`);
    setFieldPreset(defaultPreset?.code || 'custom');
    setFields(defaultPreset?.fields || catalog.data.fields.map((item) => item.code));
    setMetrics(defaults.metrics || catalog.data.metrics.map((item) => item.code));
    setInitialized(true);
  }, [catalog.data, initialized]);

  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(() => setMessage(''), 5000);
    return () => window.clearTimeout(timer);
  }, [message]);

  const filters = useMemo(
    () => buildFilters(period, customPeriod, filterState),
    [customPeriod, filterState, period],
  );
  const filtersKey = useMemo(() => JSON.stringify(filters), [filters]);

  useEffect(() => {
    if (!initialized || mode !== 'data') return undefined;
    let active = true;
    setCountLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const result = await api.previewDataExport({ fields: ['ticket_id'], filters, limit: 1 });
        if (active) setMatchingCount(result.total_matching);
      } catch {
        if (active) setMatchingCount(null);
      } finally {
        if (active) setCountLoading(false);
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [filtersKey, initialized, mode]);

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

  function chooseMode(nextMode) {
    const defaults = catalog.data?.defaults || {};
    setMode(nextMode);
    setFormat(nextMode === 'data' ? defaults.data_format || 'csv' : defaults.metrics_format || 'xlsx');
    setPreview(null);
    setError(null);
  }

  function applyFieldPreset(preset) {
    setFieldPreset(preset.code);
    if (preset.code !== 'custom') setFields(preset.fields);
    setPreview(null);
  }

  async function run(action) {
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      const result = await action();
      if (typeof result === 'string') setMessage(result);
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
    if (result) {
      setPreview(result);
      setMatchingCount(result.total_matching);
    }
  }

  function exportCurrent() {
    if (mode === 'data') return run(() => api.exportData({ format, fields, filters }));
    return run(() => api.exportMetrics({
      format,
      scope,
      metrics,
      filters,
      top_topics_limit: 10,
    }));
  }

  if (catalog.loading || !initialized) return <Spinner label="Preparando exportação" />;
  if (catalog.error) return <ErrorState error={catalog.error} onRetry={catalog.reload} />;

  const data = catalog.data;
  const dynamicOptions = data.filter_options || {};
  const statusOptions = data.statuses.map((item) => ({ value: item.code, label: item.label }));
  const priorityOptions = data.priorities.map((item) => ({ value: item.code, label: item.label }));
  const satisfactionOptions = data.satisfaction_scores.map((item) => ({ value: item.code, label: item.label }));
  const tagOptions = (dynamicOptions.tags || []).map((item) => ({ value: item.name, label: item.name }));
  const customerOptions = (dynamicOptions.customers || []).map((item) => ({ value: item.requester_email, label: item.requester_name, detail: item.requester_email }));
  const assigneeOptions = (dynamicOptions.assignees || []).map((item) => ({ value: item.external_id, label: item.name, detail: `ID ${item.external_id}` }));
  const fieldPresets = [
    ...(data.field_presets || []),
    { code: 'custom', label: 'Personalizado', description: 'Escolha cada coluna manualmente.', fields },
  ];

  const advancedFilterCount = [
    filterState.statuses,
    filterState.priorities,
    filterState.tagNames,
    filterState.requesterEmails,
    filterState.assigneeIds,
    filterState.satisfactionScores,
  ].filter((values) => values.length).length + (filterState.hasFirstResponse !== '' ? 1 : 0);

  const activeItems = [];
  if (filterState.statuses.length) activeItems.push({ key: 'statuses', label: selectedLabel('Status', filterState.statuses, statusOptions), onRemove: () => updateFilter('statuses', []) });
  if (filterState.priorities.length) activeItems.push({ key: 'priorities', label: selectedLabel('Prioridade', filterState.priorities, priorityOptions), onRemove: () => updateFilter('priorities', []) });
  if (filterState.tagNames.length) activeItems.push({ key: 'tags', label: selectedLabel('Tags', filterState.tagNames, tagOptions), onRemove: () => updateFilter('tagNames', []) });
  if (filterState.requesterEmails.length) activeItems.push({ key: 'customers', label: selectedLabel('Clientes', filterState.requesterEmails, customerOptions), onRemove: () => updateFilter('requesterEmails', []) });
  if (filterState.assigneeIds.length) activeItems.push({ key: 'assignees', label: selectedLabel('Responsáveis', filterState.assigneeIds, assigneeOptions), onRemove: () => updateFilter('assigneeIds', []) });
  if (filterState.satisfactionScores.length) activeItems.push({ key: 'satisfaction', label: selectedLabel('Satisfação', filterState.satisfactionScores, satisfactionOptions), onRemove: () => updateFilter('satisfactionScores', []) });
  if (filterState.hasFirstResponse !== '') activeItems.push({ key: 'first-response', label: filterState.hasFirstResponse === 'true' ? 'Com primeira resposta' : 'Sem primeira resposta', onRemove: () => updateFilter('hasFirstResponse', '') });

  const selectedPeriod = PERIODS.find((item) => item.value === period);
  const periodDescription = period === 'all'
    ? 'todo o período disponível'
    : period === 'custom'
      ? `de ${customPeriod.from || 'início indefinido'} até ${customPeriod.to || 'agora'}`
      : `dos últimos ${selectedPeriod?.label || '30 dias'}`;
  const formatLabel = format.toUpperCase();
  const dataCountLabel = countLoading
    ? 'os tickets encontrados'
    : matchingCount === null
      ? 'os tickets encontrados'
      : `${formatNumber(matchingCount)} ${matchingCount === 1 ? 'ticket' : 'tickets'}`;
  const exportSummary = mode === 'data'
    ? `Você exportará ${dataCountLabel} ${periodDescription}, com ${fields.length} colunas, em ${formatLabel}.`
    : `Você exportará ${metrics.length} métricas ${scope === 'overall' ? 'da visão geral' : 'agrupadas por cliente'} ${periodDescription}, em ${formatLabel}.`;
  const noData = mode === 'data' && matchingCount === 0;
  const actionLabel = busy
    ? 'Processando…'
    : mode === 'data'
      ? matchingCount === null || countLoading
        ? `Exportar tickets em ${formatLabel}`
        : `Exportar ${formatNumber(matchingCount)} ${matchingCount === 1 ? 'ticket' : 'tickets'}`
      : `Exportar métricas em ${formatLabel}`;

  return (
    <>
      <PageHeader
        eyebrow="Saída de dados"
        title="Exportação de dados"
        description="Escolha o tipo, o período e o formato. Os detalhes avançados ficam disponíveis apenas quando necessários."
      />

      <section className="panel export-guided-workspace">
        <div className="export-step">
          <div className="export-step-heading">
            <span>1</span>
            <div><strong>O que deseja exportar?</strong><small>Escolha o resultado mais adequado para sua análise.</small></div>
          </div>
          <div className="export-type-grid">
            <button type="button" className={`export-type-card ${mode === 'data' ? 'active' : ''}`} onClick={() => chooseMode('data')}>
              <i>▤</i><span><strong>Tickets detalhados</strong><small>Uma linha por ticket, com dados do cliente e do atendimento.</small></span><b>{mode === 'data' ? '✓' : ''}</b>
            </button>
            <button type="button" className={`export-type-card ${mode === 'metrics' ? 'active' : ''}`} onClick={() => chooseMode('metrics')}>
              <i>↗</i><span><strong>Métricas consolidadas</strong><small>Indicadores gerais ou agrupados por cliente.</small></span><b>{mode === 'metrics' ? '✓' : ''}</b>
            </button>
          </div>
        </div>

        <div className="export-step export-quick-options">
          <div className="export-step-heading">
            <span>2</span>
            <div><strong>Defina o básico</strong><small>Os valores recomendados já estão selecionados.</small></div>
          </div>

          <div className="export-choice-block">
            <label>Período</label>
            <div className="export-segmented-control export-period-control">
              {PERIODS.map((item) => <button type="button" key={item.value} className={period === item.value ? 'active' : ''} onClick={() => { setPeriod(item.value); setPreview(null); }}>{item.label}</button>)}
            </div>
          </div>

          {period === 'custom' && (
            <div className="export-custom-period">
              <label><span>De</span><input type="date" value={customPeriod.from} onChange={(event) => { setCustomPeriod((current) => ({ ...current, from: event.target.value })); setPreview(null); }} /></label>
              <label><span>Até</span><input type="date" value={customPeriod.to} onChange={(event) => { setCustomPeriod((current) => ({ ...current, to: event.target.value })); setPreview(null); }} /></label>
            </div>
          )}

          <div className="export-inline-options">
            <div className="export-choice-block">
              <label>Formato</label>
              <div className="export-segmented-control">
                {data.formats.map((item) => <button type="button" key={item.code} className={format === item.code ? 'active' : ''} onClick={() => setFormat(item.code)}>{item.label}</button>)}
              </div>
            </div>
            {mode === 'metrics' && (
              <div className="export-choice-block">
                <label>Organização</label>
                <div className="export-segmented-control">
                  {data.scopes.map((item) => <button type="button" key={item.code} className={scope === item.code ? 'active' : ''} onClick={() => setScope(item.code)}>{item.label}</button>)}
                </div>
              </div>
            )}
          </div>
        </div>

        {mode === 'data' ? (
          <div className="export-step">
            <div className="export-step-heading">
              <span>3</span>
              <div><strong>Escolha as colunas</strong><small>O preset Essencial atende à maioria das exportações.</small></div>
            </div>
            <div className="export-preset-grid">
              {fieldPresets.map((preset) => (
                <button type="button" key={preset.code} className={fieldPreset === preset.code ? 'active' : ''} onClick={() => applyFieldPreset(preset)}>
                  <strong>{preset.label}</strong><small>{preset.description}</small><span>{preset.code === 'custom' ? `${fields.length} selecionadas` : `${preset.fields.length} colunas`}</span>
                </button>
              ))}
            </div>
            {fieldPreset === 'custom' && (
              <fieldset className="export-custom-fields">
                <legend>Colunas personalizadas</legend>
                {data.fields.map((item) => (
                  <label key={item.code}>
                    <input type="checkbox" checked={fields.includes(item.code)} onChange={() => { setFields((current) => toggleItem(current, item.code)); setPreview(null); }} />
                    <span>{item.label}</span>
                  </label>
                ))}
              </fieldset>
            )}
          </div>
        ) : (
          <details className="export-metrics-customization">
            <summary><span><strong>Métricas incluídas</strong><small>{metrics.length} de {data.metrics.length} métricas selecionadas</small></span><i>Personalizar</i></summary>
            <fieldset className="export-custom-fields">
              <legend>Métricas exportadas</legend>
              {data.metrics.map((item) => (
                <label key={item.code}>
                  <input type="checkbox" checked={metrics.includes(item.code)} onChange={() => setMetrics((current) => toggleItem(current, item.code))} />
                  <span>{item.label}</span>
                </label>
              ))}
            </fieldset>
          </details>
        )}

        <details className="export-advanced-filters">
          <summary>
            <span><strong>Personalizar filtros</strong><small>{advancedFilterCount ? `${advancedFilterCount} restrições aplicadas` : 'Opcional — refine apenas quando necessário'}</small></span>
            <i>⌄</i>
          </summary>
          <div className="export-advanced-content">
            <FilterMenu label="Status" values={filterState.statuses} options={statusOptions} onChange={(value) => updateFilter('statuses', value)} />
            <FilterMenu label="Prioridade" values={filterState.priorities} options={priorityOptions} onChange={(value) => updateFilter('priorities', value)} />
            <FilterMenu label="Tags" values={filterState.tagNames} options={tagOptions} onChange={(value) => updateFilter('tagNames', value)} searchable />
            <FilterMenu label="Clientes" values={filterState.requesterEmails} options={customerOptions} onChange={(value) => updateFilter('requesterEmails', value)} searchable />
            <FilterMenu label="Responsáveis" values={filterState.assigneeIds} options={assigneeOptions} onChange={(value) => updateFilter('assigneeIds', value)} searchable />
            <FilterMenu label="Satisfação" values={filterState.satisfactionScores} options={satisfactionOptions} onChange={(value) => updateFilter('satisfactionScores', value)} />
            <label className="export-first-response-filter">
              <small>Primeira resposta</small>
              <select value={filterState.hasFirstResponse} onChange={(event) => updateFilter('hasFirstResponse', event.target.value)}>
                <option value="">Todas</option>
                <option value="true">Somente com resposta</option>
                <option value="false">Somente sem resposta</option>
              </select>
            </label>
          </div>
        </details>

        <ActiveFilters items={activeItems} onClear={clearFilters} />

        {error && <div className="form-error" role="alert">{error.message}</div>}

        <div className={`export-action-card ${noData ? 'empty' : ''}`}>
          <div>
            <span className="export-action-kicker">Resumo da exportação</span>
            <strong>{noData ? 'Nenhum ticket corresponde ao escopo atual.' : exportSummary}</strong>
            <small>{noData ? 'Remova algum filtro ou amplie o período para continuar.' : 'A exportação é somente leitura e não altera os dados do sistema.'}</small>
          </div>
          <div className="export-action-buttons">
            <button className="button button-primary" type="button" disabled={busy || noData || (mode === 'data' ? !fields.length : !metrics.length)} onClick={exportCurrent}>{actionLabel}</button>
            {mode === 'data' && <button className="button button-secondary" type="button" disabled={busy || noData || !fields.length} onClick={previewData}>Ver prévia</button>}
          </div>
        </div>
      </section>

      {mode === 'data' && preview && (
        <section className="export-preview-section">
          <div className="export-preview-heading">
            <div><span>Prévia dos dados</span><strong>{formatNumber(preview.preview_count)} de {formatNumber(preview.total_matching)} registros</strong></div>
            <button type="button" className="button button-secondary" onClick={() => setPreview(null)}>Fechar prévia</button>
          </div>
          <DataTable rowKey="ticket_id" rows={preview.items} columns={previewColumns} emptyTitle="Nenhum registro encontrado" />
        </section>
      )}

      {message && (
        <div className="export-toast" role="status">
          <span>✓</span><div><strong>Exportação concluída</strong><small>{message}</small></div><button type="button" onClick={() => setMessage('')}>×</button>
        </div>
      )}
    </>
  );
}
