import { useEffect, useMemo } from 'react';
import { useRouter, navigate } from './router.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { AppLayout } from '../components/AppLayout.jsx';
import { Spinner } from '../components/UI.jsx';
import { LoginPage, RegisterPage } from '../pages/AuthPages.jsx';
import { DashboardPage } from '../pages/DashboardPage.jsx';
import { CustomerDetailsPage, CustomersPage, TicketDetailsPage, TicketsPage } from '../pages/DataPages.jsx';
import { ExportsPage } from '../pages/ExportsPage.jsx';
import { MetricsPage } from '../pages/MetricsPage.jsx';
import { ErrorPage } from '../pages/ErrorPages.jsx';

export function App() {
  const { user, loading } = useAuth();
  const routes = useMemo(() => [
    { path: '/', public: false, component: DashboardPage },
    { path: '/login', public: true, component: LoginPage },
    { path: '/register', public: true, component: RegisterPage },
    { path: '/dashboard', public: false, component: DashboardPage },
    { path: '/tickets', public: false, component: TicketsPage },
    { path: '/tickets/:id', public: false, component: TicketDetailsPage },
    { path: '/customers', public: false, component: CustomersPage },
    { path: '/customers/:id', public: false, component: CustomerDetailsPage },
    { path: '/metrics', public: false, component: MetricsPage },
    { path: '/exports', public: false, component: ExportsPage },
    { path: '/401', public: true, component: () => <ErrorPage code="401" title="Sessão necessária" description="Autentique-se para continuar." /> },
    { path: '/403', public: true, component: () => <ErrorPage code="403" title="Acesso negado" description="Seu usuário não possui permissão para esta ação." /> },
    { path: '/500', public: true, component: () => <ErrorPage code="500" title="Erro interno" description="A aplicação não conseguiu concluir a operação." /> },
  ], []);
  const route = useRouter(routes);

  useEffect(() => {
    if (loading) return;
    if (route.path === '/') navigate(user ? '/dashboard' : '/login', { replace: true });
    else if (!route.public && !user) navigate('/login', { replace: true });
    else if (route.public && user && ['/login', '/register'].includes(route.path)) navigate('/dashboard', { replace: true });
  }, [loading, route.path, route.public, user]);

  if (loading) return <Spinner label="Verificando sessão" />;
  if (route.path === '*') return <ErrorPage />;
  if ((!route.public && !user) || (route.public && user && ['/login', '/register'].includes(route.path))) return null;

  const Component = route.component;
  const content = <Component {...route.params} />;
  return route.public ? content : <AppLayout pathname={route.pathname}>{content}</AppLayout>;
}
