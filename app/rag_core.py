"""Nucleo RAG para vetorizacao e recuperacao semantica do acervo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


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
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        # Banco vetorial em memoria para prototipo academico.
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name=collection_name)

        self._carregar_e_indexar_acervo()

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

        # Evita duplicacao quando a classe for reinicializada no mesmo processo.
        if self.collection.count() > 0:
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
            vetor = self.embedding_model.encode(texto).tolist()

            ids.append(doc_id)
            documentos.append(texto)
            embeddings.append(vetor)
            metadados.append(
                {
                    "id": doc_id,
                    "titulo": str(item.get("titulo", "")),
                    "autor": str(item.get("autor", "")),
                    "localizacao": str(item.get("localizacao", "")),
                    "assuntos": " | ".join(item.get("assuntos", [])),
                    "tipo": "livro",
                }
            )

        if ids:
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

        query_embedding = self.embedding_model.encode(consulta).tolist()
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
