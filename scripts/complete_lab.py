"""Resume live work and export evidence-backed reports. Run from repository root."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('HF_HOME', str(ROOT / '.model-cache'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('SKIP_ENRICHMENT', '1')

def run(*args):
    subprocess.run([sys.executable, '-u', *args], check=True, cwd=ROOT)

def read(name):
    return json.loads((ROOT / 'artifacts' / name).read_text(encoding='utf-8'))

def block(value):
    return '```json\n' + json.dumps(value, ensure_ascii=False, indent=2) + '\n```\n'

def main():
    if not (ROOT / 'artifacts/answers_50q.json').exists():
        run('scripts/setup_answers.py', '--live')
    for phase, filename in [('a', 'ragas_50q.json'), ('b', 'judge_results.json')]:
        if not (ROOT / 'artifacts' / filename).exists():
            run('scripts/run_experiments.py', '--phase', phase, '--live')
    if not (ROOT / 'artifacts/guard_results.json').exists():
        run('scripts/run_experiments.py', '--phase', 'c', '--live', '--latency-samples', '20')
    a, b, c = [read(n) for n in ['ragas_50q.json', 'judge_results.json', 'guard_results.json']]
    answers = read('answers_50q.json')
    header = 'Nhóm Lê Quang Ngọc — 2A202602664.\n\n'
    conditions = ('Pipeline dùng MiniLM multilingual 384 chiều và mmarco-mMiniLMv2 reranker; '
                  '102 raw chunks, SKIP_ENRICHMENT=1, batch size 1. '
                  'BGE-M3 không chạy được ổn định do thiếu RAM.\n\n')
    report_a = '# Phân tích lỗi Phase A\n\n' + header + conditions
    report_a += 'Metadata và điểm theo distribution:\n\n' + block(a['metadata']) + block(a['per_distribution'])
    report_a += 'Bottom 10 và matrix (worst metric của mọi câu):\n\n' + block(a['bottom_10']) + block(a['failure_clusters'])
    bottom_ids = {row['question_id'] for row in a['bottom_10']}
    report_a += 'Bằng chứng answer/context/reference cho các câu yếu:\n\n' + block([row for row in answers if row['id'] in bottom_ids])
    report_a += ('Diagnosis theo metric là giả thuyết; cần đối chiếu context/reference trước khi kết luận nguyên nhân. '
                 'Đề xuất kiểm tra retrieval với filter phiên bản, điều kiện/phủ định và reranking; '
                 'chạy lại cùng 50 câu để so sánh. Bộ mẫu và model nhỏ giới hạn khả năng suy rộng.\n')
    report_b = '# Đánh giá LLM Judge Phase B\n\n' + header
    report_b += ('A lấy từ answers pipeline, B từ model_answer được cấp; reference từ test set. '
                 'Binary calibration chấm đúng model_answer; nhãn human chỉ dùng đối chiếu sau judge.\n\n')
    report_b += block(b)
    report_b += ('Năm cặp và mười nhãn là mẫu nhỏ. Position inconsistency và verbosity win rate '
                 'là tín hiệu cần đọc nội dung, không tự chứng minh nguyên nhân bias. '
                 'Judge phải được đối chiếu human, không xem là đáp án tuyệt đối.\n')
    blueprint = '# Blueprint CI/CD đề xuất\n\n' + header
    blueprint += ('Input → Presidio → NeMo input → RAG → NeMo output → response. '
                  'Request dừng khi guard chặn; redact PII trước logging, giữ key trong .env. '
                  'Lỗi guard/API trả trạng thái không phục vụ an toàn; generation fallback phải được ghi rõ.\n\n')
    blueprint += 'Bằng chứng guard và latency:\n\n' + block(c)
    blueprint += ('Task 12 chỉ đo input_layers_sequential với hai warm-up và 20 mẫu timed; '
                  'RAG, output và full request latency chưa đo. CI đề xuất: faithfulness ≥0.75, '
                  'avg_score ≥0.65, attacks ≥18/20, clean 8/8, output 4/4; job kiểm tra ngưỡng trả nonzero khi fail. '
                  'Workflow chưa triển khai. Monitoring theo dõi false positives, P95, model/version drift và lỗi API; '
                  'Lê Quang Ngọc phụ trách kiểm tra mẫu đã redact và triage. '
                  'Cải tiến: retrieval theo phiên bản, reranking, prompt grounding, self-check latency và thêm clean controls.\n\n')
    blueprint += 'Kết quả A/B dùng làm căn cứ CI:\n\n' + block(a['per_distribution']) + block(b)
    for name, content in [('failure_clusters.md', report_a), ('bias_report.md', report_b), ('blueprint.md', blueprint)]:
        (ROOT / 'doc/reports' / name).write_text(content, encoding='utf-8')
    run('scripts/check_lab.py')

if __name__ == '__main__':
    main()
