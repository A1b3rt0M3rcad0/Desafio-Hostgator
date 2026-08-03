import { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Badge, DetailLink, ErrorState, PageHeader, Pagination, SearchField, Spinner } from '../components/UI.jsx';
import { DataTable } from '../components/DataTable.jsx';
import { formatDate, humanize } from '../utils/format.js';

function useDebouncedValue(value, delay = 350) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timeout);
  }, [delay, value]);

  return debounced;
}

function useCursorPage(loader, query = {}) {
  const queryKey = JSON.stringify(query);
  const [navigation, setNavigation] = useState({
    queryKey,
    cursors: [null],
    index: 0,
  });
  const activeNavigation = navigation.queryKey === queryKey
    ? navigation
    : { queryKey, cursors: [null], index: 0 };
  const cursor = activeNavigation.cursors[activeNavigation.index] || null;

  useEffect(() => {
    setNavigation((current) => (
      current.queryKey === queryKey
        ? current
        : { queryKey, cursors: [null], index: 0 }
    ));
  }, [queryKey]);

  const resource = useResource(
    (signal) => loader({ ...query, page_size: 25, cursor }, signal),
    [cursor, queryKey],
  );

  const data = resource.data
    ? { ...resource.data, has_previous: activeNavigation.index > 0 }
    : resource.data;

  return {
    ...resource,
    data,
    previous: () => setNavigation((current) => ({
      ...current,
      index: Math.max(0, current.index - 1),
    })),
    next: () => {
      const nextCursor = resource.data?.next_cursor;
      if (!nextCursor) return;
      setNavigation((current) => {
        const cursors = current.cursors.slice(0, current.index + 1);
        cursors.push(nextCursor);
        return { ...current, cursors, index: current.index + 1 };
      });
    },
  };
}

const STATUS_OPTIONS = ['NEW', 'OPEN', 'PENDING', 'HOLD', 'SOLVED', 'CLOSED'];
const PRIORITY_OPTIONS = ['URGENT', 'HIGH', 'NORMAL', 'LOW'];
const EMPTY_TICKET_FILTERS = {
  status: '',
  priority: '',
  createdFrom: '',
  createdTo: '',
};

function dateBoundary(value, endOfDay = false) {
  if (!value) return undefined;
  const time = endOfDay ? '23:59:59.999' : '00:00:00.000';
  return new Date(`${value}T${time}`).toISOString();
}

export function TicketsPage() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search.trim());
  const [filterDraft, setFilterDraft] = useState(EMPTY_TICKET_FILTERS);
  const [filters, setFilters] = useState(EMPTY_TICKET_FILTERS);
  const [filterError, setFilterError] = useState(null);
  const query = useMemo(() => ({
    search: debouncedSearch || undefined,
    statuses: filters.status ? [filters.status] : undefined,
    priorities: filters.priority ? [filters.priority] : undefined,
    from_at: dateBoundary(filters.createdFrom),
    to_at: dateBoundary(filters.createdTo, true),
  }), [debouncedSearch, filters]);
  const page = useCursorPage(api.listTickets, query);

  const updateFilter = (field, value) => {
    setFilterDraft((current) => ({ ...current, [field]: value }));
  };

  const applyFilters = (event) => {
    event.preventDefault();
    if (
      filterDraft.createdFrom
      && filterDraft.createdTo
      && filterDraft.createdFrom > filterDraft.createdTo
    ) {
      setFilterError('A data inicial não pode ser posterior à data final.');
      return;
    }
    setFilterError(null);
    setFilters(filterDraft);
  };

  const clearFilters = () => {
    setFilterDraft(EMPTY_TICKET_FILTERS);
    setFilters(EMPTY_TICKET_FILTERS);
    setFilterError(null);
  };

  if (page.loading && !page.data) return <Spinner label="Carregando tickets" />;
  if (page.error && !page.data) return <ErrorState error={page.error} onRetry={page.reload} />;

  return <>
    <PageHeader eyebrow="Dados" title="Tickets" description="Tickets coletados da fonte HelpDesk e associados aos clientes identificados na ingestão." />
    <form className="data-filters" onSubmit={applyFilters}>
      <label><span>Status</span><select value={filterDraft.status} onChange={(event) => updateFilter('status', event.target.value)}><option value="">Todos</option>{STATUS_OPTIONS.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
      <label><span>Prioridade</span><select value={filterDraft.priority} onChange={(event) => updateFilter('priority', event.target.value)}><option value="">Todas</option>{PRIORITY_OPTIONS.map((value) => <option key={value} value={value}>{humanize(value)}</option>)}</select></label>
      <label><span>Criado a partir de</span><input type="date" value={filterDraft.createdFrom} onChange={(event) => updateFilter('createdFrom', event.target.value)} /></label>
      <label><span>Criado até</span><input type="date" value={filterDraft.createdTo} onChange={(event) => updateFilter('createdTo', event.target.value)} /></label>
      <div className="data-filter-actions"><button className="button button-secondary" type="button" onClick={clearFilters}>Limpar</button><button className="button button-primary" type="submit">Aplicar filtros</button></div>
      {filterError && <div className="form-error data-filter-error" role="alert">{filterError}</div>}
    </form>
    {page.error && <div className="form-error mutation-error" role="alert">{page.error.message || 'Não foi possível atualizar os tickets.'}</div>}
    <div className="toolbar">
      <SearchField value={search} onChange={setSearch} placeholder="Buscar ticket, assunto, descrição ou atendente" />
      {page.loading && <span className="loading-inline" role="status">Atualizando…</span>}
    </div>
    <DataTable rows={page.data?.items || []} emptyTitle="Nenhum ticket encontrado" columns={[
      { key: 'external_ticket_id', label: 'Ticket' },
      { key: 'subject', label: 'Assunto' },
      { key: 'status', label: 'Status', render: (row) => <Badge value={row.status} /> },
      { key: 'priority', label: 'Prioridade', render: (row) => <Badge value={row.priority} /> },
      { key: 'assignee_name', label: 'Atendente' },
      { key: 'source_created_at', label: 'Criado em', render: (row) => formatDate(row.source_created_at) },
      { key: 'source_updated_at', label: 'Atualizado', render: (row) => formatDate(row.source_updated_at) },
      { key: 'actions', label: '', render: (row) => <DetailLink to={`/tickets/${row.id}`} /> },
    ]} />
    <Pagination page={page.data} onPrevious={page.previous} onNext={page.next} />
  </>;
}

