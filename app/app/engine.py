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
Voce e o BiblioBot-UFMA, assistente academico formal da Universidade Federal do Maranhao.
Seu tom deve ser cordial, claro e tecnico, simulando um bibliotecario universitario qualificado.

Regras obrigatorias:
1) Atue como mediador informacional, nao como respondente superficial.
2) Se a pergunta estiver vaga, conduza entrevista de referencia com 2 ou 3 perguntas curtas.
3) Recomende somente obras presentes no CONTEXTO RAG fornecido.
4) Se o contexto nao for suficiente, informe limite de evidencia e solicite refinamento.
5) Explique criterios usados na recomendacao (assunto, resumo, aderencia tematica).
6) Nao invente titulos, autores, localizacoes ou referencias fora do contexto RAG.
7) Quando recomendar um livro, inclua obrigatoriamente uma nota curta explicando o criterio.
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
        return float(distance) <= 0.65
    return False


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
        novidade = is_novidade_question(user_query)
        vaga = is_vague_question(user_query) and not novidade

        if vaga:
            clarification = (
                "Para que eu possa ser mais preciso na sua orientacao, voce poderia detalhar "
                "se busca esse tema para uma pesquisa academica ou uma consulta rapida? "
                "Se desejar, informe tambem tema, area e tipo de material desejado."
            )
            transparency_note = (
                "Filtro de incerteza acionado por consulta curta ou ambigua, conforme a "
                "teoria de Belkin sobre Estado Anomalo do Conhecimento."
            )
            registrar_interacao_anonima(user_query, clarification)
            return RespostaRAG(
                answer=clarification,
                context_items=[],
                transparency_note=transparency_note,
                needs_clarification=True,
                intent="clarificacao",
            )

        if novidade:
            itens = self.rag.buscar_novidades(k=k)
            intent = "novidades"
        else:
            itens_raw = self.rag.buscar_relevantes(user_query, k=k)
            itens = [item for item in itens_raw if has_minimum_relevance_signal(item, user_query)]
            intent = "busca"

        if not itens:
            resposta_educativa = build_educational_failure_message()
            registrar_interacao_anonima(user_query, resposta_educativa)
            return RespostaRAG(
                answer=resposta_educativa,
                context_items=[],
                transparency_note=(
                    "Recuperacao sem resultados suficientes; resposta orientou refinamento e "
                    "encaminhamento ao bibliotecario humano."
                ),
                needs_clarification=True,
                intent=intent,
            )

        contexto = build_rag_context(itens)

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "CONTEXTO RAG (use apenas os itens abaixo):\n"
            f"{contexto}\n\n"
            f"PERGUNTA DO USUARIO: {user_query}\n\n"
            "Instrucoes finais de resposta:\n"
            "- Recomende somente titulos presentes no CONTEXTO RAG.\n"
            "- Para cada recomendacao, informe autor e localizacao no acervo.\n"
            "- Ao final de cada recomendacao, inclua a nota de rodape explicativa.\n"
            "- Explique brevemente o criterio de aderencia ao tema.\n"
            "- Se nenhum item for adequado, solicite refinamento sem inventar dados."
        )
        answer = call_ollama(self.ollama_url, self.ollama_model, prompt)

        if answer:
            if "Nota:" not in answer and "Nota de rodape" not in answer:
                notas = "\n".join(
                    [
                        f"- {item.get('metadata', {}).get('titulo', '')}: "
                        f"{build_footnote(item, user_query)}"
                        for item in itens
                    ]
                )
                answer = f"{answer}\n\nNota de recomendacao:\n{notas}"
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
