# Nhóm thực hiện K4 Track 3A

Tên nhóm: Nhóm Lê Quang Ngọc

Repo chung: https://github.com/ngoclequang1/K4-Track-3A-Day24-Eval-Guard

Trưởng nhóm/người nộp: Lê Quang Ngọc — 2A202602664

Ngày lab/deadline áp dụng: 23:59 ngày 12/10/2026 — Asia/Ho_Chi_Minh (UTC+07:00), trừ khi coach có thông báo khác.

Commit dùng để chấm: sẽ ghi SHA của commit nộp cuối sau khi artifacts và reports hoàn tất.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Lê Quang Ngọc | 2A202602664 | Tích hợp m1–m5; cài môi trường; hoàn thiện và kiểm thử Phase A/B/C; chạy batch live; phân tích và đóng gói bài nộp | `src/m1_chunking.py`–`src/m5_enrichment.py`, `src/phase_a_ragas.py`, `src/phase_b_judge.py`, `src/phase_c_guard.py`, artifacts và reports |

Người tích hợp/chạy batch/nộp link: Lê Quang Ngọc; bằng chứng là các artifacts live, reports và commit nộp cuối.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows; Python 3.11.9; Microsoft Visual C++ Build Tools 2022, MSVC 14.44.35207 x64.

Virtualenv/dependencies/imports: `.venv` full runtime và `.venv-tests` offline; `pip check` không phát hiện dependency hỏng; imports RAGAS, NeMo, Presidio, spaCy, Annoy và m1–m5 thành công. PyArrow 17.0.0 và Torch 2.5.1 CPU được pin để tương thích NumPy 1.26.4/Windows.

Models/Qdrant/50 answers: Qdrant `qdrant/qdrant:v1.9.7` chạy trên 6333/6334; spaCy `en_core_web_lg 3.8.0` load thành công. Do giới hạn RAM, lượt nộp dùng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều) và `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, batch size 1, max_seq_length 512; BGE-M3 chỉ được giữ trong cache và không phải model tạo artifact. Pipeline đã tạo đủ 50 answers live. Enrichment lần đầu chạy xong 102 chunks nhưng kết quả chưa được lưu khi indexing lỗi; lượt nộp dùng raw chunks với `SKIP_ENRICHMENT=1`. Phase C live đạt 20/20 attacks, 8/8 clean và 4/4 output; input-layer P95 1042.600975 ms, vượt budget 500 ms.

## INDIVIDUAL

### LeQuangNgoc-2A202602664

- Phần được giao và phần thực tế đã làm: tích hợp pipeline RAG m1–m5; triển khai Tasks 1–12; chạy experiments, kiểm tra schema và viết ba báo cáo.
- Bằng chứng: các module trong `src/`, bốn JSON trong `artifacts/`, ba báo cáo trong `doc/reports/` và commit nộp cuối.
- Cách kiểm tra: `python -m pytest tests/ -q` cho logic offline; `setup_answers.py --live`, ba phase của `run_experiments.py --live` và `check_lab.py` cho batch thật.
- Điều đã học: phân biệt retrieval/generation metrics, A/B judge và binary calibration, phát hiện position bias, guardrail false positive và phạm vi latency.
- Giới hạn/cách xử lý: kết quả phụ thuộc model/API và bộ test nhỏ; giữ raw rows, model IDs, timestamps và nêu rõ phạm vi đo thay vì suy rộng production readiness.
- Nguồn/AI hỗ trợ nếu có: Codex hỗ trợ setup, triển khai và kiểm thử; kết quả được tự kiểm bằng unit tests, JSON Schema, artifacts live và checker của starter.

## Cập nhật sau khi nộp

Chưa có cập nhật sau khi nộp; mục này sẽ ghi rõ commit, thời điểm và lý do nếu có thay đổi được coach cho phép.
