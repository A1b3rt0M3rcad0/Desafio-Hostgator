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
  return <><PageHeader eyebrow="Dados" title="Tickets" description="Visualização somente leitura dos tickets coletados." /><div className="toolbar"><SearchField value={search} onChange={setSearch} placeholder="Buscar assunto, descrição ou atendente" /></div><DataTable rows={rows} emptyTitle="Nenhum ticket encontrado" columns={[
    { key: 'external_ticket_id', label: 'Ticket' },
    { key: 'subject', label: 'Assunto' },
    { key: 'status', label: 'Status', render: (row) => <Badge value={row.status} /> },
    { key: 'priority', label: 'Prioridade', render: (row) => <Badge value={row.priority} /> },
    { key: 'assignee_name', label: 'Atendente' },
    { key: 'source_updated_at', label: 'Atualizado', render: (row) => formatDate(row.source_updated_at) },
    { key: 'actions', label: '', render: (row) => <DetailLink to={`/tickets/${row.id}`} /> },
  ]} /><Pagination page={page.data} onPrevious={page.previous} onNext={page.next} /></>;
}

export function CustomersPage() {
  const page = useCursorPage(api.listCustomers);
  const [search, setSearch] = useState('');
  const rows = useMemo(() => (page.data?.items || []).filter((customer) => `${customer.requester_name} ${customer.requester_email}`.toLowerCase().includes(search.toLowerCase())), [page.data, search]);
  if (page.loading) return <Spinner label="Carregando clientes" />;
  if (page.error) return <ErrorState error={page.error} onRetry={page.reload} />;
  return <><PageHeader eyebrow="Dados" title="Clientes" description="Visualização somente leitura dos clientes associados aos tickets." /><div className="toolbar"><SearchField value={search} onChange={setSearch} placeholder="Buscar nome ou e-mail" /></div><DataTable rows={rows} emptyTitle="Nenhum cliente encontrado" columns={[
    { key: 'external_requester_id', label: 'ID externo' },
    { key: 'requester_name', label: 'Nome' },
    { key: 'requester_email', label: 'E-mail' },
    { key: 'created_at', label: 'Coletado em', render: (row) => formatDate(row.created_at) },
    { key: 'actions', label: '', render: (row) => <DetailLink to={`/customers/${row.id}`} /> },
  ]} /><Pagination page={page.data} onPrevious={page.previous} onNext={page.next} /></>;
}

function DetailPage({ type, id }) {
  const ticketMode = type === 'ticket';
  const { data, loading, error, reload } = useResource(() => ticketMode ? api.getTicket(id) : api.getCustomer(id), [id, type]);
  if (loading) return <Spinner label="Carregando detalhes" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const fields = ticketMode ? [
    ['ID externo', data.external_ticket_id], ['Assunto', data.subject], ['Descrição', data.description], ['Status', <Badge value={data.status} />], ['Prioridade', <Badge value={data.priority} />], ['Atendente', data.assignee_name], ['Criado na origem', formatDate(data.source_created_at)], ['Atualizado na origem', formatDate(data.source_updated_at)], ['Primeira resposta', formatDate(data.first_response_at)],
  ] : [
    ['ID externo', data.external_requester_id], ['Nome', data.requester_name], ['E-mail', data.requester_email], ['Coletado em', formatDate(data.created_at)], ['Atualizado em', formatDate(data.updated_at)],
  ];
  return <><PageHeader eyebrow="Detalhamento" title={ticketMode ? `Ticket #${data.external_ticket_id}` : data.requester_name} description="Registro somente leitura retornado pela API." /><article className="panel detail-panel">{fields.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value || '—'}</strong></div>)}</article></>;
}

export function TicketDetailsPage({ id }) { return <DetailPage type="ticket" id={id} />; }
export function CustomerDetailsPage({ id }) { return <DetailPage type="customer" id={id} />; }
