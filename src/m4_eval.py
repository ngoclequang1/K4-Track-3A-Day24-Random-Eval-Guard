from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from config import OPENAI_API_KEY, TEST_SET_PATH

METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
EVALUATOR_LLM = "gpt-4o-mini"
EVALUATOR_EMBEDDING = "text-embedding-3-small"


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path=TEST_SET_PATH):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def evaluate_ragas(questions, answers, contexts, ground_truths):
    if len({len(questions), len(answers), len(contexts), len(ground_truths)}) != 1:
        raise ValueError("Evaluation inputs must have equal lengths")
    output = {metric: 0.0 for metric in METRICS}
    output.update(per_question=[], status="failed",
                  metadata={"evaluator_models": [EVALUATOR_LLM, EVALUATOR_EMBEDDING]})
    if not questions:
        output["status"] = "empty"
        return output
    try:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is missing")
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        from ragas.run_config import RunConfig
        dataset = Dataset.from_dict({"question": questions, "answer": answers,
                                     "contexts": contexts, "ground_truth": ground_truths})
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=ChatOpenAI(model=EVALUATOR_LLM, temperature=0, api_key=OPENAI_API_KEY,
                           request_timeout=30, max_retries=1),
            embeddings=OpenAIEmbeddings(model=EVALUATOR_EMBEDDING, api_key=OPENAI_API_KEY,
                                        request_timeout=30, max_retries=1),
            run_config=RunConfig(timeout=60, max_retries=1, max_workers=4),
        )
        rows, invalid = [], 0
        for _, row in result.to_pandas().iterrows():
            scores = {}
            for metric in METRICS:
                value = float(row[metric])
                if not math.isfinite(value):
                    raise ValueError(f"RAGAS returned non-finite {metric}; rerun evaluation")
                scores[metric] = value
            rows.append(EvalResult(row["question"], row["answer"], list(row["contexts"]),
                                   row["ground_truth"], **scores))
        if len(rows) != len(questions):
            raise RuntimeError("Unexpected RAGAS row count")
        output.update({metric: sum(getattr(row, metric) for row in rows) / len(rows) for metric in METRICS})
        output.update(per_question=rows, status="partial" if invalid else "ok", invalid_scores=invalid)
        if invalid == len(rows) * len(METRICS):
            output.update(status="failed", error="RAGAS returned no valid metric scores")
    except Exception as exc:
        output["error"] = f"{type(exc).__name__}: {exc}"
    return output


def failure_analysis(eval_results, bottom_n=10):
    tree = {
        "faithfulness": ("Unsupported answer claims", "Ground prompt in context", "Generation"),
        "answer_relevancy": ("Answer does not address question", "Improve prompt", "Query interpretation"),
        "context_precision": ("Irrelevant retrieved chunks", "Add reranking", "Ranking"),
        "context_recall": ("Missing relevant evidence", "Improve retrieval", "Retrieval"),
    }
    failures = []
    for row in eval_results:
        values = {m: getattr(row, m) if math.isfinite(getattr(row, m)) else 0.0 for m in METRICS}
        worst = min(values, key=values.get)
        diagnosis, fix, error_tree = tree[worst]
        failures.append({"question": row.question, "expected": row.ground_truth, "got": row.answer,
                         "contexts": row.contexts, "worst_metric": worst, "score": values[worst],
                         "average_score": sum(values.values()) / 4, "diagnosis": diagnosis,
                         "suggested_fix": fix, "error_tree": error_tree})
    return sorted(failures, key=lambda item: item["average_score"])[:max(0, bottom_n)]


def save_report(results, failures, path="reports/ragas_report.json"):
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    report = {"aggregate": {m: results.get(m, 0.0) for m in METRICS},
              "status": results.get("status", "unknown"), "error": results.get("error"),
              "metadata": results.get("metadata", {}), "invalid_scores": results.get("invalid_scores", 0),
              "num_questions": len(results.get("per_question", [])), "failures": failures,
              "per_question": [asdict(row) for row in results.get("per_question", [])]}
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
