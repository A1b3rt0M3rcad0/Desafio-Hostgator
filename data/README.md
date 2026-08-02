# Dados simulados do HelpDesk

Este diretório contém o catálogo canônico de clientes usado na demonstração local e o gerador do arquivo JSON estático consumido pelo worker.

```text
data/
├── customers_seed.json
├── generate_tickets_mock.py
└── tickets.json              # gerado localmente; ignorado pelo Git
```

## Fixture padrão

O comando padrão gera:

- 30 clientes canônicos;
- 10 tickets por cliente;
- 300 tickets no total;
- IDs externos a partir de `100001`;
- datas entre `2026-01-01T00:00:00Z` e `2026-08-01T05:30:00Z`;
- múltiplos status, prioridades, tags, responsáveis e avaliações.

As identidades do solicitante não são inventadas separadamente pelo gerador. Cada ticket copia exatamente `external_requester_id`, nome e e-mail de `customers_seed.json`, permitindo o cruzamento com a tabela `customers`.

## Geração manual

A partir da raiz do repositório:

```bash
python data/generate_tickets_mock.py --pretty
```

Outro ano pode ser selecionado:

```bash
python data/generate_tickets_mock.py --year 2025 --pretty
```

Também é possível escolher uma âncora precisa:

```bash
python data/generate_tickets_mock.py --anchor 2026-07-15T12:00:00Z --pretty
```

O arquivo é validado antes da substituição e gravado de forma atômica em `data/tickets.json`.

## Inicialização pelo Compose

Em `docker compose up --build -d`, o serviço one-shot `mock-data` gera `data/tickets.json`. Em seguida, o serviço `seed` registra de forma idempotente os mesmos 30 clientes no banco local. Somente depois API e worker são iniciados.

O worker monta `data/` como `/data` em modo somente leitura e processa um lote de até 30 registros a cada 30 segundos.

Em um ambiente que já possua sua própria base de clientes, use:

```env
DEMO_SEED_ENABLED=false
```

Nesse caso, a fonte estática deve conter solicitantes compatíveis com os clientes realmente cadastrados.
