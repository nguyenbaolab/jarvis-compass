# Research: Xem chi tiết một kế hoạch

Quyết định cho lát cắt F06 `get_plan_detail`. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Nơi đặt model và chiều phụ thuộc đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011 và [research của F04/F05](../001-create-list-plans/research.md). Tài liệu này chỉ ghi cách lát cắt này tuân các nơi đó.

## 1. Chỗ tra danh tính

**Decision**: Thêm `get(plan_id: str) -> Plan | None` vào `Protocol PlanStore` trong `src/core/plans.py` và vào `MemoryPlanStore` trong `tests/fakes/`. `get` trả về kế hoạch có `id` bằng đúng chuỗi được truyền, hoặc `None` khi không có. `get_plan_detail` gọi `store.get` với chuỗi đã qua phần kiểm danh tính ở `src/core/plans.py`.

**Rationale**: (1) Store thật sẽ đọc một dòng theo khóa chính. (2) Tra chi tiết không được phụ thuộc định nghĩa danh sách đang hoạt động, vì định nghĩa đó có thể đổi khi có kế hoạch hoàn thành hoặc lưu trữ.

**Alternatives considered**: Đọc cả danh sách bằng `list_newest_first` rồi lọc theo id. Bỏ phương án này vì store thật sẽ đọc một dòng theo khóa chính, và vì tra chi tiết không được phụ thuộc định nghĩa danh sách đang hoạt động — định nghĩa đó có thể đổi khi có kế hoạch hoàn thành hoặc lưu trữ. Kiểm `None`, chuỗi rỗng, và chuỗi chỉ khoảng trắng ở lớp tool — lệch D-011; phần kiểm đó nằm ở `src/core/plans.py`, chỉ thư viện chuẩn.

## 2. Kênh trả kết quả

**Decision**: Tìm thấy thì `ToolResult(success=True, output=<JSON UTF-8>)`. JSON là một object kế hoạch do `PlanJson` sinh bằng `model_dump_json(ensure_ascii=False)`, qua `_plan_json` đã có. Không có khóa bọc `plans`. Không thêm model Pydantic. Không thấy, hoặc danh tính chưa được đưa, thì lỗi miền đổi thành `ToolError`. Không trả `ToolResult` cho hai trường hợp đó.

**Rationale**: Quy ước mã nguồn bắt tool dùng `ToolResult` và `ToolError`. Spec yêu cầu kết quả mở dùng cùng các phần thông tin với một kế hoạch trong danh sách liệt kê. Phần tử đó đã là `PlanJson` (`id`, `goal`, `subtasks`). `get_plans` trả mảng rỗng khi không khớp; mở một kế hoạch không có danh sách rỗng để đứng cùng nghĩa, nên từ chối phải là `ToolError` để người gọi phân biệt được với một lần mở thành công. `ToolError` kết thúc yêu cầu mở; lần gọi sau vẫn chạy vì store không đổi.

**Alternatives considered**: Bọc `{"plan": ...}` — thêm một kiểu đọc mới, lệch giả định dùng chung cách đọc với một phần tử của `get_plans`. `ToolResult(success=False)` — thêm tín hiệu thứ ba cạnh `ToolResult` thành công và `ToolError` mà F04 đã dùng cho từ chối. Thêm model Pydantic mới — trùng `PlanJson`.

## 3. Cách so danh tính

**Decision**: `normalize_plan_id(plan_id: str | None) -> str` trong `src/core/plans.py` xử lý `None`, chuỗi rỗng, và chuỗi chỉ khoảng trắng. Hàm dùng `str.strip()`. Hết nội dung sau `strip` thì lỗi miền "danh tính chưa được đưa". Còn nội dung thì trả về chuỗi đã `strip`. `get_plan_detail` đưa chuỗi đó vào `store.get`. `get` so bằng `==` với `Plan.id`: không `unicodedata.normalize`, không `casefold`. Hoa thường khác nhau là không khớp, `get` trả `None`, lớp tool đổi thành lỗi "không có kế hoạch với danh tính này". Khoảng trắng bên trong được giữ và tham gia so. Hai câu chữ nằm ở [contracts/get-plan-detail.md](./contracts/get-plan-detail.md).

**Rationale**: Đúng FR-005, FR-006, FR-007, và giả định so khớp trong spec. Phần kiểm id nằm ở core, chỉ thư viện chuẩn. `Plan.id` do `str(uuid.uuid4())` gán lúc lưu, chữ thường, không đi qua NFC. `str.strip()` là phép bỏ hai đầu mà F04 và F05 đã dùng cho khoảng trắng. So `==` trong `get` giữ phân biệt hoa thường mà spec yêu cầu.

**Alternatives considered**: NFC rồi mới so — spec yêu cầu trùng từng ký tự, và id lưu không được chuẩn hóa NFC; với UUID phép NFC không đổi chuỗi ASCII, nhưng thêm NFC làm luật đọc khác luật đã viết. `casefold` — làm id chữ hoa khớp id chữ thường, trái FR-007. Coi mục tiêu là danh tính — spec nói mục tiêu không thay cho danh tính.

## 4. Chỗ đặt mã và dependency

**Decision**: Thêm `normalize_plan_id` và `PlanStore.get` vào `src/core/plans.py`, thêm `get` vào `MemoryPlanStore`, và thêm `get_plan_detail` vào `src/tools/plan_tools.py`. `Plan`, `Subtask`, `PlanJson`, `create_plan`, và `get_plans` giữ nguyên. `get_plans` giữ nguyên, vẫn liệt kê bằng `list_newest_first`. Không sửa `pyproject.toml`. Không sửa `src/app.py`, `src/tools/tool_router.py`, hay `src/db/`.

**Rationale**: D-011 đã đặt luật miền và cổng lưu ở core, lớp tool chỉ gọi cổng. F06 dùng lại `Plan` và `PlanJson` chứ không mở module mới. Không có nhà cung cấp hay thư viện so chuỗi mới. Import `tools.plan_tools` từ `src/app.py` không tạo store.

**Alternatives considered**: File core mới chỉ cho F06 — tách một hàm đọc khỏi `plans.py` trong khi hàm lọc đã ở đó. Thêm package tra id — thư viện chuẩn đã đủ.

## 5. Kiểm chứng không làm đổi F04 và F05

**Decision**: Test mới chỉ gọi `get_plan_detail` cộng với `create_plan` và `get_plans` như người gọi. `uv run pytest` cả bộ test hiện có. Không sửa test cũ để chúng pass.

**Rationale**: FR-009 và SC-004 yêu cầu hành vi tạo và liệt kê giữ nguyên. Nguyên tắc VIII yêu cầu logic mới có unit test. Store mỗi test là một `MemoryPlanStore` mới, cùng cách với F04 và F05.

**Alternatives considered**: Sửa test cũ cho khớp hành vi mới — trái tiêu chí spec. Chỉ chạy file test mới — không chứng minh được test hiện có vẫn pass.
