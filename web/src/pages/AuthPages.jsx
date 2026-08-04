import { useState } from 'react';
import { Link } from '../app/router.jsx';
import { useAuth } from '../context/AuthContext.jsx';

function AuthPage({ mode }) {
  const isRegister = mode === 'register';
  const { login, register } = useAuth();
  const registrationEnabled = window.__WEB_CONFIG__?.REGISTRATION_ENABLED === true;
  const [form, setForm] = useState({ email: '', password: '', confirmation: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (isRegister && form.password !== form.confirmation) return setError('As senhas informadas não coincidem.');
    setSubmitting(true);
    try {
      await (isRegister ? register : login)({ email: form.email.trim(), password: form.password });
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível concluir a autenticação.');
    } finally {
      setSubmitting(false);
    }
  }

  if (isRegister && !registrationEnabled) return null;

  return (
    <div className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><span>HG</span><div><strong>HostGator Analytics</strong><small>Operação de suporte baseada em dados</small></div></div>
        <div><span className="eyebrow">Acesso seguro</span><h1>{isRegister ? 'Criar conta' : 'Entrar na plataforma'}</h1><p>{isRegister ? 'Cadastre um usuário para acessar o ambiente analítico.' : 'Use suas credenciais para acessar os painéis.'}</p></div>
        <form onSubmit={handleSubmit}>
          <label>E-mail<input type="email" name="email" autoComplete="email" value={form.email} onChange={updateField} required /></label>
          <label>Senha<input type="password" name="password" autoComplete={isRegister ? 'new-password' : 'current-password'} minLength="8" value={form.password} onChange={updateField} required /></label>
          {isRegister && <label>Confirmar senha<input type="password" name="confirmation" autoComplete="new-password" minLength="8" value={form.confirmation} onChange={updateField} required /></label>}
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? 'Processando...' : isRegister ? 'Criar conta' : 'Entrar'}</button>
        </form>
        {(isRegister || registrationEnabled) && <p className="auth-switch">{isRegister ? 'Já possui uma conta?' : 'Ainda não possui uma conta?'} <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Entrar' : 'Registrar-se'}</Link></p>}
      </section>
      <aside className="auth-visual"><div><span className="eyebrow">Análise operacional</span><h2>Visibilidade objetiva sobre tickets, clientes e atendimento.</h2><p>Centralize indicadores, investigue recorrências e acompanhe a qualidade do suporte em uma interface única.</p></div></aside>
    </div>
  );
}

export function LoginPage() { return <AuthPage mode="login" />; }
export function RegisterPage() { return <AuthPage mode="register" />; }
