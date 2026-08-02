# Desafio HostGator

Aplicação web para gerenciar clientes monitorados, consumir um histórico estático de tickets de HelpDesk, persistir as relações no MySQL e calcular métricas comportamentais de atendimento.

## Inicialização local

```bash
cp .env.example .env
docker compose up --build -d
```

No PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Serviços locais:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- MySQL: `localhost:3306`

A inicialização segue:

```text
db
  -> migrations
  -> mock-data gera data/tickets.json
  -> seed cadastra os clientes canônicos
  -> api + worker
  -> web
```

`mock-data`, `migrations` e `seed` são serviços one-shot. O estado `Exited (0)` é esperado depois da conclusão.

## Fonte estática de tickets

O desafio exige o consumo de um JSON estático que simula o retorno de uma plataforma de HelpDesk. O projeto mantém essa separação:

```text
data/generate_tickets_mock.py
    -> produz data/tickets.json
    -> encerra

worker
    -> consome o JSON já produzido
    -> não gera conteúdo
```

O fixture local padrão contém:

- 30 clientes canônicos em `data/customers_seed.json`;
- 10 tickets por cliente;
- 300 tickets no total;
- dados exclusivamente de 2026;
- múltiplos status, prioridades, tags, atendentes e avaliações.

O arquivo `data/tickets.json` é gerado na inicialização e ignorado pelo Git. A geração manual é:

```bash
python data/generate_tickets_mock.py --pretty
```

As identidades presentes nos tickets são derivadas do mesmo catálogo usado no seed local. Portanto, o e-mail e o identificador externo do solicitante correspondem aos registros da tabela `customers`.

Em ambientes que já possuam uma base real de clientes, desative o seed:

```env
DEMO_SEED_ENABLED=false
```

A fonte estática usada nesse ambiente deverá conter os mesmos e-mails dos clientes monitorados.

## Arquitetura

O fluxo HTTP mantém a arquitetura da aplicação:

```text
Domain
  -> Application contracts
  -> DTOs
  -> Use cases
  -> Infrastructure repositories
  -> HTTP controllers
  -> Bootstrap composers
  -> FastAPI routes
```

O worker é um processo de infraestrutura isolado:

```text
worker container
  -> engine SQLAlchemy própria e singleton por processo
  -> Unit of Work por lote
  -> repositories concretos
  -> MySQL
```

O worker não importa casos de uso, controllers, composers da API ou rotas HTTP.

## Ingestão automática

Configuração padrão:

```env
WORKER_BATCH_SIZE=30
WORKER_INTERVAL_SECONDS=30
WORKER_CONTROL_POLL_SECONDS=2
WORKER_SOURCE_PATH=/data/tickets.json
```

Enquanto a ingestão estiver ligada, o worker:

1. lê até 30 registros do JSON estático;
2. normaliza os dados recebidos;
3. localiza os clientes pelo e-mail;
4. valida o `requester_id` externo;
5. cria ou atualiza tickets de forma idempotente;
6. sincroniza tags e avaliações;
7. avança o cursor na mesma transação;
8. aguarda 30 segundos.

A relação central é:

```text
Customer 1 -------- N Ticket
Ticket   N -------- N Tag
Ticket   1 -------- 0..1 SatisfactionRating
```

O e-mail é a referência principal do cruzamento. O identificador externo do solicitante funciona como validação adicional. O worker não cria clientes.

Se um lote contiver cliente ausente, identidade conflitante ou registro inválido, a transação é revertida e o cursor não avança. O erro fica registrado em `ingestion_control.last_error`, evitando descarte silencioso.

O fim do arquivo coloca o worker em `CAUGHT_UP`. Se o JSON for regenerado, sua versão muda, o cursor volta para zero e os tickets são reavaliados sem duplicidade por causa de `external_ticket_id` e `source_updated_at`.

O dashboard expõe somente o controle funcional:

```text
Ingestão automática [ligar/desligar]
```

Endpoints:

```http
GET   /ingestion/control
PATCH /ingestion/control
```

## Gestão de clientes

O backend e o frontend oferecem CRUD completo:

```http
POST   /customers
GET    /customers
GET    /customers/{customer_id}
PATCH  /customers/{customer_id}
DELETE /customers/{customer_id}
```

A tela de clientes permite cadastrar, listar, pesquisar, editar, visualizar e excluir registros. O e-mail é único no banco e é utilizado para associar os tickets da fonte externa.

## Dados persistidos

Tabelas principais:

- `customers`;
- `tickets`;
- `tags`;
- `ticket_tags`;
- `satisfaction_ratings`;
- `ingestion_control`;
- `users` e `auth_sessions` para autenticação.

Campos de atendente e primeira resposta ficam no próprio ticket, pois não possuem ciclo de vida independente no escopo do desafio.

## Dashboard e métricas

Endpoints:

```http
GET /dashboard
GET /metrics/customers
```

Indicadores:

| Métrica | Definição |
| --- | --- |
| Volume | Quantidade de tickets dentro dos filtros. |
| Frequência média | Média dos intervalos entre tickets consecutivos do cliente. |
| Assuntos principais | Tags com maior quantidade de tickets distintos. |
| Taxa de resolução | Tickets `SOLVED` ou `CLOSED` divididos pelo total. |
| Satisfação | `GOOD / (GOOD + BAD)`. |
| Primeira resposta | Média de `first_response_at - source_created_at`. |

Filtros incluem período, cliente, status, prioridade, tags, atendente, satisfação e existência de primeira resposta.

## Exportações

Endpoints:

```http
GET  /exports/catalog
POST /exports/data/preview
POST /exports/data/download
POST /exports/metrics/download
```

Formatos suportados:

- CSV;
- XLSX.

## Autenticação

O sistema utiliza:

- access JWT curto em cookie `HttpOnly`;
- refresh token opaco com rotação e hash HMAC-SHA256;
- proteção CSRF para operações mutáveis;
- validação de origem e cookies configuráveis.

## Frontend

Telas implementadas:

- login e registro;
- dashboard analítico;
- tickets e detalhes;
- CRUD completo de clientes;
- métricas por cliente;
- exportação de dados e métricas;
- páginas de erro.

Não existe upload manual de JSON pelo frontend. A fonte é preparada pelo serviço `mock-data` e consumida exclusivamente pelo worker.

## Operação e diagnóstico

```bash
docker compose ps -a
docker compose logs migrations mock-data seed worker api web
docker compose logs -f worker
```

Primeiro lote esperado após ligar a ingestão:

```text
ticket_ingestion.batch.completed cursor=0 next_cursor=30 received=30 created=30
```

A carga completa de 300 registros termina em aproximadamente cinco minutos.
