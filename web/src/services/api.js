const config = window.__WEB_CONFIG__ || {};
const API_URL = String(config.API_URL || '/api').replace(/\/$/, '');
const REQUEST_TIMEOUT_MS = Number(config.REQUEST_TIMEOUT_MS || 15000);
const CSRF_COOKIE_NAME = config.CSRF_COOKIE_NAME || 'csrf_token';
const CSRF_HEADER_NAME = config.CSRF_HEADER_NAME || 'X-CSRF-Token';

let refreshPromise = null;

export class ApiError extends Error {
  constructor(message, status, code, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie.split('; ').find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function buildUrl(path, query) {
  const normalizedBase = `${API_URL}/`;
  const apiRoot = new URL(normalizedBase, window.location.origin);
  const url = new URL(String(path || '').replace(/^\//, ''), apiRoot);

  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) value.forEach((item) => url.searchParams.append(key, item));
    else url.searchParams.set(key, String(value));
  });

  return url.toString();
}

async function parseErrorResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  const text = await response.text();
  return text || null;
}

async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = request('/auth/refresh', { method: 'POST', retryAuth: false })
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function request(path, options = {}) {
  const {
    method = 'GET',
    body,
    query,
    headers = {},
    retryAuth = true,
    signal,
    responseType = 'json',
    withHeaders = false,
  } = options;

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });

  const normalizedMethod = method.toUpperCase();
  const requestHeaders = { Accept: responseType === 'blob' ? '*/*' : 'application/json', ...headers };
  if (body !== undefined && !(body instanceof FormData)) requestHeaders['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD', 'OPTIONS'].includes(normalizedMethod)) {
    const csrf = readCookie(CSRF_COOKIE_NAME);
    if (csrf) requestHeaders[CSRF_HEADER_NAME] = csrf;
  }

  try {
    const response = await fetch(buildUrl(path, query), {
      method: normalizedMethod,
      credentials: 'include',
      headers: requestHeaders,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
      signal: controller.signal,
    });

    if (response.status === 401 && retryAuth && !path.startsWith('/auth/')) {
      await refreshSession();
      return request(path, { ...options, retryAuth: false });
    }

    if (!response.ok) {
      const payload = await parseErrorResponse(response);
      const error = payload?.error || payload;
      throw new ApiError(
        error?.message || `A API respondeu com status ${response.status}.`,
        response.status,
        error?.code,
        error,
      );
    }

    let payload = null;
    if (response.status !== 204) {
      if (responseType === 'blob') payload = await response.blob();
      else {
        const contentType = response.headers.get('content-type') || '';
        payload = contentType.includes('application/json') ? await response.json() : await response.text();
      }
    }
    return withHeaders ? { payload, headers: response.headers } : payload;
  } catch (error) {
    if (error.name === 'AbortError') throw new ApiError('A requisição excedeu o tempo limite.', 408, 'request_timeout');
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function filenameFromHeaders(headers, fallback) {
  const disposition = headers.get('content-disposition') || '';
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] || fallback;
}

async function download(path, body, fallback) {
  const { payload, headers } = await request(path, {
    method: 'POST',
    body,
    responseType: 'blob',
    withHeaders: true,
  });
  const url = URL.createObjectURL(payload);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filenameFromHeaders(headers, fallback);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return anchor.download;
}

export async function ensureAnonymousCsrf() {
  await request('/auth/csrf', { retryAuth: false });
}

export const api = {
  login: async (credentials) => {
    await ensureAnonymousCsrf();
    return request('/auth/login', { method: 'POST', body: credentials, retryAuth: false });
  },
  register: async (credentials) => {
    await ensureAnonymousCsrf();
    await request('/auth/register', { method: 'POST', body: credentials, retryAuth: false });
    return api.login(credentials);
  },
  me: () => request('/auth/me', { retryAuth: false }),
  logout: () => request('/auth/logout', { method: 'POST', retryAuth: false }),
  listTickets: (query) => request('/tickets', { query }),
  getTicket: (id) => request(`/tickets/${id}`),
  listCustomers: (query) => request('/customers', { query }),
  getCustomer: (id) => request(`/customers/${id}`),
  listTags: (query) => request('/tags', { query }),
  listRatings: (query) => request('/satisfaction-ratings', { query }),
  getDashboard: (query) => request('/dashboard', { query }),
  listCustomerMetrics: (query) => request('/metrics/customers', { query }),
  getReportCatalog: () => request('/reports/catalog'),
  previewRawReport: (body) => request('/reports/raw/preview', { method: 'POST', body }),
  exportRawReport: (body) => download('/reports/raw/export', body, `tickets-raw.${body.format || 'csv'}`),
  exportMetricsReport: (body) => download('/reports/metrics/export', body, `metricas.${body.format || 'csv'}`),
};
