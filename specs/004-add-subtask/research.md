# Research: Thêm một việc con vào kế hoạch đang có

Quyết định cho lát cắt F08 `add_subtask`. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Ràng buộc cách làm do người dùng chốt khi gọi `/speckit-plan`. Nơi đặt model và chiều phụ thuộc đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011. Cách kiểm danh tính kế hoạch và cách ghi đè một kế hoạch đã chốt ở [research của F07](../003-update-subtask/research.md). Tài liệu này chỉ ghi cách lát cắt này tuân các nơi đó.

## 1. Một hàm dựng việc con mới

**Decision**: Thêm `new_subtask(title: str | None) -> Subtask` trong `src/core/plans.py`. Hàm này là chỗ duy nhất làm bốn việc: chuẩn hóa tiêu đề, từ chối tiêu đề thiếu hoặc rỗng, cấp `id`, đặt `SubtaskStatus.PENDING`. `title` là `None`, hoặc `_nfc_strip(title)` còn rỗng, thì `PlanDomainError` với đúng câu `Việc con không được để trống.` Kiểm `None` đứng trước `_nfc_strip`. Tiêu đề còn nội dung thì trả về `Subtask(id=str(uuid.uuid4()), title=<dạng đã chuẩn hóa>, status=SubtaskStatus.PENDING)`. `normalize_new_plan` gọi `new_subtask` cho từng chuỗi trong danh sách. `add_subtask` gọi cùng hàm đó. Không có bản sao của khối chuẩn hóa, từ chối, `uuid`, hay `PENDING` ở chỗ khác.

**Rationale**: Người dùng cấm chép luật dựng việc con. `normalize_new_plan` hôm nay đang viết khối đó trong vòng lặp. Đưa khối đó vào một hàm rồi để cả tạo kế hoạch và F08 gọi hàm đó giữ một luật. `_nfc_strip` đã có và vẫn là cách NFC rồi `strip`. Test `create_plan` với chuỗi vẫn thấy cùng tiêu đề, cùng thứ tự, cùng trạng thái `pending`. `replace_subtask_status` vẫn tạo `Subtask` khi đổi trạng thái: việc đó giữ `id` và `title` đã có, không phải luật dựng việc con mới, nên không đi qua `new_subtask`.

**Alternatives considered**: Để vòng lặp trong `normalize_new_plan` và viết lại khối đó trong tool — đúng kiểu chép mà người dùng cấm. Tách “chuẩn hóa tiêu đề” và “cấp id” thành hai hàm — người dùng gom bốn việc vào đúng một hàm. Đưa `new_subtask` vào `src/tools/` — core không được phụ thuộc tools, và `normalize_new_plan` đang ở core.

## 2. Thêm vào cuối bằng get rồi replace

**Decision**: `append_subtask(plan: Plan, subtask: Subtask) -> Plan` trong `src/core/plans.py`. Hàm không chuẩn hóa, không cấp `id`, không gọi store. Trả về `Plan` mới: cùng `id`, cùng `goal`, cùng `created_order`, tuple cũ theo thứ tự rồi `subtask` đứng cuối. Các phần tử cũ là cùng object. `add_subtask` gọi `store.get` sau khi `normalize_plan_id` và `new_subtask` đã trả về. `get` trả `None` thì lớp tool ném `Không có kế hoạch với danh tính này.` Ngược lại tool gọi `append_subtask` rồi `store.replace`. `PlanStore` không thêm phương thức. `MemoryPlanStore` không sửa. `replace` đã có: thay đúng kế hoạch cùng `id`, không thêm kế hoạch, không đụng kế hoạch khác.

**Rationale**: Người dùng bắt dùng lại `get` và `replace`. `Plan` và `Subtask` đều `frozen`, nên không sửa tuple tại chỗ. `created_order` giữ nguyên thì vị trí kế hoạch khi liệt kê không lọc không đổi. `replace` của F07 đã làm đúng việc ghi đè. Thêm `PlanStore.append` sẽ lặp luật “đứng cuối” trong mỗi store, lệch D-011, và trái ràng buộc không thêm phương thức.

**Alternatives considered**: `PlanStore.add_subtask(...)` — thêm phương thức, người dùng cấm, và nhét luật miền vào cổng lưu. Xóa kế hoạch rồi `add` lại — `id` kế hoạch và `created_order` đổi. Dựng `Plan` trong tool — lệch lớp mỏng của `update_subtask`, nơi việc tạo `Plan` mới nằm ở core.

## 3. Thứ tự từ chối

