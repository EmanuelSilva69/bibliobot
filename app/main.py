"""API FastAPI do BiblioBot-UFMA."""

from __future__ import annotations

from typing import Any
import os

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.engine import (
    build_transparency_log,
    filter_relevant_recommendations,
    from_searxng_results,
    recommend_content,
)
from app.prompts import (
    BOT_PERSONA,
    TRANSPARENCY_TEMPLATE,
    build_answer_prompt,
    build_reference_interview_prompt,
)


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


app = FastAPI(title="BiblioBot-UFMA", version="0.1.0")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
MAX_RECOMMENDATIONS = int(os.getenv("MAX_RECOMMENDATIONS", "5"))
REQUEST_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))

SESSION_MEMORY: dict[str, dict[str, Any]] = {}


# [Rastreabilidade: source 43, 58, 95]
# Justificativa: Busca ampla e filtragem local para reduzir sobrecarga informacional.
async def query_searxng(query: str) -> list[dict[str, Any]]:
    params = {"q": query, "format": "json", "categories": "science"}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            payload = response.json()
        return payload.get("results", [])
    except Exception:
        return []


# [Rastreabilidade: source 31, 58, 74]
# Justificativa: LLM local apoia mediacao dialogica sem dependencia de API externa.
async def generate_llm_answer(prompt: str) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("response", "")
    except Exception:
        return (
            "Nao foi possivel consultar o LLM no momento. "
            "Use as recomendacoes abaixo como ponto de partida para a pesquisa."
        )


# [Rastreabilidade: source 31, 43, 58, 95]
# Justificativa: Fluxo principal implementa entrevista de referencia, recomendacao por
# metadados e explicacao transparente dos criterios utilizados.
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    user_state = SESSION_MEMORY.setdefault(request.user_id, {"history": []})
    user_state["history"].append(request.message)
    known_context = " | ".join(user_state["history"][-3:])

    interview_prompt = build_reference_interview_prompt(request.message, known_context)

    profile = {
        "query": request.message,
        "subjects": request.subjects,
        "authors": request.authors,
    }

    searx_results = await query_searxng(request.message)
    collection = from_searxng_results(searx_results)

    recommendations = recommend_content(profile, collection, limit=MAX_RECOMMENDATIONS)
    recommendations = filter_relevant_recommendations(recommendations, min_score=2.0)

    transparency_log = build_transparency_log(profile, len(recommendations), MAX_RECOMMENDATIONS)
    transparency_note = TRANSPARENCY_TEMPLATE.format(
        keywords=profile["query"],
        limit=MAX_RECOMMENDATIONS,
    )

    recommendation_summary = "\n".join(
        [
            f"- {item['metadata']['title']} (score={item['score']})"
            for item in recommendations[:MAX_RECOMMENDATIONS]
        ]
    ) or "Nenhum item com relevancia minima encontrado."

    answer_prompt = (
        f"Persona:\n{BOT_PERSONA}\n\n"
        f"{build_answer_prompt(request.message, recommendation_summary, transparency_note)}\n\n"
        f"Entrevista de referencia sugerida:\n{interview_prompt}"
    )

    llm_answer = await generate_llm_answer(answer_prompt)

    return ChatResponse(
        answer=llm_answer,
        recommendations=recommendations,
        transparency=transparency_log,
        interview_prompt=interview_prompt,
    )


# [Rastreabilidade: source 21]
# Justificativa: Endpoint de saude para operacao e monitoramento em ambiente dockerizado.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bibliobot-ufma"}
