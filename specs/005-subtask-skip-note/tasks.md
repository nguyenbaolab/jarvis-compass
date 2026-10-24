---
description: "Task list for Bỏ qua việc con và ghi chú"
---

# Tasks: Bỏ qua việc con và ghi chú

**Input**: Design documents from `/specs/005-subtask-skip-note/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII, [spec.md](./spec.md), và [plan.md](./plan.md) bắt pytest. Test mới nằm ở `tests/test_subtask_skip_note.py`. Test cũ chỉ sửa đúng ba loại. Viết test trước, thấy fail đúng chỗ đã ghi trong task, rồi mới implement phần còn thiếu.

**Organization**: Theo user story để mỗi story làm và kiểm được riêng.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2, US3)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Bản giả store là `tests/fakes/memory_plan_store.py`, class `MemoryPlanStore`. Không sửa file đó. Không thêm phương thức vào `PlanStore` hay `MemoryPlanStore`
- Không sửa `pyproject.toml`. Không thêm package. Không tạo module mới. Không sửa `spec.md`. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md). Không sửa file nào trong `specs/003-update-subtask/`
- Không sửa `src/app.py`, `src/db/`, `src/tools/tool_router.py`, `src/tools/base.py`, `src/api/`, `src/clients/`, `src/scheduler/`, hay `src/core/llm.py`, `src/core/planning.py`, `src/core/session.py`
- Không sửa `tests/test_health.py`
- `Plan` không thêm trường và không đổi kiểu

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Không thêm dependency. Repo đã có khung

- [X] T001 Giữ nguyên `pyproject.toml`. Không thêm package. Không tạo module mới. File được phép sửa ở các phase sau chỉ là `src/core/plans.py`, `src/tools/schemas.py`, `src/tools/plan_tools.py`, `tests/test_subtask_skip_note.py`, `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, `tests/test_add_subtask.py`, `tests/test_update_subtask.py`, và câu trạng thái đầu `docs/ARCHITECTURE.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Sửa assertion cũ trước khi model đổi, để lát sau chỉ còn đúng ba loại lệch. Chưa có `skipped` và chưa có `note` trong JSON

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [X] T002 Sửa assertion cũ đúng ba loại (phụ thuộc T001). Không loại sửa nào khác. Không xóa test. Không nới assertion tiêu đề, số việc, thứ tự, câu danh tính, hay tập trạng thái mà test tạo kế hoạch đang khóa là `pending` hoặc `done`. Trong `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, `tests/test_add_subtask.py`, và `tests/test_update_subtask.py`: kỳ vọng khóa việc con từ `["id", "title", "status"]` thành `["id", "title", "status", "note"]`. Trong `tests/test_update_subtask.py`: câu `Trạng thái việc con chỉ nhận pending hoặc done.` thành `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` Trong `test_bad_status_wins_before_lookup` của file đó: bỏ `"skipped"` khỏi danh sách trạng thái sai. Các giá trị còn lại giữ nguyên: `None`, `""`, `"   "`, `"xong"`, `"chưa xong"`, `"Done"`, `"PENDING"`. Không sửa class `_ReplaceCounter` trong file đó. Chạy `uv run pytest tests/test_create_plan.py tests/test_get_plans.py tests/test_get_plan_detail.py tests/test_add_subtask.py tests/test_update_subtask.py` từ gốc repo. Kỳ vọng fail cho đến T004, vì JSON chưa có `note` và code còn câu hai mã. Không sửa thêm assertion để làm xanh

**Checkpoint**: Ba loại assertion đã đổi. Bộ test cũ còn đỏ. Chưa có mã `skipped`

---

## Phase 3: User Story 1 - Đánh dấu bỏ qua và chuyển giữa ba trạng thái (Priority: P1) 🎯 MVP

**Goal**: `update_subtask` nhận `skipped`, chuyển tự do với `pending` và `done`, và JSON việc con luôn có `note`

**Independent Test**: Lưu một kế hoạch có hai việc con. Đặt việc thứ nhất thành `skipped`, rồi `done`, rồi `pending`, rồi lại `skipped`. Mỗi lần mở và liệt kê. Việc kia giữ trạng thái. Ghi chú cả hai vẫn trống

### Tests for User Story 1 ⚠️

> Viết test này trước. `uv run pytest tests/test_subtask_skip_note.py` phải fail cho đến T004. File này chưa import `set_subtask_note`

