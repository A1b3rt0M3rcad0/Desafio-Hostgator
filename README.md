# Desafio HostGator

Aplicação para coleta, processamento e visualização analítica de dados de atendimento.

## Inicialização local pronta

A branch contém configurações mock versionadas em `.env` e `.env.web`. Depois de clonar, não é necessário copiar nem preencher arquivos de ambiente:

```bash
docker compose up --build
```

Para iniciar em segundo plano e aguardar todos os healthchecks:

```bash
docker compose up --build -d --wait --wait-timeout 120
```

Serviços locais padrão:

- Web: `http://localhost:5173`
- API direta: `http://localhost:8000`
- Documentação da API: `http://localhost:8000/docs`
- MySQL: `localhost:3306`

A inicialização respeita `db -> migrations -> api -> web`. O container web só inicia quando o healthcheck da API estiver saudável.

Os valores versionados são mocks exclusivamente locais. Antes de qualquer implantação real, substitua senhas e segredos e habilite HTTPS/cookies seguros.

## Como web e API se comunicam

O navegador usa `WEB_API_URL=/api`. Essa URL é relativa à própria aplicação web. O Nginx recebe as chamadas em `/api/*` e as encaminha para `WEB_API_UPSTREAM_URL=http://api:8000`, onde `api` é o nome interno do serviço Docker.

Fluxo padrão:

```text
Navegador -> http://localhost:5173/api/* -> Nginx -> http://api:8000/*
```

Essa configuração mantém a aplicação na mesma origem no navegador. A API também autoriza explicitamente `http://localhost:5173` e `http://127.0.0.1:5173` por meio de `CORS_ALLOWED_ORIGINS` e `TRUSTED_ORIGINS`.

## Arquivo `.env`

O `.env` configura banco, API, autenticação e portas Docker.

| Variável | Finalidade |
| --- | --- |
| `MYSQL_HOST_PORT` | Porta do MySQL publicada no computador. |
| `API_HOST_PORT` | Porta pública da API. |
| `WEB_HOST_PORT` | Porta pública do frontend. |
| `MYSQL_ROOT_PASSWORD` | Senha root mock usada pelo container MySQL. |
| `MYSQL_DATABASE` | Banco criado automaticamente pelo MySQL. |
| `MYSQL_URL_CONNECTION_API` | Conexão assíncrona usada pela API. |
| `MYSQL_URL_CONNECTION_MIGRATIONS` | Conexão síncrona usada pelo Alembic. |
| `JWT_SECRET_KEY` | Assina access tokens JWT. |
| `JWT_ALGORITHM` | Algoritmo JWT aceito pela implementação. |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Identificam emissor e público dos tokens. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Validade do access token. |
| `REFRESH_TOKEN_PEPPER` | Segredo usado no hash dos refresh tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Validade máxima da sessão renovável. |
| `CSRF_SECRET_KEY` | Assina os tokens CSRF. |
| `CSRF_HEADER_NAME` | Header que transporta o token CSRF. |
| `BCRYPT_ROUNDS` | Custo do hash de senha. |
| `AUTH_COOKIE_*` | Segurança e nomes dos cookies de autenticação. |
| `CORS_ALLOWED_ORIGINS` | Origens autorizadas a chamar a API pelo navegador. |
| `TRUSTED_ORIGINS` | Origens autorizadas a executar requisições mutáveis protegidas por CSRF. |

## Arquivo `.env.web`

O `.env.web` contém somente valores públicos usados pelo frontend e pelo Nginx. Nunca coloque segredos nesse arquivo.

| Variável | Finalidade |
| --- | --- |
| `WEB_APP_NAME` | Nome exibido pela aplicação. |
| `WEB_APP_ENV` | Identificação do ambiente atual. |
| `WEB_PUBLIC_URL` | Endereço público da aplicação web. |
| `WEB_API_URL` | URL usada pelo navegador para chamar a API; por padrão `/api`. |
| `WEB_API_UPSTREAM_URL` | URL interna usada pelo Nginx dentro da rede Docker. |
| `WEB_DEV_PORT` | Porta do servidor Vite fora do Docker. |
| `WEB_DEV_API_UPSTREAM_URL` | API usada pelo proxy do Vite fora do Docker. |
| `WEB_SERVER_NAME` | Nome virtual aceito pelo Nginx. |
| `WEB_REQUEST_TIMEOUT_MS` | Timeout das chamadas HTTP do navegador. |
| `WEB_REGISTRATION_ENABLED` | Habilita ou desabilita a tela de registro. |
| `WEB_CSRF_COOKIE_NAME` | Cookie público onde o frontend lê o token CSRF. |
| `WEB_CSRF_HEADER_NAME` | Header enviado pela web; deve coincidir com `CSRF_HEADER_NAME`. |

## Frontend

O frontend está em `web/` e utiliza React, JavaScript, HTML e CSS no código da aplicação. Vite é usado para empacotamento/desenvolvimento e Nginx serve os arquivos estáticos e atua como reverse proxy.

Telas implementadas:

- login e registro integrados a cookies e CSRF;
- páginas 401, 403, 404 e 500;
- dashboard principal;
- visualização somente leitura de tickets e clientes;
- detalhes de tickets e clientes;
- importação e pré-visualização local de JSON RAW;
- métricas operacionais;
- relatórios com exportação CSV e impressão/PDF pelo navegador.

A importação RAW atual valida e processa o arquivo no navegador. Ela não cadastra fontes, não altera registros persistidos e não envia o conteúdo para a API.

### Desenvolvimento sem Docker

Com a API local disponível, o Vite lê `WEB_DEV_API_UPSTREAM_URL` do `.env.web`:

```bash
cd web
npm install
npm run dev
```

## Estado e logs

```bash
docker compose ps -a
docker compose logs web api migrations db
```
