"""API FastAPI do BiblioBot-UFMA."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.engine import get_rag_engine


# [Rastreabilidade: source 31, 43, 58]
# Justificativa: Memoria curta preserva contexto da entrevista de referencia,
# apoiando interpretacao progressiva da necessidade informacional.
class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=2)
    subjects: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    recommendations: list[dict[str, Any]]
    transparency: str
    interview_prompt: str
    intent: str


app = FastAPI(title="BiblioBot-UFMA", version="0.1.0")

SESSION_MEMORY: dict[str, dict[str, Any]] = {}


# [Rastreabilidade: Belkin - Estado Anomalo do Conhecimento]
# Justificativa: O endpoint direciona consultas vagas para clarificacao antes
# de qualquer tentativa de busca ou recomendacao.
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    user_state = SESSION_MEMORY.setdefault(request.user_id, {"history": []})
    user_state["history"].append(request.message)
    known_context = " | ".join(user_state["history"][-3:])

    resultado = get_rag_engine().responder(request.message, k=5)

    interview_prompt = (
        "Contexto da interacao: "
        + (known_context or "nenhum")
        + "\n"
        + "Entrevista de referencia simulada conforme mediacao informacional."
    )

    recommendations = [
        {
            "id": item.get("metadata", {}).get("id", ""),
            "titulo": item.get("metadata", {}).get("titulo", ""),
            "autor": item.get("metadata", {}).get("autor", ""),
            "localizacao": item.get("metadata", {}).get("localizacao", ""),
            "data_aquisicao": item.get("metadata", {}).get("data_aquisicao", ""),
            "distancia": item.get("distancia", 0.0),
        }
        for item in resultado.context_items
    ]

    return ChatResponse(
        answer=resultado.answer,
        recommendations=recommendations,
        transparency=resultado.transparency_note,
        interview_prompt=interview_prompt,
        intent=resultado.intent,
    )


# [Rastreabilidade: source 21]
# Justificativa: Endpoint de saude para operacao e monitoramento em ambiente dockerizado.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bibliobot-ufma"}
