from __future__ import annotations

import logging

from langchain_core.tools import tool

from app.ai.tools.shared import _compact_agendamento, _compact_response, _tool_result
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)


@tool
def criar_agendamento_tool(
    servicoId: str,
    profissionalId: str,
    clienteId: str,
    dataHoraInicio: str,
    duracaoEmMinutos: str,
    valor: str,
    observacoes: str | None = None,
    confirmado: bool | None = None,
) -> str:
    """Cria um agendamento a partir dos dados fornecidos."""
    required_fields = [
        ("servicoId", servicoId),
        ("profissionalId", profissionalId),
        ("clienteId", clienteId),
        ("dataHoraInicio", dataHoraInicio),
        ("duracaoEmMinutos", duracaoEmMinutos),
        ("valor", valor),
    ]
    missing = [name for name, val in required_fields if val in (None, "", [])]
    if missing:
        logger.warning("[tool] criar_agendamento_tool missing=%s", missing)
        return _tool_result({"error": "ARGS_INVALIDOS", "missing": missing})

    if not str(profissionalId).isdigit():
        return _tool_result(
            {
                "error": "PROFISSIONAL_ID_INVALIDO",
                "message": "profissionalId deve ser numérico",
                "value": str(profissionalId),
            }
        )
    if not str(servicoId).isdigit():
        return _tool_result(
            {
                "error": "SERVICO_ID_INVALIDO",
                "message": "servicoId deve ser numérico",
                "value": str(servicoId),
            }
        )

    payload = {
        "servicoId": servicoId,
        "clienteId": clienteId,
        "profissionalId": profissionalId,
        "dataHoraInicio": dataHoraInicio,
        "duracaoEmMinutos": duracaoEmMinutos,
        "valor": valor,
        "observacoes": observacoes,
        "confirmado": True if confirmado is None else confirmado,
    }

    logger.info("[tool] criar_agendamento_tool payload=%s", payload)
    http = get_http_client()
    resp = http.post("/agendamentos", json=payload)
    return _tool_result(_compact_response(resp, _compact_agendamento))
