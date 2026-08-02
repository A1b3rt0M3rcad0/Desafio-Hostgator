# Desafio HostGator

Aplicação para persistência, processamento, visualização analítica e exportação de dados de atendimento.

## Inicialização local

O repositório já inclui a fonte estática em `data/tickets.json`. Copie o arquivo de exemplo para `.env` e suba o stack:

```bash
cp .env.example .env
docker compose up --build -d
```

O fixture contém 10.000 tickets determinísticos de 500 clientes fictícios. Todas as datas do arquivo padrão pertencem a 2026 e estão limitadas à referência de 1º de agosto de 2026. Para regenerá-lo:

```bash
python data/generate_tickets_mock.py
```

Outro ano pode ser selecionado explicitamente:

```bash
python data/generate_tickets_mock.py --year 2025
```

Serviços locais padrão:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- Documentação da API: `http://localhost:8000/docs`
- MySQL: `localhost:3306`

A inicialização segue `db -> migrations -> api/web` e `db -> migrations -> worker`. O healthcheck do MySQL usa TCP autenticado e o container de migrations confirma uma conexão SQL real, com retentativas limitadas, antes de executar o Alembic. O worker não depende da API e não expõe porta.

## Configuração de ambiente

Somente `.env.example` é usado como modelo de configuração. O `.env` é local, ignorado pelo Git e usado pelo Docker Compose para interpolar as configurações dos serviços.

O navegador acessa a API pelo proxy do Nginx:

```text
Navegador -> http://localhost:5173/api/* -> Nginx -> http://api:8000/*
```

Ao alterar a URL pública da web, atualize `CORS_ALLOWED_ORIGINS` e `TRUSTED_ORIGINS`.

## Arquitetura

A aplicação preserva a separação:

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

Os repositórios CRUD permanecem independentes. Dashboard, métricas e exportações utilizam contratos de leitura próprios. Controllers não executam SQL e casos de uso não dependem de FastAPI ou SQLAlchemy.

Não existe upload manual de JSON nem rota produtiva de importação. A ingestão automática é executada por um worker de infraestrutura isolado.

## Worker de ingestão automática

O serviço `worker` cria uma engine SQLAlchemy própria, singleton durante a vida do processo. Ele não utiliza composers, controllers, casos de uso ou chamadas HTTP internas. Cada ciclo cria uma nova Unit of Work e repositories concretos ligados à sessão daquele lote.

Fluxo:

```text
worker container
  -> engine própria
  -> Unit of Work por lote
  -> repositories de infraestrutura
  -> MySQL
```

Configuração padrão:

```env
WORKER_BATCH_SIZE=25
WORKER_INTERVAL_SECONDS=30
WORKER_CONTROL_POLL_SECONDS=2
WORKER_SOURCE_PATH=/data/tickets.json
```

Enquanto a ingestão estiver ligada, o worker processa exatamente um lote de até 25 registros e aguarda 30 segundos antes do próximo lote. O cursor é persistido na mesma transação dos tickets, tags, avaliações e pendências processadas.

O JSON é lido incrementalmente. O worker aceita tanto uma lista no nível raiz quanto um objeto com a propriedade `tickets`:

```json
[
  { "ticket_id": 1 }
]
```

ou:

```json
{
  "tickets": [
    { "ticket_id": 1 }
  ]
}
```

A associação utiliza `requester_email` e `requester_id` para localizar clientes previamente cadastrados. O worker não cria clientes automaticamente. Registros sem cliente correspondente ou com conflito de identidade são persistidos em `ingestion_pending_tickets`, juntamente com o payload original e a versão da fonte.

Em cada ciclo, o worker procura primeiro até 25 pendências cujo cliente agora exista. Quando encontra, processa essas pendências sem avançar o cursor do JSON e remove as linhas recuperadas na mesma transação. Quando não há pendências recuperáveis, processa o próximo lote da fonte normalmente. Assim, o cursor pode continuar avançando sem perder tickets que dependem de um cadastro posterior de cliente.

A migration que introduz a fila zera o cursor uma única vez para recuperar registros que possam ter sido consumidos antes desse mecanismo existir. Tickets já persistidos não são duplicados, pois a sincronização é idempotente por `external_ticket_id` e `source_updated_at`.

O dashboard exibe apenas um botão para ligar ou desligar a ingestão automática. As configurações de lote e intervalo permanecem no ambiente.

Endpoints de controle:

```http
GET   /ingestion/control
PATCH /ingestion/control
```

Exemplo de alteração:

```json
{
  "enabled": true
}
```

## Dashboard e métricas

Endpoints:

```http
GET /dashboard
GET /metrics/customers
```

Filtros compartilhados:

- período;
- clientes e e-mails;
- status;
- prioridades;
- tags;
- responsáveis;
- satisfação;
- existência de primeira resposta.

Métricas:

| Métrica | Definição |
| --- | --- |
| Volume de tickets | Quantidade de tickets dentro dos filtros. |
| Frequência média | Média dos intervalos entre tickets consecutivos do mesmo cliente. |
| Assuntos principais | Tags com maior quantidade de tickets distintos. |
| Taxa de resolução | Tickets `SOLVED` ou `CLOSED` divididos pelo total. |
| Índice de satisfação | `GOOD / (GOOD + BAD)`. `OFFERED` e `UNOFFERED` não entram no denominador. |
| Tempo médio até a primeira resposta | Média de `first_response_at - source_created_at` para respostas válidas. |

As faixas de tempo até a primeira resposta são indicadores operacionais e não representam conformidade de SLA.

## Exportação de dados

A exportação é estritamente de leitura. Nenhum endpoint de exportação cria, atualiza ou remove registros.

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

A exportação detalhada permite escolher campos e aplicar os mesmos filtros analíticos usados pelo dashboard. A pré-visualização é limitada, mas o arquivo final percorre todo o conjunto filtrado em lotes.

A exportação de métricas reutiliza os mesmos cálculos do dashboard e oferece os escopos:

- visão geral;
- por cliente.

Os arquivos aplicam proteção contra formula injection. Campos compostos, como tags e satisfação, são serializados com segurança em CSV e XLSX.

## Frontend

Telas implementadas:

- login e registro;
- páginas 401, 403, 404 e 500;
- dashboard analítico;
- tickets e clientes somente leitura;
- métricas por cliente;
- exportação de dados detalhados;
- exportação de métricas.

A tela `/exports` permite:

- escolher CSV ou XLSX;
- selecionar campos ou métricas;
- selecionar o escopo das métricas;
- filtrar por período, status, prioridade, tags, clientes, responsáveis, satisfação e primeira resposta;
- pré-visualizar até 50 registros detalhados;
- baixar o conjunto completo filtrado.

Não existe rota `/imports`, botão de importação ou leitura de arquivos JSON no frontend.

### Desenvolvimento sem Docker

```bash
cp .env.example .env
cd web
npm install
npm run dev
```

## Testes locais

```bash
uv sync --dev
PYTHONPATH=. uv run pytest -q
cd web
npm install
npm run build
```

Os dados dos testes são inseridos por fixtures internas, sem expor qualquer fluxo manual de ingestão na aplicação.

## Estado e logs

```bash
docker compose ps -a
docker compose logs web api worker migrations db
```
