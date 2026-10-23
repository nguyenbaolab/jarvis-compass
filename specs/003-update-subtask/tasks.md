---
description: "Task list for Đánh dấu việc con xong hoặc chưa xong"
---

# Tasks: Đánh dấu việc con xong hoặc chưa xong

**Input**: Design documents from `/specs/003-update-subtask/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII và [plan.md](./plan.md) bắt pytest. Test mới nằm ở `tests/test_update_subtask.py`. Assertion hình việc con trong test F04, F05, và F06 được cập nhật theo [quickstart.md](./quickstart.md). Viết test trước, thấy fail, rồi mới implement phần còn thiếu.

**Organization**: Theo user story để mỗi story làm và kiểm được riêng.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Bản giả store là file `tests/fakes/memory_plan_store.py`, class `MemoryPlanStore`
- Không sửa `pyproject.toml`. Không thêm package. Không sửa `spec.md`. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md). Không sửa `src/app.py`, `src/db/`, `src/tools/tool_router.py`, `src/tools/base.py`, `src/api/`, `src/clients/`, `src/scheduler/`, hay `src/core/llm.py`, `src/core/planning.py`, `src/core/session.py`
- Không sửa `tests/test_health.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Không thêm dependency. Repo đã có khung; research mục 6 không sửa `pyproject.toml`

- [X] T001 Giữ nguyên `pyproject.toml`. Không thêm package. Không tạo module mới. File được phép sửa ở các phase sau chỉ là `src/core/plans.py`, `src/tools/schemas.py`, `src/tools/plan_tools.py`, `tests/fakes/memory_plan_store.py`, `tests/test_update_subtask.py`, `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, câu trạng thái đầu `docs/ARCHITECTURE.md`, và một dòng trỏ ở `specs/001-create-list-plans/contracts/create-plan.md`, `specs/001-create-list-plans/contracts/get-plans.md`, `specs/001-create-list-plans/data-model.md`, `specs/002-get-plan-detail/contracts/get-plan-detail.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `Subtask` có danh tính và trạng thái, cổng `replace` ghi đè một kế hoạch, JSON việc con có đủ ba khóa. Cả hai story đều chặn ở đây

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [X] T002 Thêm `SubtaskStatus`, trường của `Subtask`, ba hàm miền, và `PlanStore.replace` vào `src/core/plans.py` (phụ thuộc T001). Không thêm trường cho `Plan`. Không đổi nghĩa “có mặt trong store là đang hoạt động”. Chỉ dùng thư viện chuẩn (`dataclasses`, `enum`, `typing`, `unicodedata`, `uuid`). Không dùng `unicodedata` cho danh tính hay trạng thái. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Type hint cho hàm public. Comment tiếng Việt. Không biến store tầm module. `class SubtaskStatus(StrEnum)` với `PENDING = "pending"` và `DONE = "done"`. `Subtask` frozen, thứ tự trường `id`, `title`, `status`. `id: str` do `normalize_new_plan` gán `str(uuid.uuid4())` lúc tạo việc con để lưu; giữ nguyên khi trạng thái đổi; khác `id` của kế hoạch và khác `id` của mọi việc con khác do cùng hàm tạo ra; không suy từ vị trí hay từ `title`. `title: str` giữ nghĩa và cách chuẩn hóa đã có: NFC rồi `strip`, còn nội dung; lát này không sửa `title`. `status: SubtaskStatus`; lúc tạo là `SubtaskStatus.PENDING`. `normalize_new_plan` vẫn nhận `goal: str | None` và `subtasks: list[str] | None`. Đầu vào tạo kế hoạch vẫn là danh sách chuỗi. Mỗi chuỗi còn nội dung thành một `Subtask` đủ ba trường. Hai chuỗi cùng `title` sau chuẩn hóa vẫn là hai `Subtask`, hai `id`. `normalize_subtask_id(subtask_id: str | None) -> str`: `None`, hoặc `strip()` còn rỗng, thì `PlanDomainError` với đúng câu `Danh tính việc con chưa được đưa.`; ngược lại trả về chuỗi đã `strip`. Không NFC, không `casefold`. `normalize_subtask_status(status: str | None) -> SubtaskStatus`: `None`, `strip()` còn rỗng, hoặc phần còn lại không phải `pending` hay `done`, thì `PlanDomainError` với đúng câu `Trạng thái việc con chỉ nhận pending hoặc done.`; ngược lại trả về `SubtaskStatus.PENDING` hoặc `SubtaskStatus.DONE`. `replace_subtask_status(plan: Plan, subtask_id: str, status: SubtaskStatus) -> Plan` không gọi store. Không có việc con với `id` đó: `PlanDomainError` với đúng câu `Kế hoạch này không có việc con với danh tính này.` Có và `status` đang bằng thành viên đó: trả về đúng object `plan`. Có và khác: trả về `Plan` mới, cùng `id`, `goal`, `created_order`, cùng thứ tự, chỉ việc đó đổi `status`. `normalize_plan_id` giữ nguyên hành vi F06, đúng câu `Danh tính kế hoạch chưa được đưa.` Thêm `replace(plan: Plan) -> None` vào `Protocol PlanStore`. `add` lưu đúng tuple `Subtask` đã có `id` và `status`, không cấp lại `id` việc con. Không có bản cài đặt `replace` trong `src/`

