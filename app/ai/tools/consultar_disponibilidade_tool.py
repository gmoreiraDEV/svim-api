from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from app.ai.tools.shared import _tool_result, _normalize_service_term
from app.utils.http_client import get_http_client

logger = logging.getLogger(__name__)

# -----------------------------
# Config simples (v1)
# -----------------------------
DEFAULT_OPEN_TIME = time(9, 0)
DEFAULT_CLOSE_TIME = time(18, 0)
SLOT_STEP_MIN = 30

# Se quiser ignorar domingo:
IGNORE_WEEKDAY = {6}  # 0=Mon ... 6=Sun (domingo)


# -----------------------------
# Helpers
# -----------------------------
def _parse_dt(dt_str: str) -> datetime:
    # Suporta ISO com timezone (ex: 2026-01-20T14:00:00-03:00)
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

def _to_iso(dt: datetime) -> str:
    return dt.isoformat()

def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end

def _day_start_end(dt: datetime) -> Tuple[datetime, datetime]:
    # faixa do dia em timezone do dt
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end

def _build_day_work_window(day: datetime) -> Tuple[datetime, datetime]:
    start = day.replace(hour=DEFAULT_OPEN_TIME.hour, minute=DEFAULT_OPEN_TIME.minute, second=0, microsecond=0)
    end = day.replace(hour=DEFAULT_CLOSE_TIME.hour, minute=DEFAULT_CLOSE_TIME.minute, second=0, microsecond=0)
    return start, end

def _round_up_to_step(dt: datetime, step_min: int) -> datetime:
    # arredonda pra cima para o próximo step (ex: 14:07 -> 14:30)
    minute = (dt.minute // step_min) * step_min
    rounded = dt.replace(minute=minute, second=0, microsecond=0)
    if rounded < dt.replace(second=0, microsecond=0):
        rounded += timedelta(minutes=step_min)
    return rounded

def _safe_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


# -----------------------------
# HTTP helpers (sem tool->tool)
# -----------------------------
def _http_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    http = get_http_client()
    return http.get(path, params=params)

def _fetch_servicos(nome: Optional[str], somente_visiveis: Optional[bool], incluir_valor: bool) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"page": 1, "pageSize": 200}
    if nome:
        params["nome"] = _normalize_service_term(nome)
    if somente_visiveis is not None:
        params["somenteVisiveisCliente"] = bool(somente_visiveis)

    resp = _http_get("/servicos", params=params)
    data = resp.get("data", []) or []
    # compact básico (mantém campos necessários)
    out = []
    for s in data:
        out.append({
            "id": s.get("id"),
            "nome": s.get("nome"),
            "descricao": s.get("descricao"),
            "categoria": s.get("categoria"),
            "duracaoEmMinutos": s.get("duracaoEmMinutos"),
            "preco": s.get("preco") if incluir_valor else None,
            "visivelParaCliente": s.get("visivelParaCliente"),
        })
    return out

def _fetch_profissionais() -> List[Dict[str, Any]]:
    resp = _http_get("/profissionais", params={"page": 1, "pageSize": 200})
    data = resp.get("data", []) or []
    return [{"id": p.get("id"), "nome": p.get("nome"), "apelido": p.get("apelido")} for p in data]

def _fetch_servicos_por_profissional(profissional_id: int, incluir_valor: bool) -> List[Dict[str, Any]]:
    resp = _http_get(f"/profissionais/{profissional_id}/servicos", params={"page": 1, "pageSize": 200})
    data = resp.get("data", []) or []
    out = []
    for s in data:
        out.append({
            "id": s.get("id"),
            "nome": s.get("nome"),
            "duracaoEmMinutos": s.get("duracaoEmMinutos"),
            "preco": s.get("preco") if incluir_valor else None,
            "visivelParaCliente": s.get("visivelParaCliente"),
        })
    return out

def _fetch_agendamentos(data_inicio_iso: str, data_fim_iso: str) -> List[Dict[str, Any]]:
    resp = _http_get("/agendamentos", params={
        "dataInicio": data_inicio_iso,
        "dataFim": data_fim_iso,
        "page": 1,
        "pageSize": 500
    })
    return resp.get("data", []) or []


# -----------------------------
# Matching do serviço (v1)
# -----------------------------
def _pick_service_by_id(services: List[Dict[str, Any]], servico_id: int) -> Optional[Dict[str, Any]]:
    for s in services:
        if s.get("id") == servico_id:
            return s
    return None

