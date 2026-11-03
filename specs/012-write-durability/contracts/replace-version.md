# Contract: Version khi ghi kế hoạch

`PlanStore` vẫn bốn phương thức: `add`, `list_newest_first`, `get`, `replace`. `replace(plan)` lấy version từ `plan.version`. Không thêm đối số.

## Đọc

`get` và `list_newest_first` trả `Plan.version` đúng số trong kho. Kế hoạch vừa `add` có `version` bằng 0.

## Ghi đè

`replace` thành công chỉ khi kho đang giữ đúng `plan.version`. Kiểm và tăng phải atomic trong một RPC: một `update` với `where id` và `version = expected_version`, không có hàng thì mới phân biệt `plan_missing` và `plan_version_conflict`; hoặc `select ... for update` rồi so. Không `select` rồi so mà không khóa. So bằng tay thì `is distinct from`. Sau khi thành công, lần đọc sau thấy `plan.version + 1` và thấy đủ goal cùng việc con của lần ghi đó.

`_PLAN_COLUMNS` phải chọn `version`. Thiếu thì `PlanRow.version` bắt buộc làm mọi lần đọc lỗi, nên `get` và `list_newest_first` không trả được số.

Sau khi drop chữ ký cũ và tạo `replace_plan(uuid, text, jsonb, integer)`, hàm mới không thừa hưởng quyền hàm cũ. Ghi `revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated`, rồi `grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role`.

`replace` từ chối khi số lệch. Ném `PlanConflictError`. Kho giữ nguyên hàng và việc con như trước lời gọi đó.

Không có hàng: vẫn `PlanDomainError` với câu đã có `Không có kế hoạch với danh tính này.` Không dùng câu từ chối.

## Tool

`add_subtask`, `update_subtask`, và `set_subtask_note` đọc plan rồi `replace` plan đã sửa. `version` trên plan đưa vào `replace` là số vừa đọc, không phải số đã tăng.

`PlanConflictError` thành đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` Cờ lỗi bật. Không gọi `replace` lần thứ hai. Lỗi đi về mô hình như mọi lỗi tool: chữ đó, không thêm chữ.

`create_plan` chỉ `add`. Không kiểm version. Quá hạn của `add` là lần ghi chưa chắc, không phải xung đột.

JSON thành công không có khóa `version`.
