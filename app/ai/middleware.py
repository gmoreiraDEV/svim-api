from __future__ import annotations

import json
from typing import Callable, Optional, List, Any, TYPE_CHECKING

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_openai import ChatOpenAI

if TYPE_CHECKING:
    from app.ai.agent import AgentConfig


def _dbg(cfg: AgentConfig, *args) -> None:
    if cfg.debug_agent_logs:
        try:
            print(*args, flush=True)
        except Exception:
            pass


def extract_settings_from_messages(messages) -> Optional[str]:
    """
    Lê a última SystemMessage com JSON {"type":"settings"} e retorna model_name.
    """
    model_name: Optional[str] = None

    for msg in reversed(messages or []):
        try:
            if getattr(msg, "type", None) != "system":
                continue
            content = getattr(msg, "content", None)
            if not isinstance(content, str):
                continue
            data = json.loads(content)
            if isinstance(data, dict) and data.get("type") == "settings":
                if isinstance(data.get("model"), str) and data["model"].strip():
                    model_name = data["model"].strip()
                break
        except Exception:
            continue

    return model_name


def strip_settings_messages(messages):
    """
    Remove mensagens SystemMessage com JSON {"type":"settings"} antes do LLM.
    """
    cleaned = []
    for msg in messages or []:
        try:
            if getattr(msg, "type", None) == "system":
                content = getattr(msg, "content", None)
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict) and data.get("type") == "settings":
                            continue
                    except Exception:
                        pass
        except Exception:
            pass
        cleaned.append(msg)
    return cleaned


class DynamicSettingsMiddleware(AgentMiddleware):
    """
    Troca dinâmica de modelo por requisição.

    Fonte de verdade (precedência):
      1) runtime.config.configurable.model_name
      2) runtime.context.model_name
      3) SystemMessage {"type":"settings", ...}
      4) defaults do AgentConfig
    """

    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg

    def _resolve_prefs(self, request: ModelRequest) -> Tuple[Optional[str], List[Any]]:
        messages = getattr(request, "messages", None) or []
        model_name = extract_settings_from_messages(messages)

        # runtime overrides
        runtime = getattr(request, "runtime", None)
        try:
            runtime_cfg = getattr(runtime, "config", None)
            if isinstance(runtime_cfg, dict):
                cfg = runtime_cfg.get("configurable", {}) or {}
                if isinstance(cfg.get("model_name"), str) and cfg["model_name"].strip():
                    model_name = cfg["model_name"].strip()

            ctx = getattr(runtime, "context", None)
            if isinstance(ctx, dict):
                if isinstance(ctx.get("model_name"), str) and ctx["model_name"].strip():
                    model_name = ctx["model_name"].strip()
        except Exception:
            pass

        tools = list(getattr(request, "tools", []) or [])
        return model_name, tools

    def _apply_model_tools_messages(self, request: ModelRequest, *, model_name: Optional[str], tools):
        # Messages: strip settings
        cleaned = strip_settings_messages(getattr(request, "messages", []) or [])

        # Model: if override, create new ChatOpenAI using AgentConfig (no env)
        new_model = getattr(request, "model", None)
        if model_name:
            try:
                new_model = ChatOpenAI(
                    model=model_name,
                    temperature=self.cfg.temperature,
                    openai_api_key=self.cfg.api_key,
                    openai_api_base=self.cfg.base_url,
                    max_tokens=self.cfg.max_output_tokens,
                )
            except Exception as e:
                _dbg(self.cfg, f"[SETTINGS] erro ao aplicar modelo '{model_name}': {e}")

        request.model = new_model
        request.messages = cleaned
        request.tools = tools

        _dbg(
            self.cfg,
            f"[MIDDLEWARE] model={model_name or 'default'} tools={len(tools)}"
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        model_name, tools = self._resolve_prefs(request)
        self._apply_model_tools_messages(request, model_name=model_name, tools=tools)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        model_name, tools = self._resolve_prefs(request)
        self._apply_model_tools_messages(request, model_name=model_name, tools=tools)
        return await handler(request)
