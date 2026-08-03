import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { useResource } from '../hooks/useResource.js';
import { Badge, DetailLink, ErrorState, PageHeader, Pagination, SearchField, Spinner } from '../components/UI.jsx';
import { DataTable } from '../components/DataTable.jsx';
import { formatDate } from '../utils/format.js';

function useCursorPage(loader) {
  const [cursor, setCursor] = useState(null);
  const resource = useResource(() => loader({ page_size: 25, cursor }), [cursor]);
  return {
    ...resource,
    previous: () => setCursor(resource.data?.previous_cursor || null),
    next: () => setCursor(resource.data?.next_cursor || null),
  };
}

export function TicketsPage() {
  const page = useCursorPage(api.listTickets);
  const [search, setSearch] = useState('');
  const rows = useMemo(() => (page.data?.items || []).filter((ticket) => `${ticket.subject} ${ticket.description} ${ticket.assignee_name || ''}`.toLowerCase().includes(search.toLowerCase())), [page.data, search]);
  if (page.loading) return <Spinner label="Carregando tickets" />;
  if (page.error) return <ErrorState error={page.error} onRetry={page.reload} />;
  return <><PageHeader eyebrow="Dados" title="Tickets" description="Tickets coletados da fonte HelpDesk e associados aos clientes identificados na ingestão." /><div className="toolbar"><SearchField value={search} onChange={setSearch} placeholder="Buscar assunto, descrição ou atendente" /></div><DataTable rows={rows} emptyTitle="Nenhum ticket encontrado" columns={[
    { key: 'external_ticket_id', label: 'Ticket' },
    { key: 'subject', label: 'Assunto' },
    { key: 'status', label: 'Status', render: (row) => <Badge value={row.status} /> },
    { key: 'priority', label: 'Prioridade', render: (row) => <Badge value={row.priority} /> },
    { key: 'assignee_name', label: 'Atendente' },
    { key: 'source_updated_at', label: 'Atualizado', render: (row) => formatDate(row.source_updated_at) },
    { key: 'actions', label: '', render: (row) => <DetailLink to={`/tickets/${row.id}`} /> },
  ]} /><Pagination page={page.data} onPrevious={page.previous} onNext={page.next} /></>;
}

const EMPTY_CUSTOMER = {
  external_requester_id: '',
  requester_name: '',
  requester_email: '',
};

export function CustomersPage() {
  const page = useCursorPage(api.listCustomers);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState(EMPTY_CUSTOMER);
  const [editing, setEditing] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mutationError, setMutationError] = useState(null);

  const rows = useMemo(() => (page.data?.items || []).filter((customer) => `${customer.requester_name} ${customer.requester_email}`.toLowerCase().includes(search.toLowerCase())), [page.data, search]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_CUSTOMER);
    setMutationError(null);
    setFormOpen(true);
  };

  const openEdit = (customer) => {
    setEditing(customer);
    setForm({
      external_requester_id: customer.external_requester_id ? String(customer.external_requester_id) : '',
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
    const externalIdText = form.external_requester_id.trim();
    const externalId = externalIdText ? Number(externalIdText) : null;
    if (externalId !== null && (!Number.isSafeInteger(externalId) || externalId <= 0)) {
      setMutationError(new Error('O ID externo deve ser um inteiro positivo.'));
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
    const confirmed = window.confirm(`Remover ${customer.requester_name} do monitoramento? O histórico será preservado.`);
    if (!confirmed) return;
    setMutationError(null);
    try {
      await api.deleteCustomer(customer.id);
      await page.reload();
    } catch (error) {
      setMutationError(error);
    }
  };

  if (page.loading) return <Spinner label="Carregando clientes" />;
  if (page.error) return <ErrorState error={page.error} onRetry={page.reload} />;

  return <>
    <PageHeader
      eyebrow="Dados"
      title="Clientes"
      description="Cadastre os clientes monitorados. A ingestão cruza exclusivamente o e-mail cadastrado com a fonte HelpDesk."
      action={<button className="button button-primary" type="button" onClick={openCreate}>Novo cliente</button>}
    />

    {formOpen && <section className="panel customer-form-panel" aria-label={editing ? 'Editar cliente' : 'Novo cliente'}>
      <div className="panel-header">
        <div><h2>{editing ? 'Editar cliente' : 'Cadastrar cliente'}</h2><p>{editing ? 'Atualize os dados usados no cruzamento.' : 'Inclua manualmente um cliente na base.'}</p></div>
      </div>
      <form className="customer-form" onSubmit={submitCustomer}>
        <label><span>ID externo (opcional)</span><input type="number" min="1" value={form.external_requester_id} onChange={(event) => updateField('external_requester_id', event.target.value)} /></label>
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

    <div className="toolbar"><SearchField value={search} onChange={setSearch} placeholder="Buscar nome ou e-mail" /></div>
    <DataTable rows={rows} emptyTitle="Nenhum cliente encontrado" columns={[
      { key: 'external_requester_id', label: 'ID externo', render: (row) => row.external_requester_id || '—' },
      { key: 'requester_name', label: 'Nome' },
      { key: 'requester_email', label: 'E-mail' },
      { key: 'created_at', label: 'Cadastrado em', render: (row) => formatDate(row.created_at) },
      { key: 'actions', label: '', render: (row) => <div className="table-actions"><DetailLink to={`/customers/${row.id}`} /><button className="table-action" type="button" onClick={() => openEdit(row)}>Editar</button><button className="table-action table-action-danger" type="button" onClick={() => removeCustomer(row)}>Remover monitoramento</button></div> },
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
