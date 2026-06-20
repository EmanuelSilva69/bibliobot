"""Teste de ponta a ponta da ponte Evolution API <-> BiblioBot.

Modo padrão:
- sobe um servidor HTTP mock da Evolution API em localhost;
- testa o envio de mensagem pelo EvolutionAPIClient.

Opcionalmente, se BIBLIOBOT_URL estiver definido, também testa o webhook
`POST /webhook/evolution` da aplicação em execução.
"""

from __future__ import annotations

import json
import os
import threading
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import requests


# Ensure the project root is importable when the script runs directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evolution_client import EvolutionAPIClient, EvolutionAPIConfig


class _MockEvolutionHandler(BaseHTTPRequestHandler):
    captured: list[dict[str, Any]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body}

        self.__class__.captured.append({"path": self.path, "payload": payload, "headers": dict(self.headers)})
        response = {"status": "ok", "path": self.path, "received": payload}
        encoded = json.dumps(response).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run_mock_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 19090), _MockEvolutionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, "http://127.0.0.1:19090"


def test_client(mock_base_url: str) -> None:
    client = EvolutionAPIClient(
        EvolutionAPIConfig(
            base_url=mock_base_url,
            api_key="test-key",
            instance_name="bibliobot",
            timeout=10.0,
        )
    )
    result = client.send_text_message("5511999999999", "Olá do teste")
    assert result is not None, "EvolutionAPIClient não recebeu resposta do mock"
    assert _MockEvolutionHandler.captured, "O mock não recebeu nenhuma requisição"
    print("[OK] EvolutionAPIClient -> envio de mensagem validado")
    print(json.dumps(_MockEvolutionHandler.captured[-1], ensure_ascii=False, indent=2))


def test_webhook_if_available() -> None:
    bib_url = os.getenv("BIBLIOBOT_URL")
    if not bib_url:
        print("[SKIP] BIBLIOBOT_URL não definido; pulando teste do webhook")
        return

    payload = {
        "sender_id": "5511999999999",
        "message": "bibliografia academica sobre machine learning aplicado a bibliotecas universitarias",
        "callback_url": f"{os.getenv('EVOLUTION_WEBHOOK_CALLBACK', 'http://127.0.0.1:19090/api/messages')}",
    }
    response = requests.post(f"{bib_url.rstrip('/')}/webhook/evolution", json=payload, timeout=240)
    response.raise_for_status()
    print("[OK] Webhook /webhook/evolution -> status=200")
    print(response.text)


def main() -> int:
    server, mock_base_url = run_mock_server()
    try:
        test_client(mock_base_url)
        test_webhook_if_available()
        return 0
    finally:
        server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
