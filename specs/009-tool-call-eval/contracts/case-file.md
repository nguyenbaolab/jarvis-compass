# Contract: File bộ câu và bộ dữ liệu

UTF-8 JSON. Đọc bằng `json`, không Pydantic. Sai JSON, thiếu trường, sai kiểu, id trùng, nhóm lạ, `kind` không khớp nhóm, tên bộ dữ liệu không rỗng mà không có file, mục tiêu trùng, tiêu đề trùng, hoặc kỳ vọng ghi đã đúng từ bộ dữ liệu: từ chối cả bộ trước lượt đầu. Không ghi file kết quả. Không gọi mô hình.

NFC áp lên mọi chuỗi chữ khi đọc: id, nhóm, câu người dùng, tên bộ dữ liệu, mục tiêu, tiêu đề, ghi chú, trạng thái trước khi đưa vào `SubtaskStatus`.

`dataset` rỗng sau strip: kho không có kế hoạch, không mở file.

File bộ dữ liệu chỉ được là `evals/datasets/<tên>.json`, `tên` đã NFC và strip, không chứa dấu phân cách thư mục.

Dựng kho, mỗi lần chạy, từ đầu:

1. `goal_text, _ = normalize_new_plan(goal, None)`.
2. Với mỗi việc con: `base = new_subtask(title)`, `note = normalize_subtask_note(note)`, rồi `Subtask(id=base.id, title=base.title, status=SubtaskStatus(status), note=note)`.
3. `await MemoryPlanStore().add(goal_text, tuple(items))` theo thứ tự trong file.

Không gọi hàm có tên bắt đầu bằng `_`. Không viết lớp kho khác. Không sửa `tests/fakes/memory_plan_store.py`.

Bộ câu v1: file sẽ là `evals/cases/v1.json` khi người giữ đưa nguyên văn. Plan không điền mảng `cases`.
