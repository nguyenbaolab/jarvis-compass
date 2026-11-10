# Câu cảnh báo tải

Tool dựng câu này khi lần gọi đầu chưa ghi vì vượt. Pytest khóa đúng các câu dưới. Câu của tool là chữ khóa. Mô hình được nói bằng chữ của mình, miễn nêu đủ ngày, tổng giờ, quỹ, ghi chú tính tạm khi có, danh sách dời đúng thứ tự và đúng ngày khi có, nói rõ chưa ghi hoặc hỏi chủ bot, không tự cộng giờ và không bịa việc. Ngày/tháng vẫn hai chữ số. Tỉ lệ nói đủ các phần đó là việc của eval bộ v3, không phải assert pytest.

Ngày viết `ngày/tháng`, mỗi phần hai chữ số, không năm, cùng dạng với digest (`02d/02d`). 6 tháng 11 là `06/11`, 12 tháng 11 là `12/11`. Ngày trong câu trùng hạn giữ dạng ISO của `_clash_text`.

Một ngày, có việc chưa sức, có danh sách dời:

```text
Lần này chưa ghi. Ngày 12/11 sẽ có 11 giờ trên quỹ 8 giờ (tính tạm: 2 việc chưa có sức, mỗi việc tính 3 giờ). Nếu vẫn ghi thì dời: 1. Học module 3 (kế hoạch Azure) sang 13/11. 2. Luyện nói (kế hoạch Phần Lan) sang 14/11.
```

Luật ghép:

- Mở bằng `Lần này chưa ghi.` đúng một lần.
- Mỗi ngày vượt một mệnh đề `Ngày {ngày/tháng} sẽ có {tổng} giờ trên quỹ {quỹ} giờ`, theo thứ tự code trả.
- Số việc tính tạm lớn hơn 0 thì mệnh đề đó thêm ` (tính tạm: {số} việc chưa có sức, mỗi việc tính 3 giờ)`. Số 0 thì không có đoạn đó và không có chữ `tính tạm`.
- Danh sách dời không rỗng thì thêm ` Nếu vẫn ghi thì dời:` rồi từng việc `{số}. {tiêu đề} (kế hoạch {tên kế hoạch}) sang {ngày/tháng}.` Số bắt đầu từ 1, đúng thứ tự mảng.
- Danh sách rỗng thì không có câu `Nếu vẫn ghi thì dời` và không bịa việc.

Nhiều ngày dùng cùng một câu mở, rồi một mệnh đề cho từng ngày, rồi một danh sách dời chung nếu có việc.

Vừa vượt vừa trùng hạn, chỉ ở `reschedule_subtasks`: sau các mệnh đề tải là `Kế hoạch {tên} cũng đến hạn {YYYY-MM-DD}.` Không lặp `Lần này chưa ghi.` Ngày trùng trong câu này giữ dạng ISO của `_clash_text` khi chỉ có trùng hạn. Lần chỉ trùng hạn, không vượt, vẫn là câu `_clash_text` hiện tại, nguyên văn.

Lần ghi được một phần rồi lỗi:

```text
Đã ghi lần đang xin. Đã dời: {tiêu đề đã dời}. Chưa dời: {tiêu đề chưa dời}.
```

Chưa dời được việc nào thì `Đã dời:` để trống sau dấu hai chấm. Lần xin của chủ bot lỗi trước khi có lần dời thì không dùng câu này. Lần đó vẫn là lỗi version hoặc lỗi tool đang có.