const EMPTY_CUSTOMER = {
  external_requester_id: '',
  requester_name: '',
  requester_email: '',
};

export function CustomersPage() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search.trim());
  const query = useMemo(() => ({
    search: debouncedSearch || undefined,
  }), [debouncedSearch]);
  const page = useCursorPage(api.listCustomers, query);
  const [form, setForm] = useState(EMPTY_CUSTOMER);
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState(null);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_CUSTOMER);
    setMutationError(null);
    setFormOpen(true);
  };

  const openEdit = (customer) => {
    setEditing(customer);
    setForm({
      external_requester_id: String(customer.external_requester_id),
      requester_name: customer.requester_name,
      requester_email: customer.requester_email,
    });
    setMutationError(null);
    setFormOpen(true);
  };

  const closeForm = () => {
    if (saving) return;
    setFormOpen(false);
    setEditing(null);
    setMutationError(null);
  };

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const submitCustomer = async (event) => {
    event.preventDefault();
    setMutationError(null);
    const externalId = Number(form.external_requester_id);
    if (!Number.isSafeInteger(externalId) || externalId <= 0) {
      setMutationError(new Error('Informe um ID externo inteiro e positivo.'));
      return;
    }
    const payload = {
      external_requester_id: externalId,
      requester_name: form.requester_name.trim(),
      requester_email: form.requester_email.trim().toLowerCase(),
    };
    if (!payload.requester_name || !payload.requester_email.includes('@')) {
      setMutationError(new Error('Preencha um nome e um e-mail válido.'));
      return;
    }

    setSaving(true);
    try {
      if (editing) await api.updateCustomer(editing.id, payload);
      else await api.createCustomer(payload);
      setFormOpen(false);
      setEditing(null);
      setForm(EMPTY_CUSTOMER);
      await page.reload();
    } catch (error) {
      setMutationError(error);
    } finally {
      setSaving(false);
    }
  };

  const removeCustomer = async (customer) => {
    const confirmed = window.confirm(`Excluir o cliente ${customer.requester_name}?`);
    if (!confirmed) return;
    setMutationError(null);
    try {
      await api.deleteCustomer(customer.id);
      await page.reload();
    } catch (error) {
      setMutationError(error);
    }
  };

  if (page.loading && !page.data) return <Spinner label="Carregando clientes" />;
  if (page.error && !page.data) return <ErrorState error={page.error} onRetry={page.reload} />;

  return <>
    <PageHeader
      eyebrow="Dados"
      title="Clientes"
      description="Gerencie os clientes. A ingestão cria ou reutiliza registros pelo e-mail e pelo ID externo recebidos do HelpDesk."
      action={<button className="button button-primary" type="button" onClick={openCreate}>Novo cliente</button>}
    />

    {formOpen && <section className="panel customer-form-panel" aria-label={editing ? 'Editar cliente' : 'Novo cliente'}>
      <div className="panel-header">
        <div><h2>{editing ? 'Editar cliente' : 'Cadastrar cliente'}</h2><p>{editing ? 'Atualize os dados usados no cruzamento.' : 'Inclua manualmente um cliente na base.'}</p></div>
      </div>
      <form className="customer-form" onSubmit={submitCustomer}>
        <label><span>ID externo</span><input type="number" min="1" required value={form.external_requester_id} onChange={(event) => updateField('external_requester_id', event.target.value)} /></label>
        <label><span>Nome</span><input type="text" maxLength="255" required value={form.requester_name} onChange={(event) => updateField('requester_name', event.target.value)} /></label>
        <label><span>E-mail</span><input type="email" maxLength="255" required value={form.requester_email} onChange={(event) => updateField('requester_email', event.target.value)} /></label>
        {mutationError && <div className="form-error" role="alert">{mutationError.message || 'Não foi possível salvar o cliente.'}</div>}
        <div className="form-actions">
          <button className="button button-secondary" type="button" onClick={closeForm} disabled={saving}>Cancelar</button>
          <button className="button button-primary" type="submit" disabled={saving}>{saving ? 'Salvando…' : 'Salvar cliente'}</button>
        </div>
      </form>
    </section>}

    {!formOpen && mutationError && <div className="form-error mutation-error" role="alert">{mutationError.message || 'Não foi possível concluir a operação.'}</div>}
    {page.error && <div className="form-error mutation-error" role="alert">{page.error.message || 'Não foi possível atualizar os clientes.'}</div>}

    <div className="toolbar">
      <SearchField value={search} onChange={setSearch} placeholder="Buscar por ID, nome ou e-mail" />
      {page.loading && <span className="loading-inline" role="status">Atualizando…</span>}
    </div>
    <DataTable rows={page.data?.items || []} emptyTitle="Nenhum cliente encontrado" columns={[
      { key: 'external_requester_id', label: 'ID externo' },
      { key: 'requester_name', label: 'Nome' },
      { key: 'requester_email', label: 'E-mail' },
      { key: 'created_at', label: 'Cadastrado em', render: (row) => formatDate(row.created_at) },
      { key: 'actions', label: '', render: (row) => <div className="table-actions"><DetailLink to={`/customers/${row.id}`} /><button className="table-action" type="button" onClick={() => openEdit(row)}>Editar</button><button className="table-action table-action-danger" type="button" onClick={() => removeCustomer(row)}>Excluir</button></div> },
    ]} />
    <Pagination page={page.data} onPrevious={page.previous} onNext={page.next} />
  </>;
}

