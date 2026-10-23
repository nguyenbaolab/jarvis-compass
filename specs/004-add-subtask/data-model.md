# Data Model: Thêm một việc con vào kế hoạch đang có

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách chọn hàm và chỗ đặt mã: [research.md](./research.md). Hình JSON và ba câu từ chối: [contracts/add-subtask.md](./contracts/add-subtask.md).

`Plan`, `Subtask`, và `SubtaskStatus` giữ trường và kiểu đã chốt ở [data-model của F07](../003-update-subtask/data-model.md). Lát này không thêm trường, không đổi kiểu, và không đổi nghĩa “có mặt trong store là đang hoạt động”.

## Subtask mới

Một lần thêm tạo đúng một `Subtask` bằng `new_subtask`, rồi gắn vào cuối `Plan.subtasks`.

| Việc | Ai làm | Quy tắc |
|------|--------|---------|
| Chuẩn hóa tiêu đề | `new_subtask` | Cùng `_nfc_strip` đã dùng khi tạo kế hoạch: NFC rồi bỏ khoảng trắng hai đầu. Chữ bên trong giữ nguyên. |
| Từ chối tiêu đề | `new_subtask` | `title` là `None`, hoặc chuỗi đã chuẩn hóa còn rỗng: `PlanDomainError` với câu `Việc con không được để trống.` |
| Cấp danh tính | `new_subtask` | `str(uuid.uuid4())`. Không do người gọi chọn. Không suy từ vị trí hay từ tiêu đề. |
| Trạng thái ban đầu | `new_subtask` | `SubtaskStatus.PENDING`. Hàm không nhận trạng thái. |

`normalize_new_plan` không còn tự dựng `Subtask` trong vòng lặp. Mỗi phần tử của danh sách tiêu đề đi qua `new_subtask`. Danh sách `None` hoặc rỗng vẫn cho tuple việc con rỗng, không gọi `new_subtask`. Luật mục tiêu trống giữ nguyên trong `normalize_new_plan`.

`replace_subtask_status` không gọi `new_subtask`. Đổi trạng thái giữ `id` và `title` đã có.

## Hàm miền

Nằm ở `src/core/plans.py`. Không gọi store. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

| Hàm | Việc phải làm |
|-----|----------------|
| `new_subtask(title: str \| None) -> Subtask` | Đúng một chỗ cho chuẩn hóa, từ chối, cấp `id`, và `PENDING`. `None` bị từ chối trước khi chuẩn hóa. |
| `append_subtask(plan: Plan, subtask: Subtask) -> Plan` | `subtask` đã là `Subtask` hợp lệ. Trả về `Plan` mới, cùng `id`, `goal`, `created_order`. Tuple mới là các việc cũ theo thứ tự, rồi `subtask` ở cuối. Không chuẩn hóa lại tiêu đề và không cấp lại `id`. |

`normalize_plan_id` giữ nguyên hành vi đã chốt ở F06 và F07.

Thứ tự gọi khi thêm, trước khi đụng store: `normalize_plan_id`, rồi `new_subtask`. `store.get` và `append_subtask` đứng sau hai bước đó. Chi tiết câu chữ nằm ở contract.

## PlanStore

`Protocol` trong `src/core/plans.py` không thêm thao tác. Lát này chỉ gọi hai thao tác đã có:

| Thao tác | Việc phải làm trong lát này |
|----------|------------------------------|
| `get(plan_id: str) -> Plan \| None` | Nhận danh tính đã `strip`. Trả kế hoạch có đúng `id`, hoặc `None`. |
| `replace(plan: Plan) -> None` | Ghi `Plan` do `append_subtask` trả về. Cùng `id`. Không thêm kế hoạch. Không đổi `created_order`. Không đụng kế hoạch khác. |

`MemoryPlanStore` trong `tests/fakes/` đã cài hai thao tác đó. Lát này không sửa class đó và không đưa class vào `src/`.

`add` và `list_newest_first` giữ hợp đồng đã có. `add_subtask` không gọi `add`.

## Không có chuyển trạng thái mới

Việc con mới bắt đầu ở `pending`. Các việc đã có giữ nguyên `pending` hoặc `done`. Lát này không có đường từ `pending` sang `done` hay ngược lại. Đường đó vẫn là `replace_subtask_status` của F07.

`Plan` không có chuyển trạng thái. Thêm một việc `pending` không đưa kế hoạch ra khỏi store và không đổi `created_order`.

## Không lưu trong lát cắt này

Vị trí chèn do người gọi chọn, hạn chót, mức ưu tiên, ghi chú, trạng thái bỏ qua, session, người dùng. Một người dùng duy nhất đã chốt ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Store không có khóa người dùng.
