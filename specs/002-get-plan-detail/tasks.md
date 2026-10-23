---
description: "Task list for Xem chi tiết một kế hoạch"
---

# Tasks: Xem chi tiết một kế hoạch

**Input**: Design documents from `/specs/002-get-plan-detail/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII và [plan.md](./plan.md) bắt pytest. Test nằm ở `tests/test_get_plan_detail.py`, theo [quickstart.md](./quickstart.md). Viết test trước, thấy fail, rồi mới implement.

**Organization**: Theo user story để mỗi story làm và kiểm được riêng.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Bản giả store là file `tests/fakes/memory_plan_store.py`, class `MemoryPlanStore`
- Không sửa `pyproject.toml`. Không thêm package. Không sửa `spec.md`. Không sửa `src/app.py`, `src/db/`, `src/tools/tool_router.py`, `src/tools/schemas.py`, `src/tools/base.py`, `src/api/`, `src/clients/`, `src/scheduler/`, hay `src/core/llm.py`, `src/core/planning.py`, `src/core/session.py`
- Không sửa `tests/test_create_plan.py`, `tests/test_get_plans.py`, hay `tests/test_health.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Không thêm dependency. Repo đã có khung; research mục 4 không sửa `pyproject.toml`.

- [X] T001 Giữ nguyên `pyproject.toml`. Không thêm package. Không tạo module mới. File được phép sửa ở các phase sau chỉ là `src/core/plans.py`, `src/tools/plan_tools.py`, `tests/fakes/memory_plan_store.py`, `tests/test_get_plan_detail.py`, và câu trạng thái đầu `docs/ARCHITECTURE.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Kiểm danh tính ở core và `PlanStore.get` trên cổng cùng bản giả. Cả hai story đều chặn ở đây

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [X] T002 Thêm `normalize_plan_id` và `get` vào `src/core/plans.py` (phụ thuộc T001). Không thêm trường và không đổi kiểu của `Plan` hay `Subtask`. Giữ nguyên `add`, `list_newest_first`, `normalize_new_plan`, và hàm lọc từ khóa. Chỉ dùng thư viện chuẩn đã có trong file (`dataclasses`, `typing`). Không dùng `unicodedata` cho danh tính. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Type hint cho hàm public. Comment tiếng Việt. Không biến store tầm module. `normalize_plan_id(plan_id: str | None) -> str` không gọi store. `plan_id` là `None`, hoặc `plan_id.strip()` còn rỗng: lỗi miền vì danh tính chưa được đưa, bằng `PlanDomainError` với đúng câu `Danh tính kế hoạch chưa được đưa.` Ngược lại trả về `plan_id.strip()`. Khoảng trắng bên trong được giữ. Không NFC, không `casefold`. Thêm vào `Protocol PlanStore`: `get(plan_id: str) -> Plan | None`. `get` trả về kế hoạch có `Plan.id == plan_id`, hoặc `None` khi không có. So từng ký tự, có phân biệt hoa thường. Không tạo `Plan` mới và không sửa kế hoạch đã lưu. Không có bản cài đặt `get` trong `src/`

- [X] T003 Cài `get` trên `MemoryPlanStore` trong `tests/fakes/memory_plan_store.py` (phụ thuộc T002). Chữ ký `get(plan_id: str) -> Plan | None`. Trả về kế hoạch của đúng instance khi `id` bằng đúng chuỗi được truyền, và trả `None` khi không có. So từng ký tự, có phân biệt hoa thường. Không chuẩn hóa id. Không tạo `Plan` mới và không sửa kế hoạch đã lưu. Giữ nguyên `add` và `list_newest_first`. Không đưa class này vào `src/`

**Checkpoint**: Cổng có `get`, bản giả trả `Plan` hoặc `None`, core từ chối danh tính trống. Chưa có `get_plan_detail`

---

## Phase 3: User Story 1 - Mở đúng kế hoạch theo danh tính (Priority: P1) 🎯 MVP

**Goal**: `get_plan_detail` trả về đúng kế hoạch đã lưu khi nhận đúng danh tính, cùng `id`, mục tiêu, và việc con theo thứ tự đã lưu

**Independent Test**: Lưu một kế hoạch có mục tiêu và hai việc con, lấy danh tính trong kết quả lưu, rồi mở bằng danh tính đó. Đối chiếu mục tiêu, từng việc con, và thứ tự

### Tests for User Story 1 ⚠️

> Viết test này trước. `uv run pytest tests/test_get_plan_detail.py` phải fail vì `get_plan_detail` chưa có

- [X] T004 [US1] Viết ca thành công trong `tests/test_get_plan_detail.py` (phụ thuộc T003). Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse `ToolResult.output` thành JSON rồi so trường, không so nguyên văn chuỗi. `subtasks` là mảng object `{"title": ...}`. Phủ: tạo mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày", mở bằng `id` vừa trả về; JSON có đúng `id`, đúng mục tiêu, và đúng hai object theo thứ tự đã lưu. Object chỉ có `id`, `goal`, `subtasks`. Tạo mục tiêu "Viết báo cáo" không gửi việc con, mở bằng `id` của nó, thì `subtasks` là mảng rỗng. Tạo ba kế hoạch A rồi B rồi C, mở bằng `id` của B; JSON là B, không phải A hay C. Cùng một `id`, `get_plan_detail` và phần tử tương ứng trong `get_plans` có cùng `id`, cùng `goal`, cùng `subtasks`. `id` có khoảng trắng hai đầu vẫn mở đúng kế hoạch. Mở cùng một `id` hai lần ra cùng `id`, cùng mục tiêu, cùng `subtasks`. Một lần mở thành công không đổi kết quả `get_plans`. Chưa viết ca từ chối (T006)

### Implementation for User Story 1

- [X] T005 [US1] Hiện nhánh thành công của `get_plan_detail` trong `src/tools/plan_tools.py` (phụ thuộc T002, T003, T004). Chữ ký: `get_plan_detail(plan_id: str | None, *, store: PlanStore) -> ToolResult`. `plan_id` bắt buộc phải được truyền. `store` keyword-only, bắt buộc, không giá trị mặc định. Gọi `normalize_plan_id`. Khi hàm đó trả về chuỗi, gọi `store.get` với chuỗi đó. Không gọi `list_newest_first`. `get` trả `Plan` thì trả `ToolResult(success=True, output=...)` từ `PlanJson` đã có, qua `_plan_json`, `model_dump_json(ensure_ascii=False)`. Đúng ba khóa `id`, `goal`, `subtasks`. Không bọc trong khóa `plans`. `id` trong JSON bằng `Plan.id` đã lưu. `created_order` không có trong JSON. Không thêm, không sửa, không xóa kế hoạch. Không sửa thân `create_plan` hay `get_plans`. Import module không tạo store và không đọc hay ghi biến module. Không gọi LLM, HTTP, Telegram, hay PostgREST. `src/core/plans.py` không import file này. Chưa bắt `PlanDomainError` và chưa đổi `None` từ `get` thành `ToolError` (T007)

**Checkpoint**: User Story 1 chạy riêng bằng `uv run pytest tests/test_get_plan_detail.py`

---

## Phase 4: User Story 2 - Từ chối rõ khi không mở được (Priority: P1)

**Goal**: Danh tính chưa được đưa, hoặc không trùng kế hoạch nào, thì `ToolError` với đúng câu của tình huống đó. Store giữ nguyên và lần mở sau bằng id đã lưu vẫn được

**Independent Test**: Lưu hai kế hoạch. Mở một lần bằng danh tính không trùng kế hoạch nào, và một lần bằng danh tính bỏ trống. Mỗi lần đều bị từ chối với lý do tương ứng, và hai kế hoạch vẫn còn nguyên khi liệt kê lại

### Tests for User Story 2 ⚠️

> Thêm test trước khi nối nhánh từ chối. Các ca mới trong `tests/test_get_plan_detail.py` phải fail cho đến T007

- [X] T006 [US2] Thêm ca từ chối vào `tests/test_get_plan_detail.py` (phụ thuộc T004). Cùng quy ước store mới mỗi test và parse JSON khi lần mở thành công. So câu `ToolError` đúng từng ký tự. Phủ: `id` viết hoa so với id đã lưu thì `ToolError` với đúng câu `Không có kế hoạch với danh tính này.` Mở bằng mục tiêu đã lưu, khi mục tiêu đó không bằng `id`, thì cùng câu đó. `plan_id` là một đoạn của mục tiêu đã lưu, ví dụ "tiếng Nhật" khi mục tiêu là "Học tiếng Nhật", thì `ToolError` với đúng câu `Không có kế hoạch với danh tính này.` `plan_id` là vị trí trong danh sách, ví dụ "1" và "2", thì cùng câu đó. `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì `ToolError` với đúng câu `Danh tính kế hoạch chưa được đưa.` Hai câu khác nhau từng ký tự. Sau mỗi lần từ chối, số kế hoạch và nội dung `get_plans` không đổi. Một lần mở sau bằng `id` đã lưu vẫn thành công. Không trả `ToolResult` cho hai tình huống từ chối

