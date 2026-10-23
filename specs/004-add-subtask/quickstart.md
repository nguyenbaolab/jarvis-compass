# Quickstart: Thêm một việc con vào kế hoạch đang có

Kiểm chứng F08 trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Hình JSON và ba câu từ chối nằm ở [contracts/add-subtask.md](./contracts/add-subtask.md). Cách đọc model nằm ở [data-model.md](./data-model.md).

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

Lệnh này gồm test health, test F04, test F05, test F06, test F07, và test F08. Kỳ vọng: toàn bộ pass, exit code 0.

Chạy riêng lát cắt:

```text
uv run pytest tests/test_add_subtask.py tests/test_create_plan.py
```

`tests/test_create_plan.py` phải pass mà file đó không bị sửa assertion.

## Việc mỗi test phải chứng minh

Mỗi test tạo một `MemoryPlanStore` mới và truyền vào `store=`. Không dùng store dùng chung. Store này không thêm phương thức. Thêm việc con đi bằng `get` rồi `replace`.

`tests/test_create_plan.py` giữ nguyên assertion. Tạo kế hoạch với tiêu đề là chuỗi vẫn trả cùng mục tiêu, cùng thứ tự, cùng NFC, và cùng cách từ chối bằng `ToolError` khi tiêu đề chỉ khoảng trắng. Không xóa các kiểm tra đó.

`tests/test_add_subtask.py` phủ User Story 1 và 2:

- Tạo một kế hoạch có hai việc con, một `pending` và một `done`. Thêm `"Mua giáo trình"`. Kết quả thêm, lần mở, và lần liệt kê đều có ba việc. Hai việc cũ giữ `id`, `title`, và `status`. Việc mới đứng cuối, `status` là `pending`, `id` khác `id` kế hoạch và khác `id` hai việc cũ.
- Kế hoạch không có việc con. Thêm một tiêu đề. Kết quả có đúng một việc `pending`.
- Thêm hai lần. Lần sau đứng sau lần trước. `id` của việc thêm lần đầu giữ nguyên.
- Tiêu đề `"  Mua giáo trình  "` được lưu thành `"Mua giáo trình"`. Tiêu đề trùng một việc đã có vẫn thành hai việc, hai `id`.
- Ba kế hoạch A, B, C. Thêm vào B. Thứ tự liệt kê không lọc vẫn là C, B, A. Việc cũ của B giữ `status`. Việc mới là `pending`.
- `plan_id` có khoảng trắng hai đầu vẫn trúng đúng kế hoạch. Cùng `id` khác hoa thường thì không trúng.
- `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì câu `Danh tính kế hoạch chưa được đưa.`, kể cả khi tiêu đề cũng trống.
- Danh tính còn nội dung nhưng không có kế hoạch, tiêu đề hợp lệ: câu `Không có kế hoạch với danh tính này.`
- Tiêu đề `None`, `""`, hoặc chỉ khoảng trắng, trên kế hoạch có thật: câu `Việc con không được để trống.` Số việc con không tăng.
- Danh tính không tồn tại và tiêu đề trống: câu `Việc con không được để trống.`
- `create_plan` với một phần tử tiêu đề `None`: cùng câu `Việc con không được để trống.`, và store không thêm kế hoạch đó.
- Sau mỗi lần từ chối, `get_plans` không đổi. Một lần thêm hợp lệ sau đó vẫn thành công.
- Từ khóa liệt kê chỉ nằm trong tiêu đề việc vừa thêm thì kế hoạch không khớp. Từ khóa nằm trong mục tiêu thì vẫn khớp.

Parse `ToolResult.output` thành JSON rồi so trường. Không so nguyên văn chuỗi JSON. So câu `ToolError` đúng từng ký tự với bảng trong contract.

## Ngoài kiểm chứng này

Không gọi `pywrangler`, không mở HTTP, không nối Supabase. Các đường đó thuộc lát cắt khác trong [spec.md](./spec.md).
