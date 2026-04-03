"""Nucleo RAG para vetorizacao e recuperacao semantica do acervo."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import chromadb
except Exception:  # pragma: no cover - fallback for incompatible local environments
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - fallback for incompatible local environments
    SentenceTransformer = None


# [Rastreabilidade: source 46, 58, 75, 95]
# Justificativa: A separacao entre vetorizacao e dialogo implementa modularidade,
# reduz sobrecarga informacional por triagem semantica (Ricci) e sustenta
# recomendacao baseada em conteudo com metadados bibliograficos.
class SistemaRAG:
    def __init__(
        self,
        acervo_path: str | Path = "app/data/acervo.json",
        collection_name: str = "acervo_ufma",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.acervo_path = Path(acervo_path)
        self.embedding_model_name = embedding_model
        self.embedding_model: SentenceTransformer | None = None
        self._fallback_store: list[dict[str, Any]] = []

        # Banco vetorial em memoria para prototipo academico.
        self.client = None
        self.collection = None
        if chromadb is not None:
            try:
                self.client = chromadb.Client()
                self.collection = self.client.get_or_create_collection(name=collection_name)
            except Exception:
                self.client = None
                self.collection = None

        self._carregar_e_indexar_acervo()

    # [Rastreabilidade: source 21, 46, 95]
    # Justificativa: Carregamento sob demanda reduz falhas de inicializacao do container
    # e mantém a vetorizacao disponível quando o modelo estiver pronto.
    def _get_embedding_model(self) -> SentenceTransformer:
        if self.embedding_model is None:
            if SentenceTransformer is None:
                raise RuntimeError("Modelo de embeddings indisponivel no ambiente atual.")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
        return self.embedding_model

    # [Rastreabilidade: source 46, 58, 95]
    # Justificativa: Vetorizacao combina titulo, resumo e assuntos para aproximar
    # linguagem do usuario e descritores do acervo.
    def _montar_texto_vetorizacao(self, item: dict[str, Any]) -> str:
        assuntos = ", ".join(item.get("assuntos", []))
        return " ".join(
            [
                str(item.get("titulo", "")),
                str(item.get("resumo", "")),
                assuntos,
            ]
        ).strip()

    # [Rastreabilidade: source 46, 58, 95]
    # Justificativa: Fallback lexical garante continuidade do servico em Docker
    # quando embeddings nao puderem ser carregados de imediato.
    def _lexical_score(self, consulta: str, texto: str) -> float:
        query_terms = set(re.findall(r"[a-zA-Z0-9]+", consulta.lower()))
        text_terms = set(re.findall(r"[a-zA-Z0-9]+", texto.lower()))
        if not query_terms:
            return 0.0
        overlap = query_terms.intersection(text_terms)
        return float(len(overlap))

    # [Rastreabilidade: Belkin - Estado Anomalo do Conhecimento]
    # Justificativa: Consultas curtas ou vagas devem acionar clarificacao antes
    # da busca, pois a necessidade informacional ainda nao esta suficientemente
    # estruturada.
    def consulta_ambigua(self, query: str) -> bool:
        texto = (query or "").strip().lower()
        gatilhos_novidade = ["novidade", "novidades", "livros recentes", "recentes", "mais novo", "atual"]
        if any(gatilho in texto for gatilho in gatilhos_novidade):
            return False

        if len(texto.split()) < 3:
            return True

        gatilhos = [
            "me indique",
            "quero livros",
            "preciso de livros",
            "tem material",
            "qual livro",
        ]
        return any(gatilho in texto for gatilho in gatilhos)

    # [Rastreabilidade: source 46, 58, 95]
    # Justificativa: A filtragem por novidades complementa a orientacao ao usuario
    # e melhora a recuperacao de itens recentes do acervo.
    def buscar_novidades(self, k: int = 3) -> list[dict[str, Any]]:
        if self.collection.count() == 0:
            return []

        resultados = self.collection.get(include=["metadatas", "documents"])
        metadados = resultados.get("metadatas", []) or []
        documentos = resultados.get("documents", []) or []
        ids = resultados.get("ids", []) or []

        itens: list[dict[str, Any]] = []
        for doc_id, meta, doc in zip(ids, metadados, documentos):
            data_aquisicao = meta.get("data_aquisicao", "")
            itens.append(
                {
                    "texto_indexado": doc,
                    "metadata": meta,
                    "data_aquisicao": data_aquisicao,
                    "id": doc_id,
                }
            )

        def ordenar(item: dict[str, Any]) -> datetime:
            valor = str(item.get("data_aquisicao", "1900-01-01"))
            try:
                return datetime.fromisoformat(valor)
            except ValueError:
                return datetime(1900, 1, 1)

        itens.sort(key=ordenar, reverse=True)
        return itens[:max(1, k)]

    # [Rastreabilidade: source 58, 74, 101]
    # Justificativa: Quando a recuperacao falha, o sistema deve orientar estrategia
    # alternativa e preservar o papel do bibliotecario humano.
    def orientacao_falha_busca(self, query: str) -> str:
        return (
            "Nao encontrei itens suficientemente relevantes no acervo para essa consulta. "
            "Sugestao: refine o tema com descritores mais especificos, informe autor, "
            "area do conhecimento ou recorte temporal. Se preferir, procure o bibliotecario "
            "da UFMA para apoiar a estrategia de busca e a selecao de fontes."
        )

    # [Rastreabilidade: source 21, 46, 58, 95]
    # Justificativa: Indexacao padronizada com metadados explicitos melhora
    # auditabilidade do prototipo e transparencia da recuperacao.
    def _carregar_e_indexar_acervo(self) -> None:
        if not self.acervo_path.exists():
            raise FileNotFoundError(f"Arquivo de acervo nao encontrado: {self.acervo_path}")

        with self.acervo_path.open("r", encoding="utf-8") as fp:
            dados = json.load(fp)

        if not isinstance(dados, list):
            raise ValueError("O acervo deve ser um array JSON de objetos.")

        self._fallback_store = []
        if self.collection is not None and self.collection.count() > 0:
            self.collection.delete(where={"tipo": "livro"})

        ids: list[str] = []
        documentos: list[str] = []
        metadados: list[dict[str, Any]] = []
        embeddings: list[list[float]] = []

        for item in dados:
            doc_id = str(item.get("id", "")).strip()
            if not doc_id:
                continue

            texto = self._montar_texto_vetorizacao(item)
            try:
                vetor = self._get_embedding_model().encode(texto).tolist()
            except Exception:
                vetor = []

            ids.append(doc_id)
            documentos.append(texto)
            embeddings.append(vetor)
            meta = {
                "id": doc_id,
                "titulo": str(item.get("titulo", "")),
                "autor": str(item.get("autor", "")),
                "localizacao": str(item.get("localizacao", "")),
                "data_aquisicao": str(item.get("data_aquisicao", "")),
                "assuntos": " | ".join(item.get("assuntos", [])),
                "tipo": "livro",
            }
            metadados.append(meta)
            self._fallback_store.append({"id": doc_id, "texto": texto, "metadata": meta, "embedding": vetor})

        if ids and self.collection is not None:
            self.collection.add(
                ids=ids,
                documents=documentos,
                embeddings=embeddings,
                metadatas=metadados,
            )

    # [Rastreabilidade: source 46, 58, 95]
    # Justificativa: Busca semantica entrega contexto relevante para LLM,
    # reduzindo ruido e aumentando aderencia ao acervo institucional.
    def buscar_relevantes(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        consulta = (query or "").strip()
        if not consulta:
            return []

        if self.consulta_ambigua(consulta):
            return []

        if self.collection is None:
            itens = []
            for item in self._fallback_store:
                score = self._lexical_score(consulta, item["texto"])
                if score > 0:
                    itens.append(
                        {
                            "texto_indexado": item["texto"],
                            "metadata": item["metadata"],
                            "distancia": max(0.0, 1.0 - min(score / 10.0, 1.0)),
                            "lexical_score": score,
                        }
                    )

            itens.sort(key=lambda item: item.get("lexical_score", 0.0), reverse=True)
            return itens[: max(1, k)]

        try:
            query_embedding = self._get_embedding_model().encode(consulta).tolist()
            resultado = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max(1, k),
                include=["documents", "metadatas", "distances"],
            )

            docs = resultado.get("documents", [[]])[0]
            metas = resultado.get("metadatas", [[]])[0]
            dists = resultado.get("distances", [[]])[0]

            relevantes: list[dict[str, Any]] = []
            for doc, meta, dist in zip(docs, metas, dists):
                relevantes.append(
                    {
                        "texto_indexado": doc,
                        "metadata": meta,
                        "distancia": float(dist),
                    }
                )

            return relevantes
        except Exception:
            # Fallback lexical simples para manter a aplicação operacional no Docker.
            items: list[dict[str, Any]] = []
            for item in self._fallback_store:
                doc = item["texto"]
                meta = item["metadata"]
                score = self._lexical_score(consulta, doc)
                if score <= 0:
                    continue
                items.append(
                    {
                        "texto_indexado": doc,
                        "metadata": meta,
                        "distancia": max(0.0, 1.0 - min(score / 10.0, 1.0)),
                        "lexical_score": score,
                    }
                )

            items.sort(key=lambda item: item.get("lexical_score", 0.0), reverse=True)
            return items[: max(1, k)]
