from __future__ import annotations

import glob
import hashlib
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache

from config import DATA_DIR, HIERARCHICAL_CHILD_SIZE, HIERARCHICAL_PARENT_SIZE, SEMANTIC_THRESHOLD


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


def _extract_pdf_text(path: str) -> str:
    from pypdf import PdfReader
    return "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages).strip()


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    docs = []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.md"))):
        with open(path, encoding="utf-8") as stream:
            docs.append({"text": stream.read(), "metadata": {"source": os.path.basename(path)}})
    for path in sorted(glob.glob(os.path.join(data_dir, "*.pdf"))):
        text = _extract_pdf_text(path)
        if text:
            docs.append({"text": text, "metadata": {"source": os.path.basename(path)}})
    return docs


def chunk_basic(text: str, chunk_size: int = 500, metadata: dict | None = None) -> list[Chunk]:
    chunks, current = [], ""
    for paragraph in (p.strip() for p in text.split("\n\n") if p.strip()):
        if current and len(current) + len(paragraph) > chunk_size:
            chunks.append(Chunk(current.strip(), {**(metadata or {}), "chunk_index": len(chunks)}))
            current = ""
        current += paragraph + "\n\n"
    if current.strip():
        chunks.append(Chunk(current.strip(), {**(metadata or {}), "chunk_index": len(chunks)}))
    return chunks


@lru_cache(maxsize=1)
def _semantic_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def chunk_semantic(text: str, threshold: float = SEMANTIC_THRESHOLD, metadata: dict | None = None) -> list[Chunk]:
    import numpy as np
    if not -1 <= threshold <= 1:
        raise ValueError("threshold must be between -1 and 1")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\s*\n", text) if s.strip()]
    if not sentences:
        return []
    vectors = _semantic_encoder().encode(sentences, normalize_embeddings=True)
    groups = [[sentences[0]]]
    for index in range(1, len(sentences)):
        if float(np.dot(vectors[index - 1], vectors[index])) < threshold:
            groups.append([])
        groups[-1].append(sentences[index])
    return [Chunk("\n\n".join(group), {**(metadata or {}), "strategy": "semantic", "chunk_index": i})
            for i, group in enumerate(groups)]


def chunk_hierarchical(text: str, parent_size: int = HIERARCHICAL_PARENT_SIZE,
                       child_size: int = HIERARCHICAL_CHILD_SIZE,
                       metadata: dict | None = None) -> tuple[list[Chunk], list[Chunk]]:
    if parent_size <= 0 or child_size <= 0 or child_size >= parent_size:
        raise ValueError("Require 0 < child_size < parent_size")
    metadata = metadata or {}

    def split_bounded(value: str, size: int) -> list[str]:
        pieces, value = [], value.strip()
        while value:
            end = min(size, len(value))
            if end < len(value):
                boundary = max(value.rfind("\n", 0, end + 1), value.rfind(" ", 0, end + 1))
                if boundary > 0:
                    end = boundary
            if piece := value[:end].strip():
                pieces.append(piece)
            value = value[end:].strip()
        return pieces

    parents, children = [], []
    doc_id = hashlib.sha256((str(metadata.get("source", "")) + text).encode()).hexdigest()[:16]
    for index, parent_text in enumerate(split_bounded(text, parent_size)):
        parent_id = f"{doc_id}_parent_{index}"
        parents.append(Chunk(parent_text, {**metadata, "strategy": "hierarchical",
                                           "chunk_type": "parent", "parent_id": parent_id,
                                           "chunk_index": index}))
        for child_text in split_bounded(parent_text, child_size):
            children.append(Chunk(child_text, {**metadata, "strategy": "hierarchical",
                                               "chunk_type": "child", "chunk_index": len(children)},
                                  parent_id))
    return parents, children


def chunk_structure_aware(text: str, metadata: dict | None = None) -> list[Chunk]:
    chunks, lines, section, fence = [], [], "", None
    def flush():
        content = "\n".join(lines).strip()
        if content:
            chunks.append(Chunk(content, {**(metadata or {}), "section": section,
                                          "strategy": "structure", "chunk_index": len(chunks)}))
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            fence = token if fence is None else (None if token[0] == fence[0] and len(token) >= len(fence) else fence)
        if fence is None and re.match(r"^#{1,6}\s+\S", line):
            flush(); lines = []; section = line.strip()
        lines.append(line)
    flush()
    return chunks
