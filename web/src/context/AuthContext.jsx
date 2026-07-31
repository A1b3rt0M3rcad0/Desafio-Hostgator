import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api, ApiError } from '../services/api.js';
import { navigate } from '../app/router.jsx';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.me()
      .then((currentUser) => { if (active) setUser(currentUser); })
      .catch((error) => {
        if (active && !(error instanceof ApiError && error.status === 401)) console.error(error);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    async login(credentials) {
      const response = await api.login(credentials);
      setUser(response.user);
      navigate('/dashboard', { replace: true });
    },
    async register(credentials) {
      const response = await api.register(credentials);
      setUser(response.user);
      navigate('/dashboard', { replace: true });
    },
    async logout() {
      try { await api.logout(); } finally {
        setUser(null);
        navigate('/login', { replace: true });
      }
    },
  }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth deve ser usado dentro de AuthProvider.');
  return context;
}
