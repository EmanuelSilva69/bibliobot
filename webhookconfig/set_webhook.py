"""Configura o webhook da Evolution para apontar para o FastAPI do BiblioBot.

Execute uma vez depois que a Evolution e o backend estiverem no ar.
"""

from __future__ import annotations

import os

import requests


BASE_URL = os.getenv("EVOLUTION_BASE_URL", "http://localhost:8088").rstrip("/")
API_KEY = os.getenv("EVOLUTION_API_KEY", "evolution-test-token")
INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "bibliobot")
WEBHOOK_URL = os.getenv("BIBLIOBOT_WEBHOOK_URL", "http://bibliobot:8000/webhook")


def set_webhook() -> None:
    url = f"{BASE_URL}/webhook/set/{INSTANCE_NAME}"
    headers = {
        "Content-Type": "application/json",
        "apikey": API_KEY,
    }
    payload = {
        "webhook": {
            "enabled": True,
            "url": WEBHOOK_URL,
            "byEvents": False,
            "base64": False,
            "events": ["MESSAGES_UPSERT"],
        }
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    print("[+] Webhook configurado com sucesso!")
    try:
        print(response.json())
    except Exception:
        print(response.text)


if __name__ == "__main__":
    try:
        set_webhook()
    except requests.RequestException as exc:
        print(f"[-] Erro ao configurar webhook: {exc}")