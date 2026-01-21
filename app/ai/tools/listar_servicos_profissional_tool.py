from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.ai.tools.shared import _compact_response, _compact_service, _tool_result
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


@tool
def listar_servicos_profissional_tool(
    profissionalId: int,
    page: int = 1,
    pageSize: int = 50,
    incluirValor: bool = False,
) -> str:
    """Lista os serviços oferecidos por um profissional específico."""
    params = {
        "page": page,
        "pageSize": pageSize,
    }

    logger.info(
        "[tool] listar_servicos_profissional_tool profissionalId=%s page=%s pageSize=%s",
        profissionalId,
        page,
        pageSize,
    )

    if profissionalId is None:
        logger.warning("[tool] listar_servicos_profissional_tool missing profissionalId")
        return _tool_result({"error": "Profissional não informado"})

    http = get_http_client()
    resp = http.get(f"/profissionais/{profissionalId}/servicos", params=params)
    return _tool_result(
        _compact_response(resp, lambda item: _compact_service(item, incluirValor))
    )