- [X] T003 [P] Khai báo hình JSON việc con trong `src/tools/schemas.py` (phụ thuộc T001). `SubtaskJson` có đúng ba khóa, theo thứ tự `id`, `title`, `status`. `status` khai báo đúng hai giá trị `"pending"` và `"done"`. `PlanJson` vẫn đúng ba khóa `id`, `goal`, `subtasks`. `PlansJson` giữ một khóa `plans`. Không import `src/core`. Không thêm model Pydantic cho cả kế hoạch

- [X] T004 [P] Cài `replace` trên `MemoryPlanStore` trong `tests/fakes/memory_plan_store.py` (phụ thuộc T002). Chữ ký `replace(plan: Plan) -> None`. Tìm kế hoạch có `Plan.id` bằng `plan.id`. Thay bằng `plan` được truyền. Không đổi `created_order`. Không thêm kế hoạch khi chưa có `id` đó. Không đụng kế hoạch khác. `add` giữ nguyên tuple việc con được giao, không viết lại `id` hay `status`. Giữ nguyên `list_newest_first` và `get`. Không đưa class này vào `src/`

- [X] T005 [P] Nối `id` và `status` trong `_plan_json` ở `src/tools/plan_tools.py` (phụ thuộc T002, T003). Mỗi việc con xuất `id`, `title`, và chuỗi `"pending"` hoặc `"done"`. `created_order` không có trong JSON. `create_plan`, `get_plans`, và `get_plan_detail` đi qua cùng `_plan_json`. Không thêm `update_subtask` trong task này. Không đổi luật mục tiêu, NFC, thứ tự, lọc từ khóa, hay câu từ chối F06. Import module không tạo store và không gọi mạng

- [X] T006 Cập nhật assertion hình việc con trong `tests/test_create_plan.py`, `tests/test_get_plans.py`, và `tests/test_get_plan_detail.py` (phụ thuộc T004, T005). Mỗi việc con vừa tạo có `id` và `status` là `pending`, cùng `title` đã lưu. Object việc con đủ ba khóa `id`, `title`, `status`. Giữ assertion mục tiêu, thứ tự, NFC, lọc từ khóa, kế hoạch không có việc con, và câu từ chối cũ. Không xóa các kiểm tra đó. Không so nguyên văn chuỗi JSON. `uv run pytest tests/test_create_plan.py tests/test_get_plans.py tests/test_get_plan_detail.py tests/test_health.py` pass

**Checkpoint**: Tạo, liệt kê, và mở trả việc con có `id` và `pending`. Chưa có `update_subtask`

---

## Phase 3: User Story 1 - Đánh dấu một việc con và xem lại trạng thái (Priority: P1) 🎯 MVP

**Goal**: `update_subtask` đặt một việc con thành `done` hoặc `pending` và trả về kế hoạch sau cập nhật, cùng hình với `get_plan_detail`

**Independent Test**: Lưu một kế hoạch có hai việc con. Xác nhận cả hai đang `pending` và mỗi việc có danh tính riêng. Đặt một việc thành `done`, rồi mở kế hoạch và liệt kê. Đối chiếu trạng thái, tiêu đề, thứ tự, mục tiêu, và việc còn lại vẫn `pending`

### Tests for User Story 1 ⚠️

