---
description: "Task list for Tạo và liệt kê kế hoạch"
---

# Tasks: Tạo và liệt kê kế hoạch

**Input**: Design documents from `/specs/001-create-list-plans/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII và [plan.md](./plan.md) bắt pytest. Test nằm ở `tests/test_create_plan.py` và `tests/test_get_plans.py`, theo [quickstart.md](./quickstart.md). Viết test trước, thấy fail, rồi mới implement.

**Organization**: Theo user story để mỗi story làm và kiểm được riêng.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2, US3)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Bản giả store là file `tests/fakes/memory_plan_store.py`, class `MemoryPlanStore`
- Không sửa `pyproject.toml`. Không thêm package. Không sửa `src/app.py`, `src/db/`, `src/tools/tool_router.py`, `src/api/`, `src/clients/`, `src/scheduler/`, hay `src/core/llm.py`, `src/core/planning.py`, `src/core/session.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Gói import cho bản giả store. Repo đã có khung; research mục 6 không sửa dependency.

- [X] T001 Tạo `tests/fakes/__init__.py` để `tests.fakes` là package import được. File có thể trống

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model, chuẩn hóa lúc tạo, cổng store, bản giả bộ nhớ, và hình JSON. Mọi story đều chặn ở đây

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [X] T002 [P] Tạo `Plan`, `Subtask`, một exception miền, `Protocol PlanStore`, và `normalize_new_plan` trong `src/core/plans.py`. Chỉ dùng `dataclasses`, `typing`, `unicodedata`, `uuid`. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Không import `postgrest`, `anthropic`, hay client Telegram. Không biến store tầm module. Type hint cho hàm public. Comment tiếng Việt. `Plan` không có trường trạng thái, không có trường session. `id: str` do `PlanStore.add` gán, `str(uuid.uuid4())`, giữ nguyên sau khi trả về. Hai lần thêm là hai `id`. So khớp thực thể theo `id`. `goal: str` bắt buộc. Giá trị lưu là dạng NFC, còn nội dung sau NFC rồi `strip`. Khoảng trắng bên trong giữ nguyên. `subtasks: tuple[Subtask, ...]` có thứ tự. Mỗi phần tử là một `Subtask`. Tuple rỗng là hợp lệ. `created_order: int` số nguyên ≥ 1, tăng một đơn vị mỗi lần thêm thành công trong cùng một store. Không xuất hiện trong JSON của tool. `Subtask` một trường `title: str`, không id, không hạn chót, không mức ưu tiên, không trạng thái hoàn thành. Bắt buộc khi việc con được gửi. Giá trị lưu là dạng NFC, còn nội dung sau NFC rồi `strip`. `PlanStore.add(goal, subtasks) -> Plan`: `goal` là `str` đã chuẩn hóa, `subtasks` là `tuple[Subtask, ...]`. Gán `id` và `created_order`, giữ nguyên `goal` và thứ tự `subtasks`, trả về `Plan` vừa lưu. `list_newest_first() -> tuple[Plan, ...]`: mọi kế hoạch trong store, `created_order` lớn hơn đứng trước. Store rỗng trả về tuple rỗng. Không có bản cài đặt `PlanStore` trong `src/`. `normalize_new_plan(goal: str | None, subtasks: list[str] | None)` áp `unicodedata.normalize("NFC", ...)` rồi `str.strip()` cho `goal` và từng phần tử, trả về `(goal, tuple[Subtask, ...])` hoặc exception miền. `goal` là `None`, hoặc chỉ còn rỗng sau NFC rồi `strip`: lỗi miền, không có `Plan`. `subtasks` là `None`: tuple rỗng. Bất kỳ phần tử nào chỉ còn rỗng sau NFC rồi `strip`: lỗi cả yêu cầu. Không có `Plan` mới, kế hoạch đã có không đổi. `str.strip()` chỉ bỏ hai đầu. Khoảng trắng đôi ở giữa được giữ. Hai cách mã hóa của cùng một chữ có dấu ra cùng giá trị NFC. Dấu vẫn được giữ: `"tieng"` không thành `"tiếng"`. Hai chuỗi cùng chữ sau chuẩn hóa vẫn là hai `Subtask`, đúng vị trí. Chưa thêm hàm lọc từ khóa (T009)

