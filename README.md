# Desafio HostGator

Aplicação para coleta, processamento e visualização analítica de dados de atendimento.

## Inicialização local com Docker

O backend usa o arquivo `.env` da raiz e o frontend usa o arquivo isolado `.env.web`.

```bash
cp .env.example .env
docker compose up --build -d
```

Para aguardar os healthchecks e retornar erro caso algum serviço não fique saudável:

```bash
docker compose up --build -d --wait --wait-timeout 120
```

Serviços locais:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- MySQL: `localhost:3306`

A inicialização respeita a sequência de saúde `db -> migrations -> api -> web`. O serviço web só inicia depois que a API está saudável.

Estado e logs:

```bash
docker compose ps -a
docker compose logs web api migrations db
```

## Frontend

O frontend está integralmente em `web/` e utiliza somente React, JavaScript, HTML e CSS no código da aplicação. Vite é usado apenas para empacotamento e desenvolvimento; Nginx serve o build estático e encaminha `/api/*` para a API.

Telas implementadas:

- login e registro integrados ao fluxo de cookies e CSRF da API;
- páginas de erro 401, 403, 404 e 500;
- dashboard principal;
- visualização somente leitura de tickets e clientes;
- detalhes de tickets e clientes;
- importação e pré-visualização local de JSON RAW;
- métricas operacionais;
- relatórios com exportação CSV e impressão/PDF pelo navegador.

A importação RAW atual valida e processa o arquivo no navegador. Ela não cadastra fonte, não altera registros persistidos e não envia o conteúdo para a API.

### Desenvolvimento sem Docker

Com a API disponível em `http://localhost:8000`:

```bash
cd web
npm install
npm run dev
```

O servidor de desenvolvimento encaminha `/api` para a API local.

## Variáveis da web

O arquivo `.env.web` contém apenas configuração pública:

- `WEB_APP_NAME`
- `WEB_API_BASE_PATH`
- `WEB_REQUEST_TIMEOUT_MS`
- `WEB_REGISTRATION_ENABLED`
- `WEB_CSRF_COOKIE_NAME`
- `WEB_CSRF_HEADER_NAME`

Nenhum segredo deve ser colocado nesse arquivo, pois seus valores ficam disponíveis no navegador.
