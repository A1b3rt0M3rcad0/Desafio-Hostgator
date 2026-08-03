# Arquitetura analítica

O fluxo analítico segue a separação abaixo:

```text
Controller -> Use case -> Repository contract -> SQLAlchemy repository
```

## Responsabilidades

- Os repositórios executam filtros, agregações SQL, window functions e consultas em lote.
- Os repositórios retornam DTOs tipados de consulta e não montam respostas HTTP.
- Os use cases coordenam múltiplos repositórios, calculam taxas, comparações, participações e resumos.
- Os controllers apenas adaptam entrada e saída HTTP.

## Dashboard

`GetDashboardOverview` coordena:

- `TicketRepository` para snapshots analíticos, série temporal, clientes recorrentes e responsáveis;
- `CustomerRepository` para opções de clientes;
- `TagRepository` para opções de tags.

Todos compartilham a mesma `UnitOfWork` e a mesma `AsyncSession`.

## Prevenção de N+1

Métricas por cliente e exportações utilizam consultas em lote com os identificadores da página atual. Nenhuma consulta é executada dentro de loops de clientes ou tickets.
