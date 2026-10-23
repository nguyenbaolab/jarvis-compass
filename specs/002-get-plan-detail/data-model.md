# Data Model: Xem chi tiết một kế hoạch

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách tra và chỗ đặt mã: [research.md](./research.md). Hình JSON và hai câu từ chối: [contracts/get-plan-detail.md](./contracts/get-plan-detail.md).

`Plan` và `Subtask` giữ nguyên định nghĩa ở [data-model của F04/F05](../001-create-list-plans/data-model.md). Lát cắt này không thêm trường và không đổi kiểu của hai kiểu đó. `PlanStore` thêm một thao tác đọc theo id. `add` giữ nguyên như data-model F04/F05.

## Đọc một kế hoạch

`normalize_plan_id` trong `src/core/plans.py` nhận `plan_id: str | None` và trả về `str`. Chỉ dùng thư viện chuẩn. Không gọi store.

- `plan_id` là `None`, hoặc `plan_id.strip()` còn rỗng: lỗi miền vì danh tính chưa được đưa.
- Ngược lại trả về `plan_id.strip()`. Khoảng trắng bên trong được giữ. Không NFC, không `casefold`.

`PlanStore.get(plan_id: str) -> Plan | None` trả về kế hoạch có `Plan.id == plan_id`, hoặc `None` khi không có. So từng ký tự, có phân biệt hoa thường. Không tạo `Plan` mới và không sửa kế hoạch đã lưu. Id lưu vẫn là `str(uuid.uuid4())` như data-model F04/F05. Store không chuẩn hóa id.

`MemoryPlanStore` trong `tests/fakes/` cài `get` cùng luật đó.

`get_plan_detail` gọi `normalize_plan_id`, rồi gọi `store.get` với chuỗi trả về. `get` trả `Plan` thì đó là kế hoạch mở ra: `id`, `goal`, `subtasks`, và `created_order` giữ nguyên. `get` trả `None` thì lớp tool báo không có kế hoạch với danh tính đó.

Mục tiêu, một đoạn mục tiêu, hoặc vị trí trong danh sách chỉ khớp khi chuỗi đó tình cờ bằng `Plan.id`. Luật này không coi chúng là danh tính.

## Không thêm vào model

Trạng thái hoàn thành, hạn chót, mức ưu tiên, ghi chú, session, người dùng. Việc con không có danh tính riêng. Mở một kế hoạch không đổi các trường đã lưu.

## Chuyển trạng thái

Không có. Mở thành công hay bị từ chối đều không thêm, không sửa, không xóa kế hoạch.
