# Blueprint CI/CD cho RAG và guardrails

Nhóm: Nhóm Lê Quang Ngọc

Người phụ trách: Lê Quang Ngọc — 2A202602664

Đây là đề xuất CI/CD, chưa phải workflow đã triển khai/chạy. Nguồn là `artifacts/ragas_50q.json`, `artifacts/judge_results.json` và `artifacts/guard_results.json`. Phase C chạy lúc `2026-10-12T08:06:32.686870+00:00` với guard model `gpt-4o-mini`; generation/evaluator/judge lần lượt là `gpt-4o-mini-2024-07-18`, `gpt-4o-mini` + `text-embedding-3-small`, và `gpt-4o-mini`.

## Kiến trúc và failure action

`Input → Presidio → NeMo input rail → RAG → NeMo output rail → response`

- Presidio nhận diện/redact CCCD/CMND, số điện thoại Việt Nam và email. NeMo input chặn jailbreak, yêu cầu dữ liệu bí mật và mật khẩu. Request thật short-circuit ngay khi một tầng chặn.
- Chỉ input đã qua redact mới được ghi log; không ghi raw PII, API key hay nội dung bí mật. Secrets nằm trong `.env`/secret store của CI, không commit vào repo.
- RAG chỉ chạy khi input được phép. Output rail giữ câu an toàn và thay câu nhạy cảm bằng refusal chuẩn.
- Guard/API lỗi, timeout hoặc output không parse được thì fail closed với trạng thái không phục vụ an toàn và correlation ID; không tự chuyển sang câu trả lời không được kiểm duyệt. Extractive fallback, nếu bật, phải được đánh dấu trong artifact.

Kết quả live: attacks `20/20`, clean `8/8` allowed (false-positive rate `0.0`), output `4/4`. Hai output an toàn được giữ; hai output chứa CCCD/mật khẩu bị thay bởi refusal.

## Phạm vi và số đo latency

Task 12 đo `input_layers_sequential`: luôn chạy Presidio rồi NeMo input, không short-circuit. Engines được tạo trước; 2 warm-up thật bị loại; 20 mẫu timed dùng `perf_counter`, percentile nội suy tuyến tính và input total được tính từ từng sample.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | 47.140 | 81.758 | 92.846 | Đã đo, 20 mẫu |
| NeMo input | 785.653 | 999.186 | 1048.249 | Đã đo, bottleneck |
| Input guard sequential | 850.832 | 1042.601 | 1090.540 | Không đạt target 500 ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input total |

`latency_budget_ok=false`. NeMo input chiếm phần lớn P95. Hướng tối ưu là rule/local classifier trước LLM, cache cấu hình/connection, giới hạn prompt và benchmark lại cùng 2 warm-up + tối thiểu 20 mẫu. Để đo các phần còn thiếu, bổ sung timestamps quanh retrieval, generation và output rail, rồi báo cáo cả đường allowed lẫn blocked.

## CI gates đề xuất

- Chạy offline: `python -m pytest -q -p no:cacheprovider --basetemp <workspace-temp>` và `python scripts/check_lab.py`; job trả nonzero nếu test/schema/hash/count sai.
- Chạy evaluation theo lịch hoặc khi đổi model/data: Phase A yêu cầu faithfulness ≥0.75 và avg_score ≥0.65 trên 50 câu; Phase B yêu cầu κ >0.6 và position inconsistency được audit; Phase C yêu cầu attacks ≥18/20, clean 8/8 và output 4/4.
- Mốc bắt buộc của lab vẫn là attacks ≥15/20. Gate 18/20 là tiêu chuẩn CI đề xuất, không phải sửa rubric.
- Chưa bật gate full-guard P95 <500 ms vì full guard chưa đo. Với scope đã đo, build hiện phải cảnh báo/fail performance do input P95 `1042.601 ms`.
- Các ngưỡng phải được code thành assertions/exit code trong job; biến môi trường `MIN_*` tự nó không tạo gate. Workflow CI hiện chưa được triển khai.

## Monitoring và cải tiến

Theo mỗi release/model version, lưu model IDs, hashes đầu vào, pass rates, distribution means, bottom 10, κ, position-bias rate, false-positive rate và P50/P95/P99. Chỉ lưu prompt/output đã redact; Lê Quang Ngọc phụ trách triage và kiểm tra thủ công các mẫu version conflict/negation.

Baseline hiện tại: factual mean `0.8485`, multi-hop `0.5861` (yếu nhất), adversarial `0.6681`; κ `1.0`; attacks `20/20`; clean FPR `0.0`; input-layer P95 `1042.601 ms`.

Cải tiến có thể kiểm chứng:

1. Lọc/rerank theo trạng thái và ngày hiệu lực để giảm lỗi câu 39, 42, 44; chạy lại cùng 50 câu và so adversarial mean.
2. Retrieve theo từng vế rồi hợp nhất cho multi-hop; mục tiêu nâng multi-hop mean từ `0.5861` lên ≥`0.65`.
3. Sửa prompt/assembly để không nối “Không tìm thấy” sau đáp án hợp lệ như câu 38; theo dõi faithfulness và answer relevancy.
4. Đưa rule/classifier cục bộ trước NeMo LLM, sau đó benchmark lại input P95 mà vẫn giữ attacks ≥18/20 và clean 8/8.
5. Mở rộng ngoài bộ 50/20/8/4, chạy lặp nhiều lần và cảnh báo drift khi metric giảm quá 5 điểm phần trăm hoặc FPR >0.
