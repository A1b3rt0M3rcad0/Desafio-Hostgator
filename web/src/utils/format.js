export function formatDate(value, options = {}) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: options.dateStyle || 'short',
    timeStyle: options.withTime === false ? undefined : 'short',
  }).format(date);
}

export function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value || 0));
}

export function formatPercent(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 }).format(Number(value || 0));
}

export function humanize(value) {
  if (!value) return '—';
  return String(value).toLowerCase().replaceAll('_', ' ').replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

export function minutesBetween(start, end) {
  if (!start || !end) return null;
  return Math.max(0, Math.round((new Date(end) - new Date(start)) / 60000));
}

export function formatDuration(minutes) {
  if (minutes === null || minutes === undefined || Number.isNaN(minutes)) return '—';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours}h${rest ? ` ${rest}min` : ''}`;
}
