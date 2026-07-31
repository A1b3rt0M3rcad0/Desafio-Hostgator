# Desafio HostGator

Aplicação para coleta, persistência, processamento e visualização analítica de dados de atendimento.

## Inicialização local

Existe um único arquivo de configuração para todo o projeto. Copie o exemplo para `.env` e suba o stack:

```bash
cp .env.example .env
docker compose up --build
```

Para iniciar em segundo plano e aguardar todos os healthchecks:

```bash
cp .env.example .env
docker compose up --build -d --wait --wait-timeout 120
```

Serviços locais padrão:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- Documentação da API: `http://localhost:8000/docs`
- MySQL: `localhost:3306`

A inicialização segue `db -> migrations -> api -> web`. O container web só inicia após o healthcheck da API ficar saudável.

## Configuração de ambiente

Somente `.env.example` é versionado. O arquivo `.env` é local, ignorado pelo Git e utilizado pelo Docker Compose para interpolar as configurações de todos os serviços.

O `.env.example` está dividido por seções:

| Seção | Consumidor | Responsabilidade |
| --- | --- | --- |
| Docker Compose | Compose | Portas publicadas no host. |
| Database | `db` | Inicialização do MySQL. |
| Migrations | `migrations` | URL síncrona usada pelo Alembic. |
| API - Database | `api` | URL assíncrona usada pela aplicação. |
| API - JWT/Session | `api` | Tokens de acesso e renovação de sessão. |
| API - CSRF/Hash | `api` | Proteção CSRF e custo do bcrypt. |
| API - Cookies | `api` | Segurança e nomes dos cookies. |
| API - Browser permissions | `api` | CORS e origens confiáveis. |
| Web runtime | `web` | Configuração pública do frontend e do Nginx. |
| Web development | Vite | Porta e upstream usados por `npm run dev`. |

Embora todas as variáveis estejam no mesmo `.env`, o `docker-compose.yaml` repassa a cada container somente as variáveis necessárias. Segredos da API não são injetados no container web.

Os valores fornecidos são mocks para desenvolvimento local. Substitua senhas e segredos antes de qualquer implantação real.

## Comunicação entre web e API

No Docker, o navegador usa:

```env
WEB_API_URL=/api
```

O Nginx recebe `/api/*` e encaminha internamente para:

```env
WEB_API_UPSTREAM_URL=http://api:8000
```

Fluxo:

```text
Navegador -> http://localhost:5173/api/* -> Nginx -> http://api:8000/*
```

A API permite por padrão os acessos originados de:

