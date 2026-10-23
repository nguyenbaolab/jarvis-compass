# Data Model: Đánh dấu việc con xong hoặc chưa xong

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách chọn trường, danh tính, và chỗ đặt mã: [research.md](./research.md). Hình JSON và năm câu từ chối: [contracts/update-subtask.md](./contracts/update-subtask.md).

`Plan` giữ các trường đã chốt ở [data-model của F04/F05](../001-create-list-plans/data-model.md). Lát này không thêm trường cho `Plan` và không đổi nghĩa “có mặt trong store là đang hoạt động”.

## Subtask

Dataclass `frozen` trong `src/core/plans.py`. Một việc con thuộc đúng một `Plan`, nằm trong `Plan.subtasks`.

`SubtaskStatus` là `class SubtaskStatus(StrEnum)` trong cùng file, thuộc thư viện chuẩn `enum`. `PENDING = "pending"`. `DONE = "done"`.

| Trường | Kiểu | Ai gán | Quy tắc |
|--------|------|--------|---------|
| `id` | `str` | `normalize_new_plan` | `str(uuid.uuid4())` lúc tạo việc con để lưu. Giữ nguyên khi trạng thái đổi. Khác `id` của kế hoạch và khác `id` của mọi việc con khác do cùng hàm tạo ra. Không suy từ vị trí hay từ `title`. |
| `title` | `str` | người gọi, sau chuẩn hóa | Giữ nghĩa và cách chuẩn hóa ở data-model F04/F05: NFC rồi `strip`, còn nội dung. Lát này không sửa `title`. |
| `status` | `SubtaskStatus` | `normalize_new_plan`, rồi `replace_subtask_status` | Lúc tạo là `SubtaskStatus.PENDING`. Sau cập nhật thành công là đúng thành viên đã yêu cầu. JSON xuất chuỗi `"pending"` hoặc `"done"`. |

Vị trí việc con vẫn là chỉ số trong `tuple`, bắt đầu từ 0. Cập nhật không đổi chỉ số.

`normalize_new_plan` vẫn nhận `goal: str | None` và `subtasks: list[str] | None`. Đầu vào tạo kế hoạch vẫn là danh sách chuỗi, không phải object. Mỗi chuỗi còn nội dung thành một `Subtask` đủ ba trường. Hai chuỗi cùng `title` sau chuẩn hóa vẫn là hai `Subtask`, hai `id`.

## Hàm miền mới

Nằm ở `src/core/plans.py`. Không gọi store. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

| Hàm | Việc phải làm |
|-----|----------------|
| `normalize_subtask_id(subtask_id: str \| None) -> str` | `None`, hoặc `strip()` còn rỗng: `PlanDomainError` với câu danh tính việc con chưa được đưa. Ngược lại trả về chuỗi đã `strip`. Không NFC, không `casefold`. |
| `normalize_subtask_status(status: str \| None) -> SubtaskStatus` | `None`, `strip()` còn rỗng, hoặc phần còn lại không phải `pending` hay `done`: `PlanDomainError` với câu trạng thái chỉ nhận `pending` hoặc `done`. Ngược lại trả về `SubtaskStatus.PENDING` hoặc `SubtaskStatus.DONE`. |
| `replace_subtask_status(plan: Plan, subtask_id: str, status: SubtaskStatus) -> Plan` | `subtask_id` và `status` đã qua hai hàm trên. Không có việc con với `id` đó trong `plan.subtasks`: `PlanDomainError` với câu kế hoạch này không có việc con đó. Có và `status` đang bằng thành viên đó: trả về đúng `plan`. Có và khác: trả về `Plan` mới, cùng `id`, `goal`, `created_order`, cùng thứ tự, chỉ việc đó đổi `status`. |

`normalize_plan_id` giữ nguyên hành vi đã chốt ở F06.

Thứ tự gọi khi cập nhật, trước khi đụng store: `normalize_plan_id`, rồi `normalize_subtask_id`, rồi `normalize_subtask_status`. Tra `store.get` và `replace_subtask_status` đứng sau ba bước đó. Chi tiết câu chữ và thứ tự nằm ở contract.

## PlanStore

`Protocol` trong `src/core/plans.py`. Thêm một thao tác. `add`, `list_newest_first`, và `get` giữ hợp đồng đã có, với một điểm: `add` lưu đúng tuple `Subtask` đã có `id` và `status`, không cấp lại `id` việc con.

| Thao tác | Việc phải làm |
|----------|----------------|
| `replace(plan: Plan) -> None` | Tìm kế hoạch có `Plan.id` bằng `plan.id`. Thay bằng `plan` được truyền. Không đổi `created_order`. Không thêm kế hoạch khi chưa có `id` đó. Không đụng kế hoạch khác. |

`MemoryPlanStore` trong `tests/fakes/` cài `replace` trên danh sách của đúng instance đó. Không đưa class này vào `src/`.

## Chuyển trạng thái

Chỉ trạng thái của một việc con đổi.

| Từ | Tới | Khi nào |
|----|-----|---------|
| `pending` | `done` | Cập nhật thành công với mã `done`. |
| `done` | `pending` | Cập nhật thành công với mã `pending`. |
| `pending` | `pending` | Cập nhật thành công, store không ghi lại. |
| `done` | `done` | Cập nhật thành công, store không ghi lại. |

Không có đường ra khỏi tập này trong lát cắt. `skipped` không được nhận. `Plan` không có chuyển trạng thái: kế hoạch vẫn nằm trong store và vẫn được liệt kê khi không lọc, kể cả khi mọi việc con là `done`.

## Không lưu trong lát cắt này

Hạn chót, mức ưu tiên, ghi chú, trạng thái bỏ qua, session, người dùng. Một người dùng duy nhất đã chốt ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Store không có khóa người dùng.