- [X] T003 Cài `MemoryPlanStore` trong `tests/fakes/memory_plan_store.py` (phụ thuộc T001, T002). Class tên `MemoryPlanStore`. Danh sách trong bộ nhớ của đúng instance đó. `created_order` bắt đầu ở 1, tăng một đơn vị mỗi `add` thành công. `add` gán `id` bằng `str(uuid.uuid4())` (chữ thường, có gạch) và không chuẩn hóa lại `goal` hay `subtasks`. `list_newest_first` để `created_order` lớn hơn đứng trước; store rỗng trả tuple rỗng. Không đưa class này vào `src/`

- [X] T004 [P] Tạo hình JSON ở `src/tools/schemas.py` bằng Pydantic 2 `BaseModel` và `model_dump_json(ensure_ascii=False)`. Chỉ hai API đó (Pydantic 2.12.5 trên Worker và 2.13.5 local). Object kế hoạch đúng ba khóa `id`, `goal`, `subtasks`. `subtasks` là mảng object, mỗi phần tử đúng một khóa `title`. Object liệt kê đúng một khóa `plans`, luôn có mặt. Không đặt `Plan` hay `PlanStore` trong file này

**Checkpoint**: Model, cổng, bản giả, và schema sẵn. Chưa có `create_plan` hay `get_plans`

---

## Phase 3: User Story 1 - Lưu một kế hoạch vừa chốt (Priority: P1) 🎯 MVP

**Goal**: `create_plan` lưu một mục tiêu và các việc con, trả về đúng kế hoạch vừa lưu, hoặc từ chối cả yêu cầu mà không ghi store

**Independent Test**: Gửi một mục tiêu cùng hai việc con, rồi kiểm tra kết quả trả về. Không cần bước liệt kê

### Tests for User Story 1 ⚠️

> Viết test này trước. `uv run pytest tests/test_create_plan.py` phải fail vì `create_plan` chưa có

- [X] T005 [US1] Viết `tests/test_create_plan.py`. Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse `ToolResult.output` thành JSON rồi so trường, không so nguyên văn chuỗi. `subtasks` là mảng object `{"title": ...}`, không phải chuỗi. Không assert câu chữ của `ToolError`. Phủ: mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày" trả đúng mục tiêu, đúng thứ tự, và `id` khớp `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`; object kế hoạch chỉ có `id`, `goal`, `subtasks`, mỗi việc con chỉ có `title`. Không gửi việc con, mục tiêu "Viết báo cáo", thì `subtasks` là mảng rỗng. Gửi `subtasks=[]` với mục tiêu hợp lệ cũng trả `subtasks` là mảng rỗng. Hai lần tạo cùng nội dung ra hai `id` khác nhau và cả hai còn trong store. `"  Học tiếng Nhật  "` và `"  Học hiragana  "` lưu thành `"Học tiếng Nhật"` và `"Học hiragana"`; khoảng trắng đôi ở giữa giữ nguyên. Hai việc con trùng chữ vẫn là hai phần tử đúng vị trí. `goal` và từng `title` lưu dạng NFC: tạo với `unicodedata.normalize("NFD", "Học tiếng Nhật")` thì `goal` trả về là `unicodedata.normalize("NFC", "Học tiếng Nhật")` (chữ "ế" NFC là U+1EBF, NFD là U+0065 U+0302 U+0301). `goal` là `None`, `""`, hoặc chỉ khoảng trắng thì ném `ToolError` và store không đổi, kể cả khi đã có hai kế hoạch. Một việc con `""` hoặc chỉ khoảng trắng, kể cả khi đứng giữa việc con hợp lệ, ném `ToolError` và không lưu phần nào

### Implementation for User Story 1

