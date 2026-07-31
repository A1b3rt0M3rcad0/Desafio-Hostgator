import { useMemo, useState } from 'react';
import { api } from '../services/api.js';
import { DataTable } from '../components/DataTable.jsx';
import { PageHeader } from '../components/UI.jsx';
import { formatNumber } from '../utils/format.js';

function normalizeRecords(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.tickets)) return payload.tickets;
  if (Array.isArray(payload?.data)) return payload.data;
  throw new Error('O JSON deve conter uma lista ou uma propriedade tickets/data com uma lista.');
}

export function ImportPage() {
  const [file, setFile] = useState(null);
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function processFile(selectedFile) {
    setError('');
    setRecords([]);
    setResult(null);
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith('.json')) return setError('Selecione um arquivo JSON.');
    if (selectedFile.size > 25 * 1024 * 1024) return setError('O arquivo excede o limite de 25 MB.');
    try {
      const parsed = JSON.parse(await selectedFile.text());
      const normalized = normalizeRecords(parsed);
      if (!normalized.length) throw new Error('O arquivo não contém tickets.');
      setRecords(normalized);
    } catch (parseError) {
      setError(parseError.message || 'Não foi possível processar o arquivo.');
    }
  }

  async function synchronize() {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.syncTickets(records));
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível sincronizar os tickets.');
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo(() => {
    const keys = Object.keys(records[0] || {}).slice(0, 8);
    return keys.map((key) => ({
      key,
      label: key.replaceAll('_', ' '),
      render: (row) => typeof row[key] === 'object' && row[key] !== null ? JSON.stringify(row[key]) : row[key],
    }));
  }, [records]);

  return (
    <>
      <PageHeader eyebrow="Coleta" title="Importação de dados RAW" description="Valide o JSON do mock e sincronize clientes, tickets, tags e avaliações no banco. A operação é idempotente por ticket_id e updated_at." />
      <section className="panel upload-panel">
        <label className="dropzone">
          <input type="file" accept="application/json,.json" onChange={(event) => { const selected = event.target.files?.[0]; setFile(selected); processFile(selected); }} />
          <strong>Selecionar arquivo JSON</strong>
          <span>Limite de 25 MB. O conteúdo só é persistido após confirmação.</span>
        </label>
        {error && <div className="form-error" role="alert">{error}</div>}
        {records.length > 0 && (
          <div className="import-summary">
            <div><span>Arquivo</span><strong>{file.name}</strong></div>
            <div><span>Tickets validados</span><strong>{formatNumber(records.length)}</strong></div>
            <button className="button button-primary" type="button" disabled={busy} onClick={synchronize}>{busy ? 'Sincronizando…' : 'Sincronizar no banco'}</button>
          </div>
        )}
        {result && (
          <div className="form-success" role="status">
            Sincronização concluída: {formatNumber(result.created)} criados, {formatNumber(result.updated)} atualizados, {formatNumber(result.unchanged)} inalterados, {formatNumber(result.customers_created)} clientes e {formatNumber(result.tags_created)} tags criados.
          </div>
        )}
      </section>
      {records.length > 0 && <section className="panel"><div className="panel-header"><div><span className="eyebrow">Pré-visualização</span><h2>Primeiros 20 registros</h2></div></div><DataTable columns={columns} rows={records.slice(0, 20)} rowKey="ticket_id" /></section>}
    </>
  );
}
