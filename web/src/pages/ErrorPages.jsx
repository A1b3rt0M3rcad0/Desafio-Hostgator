import { Link } from '../app/router.js';

export function ErrorPage({ code = '404', title = 'Página não encontrada', description = 'A rota informada não existe ou foi removida.' }) {
  return <div className="error-page"><span>{code}</span><h1>{title}</h1><p>{description}</p><Link className="button button-primary" to="/dashboard">Voltar ao dashboard</Link></div>;
}
