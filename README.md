# Desafio HostGator

Aplicação web para gerenciar clientes monitorados, cruzar seus e-mails com uma fonte JSON estática de HelpDesk, persistir tickets no MySQL e calcular métricas comportamentais de atendimento.

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
  -> consulta o cursor persistido
  -> seleciona o próximo lote em memória
  -> abre uma Unit of Work curta
  -> chama IngestTicketBatch
  -> o caso de uso cruza somente e-mails de clientes monitorados
  -> repositories consultam e persistem clientes, tickets, tags e avaliações em lote
  -> atualiza o cursor na mesma transação
```

O cursor percorre circularmente a fonte estática. Isso permite que um cliente cadastrado depois da primeira leitura seja reconhecido em uma rodada posterior, sem criar clientes automaticamente a partir do JSON.

Clientes disponíveis no arquivo de demonstração:

- `ana.fernandes@techcorp.com.br` (`requester_id` 44521)
- `bruno.silva@lojaviva.com.br` (`requester_id` 44522)
- `camila.rocha@nexustech.com.br` (`requester_id` 44523)

O ID externo é opcional no cadastro. Quando ausente, a primeira correspondência válida por e-mail vincula o `requester_id` da fonte ao cliente.

O gerador `data/generate_tickets_mock.py` permanece disponível apenas como utilitário de desenvolvimento para substituir manualmente o arquivo estático quando necessário. Ele não é chamado pelo worker.

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

A ingestão utiliza a mesma separação de responsabilidades:

```text
worker container
  -> leitura e seleção técnica da fonte JSON
  -> Bootstrap composer
  -> IngestTicketBatch
  -> repository contracts
  -> repositories SQLAlchemy
  -> MySQL
```

O worker é responsável somente por configuração, temporização, leitura da fonte, sinais de encerramento, abertura da Unit of Work e acionamento do caso de uso. Regras de cruzamento, identidade, idempotência, classificação e avanço do cursor pertencem ao `IngestTicketBatch`.

## Ingestão automática

Configuração padrão:

```env
WORKER_SOURCE_PATH=/data/tickets.json
WORKER_BATCH_SIZE=30
WORKER_INTERVAL_SECONDS=30
WORKER_CONTROL_POLL_SECONDS=2
```

Enquanto a ingestão estiver ligada:

1. o worker consulta o estado e o cursor persistidos;
2. seleciona o próximo lote do JSON já validado;
3. abre uma Unit of Work curta;
4. o `IngestTicketBatch` bloqueia e valida o cursor;
5. busca em lote somente os clientes monitorados pelos e-mails recebidos;
6. ignora solicitantes não cadastrados e conflitos de identidade;
7. busca os tickets existentes por IDs externos em uma consulta;
8. classifica tickets novos, atualizados e inalterados em memória;
9. persiste tickets, tags, relações e avaliações em lote;
10. atualiza o cursor na mesma transação;
11. aguarda o intervalo configurado e inicia outra rodada.

A relação central é:

```text
Customer 1 -------- N Ticket
Ticket   N -------- N Tag
Ticket   1 -------- 0..1 SatisfactionRating
```

Os campos de atendente e primeira resposta ficam no próprio ticket.

`ingestion_control.cursor_position` representa a posição da próxima leitura dentro da fonte estática. Se a transação falhar, o cursor não avança e o mesmo lote será tentado novamente.

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

O CRUD define a base monitorada. A ingestão nunca cria clientes a partir do JSON.

- O e-mail normalizado é a chave de cruzamento com a fonte.
- O identificador externo é opcional e funciona como vínculo auxiliar.
- A primeira correspondência pode preencher o identificador externo ausente.
- Uma divergência posterior de identificador externo é tratada como conflito.
- `DELETE` desativa o monitoramento e preserva o histórico de tickets.
- Um novo cadastro do mesmo e-mail reativa o cliente existente.

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

Não existe upload manual de JSON pelo frontend. A fonte é versionada e consumida pelo worker.

## Operação e diagnóstico

```bash
docker compose ps -a
docker compose logs migrations worker api web
docker compose logs -f worker
```

Exemplo de log de uma rodada:

```text
ticket_ingestion.completed received=9 matched_customers=1 ignored_unmonitored=6 identity_conflicts=0 created=3 updated=0 unchanged=0 next_cursor=0
```

Para testar a ingestão, cadastre ao menos um dos e-mails disponíveis em `data/tickets.json`, ligue a ingestão no dashboard e acompanhe os logs do worker.