### Implementation for User Story 2

- [X] T007 [US2] Nối từ chối trong `get_plan_detail` ở `src/tools/plan_tools.py` (phụ thuộc T005, T006). `PlanDomainError` từ `normalize_plan_id` đổi thành `ToolError` và mang nguyên câu của lỗi miền, đúng `Danh tính kế hoạch chưa được đưa.` Khi lỗi miền ném ra, không gọi `store.get`. `store.get` trả `None` thì ném `ToolError` với đúng câu `Không có kế hoạch với danh tính này.` Không trả `ToolResult` cho hai tình huống đó. Store giữ nguyên. Không sửa thân `create_plan` hay `get_plans`. `get_plans` giữ nguyên, vẫn liệt kê bằng `list_newest_first`

**Checkpoint**: Cả hai story pass. `uv run pytest tests/test_get_plan_detail.py tests/test_create_plan.py tests/test_get_plans.py`

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Sửa câu trạng thái kiến trúc cho khớp F06, rồi chạy đúng lệnh quickstart. Không liệt kê phương thức của `PlanStore` trong docs. Không thêm việc ngoài spec và plan

- [X] T008 [P] Sửa câu trạng thái đầu `docs/ARCHITECTURE.md`. Câu hiện tại nói logic F04 và F05 đã có ở `src/core/plans.py` và `src/tools/plan_tools.py`. Sửa để nói logic F04, F05, và F06 đã có ở hai file đó, chưa nối HTTP, LLM hay database. Giữ nguyên §2 và các mục khác. Không liệt kê phương thức của `PlanStore`. Không sửa `docs/DECISIONS.md`

