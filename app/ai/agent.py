from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional
from zoneinfo import ZoneInfo

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.ai.middleware import DynamicSettingsMiddleware
from app.ai.prompts import render_default_system_prompt


def _sp_today_str() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")


@dataclass(frozen=True)
class AgentConfig:
    # Logs
    debug_agent_logs: bool = False

    # Provider (OpenAI-compatible)
    provider_name: str = "openrouter"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"

    # Defaults (com override do Studio aplicado antes de criar o config)
    default_model_name: str = "google/gemini-2.5-flash"
    default_system_prompt: str = ""
    temperature: float = 0.2
    max_output_tokens: int = 2048

    # Summarization
    summary_model_name: str = "google/gemini-2.0-flash-001"
    max_tokens_before_summary: int = 10000
    messages_to_keep: int = 12

    @staticmethod
    def default_prompt() -> str:
        return render_default_system_prompt(today=_sp_today_str())


def _dbg(cfg: AgentConfig, *args) -> None:
    if cfg.debug_agent_logs:
        try:
            print(*args, flush=True)
        except Exception:
            pass


def create_agent_graph(
    *,
    cfg: AgentConfig,
    model_name: str,
    system_prompt: str,
    tools: Optional[Iterable[BaseTool]] = None,
    temperature: Optional[float] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
):
    """
    Factory: monta e retorna o agente (Runnable) pronto para LangGraph.
    """
    if not cfg.api_key:
        raise RuntimeError(f"API key do provedor '{cfg.provider_name}' não definida.")

    agent_tools: List[BaseTool] = list(tools or [])

    llm = ChatOpenAI(
        model=model_name,
        temperature=cfg.temperature if temperature is None else temperature,
        openai_api_key=cfg.api_key,
        openai_api_base=cfg.base_url,
        max_tokens=cfg.max_output_tokens,
    )

    _dbg(cfg, f"[AGENT] model={model_name} tools={len(agent_tools)}")

    middlewares = [
        DynamicSettingsMiddleware(cfg),
        SummarizationMiddleware(
            model=ChatOpenAI(
                model=cfg.summary_model_name,
                temperature=0.0,
                openai_api_key=cfg.api_key,
                openai_api_base=cfg.base_url,
                max_tokens=cfg.max_output_tokens,
            ),
            max_tokens_before_summary=cfg.max_tokens_before_summary,
            messages_to_keep=cfg.messages_to_keep,
        ),
    ]

    return create_agent(
        model=llm,
        tools=agent_tools,
        system_prompt=system_prompt,
        state_schema=AgentState,
        middleware=middlewares,
        checkpointer=checkpointer,
    )


def build_graph(
    *,
    cfg: AgentConfig,
    model_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    tools: Optional[Iterable[BaseTool]] = None,
    temperature: Optional[float] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
):
    """
    Helper: cria o grafo com defaults do config, permitindo overrides.
    """
    final_model = model_name or cfg.default_model_name
    final_prompt = system_prompt or (cfg.default_system_prompt or AgentConfig.default_prompt())
    return create_agent_graph(
        cfg=cfg,
        model_name=final_model,
        system_prompt=final_prompt,
        tools=tools,
        temperature=temperature,
        checkpointer=checkpointer,
    )
