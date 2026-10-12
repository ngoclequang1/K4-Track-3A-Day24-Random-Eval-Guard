# Phân tích lỗi Phase A

Nhóm: Nhóm Lê Quang Ngọc

Người phụ trách: Lê Quang Ngọc — 2A202602664

Nguồn: `artifacts/ragas_50q.json`; run timestamp: `2026-10-12T09:06:11.782147+00:00`. Cả 50 câu dùng generation mode `llm` với `gpt-4o-mini-2024-07-18`; evaluator dùng `gpt-4o-mini` và `text-embedding-3-small`. Pipeline retrieval dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều), reranker `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, 102 raw chunks và `SKIP_ENRICHMENT=1`. Đây là cấu hình giảm RAM thay cho BGE-M3.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---:|---:|---:|
| faithfulness | 1.0000 | 0.3303 | 0.6500 |
| answer_relevancy | 0.5148 | 0.3309 | 0.3722 |
| context_precision | 0.9542 | 0.9250 | 1.0000 |
| context_recall | 0.9250 | 0.7583 | 0.6500 |
| avg_score | 0.8485 | 0.5861 | 0.6681 |

## Bottom 10 và nguyên nhân

| Rank | ID | Distribution | Avg | Worst metric | Diagnosis | Suggested fix |
|---:|---:|---|---:|---|---|---|
| 1 | 40 | multi_hop | 0.0000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 2 | 21 | multi_hop | 0.3333 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 3 | 50 | adversarial | 0.3333 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 4 | 39 | multi_hop | 0.3750 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 5 | 30 | multi_hop | 0.3750 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 6 | 34 | multi_hop | 0.4167 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 7 | 42 | adversarial | 0.4167 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 8 | 44 | adversarial | 0.5000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 9 | 38 | multi_hop | 0.5000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 10 | 32 | multi_hop | 0.5000 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |

Diagnosis tự động ở bảng là giả thuyết dựa trên metric; đối chiếu nội dung cho thấy hai nhóm lỗi cụ thể hơn:

- Retrieval thiếu phủ: câu 40 có precision/recall đều 0 và không lấy được quy trình báo cáo sự cố trong 1 giờ, nên answer là “Không tìm thấy”. Câu 21 chỉ recall 0.5 vì cần ghép chính sách phép năm với bảng lương.
- Generation/refusal sai dù context đủ: câu 32 có precision và recall gần 1 nhưng vẫn trả “Không tìm thấy”; câu 38 lấy đúng dữ kiện và tính đúng 600 USD nhưng nối thêm “Không tìm thấy”, khiến faithfulness/relevancy bằng 0. Đây là lỗi prompt/response assembly, không phải retrieval.
- Version conflict và phủ định: câu 39, 42 và 44 lấy cả văn bản cũ lẫn hiện hành nhưng không chọn được v2.0/v2024; câu 50 đã lấy đúng đoạn cấm NordVPN nhưng vẫn từ chối trả lời. Cần ưu tiên metadata trạng thái/ngày hiệu lực và giữ rõ từ phủ định “không”.

## Matrix và nhóm yếu nhất

| Worst metric | factual | multi_hop | adversarial |
|---|---:|---:|---:|
| faithfulness | 0 | 14 | 3 |
| context_recall | 2 | 0 | 2 |
| context_precision | 0 | 0 | 0 |
| answer_relevancy | 18 | 6 | 5 |

Nhóm yếu theo mean thấp nhất là `multi_hop`, mean `0.5861`. Trên toàn bộ 50 câu, `answer_relevancy` là worst metric xuất hiện nhiều nhất: 29 câu. Multi-hop yếu vì phải ghép nhiều chính sách/điều kiện, trong khi chunk nhỏ và model generation thường chuyển sang “Không tìm thấy” khi bằng chứng nằm ở nhiều context.

Hướng sửa có thể kiểm chứng: thêm metadata version/effective-status vào index; retrieve theo từng vế câu hỏi rồi hợp nhất; rerank với tín hiệu version; sửa prompt để trả lời từng vế và chỉ dùng fallback khi không vế nào có bằng chứng; loại việc nối fallback sau câu trả lời hợp lệ. Chạy lại đúng 50 câu, giữ nguyên evaluator, rồi so sánh riêng multi-hop faithfulness/relevancy và danh sách bottom 10.

## Bẫy adversarial và giới hạn

Adversarial mean `0.6681` thấp hơn factual `0.8485`, chủ yếu ở xung đột phiên bản (42, 44) và phủ định chính sách VPN (50). Chênh lệch này chỉ cho thấy nhóm adversarial khó hơn, không chứng minh pipeline đã nhận diện bẫy. Kết quả bị giới hạn bởi 50 câu, một lượt model/API, model retrieval nhỏ hơn cấu hình ban đầu và việc bỏ enrichment; cần lặp lại trên nhiều seed/model trước khi suy rộng.
