# Desafio HostGator

## Inicialização local com Docker

O projeto usa um único arquivo de ambiente na raiz: `.env`.

```bash
cp .env.example .env
docker compose up --build -d
```

O `.env.example` contém credenciais e segredos mock válidos apenas para desenvolvimento local. Troque todos os segredos antes de usar fora de testes.

Para fazer o comando aguardar os healthchecks e retornar erro caso o stack não fique saudável:

```bash
docker compose up --build -d --wait --wait-timeout 120
```

Estado e logs podem ser consultados nativamente pelo Docker:

```bash
docker compose ps -a
docker compose logs api migrations db
```
