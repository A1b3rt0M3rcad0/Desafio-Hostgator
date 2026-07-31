import { useMemo, useState } from 'react';
import { DataTable } from '../components/DataTable.jsx';
import { PageHeader } from '../components/UI.jsx';

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
  const [processedAt, setProcessedAt] = useState(null);

  async function processFile(selectedFile) {
    setError('');
    setRecords([]);
    setProcessedAt(null);
    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith('.json')) return setError('Selecione um arquivo JSON.');
    if (selectedFile.size > 10 * 1024 * 1024) return setError('O arquivo excede o limite de 10 MB.');
    try {
      const parsed = JSON.parse(await selectedFile.text());
      const normalized = normalizeRecords(parsed);
      setRecords(normalized);
      setProcessedAt(new Date());
    } catch (parseError) {
      setError(parseError.message || 'Não foi possível processar o arquivo.');
    }
  }

  const columns = useMemo(() => {
    const keys = Object.keys(records[0] || {}).slice(0, 6);
    return keys.map((key) => ({ key, label: key.replaceAll('_', ' ') }));
  }, [records]);

  function downloadReport() {
    const report = { file: file?.name, processed_at: processedAt?.toISOString(), records: records.length, sample: records.slice(0, 10) };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'relatorio-importacao.json';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <><PageHeader eyebrow="Coleta" title="Importação de dados RAW" description="Validação e pré-visualização local de arquivos JSON, sem cadastro de fontes ou alteração manual dos registros." /><section className="panel upload-panel"><label className="dropzone"><input type="file" accept="application/json,.json" onChange={(event) => { const selected = event.target.files?.[0]; setFile(selected); processFile(selected); }} /><strong>Selecionar arquivo JSON</strong><span>Limite de 10 MB. O arquivo é processado no navegador e não é persistido.</span></label>{error && <div className="form-error" role="alert">{error}</div>}{records.length > 0 && <div className="import-summary"><div><span>Arquivo</span><strong>{file.name}</strong></div><div><span>Registros</span><strong>{records.length}</strong></div><button className="button button-secondary" type="button" onClick={downloadReport}>Baixar relatório</button></div>}</section>{records.length > 0 && <section className="panel"><div className="panel-header"><div><span className="eyebrow">Pré-visualização</span><h2>Primeiros 20 registros</h2></div></div><DataTable columns={columns} rows={records.slice(0, 20)} /></section>}</>;
}
