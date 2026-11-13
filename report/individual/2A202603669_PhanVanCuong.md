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

- **A:** fixed-size 500 ký tự, overlap 50.
- **B:** gom theo paragraph, tối đa 500 ký tự.
- **C:** giống B, thêm filter `section` khi câu hỏi có filter.
- **Benchmark:** 20 câu hỏi tại `starter/benchmark/questions.json`, gồm 15 dev và 5 test; có 8 câu dùng filter.
- **Tiêu chí chọn:** ưu tiên Evidence Hit@3, sau đó Hit@1 và tài nguyên.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---:|---:|---:|---:|---:|
| A | dev | 2/15 | 6/15 | 350 | 3.7919 s | 0 |
| A | test | 0/5 | 0/5 | 350 | 3.7919 s | 0 |
| B | dev | 3/15 | 6/15 | 313 | 3.2795 s | 0 |
| B | test | 0/5 | 0/5 | 313 | 3.2795 s | 0 |
| C | dev | 3/15 | 6/15 | 313 | 3.2709 s | 0 |
| C | test | 0/5 | 0/5 | 313 | 3.2709 s | 0 |

Trace: `starter/results/traces.json`; summary: `starter/results/summary.json`.

| Strategy | Coherence trung bình /2 | Metadata đủ và đúng | Filter tuân thủ | Grounding 0/1/2 |
|---|---:|---:|---:|---|
| A | 1.1/2 (10) | 15/15 | N/A | 0:2, 1:2, 2:1; TB 0.8/2 |
| B | 2.0/2 (10) | 15/15 | N/A | 0:3, 1:1, 2:1; TB 0.6/2 |
| C | 2.0/2 (10) | 15/15 | 15/15 | 0:3, 1:1, 2:1; TB 0.6/2 |

Audit chi tiết: `starter/results/manual_audit.json`. Người chấm: tác giả. Coherence dùng cùng 10 vị trí trang 49–58; metadata kiểm tra 5 câu test × top-3; grounding chấm 5 câu test mỗi strategy.

## Phân tích và kết luận sơ bộ

- B và C đạt Hit@1 dev 3/15, cao hơn A 2/15.
- B và C có 313 chunk, ít hơn A 350 chunk, đồng thời ingest nhanh hơn.
- C chưa cải thiện điểm tự động so với B trên bộ dev hiện tại.
- Cả ba cấu hình đạt 0/5 trên test theo proxy Evidence Hit@3, nhưng audit thủ công cho thấy q18 vẫn có grounding tốt ở cả ba strategy.
- A có coherence thấp hơn B/C do fixed-size thường cắt giữa ý; B/C đạt 2.0/2 trên mẫu coherence.
- C tuân thủ filter 15/15 nhưng không cải thiện grounding so với B; đúng filter không đảm bảo lấy được evidence tốt.
- Hạn chế: test chỉ có 5 câu, corpus chỉ dùng trang 30–80, và Evidence Hit@3 tự động yêu cầu evidence nằm trong một chunk.
