# Contract: Chuỗi khi lượt không kết thúc bình thường

Mọi chuỗi cố định nằm trong `src/tools/saved_reply.py`: ba câu và sáu mẫu dòng đã chốt ở [spec](../spec.md) phần Assumptions. Không có bản sao thứ hai trong `src/core`, `src/turns`, hay `src/db`.

Ba câu:

- Lần ghi quá hạn: `Chưa chắc thay đổi đã được lưu.`
- Lần ghi bị từ chối: `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`
- Lần đọc quá hạn: `Không thực hiện được yêu cầu này.`

## Gửi mô hình

Khi lượt còn chạy tiếp, nội dung tool trả được gửi lại mô hình không đổi chữ. Trường hiệu lực trên `ToolResult` không nằm trong tin đó.

Khóa dòng log tool vẫn là `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`. Khóa dòng log mô hình vẫn là `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`.

## Chuỗi của lượt

Lượt không kết thúc bình thường khi hết giờ, mô hình lỗi, chạm trần ba vòng, câu trả lời bị cắt, câu trả lời bị từ chối, hoặc văn bản mô hình rỗng hay chỉ khoảng trắng khi lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối.

Nếu đã có lần ghi thành công, lần ghi quá hạn, hoặc lần ghi bị từ chối, chuỗi lượt là bản ghép từ `saved_reply.py`: các dòng đã lưu theo thứ tự ghi xong, rồi câu chưa chắc nếu có lần ghi quá hạn, rồi câu từ chối nếu có lần ghi bị từ chối. Không dùng `Chưa liên lạc được để trả lời lúc này.` và không dùng `Chưa trả lời xong yêu cầu này.`

Chưa có ba dạng đó: giữ câu spec lượt mô hình đã chốt cho lối kết đó.

Văn bản mô hình còn chữ khác khoảng trắng là kết thúc bình thường. Trả đúng văn bản đó, kể cả khi đã ghi.

Văn bản rỗng khi không có lần ghi thành công, lần ghi bị bỏ, và lần ghi bị từ chối vẫn là chuỗi rỗng. Văn bản chỉ khoảng trắng khi không có cả ba trả đúng văn bản đó.

Hủy tác vụ vẫn đi ra ngoài lượt. Thiếu khóa vẫn lỗi trước mọi lời gọi.

Lời hướng dẫn, `PROMPT_VERSION`, bộ định nghĩa tool, `DEFINITIONS_VERSION`, bộ câu đánh giá, và cách chấm không đổi.