- [X] T006 [US1] Hiện `create_plan` trong `src/tools/plan_tools.py` (phụ thuộc T002, T003, T004, T005). Chữ ký: `create_plan(goal: str | None, subtasks: list[str] | None = None, *, store: PlanStore) -> ToolResult`. `store` keyword-only, bắt buộc, không giá trị mặc định. Gọi `normalize_new_plan`; exception miền đổi thành `ToolError` và không gọi `store.add`. `ToolError` tiếng Việt, không nêu tên nhân vật AI khác. Thành công: `store.add` đúng một lần, trả `ToolResult(success=True, output=...)` với JSON từ model ở `src/tools/schemas.py`, `model_dump_json(ensure_ascii=False)`. Đầu vào việc con là `list[str]`; JSON là mảng object `title`. Import module không tạo store và không đọc hay ghi biến module. Không gọi LLM, HTTP, Telegram, hay PostgREST. `src/core/plans.py` không import file này. Không sửa `src/app.py`

**Checkpoint**: User Story 1 chạy riêng bằng `uv run pytest tests/test_create_plan.py`

---

## Phase 4: User Story 2 - Xem lại các kế hoạch đang hoạt động (Priority: P1)

**Goal**: `get_plans` không từ khóa trả mọi kế hoạch đang lưu, mới hơn đứng trước, kèm đủ việc con. Danh sách rỗng là thành công

**Independent Test**: Chuẩn bị sẵn vài kế hoạch đã lưu, rồi liệt kê không kèm từ khóa. Có thể kiểm riêng, không cần vừa tạo trong cùng một bước

### Tests for User Story 2 ⚠️

> Viết test này trước. `uv run pytest tests/test_get_plans.py` phải fail vì `get_plans` chưa có

- [X] T007 [US2] Viết phần không lọc trong `tests/test_get_plans.py` (phụ thuộc T006). Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse JSON rồi so trường. Phủ: sau một lần `create_plan` thành công, `get_plans` không từ khóa trả đúng `id`, mục tiêu, và `subtasks` là mảng object `{"title": ...}` đúng thứ tự đã lưu. Ba lần tạo A rồi B rồi C liệt kê thành C, B, A, mỗi kế hoạch kèm đủ việc con. Hai kế hoạch trùng mục tiêu đều có mặt, phân biệt bằng `id`. Store rỗng trả `{"plans": []}` và `success is True`. Một lần `create_plan` bị từ chối không làm số kế hoạch tăng. (a) Tạo với `goal` là `unicodedata.normalize("NFD", "Học tiếng Nhật")`; `get_plans` không lọc trả `goal` là `unicodedata.normalize("NFC", "Học tiếng Nhật")`. Chưa viết các ca lọc từ khóa (T010)

### Implementation for User Story 2

- [X] T008 [US2] Hiện `get_plans` trong `src/tools/plan_tools.py` (phụ thuộc T004, T007). Chữ ký: `get_plans(keyword: str | None = None, *, store: PlanStore) -> ToolResult`. `store` keyword-only, bắt buộc, không giá trị mặc định. Gọi `store.list_newest_first()` và trả mọi kế hoạch, `created_order` không có trong JSON. `output` do model `plans` ở `src/tools/schemas.py` sinh bằng `model_dump_json(ensure_ascii=False)`. Store rỗng vẫn là `ToolResult(success=True)`. Không thêm, sửa, hay xóa kế hoạch. Không gọi LLM, HTTP, Telegram, hay PostgREST. Không đọc hay ghi biến module. Chưa so khớp từ khóa; nhánh lọc thuộc T011

**Checkpoint**: User Story 1 và 2 cùng pass. `uv run pytest tests/test_create_plan.py tests/test_get_plans.py`

---

## Phase 5: User Story 3 - Tìm kế hoạch theo một từ trong mục tiêu (Priority: P2)

**Goal**: `get_plans` có từ khóa chỉ giữ kế hoạch mà từ khóa là đoạn liên tục trong mục tiêu, không phân biệt hoa thường, có phân biệt dấu

**Independent Test**: Lưu vài kế hoạch có mục tiêu khác nhau, rồi liệt kê kèm một từ khóa và đối chiếu đúng tập được trả về

### Tests for User Story 3 ⚠️

> Thêm test trước khi nối nhánh lọc. Các ca mới trong `tests/test_get_plans.py` phải fail cho đến T011

