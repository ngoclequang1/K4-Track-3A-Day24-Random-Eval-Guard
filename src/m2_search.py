from __future__ import annotations

from dataclasses import dataclass
from config import (BM25_TOP_K, COLLECTION_NAME, DENSE_TOP_K, EMBEDDING_DIM, EMBEDDING_MODEL,
                    HYBRID_TOP_K, QDRANT_HOST, QDRANT_PORT)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str


def segment_vietnamese(text: str) -> str:
    from underthesea import word_tokenize
    return word_tokenize(text, format="text").replace("_", " ") if text.strip() else ""


class BM25Search:
    def __init__(self):
        self.documents, self.bm25 = [], None

    def index(self, chunks: list[dict]) -> None:
        from rank_bm25 import BM25Okapi
        self.documents = list(chunks)
        corpus = [segment_vietnamese(c["text"].lower()).split() for c in chunks]
        self.bm25 = BM25Okapi(corpus) if any(corpus) else None

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        if self.bm25 is None or top_k <= 0 or not query.strip():
            return []
        scores = self.bm25.get_scores(segment_vietnamese(query.lower()).split())
        indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [SearchResult(self.documents[i]["text"], float(scores[i]),
                             dict(self.documents[i].get("metadata", {})), "bm25")
                for i in indices if scores[i] > 0]


class DenseSearch:
    def __init__(self):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=10)
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            import torch
            torch.set_num_threads(2)
            self._encoder = SentenceTransformer(
                EMBEDDING_MODEL, model_kwargs={"torch_dtype": torch.float16})
            self._encoder.max_seq_length = 512
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        from qdrant_client.models import Distance, PointStruct, VectorParams
        vectors = self._get_encoder().encode([c["text"] for c in chunks], batch_size=1,
                                             show_progress_bar=True) if chunks else []
        dimension = len(vectors[0]) if chunks else EMBEDDING_DIM
        if self.client.collection_exists(collection):
            self.client.delete_collection(collection)
        self.client.create_collection(collection, vectors_config=VectorParams(size=dimension, distance=Distance.COSINE))
        for start in range(0, len(chunks), 64):
            points = [PointStruct(id=i, vector=vectors[i].tolist(),
                                  payload={**chunks[i].get("metadata", {}), "text": chunks[i]["text"]})
                      for i in range(start, min(start + 64, len(chunks)))]
            self.client.upsert(collection, points, wait=True)

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        if top_k <= 0 or not query.strip() or not self.client.collection_exists(collection):
            return []
        vector = self._get_encoder().encode(query).tolist()
        response = self.client.search(collection, query_vector=vector, limit=top_k, with_payload=True)
        return [SearchResult(p.payload["text"], float(p.score),
                             {k: v for k, v in p.payload.items() if k != "text"}, "dense")
                for p in response if p.payload and "text" in p.payload]


def reciprocal_rank_fusion(results_list: list[list[SearchResult]], k: int = 60,
                           top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
    if k < 0:
        raise ValueError("k must be non-negative")
    scores, representatives = {}, {}
    for results in results_list:
        seen = set()
        for rank, result in enumerate(results):
            key = (result.text, result.metadata.get("source"), result.metadata.get("chunk_index"))
            if key in seen:
                continue
            seen.add(key); representatives.setdefault(key, result)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return [SearchResult(representatives[key].text, scores[key], dict(representatives[key].metadata), "hybrid")
            for key in sorted(scores, key=scores.get, reverse=True)[:max(0, top_k)]]


class HybridSearch:
    def __init__(self):
        self.bm25, self.dense = BM25Search(), DenseSearch()
    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks); self.dense.index(chunks)
    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        return reciprocal_rank_fusion([self.bm25.search(query), self.dense.search(query)], top_k=top_k)
