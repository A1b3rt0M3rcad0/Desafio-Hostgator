import { Link } from '../app/router.js';
import { humanize } from '../utils/format.js';

export function Spinner({ label = 'Carregando' }) {
  return <div className="state-box" role="status"><span className="spinner" aria-hidden="true" /><span>{label}</span></div>;
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state-box state-error" role="alert">
      <strong>Não foi possível carregar os dados.</strong>
      <span>{error?.message || 'Erro inesperado.'}</span>
      {onRetry && <button className="button button-secondary" type="button" onClick={onRetry}>Tentar novamente</button>}
    </div>
  );
}

export function EmptyState({ title = 'Nenhum dado encontrado', description = 'A consulta não retornou registros.' }) {
  return <div className="state-box"><strong>{title}</strong><span>{description}</span></div>;
}

export function Badge({ value, variant }) {
  const normalized = String(value || 'indefinido').toLowerCase();
  return <span className={`badge badge-${variant || normalized}`}>{humanize(value)}</span>;
}

export function KpiCard({ label, value, detail }) {
  return <article className="kpi-card"><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</article>;
}

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}

export function SearchField({ value, onChange, placeholder = 'Buscar' }) {
  return (
    <label className="search-field">
      <span className="sr-only">Buscar</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

export function Pagination({ page, onPrevious, onNext }) {
  return (
    <div className="pagination">
      <button type="button" className="button button-secondary" disabled={!page?.has_previous} onClick={onPrevious}>Anterior</button>
      <span>Paginação por cursor</span>
      <button type="button" className="button button-secondary" disabled={!page?.has_next} onClick={onNext}>Próxima</button>
    </div>
  );
}

export function DetailLink({ to, children = 'Visualizar' }) {
  return <Link className="table-link" to={to}>{children}</Link>;
}
