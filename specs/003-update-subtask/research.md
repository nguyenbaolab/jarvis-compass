# Research: Đánh dấu việc con xong hoặc chưa xong

Quyết định cho lát cắt F07 `update_subtask`. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Nơi đặt model và chiều phụ thuộc đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011 và [research của F04/F05](../001-create-list-plans/research.md). Cách kiểm danh tính kế hoạch đã chốt ở [research của F06](../002-get-plan-detail/research.md). Tài liệu này chỉ ghi cách lát cắt này tuân các nơi đó.

## 1. Trường của việc con

**Decision**: `Subtask` thêm `id: str` và `status: SubtaskStatus`, giữ `title: str`. Thứ tự trường là `id`, `title`, `status`. `Plan` không thêm trường. Trong `src/core/plans.py`, `class SubtaskStatus(StrEnum)` thuộc thư viện chuẩn `enum`, với `PENDING = "pending"` và `DONE = "done"`. `normalize_subtask_status` trả về `SubtaskStatus`. `replace_subtask_status` nhận `SubtaskStatus`. JSON việc con có đúng ba khóa `id`, `title`, `status`, theo thứ tự đó, qua `SubtaskJson`. JSON vẫn xuất chuỗi `"pending"` hoặc `"done"`. `SubtaskJson.status` trong `src/tools/schemas.py` khai báo đúng hai giá trị đó.

**Rationale**: Spec yêu cầu mỗi việc con có danh tính riêng và trạng thái, và `title` giữ tên cùng nghĩa. Thêm `skipped` sau này chỉ là thêm một thành viên enum. Kiểu chặn giá trị sai khi store dựng lại `Subtask` từ dữ liệu lưu, vì đường đó không đi qua hàm chuẩn hóa.

**Alternatives considered**: `done: bool` — không thêm được `skipped` mà không đổi kiểu. Để `status` chỉ ở `SubtaskJson` — model miền không còn là nguồn của trạng thái, lệch D-011.

## 2. Lúc cấp danh tính việc con

**Decision**: `normalize_new_plan` tạo `Subtask(id=str(uuid.uuid4()), title=..., status=SubtaskStatus.PENDING)`. `uuid` là thư viện chuẩn. `id` việc con sinh trong core, khác `id` kế hoạch do store sinh. `PlanStore.add` giữ nguyên tuple việc con được giao, không viết lại `id` hay `status`. `id` kế hoạch vẫn do `MemoryPlanStore.add` cấp, như F04. Đổi trạng thái tạo `Subtask` mới với cùng `id` và cùng `title`.

**Rationale**: Spec cấp danh tính lúc việc con được lưu cùng kế hoạch, và danh tính không đổi khi trạng thái đổi. `create_plan` chỉ gọi `add` sau khi `normalize_new_plan` thành công, nên danh tính có mặt trên việc con ngay khi lưu. Store không viết lại việc con, nên mọi bản cài đặt sau này của `PlanStore` không tự nghĩ một kiểu danh tính khác. `id` kế hoạch không chuyển vào core trong lát này vì F04 đã giao việc đó cho store. `id` việc con phải có trước khi lưu để `replace(plan)` ghi đè cả kế hoạch mà vẫn giữ nguyên `id` việc con. Kho thật nhận UUID từ ngoài.

**Alternatives considered**: Store cấp `id` việc con giống `id` kế hoạch. Muốn vậy thì `Subtask` đi vào `add` chưa có `id`, hoặc store phá tuple đã giao. Cả hai lệch luật “add giữ nguyên việc con” của F04. Người gọi tự đưa `id` — spec nói danh tính do hệ thống cấp.

## 3. Thứ tự từ chối

**Decision**: `update_subtask` gọi lần lượt `normalize_plan_id`, `normalize_subtask_id`, `normalize_subtask_status`. Cả ba trả về hoặc ném `PlanDomainError` trước `store.get`. `normalize_subtask_id` dùng cùng luật `str.strip()` và `==` với `normalize_plan_id`, câu thiếu là `Danh tính việc con chưa được đưa.` `normalize_subtask_status` dùng `str.strip()`. Hết nội dung, hoặc phần còn lại không thuộc tập `pending` và `done`, thì câu `Trạng thái việc con chỉ nhận pending hoặc done.` Không NFC, không `casefold`, cho cả danh tính việc con và trạng thái. Sau ba bước đó, `store.get` trả `None` thì lớp tool ném `Không có kế hoạch với danh tính này.` Việc con không nằm trong kế hoạch đã tìm thấy thì `replace_subtask_status` ném `Kế hoạch này không có việc con với danh tính này.`

**Rationale**: Spec FR-013: khi nhiều lỗi cùng lúc, chỉ trả câu đầu tiên, theo thứ tự danh tính kế hoạch, danh tính việc con, trạng thái, kế hoạch có thật, việc con thuộc kế hoạch. Kiểm đầu vào trước nên một danh tính việc con trống không bị báo thành “không có kế hoạch”, và một trạng thái lạ không bị báo thành “không có việc con”. Hai câu danh tính kế hoạch giữ nguyên F06. Phần kiểm nằm ở core, chỉ thư viện chuẩn, đúng D-011.