- [X] T003 [US1] Viết ca trạng thái trong `tests/test_subtask_skip_note.py` (phụ thuộc T002). Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse `ToolResult.output` thành JSON rồi so trường, không so nguyên văn chuỗi. Không dùng phép so object. Ca không ghi dùng lớp viết trong file này, cùng khuôn `_ReplaceCounter` của `tests/test_update_subtask.py`: đếm `replace` trên đúng instance rồi gọi `replace` của lớp cha. Không thêm bộ đếm vào `tests/fakes/memory_plan_store.py`. Phủ: đặt `skipped` thì danh tính kế hoạch, danh tính việc con, tiêu đề, mục tiêu, và thứ tự không đổi. Rồi `done`, rồi `pending`, rồi lại `skipped`. Lần mở và lần liệt kê thấy đúng mã. Việc kia giữ trạng thái. `note` cả hai là `null`. Mọi việc `skipped`: liệt kê không lọc và mở đều thấy kế hoạch, cùng danh tính và cùng mục tiêu. Kế hoạch có việc `done` lẫn việc `skipped` vẫn được liệt kê khi không lọc và mở được. `" skipped "` thành `skipped`. `Skipped`, `SKIPPED`, và `bỏ qua`, kể cả khi danh tính kế hoạch không tồn tại, bị từ chối bằng đúng câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` và câu đó thắng trước khi tra kế hoạch. JSON của lần đặt `skipped` có `status` là `"skipped"`. Đặt lại đúng `skipped` đang có thì thành công và số lần `replace` không tăng so với ngay trước lời gọi đó. Chưa viết ca ghi chú (T005) và chưa viết ca từ chối của `set_subtask_note` (T007)

### Implementation for User Story 1

- [X] T004 [US1] Thêm `skipped` và `note` vào model và JSON trong `src/core/plans.py` và `src/tools/schemas.py` (phụ thuộc T002, T003). Không thêm trường cho `Plan`. Không thêm phương thức vào `PlanStore`. Chỉ dùng thư viện chuẩn. Thêm `replace` từ `dataclasses`. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Type hint cho hàm public. Comment tiếng Việt. `SubtaskStatus` thêm `SKIPPED = "skipped"`. `Subtask` thêm `note: str | None` đứng sau `status`, không có giá trị mặc định. `new_subtask` là lời gọi `Subtask(...)` duy nhất và truyền `note=None` cùng `status=SubtaskStatus.PENDING`. `normalize_subtask_status` nhận `skipped` sau `strip`. Cả nhánh `None` và nhánh `ValueError` dùng một hằng câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` Không NFC và không `casefold` cho trạng thái. Một hàm nội bộ là chỗ duy nhất tìm việc con theo `id`. Không thấy thì `PlanDomainError` với hằng duy nhất `Kế hoạch này không có việc con với danh tính này.` Hàm đổi trả cùng object việc thì hàm nội bộ trả cùng object `Plan`. `replace_subtask_status` gọi hàm đó. Trạng thái đã đúng thì không `replace`. Khác thì `dataclasses.replace(item, status=status)`. Không dựng `Subtask(...)` khi đổi trạng thái. Docstring `SubtaskStatus` bỏ chữ chỉ có `pending` hoặc `done`. Docstring `normalize_subtask_status` nói đủ ba mã. Trong `src/tools/schemas.py`, `SubtaskJson.status` là `Literal["pending", "done", "skipped"]`. Thêm `note: str | None` sau `status`. Bỏ câu docstring “Đúng ba khóa”. Không đặt `exclude_none`. `_plan_json` trong `src/tools/plan_tools.py` truyền `note=item.note`. Chưa thêm `normalize_subtask_note`, `replace_subtask_note`, hay `set_subtask_note`. Chạy `uv run pytest tests/test_subtask_skip_note.py tests/test_create_plan.py tests/test_get_plans.py tests/test_get_plan_detail.py tests/test_add_subtask.py tests/test_update_subtask.py`. Kỳ vọng pass, exit code 0

**Checkpoint**: User Story 1 chạy riêng bằng `uv run pytest tests/test_subtask_skip_note.py`. Bộ test cũ xanh

---

## Phase 4: User Story 2 - Gắn một ghi chú và xem lại (Priority: P1)

**Goal**: `set_subtask_note` đặt một ghi chú, ghi đè, hoặc xóa, và trả về kế hoạch. Đổi trạng thái không làm mất ghi chú

