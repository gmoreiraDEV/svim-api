from __future__ import annotations

import logging
from typing import Any, Dict

from langchain_core.tools import tool

from app.ai.tools.shared import (
    _compact_response,
    _compact_service,
    _normalize_service_term,
    _tool_result,
)
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


@tool
def listar_servicos_tool(
    nome: str | None = None,
    categoria: str | None = None,
    somenteVisiveisCliente: bool | None = None,
    page: int | None = 1,
    pageSize: int | None = 50,
    incluirValor: bool = False,
) -> str:
    """Lista serviços filtrando por nome, categoria e visibilidade."""
    params: Dict[str, Any] = {
        "page": page,
        "pageSize": pageSize,
    }

    if nome is not None:
        params["nome"] = _normalize_service_term(nome)

    if categoria is not None:
        params["categoria"] = _normalize_service_term(categoria)

    logger.info("[tool] listar_servicos_tool params=%s", params)
    if somenteVisiveisCliente is not None:
        params["somenteVisiveisCliente"] = bool(somenteVisiveisCliente)

    http = get_http_client()
    resp = http.get("/servicos", params=params)
    return _tool_result(
        _compact_response(resp, lambda item: _compact_service(item, incluirValor))
    )
