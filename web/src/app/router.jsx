import { useEffect, useMemo, useState } from 'react';

const routeListeners = new Set();

function notifyRouteChange() {
  routeListeners.forEach((listener) => listener(window.location.pathname));
}

export function navigate(path, { replace = false } = {}) {
  const method = replace ? 'replaceState' : 'pushState';
  window.history[method]({}, '', path);
  notifyRouteChange();
  window.scrollTo({ top: 0, behavior: 'instant' });
}

export function Link({ to, className, children, onClick, ...props }) {
  function handleClick(event) {
    onClick?.(event);
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    navigate(to);
  }

  return <a href={to} className={className} onClick={handleClick} {...props}>{children}</a>;
}

function compileRoute(pattern) {
  const keys = [];
  const expression = pattern
    .split('/')
    .map((part) => {
      if (part.startsWith(':')) {
        keys.push(part.slice(1));
        return '([^/]+)';
      }
      return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    })
    .join('/');
  return { keys, regex: new RegExp(`^${expression}/?$`) };
}

export function useRouter(routes) {
  const [pathname, setPathname] = useState(window.location.pathname);
  const compiled = useMemo(
    () => routes.map((route) => ({ ...route, ...compileRoute(route.path) })),
    [routes],
  );

  useEffect(() => {
    const handler = () => setPathname(window.location.pathname);
    routeListeners.add(handler);
    window.addEventListener('popstate', handler);
    return () => {
      routeListeners.delete(handler);
      window.removeEventListener('popstate', handler);
    };
  }, []);

  for (const route of compiled) {
    const match = pathname.match(route.regex);
    if (match) {
      const params = Object.fromEntries(route.keys.map((key, index) => [key, decodeURIComponent(match[index + 1])]));
      return { ...route, params, pathname };
    }
  }

  return { path: '*', pathname, params: {} };
}
