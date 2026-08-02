#!/usr/bin/env python3
"""Generate the static HelpDesk JSON consumed by the ingestion worker.

The fixture is built from a canonical customer snapshot. The default command
creates 300 deterministic tickets (10 per customer), all dated in 2026, and
writes them to ``data/tickets.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

GENERATOR_VERSION: Final[int] = 3
DEFAULT_YEAR: Final[int] = 2026
DEFAULT_TICKETS_PER_CUSTOMER: Final[int] = 10
DEFAULT_START_ID: Final[int] = 100_001
DATA_DIR: Final[Path] = Path(__file__).resolve().parent
DEFAULT_CUSTOMERS_FILE: Final[Path] = DATA_DIR / "customers_seed.json"
DEFAULT_OUTPUT: Final[Path] = DATA_DIR / "tickets.json"

STATUSES: Final[tuple[str, ...]] = ("new", "open", "pending", "hold", "solved", "closed")
PRIORITIES: Final[tuple[str, ...]] = ("urgent", "high", "normal", "low")
RATINGS: Final[tuple[str, ...]] = ("unoffered", "offered", "good", "bad")

AGENTS: Final[dict[str, tuple[int, str]]] = {
    "n1": (9101, "Patrícia Gomes (Suporte N1)"),
    "infra": (9102, "Rafael Souza (N2 - Infraestrutura)"),
    "domains": (9103, "Marina Alves (Domínios e DNS)"),
    "email": (9104, "Lucas Mendes (E-mail)"),
    "hosting": (9105, "Fernanda Costa (Hospedagem)"),
    "billing": (9106, "Juliana Martins (Financeiro)"),
    "wordpress": (9107, "Bruno Carvalho (WordPress)"),
    "security": (9108, "Camila Rocha (Segurança e SSL)"),
    "migration": (9109, "Diego Nunes (Migrações)"),
    "performance": (9110, "André Lima (Servidores e Performance)"),
}

SCENARIOS: Final[tuple[tuple[str, str, tuple[str, ...]], ...]] = (
    ("Falha de login", "n1", ("login", "autenticacao")),
    ("Redefinição de senha", "n1", ("senha", "token-expirado")),
    ("Conta bloqueada", "security", ("conta-bloqueada", "tentativas")),
    ("Propagação de DNS", "domains", ("dns", "propagacao")),
    ("Certificado SSL pendente", "security", ("ssl", "certificado")),
    ("Conflito de plugin WordPress", "wordpress", ("wordpress", "plugin")),
    ("Migração de site", "migration", ("migracao", "arquivos")),
    ("Erro HTTP 503", "hosting", ("erro-503", "indisponibilidade")),
    ("Uso elevado de CPU", "performance", ("cpu", "memoria")),
    ("Caixa postal sem espaço", "email", ("email", "quota")),
    ("Configuração SPF e DKIM", "email", ("spf", "dkim")),
    ("Falha de autenticação SMTP", "email", ("smtp", "credenciais")),
    ("Cobrança duplicada", "billing", ("cobranca", "duplicidade")),
    ("Segunda via de fatura", "billing", ("fatura", "pagamento")),
    ("Cancelamento e estorno", "billing", ("cancelamento", "estorno")),
    ("Restauração de backup", "infra", ("backup", "restauracao")),
    ("Falha de conexão FTP", "hosting", ("ftp", "firewall")),
    ("Acesso ao cPanel negado", "n1", ("cpanel", "permissao")),
    ("Tarefa cron não executada", "infra", ("cron", "agendamento")),
    ("Loop de redirecionamento", "hosting", ("redirect", "htaccess")),
    ("Malware detectado", "security", ("malware", "quarentena")),
    ("Mensagem de phishing", "security", ("phishing", "abuso")),
    ("Subdomínio sem resolução", "domains", ("subdominio", "zona-dns")),
    ("Timeout de API", "performance", ("api", "timeout")),
    ("Acesso SSH rejeitado", "infra", ("ssh", "chave-publica")),
    ("Cache antigo no CDN", "performance", ("cdn", "cache")),
    ("Transferência de domínio", "domains", ("epp", "transferencia-dominio")),
    ("Migração de caixa IMAP", "migration", ("imap", "migracao-email")),
    ("Limite de conexões MySQL", "performance", ("mysql", "conexoes")),
    ("Erro 404 no WordPress", "wordpress", ("erro-404", "rewrite")),
    ("Atualização de PHP", "hosting", ("php", "versao-php")),
    ("Acesso indevido ao site", "security", ("incidente", "credencial-vazada")),
    ("Backup automático ausente", "infra", ("backup-automatico", "retencao")),
    ("Webhook sem entrega", "performance", ("webhook", "integracao")),
    ("Importação de banco falhou", "migration", ("importacao-banco", "sql")),
)

CHANNEL_TAGS: Final[tuple[str, ...]] = ("chat", "email", "formulario-web", "telefone")
ACCOUNT_TAGS: Final[tuple[str, ...]] = ("cliente-pj", "cliente-pme", "cloud", "vps", "compartilhado")


def parse_iso8601(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_anchor(year: int) -> datetime:
    if year < 2000 or year > 2100:
        raise ValueError("--year deve estar entre 2000 e 2100")
    return datetime(year, 8, 1, 5, 30, tzinfo=timezone.utc)


def deterministic_rng(seed: str, namespace: str, identifier: int) -> random.Random:
    message = f"{namespace}:v{GENERATOR_VERSION}:{identifier}".encode()
    digest = hmac.new(seed.encode(), message, hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def load_customers(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("O catálogo de clientes deve ser uma lista JSON não vazia")

    customers: list[dict[str, Any]] = []
    ids: set[int] = set()
    emails: set[str] = set()
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ValueError(f"Cliente na posição {index} não é um objeto")
        external_id = int(raw["external_requester_id"])
        name = str(raw["requester_name"]).strip()
        email = str(raw["requester_email"]).strip().lower()
        if not name or "@" not in email:
            raise ValueError(f"Cliente inválido na posição {index}")
        if external_id in ids or email in emails:
            raise ValueError("IDs externos e e-mails de clientes devem ser únicos")
        ids.add(external_id)
        emails.add(email)
        customers.append(
            {
                "external_requester_id": external_id,
                "requester_name": name,
                "requester_email": email,
            }
        )
    return customers


def choose_status(rng: random.Random, offset: int) -> str:
    if offset < len(STATUSES):
        return STATUSES[offset]
    return rng.choices(STATUSES, weights=(7, 24, 18, 10, 21, 20), k=1)[0]


def choose_priority(rng: random.Random, offset: int) -> str:
    if offset < len(PRIORITIES):
        return PRIORITIES[offset]
    return rng.choices(PRIORITIES, weights=(8, 24, 48, 20), k=1)[0]


def clamp(value: datetime, anchor: datetime) -> datetime:
    return min(value, anchor)


def build_timeline(
    rng: random.Random,
    status: str,
    created: datetime,
    ticket_id: int,
    anchor: datetime,
) -> dict[str, Any]:
    response: datetime | None = None
    offered: datetime | None = None
    rated: datetime | None = None
    score = "unoffered"
    comment = ""

    if status == "new":
        updated = created
    elif status == "open":
        updated = clamp(created + timedelta(minutes=rng.randint(10, 72 * 60)), anchor)
        if rng.random() < 0.78:
            response = clamp(created + timedelta(minutes=rng.randint(4, 180)), anchor)
    elif status in {"pending", "hold"}:
        response = clamp(created + timedelta(minutes=rng.randint(4, 120)), anchor)
        updated = clamp(response + timedelta(minutes=rng.randint(30, 10 * 24 * 60)), anchor)
    else:
        response = clamp(created + timedelta(minutes=rng.randint(3, 180)), anchor)
        solved = clamp(response + timedelta(minutes=rng.randint(30, 7 * 24 * 60)), anchor)
        score = RATINGS[ticket_id % len(RATINGS)]
        if score != "unoffered":
            offered = clamp(solved + timedelta(minutes=rng.randint(1, 30)), anchor)
        if score in {"good", "bad"}:
            assert offered is not None
            rated = clamp(offered + timedelta(minutes=rng.randint(10, 48 * 60)), anchor)
            comment = "Atendimento satisfatório." if score == "good" else "Atendimento abaixo do esperado."
        updated = solved if status == "solved" else clamp(solved + timedelta(days=rng.randint(1, 4)), anchor)
        updated = max(updated, offered or updated, rated or updated)

    return {
        "updated_at": updated,
        "first_response_at": response,
        "rating": {
            "score": score,
            "offered_at": offered,
            "rated_at": rated,
            "comment": comment,
        },
    }


def generate_ticket(
    *,
    customer: dict[str, Any],
    ticket_id: int,
    offset: int,
    seed: str,
    year_start: datetime,
    anchor: datetime,
) -> dict[str, Any]:
    rng = deterministic_rng(seed, "ticket", ticket_id)
    topic, agent_key, scenario_tags = SCENARIOS[rng.randrange(len(SCENARIOS))]
    status = choose_status(rng, offset)
    priority = choose_priority(rng, offset)
    created = year_start + timedelta(
        seconds=rng.randint(0, int((anchor - year_start).total_seconds()))
    )
    timeline = build_timeline(rng, status, created, ticket_id, anchor)
    email_domain = customer["requester_email"].split("@", 1)[1]

    assignee_id: int | None = None
    assignee_name: str | None = None
    if status != "new":
        assignee_id, assignee_name = AGENTS[agent_key]

    rating = timeline["rating"]
    return {
        "ticket_id": ticket_id,
        "subject": f"{topic} em {email_domain}",
        "description": f"Solicitação fictícia sobre {topic.lower()} no ambiente {email_domain}.",
        "status": status,
        "priority": priority,
        "requester_id": customer["external_requester_id"],
        "requester_name": customer["requester_name"],
        "requester_email": customer["requester_email"],
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "created_at": isoformat_z(created),
        "updated_at": isoformat_z(timeline["updated_at"]),
        "first_response_at": isoformat_z(timeline["first_response_at"]),
        "tags": list(
            dict.fromkeys(
                (*scenario_tags, rng.choice(CHANNEL_TAGS), rng.choice(ACCOUNT_TAGS))
            )
        ),
        "satisfaction_rating": {
            "score": rating["score"],
            "offered_at": isoformat_z(rating["offered_at"]),
            "rated_at": isoformat_z(rating["rated_at"]),
            "comment": rating["comment"],
        },
    }


def generate_dataset(
    *,
    customers: list[dict[str, Any]],
    tickets_per_customer: int,
    start_id: int,
    seed: str,
    anchor: datetime,
) -> list[dict[str, Any]]:
    if tickets_per_customer < 2:
        raise ValueError("Cada cliente deve receber ao menos dois tickets")
    year_start = datetime(anchor.year, 1, 1, tzinfo=timezone.utc)
    tickets: list[dict[str, Any]] = []
    offset = 0

    # Round-robin ordering: every batch of 30 contains one ticket per customer.
    for _round in range(tickets_per_customer):
        for customer in customers:
            tickets.append(
                generate_ticket(
                    customer=customer,
                    ticket_id=start_id + offset,
                    offset=offset,
                    seed=seed,
                    year_start=year_start,
                    anchor=anchor,
                )
            )
            offset += 1
    return tickets


def validate_dataset(
    tickets: list[dict[str, Any]],
    *,
    customers: list[dict[str, Any]],
    tickets_per_customer: int,
    anchor: datetime,
) -> dict[str, Any]:
    expected_count = len(customers) * tickets_per_customer
    if len(tickets) != expected_count:
        raise RuntimeError("Quantidade de tickets inválida")
    ids = {ticket["ticket_id"] for ticket in tickets}
    if len(ids) != expected_count:
        raise RuntimeError("IDs de tickets duplicados")

    customer_counts = Counter(ticket["requester_email"] for ticket in tickets)
    if set(customer_counts.values()) != {tickets_per_customer}:
        raise RuntimeError("Distribuição por cliente inválida")

    year_start = datetime(anchor.year, 1, 1, tzinfo=timezone.utc)
    for ticket in tickets:
        for value in (
            ticket["created_at"],
            ticket["updated_at"],
            ticket["first_response_at"],
            ticket["satisfaction_rating"]["offered_at"],
            ticket["satisfaction_rating"]["rated_at"],
        ):
            if value is None:
                continue
            parsed = parse_iso8601(value)
            if parsed < year_start or parsed > anchor:
                raise RuntimeError(f"Ticket {ticket['ticket_id']} fora do ano da âncora")

    statuses = Counter(ticket["status"] for ticket in tickets)
    priorities = Counter(ticket["priority"] for ticket in tickets)
    ratings = Counter(ticket["satisfaction_rating"]["score"] for ticket in tickets)
    if set(statuses) != set(STATUSES):
        raise RuntimeError("Cobertura de status incompleta")
    if set(priorities) != set(PRIORITIES):
        raise RuntimeError("Cobertura de prioridades incompleta")
    if set(ratings) != set(RATINGS):
        raise RuntimeError("Cobertura de satisfação incompleta")

    return {
        "tickets": len(tickets),
        "customers": len(customers),
        "statuses": dict(statuses),
        "priorities": dict(priorities),
        "ratings": dict(ratings),
    }


def write_json(path: Path, tickets: list[dict[str, Any]], *, pretty: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(
            tickets,
            output,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        output.write("\n")
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    temporary.replace(path)
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera o JSON estático de tickets do desafio HostGator"
    )
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--year", type=int, help=f"Ano do dataset. Padrão: {DEFAULT_YEAR}")
    date_group.add_argument("--anchor", help="Data máxima ISO-8601; define o ano")
    parser.add_argument("--customers-file", type=Path, default=DEFAULT_CUSTOMERS_FILE)
    parser.add_argument(
        "--tickets-per-customer",
        type=int,
        default=DEFAULT_TICKETS_PER_CUSTOMER,
    )
    parser.add_argument("--start-id", type=int, default=DEFAULT_START_ID)
    parser.add_argument("--seed")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        anchor = parse_iso8601(args.anchor) if args.anchor else default_anchor(args.year or DEFAULT_YEAR)
        seed = args.seed or f"hostgator-challenge-{anchor.year}"
        customers = load_customers(args.customers_file)
        tickets = generate_dataset(
            customers=customers,
            tickets_per_customer=args.tickets_per_customer,
            start_id=args.start_id,
            seed=seed,
            anchor=anchor,
        )
        summary = validate_dataset(
            tickets,
            customers=customers,
            tickets_per_customer=args.tickets_per_customer,
            anchor=anchor,
        )
        digest = write_json(args.output, tickets, pretty=args.pretty)
    except (KeyError, TypeError, ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(f"Arquivo: {args.output.resolve()}")
    print(f"Ano: {anchor.year}")
    print(f"Âncora: {isoformat_z(anchor)}")
    print(f"SHA-256: {digest}")
    print(f"Tickets: {summary['tickets']}")
    print(f"Clientes: {summary['customers']}")
    print(f"Status: {summary['statuses']}")
    print(f"Prioridades: {summary['priorities']}")
    print(f"Avaliações: {summary['ratings']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
