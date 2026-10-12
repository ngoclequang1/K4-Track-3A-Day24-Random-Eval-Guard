# Kiểm chứng Phase C live

Người phụ trách: Lê Quang Ngọc — 2A202602664.
Nguồn: `artifacts/guard_results.json`, model guard `gpt-4o-mini`.

Lượt cuối đạt 20/20 attacks, 8/8 clean controls và 4/4 output cases. False-positive rate trên clean controls là 0. Đây là bằng chứng trên bộ mẫu được cấp, chưa chứng minh khả năng chống mọi tấn công thực tế.

Lượt đầu đạt 20/20 attacks nhưng chỉ 1/8 clean controls vì Presidio nhận diện PERSON/LOCATION bằng model tiếng Anh trên tiếng Việt. Đã giới hạn entities PII dùng để chặn vào VN_CCCD, VN_PHONE, PHONE_NUMBER và EMAIL_ADDRESS. Lượt kế tiếp đạt 18/20 attacks và 7/8 clean; câu hỏi chung về độ dài mật khẩu bị NeMo chặn nhầm. Prompt đã làm rõ quy định mật khẩu/MFA được phép, yêu cầu mật khẩu hoặc secrets thực tế bị chặn. Lượt cuối được chạy lại toàn bộ với cấu hình sửa và đạt các số đo trên.

Task 12 đo đủ hai tầng Presidio rồi NeMo input cho mỗi mẫu, dùng 2 warm-up và 20 mẫu timed; percentile nội suy tuyến tính. Input guard P50=850.8324 ms, P95=1042.600975 ms, P99=1090.539875 ms. Budget 500 ms không đạt. API self-check là phần cần tối ưu; phải đo thêm khi thay đổi kiến trúc. RAG, output rail latency và full request latency chưa đo.

Source sau sửa đạt 86 unit tests offline; schema/contract của artifact Phase C đã kiểm tra thành công. Các tests mock kiểm tra interface và logic; artifact live cung cấp kết quả chạy API thực tế.
