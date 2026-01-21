from __future__ import annotations

from contextlib import AsyncExitStack

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.settings import get_settings
from app.ai.agent import AgentConfig, build_graph
from app.ai.tools import (
    consultar_disponibilidade_tool,
    criar_agendamento_tool,
    listar_agendamentos_tool,
    listar_profissionais_tool,
    listar_servicos_profissional_tool,
    listar_servicos_tool,
)


def build_agent_graph(checkpointer: BaseCheckpointSaver):
    settings = get_settings()
    use_openrouter = settings.use_openrouter
    provider_name = "openrouter" if use_openrouter else "openai"
    api_key = (settings.openrouter_api_key or "") if use_openrouter else (settings.openai_api_key or "")
    base_url = settings.openrouter_base_url if use_openrouter else settings.openai_base_url
    cfg = AgentConfig(
        debug_agent_logs=settings.debug_agent_logs,
        provider_name=provider_name,
        api_key=api_key,
        base_url=base_url,
        max_output_tokens=settings.openrouter_max_tokens,
        default_model_name=settings.effective_model_name,
    )
    tools = [
        consultar_disponibilidade_tool,
        criar_agendamento_tool,
        listar_agendamentos_tool,
        listar_profissionais_tool,
        listar_servicos_profissional_tool,
        listar_servicos_tool,
    ]
    return build_graph(cfg=cfg, checkpointer=checkpointer, tools=tools)


async def open_checkpointer(database_url: str) -> tuple[AsyncExitStack, AsyncPostgresSaver]:
    """Cria e mantém um AsyncPostgresSaver ativo até o fechamento."""
    stack = AsyncExitStack()
    cm = AsyncPostgresSaver.from_conn_string(database_url)
    saver = await stack.enter_async_context(cm)
    return stack, saver
