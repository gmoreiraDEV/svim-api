from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.ai.tools.shared import _compact_professional, _compact_response, _tool_result
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


@tool
def listar_profissionais_tool(page: int = 1, pageSize: int = 50) -> str:
    """Lista profissionais disponíveis de forma paginada."""
    params = {
        "page": page,
        "pageSize": pageSize,
    }
    logger.info("[tool] listar_profissionais_tool params=%s", params)
    client = get_http_client()
    resp = client.get("/profissionais", params=params)
    return _tool_result(_compact_response(resp, _compact_professional))