**Decision**: `add_subtask` gọi `normalize_plan_id(plan_id)` rồi `new_subtask(title)` trước `store.get`. Cả hai ném `PlanDomainError` thì lớp tool đổi thành `ToolError` và dừng ở câu đầu tiên. `new_subtask` có thể đã cấp `id` cho một `Subtask` chưa được `replace`. Object đó bị bỏ khi kế hoạch không tồn tại. Không ghi store. Câu danh tính kế hoạch là hai câu đã có của `normalize_plan_id` và của nhánh `get` trả `None` trong `update_subtask`. Không viết hàm chuẩn hóa danh tính mới.

**Rationale**: Spec FR-010: danh tính kế hoạch, rồi tiêu đề, rồi kế hoạch có thật. Tiêu đề `None` hoặc trống cộng với danh tính không tồn tại phải ra câu tiêu đề, không ra câu không có kế hoạch. Gọi `new_subtask` trước `get` là cách giữ đúng thứ tự khi bốn việc dựng việc con nằm trong một hàm, gồm cả cấp `id`. `id` bị bỏ không vào store.

**Alternatives considered**: `get` trước rồi mới kiểm tiêu đề — tiêu đề trống trên danh tính không tồn tại sẽ thành câu không có kế hoạch, trái spec. Kiểm tiêu đề rỗng trong tool, rồi gọi hàm core chỉ để cấp `id` — chép điều kiện rỗng ra khỏi `new_subtask`.

## 4. Hình kết quả và test tạo kế hoạch

**Decision**: Thành công thì `ToolResult` từ `_plan_json`, cùng hàm `get_plan_detail` đang dùng, rồi `PlanJson.model_dump_json(ensure_ascii=False)`. Không thêm model Pydantic. `SubtaskJson` và `PlanJson` không đổi. `tests/test_create_plan.py` không sửa assertion. Test mới nằm ở `tests/test_add_subtask.py`. Một test trong file mới gọi `create_plan` với một phần tử tiêu đề `None`: `ToolError` đúng câu `Việc con không được để trống.`, store không thêm kế hoạch. Các test cũ không truyền `None`, và assertion của chúng chỉ khóa kiểu `ToolError`, số kế hoạch, mục tiêu, thứ tự, NFC, và hình việc con đã có.

**Rationale**: Spec yêu cầu kết quả thêm cùng các phần với kết quả mở. Một hàm `_plan_json` giữ một cách đọc. Người dùng cấm sửa assertion của test `create_plan`. Hành vi với chuỗi tiêu đề không đổi vì `normalize_new_plan` gọi `new_subtask` chứ không viết luật khác. `None` là đường mới. Test đường đó nằm ở file mới, để chứng minh `create_plan` đi qua cùng hàm, mà không đụng assertion cũ.

**Alternatives considered**: Sửa test cũ để khóa câu chữ tiêu đề trống — người dùng cấm sửa assertion đó. JSON thêm bọc một khóa mới — lệch `get_plan_detail`. Viết `_plan_json` thứ hai trong `add_subtask` — người dùng bắt dùng đúng hàm đang dùng.

## 5. Không đổi model

**Decision**: Không thêm, không xóa, không đổi tên, không đổi kiểu trường của `Plan`, `Subtask`, hay `SubtaskStatus`. `SubtaskStatus` vẫn chỉ `PENDING` và `DONE`. `add_subtask` không nhận trạng thái.

**Rationale**: Người dùng khóa model. Spec cũng không thêm thuộc tính cho kế hoạch. Việc con mới dùng đúng ba trường đã có.

**Alternatives considered**: Thêm `position` vào `Subtask` — đổi model, và spec nói vị trí cuối không phải danh tính. Thêm thành viên enum cho trạng thái lúc thêm — spec cấm chọn trạng thái.

## 6. Chỗ đặt mã

**Decision**: Sửa `normalize_new_plan` và thêm `new_subtask` cùng `append_subtask` trong `src/core/plans.py`. Thêm `add_subtask` trong `src/tools/plan_tools.py`. Thêm `tests/test_add_subtask.py`. Không sửa `PlanStore`, `MemoryPlanStore`, `src/tools/schemas.py`, `src/tools/base.py`, `pyproject.toml`, `src/app.py`, `src/tools/tool_router.py`, hay `src/db/`. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md).

**Rationale**: D-011 đặt luật miền ở core và tool là lớp mỏng. Không có nhà cung cấp mới, không có package mới. `uuid` đã dùng trong core từ F07.

**Alternatives considered**: File core mới chỉ cho thêm việc con — tách luật tiêu đề khỏi `plans.py` trong khi `normalize_new_plan` đã ở đó. Sửa `MemoryPlanStore` để có helper riêng — người dùng cấm, và `replace` đã đủ.
