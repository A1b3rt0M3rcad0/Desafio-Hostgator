#!/usr/bin/env python3
"""
Gera um arquivo JSON estático de tickets no formato achatado do desafio.

Propriedades:
- somente biblioteca padrão;
- 10.000 tickets por padrão;
- geração determinística por ticket_id;
- o mesmo ticket_id sempre gera o mesmo conteúdo, mantendo:
  master seed, generator version, start id, quantidade de clientes e catálogos;
- evita IDs duplicados;
- evita tickets com assunto e descrição iguais para o mesmo cliente;
- cobre todos os status, prioridades e estados de satisfação;
- utiliza 10 agentes compatíveis com operações de hospedagem;
- utiliza mais de 50 tags distintas;
- valida integralmente o dataset antes de gravá-lo.

Uso:
    python generate_tickets_mock.py

Uso configurado:
    python generate_tickets_mock.py \
        --count 10000 \
        --customers 500 \
        --output tickets_mock_10000.json \
        --seed hostgator-challenge-v1 \
        --start-id 100001

O JSON gerado pode ser carregado pela Mock API sem regeneração dinâmica.
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


GENERATOR_VERSION: Final[int] = 1
DEFAULT_SEED: Final[str] = "hostgator-challenge-v1"
DEFAULT_COUNT: Final[int] = 10_000
DEFAULT_CUSTOMER_COUNT: Final[int] = 500
DEFAULT_START_ID: Final[int] = 100_001
DEFAULT_OUTPUT: Final[str] = "tickets_mock_10000.json"
DEFAULT_ANCHOR: Final[str] = "2026-07-29T12:00:00Z"

ALLOWED_STATUSES: Final[set[str]] = {
    "new",
    "open",
    "pending",
    "hold",
    "solved",
    "closed",
}
ALLOWED_PRIORITIES: Final[set[str]] = {
    "low",
    "normal",
    "high",
    "urgent",
}
ALLOWED_RATINGS: Final[set[str]] = {
    "unoffered",
    "offered",
    "good",
    "bad",
}

AGENTS: Final[dict[str, dict[str, Any]]] = {
    "n1": {
        "id": 9101,
        "name": "Patrícia Gomes (Suporte N1)",
    },
    "infra": {
        "id": 9102,
        "name": "Rafael Souza (N2 - Infraestrutura)",
    },
    "domains": {
        "id": 9103,
        "name": "Marina Alves (Domínios e DNS)",
    },
    "email": {
        "id": 9104,
        "name": "Lucas Mendes (E-mail)",
    },
    "hosting": {
        "id": 9105,
        "name": "Fernanda Costa (Hospedagem)",
    },
    "billing": {
        "id": 9106,
        "name": "Juliana Martins (Financeiro)",
    },
    "wordpress": {
        "id": 9107,
        "name": "Bruno Carvalho (WordPress)",
    },
    "security": {
        "id": 9108,
        "name": "Camila Rocha (Segurança e SSL)",
    },
    "migration": {
        "id": 9109,
        "name": "Diego Nunes (Migrações)",
    },
    "performance": {
        "id": 9110,
        "name": "André Lima (Servidores e Performance)",
    },
}


def scenario(
    subject: str,
    description: str,
    agent: str,
    tags: list[str],
) -> dict[str, Any]:
    return {
        "subject": subject,
        "description": description,
        "agent": agent,
        "tags": tags,
    }


SCENARIOS: Final[list[dict[str, Any]]] = [
    scenario(
        "Sistema de login indisponível em {domain}",
        "Os usuários não conseguem acessar o portal hospedado em {domain}. "
        "A aplicação retorna o erro {error_code}.",
        "n1",
        ["login", "portal", "autenticacao", "erro-aplicacao"],
    ),
    scenario(
        "Erro ao redefinir senha da conta {mailbox}",
        "O link de redefinição enviado para {mailbox} expira antes da conclusão "
        "da troca de senha.",
        "n1",
        ["senha", "redefinicao", "token-expirado", "email-transacional"],
    ),
    scenario(
        "Conta {mailbox} bloqueada após tentativas de acesso",
        "A conta {mailbox} foi bloqueada após várias tentativas de autenticação "
        "sem sucesso originadas do IP {ip_address}.",
        "security",
        ["conta-bloqueada", "tentativas", "autenticacao", "seguranca"],
    ),
    scenario(
        "Domínio {domain} ainda não está acessível",
        "O domínio {domain} foi registrado, mas ainda não responde em diferentes "
        "provedores de internet.",
        "domains",
        ["dominio", "dns", "propagacao", "nameserver"],
    ),
    scenario(
        "Certificado SSL pendente para {domain}",
        "O certificado SSL de {domain} permanece pendente e o navegador apresenta "
        "aviso de conexão não segura.",
        "security",
        ["ssl", "certificado", "https", "validacao"],
    ),
    scenario(
        "Conflito de plugins no WordPress de {domain}",
        "Após a atualização do plugin {plugin}, o painel de {domain} apresenta "
        "erro fatal de compatibilidade.",
        "wordpress",
        ["wordpress", "plugin", "erro-php", "compatibilidade"],
    ),
    scenario(
        "Migração do site {domain}",
        "Solicitação de migração do site {domain}, incluindo arquivos e o banco "
        "{database}. Referência {operation_ref}.",
        "migration",
        ["migracao", "wordpress", "backup", "banco-de-dados"],
    ),
    scenario(
        "Site {domain} apresentando erro 503",
        "O site {domain} retorna erro 503 durante períodos de maior volume de "
        "acessos.",
        "hosting",
        ["hospedagem", "erro-503", "indisponibilidade", "recursos"],
    ),
    scenario(
        "Uso elevado de CPU no serviço {service_name}",
        "O serviço {service_name} ligado a {domain} apresenta alto consumo de CPU "
        "e memória.",
        "performance",
        ["performance", "cpu", "memoria", "processos"],
    ),
    scenario(
        "Caixa postal {mailbox} atingiu o limite",
        "O envio e o recebimento de mensagens da caixa {mailbox} foram interrompidos "
        "por falta de espaço.",
        "email",
        ["email", "caixa-postal", "armazenamento", "quota"],
    ),
    scenario(
        "Configuração de SPF, DKIM e DMARC para {domain}",
        "É necessário validar os registros de autenticação e entrega de e-mails "
        "do domínio {domain}.",
        "email",
        ["spf", "dkim", "dmarc", "entregabilidade"],
    ),
    scenario(
        "Falha de autenticação SMTP em {mailbox}",
        "A conta {mailbox} não autentica no servidor SMTP usando a porta "
        "{smtp_port}.",
        "email",
        ["smtp", "envio-email", "credenciais", "porta-smtp"],
    ),
    scenario(
        "Cobrança duplicada na fatura {invoice_ref}",
        "Foram identificadas duas cobranças referentes à fatura {invoice_ref} "
        "do plano {plan_name}.",
        "billing",
        ["cobranca", "duplicidade", "renovacao", "financeiro"],
    ),
    scenario(
        "Segunda via da fatura {invoice_ref}",
        "O cliente precisa acessar a segunda via da fatura {invoice_ref} e a nota "
        "fiscal correspondente.",
        "billing",
        ["fatura", "boleto", "nota-fiscal", "pagamento"],
    ),
    scenario(
        "Cancelamento do pedido {order_ref}",
        "O cliente solicita o cancelamento do pedido {order_ref} e a confirmação "
        "do prazo de estorno.",
        "billing",
        ["estorno", "cancelamento", "reembolso", "prazo"],
    ),
    scenario(
        "Restauração do backup {backup_ref}",
        "Solicitação de restauração do banco {database} usando o ponto de "
        "recuperação {backup_ref}.",
        "infra",
        ["backup", "restauracao", "mysql", "ponto-restauracao"],
    ),
    scenario(
        "Falha de conexão FTP em {domain}",
        "A conexão FTP de {domain} é recusada mesmo com credenciais válidas. "
        "Origem {ip_address}.",
        "hosting",
        ["ftp", "conexao", "firewall", "credenciais-ftp"],
    ),
    scenario(
        "Acesso ao cPanel de {domain} negado",
        "O painel de {domain} retorna permissão insuficiente para o usuário "
        "{mailbox}.",
        "n1",
        ["cpanel", "painel", "permissao", "acesso-negado"],
    ),
    scenario(
        "Tarefa cron {operation_ref} não executa",
        "A tarefa cron {operation_ref} ligada ao serviço {service_name} não é "
        "executada no horário configurado.",
        "infra",
        ["cron", "agendamento", "script", "automacao"],
    ),
    scenario(
        "Loop de redirecionamento em {domain}",
        "O site {domain} apresenta excesso de redirecionamentos após uma alteração "
        "no arquivo .htaccess.",
        "hosting",
        ["redirecionamento", "htaccess", "url", "loop"],
    ),
    scenario(
        "Arquivos maliciosos detectados em {domain}",
        "A varredura {scan_ref} identificou arquivos suspeitos e alterações não "
        "reconhecidas em {domain}.",
        "security",
        ["malware", "arquivo-infectado", "quarentena", "scanner"],
    ),
    scenario(
        "Mensagens de phishing recebidas em {mailbox}",
        "A caixa {mailbox} recebeu mensagens fraudulentas imitando comunicações "
        "administrativas.",
        "security",
        ["phishing", "spam", "abuso", "email"],
    ),
    scenario(
        "Subdomínio {subdomain} não resolve corretamente",
        "O subdomínio {subdomain} não aponta para o endereço {ip_address} "
        "configurado na zona DNS.",
        "domains",
        ["subdominio", "zona-dns", "apontamento", "dns"],
    ),
    scenario(
        "API de {domain} retorna timeout",
        "As chamadas para o endpoint {api_path} de {domain} excedem o tempo limite "
        "durante a operação {operation_ref}.",
        "performance",
        ["api", "timeout", "integracao", "latencia"],
    ),
    scenario(
        "Acesso SSH rejeitado em {domain}",
        "O servidor associado a {domain} rejeita a chave pública registrada para "
        "o acesso {operation_ref}.",
        "infra",
        ["ssh", "chave-publica", "acesso-remoto", "permissao-ssh"],
    ),
    scenario(
        "Conteúdo antigo permanece no CDN de {domain}",
        "As alterações publicadas em {domain} não aparecem após a operação de "
        "limpeza {operation_ref}.",
        "performance",
        ["cdn", "cache", "purge", "performance"],
    ),
    scenario(
        "Transferência do domínio {domain} pendente",
        "A transferência de {domain} não avançou após o envio do código EPP "
        "associado à operação {operation_ref}.",
        "domains",
        ["transferencia-dominio", "epp", "registro", "dominio"],
    ),
    scenario(
        "Domínio adicional {domain} abre diretório incorreto",
        "O domínio {domain} exibe conteúdo diferente do document root configurado "
        "no painel.",
        "domains",
        ["dominio-adicional", "redirecionamento", "configuracao", "document-root"],
    ),
    scenario(
        "Migração IMAP da caixa {mailbox}",
        "Solicitação de cópia das mensagens da caixa {mailbox} a partir do provedor "
        "anterior. Operação {operation_ref}.",
        "migration",
        ["migracao-email", "imap", "sincronizacao", "caixa-postal"],
    ),
    scenario(
        "Anexo excede o limite em {mailbox}",
        "O servidor rejeita mensagens da caixa {mailbox} com anexos acima de "
        "{attachment_mb} MB.",
        "email",
        ["anexo", "limite-envio", "tamanho-arquivo", "email"],
    ),
    scenario(
        "Banco {database} atingiu o limite de conexões",
        "O banco {database} rejeita novas conexões durante o pico registrado na "
        "operação {operation_ref}.",
        "performance",
        ["mysql", "conexoes", "limite-conexoes", "performance"],
    ),
    scenario(
        "Permissões incorretas nos arquivos de {domain}",
        "Os arquivos de {domain} apresentam permissões incompatíveis com a execução "
        "do serviço web.",
        "hosting",
        ["permissoes-arquivo", "chmod", "hospedagem", "erro-403"],
    ),
    scenario(
        "Erro 404 em páginas internas de {domain}",
        "As páginas internas de {domain} retornam erro 404, embora a página inicial "
        "esteja acessível.",
        "wordpress",
        ["erro-404", "links-permanentes", "wordpress", "rewrite"],
    ),
    scenario(
        "Atualização do PHP em {domain}",
        "O cliente solicita a alteração da versão do PHP usada por {domain} para "
        "{php_version}.",
        "hosting",
        ["php", "versao-php", "compatibilidade", "configuracao"],
    ),
    scenario(
        "Plano {plan_name} próximo do limite de disco",
        "A conta ligada a {domain} atingiu mais de 90% do espaço disponível no "
        "plano {plan_name}.",
        "hosting",
        ["espaco-disco", "plano-hospedagem", "armazenamento", "alerta"],
    ),
    scenario(
        "Renovação do domínio {domain} não confirmada",
        "O pagamento da renovação de {domain} consta como aprovado, mas a validade "
        "do domínio não foi atualizada.",
        "billing",
        ["renovacao-dominio", "pagamento", "validade", "financeiro"],
    ),
    scenario(
        "Registro MX incorreto em {domain}",
        "O domínio {domain} possui registros MX apontando para um serviço de e-mail "
        "diferente do contratado.",
        "email",
        ["mx", "dns", "recebimento-email", "configuracao-email"],
    ),
    scenario(
        "Site {domain} comprometido após acesso indevido",
        "Foram identificadas alterações não autorizadas no site {domain} após um "
        "login originado do IP {ip_address}.",
        "security",
        ["acesso-indevido", "credencial-vazada", "incidente", "seguranca"],
    ),
    scenario(
        "Aplicação de {domain} apresenta erro de conexão",
        "A aplicação hospedada em {domain} não consegue se conectar ao banco "
        "{database}.",
        "infra",
        ["conexao-banco", "aplicacao", "mysql", "configuracao"],
    ),
    scenario(
        "Deploy de {domain} interrompido",
        "O deploy identificado por {operation_ref} foi interrompido durante a "
        "publicação dos arquivos.",
        "hosting",
        ["deploy", "publicacao", "arquivos", "falha-deploy"],
    ),
    scenario(
        "Backup automático não foi gerado para {domain}",
        "O backup programado {backup_ref} não aparece no painel de {domain}.",
        "infra",
        ["backup-automatico", "agendamento", "retencao", "hospedagem"],
    ),
    scenario(
        "Latência elevada no acesso a {domain}",
        "O acesso a {domain} apresenta latência acima do esperado a partir da "
        "região {region}.",
        "performance",
        ["latencia", "rede", "regiao", "tempo-resposta"],
    ),
    scenario(
        "Webhook de {domain} não entrega eventos",
        "O webhook configurado no caminho {api_path} não entrega os eventos da "
        "operação {operation_ref}.",
        "performance",
        ["webhook", "integracao", "evento", "falha-entrega"],
    ),
    scenario(
        "Conta de e-mail {mailbox} marcada como spam",
        "As mensagens enviadas por {mailbox} estão sendo classificadas como spam "
        "pelos destinatários.",
        "email",
        ["reputacao", "spam", "blacklist", "entregabilidade"],
    ),
    scenario(
        "Importação do banco {database} falhou",
        "A importação do banco {database} falhou durante o processamento do arquivo "
        "{backup_ref}.",
        "migration",
        ["importacao-banco", "sql", "migração", "erro-importacao"],
    ),
]


FIRST_NAMES: Final[list[str]] = [
    "Ana", "Beatriz", "Bruno", "Camila", "Carlos", "Daniel", "Eduarda",
    "Felipe", "Fernanda", "Gabriel", "Helena", "Igor", "Isabela", "João",
    "Juliana", "Larissa", "Leonardo", "Lucas", "Mariana", "Mateus",
    "Natália", "Paulo", "Rafael", "Renata", "Rodrigo", "Sabrina", "Thiago",
    "Vanessa", "Vinícius", "Yasmin", "Aline", "Caio", "Débora", "Gustavo",
    "Heloísa", "Leandro", "Marcelo", "Priscila", "Roberta", "Samuel",
]

LAST_NAMES: Final[list[str]] = [
    "Almeida", "Alves", "Andrade", "Barbosa", "Cardoso", "Carvalho",
    "Castro", "Costa", "Dias", "Fernandes", "Ferreira", "Freitas",
    "Gomes", "Lima", "Lopes", "Martins", "Mendes", "Monteiro", "Moraes",
    "Moreira", "Nascimento", "Nunes", "Oliveira", "Pereira", "Ribeiro",
    "Rocha", "Rodrigues", "Silva", "Souza", "Teixeira", "Azevedo",
    "Batista", "Campos", "Correia", "Cunha", "Farias", "Machado",
    "Melo", "Pires", "Rezende",
]

COMPANIES: Final[list[str]] = [
    "agenciaponto", "alphacommerce", "automaweb", "belaforma",
    "bluecommerce", "byteworks", "casaverde", "clickmais", "cloudmix",
    "dataplus", "digitalcore", "ecovendas", "fastloja", "fococriativo",
    "grupohorizonte", "inovamais", "lojaviva", "marketway", "midiaponto",
    "nexustech", "pixelstudio", "portalativo", "redeconecta",
    "solucaoweb", "techcorp", "vendamais", "webprime", "agilstore",
    "baseonline", "conectashop", "evolux", "flowdigital", "idealcommerce",
    "midianova", "nuvemativa", "orbeweb", "primehost", "startdigital",
    "upcommerce", "vitrineweb",
]

PLUGINS: Final[list[str]] = [
    "WooCommerce", "Elementor", "Yoast SEO", "Contact Form 7",
    "WP Rocket", "LiteSpeed Cache", "Wordfence", "Rank Math",
]

PLAN_NAMES: Final[list[str]] = [
    "Hospedagem P", "Hospedagem M", "Hospedagem Business",
    "Cloud Standard", "Cloud Plus", "WordPress Pro", "VPS 2",
]

SERVICE_NAMES: Final[list[str]] = [
    "php-fpm", "nginx", "apache", "mysql", "redis", "node", "cron",
]

REGIONS: Final[list[str]] = [
    "São Paulo", "Rio de Janeiro", "Curitiba", "Recife", "Brasília",
    "Porto Alegre", "Belo Horizonte", "Fortaleza",
]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    return ascii_value.strip("-")


def normalize_text(value: str) -> str:
    return " ".join(slugify(value).replace("-", " ").split())


def parse_iso8601(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def deterministic_rng(
    master_seed: str,
    namespace: str,
    identifier: int,
) -> random.Random:
    message = (
        f"{namespace}:v{GENERATOR_VERSION}:{identifier}"
    ).encode("utf-8")

    digest = hmac.new(
        master_seed.encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()

    seed = int.from_bytes(digest[:16], byteorder="big", signed=False)
    return random.Random(seed)


def build_customer(
    master_seed: str,
    customer_index: int,
) -> dict[str, Any]:
    rng = deterministic_rng(master_seed, "customer", customer_index)

    first_name = FIRST_NAMES[customer_index % len(FIRST_NAMES)]
    last_name = LAST_NAMES[
        (customer_index // len(FIRST_NAMES)) % len(LAST_NAMES)
    ]
    company_base = COMPANIES[customer_index % len(COMPANIES)]
    company_slug = f"{company_base}{customer_index + 1}"

    # Usa RNG do cliente para evitar padrões excessivamente sequenciais.
    if rng.random() < 0.5:
        last_name = LAST_NAMES[rng.randrange(len(LAST_NAMES))]

    full_name = f"{first_name} {last_name}"
    email = (
        f"{slugify(first_name)}.{slugify(last_name)}"
        f"{customer_index + 1}@{company_slug}.com.br"
    )

    return {
        "requester_id": 40_000 + customer_index,
        "requester_name": full_name,
        "requester_email": email,
        "company_slug": company_slug,
    }


def weighted_choice(
    rng: random.Random,
    values: list[str],
    weights: list[int],
) -> str:
    return rng.choices(values, weights=weights, k=1)[0]


def choose_status(rng: random.Random, offset: int) -> str:
    # Garante cobertura mínima nos primeiros registros.
    guaranteed = ["new", "open", "pending", "hold", "solved", "closed"]
    if offset < len(guaranteed):
        return guaranteed[offset]

    return weighted_choice(
        rng,
        ["new", "open", "pending", "hold", "solved", "closed"],
        [7, 24, 18, 10, 21, 20],
    )


def choose_priority(rng: random.Random, offset: int) -> str:
    guaranteed = ["urgent", "high", "normal", "low"]
    if offset < len(guaranteed):
        return guaranteed[offset]

    return weighted_choice(
        rng,
        ["urgent", "high", "normal", "low"],
        [8, 24, 48, 20],
    )


def build_context(
    rng: random.Random,
    customer: dict[str, Any],
    ticket_id: int,
) -> dict[str, str | int]:
    company = customer["company_slug"]
    domain = f"{company}-{ticket_id}.com.br"
    mailbox_prefix = rng.choice(
        ["contato", "financeiro", "suporte", "comercial", "admin", "vendas"]
    )
    mailbox = f"{mailbox_prefix}.{ticket_id}@{company}.com.br"

    octet_2 = 10 + (ticket_id % 200)
    octet_3 = 1 + ((ticket_id // 7) % 250)
    octet_4 = 1 + ((ticket_id // 13) % 250)

    return {
        "domain": domain,
        "subdomain": f"{rng.choice(['app', 'api', 'loja', 'blog', 'painel'])}.{domain}",
        "mailbox": mailbox,
        "database": f"db_{company}_{ticket_id}",
        "operation_ref": f"OP-{ticket_id}",
        "invoice_ref": f"FAT-{ticket_id}",
        "order_ref": f"PED-{ticket_id}",
        "backup_ref": f"BKP-{ticket_id}",
        "scan_ref": f"SCAN-{ticket_id}",
        "service_name": rng.choice(SERVICE_NAMES),
        "plugin": rng.choice(PLUGINS),
        "plan_name": rng.choice(PLAN_NAMES),
        "error_code": rng.choice(["500", "502", "504", "ERR_CONNECTION_RESET"]),
        "ip_address": f"177.{octet_2}.{octet_3}.{octet_4}",
        "smtp_port": rng.choice([465, 587]),
        "attachment_mb": rng.choice([25, 35, 50, 75]),
        "php_version": rng.choice(["8.1", "8.2", "8.3", "8.4"]),
        "api_path": rng.choice(
            ["/api/orders", "/api/webhooks", "/api/login", "/api/checkout"]
        ),
        "region": rng.choice(REGIONS),
    }


def build_timeline(
    rng: random.Random,
    status: str,
    created_at: datetime,
    ticket_id: int,
) -> dict[str, Any]:
    first_response_at: datetime | None = None
    offered_at: datetime | None = None
    rated_at: datetime | None = None
    score = "unoffered"
    comment: str | None = None

    if status == "new":
        updated_at = created_at

    elif status == "open":
        updated_at = created_at + timedelta(
            minutes=rng.randint(10, 72 * 60)
        )

        # Um ticket aberto pode já ter responsável e ainda não ter resposta.
        if rng.random() < 0.78:
            maximum_minutes = max(
                4,
                min(
                    180,
                    int((updated_at - created_at).total_seconds() // 60),
                ),
            )
            first_response_at = created_at + timedelta(
                minutes=rng.randint(4, maximum_minutes)
            )

    elif status in {"pending", "hold"}:
        first_response_at = created_at + timedelta(
            minutes=rng.randint(4, 120)
        )
        updated_at = first_response_at + timedelta(
            minutes=rng.randint(30, 10 * 24 * 60)
        )

    else:
        first_response_at = created_at + timedelta(
            minutes=rng.randint(3, 180)
        )
        solved_at = first_response_at + timedelta(
            minutes=rng.randint(30, 7 * 24 * 60)
        )

        # Determinístico por ID e cobre os quatro estados.
        score = ["unoffered", "offered", "good", "bad"][ticket_id % 4]

        if score != "unoffered":
            offered_at = solved_at + timedelta(
                minutes=rng.randint(1, 30)
            )

        if score in {"good", "bad"}:
            rated_at = offered_at + timedelta(
                minutes=rng.randint(10, 48 * 60)
            )

            if score == "good":
                comment = rng.choice(
                    [
                        "O atendimento foi rápido e resolveu o problema.",
                        "A orientação foi clara e a solução funcionou.",
                        "O problema foi resolvido dentro do esperado.",
                        "O suporte explicou corretamente cada etapa.",
                    ]
                )
            else:
                comment = rng.choice(
                    [
                        "A solução demorou mais do que o esperado.",
                        "Foi necessário repetir informações durante o atendimento.",
                        "O problema foi resolvido, mas o acompanhamento poderia melhorar.",
                        "A primeira resposta não esclareceu a causa do problema.",
                    ]
                )

        if status == "solved":
            updated_at = max(
                solved_at,
                offered_at or solved_at,
                rated_at or solved_at,
            )
        else:
            closed_at = solved_at + timedelta(days=rng.randint(1, 4))
            updated_at = max(
                closed_at,
                offered_at or closed_at,
                rated_at or closed_at,
            )

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


def generate_ticket(
    *,
    master_seed: str,
    ticket_id: int,
    offset: int,
    start_id: int,
    customer_count: int,
    anchor_at: datetime,
) -> dict[str, Any]:
    del start_id  # Parte da configuração externa; não afeta o RNG do ticket.

    rng = deterministic_rng(master_seed, "ticket", ticket_id)

    # Distribuição uniforme: com 10.000 tickets e 500 clientes,
    # cada cliente recebe exatamente 20 tickets.
    customer_index = offset % customer_count
    customer = build_customer(master_seed, customer_index)

    scenario_item = SCENARIOS[rng.randrange(len(SCENARIOS))]
    context = build_context(rng, customer, ticket_id)

    status = choose_status(rng, offset)
    priority = choose_priority(rng, offset)

    created_at = anchor_at - timedelta(
        days=rng.randint(0, 730),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )

    timeline = build_timeline(
        rng=rng,
        status=status,
        created_at=created_at,
        ticket_id=ticket_id,
    )

    if status == "new":
        assignee_id = None
        assignee_name = None
    else:
        agent = AGENTS[scenario_item["agent"]]
        assignee_id = agent["id"]
        assignee_name = agent["name"]

    extra_tags = [
        rng.choice(["chat", "email", "formulario-web", "telefone"]),
        rng.choice(
            [
                "cliente-pj",
                "cliente-pme",
                "servico-compartilhado",
                "cloud",
                "vps",
            ]
        ),
    ]

    tags = list(
        dict.fromkeys(
            [*scenario_item["tags"], *extra_tags]
        )
    )

    rating = timeline["satisfaction_rating"]

    return {
        "ticket_id": ticket_id,
        "subject": scenario_item["subject"].format(**context),
        "description": scenario_item["description"].format(**context),
        "status": status,
        "priority": priority,
        "requester_id": customer["requester_id"],
        "requester_name": customer["requester_name"],
        "requester_email": customer["requester_email"],
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
        "created_at": isoformat_z(created_at),
        "updated_at": isoformat_z(timeline["updated_at"]),
        "first_response_at": isoformat_z(
            timeline["first_response_at"]
        ),
        "tags": tags,
        "satisfaction_rating": {
            "score": rating["score"],
            "offered_at": isoformat_z(rating["offered_at"]),
            "rated_at": isoformat_z(rating["rated_at"]),
            "comment": rating["comment"],
        },
    }


def semantic_fingerprint(ticket: dict[str, Any]) -> str:
    canonical = "|".join(
        [
            ticket["requester_email"].strip().lower(),
            normalize_text(ticket["subject"]),
            normalize_text(ticket["description"]),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_ticket_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return parse_iso8601(value)


def validate_ticket(ticket: dict[str, Any]) -> None:
    required_keys = {
        "ticket_id",
        "subject",
        "description",
        "status",
        "priority",
        "requester_id",
        "requester_name",
        "requester_email",
        "assignee_id",
        "assignee_name",
        "created_at",
        "updated_at",
        "first_response_at",
        "tags",
        "satisfaction_rating",
    }

    missing = required_keys - set(ticket)
    if missing:
        raise ValueError(
            f"Ticket {ticket.get('ticket_id')} sem campos: {sorted(missing)}"
        )

    ticket_id = ticket["ticket_id"]
    status = ticket["status"]
    priority = ticket["priority"]
    rating = ticket["satisfaction_rating"]["score"]

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Ticket {ticket_id}: status inválido: {status}")

    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(
            f"Ticket {ticket_id}: prioridade inválida: {priority}"
        )

    if rating not in ALLOWED_RATINGS:
        raise ValueError(f"Ticket {ticket_id}: rating inválido: {rating}")

    created_at = parse_ticket_datetime(ticket["created_at"])
    updated_at = parse_ticket_datetime(ticket["updated_at"])
    first_response_at = parse_ticket_datetime(ticket["first_response_at"])
    offered_at = parse_ticket_datetime(
        ticket["satisfaction_rating"]["offered_at"]
    )
    rated_at = parse_ticket_datetime(
        ticket["satisfaction_rating"]["rated_at"]
    )

    if updated_at < created_at:
        raise ValueError(
            f"Ticket {ticket_id}: updated_at anterior ao created_at."
        )

    if first_response_at and first_response_at < created_at:
        raise ValueError(
            f"Ticket {ticket_id}: first_response_at anterior ao created_at."
        )

    if status == "new":
        if ticket["assignee_id"] is not None:
            raise ValueError(
                f"Ticket {ticket_id}: ticket new não pode ter assignee."
            )
        if ticket["assignee_name"] is not None:
            raise ValueError(
                f"Ticket {ticket_id}: ticket new não pode ter assignee_name."
            )
        if first_response_at is not None:
            raise ValueError(
                f"Ticket {ticket_id}: ticket new não pode ter primeira resposta."
            )
    else:
        if ticket["assignee_id"] is None or ticket["assignee_name"] is None:
            raise ValueError(
                f"Ticket {ticket_id}: status {status} exige assignee."
            )

    if rating == "unoffered":
        if offered_at is not None or rated_at is not None:
            raise ValueError(
                f"Ticket {ticket_id}: unoffered inconsistente."
            )
    elif rating == "offered":
        if offered_at is None or rated_at is not None:
            raise ValueError(
                f"Ticket {ticket_id}: offered inconsistente."
            )
    else:
        if offered_at is None or rated_at is None:
            raise ValueError(
                f"Ticket {ticket_id}: {rating} exige offered_at e rated_at."
            )
        if rated_at < offered_at:
            raise ValueError(
                f"Ticket {ticket_id}: rated_at anterior ao offered_at."
            )

    if len(ticket["tags"]) != len(set(ticket["tags"])):
        raise ValueError(
            f"Ticket {ticket_id}: possui tags duplicadas."
        )


def generate_dataset(
    *,
    count: int,
    customer_count: int,
    start_id: int,
    master_seed: str,
    anchor_at: datetime,
) -> list[dict[str, Any]]:
    if count <= 0:
        raise ValueError("--count deve ser maior que zero.")

    if customer_count <= 0:
        raise ValueError("--customers deve ser maior que zero.")

    if count < customer_count * 2:
        raise ValueError(
            "--count deve permitir pelo menos dois tickets por cliente. "
            f"Mínimo para {customer_count} clientes: {customer_count * 2}."
        )

    tickets: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    seen_fingerprints: set[str] = set()

    for offset in range(count):
        ticket_id = start_id + offset

        if ticket_id in seen_ids:
            raise RuntimeError(f"ticket_id duplicado: {ticket_id}")

        ticket = generate_ticket(
            master_seed=master_seed,
            ticket_id=ticket_id,
            offset=offset,
            start_id=start_id,
            customer_count=customer_count,
            anchor_at=anchor_at,
        )

        validate_ticket(ticket)
        fingerprint = semantic_fingerprint(ticket)

        if fingerprint in seen_fingerprints:
            raise RuntimeError(
                "Ticket semanticamente duplicado detectado: "
                f"{ticket_id} / {ticket['subject']}"
            )

        seen_ids.add(ticket_id)
        seen_fingerprints.add(fingerprint)
        tickets.append(ticket)

    return tickets


def validate_dataset(
    tickets: list[dict[str, Any]],
    expected_count: int,
    customer_count: int,
) -> dict[str, Any]:
    if len(tickets) != expected_count:
        raise RuntimeError(
            f"Quantidade inválida: esperado={expected_count}, "
            f"obtido={len(tickets)}."
        )

    ids = {ticket["ticket_id"] for ticket in tickets}
    if len(ids) != expected_count:
        raise RuntimeError("Existem ticket_ids duplicados.")

    fingerprints = {
        semantic_fingerprint(ticket)
        for ticket in tickets
    }
    if len(fingerprints) != expected_count:
        raise RuntimeError(
            "Existem tickets semanticamente duplicados."
        )

    customer_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    rating_counts: Counter[str] = Counter()
    agent_ids: set[int] = set()
    tags: set[str] = set()

    for ticket in tickets:
        validate_ticket(ticket)

        customer_counts[ticket["requester_email"]] += 1
        status_counts[ticket["status"]] += 1
        priority_counts[ticket["priority"]] += 1
        rating_counts[
            ticket["satisfaction_rating"]["score"]
        ] += 1
        tags.update(ticket["tags"])

        if ticket["assignee_id"] is not None:
            agent_ids.add(ticket["assignee_id"])

    if len(customer_counts) != customer_count:
        raise RuntimeError(
            f"Clientes usados={len(customer_counts)}, "
            f"esperado={customer_count}."
        )

    clients_with_less_than_two = [
        email
        for email, count in customer_counts.items()
        if count < 2
    ]
    if clients_with_less_than_two:
        raise RuntimeError(
            "Existem clientes com menos de dois tickets."
        )

    if set(status_counts) != ALLOWED_STATUSES:
        raise RuntimeError(
            f"Nem todos os status foram utilizados: {dict(status_counts)}"
        )

    if set(priority_counts) != ALLOWED_PRIORITIES:
        raise RuntimeError(
            "Nem todas as prioridades foram utilizadas: "
            f"{dict(priority_counts)}"
        )

    if set(rating_counts) != ALLOWED_RATINGS:
        raise RuntimeError(
            f"Nem todos os ratings foram utilizados: {dict(rating_counts)}"
        )

    if len(agent_ids) != len(AGENTS):
        raise RuntimeError(
            f"Agentes usados={len(agent_ids)}, esperado={len(AGENTS)}."
        )

    if len(tags) < 50:
        raise RuntimeError(
            f"Apenas {len(tags)} tags distintas foram utilizadas."
        )

    return {
        "tickets": len(tickets),
        "customers": len(customer_counts),
        "agents": len(agent_ids),
        "distinct_tags": len(tags),
        "statuses": dict(status_counts),
        "priorities": dict(priority_counts),
        "ratings": dict(rating_counts),
    }


def write_json(
    output_path: Path,
    tickets: list[dict[str, Any]],
    compact: bool,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        if compact:
            json.dump(
                tickets,
                output_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        else:
            json.dump(
                tickets,
                output_file,
                ensure_ascii=False,
                indent=2,
            )
        output_file.write("\n")

    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera tickets mock determinísticos no formato JSON do desafio."
        )
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Quantidade de tickets. Padrão: {DEFAULT_COUNT}.",
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=DEFAULT_CUSTOMER_COUNT,
        help=(
            "Quantidade de clientes. Cada cliente deve receber ao menos "
            f"dois tickets. Padrão: {DEFAULT_CUSTOMER_COUNT}."
        ),
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=DEFAULT_START_ID,
        help=f"Primeiro ticket_id. Padrão: {DEFAULT_START_ID}.",
    )
    parser.add_argument(
        "--seed",
        default=DEFAULT_SEED,
        help=f"Master seed. Padrão: {DEFAULT_SEED}.",
    )
    parser.add_argument(
        "--anchor",
        default=DEFAULT_ANCHOR,
        help=(
            "Data máxima para geração dos tickets em ISO-8601. "
            f"Padrão: {DEFAULT_ANCHOR}."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Arquivo de saída. Padrão: {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Gera JSON sem indentação para reduzir o tamanho.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        anchor_at = parse_iso8601(args.anchor)

        tickets = generate_dataset(
            count=args.count,
            customer_count=args.customers,
            start_id=args.start_id,
            master_seed=args.seed,
            anchor_at=anchor_at,
        )

        summary = validate_dataset(
            tickets=tickets,
            expected_count=args.count,
            customer_count=args.customers,
        )

        digest = write_json(
            output_path=args.output,
            tickets=tickets,
            compact=args.compact,
        )

    except (ValueError, RuntimeError, OSError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(f"Arquivo: {args.output.resolve()}")
    print(f"SHA-256: {digest}")
    print(f"Generator version: {GENERATOR_VERSION}")
    print(f"Master seed: {args.seed}")
    print(f"Tickets: {summary['tickets']}")
    print(f"Clientes: {summary['customers']}")
    print(f"Agentes: {summary['agents']}")
    print(f"Tags distintas: {summary['distinct_tags']}")
    print(f"Status: {summary['statuses']}")
    print(f"Prioridades: {summary['priorities']}")
    print(f"Avaliações: {summary['ratings']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
