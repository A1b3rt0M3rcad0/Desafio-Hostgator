# Fonte de tickets

`data/tickets.json` é o fixture estático consumido diretamente pelo worker de infraestrutura.
Ele contém 10.000 tickets determinísticos para 500 clientes fictícios.

O fixture versionado usa como referência `2026-08-01T05:30:00Z`. Todos os campos de data — criação, atualização, primeira resposta, oferta e avaliação — ficam entre `2026-01-01T00:00:00Z` e essa referência. Não existem registros de 2024 ou 2025 no arquivo padrão.

O diretório `data/` concentra tanto o gerador quanto o arquivo consumido pelo worker:

```text
data/
├── generate_tickets_mock.py
├── tickets.json
└── README.md
```

Para regenerar o fixture padrão de 2026, execute a partir da raiz do repositório:

```bash
python data/generate_tickets_mock.py
```

Também é possível selecionar outro ano. O mês, dia e horário de referência permanecem em 1º de agosto às 05:30 UTC:

```bash
python data/generate_tickets_mock.py --year 2025
```

Uma âncora exata pode ser informada no lugar de `--year`:

```bash
python data/generate_tickets_mock.py --anchor 2026-07-15T12:00:00Z
```

O arquivo é validado antes da substituição e gravado de forma atômica. O worker monta `data/` como `/data` em modo somente leitura e processa um lote de até 25 registros a cada 30 segundos por padrão.