function DetailPage({ type, id }) {
  const ticketMode = type === 'ticket';
  const { data, loading, error, reload } = useResource(() => ticketMode ? api.getTicket(id) : api.getCustomer(id), [id, type]);
  if (loading) return <Spinner label="Carregando detalhes" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const fields = ticketMode ? [
    ['ID externo', data.external_ticket_id], ['Assunto', data.subject], ['Descrição', data.description], ['Status', <Badge value={data.status} />], ['Prioridade', <Badge value={data.priority} />], ['Atendente', data.assignee_name], ['Criado na origem', formatDate(data.source_created_at)], ['Atualizado na origem', formatDate(data.source_updated_at)], ['Primeira resposta', formatDate(data.first_response_at)],
  ] : [
    ['ID externo', data.external_requester_id], ['Nome', data.requester_name], ['E-mail', data.requester_email], ['Cadastrado em', formatDate(data.created_at)], ['Atualizado em', formatDate(data.updated_at)],
  ];
  return <><PageHeader eyebrow="Detalhamento" title={ticketMode ? `Ticket #${data.external_ticket_id}` : data.requester_name} description="Registro retornado pela API." /><article className="panel detail-panel">{fields.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value || '—'}</strong></div>)}</article></>;
}

export function TicketDetailsPage({ id }) { return <DetailPage type="ticket" id={id} />; }
export function CustomerDetailsPage({ id }) { return <DetailPage type="customer" id={id} />; }
