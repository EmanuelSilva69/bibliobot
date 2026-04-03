"""Motor de integracao entre RAG e LLM local (Ollama)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

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
Voce e o BiblioBot-UFMA, assistente academico formal da Universidade Federal do Maranhao.
Seu tom deve ser cordial, claro e tecnico, simulando um bibliotecario universitario qualificado.

Regras obrigatorias:
1) Atue como mediador informacional, nao como respondente superficial.
2) Se a pergunta estiver vaga, conduza entrevista de referencia com 2 ou 3 perguntas curtas.
3) Recomende somente obras presentes no CONTEXTO RAG fornecido.
4) Se o contexto nao for suficiente, informe limite de evidencia e solicite refinamento.
5) Explique criterios usados na recomendacao (assunto, resumo, aderencia tematica).
6) Nao invente titulos, autores, localizacoes ou referencias fora do contexto RAG.
""".strip()


@dataclass
class RespostaRAG:
    answer: str
    context_items: list[dict[str, Any]]
    transparency_note: str
    needs_clarification: bool


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
def call_ollama(ollama_url: str, model: str, prompt: str, timeout: float = 30.0) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()
    except Exception:
        return (
            "No momento nao foi possivel consultar o modelo local. "
            "Reformule a pergunta com tema, nivel e tipo de material para nova tentativa."
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
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://ollama:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # [Rastreabilidade: source 31, 43, 58, 95, 101]
    # Justificativa: Fluxo integra entrevista de referencia, contexto RAG restrito,
    # e resposta explicavel alinhada a etica e transparencia algoritmica.
    def responder(self, user_query: str, k: int = 3) -> RespostaRAG:
        itens = self.rag.buscar_relevantes(user_query, k=k)
        contexto = build_rag_context(itens)
        vaga = is_vague_question(user_query)

        if vaga:
            clarification = (
                "Para orientar melhor sua busca academica, preciso de tres esclarecimentos: "
                "(1) tema ou disciplina principal, (2) objetivo da pesquisa (trabalho, artigo, revisao), "
                "(3) nivel de profundidade desejado (introducao, intermediario ou avancado)."
            )
            transparency_note = (
                "Entrevista de referencia acionada por baixa especificidade da consulta. "
                f"Itens RAG recuperados: {len(itens)}."
            )
            return RespostaRAG(
                answer=clarification,
                context_items=itens,
                transparency_note=transparency_note,
                needs_clarification=True,
            )

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "CONTEXTO RAG (use apenas os itens abaixo):\n"
            f"{contexto}\n\n"
            f"PERGUNTA DO USUARIO: {user_query}\n\n"
            "Instrucoes finais de resposta:\n"
            "- Recomende somente titulos presentes no CONTEXTO RAG.\n"
            "- Para cada recomendacao, informe autor e localizacao no acervo.\n"
            "- Explique brevemente o criterio de aderencia ao tema.\n"
            "- Se nenhum item for adequado, solicite refinamento sem inventar dados."
        )
        answer = call_ollama(self.ollama_url, self.ollama_model, prompt)

        transparency_note = (
            "Resposta gerada com contexto restrito ao RAG. "
            f"Itens consultados: {len(itens)}. "
            "Criterios: similaridade semantica entre consulta e metadados (titulo, resumo, assuntos)."
        )
        return RespostaRAG(
            answer=answer,
            context_items=itens,
            transparency_note=transparency_note,
            needs_clarification=False,
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
