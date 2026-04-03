"""Motor de recomendacao baseada em conteudo para o BiblioBot-UFMA."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re


# [Rastreabilidade: source 46, 75, 95]
# Justificativa: Estrutura de metadados permite recomendacao baseada em conteudo,
# alinhada ao recorte de titulo, assunto e autor citado no projeto.
@dataclass
class DocumentMetadata:
    title: str
    authors: list[str]
    subjects: list[str]
    abstract: str
    source: str
    url: str


# [Rastreabilidade: source 44, 63, 95]
# Justificativa: Relacoes semanticas simples reforcam proximidade entre termos de busca
# e descritores bibliograficos, reduzindo perda de itens relevantes.
SEMANTIC_RELATIONS: dict[str, set[str]] = {
    "chatbot": {"agente conversacional", "assistente virtual", "dialogo"},
    "recomendacao": {"sugestao", "curadoria", "indicacao"},
    "biblioteca": {"acervo", "catalogo", "informacao"},
    "informacional": {"informacao", "busca", "necessidade"},
    "academico": {"cientifico", "universitario", "pesquisa"},
}


# [Rastreabilidade: source 31, 46, 63]
# Justificativa: Extrair termos da necessidade informacional e etapa essencial da
# entrevista de referencia para converter linguagem natural em criterios de busca.
def extract_keywords(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    tokens = [tok for tok in cleaned.split() if len(tok) > 2]
    stopwords = {
        "para", "como", "com", "dos", "das", "que", "uma", "por", "sem", "sobre",
        "entre", "mais", "menos", "onde", "quando", "qual", "quais", "ser", "sao",
    }
    return [t for t in tokens if t not in stopwords]


# [Rastreabilidade: source 44, 58, 95]
# Justificativa: Transparencia algoritmica exige registrar motivos da recomendacao.
def score_document(user_keywords: list[str], doc: DocumentMetadata) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0

    full_text = " ".join([
        doc.title.lower(),
        " ".join(a.lower() for a in doc.authors),
        " ".join(s.lower() for s in doc.subjects),
        doc.abstract.lower(),
    ])

    for kw in user_keywords:
        if kw in doc.title.lower():
            score += 3.0
            reasons.append(f"termo '{kw}' encontrado no titulo")
        elif kw in " ".join(s.lower() for s in doc.subjects):
            score += 2.5
            reasons.append(f"termo '{kw}' encontrado no assunto")
        elif kw in " ".join(a.lower() for a in doc.authors):
            score += 2.0
            reasons.append(f"termo '{kw}' encontrado no autor")
        elif kw in doc.abstract.lower():
            score += 1.5
            reasons.append(f"termo '{kw}' encontrado no resumo")

        for related in SEMANTIC_RELATIONS.get(kw, set()):
            if related in full_text:
                score += 0.8
                reasons.append(f"relacao semantica entre '{kw}' e '{related}'")

    return score, reasons


# [Rastreabilidade: source 46, 75, 95]
# Justificativa: Funcao central de recomendacao por conteudo com metadados bibliograficos.
def recommend_content(user_profile: dict[str, Any], collection: list[DocumentMetadata], limit: int = 5) -> list[dict[str, Any]]:
    interest_text = " ".join([
        str(user_profile.get("query", "")),
        " ".join(user_profile.get("subjects", [])),
        " ".join(user_profile.get("authors", [])),
    ])
    keywords = extract_keywords(interest_text)

    ranked: list[tuple[float, list[str], DocumentMetadata]] = []
    for doc in collection:
        score, reasons = score_document(keywords, doc)
        if score > 0:
            ranked.append((score, reasons, doc))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = ranked[:limit]

    return [
        {
            "score": round(score, 2),
            "reasons": reasons[:4],
            "metadata": asdict(doc),
        }
        for score, reasons, doc in selected
    ]


# [Rastreabilidade: source 58, 63, 101]
# Justificativa: Mitigacao de sobrecarga informacional por corte de baixa relevancia.
def filter_relevant_recommendations(recommendations: list[dict[str, Any]], min_score: float = 2.0) -> list[dict[str, Any]]:
    return [item for item in recommendations if item["score"] >= min_score]


# [Rastreabilidade: source 58, 74, 101]
# Justificativa: Nota sintetica para transparencia ao usuario final.
def build_transparency_log(user_profile: dict[str, Any], returned_items: int, limit: int) -> str:
    return (
        "Recomendacao baseada em metadados (titulo, assunto, autor, resumo), "
        f"consulta='{user_profile.get('query', '')}', "
        f"itens retornados={returned_items}, limite configurado={limit}."
    )


# [Rastreabilidade: source 46, 58, 95]
# Justificativa: Conversao de resultados externos em metadados padronizados.
def from_searxng_results(results: list[dict[str, Any]]) -> list[DocumentMetadata]:
    normalized: list[DocumentMetadata] = []
    for item in results:
        title = item.get("title") or "Sem titulo"
        abstract = item.get("content") or item.get("snippet") or ""
        source = item.get("engine") or item.get("source") or "searxng"
        url = item.get("url") or ""

        subject_candidates = extract_keywords(f"{title} {abstract}")
        subjects = list(dict.fromkeys(subject_candidates[:6]))

        normalized.append(
            DocumentMetadata(
                title=title,
                authors=[],
                subjects=subjects,
                abstract=abstract,
                source=source,
                url=url,
            )
        )
    return normalized
