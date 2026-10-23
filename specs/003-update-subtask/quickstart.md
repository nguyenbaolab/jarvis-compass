# Quickstart: Đánh dấu việc con xong hoặc chưa xong

Kiểm chứng F07 trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Hình JSON và năm câu từ chối nằm ở [contracts/update-subtask.md](./contracts/update-subtask.md). Cách đọc model nằm ở [data-model.md](./data-model.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và [uv](https://docs.astral.sh/uv/).
- Không tạo file `.env`. Tool không đọc cấu hình.

## Chuẩn bị

```text
uv sync
```

## Chạy

```text
uv run pytest
```

Lệnh này gồm test health, test F04, test F05, test F06, và test F07. Kỳ vọng: toàn bộ pass, exit code 0.

Chạy riêng lát cắt:

```text
uv run pytest tests/test_update_subtask.py
```

## Việc mỗi test phải chứng minh

Mỗi test tạo một `MemoryPlanStore` mới và truyền vào `store=`. Không dùng store dùng chung. `add` giữ nguyên `id` và `status` của việc con đã được `normalize_new_plan` cấp. `replace` chỉ đổi kế hoạch có cùng `id`.

`tests/test_create_plan.py`, `tests/test_get_plans.py`, và `tests/test_get_plan_detail.py` vẫn chứng minh mục tiêu, thứ tự, NFC, lọc từ khóa, và câu từ chối cũ. Assertion hình việc con đổi từ chỉ `title` sang đủ `id`, `title`, `status`. Việc con vừa tạo có `status` là `pending`. Không xóa các kiểm tra đó.

`tests/test_update_subtask.py` phủ User Story 1 và 2:

- Tạo một kế hoạch có hai việc con. Kết quả tạo, lần mở, và lần liệt kê đều có hai `id` khác nhau, khác `id` kế hoạch, và cả hai `status` là `pending`. `title` đúng nội dung đã lưu.
- Đặt việc thứ nhất thành `done` bằng `id` kế hoạch và `id` việc đó. `update_subtask` trả về JSON cùng hình với `get_plan_detail`: việc đó `done`, việc kia `pending`, cùng `id`, cùng `title`, cùng thứ tự, cùng mục tiêu.
- Đặt lại việc đó thành `pending`. Mở và liệt kê đều thấy `pending`.
- Đặt lại `done` khi việc đang `done`. Thành công, vẫn `done`, và store không cần một kế hoạch mới.
- Hai việc con cùng `title`. Đặt `done` bằng `id` của việc đứng trước. Việc kia vẫn `pending`.
- Mọi việc con đều `done`. Kế hoạch vẫn có trong `get_plans` không lọc, cùng `id` kế hoạch.
- `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì câu `Danh tính kế hoạch chưa được đưa.`, kể cả khi `subtask_id` và `status` cũng không dùng được.
- Danh tính kế hoạch còn nội dung, `subtask_id` trống, `status` không hợp lệ: câu `Danh tính việc con chưa được đưa.`, kể cả khi không có kế hoạch với danh tính đó.
- Hai danh tính còn nội dung, `status` là `xong` hoặc `Done`: câu `Trạng thái việc con chỉ nhận pending hoặc done.`, kể cả khi không có kế hoạch đó.
- Hai danh tính còn nội dung, `status` là `done`, nhưng không có kế hoạch: câu `Không có kế hoạch với danh tính này.`
- Kế hoạch A nhận `id` việc con của kế hoạch B và `status` `done`: câu `Kế hoạch này không có việc con với danh tính này.` Cả hai kế hoạch giữ trạng thái cũ.
- Đưa `title` hoặc vị trí `"1"` khi chuỗi đó không phải `id` việc con, cùng `status` `done`: cùng câu việc con không thuộc kế hoạch.
- `status` là `" done "` thì thành `done`. Danh tính có khoảng trắng hai đầu vẫn trúng. Danh tính viết hoa so với `id` đã lưu thì không trúng.
- Sau mỗi lần từ chối, `get_plans` không đổi. Một lần đặt `done` sau đó vẫn thành công.

Parse `ToolResult.output` thành JSON rồi so trường. Không so nguyên văn chuỗi JSON. So câu `ToolError` đúng từng ký tự với bảng trong contract.

## Ngoài kiểm chứng này

Không gọi `pywrangler`, không mở HTTP, không nối Supabase. Các đường đó thuộc lát cắt khác trong [spec.md](./spec.md).
