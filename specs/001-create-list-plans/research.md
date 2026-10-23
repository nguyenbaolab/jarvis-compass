# Research: Tạo và liệt kê kế hoạch

Quyết định cho lát cắt F04 `create_plan` và F05 `get_plans`. Lý do sản phẩm và luật nằm ở [docs/PRODUCT.md](../../docs/PRODUCT.md), [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), [docs/DECISIONS.md](../../docs/DECISIONS.md), và [.specify/memory/constitution.md](../../.specify/memory/constitution.md). Tài liệu này chỉ ghi cách lát cắt này tuân các nơi đó.

## 1. Nơi lưu trong lát cắt này

**Decision**: `create_plan` và `get_plans` nhận một cổng `PlanStore` do người gọi truyền vào. `Protocol` đó nằm ở `src/core/plans.py`. Bản cài đặt bộ nhớ `MemoryPlanStore` chỉ nằm ở `tests/fakes/`. Không có bản cài đặt nào trong `src/`. Không có biến store ở tầm module.

**Rationale**: Giả định trong spec yêu cầu đúng sai của tạo và liệt kê quan sát được trước khi kho thật tồn tại, và loại trừ việc dựng hoặc nối kho đó. Nguyên tắc III giới hạn truy cập database thật vào `src/db/client.py` bằng PostgREST. Nguyên tắc II cấm giữ trạng thái trong bộ nhớ Python của Worker giữa các request. Cổng được bơm từ ngoài cho phép test tạo một store mới mỗi lần, còn mã trong `src/` không tự giữ danh sách kế hoạch.

**Alternatives considered**: Gọi PostgREST ngay trong lát cắt này — spec đang loại trừ kho thật, và database chưa được tạo. Dict toàn cục trong `src/tools/` — giữ trạng thái giữa các lần gọi trên cùng process. Trả lại đúng input mà không lưu — liệt kê sau đó không thấy cùng danh tính đã trả về lúc tạo.

## 2. Kênh trả kết quả

**Decision**: Thành công trả `ToolResult(success=True, output=<JSON UTF-8>)`. JSON do model Pydantic của response, ở `src/tools/schemas.py`, sinh bằng `model_dump_json(ensure_ascii=False)`. `subtasks` trong JSON của cả hai tool là mảng object `{"title": "..."}`, giữ thứ tự. Core trả `tuple[Subtask, ...]`; lớp tool đổi sang JSON. Từ chối tạo thì lỗi miền được đổi thành `ToolError` trước khi gọi `PlanStore.add`. Liệt kê rỗng vẫn là thành công, với `plans` là mảng rỗng.

**Rationale**: Quy ước mã nguồn bắt tool dùng `ToolResult` và `ToolError` (`src/tools/base.py` đã có hai kiểu này). Kịch bản chấp nhận cần danh tính, mục tiêu, và từng việc con theo thứ tự — một câu văn xuôi không chốt được các trường đó. `success=False` không dùng cho input bị từ chối, vì danh sách rỗng cũng là kết quả hợp lệ của `get_plans`; hai tình huống phải khác nhau ở kiểu tín hiệu. Object `title` là hình đã chốt cho output; đầu vào `create_plan` vẫn là danh sách chuỗi.

**Alternatives considered**: Thêm field `data` vào `ToolResult` — đổi kiểu dùng chung trước khi có người gọi nào cần. Trả thẳng dataclass `Plan` — bỏ hình dạng `ToolResult` mà luật đã chốt. Bắt lỗi validation bằng `ToolResult(success=False)` — trùng tín hiệu với liệt kê không có kế hoạch. Giữ `subtasks` là mảng chuỗi trong JSON — lệch hình object đã chốt cho output.

## 3. Danh tính và thứ tự tạo

