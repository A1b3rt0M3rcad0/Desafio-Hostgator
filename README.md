# Desafio HostGator

Aplicação para coleta, processamento e visualização analítica de dados de atendimento.

## Inicialização local

Existe um único arquivo de configuração para todo o projeto. Copie o exemplo para `.env` e suba o stack:

```bash
cp .env.example .env
docker compose up --build
```

Para iniciar em segundo plano e aguardar todos os healthchecks:

```bash
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

## Frontend

O frontend está em `web/` e utiliza React, JavaScript, HTML e CSS no código da aplicação. Vite é usado somente no desenvolvimento e no build; Nginx serve os arquivos estáticos e atua como reverse proxy.

Telas implementadas:

- login e registro;
- páginas 401, 403, 404 e 500;
- dashboard principal;
- visualização somente leitura de tickets e clientes;
- detalhes de tickets e clientes;
- importação e pré-visualização local de JSON RAW;
- métricas operacionais;
- relatórios com exportação CSV e impressão/PDF pelo navegador.

A importação RAW atual valida e processa o arquivo no navegador. Ela não cadastra fontes, não altera registros persistidos e não envia o conteúdo para a API.

### Desenvolvimento sem Docker

O Vite lê `WEB_DEV_PORT` e `WEB_DEV_API_UPSTREAM_URL` do `.env` localizado na raiz:

```bash
cp .env.example .env
cd web
npm install
npm run dev
```

## Estado e logs

```bash
docker compose ps -a
docker compose logs web api migrations db
```