- [X] T009 [P] [US3] Thêm hàm lọc theo từ khóa trong goal vào `src/core/plans.py` (phụ thuộc T002). Hàm nhận danh sách mới-nhất-trước và từ khóa, giữ kế hoạch khớp, đúng thứ tự tương đối. `keyword` là `None`: không lọc. Ngược lại, từ khóa đi qua `unicodedata.normalize("NFC", ...)` rồi `strip`. Chuỗi rỗng sau bước đó: không lọc. So khớp: NFC rồi `casefold` ở cả hai phía. Một kế hoạch khớp khi từ khóa đã chuẩn hóa, sau `casefold`, là đoạn con của `goal` sau NFC rồi `casefold`. Việc con không tham gia. `"tieng"` không khớp `"tiếng"`. Khoảng trắng bên trong từ khóa được giữ. Không đặt luật này trong `src/tools/`

- [X] T010 [P] [US3] Thêm ca lọc vào `tests/test_get_plans.py` (phụ thuộc T007). Cùng quy ước store mới mỗi test và parse JSON. Phủ: từ khóa "Nhật" chỉ trả kế hoạch "Học tiếng Nhật", không trả "Học guitar", kèm đủ việc con. "tiếng" khớp "Học tiếng Nhật". "TIẾNG" vẫn khớp. `"  Nhật  "` khớp. "tieng" không khớp "tiếng". Việc con "Mua giáo trình Nhật" với từ khóa "giáo trình" không trả kế hoạch đó. Từ khóa không nằm trong mục tiêu nào trả `{"plans": []}`, `success is True`, không ném lỗi. Từ khóa `None`, `""`, hoặc chỉ khoảng trắng cho cùng kết quả với liệt kê không lọc. (b) Goal đã lưu từ dạng NFD ở ca (a); `keyword` là `unicodedata.normalize("NFC", "tiếng")` trả về kế hoạch đó. `"tiếng  Nhật"` (hai dấu cách) không khớp "Học tiếng Nhật". Hai kế hoạch trùng mục tiêu "Học tiếng Nhật", từ khóa "Nhật", thì cả hai đều được trả về, phân biệt bằng `id`

### Implementation for User Story 3

- [X] T011 [US3] Nối từ khóa trong `get_plans` ở `src/tools/plan_tools.py` (phụ thuộc T008, T009, T010). Sau `list_newest_first`, gọi hàm lọc của T009. Tool không tự NFC, `strip`, hay `casefold` lại. Thứ tự tương đối của danh sách không lọc được giữ. Không khớp vẫn là `ToolResult` thành công với `plans` rỗng

**Checkpoint**: Cả ba story pass. `uv run pytest tests/test_create_plan.py tests/test_get_plans.py`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Sửa docs cho khớp chỗ đặt model, rồi chạy đúng lệnh quickstart. Không thêm việc ngoài spec và plan

- [X] T012 [P] Sửa `docs/ARCHITECTURE.md` §2, giữ nguyên các dòng module khác. Dòng `src/core/`: thêm model miền dùng chung (`Plan`, `Subtask`, `PlanStore`, chuẩn hóa NFC) ở `src/core/plans.py`. Dòng `src/tools/`: ghi `plan_tools` là lớp mỏng gọi core

- [X] T013 [P] Thêm một quyết định vào `docs/DECISIONS.md`, số tiếp theo `D-011`, ngày 2026-10-23, status Accepted, cùng kiểu mục với `D-010` (`Date`, `Status`, `Quyết định`, `Lý do`). Quyết định: model miền và cổng lưu trữ đặt ở `src/core`, tool chỉ là lớp mỏng. Lý do: Plan được F06 đến F10 dùng lại. Không ghi đè `D-001` đến `D-010`

- [X] T014 [P] Chạy `uv run pytest` theo `specs/001-create-list-plans/quickstart.md`, từ gốc repo. Kỳ vọng toàn bộ pass, gồm `tests/test_health.py`, exit code 0. Không tạo `.env`, không gọi `pywrangler`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc phase khác
- **Foundational (Phase 2)**: phụ thuộc T001. Chặn mọi user story
- **User Stories (Phase 3+)**: phụ thuộc xong Phase 2
- **Polish (Phase 6)**: phụ thuộc xong story muốn giao. `T014` cần code và test của các story đó. `T012` và `T013` sửa docs sau khi chỗ đặt module đã đúng như các task trên

