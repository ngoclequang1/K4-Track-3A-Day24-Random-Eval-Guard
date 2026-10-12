# Cấu hình model trên máy RAM 8 GB

Theo lựa chọn của Lê Quang Ngọc, pipeline chuyển khỏi BGE-M3 và BGE-reranker-v2-m3 vì RAM trống dưới 1 GB khiến indexing bị paging nặng.

- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions.
- Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`.
- Generation/judge/guard: `gpt-4o-mini`; evaluator: `gpt-4o-mini` và `text-embedding-3-small`.
- Dense encode dùng FP16, 2 CPU threads, batch size 1, giới hạn 512 tokens; rerank batch size 1 và giới hạn 512 tokens.
- Setup dùng 102 raw chunks với `SKIP_ENRICHMENT=1` sau lượt enrichment không được lưu vì lỗi indexing. Các kết quả đánh giá phải được diễn giải theo cấu hình này.

Model cards: [embedding](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [reranker](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).

Đây là thay đổi cấu hình thực nghiệm, không phải kết quả đo chất lượng. Artifacts chỉ được tạo sau khi pipeline và API thực sự chạy thành công.