**Independent Test**: Lưu một kế hoạch có hai việc con. Đặt việc thứ nhất thành `skipped`. Gắn ghi chú "Đợi giáo trình", ghi đè bằng ghi chú khác, rồi xóa. Mỗi lần mở và liệt kê. Trạng thái vẫn `skipped`. Việc kia không có ghi chú

### Tests for User Story 2 ⚠️

> Thêm test trước khi có `set_subtask_note`. Ca việc con mới có `note` null khi liệt kê và khi mở ngay sau tạo thì qua ngay sau T004. Các ca gọi `set_subtask_note` phải fail cho đến T006

- [X] T005 [US2] Thêm ca ghi chú vào `tests/test_subtask_skip_note.py` (phụ thuộc T004). Cùng quy ước store mới mỗi test và parse JSON khi thành công. Không dùng phép so object. Phủ: tạo kế hoạch xong, liệt kê và mở ngay sau đó, việc con mới có `note` là `null`. Ca này qua ngay sau T004. Thêm việc con: việc mới có `note` là `null`, khóa đúng thứ tự `id`, `title`, `status`, `note`. Đặt ghi chú `"Đợi giáo trình"` rồi đổi trạng thái: ghi chú vẫn `"Đợi giáo trình"`, và đặt ghi chú không đổi trạng thái. Ghi đè bằng `"Học sau"` thì ghi chú cũ không còn. `"  Đợi giáo trình  "` lưu thành `"Đợi giáo trình"`. Ghi chú NFD lưu và trả về dạng NFC. Ghi chú có dấu phẩy, xuống dòng, và khoảng trắng đôi thì chữ bên trong giữ nguyên. `None`, `""`, hoặc chỉ khoảng trắng khi đang có ghi chú thì `note` thành `null` và trạng thái không đổi. Một ghi chú dài hơn vài trăm ký tự được lưu nguyên văn sau chuẩn hóa, không bị cắt. `add_subtask` không làm mất ghi chú của việc con đã có. Đặt lại đúng ghi chú đang có, sau chuẩn hóa, thì thành công và số lần `replace` không tăng. Xóa khi chưa có ghi chú thì thành công và số lần `replace` không tăng. Chưa viết ca từ chối danh tính của `set_subtask_note` (T007). Chạy `uv run pytest tests/test_subtask_skip_note.py`. Kỳ vọng fail vì chưa import được `set_subtask_note`, cho đến T006

### Implementation for User Story 2

- [X] T006 [US2] Hiện nhánh thành công của ghi chú trong `src/core/plans.py` và `src/tools/plan_tools.py` (phụ thuộc T004, T005). `normalize_subtask_note(note: str | None) -> str | None`: `None` trả `None` trước `_nfc_strip`. Chuỗi khác đi qua `_nfc_strip`. Kết quả rỗng trả `None`. Không cắt và không có hạn số. `replace_subtask_note` cùng khuôn `replace_subtask_status`, gọi hàm nội bộ tìm việc ở T004, không chép vòng `for`. Ghi chú đã bằng thì trả đúng object `Plan`. Khác thì `dataclasses.replace(item, note=note)`. `set_subtask_note(plan_id: str | None, subtask_id: str | None, note: str | None, *, store: PlanStore) -> ToolResult`. `store` keyword-only, bắt buộc, không giá trị mặc định. Trước `store.get`, gọi đúng thứ tự `normalize_plan_id`, `normalize_subtask_id`, `normalize_subtask_note`. `get` trả `Plan` thì gọi `replace_subtask_note`. Object trả về khác object đã đọc thì `store.replace`. Cùng object thì không gọi `replace`. Trả về `_plan_tool_result`. Dùng lại `_MISSING_PLAN_MESSAGE` chỉ ở T008. Chưa đổi `PlanDomainError` và `None` từ `get` thành `ToolError`. Không gọi `store.add`. Không gọi LLM, HTTP, Telegram, hay PostgREST. Chạy `uv run pytest tests/test_subtask_skip_note.py`. Kỳ vọng pass, exit code 0

**Checkpoint**: User Story 2 chạy riêng bằng `uv run pytest tests/test_subtask_skip_note.py`

---

## Phase 5: User Story 3 - Từ chối rõ khi không đổi được (Priority: P1)

**Goal**: `set_subtask_note` từ chối danh tính bằng đúng câu và đúng thứ tự của `update_subtask`. Không ghi store

