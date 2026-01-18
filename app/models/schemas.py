from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------- Chat / Messages ----------

class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatInput(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)


class RunConfig(BaseModel):
    configurable: Optional[Dict[str, Any]] = None


# ---------- Threads ----------

class ThreadObj(BaseModel):
    thread_id: str
    created_at: Optional[datetime] = None
    values: Dict[str, Any] = Field(default_factory=dict)


class ThreadSearchRequest(BaseModel):
    limit: Optional[int] = 50


# ---------- User Profiles ----------

class UserProfileCreate(BaseModel):
    customer_profile: int
    name: Optional[str] = None
    phone: Optional[str] = None


class UserProfileObj(BaseModel):
    customer_profile: int
    name: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserProfileThreadUpdate(BaseModel):
    thread_id: str


# ---------- Runs ----------

class RunRequest(BaseModel):
    input: ChatInput
    config: Optional[RunConfig] = None


class RunResult(BaseModel):
    messages: List[Dict[str, Any]] = Field(default_factory=list)


class RunResponse(BaseModel):
    result: RunResult
