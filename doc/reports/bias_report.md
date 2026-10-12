# Đánh giá LLM Judge Phase B

Nhóm: Nhóm Lê Quang Ngọc

Người phụ trách: Lê Quang Ngọc — 2A202602664

Nguồn: `artifacts/judge_results.json`; run timestamp: `2026-10-12T09:06:44.123971+00:00`. Generation model là `gpt-4o-mini-2024-07-18`; judge model là `gpt-4o-mini`. A lấy từ `artifacts/answers_50q.json:answer`, B từ `fixtures/human_labels_10q.json:model_answer`, reference từ `fixtures/test_set_50q.json:ground_truth`.

## Năm cặp A/B và hai lượt

Lượt 2 đảo vị trí candidate trong prompt; winner và scores dưới đây đã được quy về nhãn A/B gốc.

| ID | A (pipeline) | B (supplied) | Pass 1 | Pass 2 | Final | Consistent | Scores P1 A/B | Scores P2 A/B |
|---:|---|---|---|---|---|---|---|---|
| 1 | 3 ngày làm việc | 3 ngày có lương | B | B | B | yes | 0.8 / 1.0 | 0.8 / 1.0 |
| 5 | CEO phê duyệt | Giám đốc phòng ban | A | A | A | yes | 1.0 / 0.0 | 1.0 / 0.0 |
| 12 | 1 tháng lương, nêu điều kiện ≥6 tháng | 1 tháng lương | A | tie | tie | no | 1.0 / 0.8 | 1.0 / 1.0 |
| 21 | Không tìm thấy | 18 ngày và lương 20–35 triệu | B | B | B | yes | 0.0 / 1.0 | 0.0 / 1.0 |
| 41 | 15 ngày theo v2024 | 12 ngày theo v2023 | A | A | A | yes | 1.0 / 0.0 | 1.0 / 0.0 |

Position bias count/rate là `1/5 = 0.20`. Case 12 đổi từ A sang tie sau swap: hai answer cùng kết luận nhưng A nêu điều kiện đầy đủ hơn, nên đây là dấu hiệu judge nhạy vị trí/độ chi tiết. Bốn case còn lại ổn định và phù hợp reference.

Trong 4 case decisive, answer dài hơn thắng 3 lần, verbosity win rate `0.75` (`a_wins_a_longer=1`, `b_wins_b_longer=2`). Tuy nhiên ở các case 1 và 21 phần dài hơn cũng mang thêm thông tin đúng; tỷ lệ này là tín hiệu cần audit chứ chưa đủ kết luận judge thiên vị độ dài.

## Calibration đúng model_answer

Prompt binary chỉ nhận question, supplied model_answer và reference; human labels/notes chỉ được dùng sau khi judge trả kết quả.

| ID | Model answer rút gọn | Judge | Human | Agree |
|---:|---|---:|---:|---|
| 1 | 3 ngày làm việc có lương | 1 | 1 | yes |
| 5 | Giám đốc phòng ban duyệt 55 triệu | 0 | 0 | yes |
| 12 | Tối thiểu 1 tháng lương | 1 | 1 | yes |
| 21 | 18 ngày; lương 20–35 triệu | 1 | 1 | yes |
| 23 | Hoàn trả 25 triệu sau 8 tháng | 1 | 1 | yes |
| 29 | Trưởng phòng; phạt 2%/tháng | 0 | 0 | yes |
| 33 | 19 ngày; phụ cấp 1,5 triệu | 1 | 1 | yes |
| 41 | 12 ngày phép | 0 | 0 | yes |
| 46 | Thử việc không có phép năm | 1 | 1 | yes |
| 50 | Được dùng VPN cá nhân | 0 | 0 | yes |

Observed agreement là `10/10 = 1.0`. Tỷ lệ positive của cả judge và human là `0.6`, negative là `0.4`, nên chance agreement `Pe = 0.6² + 0.4² = 0.52`. Cohen’s κ = `(1.0 - 0.52) / (1 - 0.52) = 1.0`.

## Giới hạn và cách dùng judge

κ cao hơn ngưỡng 0.6 nhưng chỉ trên 10 mẫu và cùng một lượt judge model. Pairwise chỉ có 5 cặp; case 12 đã cho thấy bất ổn khi đảo vị trí. Vì vậy judge không được xem là đáp án tuyệt đối: production gate nên chạy swap, giữ tie khi bất đồng, audit thủ công các case version/negation và lấy mẫu lớn hơn với nhiều lần chạy. Nếu lệch human, cần kiểm tra prompt, reference và nội dung reasoning trước khi đổi nhãn.
