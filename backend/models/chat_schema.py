"""Pydantic schemas for chat"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    type: str = "text"
    message: str
    data: dict | None = None
