# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

- **Chủ đề:** Introduction to Computer Science.
- **Nguồn/quyền:** OpenStax, [Introduction to Computer Science](https://openstax.org/details/books/introduction-computer-science), OpenStax license.
- **Corpus:** `starter/data/introduction_to_computer_science.pdf`, trang vật lý 30–80, gồm 51 trang có text; sau chuẩn hóa có 145318 ký tự.
- **Chuẩn hóa:** Unicode NFKC, thay non-breaking space, chuẩn hóa khoảng trắng và dòng trống; trang không có text được đánh dấu cảnh báo, không fallback im lặng sang OCR.
- **Embedding:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, local, 384 chiều, vector chuẩn hóa; chi phí 0.
- **Vector store:** PostgreSQL 16.16 + pgvector 0.8.7, Docker local, cosine distance.
- **Metadata:** `document_id`, `source`, `page`, `section`; `section` được dùng làm trường filter.

## Cấu hình và benchmark

- **A:** fixed-size 800 ký tự, overlap 100 (iteration 2; iteration 1 dùng 500/50).
- **B:** gom theo paragraph, tối đa 800 ký tự (iteration 2; iteration 1 dùng 500).
- **C:** giống B, thêm filter `section` khi câu hỏi có filter.
- **Benchmark:** 20 câu hỏi tại `starter/benchmark/questions.json`, gồm 15 dev và 5 test; có 8 câu dùng filter.
- **Tiêu chí chọn:** ưu tiên Evidence Hit@3, sau đó Hit@1 và tài nguyên.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 4/15 | 7/15 | 233 | 2.5941 s | 0 |
| A | test | 0/5 | 1/5 | 233 | 2.5941 s | 0 |
| B | dev | 2/15 | 5/15 | 206 | 2.1290 s | 0 |
| B | test | 0/5 | 0/5 | 206 | 2.1290 s | 0 |
| C | dev | 2/15 | 5/15 | 206 | 2.2599 s | 0 |
| C | test | 0/5 | 0/5 | 206 | 2.2599 s | 0 |

Trace: `starter/results/traces.json`; summary: `starter/results/summary.json`. Đây là kết quả iteration 2.

| Strategy | Coherence trung bình /2 | Metadata đủ và đúng | Filter tuân thủ | Grounding 0/1/2 |
|---|---:|---:|---:|---|
| A | 1.1/2 (10) | 15/15 | N/A | 0:2, 1:2, 2:1; TB 0.8/2 |
| B | 2.0/2 (10) | 15/15 | N/A | 0:3, 1:1, 2:1; TB 0.6/2 |
| C | 2.0/2 (10) | 15/15 | 15/15 | 0:3, 1:1, 2:1; TB 0.6/2 |

Audit chi tiết: `starter/results/manual_audit.json`. Người chấm: tác giả. Coherence dùng cùng 10 vị trí trang 49–58; metadata kiểm tra 5 câu test × top-3; grounding chấm 5 câu test mỗi strategy.

## Phân tích và kết luận sơ bộ

- A đạt kết quả tự động tốt nhất ở iteration 2: Hit@1 dev 4/15 và Evidence Hit@3 dev 7/15.
- Tăng kích thước chunk làm A giảm từ 350 xuống 233 chunk và tăng Evidence Hit@3 test từ 0/5 lên 1/5.
- B/C giảm điểm dev so với iteration 1; vì vậy không được kết luận chunk lớn luôn tốt hơn.
- C tuân thủ filter 15/15 nhưng không cải thiện điểm retrieval so với B.
- `manual_audit.json` là audit của iteration 1; cần chấm lại coherence/grounding nếu dùng iteration 2 làm kết quả cuối.
- Vì test đã được xem trước khi chạy iteration 2, iteration 2 phải được ghi nhận là thử nghiệm sau khi xem test, không phải đánh giá mù ban đầu.
- Hạn chế: test chỉ có 5 câu, corpus chỉ dùng trang 30–80, và Evidence Hit@3 tự động yêu cầu evidence nằm trong một chunk.
