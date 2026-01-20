from __future__ import annotations

import logging
from typing import Any, Dict

from langchain_core.tools import tool

from app.ai.tools.shared import _compact_agendamento, _compact_response, _tool_result
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


@tool
def listar_agendamentos_tool(
    dataInicio: str,
    dataFim: str,
    page: int | None = 1,
    pageSize: int | None = 50,
) -> str:
    """
    Lista todos os agendamentos passando os paramentros de roda data de inicio, data do fim e id do cliente
    """
    params: Dict[str, Any] = {
        "dataInicio": dataInicio,
        "dataFim": dataFim,
        "page": page,
        "pageSize": pageSize,
    }

    logger.info("[tool] listar_agendamentos_tool params=%s", params)
    http = get_http_client()
    resp = http.get("/agendamentos", params=params)
    return _tool_result(_compact_response(resp, _compact_agendamento))