> Viết test này trước. `uv run pytest tests/test_update_subtask.py` phải fail vì `update_subtask` chưa có

- [X] T007 [US1] Viết ca thành công trong `tests/test_update_subtask.py` (phụ thuộc T006). Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse `ToolResult.output` thành JSON rồi so trường, không so nguyên văn chuỗi. Phủ: tạo mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày"; kết quả tạo, lần mở, và lần liệt kê đều có hai `id` khác nhau, khác `id` kế hoạch, cả hai `status` là `pending`, `title` đúng nội dung đã lưu. Đặt việc "Học hiragana" thành `done` bằng `id` kế hoạch và `id` việc đó; JSON trả về cùng hình với `get_plan_detail`: việc đó `done`, việc kia `pending`, cùng `id`, cùng `title`, cùng thứ tự, cùng mục tiêu. Đặt lại việc đó thành `pending`; mở và liệt kê đều thấy `pending`. Đặt lại `done` khi việc đang `done`: thành công, vẫn `done`, cùng `id` kế hoạch. Đặt lại `pending` khi việc đang `pending`: thành công, vẫn `pending`, không gọi `replace`, cùng `id` kế hoạch. Hai việc con cùng `title` "Ôn bài": đặt `done` bằng `id` của việc đứng trước; việc kia vẫn `pending`. Mọi việc con đều `done`: kế hoạch vẫn có trong `get_plans` không lọc, cùng `id` kế hoạch. `status` là `" done "` thì thành `done`. Danh tính kế hoạch và danh tính việc con có khoảng trắng hai đầu vẫn trúng. Chưa viết ca từ chối (T009)

### Implementation for User Story 1

- [X] T008 [US1] Hiện nhánh thành công của `update_subtask` trong `src/tools/plan_tools.py` (phụ thuộc T004, T007). Chữ ký: `update_subtask(plan_id: str | None, subtask_id: str | None, status: str | None, *, store: PlanStore) -> ToolResult`. Ba đối số đầu bắt buộc phải được truyền. `store` keyword-only, bắt buộc, không giá trị mặc định. Trước `store.get`, gọi đúng thứ tự `normalize_plan_id`, `normalize_subtask_id`, `normalize_subtask_status`. Khi cả ba trả về, gọi `store.get` với danh tính kế hoạch đã `strip`. `get` trả `Plan` thì gọi `replace_subtask_status` với `SubtaskStatus` đã trả về. Nếu hàm đó trả về object `Plan` khác, gọi `store.replace` với object đó. Nếu trả về đúng object cũ, không gọi `replace`. Trả `ToolResult(success=True, output=...)` từ `PlanJson` qua `_plan_json`, `model_dump_json(ensure_ascii=False)`. Không bọc trong khóa `plans`. Không sửa `title`, không thêm, không xóa, không sắp xếp lại việc con. Không đưa kế hoạch ra khỏi store khi mọi việc con là `done`. Import module không tạo store và không đọc hay ghi biến module. Không gọi LLM, HTTP, Telegram, hay PostgREST. `src/core/plans.py` không import file này. Chưa đổi `PlanDomainError` và `None` từ `get` thành `ToolError` (T010)

**Checkpoint**: User Story 1 chạy riêng bằng `uv run pytest tests/test_update_subtask.py`

---

## Phase 4: User Story 2 - Từ chối rõ khi không cập nhật được (Priority: P1)

**Goal**: Năm tình huống từ chối là `ToolError` với đúng câu của tình huống đầu tiên. Store giữ nguyên và lần cập nhật sau bằng dữ liệu đúng vẫn được

**Independent Test**: Lưu hai kế hoạch, mỗi kế hoạch có một việc con. Gọi cập nhật với danh tính kế hoạch bỏ trống, với danh tính kế hoạch không tồn tại, với danh tính việc con bỏ trống, với danh tính việc con của kế hoạch kia, và với trạng thái không phải `pending` hay `done`. Mỗi lần bị từ chối bằng đúng câu của tình huống đó. Sau đó đặt `done` đúng một việc và mở lại thấy chỉ việc đó `done`

### Tests for User Story 2 ⚠️

> Thêm test trước khi nối nhánh từ chối. Các ca mới trong `tests/test_update_subtask.py` phải fail cho đến T010

