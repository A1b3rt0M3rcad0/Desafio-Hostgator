# Dados simulados do HelpDesk

Este diretório contém o gerador importado pelo worker e o snapshot JSON da rodada atual.

```text
data/
├── generate_tickets_mock.py
└── tickets.json              # gerado em runtime; ignorado pelo Git
```

## Funcionamento

Quando a ingestão automática está ligada, cada ciclo executa o seguinte fluxo:

```text
worker
  -> chama generate_and_write_batch(...)
  -> gera 30 tickets para uma base padrão de 500 clientes
  -> grava tickets.json.tmp
  -> substitui tickets.json atomicamente
  -> lê os 30 registros do JSON
  -> persiste clientes, tickets, tags e avaliações
  -> aguarda o intervalo configurado
```

O arquivo `tickets.json` contém somente a rodada atual. Ele é sobrescrito no ciclo seguinte.

O gerador é responsável por todo o conteúdo fictício:

- identidade do cliente;
- assunto e descrição do ticket;
- status e prioridade;
- atendente;
- primeira resposta;
- tags;
- satisfação;
- datas da origem.

O worker não inventa esses valores. Ele chama o módulo, lê o JSON produzido e utiliza os repositories para separar e persistir as relações.

## Valores padrão

```env
WORKER_BATCH_SIZE=30
WORKER_INTERVAL_SECONDS=30
MOCK_CUSTOMER_COUNT=500
MOCK_START_TICKET_ID=100001
MOCK_YEAR=2026
MOCK_SEED=hostgator-challenge-v4
```

Os clientes possuem identidades determinísticas dentro do intervalo de IDs externos `40000–40499`. Cada rodada seleciona 30 clientes da base em sequência circular. Depois que a base inteira é percorrida, clientes anteriores voltam a receber tickets, permitindo métricas de recorrência.

Os tickets recebem IDs externos novos em cada ciclo:

```text
rodada 1: 100001–100030
rodada 2: 100031–100060
rodada 3: 100061–100090
```

## Geração manual

A partir da raiz do repositório:

```bash
python data/generate_tickets_mock.py --pretty
```

Exemplo configurado:

```bash
python data/generate_tickets_mock.py \
  --cycle 4 \
  --start-id 100121 \
  --count 30 \
  --customers 500 \
  --year 2026 \
  --pretty
```

A escrita é atômica: o conteúdo é validado em `tickets.json.tmp`, sincronizado em disco e somente então substitui `tickets.json`.
