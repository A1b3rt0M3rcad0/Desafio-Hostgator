import { Link } from '../app/router.jsx';
import { useAuth } from '../context/AuthContext.jsx';

const navigation = [
  ['/dashboard', 'Visão geral'],
  ['/tickets', 'Tickets'],
  ['/customers', 'Clientes'],
  ['/metrics', 'Métricas'],
  ['/exports', 'Exportação de dados'],
];

export function AppLayout({ pathname, children }) {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/dashboard" className="brand"><span>HG</span><strong>{window.__WEB_CONFIG__?.APP_NAME || 'HostGator Analytics'}</strong></Link>
        <nav aria-label="Navegação principal">
          {navigation.map(([path, label]) => <Link key={path} to={path} className={pathname.startsWith(path) ? 'active' : ''}>{label}</Link>)}
        </nav>
        <div className="sidebar-footer"><small>{user?.email || user?.id || 'Usuário autenticado'}</small><button type="button" onClick={logout}>Sair</button></div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
