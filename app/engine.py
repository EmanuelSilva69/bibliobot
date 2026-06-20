"""Motor de integracao entre RAG e LLM local (Ollama)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import os
import re

import requests

from app.rag_core import SistemaRAG
from app.recommendation_engine import (
    DocumentMetadata,
    build_transparency_log,
    filter_relevant_recommendations,
    from_searxng_results,
    recommend_content,
)


# [Rastreabilidade: source 31, 43, 58, 74, 101]
# Justificativa: Prompt de sistema formaliza o papel de mediador informacional,
# aplica entrevista de referencia para consultas vagas e restringe recomendacao
# ao contexto recuperado pelo RAG, promovendo transparencia algoritmica.
SYSTEM_PROMPT = """
Voce e o BiblioBot-UFMA, assistente academico da UFMA.
Responda em portugues de forma direta e curta, SEM pensar passo a passo.

Regras:
1) Recomende somente obras do CONTEXTO RAG.
2) Responda em no maximo 3 frases.
3) PROIBIDO usar <think> ou cadeias de raciocinio. Responda na hora.
4) Nao invente dados fora do contexto.
5) Se nao houver itens, informe e peca refinamento.
""".strip()


@dataclass
class RespostaRAG:
    answer: str
    context_items: list[dict[str, Any]]
    transparency_note: str
    needs_clarification: bool
    intent: str = "busca"


# [Rastreabilidade: source 31, 43, 58]
# Justificativa: Heuristica simples identifica incerteza para acionar entrevista
# de referencia conforme mediacao informacional descrita no estudo.
def is_vague_question(user_query: str) -> bool:
    query = (user_query or "").strip().lower()
    if len(query.split()) <= 3:
        return True

    vague_markers = [
        "me indique livros",
        "quero livros",
        "preciso de livros",
        "qual livro",
        "tem material",
        "me ajuda",
    ]
    return any(marker in query for marker in vague_markers)


# [Rastreabilidade: source 46, 58, 95]
# Justificativa: A intencao de novidades operacionaliza orientacao e atualizacao
# de usuarios, com filtragem temporal do acervo.
def is_novidade_question(user_query: str) -> bool:
    query = (user_query or "").strip().lower()
    markers = ["novidade", "novidades", "livros recentes", "recentes", "mais novo", "atual"]
    return any(marker in query for marker in markers)


# [Rastreabilidade: Mediação de Informação - Almeida Júnior]
# Justificativa: Quando a recuperacao falha, a resposta deve orientar nova estrategia
# de busca e preservar a mediacao humana.
def build_educational_failure_message() -> str:
    return (
        "Nao encontrei itens suficientemente relevantes no acervo para essa consulta. "
        "Sugestao de estrategia: especifique tema, area, autor ou recorte temporal, e tente "
        "novamente com termos mais precisos. Se preferir, procure o bibliotecario da UFMA "
        "para apoio na definicao da necessidade informacional e na escolha das fontes."
    )


# [Rastreabilidade: source 58, 74, 101]
# Justificativa: Notas explicativas por item tornam o criterio de recomendacao auditavel.
def build_footnote(item: dict[str, Any], query: str) -> str:
    meta = item.get("metadata", {})
    assuntos = meta.get("assuntos", "")
    return (
        f"Recomendei este titulo porque ele compartilha descritores relacionados a sua busca "
        f"({query}) e apresenta aderencia tematica com os assuntos [{assuntos}]."
    )


# [Rastreabilidade: source 58, 95, 101]
# Justificativa: Evita recomendacao forçada sem evidencia minima de aderencia,
# reforcando transparencia e mitigando falso positivo na recuperacao automatizada.
def has_minimum_relevance_signal(item: dict[str, Any], query: str) -> bool:
    lexical_score = float(item.get("lexical_score", 0.0) or 0.0)
    if lexical_score > 0:
        return True

    meta = item.get("metadata", {})
    combined = " ".join(
        [
            str(meta.get("titulo", "")),
            str(meta.get("assuntos", "")),
            str(item.get("texto_indexado", "")),
        ]
    ).lower()

    terms = re.findall(r"[a-zA-Z0-9]+", (query or "").lower())
    if not terms:
        return False

    overlap = sum(1 for term in terms if term in combined)
    if overlap > 0:
        return True

    distance = item.get("distancia")
    if isinstance(distance, (int, float)):
        return float(distance) <= 1.5
    return True


# [Rastreabilidade: source 58, 74, 101]
# Justificativa: Registro anonimo apoia analise qualitativa da pesquisa sem expor dados pessoais.
def registrar_interacao_anonima(pergunta: str, resposta: str) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "interacoes_anonimas.log"
    timestamp = datetime.utcnow().isoformat(timespec="seconds")

    pergunta_limpa = re.sub(r"\s+", " ", (pergunta or "")).strip()
    resposta_limpa = re.sub(r"\s+", " ", (resposta or "")).strip()
    resposta_resumida = resposta_limpa[:500]

    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(f"{timestamp} | pergunta={pergunta_limpa} | resposta={resposta_resumida}\n")


# [Rastreabilidade: source 46, 58, 95]
# Justificativa: Contexto textual controlado para reduzir alucinacoes e manter
# recomendacoes aderentes ao acervo vetorizado.
def build_rag_context(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Sem itens relevantes no acervo para a consulta atual."

    partes: list[str] = []
    for idx, item in enumerate(items, start=1):
        meta = item.get("metadata", {})
        partes.append(
            "\n".join(
                [
                    f"Item {idx}",
                    f"ID: {meta.get('id', '')}",
                    f"Titulo: {meta.get('titulo', '')}",
                    f"Autor: {meta.get('autor', '')}",
                    f"Assuntos: {meta.get('assuntos', '')}",
                    f"Localizacao: {meta.get('localizacao', '')}",
                    f"Distancia vetorial: {item.get('distancia', 0.0):.4f}",
                ]
            )
        )
    return "\n\n".join(partes)


# [Rastreabilidade: source 58, 74, 101]
# Justificativa: Chamada ao LLM local com prompt fechado e transparencia sobre
# criterios reduz risco etico e reforca auditabilidade.
def call_ollama(ollama_url: str, model: str, system: str, prompt: str, timeout: float = 30.0) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 800},
    }
    print(f"[OLLAMA] URL={ollama_url}/api/chat | model={model}")
    import time as _time
    start = _time.time()
    try:
        response = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=timeout)
        elapsed = _time.time() - start
        print(f"[OLLAMA] status={response.status_code} | elapsed={elapsed:.2f}s")
        response.raise_for_status()
        data = response.json()
        answer = str(data.get("message", {}).get("content", "")).strip()
        print(f"[OLLAMA] response={answer[:300]}...")
        return answer
    except Exception as exc:
        elapsed = _time.time() - start
        print(f"[OLLAMA] EXCEPTION after {elapsed:.2f}s: {exc}")
        return ""


def call_lmstudio(lmstudio_url: str, model: str, prompt: str, timeout: float = 120.0) -> str:
    # Restrict to the two LMStudio endpoints we know are supported and expect 'input'
    base = lmstudio_url.rstrip("/")
    endpoints = [f"{base}/api/v1/chat", f"{base}/v1/responses"]

    # Different payload shapes to attempt per endpoint
    # Try the simplest 'input' shape first (LMStudio accepts this), then other shapes
    # Use the canonical 'input' payload first (string) for both endpoints.
    payloads = [{"model": model, "input": prompt}]

    def _extract_text_from_response(data: Any) -> str | None:
        # Direct response string
        if isinstance(data, str):
            return data.strip()
        if not isinstance(data, dict):
            return None

        # LMStudio native: often returns an "output" list; handle both dict and list shapes
        resp = data.get("response") or data.get("output") or data.get("result")
        # If resp is a dict containing 'output' list
        if isinstance(resp, dict):
            out = resp.get("output") or resp.get("results") or resp.get("content")
        else:
            out = resp

        if isinstance(out, list) and out:
            parts = []
            for entry in out:
                if isinstance(entry, dict):
                    # entry may contain 'content' as string or list
                    content = entry.get("content")
                    if isinstance(content, str):
                        parts.append(content)
                        continue
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and "text" in c:
                                parts.append(c.get("text", ""))
                            elif isinstance(c, str):
                                parts.append(c)
                        continue
                    # fallback: entry may itself be a text container
                    if "text" in entry:
                        parts.append(entry.get("text", ""))
                elif isinstance(entry, str):
                    parts.append(entry)
            if parts:
                return "\n\n".join([p.strip() for p in parts if p])
        # OpenAI-like choices
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            first = data["choices"][0]
            # Chat style
            if isinstance(first, dict):
                if "message" in first and isinstance(first["message"], dict):
                    # message.content may be dict or str
                    msg = first["message"].get("content")
                    if isinstance(msg, dict) and "text" in msg:
                        return str(msg.get("text", "")).strip()
                    if isinstance(msg, str):
                        return msg.strip()
                if "text" in first:
                    return str(first.get("text", "")).strip()

        # 'results' with content/text
        if "results" in data and isinstance(data["results"], list):
            parts = []
            for r in data["results"]:
                if isinstance(r, dict):
                    if "content" in r:
                        c = r.get("content")
                        if isinstance(c, str):
                            parts.append(c)
                        elif isinstance(c, list):
                            for x in c:
                                if isinstance(x, dict) and "text" in x:
                                    parts.append(x.get("text", ""))
            if parts:
                return "".join(parts).strip()

        # top-level text
        if "text" in data:
            return str(data.get("text", "")).strip()

        return None

    for endpoint in endpoints:
        p = payloads[0]
        try:
            response = requests.post(endpoint, json=p, timeout=timeout)
            # try to parse JSON
            try:
                data = response.json()
            except Exception:
                data = None

            if data:
                text = _extract_text_from_response(data)
                if text:
                    return text
                # if the response contains an 'error' field, include it in return to help debugging
                if isinstance(data, dict) and "error" in data:
                    err = data.get("error")
                    return f"LMStudio error: {err}"
            else:
                # fallback to raw text
                raw = response.text
                if raw:
                    return raw.strip()
        except Exception:
            # try next endpoint
            continue

    return (
        "No momento nao foi possivel consultar o modelo LMStudio local. "
        "Verifique se o servidor LMStudio esta rodando em LLM_URL e tente novamente."
    )


class MotorRAGLLM:
    # [Rastreabilidade: source 21, 46, 95]
    # Justificativa: Separacao clara entre camada de recuperacao semantica e camada
    # de geracao textual para modularidade e manutencao academica.
    def __init__(
        self,
        rag_system: SistemaRAG | None = None,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
    ) -> None:
        self.rag = rag_system or SistemaRAG()
        # LLM backend configuration: use Ollama by default for local execution.
        self.llm_backend = os.getenv("LLM_BACKEND", "ollama").lower()
        # Prefer an explicit URL, then the Ollama service, then a local fallback.
        self.llm_url = os.getenv("LLM_URL", os.getenv("OLLAMA_URL", "http://host.docker.internal:11434"))
        # Default to the local Ollama model when no override is provided.
        self.llm_model = os.getenv(
            "LLM_MODEL",
            os.getenv("OLLAMA_MODEL", "hf.co/jedisct1/MiMo-7B-RL-GGUF:Q8_0"),
        )
        # HTTP timeout (seconds) for LLM calls; can be set via env HTTP_TIMEOUT
        try:
            self.http_timeout = float(os.getenv("HTTP_TIMEOUT", os.getenv("HTTP_CLIENT_TIMEOUT", "120")))
        except Exception:
            self.http_timeout = 120.0

    # [Rastreabilidade: source 31, 43, 58, 95, 101]
    # Justificativa: Fluxo integra entrevista de referencia, contexto RAG restrito,
    # e resposta explicavel alinhada a etica e transparencia algoritmica.
    def responder(self, user_query: str, k: int = 3) -> RespostaRAG:
        novidade = is_novidade_question(user_query)

        if novidade:
            itens = self.rag.buscar_novidades(k=k)
            intent = "novidades"
        else:
            itens_raw = self.rag.buscar_relevantes(user_query, k=k)
            itens = [item for item in itens_raw if has_minimum_relevance_signal(item, user_query)]
            intent = "busca"

        contexto = build_rag_context(itens) if itens else "Sem itens relevantes no acervo para a consulta atual."

        user_prompt = (
            "CONTEXTO RAG:\n"
            f"{contexto}\n\n"
            f"PERGUNTA: {user_query}\n\n"
            "Responda em no maximo 3 frases. Recomende apenas livros do CONTEXTO RAG. PROIBIDO usar <think>."
        )

        print(f"[BOT] user_query={user_query} | itens_encontrados={len(itens)} | intent={intent}")
        answer = call_ollama(self.llm_url, self.llm_model, SYSTEM_PROMPT, user_prompt, timeout=self.http_timeout)

        if answer:
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
            answer = re.sub(r'<think>.*', '', answer, flags=re.DOTALL)
            answer = answer.strip()
        else:
            if not itens:
                answer = build_educational_failure_message()
            else:
                linhas = []
                for item in itens:
                    meta = item.get("metadata", {})
                    linhas.append(
                        f"- {meta.get('titulo', '')} | {meta.get('autor', '')} | {meta.get('localizacao', '')}"
                    )
                answer = (
                    "Segue uma selecao baseada no contexto recuperado:\n"
                    + "\n".join(linhas)
                    + "\n\n"
                    + "Nota de recomendacao: "
                    + build_footnote(itens[0], user_query)
                )

        transparency_note = (
            "Resposta gerada com contexto restrito ao RAG. "
            f"Itens consultados: {len(itens)}. "
            "Criterios: similaridade semantica entre consulta e metadados (titulo, resumo, assuntos)."
        )
        registrar_interacao_anonima(user_query, answer)
        return RespostaRAG(
            answer=answer,
            context_items=itens,
            transparency_note=transparency_note,
            needs_clarification=False,
            intent=intent,
        )


# [Rastreabilidade: source 21, 46, 95]
# Justificativa: Singleton simples para reduzir custo de carga de embeddings em runtime.
_ENGINE_INSTANCE: MotorRAGLLM | None = None


def get_rag_engine() -> MotorRAGLLM:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = MotorRAGLLM()
    return _ENGINE_INSTANCE


__all__ = [
    "DocumentMetadata",
    "build_transparency_log",
    "filter_relevant_recommendations",
    "from_searxng_results",
    "recommend_content",
    "SistemaRAG",
    "RespostaRAG",
    "MotorRAGLLM",
    "get_rag_engine",
    "is_vague_question",
    "build_rag_context",
]