**Decision**: `PlanStore.add` gán `id` bằng `str(uuid.uuid4())` (chữ thường, có gạch) và `created_order` là số nguyên tăng dần trong store đó, bắt đầu từ 1. `list_newest_first` xếp `created_order` giảm dần. JSON trả về chỉ có `id`, `goal`, `subtasks`. Mỗi phần tử `subtasks` là object một khóa `title`. Model lưu `Plan.subtasks` là `tuple[Subtask, ...]`. `created_order` ở lại trong model lưu.

**Rationale**: Spec yêu cầu danh tính do hệ thống tạo khi lưu, giữ nguyên lúc liệt kê, và hai lần tạo trùng nội dung phải ra hai danh tính. Thứ tự liệt kê không lọc là kế hoạch tạo sau đứng trước; UUID ngẫu nhiên không phải khóa sắp xếp. `uuid` thuộc thư viện chuẩn. Đã chạy `uuid.uuid4()` trên CPython 3.13.5 của repo.

**Alternatives considered**: Id số nguyên — duy nhất trong một store, đổi hợp đồng khi kho thật gán id. Sắp theo chuỗi UUID — không theo thời điểm tạo. Thư viện ULID — thêm dependency cho một nhu cầu thư viện chuẩn đã đáp ứng.

## 4. Khớp từ khóa

**Decision**: `goal`, từng subtask, và từ khóa lọc đều qua `unicodedata.normalize("NFC", ...)` rồi mới `strip`. Giá trị lưu là dạng NFC. Từ khóa `None`, hoặc rỗng sau NFC rồi `strip`, nghĩa là không lọc. So khớp lọc: NFC rồi `casefold` ở cả hai phía. Kế hoạch khớp khi từ khóa đã chuẩn hóa, sau `casefold`, là một đoạn con của `goal` sau cùng phép đó. Việc con không tham gia. Khoảng trắng bên trong từ khóa và mục tiêu được giữ. `"tieng"` không khớp `"tiếng"`.

**Rationale**: Đúng FR-010, FR-011, FR-012, FR-014, và giả định mới: hai cách mã hóa của cùng một chữ có dấu được coi là như nhau khi lưu và khi lọc, trong khi dấu tiếng Việt vẫn phân biệt. NFC gộp cùng một chữ về một dạng mà không bỏ dấu. `casefold` là phép không phân biệt hoa thường của Unicode. Các quan sát `casefold` đã ghi trước đó trên CPython 3.13.5 của repo vẫn đúng với chữ trong spec: `casefold("TIẾNG") == casefold("tiếng")`; `"tieng"` không nằm trong `"tiếng"`; `"Nhật"` nằm trong `"Học tiếng Nhật"`; từ khóa có khoảng trắng hai đầu vẫn khớp sau `strip`; `"tiếng  Nhật"` (hai dấu cách) không nằm trong `"Học tiếng Nhật"`; `"giáo trình"` không nằm trong mục tiêu đó. Hai tình huống kiểm ghi ở [contracts/create-plan.md](./contracts/create-plan.md) và [contracts/get-plans.md](./contracts/get-plans.md): (a) tạo với goal dạng NFD, liệt kê ra goal dạng NFC; (b) goal lưu từ NFD, lọc bằng từ khóa NFC của cùng chữ thì khớp.

**Alternatives considered**: Chỉ `strip` rồi `casefold`, không NFC — cùng một chữ dạng NFD và NFC không khớp, và giá trị lưu phụ thuộc cách mã hóa đầu vào. `str.lower` — cùng kết quả với các chữ Việt trong spec, nhưng `casefold` là phép không phân biệt hoa thường của Unicode. Chuẩn hóa về NFD rồi bỏ dấu tổ hợp — làm `"tieng"` khớp `"tiếng"`, trái giả định phân biệt dấu.

## 5. Chỗ đặt module

