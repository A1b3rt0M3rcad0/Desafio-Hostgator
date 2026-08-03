#!/usr/bin/env python3
"""Generate one simulated HelpDesk batch for the ingestion worker.

The worker imports this module on every enabled cycle. The generator owns all
mock content, creates a deterministic customer pool (500 by default), produces
one batch (30 tickets by default), and atomically replaces ``tickets.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

GENERATOR_VERSION: Final[int] = 4
DEFAULT_SEED: Final[str] = "hostgator-challenge-v4"
DEFAULT_CUSTOMER_COUNT: Final[int] = 500
DEFAULT_BATCH_SIZE: Final[int] = 30
DEFAULT_START_TICKET_ID: Final[int] = 100_001
DEFAULT_YEAR: Final[int] = 2026
DEFAULT_OUTPUT: Final[Path] = Path(__file__).resolve().with_name("tickets.json")

STATUSES: Final[tuple[str, ...]] = (
    "new",
    "open",
    "pending",
    "hold",
    "solved",
    "closed",
)
PRIORITIES: Final[tuple[str, ...]] = ("urgent", "high", "normal", "low")
RATINGS: Final[tuple[str, ...]] = ("unoffered", "offered", "good", "bad")

FIRST_NAMES: Final[tuple[str, ...]] = (
    "Ana", "Beatriz", "Bruno", "Camila", "Carlos", "Daniel", "Eduarda",
    "Felipe", "Fernanda", "Gabriel", "Helena", "Igor", "Isabela", "João",
    "Juliana", "Larissa", "Leonardo", "Lucas", "Mariana", "Mateus",
    "Natália", "Paulo", "Rafael", "Renata", "Rodrigo", "Sabrina", "Thiago",
    "Vanessa", "Vinícius", "Yasmin", "Aline", "Caio", "Débora", "Gustavo",
    "Heloísa", "Leandro", "Marcelo", "Priscila", "Roberta", "Samuel",
)
LAST_NAMES: Final[tuple[str, ...]] = (
    "Almeida", "Alves", "Andrade", "Barbosa", "Cardoso", "Carvalho",
    "Castro", "Costa", "Dias", "Fernandes", "Ferreira", "Freitas",
    "Gomes", "Lima", "Lopes", "Martins", "Mendes", "Monteiro", "Moraes",
    "Moreira", "Nascimento", "Nunes", "Oliveira", "Pereira", "Ribeiro",
    "Rocha", "Rodrigues", "Silva", "Souza", "Teixeira", "Azevedo",
    "Batista", "Campos", "Correia", "Cunha", "Farias", "Machado",
    "Melo", "Pires", "Rezende",
)
COMPANIES: Final[tuple[str, ...]] = (
    "agenciaponto", "alphacommerce", "automaweb", "belaforma", "bluecommerce",
    "byteworks", "casaverde", "clickmais", "cloudmix", "dataplus",
    "digitalcore", "ecovendas", "fastloja", "fococriativo", "grupohorizonte",
    "inovamais", "lojaviva", "marketway", "midiaponto", "nexustech",
    "pixelstudio", "portalativo", "redeconecta", "solucaoweb", "techcorp",
    "vendamais", "webprime", "agilstore", "baseonline", "conectashop",
    "evolux", "flowdigital", "idealcommerce", "midianova", "nuvemativa",
    "orbeweb", "primehost", "startdigital", "upcommerce", "vitrineweb",
)

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


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def deterministic_rng(seed: str, namespace: str, identifier: int) -> random.Random:
    message = f"{namespace}:v{GENERATOR_VERSION}:{identifier}".encode("utf-8")
    digest = hmac.new(seed.encode("utf-8"), message, hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest[:16], "big"))


def build_customer(*, seed: str, customer_index: int) -> dict[str, Any]:
    rng = deterministic_rng(seed, "customer", customer_index)
    first_name = FIRST_NAMES[customer_index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(customer_index // len(FIRST_NAMES)) % len(LAST_NAMES)]
    if rng.random() < 0.5:
        last_name = LAST_NAMES[rng.randrange(len(LAST_NAMES))]
    company = f"{COMPANIES[customer_index % len(COMPANIES)]}{customer_index + 1}"
    return {
        "requester_id": 40_000 + customer_index,
        "requester_name": f"{first_name} {last_name}",
        "requester_email": (
            f"{slugify(first_name)}.{slugify(last_name)}{customer_index + 1}"
            f"@{company}.com.br"
        ),
    }


def _year_anchor(year: int, cycle_number: int) -> datetime:
    if year < 2000 or year > 2100:
        raise ValueError("year must be between 2000 and 2100")
    base = datetime(year, 8, 1, 5, 30, tzinfo=timezone.utc)
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    return min(base + timedelta(seconds=max(cycle_number, 0) * 30), end)


def _isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_timeline(
    *,
    rng: random.Random,
    status: str,
    created_at: datetime,
    ticket_id: int,
    anchor: datetime,
) -> dict[str, Any]:
    first_response_at: datetime | None = None
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    score = "unoffered"
    comment = ""

    def clamp(value: datetime) -> datetime:
        return min(value, anchor)

    if status == "new":
        updated_at = created_at
    elif status == "open":
        updated_at = clamp(created_at + timedelta(minutes=rng.randint(10, 72 * 60)))
        if rng.random() < 0.78:
            first_response_at = clamp(created_at + timedelta(minutes=rng.randint(4, 180)))
    elif status in {"pending", "hold"}:
        first_response_at = clamp(created_at + timedelta(minutes=rng.randint(4, 120)))
        updated_at = clamp(first_response_at + timedelta(minutes=rng.randint(30, 10 * 24 * 60)))
    else:
        first_response_at = clamp(created_at + timedelta(minutes=rng.randint(3, 180)))
        solved_at = clamp(first_response_at + timedelta(minutes=rng.randint(30, 7 * 24 * 60)))
        score = RATINGS[ticket_id % len(RATINGS)]
        if score != "unoffered":
            offered_at = clamp(solved_at + timedelta(minutes=rng.randint(1, 30)))
        if score in {"good", "bad"}:
            assert offered_at is not None
            rated_at = clamp(offered_at + timedelta(minutes=rng.randint(10, 48 * 60)))
            comment = (
                "Atendimento satisfatório."
                if score == "good"
                else "Atendimento abaixo do esperado."
            )
        updated_at = solved_at
        if status == "closed":
            updated_at = clamp(solved_at + timedelta(days=rng.randint(1, 4)))
        updated_at = max(updated_at, offered_at or updated_at, rated_at or updated_at)

    return {
        "updated_at": updated_at,
        "first_response_at": first_response_at,
        "satisfaction_rating": {
            "score": score,
            "offered_at": offered_at,
            "rated_at": rated_at,
            "comment": comment,
        },
    }


def _generate_ticket(
    *,
    customer: dict[str, Any],
    ticket_id: int,
    batch_offset: int,
    cycle_number: int,
    seed: str,
    year: int,
) -> dict[str, Any]:
    rng = deterministic_rng(seed, "ticket", ticket_id)
    anchor = _year_anchor(year, cycle_number)
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    available_seconds = max(0, int((anchor - year_start).total_seconds()))
    created_at = year_start + timedelta(seconds=rng.randint(0, available_seconds))
    status = STATUSES[batch_offset % len(STATUSES)]
    priority = PRIORITIES[batch_offset % len(PRIORITIES)]
    topic, agent_key, scenario_tags = SCENARIOS[rng.randrange(len(SCENARIOS))]
    timeline = _build_timeline(
        rng=rng,
        status=status,
        created_at=created_at,
        ticket_id=ticket_id,
        anchor=anchor,
    )
    assignee_id: int | None = None
    assignee_name: str | None = None
    if status != "new":
        assignee_id, assignee_name = AGENTS[agent_key]

    domain = customer["requester_email"].split("@", 1)[1]
    rating = timeline["satisfaction_rating"]
    return {
        "ticket_id": ticket_id,
        "subject": f"{topic} em {domain}",
        "description": (
            f"Solicitação fictícia do ciclo {cycle_number + 1} sobre "
            f"{topic.lower()} no ambiente {domain}."
        ),
        "status": status,
        "priority": priority,
        "requester_id": customer["requester_id"],
        "requester_name": customer["requester_name"],
        "requester_email": customer["requester_email"],
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "created_at": _isoformat_z(created_at),
        "updated_at": _isoformat_z(timeline["updated_at"]),
        "first_response_at": _isoformat_z(timeline["first_response_at"]),
        "tags": list(
            dict.fromkeys(
                (*scenario_tags, rng.choice(CHANNEL_TAGS), rng.choice(ACCOUNT_TAGS))
            )
        ),
        "satisfaction_rating": {
            "score": rating["score"],
            "offered_at": _isoformat_z(rating["offered_at"]),
            "rated_at": _isoformat_z(rating["rated_at"]),
            "comment": rating["comment"],
        },
    }


def generate_batch(
    *,
    cycle_number: int,
    start_ticket_id: int,
    ticket_count: int = DEFAULT_BATCH_SIZE,
    customer_count: int = DEFAULT_CUSTOMER_COUNT,
    year: int = DEFAULT_YEAR,
    seed: str = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    if cycle_number < 0:
        raise ValueError("cycle_number cannot be negative")
    if start_ticket_id <= 0:
        raise ValueError("start_ticket_id must be positive")
    if ticket_count <= 0:
        raise ValueError("ticket_count must be positive")
    if customer_count <= 0:
        raise ValueError("customer_count must be positive")
    if ticket_count > customer_count:
        raise ValueError("ticket_count cannot exceed customer_count")

    first_customer = (cycle_number * ticket_count) % customer_count
    tickets: list[dict[str, Any]] = []
    for offset in range(ticket_count):
        customer_index = (first_customer + offset) % customer_count
        customer = build_customer(seed=seed, customer_index=customer_index)
        tickets.append(
            _generate_ticket(
                customer=customer,
                ticket_id=start_ticket_id + offset,
                batch_offset=offset,
                cycle_number=cycle_number,
                seed=seed,
                year=year,
            )
        )
    validate_batch(
        tickets,
        expected_count=ticket_count,
        customer_count=customer_count,
        year=year,
    )
    return tickets


def validate_batch(
    tickets: list[dict[str, Any]],
    *,
    expected_count: int,
    customer_count: int,
    year: int,
) -> None:
    if len(tickets) != expected_count:
        raise RuntimeError("generated ticket count is invalid")
    if len({ticket["ticket_id"] for ticket in tickets}) != expected_count:
        raise RuntimeError("generated ticket IDs are not unique")
    if len({ticket["requester_email"] for ticket in tickets}) != expected_count:
        raise RuntimeError("a batch must use distinct customers")
    requester_ids = {ticket["requester_id"] for ticket in tickets}
    if any(value < 40_000 or value >= 40_000 + customer_count for value in requester_ids):
        raise RuntimeError("generated customer is outside the configured pool")
    if set(ticket["status"] for ticket in tickets) != set(STATUSES):
        raise RuntimeError("status coverage is incomplete")
    if set(ticket["priority"] for ticket in tickets) != set(PRIORITIES):
        raise RuntimeError("priority coverage is incomplete")
    for ticket in tickets:
        for field in ("created_at", "updated_at", "first_response_at"):
            value = ticket[field]
            if value is not None and datetime.fromisoformat(value.replace("Z", "+00:00")).year != year:
                raise RuntimeError(f"ticket {ticket['ticket_id']} has a timestamp outside {year}")


def write_json_atomic(
    path: str | Path,
    tickets: list[dict[str, Any]],
    *,
    pretty: bool = False,
) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(
            tickets,
            output,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    temporary.replace(target)
    return digest


def generate_and_write_batch(
    *,
    output: str | Path,
    cycle_number: int,
    start_ticket_id: int,
    ticket_count: int = DEFAULT_BATCH_SIZE,
    customer_count: int = DEFAULT_CUSTOMER_COUNT,
    year: int = DEFAULT_YEAR,
    seed: str = DEFAULT_SEED,
    pretty: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    tickets = generate_batch(
        cycle_number=cycle_number,
        start_ticket_id=start_ticket_id,
        ticket_count=ticket_count,
        customer_count=customer_count,
        year=year,
        seed=seed,
    )
    digest = write_json_atomic(output, tickets, pretty=pretty)
    return tickets, digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera um lote de tickets HelpDesk")
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--start-id", type=int, default=DEFAULT_START_TICKET_ID)
    parser.add_argument("--count", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--customers", type=int, default=DEFAULT_CUSTOMER_COUNT)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        tickets, digest = generate_and_write_batch(
            output=args.output,
            cycle_number=args.cycle,
            start_ticket_id=args.start_id,
            ticket_count=args.count,
            customer_count=args.customers,
            year=args.year,
            seed=args.seed,
            pretty=args.pretty,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    customers = Counter(ticket["requester_email"] for ticket in tickets)
    print(f"Arquivo: {args.output.resolve()}")
    print(f"Ciclo: {args.cycle}")
    print(f"Tickets: {len(tickets)}")
    print(f"Clientes no lote: {len(customers)}")
    print(f"Base de clientes: {args.customers}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
