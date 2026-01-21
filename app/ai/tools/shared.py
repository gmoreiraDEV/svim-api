from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable

from app.ai.aliases import SERVICE_ALIASES
from app.ai.stop_words import STOPWORDS


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _normalize_service_term(term: str | None) -> str | None:
    if not term:
        return term
    text = _strip_accents(term.lower())
    text = re.sub(r"[^a-z0-9\\s]", " ", text)
    tokens = [t for t in text.split() if t and t not in STOPWORDS]
    if not tokens:
        return term
    normalized = " ".join(tokens)
    return SERVICE_ALIASES.get(normalized, normalized)


def _trim_fields(item: Dict[str, Any], allowed_keys: Iterable[str]) -> Dict[str, Any]:
    """Keep only whitelisted keys from a dict."""
    return {
        key: item[key]
        for key in allowed_keys
        if key in item and item[key] not in (None, "", [])
    }


def _compact_service(item: Dict[str, Any], include_valor: bool = False) -> Dict[str, Any]:
    keys = ["id", "nome", "categoria", "duracaoEmMinutos"]
    if include_valor:
        keys.append("valor")
    service = _trim_fields(item, keys)
    if include_valor and "valor" not in service and "preco" in item:
        service["valor"] = item.get("preco")
    if "descricao" in item:
        service["descricao"] = str(item["descricao"])[:160]
    return service


def _compact_professional(item: Dict[str, Any]) -> Dict[str, Any]:
    return _trim_fields(
        item,
        (
            "id",
            "nome",
            "apelido",
            "categoria",
            "especialidades",
        ),
    )


def _compact_agendamento(item: Dict[str, Any]) -> Dict[str, Any]:
    agendamento = _trim_fields(
        item,
        ("id", "dataHoraInicio", "dataHoraFim", "duracaoEmMinutos", "valor", "status"),
    )
    if isinstance(item.get("servico"), dict):
        agendamento["servico"] = _compact_service(item["servico"])
    if isinstance(item.get("profissional"), dict):
        agendamento["profissional"] = _compact_professional(item["profissional"])
    if isinstance(item.get("cliente"), dict):
        agendamento["cliente"] = _trim_fields(item["cliente"], ("id", "nome"))
    return agendamento


def _compact_response(
    response: Dict[str, Any],
    data_mapper: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    """Remove campos desnecessários das respostas para economizar tokens."""
    if not isinstance(response, dict):
        return response

    if response.get("error"):
        return response

    compacted: Dict[str, Any] = {}

    data = response.get("data")
    if isinstance(data, list):
        compacted["data"] = [data_mapper(item) for item in data]
    elif isinstance(data, dict):
        compacted["data"] = data_mapper(data)
    else:
        compacted["data"] = data

    for meta_key in ("page", "pageSize", "total", "message"):
        if meta_key in response:
            compacted[meta_key] = response[meta_key]

    return compacted


def _tool_result(payload: Dict[str, Any]) -> str:
    """Serializa o payload em JSON compacto para ser usado pelo agente."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
