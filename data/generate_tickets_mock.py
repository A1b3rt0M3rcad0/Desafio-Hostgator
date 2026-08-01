#!/usr/bin/env python3
"""Generate the static HelpDesk fixture consumed by the ingestion worker.

The default command writes ``data/tickets.json`` with 10,000 deterministic
records. Every generated timestamp belongs to the selected year and is bounded
by the anchor. The default dataset uses 2026 and is anchored on 1 August 2026.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

GENERATOR_VERSION: Final[int] = 2
DEFAULT_YEAR: Final[int] = 2026
DEFAULT_COUNT: Final[int] = 10_000
DEFAULT_CUSTOMERS: Final[int] = 500
DEFAULT_START_ID: Final[int] = 100_001
DEFAULT_OUTPUT: Final[Path] = Path(__file__).with_name("tickets.json")

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

SCENARIOS: Final[list[tuple[str, str, tuple[str, ...]]]] = [
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
]

FIRST_NAMES: Final[tuple[str, ...]] = (
    "Ana", "Beatriz", "Bruno", "Camila", "Carlos", "Daniel", "Eduarda", "Felipe",
    "Fernanda", "Gabriel", "Helena", "Igor", "Isabela", "João", "Juliana",
    "Larissa", "Leonardo", "Lucas", "Mariana", "Mateus", "Natália", "Paulo",
    "Rafael", "Renata", "Rodrigo", "Sabrina", "Thiago", "Vanessa", "Vinícius", "Yasmin",
)
LAST_NAMES: Final[tuple[str, ...]] = (
    "Almeida", "Alves", "Andrade", "Barbosa", "Cardoso", "Carvalho", "Castro",
    "Costa", "Dias", "Fernandes", "Ferreira", "Freitas", "Gomes", "Lima", "Lopes",
    "Martins", "Mendes", "Monteiro", "Moraes", "Moreira", "Nascimento", "Nunes",
    "Oliveira", "Pereira", "Ribeiro", "Rocha", "Rodrigues", "Silva", "Souza", "Teixeira",
)
CHANNEL_TAGS: Final[tuple[str, ...]] = ("chat", "email", "formulario-web", "telefone")
ACCOUNT_TAGS: Final[tuple[str, ...]] = ("cliente-pj", "cliente-pme", "cloud", "vps", "compartilhado")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def parse_iso8601(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def deterministic_rng(seed: str, namespace: str, identifier: int) -> random.Random:
    message = f"{namespace}:v{GENERATOR_VERSION}:{identifier}".encode()
    digest = hmac.new(seed.encode(), message, hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def default_anchor(year: int) -> datetime:
    if year < 2000 or year > 2100:
        raise ValueError("--year deve estar entre 2000 e 2100")
    return datetime(year, 8, 1, 5, 30, tzinfo=timezone.utc)


def build_customer(seed: str, index: int) -> dict[str, Any]:
    rng = deterministic_rng(seed, "customer", index)
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    if rng.random() < 0.5:
        last = rng.choice(LAST_NAMES)
    company = f"empresa{index + 1}"
    return {
        "requester_id": 40_000 + index,
        "requester_name": f"{first} {last}",
        "requester_email": f"{slugify(first)}.{slugify(last)}{index + 1}@{company}.com.br",
        "company": company,
    }


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


def build_timeline(rng: random.Random, status: str, created: datetime, ticket_id: int, anchor: datetime) -> dict[str, Any]:
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
            rated = clamp(offered + timedelta(minutes=rng.randint(10, 48 * 60)), anchor)
            comment = "Atendimento satisfatório." if score == "good" else "Atendimento abaixo do esperado."
        updated = solved if status == "solved" else clamp(solved + timedelta(days=rng.randint(1, 4)), anchor)
        updated = max(updated, offered or updated, rated or updated)

    return {
        "updated_at": updated,
        "first_response_at": response,
        "rating": {"score": score, "offered_at": offered, "rated_at": rated, "comment": comment},
    }


def generate_ticket(*, seed: str, ticket_id: int, offset: int, customers: int, year_start: datetime, anchor: datetime) -> dict[str, Any]:
    rng = deterministic_rng(seed, "ticket", ticket_id)
    customer = build_customer(seed, offset % customers)
    topic, agent_key, scenario_tags = SCENARIOS[rng.randrange(len(SCENARIOS))]
    status = choose_status(rng, offset)
    priority = choose_priority(rng, offset)
    total_seconds = int((anchor - year_start).total_seconds())
    created = year_start + timedelta(seconds=rng.randint(0, total_seconds))
    timeline = build_timeline(rng, status, created, ticket_id, anchor)
    domain = f"{customer['company']}-{ticket_id}.com.br"

    assignee_id: int | None = None
    assignee_name: str | None = None
    if status != "new":
        assignee_id, assignee_name = AGENTS[agent_key]

    rating = timeline["rating"]
    return {
        "ticket_id": ticket_id,
        "subject": f"{topic} em {domain}",
        "description": f"Solicitação fictícia sobre {topic.lower()} no serviço {domain}.",
        "status": status,
        "priority": priority,
        "requester_id": customer["requester_id"],
        "requester_name": customer["requester_name"],
        "requester_email": customer["requester_email"],
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "created_at": isoformat_z(created),
        "updated_at": isoformat_z(timeline["updated_at"]),
        "first_response_at": isoformat_z(timeline["first_response_at"]),
        "tags": list(dict.fromkeys((*scenario_tags, rng.choice(CHANNEL_TAGS), rng.choice(ACCOUNT_TAGS)))),
        "satisfaction_rating": {
            "score": rating["score"],
            "offered_at": isoformat_z(rating["offered_at"]),
            "rated_at": isoformat_z(rating["rated_at"]),
            "comment": rating["comment"],
        },
    }


def validate_ticket(ticket: dict[str, Any], *, year_start: datetime, anchor: datetime) -> None:
    dates = [
        ticket["created_at"], ticket["updated_at"], ticket["first_response_at"],
        ticket["satisfaction_rating"]["offered_at"], ticket["satisfaction_rating"]["rated_at"],
    ]
    parsed = [parse_iso8601(value) for value in dates if value]
    if any(value < year_start or value > anchor for value in parsed):
        raise ValueError(f"Ticket {ticket['ticket_id']}: timestamp fora de {anchor.year}")
    if parse_iso8601(ticket["updated_at"]) < parse_iso8601(ticket["created_at"]):
        raise ValueError(f"Ticket {ticket['ticket_id']}: timeline inválida")
    if ticket["status"] == "new" and any((ticket["assignee_id"], ticket["assignee_name"], ticket["first_response_at"])):
        raise ValueError(f"Ticket {ticket['ticket_id']}: ticket new inconsistente")
    if ticket["status"] != "new" and (ticket["assignee_id"] is None or ticket["assignee_name"] is None):
        raise ValueError(f"Ticket {ticket['ticket_id']}: responsável ausente")


def generate_dataset(*, count: int, customers: int, start_id: int, seed: str, anchor: datetime) -> list[dict[str, Any]]:
    if count <= 0 or customers <= 0:
        raise ValueError("--count e --customers devem ser maiores que zero")
    if count < customers * 2:
        raise ValueError("Cada cliente deve receber pelo menos dois tickets")
    year_start = datetime(anchor.year, 1, 1, tzinfo=timezone.utc)
    tickets = [
        generate_ticket(
            seed=seed, ticket_id=start_id + offset, offset=offset, customers=customers,
            year_start=year_start, anchor=anchor,
        )
        for offset in range(count)
    ]
    for ticket in tickets:
        validate_ticket(ticket, year_start=year_start, anchor=anchor)
    return tickets


def validate_dataset(tickets: list[dict[str, Any]], *, count: int, customers: int) -> dict[str, Any]:
    ids = {ticket["ticket_id"] for ticket in tickets}
    customer_counts = Counter(ticket["requester_email"] for ticket in tickets)
    statuses = Counter(ticket["status"] for ticket in tickets)
    priorities = Counter(ticket["priority"] for ticket in tickets)
    ratings = Counter(ticket["satisfaction_rating"]["score"] for ticket in tickets)
    agents = {ticket["assignee_id"] for ticket in tickets if ticket["assignee_id"] is not None}
    tags = {tag for ticket in tickets for tag in ticket["tags"]}
    if len(tickets) != count or len(ids) != count:
        raise RuntimeError("Quantidade ou IDs de tickets inválidos")
    if len(customer_counts) != customers or any(value < 2 for value in customer_counts.values()):
        raise RuntimeError("Distribuição de clientes inválida")
    if set(statuses) != set(STATUSES) or set(priorities) != set(PRIORITIES) or set(ratings) != set(RATINGS):
        raise RuntimeError("Cobertura de enums incompleta")
    if len(agents) != len(AGENTS) or len(tags) < 50:
        raise RuntimeError("Cobertura de agentes ou tags incompleta")
    return {"tickets": count, "customers": customers, "agents": len(agents), "tags": len(tags)}


def write_json(path: Path, tickets: list[dict[str, Any]], *, pretty: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(tickets, output, ensure_ascii=False, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
        output.write("\n")
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    temporary.replace(path)
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera data/tickets.json para o desafio HostGator")
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--year", type=int, help=f"Ano do dataset. Padrão: {DEFAULT_YEAR}")
    date_group.add_argument("--anchor", help="Data máxima ISO-8601; define também o ano do dataset")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMERS)
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
        tickets = generate_dataset(count=args.count, customers=args.customers, start_id=args.start_id, seed=seed, anchor=anchor)
        summary = validate_dataset(tickets, count=args.count, customers=args.customers)
        digest = write_json(args.output, tickets, pretty=args.pretty)
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    created = [parse_iso8601(ticket["created_at"]) for ticket in tickets]
    updated = [parse_iso8601(ticket["updated_at"]) for ticket in tickets]
    print(f"Arquivo: {args.output.resolve()}")
    print(f"Ano: {anchor.year}")
    print(f"Âncora: {isoformat_z(anchor)}")
    print(f"SHA-256: {digest}")
    print(f"Tickets: {summary['tickets']}")
    print(f"Clientes: {summary['customers']}")
    print(f"Agentes: {summary['agents']}")
    print(f"Tags distintas: {summary['tags']}")
    print(f"Menor created_at: {isoformat_z(min(created))}")
    print(f"Maior created_at: {isoformat_z(max(created))}")
    print(f"Maior updated_at: {isoformat_z(max(updated))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
