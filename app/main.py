"""API FastAPI do BiblioBot-UFMA."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from app.engine import get_rag_engine
from app.evolution_client import EvolutionAPIClient, build_evolution_router


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
app.include_router(build_evolution_router())
evolution_client = EvolutionAPIClient()

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


@app.post("/webhook")
async def receive_whatsapp_message(request: Request) -> dict[str, str]:
    """Recebe payload bruto da Evolution API e responde apenas mensagens novas."""

    payload = await request.json()

    event_type = str(payload.get("event", "")).lower()
    if event_type != "messages.upsert":
        return {"status": "ignorado", "motivo": "nao_e_mensagem_nova"}

    data = payload.get("data", {})
    key = data.get("key", {})
    message = data.get("message", {})

    remote_jid = str(key.get("remoteJid", ""))
    is_from_me = bool(key.get("fromMe", False))

    allowed_group = os.getenv("ALLOWED_GROUP_JID", "").strip()
    allowed_numbers_str = os.getenv("ALLOWED_NUMBERS", "").strip()
    allowed_numbers = [n.strip() for n in allowed_numbers_str.split(",") if n.strip()] if allowed_numbers_str else []

    if is_from_me or "status@broadcast" in remote_jid:
        return {"status": "ignorado", "motivo": "propria_mensagem_ou_status"}

    if "@g.us" in remote_jid:
        if allowed_group and remote_jid != allowed_group:
            print(f"[WEBHOOK] grupo ignorado (nao permitido): {remote_jid}")
            return {"status": "ignorado", "motivo": "grupo_nao_permitido"}
    else:
        if allowed_group:
            if remote_jid not in allowed_numbers:
                print(f"[WEBHOOK] privado ignorado (nao permitido): {remote_jid}")
                return {"status": "ignorado", "motivo": "numero_nao_permitido"}

    text_message = ""
    mentioned = False
    bot_jid = os.getenv("BOT_JID", "").strip()
    if isinstance(message, dict):
        if isinstance(message.get("extendedTextMessage"), dict):
            ext = message["extendedTextMessage"]
            text_message = str(ext.get("text", ""))
            mentioned_jids = ext.get("contextInfo", {}).get("mentionedJid", [])
            if bot_jid and remote_jid.endswith("@g.us"):
                mentioned = bot_jid in mentioned_jids
        elif isinstance(message.get("conversation"), str):
            text_message = message["conversation"]

    if not text_message:
        return {"status": "ignorado", "motivo": "sem_texto"}

    if remote_jid.endswith("@g.us") and not mentioned:
        if bot_jid:
            data_ctx = data.get("contextInfo", {})
            data_mentioned = data_ctx.get("mentionedJid", []) if isinstance(data_ctx, dict) else []
            mentioned = bool(data_mentioned)
            if not mentioned:
                if "@" in text_message:
                    mentioned = True

    if remote_jid.endswith("@g.us") and not mentioned:
        if bot_jid:
            print(f"[WEBHOOK] grupo ignorado (nao mencionado): {remote_jid}")
            return {"status": "ignorado", "motivo": "nao_mencionado"}

    numero_remetente = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")
    print(f"[WEBHOOK] event={event_type} | de={remote_jid} | texto={text_message}")
    print(f"[WEBHOOK] payload keys={list(payload.keys())} | data keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}")

    resultado = get_rag_engine().responder(text_message, k=int(os.getenv("MAX_RECOMMENDATIONS", "5")))
    resposta = (resultado.answer or "").strip()

    if not resposta:
        resposta = (
            "No momento nao consegui gerar uma resposta util. "
            "Tente reformular a pergunta com mais contexto."
        )

    print(f"[WEBHOOK] resposta enviada para {numero_remetente}: {resposta[:150]}...")
    evolution_client.send_text_message(numero_remetente, resposta)

    return {"status": "sucesso"}
