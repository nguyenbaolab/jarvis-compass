# Quickstart: Xem chi tiết một kế hoạch

Kiểm chứng F06 trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Hình JSON và hai câu từ chối nằm ở [contracts/get-plan-detail.md](./contracts/get-plan-detail.md). Cách đọc model nằm ở [data-model.md](./data-model.md).

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

Lệnh này gồm test health, test F04, test F05, và test F06. Kỳ vọng: toàn bộ pass, exit code 0.

Chạy riêng lát cắt:

```text
uv run pytest tests/test_get_plan_detail.py
```

## Việc mỗi test phải chứng minh

Test tạo một `MemoryPlanStore` mới trong từng test và truyền vào `store=`. Store này có `get(plan_id: str) -> Plan | None`: trả về kế hoạch khi `id` trùng chuỗi được truyền, và trả `None` khi không có. Không dùng store dùng chung giữa các test. Không sửa `tests/test_create_plan.py` hay `tests/test_get_plans.py`.

`get_plan_detail` mở kế hoạch bằng `store.get` sau `normalize_plan_id`. `plan_id` là `None`, rỗng, hoặc chỉ khoảng trắng thì lỗi miền ở core, trước `get`. `get` trả `None` thì câu không có kế hoạch.

`tests/test_get_plan_detail.py` phủ User Story 1 và 2:

- Tạo một kế hoạch có mục tiêu và hai việc con, rồi mở bằng `id` vừa trả về. JSON mở ra có đúng `id`, đúng mục tiêu, và đúng hai object `{"title": ...}` theo thứ tự đã lưu.
- Tạo một kế hoạch không có việc con, rồi mở bằng `id` của nó. `subtasks` là mảng rỗng.
- Tạo ba kế hoạch, mở bằng `id` của kế hoạch giữa. JSON là kế hoạch đó, không phải hai kế hoạch kia.
- Cùng một `id`, `get_plan_detail` và phần tử tương ứng trong `get_plans` có cùng `id`, cùng `goal`, cùng `subtasks`.
- `id` có khoảng trắng hai đầu vẫn mở đúng kế hoạch. `id` viết hoa so với id đã lưu thì `ToolError` với câu không có kế hoạch.
- Mở bằng mục tiêu đã lưu, khi mục tiêu đó không bằng `id`, thì `ToolError` với câu không có kế hoạch.
- `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì `ToolError` với câu danh tính chưa được đưa. Câu này khác câu không có kế hoạch.
- Sau mỗi lần từ chối, số kế hoạch và nội dung `get_plans` không đổi. Một lần mở sau bằng `id` đã lưu vẫn thành công.
- Một lần mở thành công không đổi kết quả `get_plans`.

Parse `ToolResult.output` thành JSON rồi so trường. Không so nguyên văn chuỗi JSON. So câu `ToolError` đúng từng ký tự với bảng trong contract.

## Ngoài bước kiểm chứng này

Không gọi `uv run pywrangler dev`. Không cần database đang chạy. `src/db/client.py` vẫn là stub.
