from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from config import GENERATION_MODEL, OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str


def _request(instruction, text, json_mode=False, max_tokens=400):
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        options = {"response_format": {"type": "json_object"}} if json_mode else {}
        result = OpenAI(api_key=OPENAI_API_KEY, timeout=30, max_retries=1).chat.completions.create(
            model=GENERATION_MODEL, temperature=0, max_tokens=max_tokens,
            messages=[{"role": "system", "content": instruction + " Chỉ dùng thông tin trong văn bản."},
                      {"role": "user", "content": text}], **options)
        content = result.choices[0].message.content or ""
        return json.loads(content) if json_mode else content.strip()
    except Exception:
        return None


def _summary(text):
    return " ".join(s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip())[:500]


def _questions(text, count):
    sentences = [s.strip().lstrip("# ") for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 10]
    return [f"Nội dung nào được quy định về: {s}?" for s in sentences[:max(0, count)]]


def _metadata(text):
    title = re.search(r"^#+\s+(.+)$", text, re.MULTILINE)
    return {"topic": title.group(1) if title else "general", "entities": [], "category": "policy",
            "language": "vi", "date_range": re.findall(r"\b\d{2}/\d{2}/\d{4}\b", text)}


def summarize_chunk(text):
    value = _request("Tóm tắt tối đa 2 câu tiếng Việt.", text, max_tokens=150)
    return value if isinstance(value, str) and value else _summary(text)


def generate_hypothesis_questions(text, n_questions=3):
    if n_questions <= 0 or not text.strip():
        return []
    value = _request(f'Trả về JSON {{"questions": [...]}} gồm {n_questions} câu hỏi.', text, True)
    questions = value.get("questions") if isinstance(value, dict) else None
    if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
        return [q.strip().rstrip("?") + "?" for q in questions if q.strip()][:n_questions]
    return _questions(text, n_questions)


def contextual_prepend(text, document_title=""):
    value = _request("Viết 1 câu ngắn mô tả chủ đề đoạn văn.", f"Tài liệu: {document_title}\n\n{text}", max_tokens=80)
    context = value if isinstance(value, str) and value else f"Trích từ {document_title or 'tài liệu chính sách'}."
    return f"{context}\n\n{text}"


def extract_metadata(text):
    value = _request("Trả về JSON metadata gồm topic, entities, date_range, category, language.", text, True)
    return {**_metadata(text), **value} if isinstance(value, dict) else _metadata(text)


def enrich_chunks(chunks, methods=None):
    if os.getenv("SKIP_ENRICHMENT") == "1":
        return []
    methods = ["combined"] if methods is None else methods
    if set(methods) - {"combined", "summary", "hyqa", "contextual", "metadata"}:
        raise ValueError("Unknown enrichment method")
    enriched = []
    for chunk in chunks:
        text, metadata = chunk["text"], chunk.get("metadata", {})
        source = metadata.get("source", "")
        summary = summarize_chunk(text) if "combined" in methods or "summary" in methods else ""
        questions = generate_hypothesis_questions(text) if "combined" in methods or "hyqa" in methods else []
        auto_meta = extract_metadata(text) if "combined" in methods or "metadata" in methods else {}
        enriched_text = contextual_prepend(text, source) if "combined" in methods or "contextual" in methods else text
        if summary:
            enriched_text += f"\n\nTóm tắt: {summary}"
        if questions:
            enriched_text += "\n\nCâu hỏi liên quan:\n" + "\n".join(questions)
        enriched.append(EnrichedChunk(text, enriched_text, summary, questions,
                                      {**auto_meta, **metadata}, "+".join(methods)))
    return enriched
