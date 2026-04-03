"""Suite de smoke tests do BiblioBot-UFMA.

Executa validacoes funcionais da API em cinco cenarios-chave:
1) Health check.
2) Clarificacao de incerteza (Belkin/ASK).
3) Novidades do acervo.
4) Recomendacao com transparencia.
5) Falha educativa com orientacao humana.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class TestResult:
    name: str
    success: bool
    details: str


def post_chat(base_url: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    response = requests.post(f"{base_url}/chat", json=payload, timeout=60)
    data: dict[str, Any]
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}
    return response.status_code, data


def assert_contains(text: str, needles: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def test_health(base_url: str) -> TestResult:
    name = "health"
    try:
        response = requests.get(f"{base_url}/health", timeout=20)
        ok = response.status_code == 200
        payload = response.json() if ok else {}
        success = ok and payload.get("status") == "ok"
        details = f"status={response.status_code}, payload={payload}"
        return TestResult(name, success, details)
    except Exception as exc:
        return TestResult(name, False, f"erro: {exc}")


def test_clarificacao(base_url: str) -> TestResult:
    name = "clarificacao_incerteza"
    payload = {"user_id": "t1", "message": "IA", "subjects": [], "authors": []}
    try:
        status, data = post_chat(base_url, payload)
        answer = str(data.get("answer", ""))
        success = (
            status == 200
            and data.get("intent") == "clarificacao"
            and assert_contains(answer, ["pesquisa academica", "consulta rapida", "detalhar"])
        )
        return TestResult(name, success, f"status={status}, intent={data.get('intent')}")
    except Exception as exc:
        return TestResult(name, False, f"erro: {exc}")


def test_novidades(base_url: str) -> TestResult:
    name = "novidades_acervo"
    payload = {
        "user_id": "t2",
        "message": "quais as novidades do acervo?",
        "subjects": [],
        "authors": [],
    }
    try:
        status, data = post_chat(base_url, payload)
        recs = data.get("recommendations", [])
        has_date = bool(recs) and all("data_aquisicao" in item for item in recs)
        success = status == 200 and data.get("intent") == "novidades" and has_date
        return TestResult(name, success, f"status={status}, recs={len(recs)}")
    except Exception as exc:
        return TestResult(name, False, f"erro: {exc}")


def test_transparencia(base_url: str) -> TestResult:
    name = "recomendacao_transparente"
    payload = {
        "user_id": "t3",
        "message": "bibliografia academica sobre machine learning aplicado a bibliotecas universitarias",
        "subjects": ["inteligencia artificial"],
        "authors": [],
    }
    try:
        status, data = post_chat(base_url, payload)
        answer = str(data.get("answer", ""))
        transparency = str(data.get("transparency", ""))
        success = (
            status == 200
            and assert_contains(answer, ["nota", "recomendei", "criterio"])
            and assert_contains(transparency, ["similaridade", "metadados", "rag"])
        )
        return TestResult(name, success, f"status={status}, intent={data.get('intent')}")
    except Exception as exc:
        return TestResult(name, False, f"erro: {exc}")


def test_falha_educativa(base_url: str) -> TestResult:
    name = "falha_educativa"
    payload = {
        "user_id": "t4",
        "message": "xqzv wktr plyn jhbm",
        "subjects": [],
        "authors": [],
    }
    try:
        status, data = post_chat(base_url, payload)
        answer = str(data.get("answer", ""))
        success = status == 200 and assert_contains(
            answer,
            ["bibliotecario", "refine", "estrategia", "ufma"],
        )
        return TestResult(name, success, f"status={status}, intent={data.get('intent')}")
    except Exception as exc:
        return TestResult(name, False, f"erro: {exc}")


def run_all(base_url: str) -> list[TestResult]:
    return [
        test_health(base_url),
        test_clarificacao(base_url),
        test_novidades(base_url),
        test_transparencia(base_url),
        test_falha_educativa(base_url),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke tests do BiblioBot-UFMA")
    parser.add_argument("--base-url", default="http://localhost:18000", help="URL base da API")
    parser.add_argument("--json", action="store_true", help="Imprime resultado em JSON")
    args = parser.parse_args()

    results = run_all(args.base_url)
    passed = sum(1 for item in results if item.success)
    total = len(results)

    if args.json:
        payload = {
            "base_url": args.base_url,
            "passed": passed,
            "total": total,
            "results": [item.__dict__ for item in results],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Base URL: {args.base_url}")
        for item in results:
            status = "OK" if item.success else "FAIL"
            print(f"[{status}] {item.name} -> {item.details}")
        print(f"Resumo: {passed}/{total} testes aprovados")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