def _pick_service_by_term(services: List[Dict[str, Any]], term: str) -> Optional[Dict[str, Any]]:
    t = _normalize_service_term(term).lower().strip()
    if not t:
        return None

    # 1) match exato
    for s in services:
        if str(s.get("nome", "")).lower().strip() == t:
            return s

    # 2) contains
    contains = [s for s in services if t in str(s.get("nome", "")).lower()]
    if contains:
        # pega o mais curto (tende a ser o “mais específico”)
        contains.sort(key=lambda x: len(str(x.get("nome", ""))))
        return contains[0]

    # 3) fallback: palavras
    words = [w for w in t.split() if len(w) >= 3]
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for s in services:
        name = str(s.get("nome", "")).lower()
        score = sum(1 for w in words if w in name)
        if score > 0:
            scored.append((score, s))
    if scored:
        scored.sort(key=lambda x: (-x[0], len(str(x[1].get("nome", "")))))
        return scored[0][1]

    return None


# -----------------------------
# Disponibilidade (v1)
# -----------------------------
def _agendamento_interval(ag: Dict[str, Any]) -> Optional[Tuple[datetime, datetime]]:
    start_raw = ag.get("dataHoraInicio")
    dur = ag.get("duracaoEmMinutos")
    if not start_raw or dur is None:
        return None
    try:
        start = _parse_dt(start_raw)
        end = start + timedelta(minutes=int(dur))
        return start, end
    except Exception:
        return None

def _is_slot_free(
    slot_start: datetime,
    slot_end: datetime,
    agendamentos: List[Dict[str, Any]],
    profissional_id: int,
) -> bool:
    for ag in agendamentos:
        prof = (ag.get("profissional") or {}).get("id")
        if prof != profissional_id:
            continue
        itv = _agendamento_interval(ag)
        if not itv:
            continue
        ag_start, ag_end = itv
        if _overlap(slot_start, slot_end, ag_start, ag_end):
            return False
    return True

