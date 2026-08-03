# Desafio HostGator

Aplicação web para gerenciar os clientes monitorados, cruzar seus e-mails com uma fonte JSON estática de HelpDesk, persistir tickets no MySQL e calcular métricas comportamentais de atendimento.

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
  -> api + worker
  -> web
```

Somente `migrations` é um serviço one-shot. O estado `Exited (0)` é esperado depois da conclusão das migrations.

## Fonte estática de tickets

O worker consome `data/tickets.json`, versionado no repositório. O arquivo representa o retorno estático de uma plataforma de HelpDesk e não é regenerado durante a execução.

O fluxo é:

```text
worker
  -> carrega e valida o JSON uma vez
  -> seleciona um lote pelo cursor persistido
  -> abre uma Unit of Work curta
  -> chama IngestTicketBatch
  -> o caso de uso cruza somente e-mails de clientes monitorados
  -> repositories consultam e persistem clientes, tickets, tags e avaliações em lote
  -> o cursor percorre circularmente a fonte estática
```

O percurso circular permite que um cliente cadastrado depois da primeira leitura seja reconhecido em uma rodada posterior, sem criar clientes automaticamente a partir da fonte.

Clientes disponíveis no arquivo de demonstração:

- `ana.fernandes@techcorp.com.br` (`requester_id` 44521)
- `bruno.silva@lojaviva.com.br` (`requester_id` 44522)
- `camila.rocha@nexustech.com.br` (`requester_id` 44523)

O ID externo é opcional no cadastro. Quando ausente, a primeira correspondência válida por e-mail vincula o `requester_id` da fonte ao cliente.

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
  -> gerador Python
  -> snapshot JSON da rodada
  -> engine SQLAlchemy própria e singleton por processo
  -> Unit of Work por rodada
  -> repositories concretos
  -> MySQL
```

O worker não utiliza controllers, rotas HTTP, composers ou casos de uso da API.

## Ingestão automática

Configuração padrão:

```env
WORKER_SOURCE_PATH=/data/tickets.json
WORKER_BATCH_SIZE=30
WORKER_INTERVAL_SECONDS=30
WORKER_CONTROL_POLL_SECONDS=2
```

Enquanto a ingestão estiver ligada, o worker:

1. consulta o estado persistido da ingestão;
2. chama o gerador para produzir exatamente 30 registros;
3. sobrescreve `tickets.json` de forma atômica;
4. lê e valida integralmente o JSON produzido;
5. busca em lote somente os clientes monitorados pelos e-mails do lote;
6. ignora solicitantes não cadastrados e conflitos de identidade;
7. cria ou atualiza tickets de forma idempotente e em lote;
8. sincroniza tags e avaliações em lote;
9. atualiza o cursor na mesma transação;
10. aguarda 30 segundos e inicia outra rodada.

A relação central é:

```text
Customer 1 -------- N Ticket
Ticket   N -------- N Tag
Ticket   1 -------- 0..1 SatisfactionRating
```

Os campos de atendente e primeira resposta ficam no próprio ticket.

`ingestion_control.cursor_position` representa a quantidade total de registros gerados e persistidos. O próximo ID externo é calculado a partir desse valor. Se a transação falhar, o cursor não avança; na tentativa seguinte, o mesmo lote determinístico é produzido novamente.

O JSON é sobrescrito mesmo que o banco mantenha todos os tickets anteriores. Assim, o arquivo representa somente o retorno atual da origem, enquanto o MySQL mantém o histórico acumulado.

O dashboard expõe o controle:

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

A ingestão nunca cria clientes a partir do JSON. O CRUD define a base monitorada; o e-mail normalizado realiza o cruzamento. A exclusão desativa o monitoramento e preserva o histórico de tickets.

## Dados persistidos

Tabelas principais:

- `customers`;
- `tickets`;
- `tags`;
- `ticket_tags`;
- `satisfaction_ratings`;
- `ingestion_control`;
- `users` e `auth_sessions` para autenticação.

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

Não existe upload manual de JSON pelo frontend. O snapshot é gerado e consumido pelo worker em cada rodada.

## Operação e diagnóstico

```bash
docker compose ps -a
docker compose logs migrations worker api web
docker compose logs -f worker
```

Primeira rodada esperada após ligar a ingestão:

```text
ticket_ingestion.completed cycle=1 generated=30 customers_created=30 tickets_created=30 next_ticket_id=100031
```

Rodada seguinte:

```text
ticket_ingestion.completed cycle=2 generated=30 customers_created=30 tickets_created=30 next_ticket_id=100061
```

Depois que os 500 clientes da base já tiverem aparecido, novas rodadas reutilizam esses clientes e continuam adicionando 30 tickets a cada intervalo.
