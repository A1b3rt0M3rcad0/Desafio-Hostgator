import { useEffect, useState } from 'react';
import { Link } from '../app/router.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { api } from '../services/api.js';

const navigation = [
  ['/dashboard', 'Visão geral'],
  ['/tickets', 'Tickets'],
  ['/customers', 'Clientes'],
  ['/metrics', 'Métricas'],
  ['/exports', 'Exportação de dados'],
];

function IngestionToggleButton() {
  const [enabled, setEnabled] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    api.getIngestionControl()
      .then((control) => {
        if (active) setEnabled(Boolean(control.enabled));
      })
      .catch((requestError) => {
        if (active) setError(requestError);
      });
    return () => { active = false; };
  }, []);

  async function toggle() {
    if (enabled === null || updating) return;
    setUpdating(true);
    setError(null);
    try {
      const control = await api.updateIngestionControl(!enabled);
      setEnabled(Boolean(control.enabled));
    } catch (requestError) {
      setError(requestError);
    } finally {
      setUpdating(false);
    }
  }

  const label = error
    ? 'Ingestão indisponível'
    : enabled
      ? 'Desligar ingestão automática'
      : 'Ligar ingestão automática';

  return (
    <button
      type="button"
      className="button button-secondary"
      disabled={enabled === null || updating || Boolean(error)}
      onClick={toggle}
      title={error?.message || undefined}
    >
      {updating ? 'Atualizando ingestão...' : label}
    </button>
  );
}

export function AppLayout({ pathname, children }) {
  const { user, logout } = useAuth();
  const showIngestionControl = pathname.startsWith('/dashboard');

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/dashboard" className="brand"><span>HG</span><strong>{window.__WEB_CONFIG__?.APP_NAME || 'HostGator Analytics'}</strong></Link>
        <nav aria-label="Navegação principal">
          {navigation.map(([path, label]) => <Link key={path} to={path} className={pathname.startsWith(path) ? 'active' : ''}>{label}</Link>)}
        </nav>
        <div className="sidebar-footer"><small>{user?.email || user?.id || 'Usuário autenticado'}</small><button type="button" onClick={logout}>Sair</button></div>
      </aside>
      <main className="main-content">
        {showIngestionControl ? (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
            <IngestionToggleButton />
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}