def _suggest_slots(
    base_dt: datetime,
    dias_busca: int,
    sugestoes: int,
    dur_min: int,
    profissionais: List[Dict[str, Any]],
    agendamentos: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    # varrer dias
    day_cursor = base_dt
    for _ in range(dias_busca):
        if day_cursor.weekday() in IGNORE_WEEKDAY:
            day_cursor = (day_cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            continue

        work_start, work_end = _build_day_work_window(day_cursor)
        # começa no "agora" arredondado (no primeiro dia) ou no inicio do expediente
        if day_cursor.date() == base_dt.date():
            cursor = _round_up_to_step(max(base_dt, work_start), SLOT_STEP_MIN)
        else:
            cursor = work_start

        while cursor + timedelta(minutes=dur_min) <= work_end:
            slot_start = cursor
            slot_end = cursor + timedelta(minutes=dur_min)

            # tenta achar algum profissional livre
            for p in profissionais:
                pid = p["id"]
                if _is_slot_free(slot_start, slot_end, agendamentos, pid):
                    suggestions.append({
                        "profissionalId": pid,
                        "profissionalNome": p.get("nome"),
                        "start": _to_iso(slot_start),
                        "end": _to_iso(slot_end),
                    })
                    break

            if len(suggestions) >= sugestoes:
                return suggestions

            cursor += timedelta(minutes=SLOT_STEP_MIN)

        day_cursor = (day_cursor + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return suggestions


@tool
def consultar_disponibilidade_tool(
    termoServico: str | None = None,
    servicoId: int | None = None,
    profissionalId: int | None = None,
    dataHoraDesejada: str | None = None,
    somenteVisiveisCliente: bool = True,
    diasBusca: int = 14,
    sugestoes: int = 3,
    incluirValor: bool = False,
) -> str:
    """
    Resolve serviço + profissionais aptos + checa disponibilidade do horário desejado e sugere próximos slots.
    """
    logger.info(
        "[tool] consultar_disponibilidade_tool termoServico=%s servicoId=%s profissionalId=%s dataHoraDesejada=%s",
        termoServico,
        servicoId,
        profissionalId,
        dataHoraDesejada,
    )

    # 1) serviços (filtra por termo quando possível)
    services = _fetch_servicos(nome=termoServico, somente_visiveis=somenteVisiveisCliente, incluir_valor=incluirValor)
    if not services:
        return _tool_result({"error": "Nenhum serviço encontrado"})

    # 2) resolve serviço
    chosen_service = None
    if servicoId is not None:
        chosen_service = _pick_service_by_id(services, int(servicoId))
    if chosen_service is None and termoServico:
        chosen_service = _pick_service_by_term(services, termoServico)

    if chosen_service is None:
        # devolve candidatos pro agente pedir confirmação
        return _tool_result({
            "needsClarification": True,
            "message": "Não consegui identificar com certeza o serviço. Sugira ao cliente escolher um.",
            "serviceCandidates": services[:10],
        })

    dur_min = _safe_int(chosen_service.get("duracaoEmMinutos")) or 30

    # 3) profissionais (geral) + filtra os que fazem o serviço
    all_prof = _fetch_profissionais()
    if not all_prof:
        return _tool_result({"error": "Nenhum profissional encontrado"})

    # para cada profissional, busca serviços e vê se tem o service id
    eligible: List[Dict[str, Any]] = []
    eligible_ids = set()

    # se o cliente já escolheu profissional, tentamos só ele primeiro (evita N chamadas)
    prof_to_check = []
    if profissionalId is not None:
        prof_to_check = [p for p in all_prof if p.get("id") == int(profissionalId)]
        if not prof_to_check:
            prof_to_check = []
    if not prof_to_check:
        prof_to_check = all_prof

    for p in prof_to_check:
        pid = p["id"]
        servs = _fetch_servicos_por_profissional(pid, incluir_valor=incluirValor)
        if any(s.get("id") == chosen_service["id"] for s in servs):
            eligible.append(p)
            eligible_ids.add(pid)

    if not eligible:
        return _tool_result({
            "service": chosen_service,
            "eligibleProfessionals": [],
            "requested": None,
            "suggestedSlots": [],
            "message": "Nenhum profissional realiza esse serviço no momento.",
        })

    # 4) agendamentos para janela de busca
    base_dt = _parse_dt(dataHoraDesejada) if dataHoraDesejada else datetime.now().astimezone()
    window_start = base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=max(1, int(diasBusca)))

    ags = _fetch_agendamentos(_to_iso(window_start), _to_iso(window_end))

    # 5) checar slot desejado (se veio)
    requested = None
    if dataHoraDesejada:
        req_start = _parse_dt(dataHoraDesejada)
        req_end = req_start + timedelta(minutes=dur_min)

        if profissionalId is not None:
            ok = _is_slot_free(req_start, req_end, ags, int(profissionalId))
            requested = {
                "requestedStart": _to_iso(req_start),
                "requestedEnd": _to_iso(req_end),
                "available": ok,
                "checkedProfessionalId": int(profissionalId),
            }
        else:
            # se não tem profissional escolhido, basta existir ao menos um livre
            ok_any = False
            ok_pid = None
            for p in eligible:
                if _is_slot_free(req_start, req_end, ags, p["id"]):
                    ok_any = True
                    ok_pid = p["id"]
                    break
            requested = {
                "requestedStart": _to_iso(req_start),
                "requestedEnd": _to_iso(req_end),
                "available": ok_any,
                "suggestedProfessionalId": ok_pid,
            }

    # 6) sugestões: se não veio data, ou se veio mas não está disponível
    need_suggest = (requested is None) or (requested is not None and requested.get("available") is False)
    suggested_slots: List[Dict[str, Any]] = []
    if need_suggest:
        # se o cliente escolheu profissional, sugerimos só com ele
        if profissionalId is not None:
            eligible_for_suggest = [p for p in eligible if p["id"] == int(profissionalId)] or eligible
        else:
            eligible_for_suggest = eligible

        suggested_slots = _suggest_slots(
            base_dt=base_dt,
            dias_busca=int(diasBusca),
            sugestoes=int(sugestoes),
            dur_min=dur_min,
            profissionais=eligible_for_suggest,
            agendamentos=ags,
        )

    return _tool_result({
        "service": chosen_service,
        "eligibleProfessionals": eligible[:10],  # limita pra não explodir tokens
        "requested": requested,
        "suggestedSlots": suggested_slots,
        "meta": {
            "duracaoEmMinutos": dur_min,
            "diasBusca": int(diasBusca),
            "slotStepMin": SLOT_STEP_MIN,
            "openTime": DEFAULT_OPEN_TIME.strftime("%H:%M"),
            "closeTime": DEFAULT_CLOSE_TIME.strftime("%H:%M"),
        }
    })
