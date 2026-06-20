"""Integração Evolution API + WhatsApp para o BiblioBot-UFMA.

Este módulo concentra a comunicação de entrada/saída do fluxo WhatsApp:
- recebe webhooks do Evolution API;
- consulta o motor RAG/LLM local;
- envia a resposta de volta para a Evolution API.

Mantém a aplicação principal desacoplada e permite testes isolados.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

try:  # pragma: no cover - optional for standalone client testing
    from fastapi import APIRouter
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    APIRouter = None

    class BaseModel:  # type: ignore[override]
        pass

    def Field(default: Any = None, **_: Any) -> Any:  # type: ignore[override]
        return default

from app.engine import get_rag_engine


logger = logging.getLogger(__name__)


class EvolutionWebhookRequest(BaseModel):
    """Payload mínimo aceito pelo webhook de entrada.

    O Evolution API pode enviar payloads mais ricos; para o fluxo do Bibliobot
    precisamos apenas do identificador do remetente e do texto.
    """

    sender_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    callback_url: str | None = None


@dataclass
class EvolutionAPIConfig:
    base_url: str
    api_key: str
    instance_name: str
    timeout: float


def get_evolution_config() -> EvolutionAPIConfig:
    """Lê a configuração a partir das variáveis de ambiente.

    Variáveis aceitas:
    - EVOLUTION_BASE_URL: URL do servidor Evolution API
    - EVOLUTION_API_KEY: chave de autenticação
    - EVOLUTION_INSTANCE_NAME: nome da instância WhatsApp
    - EVOLUTION_TIMEOUT: timeout HTTP em segundos
    """

    return EvolutionAPIConfig(
        base_url=os.getenv("EVOLUTION_BASE_URL", os.getenv("EVOLUTION_API_URL", "http://evolution-api:8080")),
        api_key=os.getenv("EVOLUTION_API_KEY", os.getenv("WHATSAPP_API_TOKEN", "")),
        instance_name=os.getenv("EVOLUTION_INSTANCE_NAME", "bibliobot"),
        timeout=float(os.getenv("EVOLUTION_TIMEOUT", os.getenv("HTTP_TIMEOUT", "20"))),
    )


class EvolutionAPIClient:
    """Cliente simples para envio de texto via Evolution API."""

    def __init__(self, config: EvolutionAPIConfig | None = None) -> None:
        self.config = config or get_evolution_config()

    def send_text_message(self, number: str, text: str) -> dict[str, Any] | None:
        endpoint = f"{self.config.base_url.rstrip('/')}/message/sendText/{self.config.instance_name}"
        payload = {
            "number": number,
            "options": {
                "delay": 1200,
                "presence": "composing",
            },
            "text": text,
        }

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["apikey"] = self.config.api_key

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=self.config.timeout)
            response.raise_for_status()
            logger.info("Evolution API: mensagem enviada para %s", number)
            try:
                return response.json()
            except Exception:
                return {"raw": response.text}
        except requests.RequestException as exc:
            logger.error("Evolution API: erro ao enviar mensagem para %s: %s", number, exc)
            return None


def build_evolution_router() -> APIRouter:
    """Cria um router FastAPI com webhook de entrada para Evolution/WhatsApp."""

    if APIRouter is None:
        raise RuntimeError("FastAPI/Pydantic não estão disponíveis neste ambiente.")

    router = APIRouter(prefix="/webhook", tags=["evolution"])

    @router.post("/evolution")
    def evolution_webhook(req: EvolutionWebhookRequest) -> dict[str, str]:
        """Recebe a mensagem do WhatsApp, consulta o BiblioBot e devolve a resposta."""

        resultado = get_rag_engine().responder(req.message, k=int(os.getenv("MAX_RECOMMENDATIONS", "5")))
        reply_text = resultado.answer

        client = EvolutionAPIClient()

        # Prioridade: callback_url explícito > envio direto para a instância Evolution
        if req.callback_url:
            try:
                headers = {"Content-Type": "application/json"}
                if client.config.api_key:
                    headers["apikey"] = client.config.api_key
                requests.post(
                    req.callback_url,
                    json={"recipient": req.sender_id, "message": reply_text},
                    headers=headers,
                    timeout=client.config.timeout,
                )
            except requests.RequestException as exc:
                logger.error("Webhook callback falhou: %s", exc)
        else:
            client.send_text_message(req.sender_id, reply_text)

        return {"status": "ok"}

    return router


__all__ = [
    "EvolutionAPIClient",
    "EvolutionWebhookRequest",
    "EvolutionAPIConfig",
    "get_evolution_config",
    "build_evolution_router",
]