- [X] T009 [P] Chạy `uv run pytest` theo `specs/002-get-plan-detail/quickstart.md`, từ gốc repo. Kỳ vọng toàn bộ pass, gồm `tests/test_health.py`, `tests/test_create_plan.py`, và `tests/test_get_plans.py`, exit code 0. Không tạo `.env`, không gọi `pywrangler`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc phase khác
- **Foundational (Phase 2)**: phụ thuộc T001. Chặn mọi user story
- **User Stories (Phase 3+)**: phụ thuộc xong Phase 2
- **Polish (Phase 5)**: phụ thuộc xong story muốn giao. `T009` cần code và test của các story đó. `T008` sửa docs sau khi `get_plan_detail` đã có

### User Story Dependencies

- **User Story 1 (P1)**: sau Phase 2. Không cần US2
- **User Story 2 (P1)**: sau T005. Từ chối là nhánh thêm của `get_plan_detail` và các ca thêm trong `tests/test_get_plan_detail.py`. Không cần route HTTP hay database

### Within Each User Story

- Test viết trước và fail trước implementation của story đó
- `normalize_plan_id` và `PlanStore.get` xong trước `get_plan_detail`
- `MemoryPlanStore.get` xong trước test gọi tool
- Nhánh thành công xong trước ca từ chối
- Phần kiểm `None`, rỗng, và chỉ khoảng trắng chỉ ở `src/core/plans.py`. Hình JSON dùng lại `PlanJson` trong `src/tools/schemas.py`

### Parallel Opportunities

- T008 và T009 song song sau khi story đã xong (một file docs và một lệnh test)
- Không song song T002 với T003: `MemoryPlanStore.get` theo chữ ký vừa thêm trên `PlanStore`
- Không song song các task cùng sửa `src/tools/plan_tools.py` (T005 rồi T007) hay cùng sửa `tests/test_get_plan_detail.py` (T004 rồi T006)

---

## Parallel Example: User Story 1

```text
Sau Phase 2, US1 làm tuần tự một file test rồi một hàm tool:
T004: tests/test_get_plan_detail.py ca thành công
T005: src/tools/plan_tools.py get_plan_detail nhánh thành công
```

Không có hai task US1 khác file để chạy cùng lúc.

---

## Parallel Example: User Story 2

```text
US2 tuần tự vì test và hàm nằm trên file đã sửa ở US1:
T006: ca từ chối trong tests/test_get_plan_detail.py
T007: nhánh ToolError trong src/tools/plan_tools.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2
2. Xong Phase 3 (US1)
3. Dừng và chạy `uv run pytest tests/test_get_plan_detail.py`
4. US1 là lát cắt nhỏ nhất vẫn mở được một kế hoạch vừa lưu

### Incremental Delivery

1. Setup + Foundational
2. US1 → test riêng → MVP
3. US2 → test từ chối riêng. SC-003 cần US2
4. Phase 5: câu trạng thái kiến trúc rồi `uv run pytest`

### Parallel Team Strategy

1. Cùng xong Phase 1. Phase 2 tuần tự: một người thêm `normalize_plan_id` và `PlanStore.get` trong `src/core/plans.py`, rồi cài `get` trong `tests/fakes/memory_plan_store.py`
2. Sau đó US1 rồi US2 trên `src/tools/plan_tools.py` và `tests/test_get_plan_detail.py`, vì mỗi story dùng lại hai file đó
3. Sau story, một người sửa câu trạng thái `docs/ARCHITECTURE.md`, người kia chạy `uv run pytest`

---

## Notes

- [P] chỉ khi khác file và không phụ thuộc task chưa xong
- [US1] và [US2] chỉ gắn task trong phase story
- Mỗi test một `MemoryPlanStore` mới, truyền `store=`
- `tests/test_health.py`, `tests/test_create_plan.py`, và `tests/test_get_plans.py` đã có và phải vẫn pass
- Phạm vi dừng ở F06. Không có task cho F07 đến F10, route HTTP, LLM, hay kho thật