- [X] T009 [US2] Thêm ca từ chối vào `tests/test_update_subtask.py` (phụ thuộc T008). Cùng quy ước store mới mỗi test và parse JSON khi lần cập nhật thành công. So câu `ToolError` đúng từng ký tự. Phủ, theo thứ tự câu đầu tiên: `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì đúng câu `Danh tính kế hoạch chưa được đưa.`, kể cả khi `subtask_id` và `status` cũng không dùng được. Danh tính kế hoạch còn nội dung, `subtask_id` là `None`, `""`, hoặc chỉ khoảng trắng, `status` không hợp lệ: đúng câu `Danh tính việc con chưa được đưa.`, kể cả khi không có kế hoạch với danh tính đó. Hai danh tính còn nội dung, `status` là `None`, `""`, chỉ khoảng trắng, `xong`, `chưa xong`, `Done`, hoặc `PENDING`: đúng câu `Trạng thái việc con chỉ nhận pending hoặc done.`, kể cả khi không có kế hoạch đó. Hai danh tính còn nội dung, `status` là `done`, nhưng không có kế hoạch: đúng câu `Không có kế hoạch với danh tính này.` Kế hoạch A nhận `id` việc con của kế hoạch B và `status` `done`: đúng câu `Kế hoạch này không có việc con với danh tính này.` Cả hai kế hoạch giữ trạng thái cũ. Đưa `title` hoặc vị trí `"1"` khi chuỗi đó không phải `id` việc con, cùng `status` `done`: cùng câu đó. Kế hoạch không có việc con nào, danh tính việc con còn nội dung, `status` là `done`: cùng câu đó. `subtask_id` là một đoạn của tiêu đề việc con, không phải `id` việc con, cùng `status` `done`: cùng câu đó. `plan_id` viết hoa so với `id` kế hoạch đã lưu, hai đầu vào kia hợp lệ: đúng câu `Không có kế hoạch với danh tính này.` `subtask_id` viết hoa so với `id` việc con đã lưu, `status` là `done`: đúng câu `Kế hoạch này không có việc con với danh tính này.` Sau mỗi lần từ chối, `get_plans` không đổi. Một lần đặt `done` sau đó vẫn thành công. Không trả `ToolResult` cho năm tình huống từ chối. Không nhận `skipped`

### Implementation for User Story 2

- [X] T010 [US2] Nối từ chối trong `update_subtask` ở `src/tools/plan_tools.py` (phụ thuộc T008, T009). `PlanDomainError` đổi thành `ToolError` và mang nguyên câu của lỗi miền. Khi một hàm chuẩn hóa ném lỗi, không gọi hàm chuẩn hóa sau và không gọi `store.get`. `store.get` trả `None` thì ném `ToolError` với đúng câu `Không có kế hoạch với danh tính này.`, và không gọi `replace_subtask_status`. Việc con không thuộc kế hoạch thì `ToolError` với đúng câu `Kế hoạch này không có việc con với danh tính này.`, và không gọi `store.replace`. Không trả `ToolResult` cho năm tình huống đó. Store giữ nguyên. Không sửa thân `create_plan`, `get_plans`, hay `get_plan_detail`

**Checkpoint**: Cả hai story pass. `uv run pytest tests/test_update_subtask.py tests/test_create_plan.py tests/test_get_plans.py tests/test_get_plan_detail.py`

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Sửa câu trạng thái kiến trúc và thêm dòng trỏ tới hình việc con mới, rồi chạy đúng lệnh quickstart. Không chép lại luật. Không sửa `docs/PRODUCT.md`

- [X] T011 [P] Sửa câu trạng thái đầu `docs/ARCHITECTURE.md` (phụ thuộc T010). Câu hiện tại nói logic F04, F05, và F06 đã có ở `src/core/plans.py` và `src/tools/plan_tools.py`. Sửa để nói logic F04, F05, F06, và F07 đã có ở hai file đó, chưa nối HTTP, LLM hay database. Giữ nguyên §2 và các mục khác. Không liệt kê phương thức của `PlanStore`. Không sửa `docs/DECISIONS.md`. Không sửa `docs/PRODUCT.md`

- [X] T012 [P] Thêm một dòng trỏ tới `specs/003-update-subtask/contracts/update-subtask.md` trong `specs/001-create-list-plans/contracts/create-plan.md`, `specs/001-create-list-plans/contracts/get-plans.md`, `specs/001-create-list-plans/data-model.md`, và `specs/002-get-plan-detail/contracts/get-plan-detail.md` (phụ thuộc T010). Dòng đó nói hình việc con từ F07 thêm `id` và `status`, chi tiết ở contract đó. Không chép luật trạng thái, danh tính, hay câu từ chối. Không sửa các mục khác của bốn file

- [X] T013 [P] Chạy `uv run pytest` theo `specs/003-update-subtask/quickstart.md`, từ gốc repo (phụ thuộc T010). Kỳ vọng toàn bộ pass, gồm `tests/test_health.py`, `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, và `tests/test_update_subtask.py`, exit code 0. Không tạo `.env`, không gọi `pywrangler`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc phase khác
- **Foundational (Phase 2)**: phụ thuộc T001. Chặn mọi user story
- **User Stories (Phase 3+)**: phụ thuộc xong Phase 2
- **Polish (Phase 5)**: phụ thuộc xong T010. `T011`, `T012`, và `T013` không phụ thuộc lẫn nhau