### User Story Dependencies

- **User Story 1 (P1)**: sau Phase 2. Không cần US2 hay US3
- **User Story 2 (P1)**: sau Phase 2. Ca liệt kê thuần có thể nhồi sẵn `MemoryPlanStore`. Ca tạo-rồi-liệt-kê và ca tạo bị từ chối cần `create_plan` (T006). `get_plans` nằm cùng `src/tools/plan_tools.py` với `create_plan`, làm sau T006
- **User Story 3 (P2)**: sau T008. Lọc là nhánh thêm của `get_plans` và các ca thêm trong `tests/test_get_plans.py`. Không cần route HTTP hay database

### Within Each User Story

- Test viết trước và fail trước implementation của story đó
- `normalize_new_plan` và cổng store xong trước `create_plan`
- `create_plan` xong trước ca tạo-rồi-liệt-kê của US2
- Hàm lọc và test lọc xong trước khi nối vào `get_plans`
- Luật chuẩn hóa và lọc chỉ ở `src/core/plans.py`. Hình JSON chỉ ở `src/tools/schemas.py`

### Parallel Opportunities

- T002 và T004 song song (hai file, T004 không cần model miền)
- T009 và T010 song song (hàm lọc và file test)
- T012, T013, và T014 song song sau khi story đã xong (ba file hoặc một lệnh test; T014 không sửa docs)
- Không song song các task cùng sửa `src/tools/plan_tools.py` (T006, T008, T011) hay cùng sửa `tests/test_get_plans.py` (T007 rồi T010)

---

## Parallel Example: User Story 1

```text
Sau Phase 2, US1 làm tuần tự một file test rồi một hàm tool:
T005: tests/test_create_plan.py
T006: src/tools/plan_tools.py create_plan
```

Không có hai task US1 khác file để chạy cùng lúc. T002 và T004 ở Phase 2 mới là cặp song song trước US1.

---

## Parallel Example: User Story 2

```text
US2 tuần tự vì test gọi create_plan và get_plans sửa cùng file với T006:
T007: tests/test_get_plans.py (không lọc)
T008: src/tools/plan_tools.py get_plans
```

---

## Parallel Example: User Story 3

```text
T009: hàm lọc theo từ khóa trong goal, src/core/plans.py
T010: ca lọc trong tests/test_get_plans.py
```

Rồi T011 nối hàm lọc vào `get_plans` trong `src/tools/plan_tools.py`.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2
2. Xong Phase 3 (US1)
3. Dừng và chạy `uv run pytest tests/test_create_plan.py`
4. US1 là lát cắt nhỏ nhất vẫn lưu được một kế hoạch

### Incremental Delivery

1. Setup + Foundational
2. US1 → test riêng → MVP
3. US2 → test riêng. SC-002 (tạo xong liệt kê thấy đúng kế hoạch) cần US1 và US2
4. US3 → test lọc riêng
5. Phase 6: docs rồi `uv run pytest`

### Parallel Team Strategy

1. Cùng xong Phase 1 và Phase 2. Trong Phase 2, một người làm `src/core/plans.py` và `MemoryPlanStore`, người kia làm `src/tools/schemas.py`
2. Sau đó US1 rồi US2 rồi US3 trên `src/tools/plan_tools.py`, vì cùng một file
3. Ở US3, một người thêm hàm lọc trong `src/core/plans.py`, người kia thêm ca test trong `tests/test_get_plans.py`, rồi một người nối vào `get_plans`

---

## Notes

- [P] chỉ khi khác file và không phụ thuộc task chưa xong
- [US1], [US2], [US3] chỉ gắn task trong phase story
- Mỗi test một `MemoryPlanStore` mới, truyền `store=`
- `tests/test_health.py` đã có và phải vẫn pass; không sửa file đó trong các task trên
- Phạm vi dừng ở F04 và F05. F06 đến F10 chỉ xuất hiện trong lý do của D-011, không có task làm các tool hay scheduler đó
