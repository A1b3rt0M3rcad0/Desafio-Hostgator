# Desafio HostGator

Desenvolvido por **Alberto Mercado**.

## Executar o sistema localmente

Requisitos: Docker e Docker Compose.

Linux ou macOS:

```bash
cp .env.example .env
docker compose up --build -d
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Acessos locais:

- Aplicação: `http://localhost:5173`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Para encerrar o sistema:

```bash
docker compose down
```

## Executar os testes localmente

Testes unitários:

```bash
docker compose -f docker-compose.tests.yaml run --rm --build unit_tests
```

Testes de integração:

```bash
docker compose -f docker-compose.tests.yaml up --build --exit-code-from integration_tests integration_tests
docker compose -f docker-compose.tests.yaml down --volumes --remove-orphans
```