**Independent Test**: Lưu hai kế hoạch, mỗi kế hoạch một việc con. Gọi đặt ghi chú với danh tính kế hoạch trống, danh tính việc con trống, danh tính không tồn tại, và việc con của kế hoạch kia. Mỗi lần đúng câu của tình huống đó. Sau đó đặt một ghi chú lên đúng một việc

### Tests for User Story 3 ⚠️

> Ca `Skipped`, `SKIPPED`, và `bỏ qua` đã nằm ở T003 và qua ngay sau T004. Không viết lại. Chỉ các ca từ chối của `set_subtask_note` phải fail cho đến T008

- [X] T007 [US3] Thêm ca từ chối của `set_subtask_note` vào `tests/test_subtask_skip_note.py` (phụ thuộc T006). Cùng quy ước store mới mỗi test. So câu `ToolError` đúng từng ký tự. Phủ, theo thứ tự câu đầu tiên: `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì đúng câu `Danh tính kế hoạch chưa được đưa.`, kể cả khi danh tính việc con và ghi chú cũng không dùng được. Danh tính kế hoạch còn nội dung, `subtask_id` là `None`, `""`, hoặc chỉ khoảng trắng: đúng câu `Danh tính việc con chưa được đưa.`, kể cả khi không có kế hoạch đó. Hai danh tính còn nội dung nhưng không có kế hoạch, ghi chú `"Đợi giáo trình"` hoặc chỉ khoảng trắng: đúng câu `Không có kế hoạch với danh tính này.` Kế hoạch A và kế hoạch B, đặt ghi chú cho A bằng danh tính việc con của B: đúng câu `Kế hoạch này không có việc con với danh tính này.` Cả hai kế hoạch giữ nguyên. Sau mỗi lần từ chối, `get_plans` không đổi. Một lần đặt hợp lệ sau đó vẫn thành công. Không trả `ToolResult` cho các tình huống từ chối này

### Implementation for User Story 3

- [X] T008 [US3] Nối từ chối trong `set_subtask_note` ở `src/tools/plan_tools.py` (phụ thuộc T006, T007). `PlanDomainError` từ ba hàm chuẩn hóa và từ `replace_subtask_note` đổi thành `ToolError` và mang nguyên câu. Khi `normalize_plan_id` ném lỗi, không gọi các bước sau và không gọi `store.get`. Khi `normalize_subtask_id` ném lỗi, không gọi `store.get`. `store.get` trả `None` thì ném `ToolError(_MISSING_PLAN_MESSAGE)`, không gọi `store.replace`. Không viết câu `Kế hoạch này không có việc con với danh tính này.` trong file tool. Không trả `ToolResult` cho các tình huống từ chối. Không sửa thân `create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, hay `add_subtask`, ngoài `_plan_json` đã truyền `note` ở T004. Chạy `uv run pytest tests/test_subtask_skip_note.py tests/test_update_subtask.py`. Kỳ vọng pass, exit code 0

**Checkpoint**: Cả ba story pass

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Sửa câu trạng thái kiến trúc, rồi chạy đúng lệnh quickstart. Không chép lại luật. Không sửa `docs/PRODUCT.md`. Không sửa `specs/003-update-subtask/`

- [X] T009 [P] Sửa câu trạng thái đầu `docs/ARCHITECTURE.md` (phụ thuộc T008). Câu hiện tại nói logic F04, F05, F06, F07, và F08 đã có ở `src/core/plans.py` và `src/tools/plan_tools.py`, chưa nối HTTP, LLM hay database. Sửa để nói F07 gồm cả `skipped` và ghi chú, vẫn ở hai file đó, vẫn chưa nối HTTP, LLM hay database. Giữ nguyên các mục khác. Không sửa `docs/DECISIONS.md`. Không sửa `docs/PRODUCT.md`

- [X] T010 [P] Chạy `uv run pytest` theo `specs/005-subtask-skip-note/quickstart.md`, từ gốc repo (phụ thuộc T008). Kỳ vọng toàn bộ pass, gồm `tests/test_health.py` và `tests/test_subtask_skip_note.py`, exit code 0. Không tạo `.env`, không gọi `pywrangler`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc phase khác
- **Foundational (Phase 2)**: phụ thuộc T001. Chặn mọi user story
- **User Stories (Phase 3+)**: phụ thuộc xong Phase 2
- **Polish (Phase 6)**: phụ thuộc xong T008. `T009` và `T010` không phụ thuộc lẫn nhau