```env
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Ao alterar a URL pública da web, atualize também essas duas variáveis.

## Arquitetura

A aplicação preserva a separação:

```text
Domain -> Application contracts/DTOs/use cases -> Infrastructure -> Presentation -> Bootstrap composers
```

Os repositórios CRUD existentes permanecem independentes. Dashboard, métricas, importação e relatórios utilizam contratos próprios de leitura e sincronização, evitando adicionar consultas analíticas ao `TicketRepository` genérico.

O dashboard utiliza um read model especializado. Os relatórios e a listagem de métricas por cliente continuam utilizando o repositório analítico base, evitando que dimensões e comparações específicas da tela contaminem os demais casos de uso.

## Importação do mock

A tela de importação valida o JSON no navegador e, após confirmação, envia os tickets para:

```http
POST /imports/tickets/sync
```

O endpoint aceita uma lista direta ou objetos com `tickets` ou `data`. A sincronização:

- cria ou atualiza clientes;
- cria ou atualiza tickets pelo `ticket_id` externo;
- usa `updated_at` da origem para evitar sobrescrever dados mais novos;
- sincroniza tags e avaliações;
- remove duplicidades do mesmo arquivo mantendo a versão mais recente;
- é idempotente para reprocessamentos do mesmo dataset.

## Dashboard e métricas

O dashboard consulta o banco completo por meio de:

```http
GET /dashboard
GET /metrics/customers
```

Filtros suportados incluem período, clientes, e-mails, status, prioridades, tags, atendentes, avaliações e existência de primeira resposta.

O `GET /dashboard` fornece, no mesmo escopo de filtros:

- métricas atuais e comparação com o período anterior de mesma duração;
- resumo operacional determinístico;
- série temporal diária com tickets abertos, resolvidos, resolução, satisfação e primeira resposta;
- distribuição de status;
- desempenho por prioridade;
- distribuição do tempo até a primeira resposta;
- assuntos principais com volume, participação, resolução e resposta média;
- recorrência e concentração por cliente;
- dimensões completas para os seletores de tags, clientes e responsáveis.

A série temporal pode ser limitada para exibição sem alterar os denominadores das participações. Percentuais de prioridade, assunto e faixa de resposta sempre usam o volume completo resultante dos filtros.

Definições utilizadas:

| Métrica | Definição |
| --- | --- |
| Volume de tickets | Quantidade de tickets dentro dos filtros. |
| Frequência média | Média dos intervalos entre tickets consecutivos do mesmo cliente. |
| Assuntos principais | Tags com maior quantidade de tickets distintos. |
| Taxa de resolução | Tickets `SOLVED` ou `CLOSED` divididos pelo total. |
| Índice de satisfação | `GOOD / (GOOD + BAD)`. `OFFERED` e `UNOFFERED` não entram no denominador. |
| Tempo médio até a primeira resposta | Média de `first_response_at - source_created_at` para respostas válidas. |

As faixas de tempo até a primeira resposta são indicadores operacionais. Elas não representam conformidade de SLA, pois não existe meta formal configurada por prioridade.

Quando não existe denominador válido, taxas e médias retornam `null`, evitando representar ausência de dados como zero.

## Relatórios

Endpoints:

```http
GET  /reports/catalog
POST /reports/raw/preview
POST /reports/raw/export
POST /reports/metrics/export
```

Formatos suportados:

- CSV;
- XLSX.

O relatório RAW permite selecionar campos, filtros e pré-visualizar os resultados. O preset `mock_complete` reconstrói o contrato lógico do mock a partir das tabelas normalizadas. Datas são normalizadas em UTC, tags são ordenadas e campos compostos são serializados como JSON dentro de CSV/XLSX.

A reconstrução é semanticamente equivalente ao mock, mas não pretende reproduzir byte a byte indentação, ordem original do arquivo ou espaçamento.

As exportações aplicam proteção contra formula injection em planilhas e não incluem usuários, credenciais ou sessões de autenticação.

## Frontend

O frontend está em `web/` e utiliza React, JavaScript, HTML e CSS no código da aplicação. Vite é usado somente no desenvolvimento e no build; Nginx serve os arquivos estáticos e atua como reverse proxy.

Telas implementadas:

- login e registro;
- páginas 401, 403, 404 e 500;
- dashboard analítico com períodos rápidos e intervalo personalizado;
- filtros pesquisáveis por status, prioridade, tags, cliente e responsável;
- escopo ativo persistido na URL e representado por chips removíveis;
- resumo operacional e quatro indicadores principais comparados ao período anterior;
- gráfico temporal interativo com inspeção de cada período;
- composição da fila, pressão por prioridade e distribuição da primeira resposta;
- recorrência dos clientes e análise de assuntos principais;
- visualização somente leitura de tickets e clientes;
- detalhes de tickets e clientes;
- importação persistente do JSON RAW;
- métricas paginadas por cliente;
- relatórios RAW e de métricas em CSV e XLSX.

Os gráficos principais utilizam SVG responsivo no próprio frontend. Estados sem dados são explícitos e nunca fabricam totais para manter um gráfico visível.

### Desenvolvimento sem Docker

O Vite lê `WEB_DEV_PORT` e `WEB_DEV_API_UPSTREAM_URL` do `.env` localizado na raiz:

```bash
cp .env.example .env
cd web
npm install
npm run dev
```

## Testes

```bash
uv sync --dev
PYTHONPATH=. uv run pytest -q
cd web
npm install
npm run build
```

A pipeline `Analytics CI` executa compilação Python, suíte pytest com MySQL 8 e build do frontend. Os cenários de integração cobrem importação idempotente, fórmulas, reconstrução RAW, comparação temporal, dimensões de filtro e independência entre limite visual da série e denominadores analíticos.

A validação automatizada atual executa 15 testes e o build de produção do frontend. A aprovação visual final deve ser feita com a aplicação executando no navegador e dados representativos importados.

## Estado e logs

```bash
docker compose ps -a
docker compose logs web api migrations db
```