**Decision**: `src/core/plans.py` chứa `Plan`, `Subtask`, `normalize_new_plan`, lỗi miền, `Protocol PlanStore`, và hàm lọc theo từ khóa trong goal. Chỉ dùng thư viện chuẩn: `dataclasses`, `typing`, `unicodedata`, `uuid`. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. `src/tools/plan_tools.py` là lớp mỏng: gọi core, đổi kết quả thành `ToolResult`, đổi lỗi miền thành `ToolError`. `src/tools/schemas.py` giữ hình dạng JSON của tool. Model plan và cổng store không đặt thành module riêng trong `src/tools/`. Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`. `src/app.py` đã import `tools.plan_tools`. Import các module này không tạo store và không gọi mạng.

**Rationale**: `Plan` sẽ được scheduler (F10) và các tool F06 đến F09 dùng lại. Đặt kiểu và luật trong `src/core/` để scheduler và các tool đó không phải import gói tool chỉ để lấy model và chuẩn hóa. Lớp tool giữ `ToolResult`, `ToolError`, và schema Pydantic, đúng quy ước tool ở constitution.

**Alternatives considered**: Giữ model và cổng trong `src/tools/` — scheduler (F10) và các tool F06 đến F09 phải phụ thuộc gói tool để dùng lại `Plan`. Thêm package domain mới ở ngoài `src/core/` — repo đã có `src/core/` cho logic lõi. Nhét chuẩn hóa vào model Pydantic — core không dùng lại luật đó nếu không kéo Pydantic, và luật dễ nằm hai nơi.

## 6. Dependency

**Decision**: Không sửa `pyproject.toml`. `src/core/plans.py` dùng `dataclasses`, `typing`, `unicodedata`, và `uuid`. Schema JSON của tool dùng Pydantic 2 đã có qua FastAPI. `pylock.toml` ghi Pydantic 2.12.5 kèm wheel Pyodide; môi trường local đang resolve 2.13.5. Chỉ dùng API có ở cả hai (`BaseModel`, `model_dump_json`).

**Rationale**: Lát cắt không thêm nhà cung cấp, driver, hay thư viện id. `unicodedata` thuộc thư viện chuẩn, đủ cho NFC. FastAPI đã kéo Pydantic, và lock đã có wheel cho runtime Worker. Pydantic chỉ ở biên JSON của tool, không ở core.

**Alternatives considered**: Khai báo `pydantic` thành dependency trực tiếp — chưa cần, vì FastAPI đã yêu cầu nó và lock đã ship wheel. Thêm package sắp xếp Unicode — `unicodedata` và `str.casefold` đủ cho spec.

## 7. Chuẩn hóa trước khi lưu

**Decision**: Một hàm `normalize_new_plan(goal, subtasks)` trong `src/core/plans.py`. `goal` và từng việc con đi qua `unicodedata.normalize("NFC", ...)` rồi `str.strip()`. Giá trị lưu là dạng NFC. `goal is None` hoặc chỉ còn rỗng sau bước đó thì ném lỗi miền, và `create_plan` chuyển lỗi đó thành `ToolError`. `subtasks is None` thành tuple rỗng. Một việc con rỗng sau NFC rồi `strip` làm hỏng cả yêu cầu; hàm trả lỗi trước `add`. Mỗi chuỗi giữ lại trở thành một `Subtask` với `title` đã chuẩn hóa. Hai việc con cùng chữ, sau chuẩn hóa, vẫn là hai phần tử đúng vị trí. Hai kế hoạch cùng mục tiêu là hai lần `add`.

**Rationale**: FR-003 đến FR-006, FR-014, và giả định Unicode trong spec. Một hàm là nơi duy nhất của luật này, nên test đi qua `create_plan` là đủ để thấy cả từ chối lẫn việc store không đổi. Store không chuẩn hóa lại.

**Alternatives considered**: Kiểm tra lại trong store — store phải biết chính sách từ chối, và test khó tách "không gọi add" khỏi "add tự bỏ qua". Validator Pydantic song song với hàm miền — hai bản luật cho cùng một quy tắc. Chỉ `strip`, không NFC — giá trị lưu đổi theo dạng mã hóa đầu vào.