### User Story Dependencies

- **User Story 1 (P1)**: sau T002. Không cần US2
- **User Story 2 (P1)**: sau T004. Ghi chú cần trường `note` và hàm tìm việc đã có ở US1. Không cần US3
- **User Story 3 (P1)**: sau T006. Từ chối là nhánh thêm của `set_subtask_note`. Ca trạng thái sai `Skipped`, `SKIPPED`, và `bỏ qua` đã xong ở T004

### Within Each User Story

- Test viết trước và fail trước implementation của story đó, trừ các ca đã ghi là qua từ task trước
- Ba loại sửa test cũ xong trước khi thêm `note` vào JSON
- Nhánh thành công của ghi chú xong trước ca từ chối của `set_subtask_note`
- Câu không có việc con và vòng tìm theo `id` chỉ ở một hàm trong `src/core/plans.py`
- Hình JSON một kế hoạch chỉ đi qua `_plan_json`

### Parallel Opportunities

- T009 và T010 song song sau T008
- Không song song các task cùng sửa `src/core/plans.py` (T004 rồi T006), cùng sửa `src/tools/plan_tools.py` (T004, T006, rồi T008), hay cùng sửa `tests/test_subtask_skip_note.py` (T003, T005, rồi T007)
- T002 sửa năm file test cũ. T003 tạo file test mới. Hai task khác file, nhưng T003 nằm sau Phase 2 nên làm sau T002

---

## Parallel Example: User Story 1

```text
Sau Phase 2, US1 làm tuần tự một file test rồi model:
T003: tests/test_subtask_skip_note.py ca trạng thái
T004: src/core/plans.py và src/tools/schemas.py
```

Không có hai task US1 khác file để chạy cùng lúc sau khi T003 bắt đầu.

---

## Parallel Example: User Story 2

```text
US2 tuần tự vì test và hàm dùng file đã sửa ở US1:
T005: ca ghi chú trong tests/test_subtask_skip_note.py
T006: normalize_subtask_note, replace_subtask_note, set_subtask_note
```

---

## Parallel Example: User Story 3

```text
US3 tuần tự trên hai file đã có:
T007: ca từ chối trong tests/test_subtask_skip_note.py
T008: ToolError trong src/tools/plan_tools.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2
2. Xong Phase 3 (US1)
3. Dừng và chạy `uv run pytest tests/test_subtask_skip_note.py tests/test_update_subtask.py`
4. US1 là lát cắt nhỏ nhất vẫn đặt được `skipped` và đọc lại thấy mã đó, với `note` là `null`

### Incremental Delivery

1. Setup + sửa ba loại assertion cũ: bộ test cũ còn đỏ
2. US1 → `skipped`, JSON `note`, bộ test cũ xanh
3. US2 → đặt, ghi đè, và xóa ghi chú
4. US3 → câu từ chối của `set_subtask_note`
5. Phase 6: câu trạng thái kiến trúc, rồi `uv run pytest`

### Parallel Team Strategy

1. Cùng xong T001 rồi T002. T002 đụng năm file test cũ
2. US1, US2, rồi US3 trên `src/core/plans.py`, `src/tools/plan_tools.py`, và `tests/test_subtask_skip_note.py`, vì mỗi story dùng lại các file đó
3. Sau T008, một người sửa `docs/ARCHITECTURE.md`, một người chạy `uv run pytest`

---

## Notes

- [P] chỉ khi khác file và không phụ thuộc task chưa xong
- [US1], [US2], và [US3] chỉ gắn task trong phase story
- Mỗi test một `MemoryPlanStore` mới, truyền `store=`
- `tests/test_health.py` đã có và phải vẫn pass
- Phạm vi dừng ở phần còn lại của F07. Không có task cho trạng thái cấp kế hoạch, lịch sử nhiều ghi chú, xóa việc con, route HTTP, LLM, hay kho thật
- Hai giới hạn đã biết trong [plan.md](./plan.md) không có task: mất một lần ghi khi hai yêu cầu đồng thời, và store thật ở F03 phải lưu ghi chú trống là NULL. Lát này không thêm khóa và không dựng store đó
- `docs/PRODUCT.md` giữ nguyên dòng F07 gốc
- `specs/003-update-subtask/` giữ làm biên bản