**Alternatives considered**: Tra kế hoạch trước rồi mới kiểm việc con và trạng thái — trái thứ tự spec vừa chốt. Một hàm tool tự `strip` — lệch D-011, giống phương án đã bỏ ở F06. NFC cho trạng thái — mã là ASCII, NFC không đổi chúng, nhưng thêm NFC làm luật đọc khác luật danh tính kế hoạch không cần thiết và dễ hiểu nhầm là có chuẩn hóa chữ.

## 4. Cách ghi trạng thái mới

**Decision**: `replace_subtask_status(plan: Plan, subtask_id: str, status: SubtaskStatus) -> Plan` trong `src/core/plans.py`. Hàm không gọi store. Không thấy việc con thì ném `PlanDomainError`. Thấy và `status` đã bằng trạng thái đang có thì trả về đúng object `Plan` đó. Thấy và trạng thái khác thì trả về `Plan` mới: cùng `id`, `goal`, `created_order`; tuple mới, chỉ việc được chỉ định là `Subtask` mới; các việc khác là cùng object cũ. `PlanStore.replace(plan: Plan) -> None` ghi đè kế hoạch có cùng `id`, không thêm phần tử. Tool chỉ gọi `replace` khi `replace_subtask_status` trả về object khác.

**Rationale**: `Plan` và `Subtask` đều `frozen`. Không sửa tại chỗ. Luật “chỉ một việc đổi trạng thái” ở core thì mọi store sau này không tự viết lại luật đó. Đặt lại đúng trạng thái đang có là thành công theo spec, và không ghi store. `created_order` giữ nguyên nên thứ tự liệt kê không đổi. Không có trường trạng thái trên `Plan`, nên mọi việc con `done` không đưa kế hoạch ra khỏi danh sách.

**Alternatives considered**: `PlanStore.update_subtask(...)` chứa luật đổi một việc — mỗi store phải lặp luật miền, lệch D-011. Sửa `status` tại chỗ — dataclass đang frozen, và F04 đã chọn frozen để kế hoạch đã trả về không bị đổi ngầm. Xóa rồi `add` lại — `id` kế hoạch và `created_order` đổi, trái spec.

## 5. Kênh trả kết quả và test hình cũ

**Decision**: Thành công thì `ToolResult(success=True, output=<JSON UTF-8>)` từ `PlanJson.model_dump_json(ensure_ascii=False)`, qua `_plan_json`. Cùng hàm đó cho `create_plan`, `get_plans`, `get_plan_detail`, và `update_subtask`. Không thêm model Pydantic cho cả kế hoạch. Từ chối thì `ToolError`, không trả `ToolResult`. Test F04, F05, và F06 đang khóa việc con bằng `{"title": ...}` hoặc `set(item) == {"title"}`. Các assertion đó được sửa để chờ `id`, `title`, và `status`, vì FR-003 đổi hình chung. Assertion mục tiêu, thứ tự, NFC, lọc từ khóa, và câu từ chối F06 giữ nguyên. Test mới của F07 nằm ở `tests/test_update_subtask.py`.

**Rationale**: Spec yêu cầu bốn kết quả dùng cùng các phần của việc con. Một `PlanJson` giữ một cách đọc. Sửa assertion hình cũ là đổi kỳ vọng cho đúng hợp đồng mới, không phải xóa kiểm tra. Giữ nguyên assertion `{"title": ...}` sẽ làm `uv run pytest` thất bại dù hành vi tạo và liệt kê vẫn đúng.

**Alternatives considered**: JSON cập nhật bọc `{"plan": ...}` — lệch cách đọc của `get_plan_detail`. Để test cũ nguyên và chấp nhận chúng fail — trái luật test phải pass. Nới assertion thành “có khóa title” rồi bỏ kiểm thứ tự — yếu hơn hợp đồng FR-003.

## 6. Chỗ đặt mã

**Decision**: Sửa `Subtask`, `normalize_new_plan`, `PlanStore`, và thêm hàm thuần trong `src/core/plans.py`. Sửa `SubtaskJson` và `_plan_json`. Thêm `update_subtask` trong `src/tools/plan_tools.py`. Thêm `replace` trong `MemoryPlanStore`. Không sửa `pyproject.toml`, `src/app.py`, `src/tools/tool_router.py`, hay `src/db/`. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md).

**Rationale**: D-011 đã đặt luật miền và cổng lưu ở core. F07 dùng lại `Plan` và `PlanJson` chứ không mở module mới. Không có nhà cung cấp mới. `uuid` đã được lát F04 dùng cho `id` kế hoạch, nay dùng trong core cho `id` việc con, vẫn là thư viện chuẩn.

**Alternatives considered**: File core mới chỉ cho trạng thái — tách một trường của `Subtask` khỏi `plans.py` trong khi `Subtask` đã ở đó. Thêm package enum — `StrEnum` thuộc thư viện chuẩn `enum`, không thêm package.