### User Story Dependencies

- **User Story 1 (P1)**: sau Phase 2. Không cần US2
- **User Story 2 (P1)**: sau T008. Từ chối là nhánh thêm của `update_subtask` và các ca thêm trong `tests/test_update_subtask.py`. Không cần route HTTP hay database

### Within Each User Story

- Test viết trước và fail trước implementation của story đó
- `SubtaskStatus`, `replace_subtask_status`, và `PlanStore.replace` xong trước `update_subtask`
- `MemoryPlanStore.replace` và `_plan_json` xong trước test gọi tool
- Nhánh thành công xong trước ca từ chối
- Ba bước kiểm đầu vào chỉ ở `src/core/plans.py`. Hình JSON một kế hoạch chỉ ở `PlanJson`

### Parallel Opportunities

- T003 song song với T002: một file schema, một file core
- T004 và T005 song song sau T002 và T003: một file store giả, một file tool
- T011, T012, và T013 song song sau T010
- Không song song các task cùng sửa `src/tools/plan_tools.py` (T005 rồi T008 rồi T010) hay cùng sửa `tests/test_update_subtask.py` (T007 rồi T009)

---

## Parallel Example: User Story 1

```text
Sau Phase 2, US1 làm tuần tự một file test rồi một hàm tool:
T007: tests/test_update_subtask.py ca thành công
T008: src/tools/plan_tools.py update_subtask nhánh thành công
```

Không có hai task US1 khác file để chạy cùng lúc.

---

## Parallel Example: User Story 2

```text
US2 tuần tự vì test và hàm nằm trên file đã sửa ở US1:
T009: ca từ chối trong tests/test_update_subtask.py
T010: nhánh ToolError trong src/tools/plan_tools.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2
2. Xong Phase 3 (US1)
3. Dừng và chạy `uv run pytest tests/test_update_subtask.py`
4. US1 là lát cắt nhỏ nhất vẫn đặt được một việc con thành `done` và đọc lại thấy trạng thái đó

### Incremental Delivery

1. Setup + Foundational: việc con mới có `id` và `pending` trên tạo, liệt kê, và mở
2. US1 → test riêng → MVP
3. US2 → năm câu từ chối. FR-013 cần US2
4. Phase 5: câu trạng thái kiến trúc, dòng trỏ, rồi `uv run pytest`

### Parallel Team Strategy

1. Cùng xong Phase 1. T002 và T003 song song. Sau đó T004 và T005 song song, rồi T006
2. US1 rồi US2 trên `src/tools/plan_tools.py` và `tests/test_update_subtask.py`, vì mỗi story dùng lại hai file đó
3. Sau T010, một người sửa `docs/ARCHITECTURE.md`, một người thêm dòng trỏ ở bốn file spec cũ, một người chạy `uv run pytest`

---

## Notes

- [P] chỉ khi khác file và không phụ thuộc task chưa xong
- [US1] và [US2] chỉ gắn task trong phase story
- Mỗi test một `MemoryPlanStore` mới, truyền `store=`
- `tests/test_health.py` đã có và phải vẫn pass
- Phạm vi dừng ở F07 lát `pending` và `done`. Không có task cho `skipped`, ghi chú, F08, route HTTP, LLM, hay kho thật
- `docs/PRODUCT.md` giữ nguyên dòng F07 gốc
