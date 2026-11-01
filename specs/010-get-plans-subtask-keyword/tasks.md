---
description: "Task list for Từ khóa liệt kê khớp tiêu đề việc con"
---

# Tasks: Từ khóa liệt kê khớp tiêu đề việc con

**Input**: Design documents from `/specs/010-get-plans-subtask-keyword/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII và [spec.md](./spec.md) bắt một kiểm tra cho từng ý. Test mới chỉ thêm trong `tests/test_get_plans.py`, mỗi test một `MemoryPlanStore`. Năm assertion cũ được sửa, đúng danh sách [research.md](./research.md) mục 5. Mọi assertion cũ khác giữ nguyên. Viết test của story trước, thấy fail, rồi mới sửa luật lọc hoặc catalog cho story đó.

**Organization**: Theo user story. US1 làm hàm lọc xét tiêu đề. US2 và US3 thêm ca trên cùng hàm đó. US4 đổi câu mô tả và số phiên bản.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2, US3, US4)
- Phase setup và phase nền không gắn story
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Mỗi task chỉ sửa file có trong `specs/010-get-plans-subtask-keyword/allowed-files.txt`
- Không thêm package. Không tạo module mới. Không sửa `Plan`, `Subtask`, `PlanStore`, `MemoryPlanStore`, `SupabasePlanStore`, `src/db/`, `src/tools/schemas.py`, `src/core/system_prompt.py`, `evals/`, `docs/`, `AGENTS.md`
- Không đọc, không ghi `.env` thật và `.dev.vars`

## Phase 1: Setup

**Purpose**: Khóa danh sách file trước khi sửa code

- [x] T001 Phạm vi file của lát này là đúng sáu đường dẫn sau, đã ghi vào `specs/010-get-plans-subtask-keyword/allowed-files.txt`, cộng dòng `specs/010-get-plans-subtask-keyword/**`. Không dùng `*` ở chỗ khác. File được sửa hoặc tạo khi làm các task sau chỉ là: `src/core/plans.py`, `src/tools/plan_tools.py`, `src/tools/tool_definitions.py`, `tests/test_get_plans.py`, `tests/test_add_subtask.py`, `tests/test_tool_router.py`

---

## Phase 2: Foundational

**Purpose**: Đổi tên hàm lọc và một chỗ NFC rồi `casefold`, chưa xét tiêu đề. Mọi story chặn ở đây

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [x] T002 Đổi tên `filter_by_goal_keyword` thành `filter_by_keyword` trong `src/core/plans.py` và sửa import cùng lời gọi trong `src/tools/plan_tools.py` (phụ thuộc T001). `git grep -n filter_by_goal_keyword -- src tests` sau task này không còn dòng nào. Các file trong `specs/010-get-plans-subtask-keyword` còn nhắc tên cũ là đúng, không sửa. Chưa xét `title`. Docstring của `get_plans` vẫn nói lọc trong goal, vì hành vi chưa đổi. Trong `filter_by_keyword`, một hàm lồng làm đúng `unicodedata.normalize("NFC", value)` rồi `casefold`, và không `strip`. Từ khóa đã chuẩn hóa sau NFC rồi `strip`, và `plan.goal`, đều đi qua hàm lồng đó. `keyword` là `None`, hoặc NFC rồi `strip` còn `""`, thì trả đúng tuple đầu vào. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Không thêm thư viện. Không đổi trường hay kiểu của `Plan` và `Subtask`. Không thêm phương thức store

**Checkpoint**: Test cũ của `get_plans` vẫn pass. Tiêu đề việc con chưa làm kế hoạch khớp

---

## Phase 3: User Story 1 - Tìm được kế hoạch khi từ khóa nằm ở tên việc con (Priority: P1) MVP

**Goal**: Từ khóa còn nội dung thì kế hoạch được giữ nếu mục tiêu hoặc ít nhất một tiêu đề chứa từ khóa. Mỗi kế hoạch một lần. Thứ tự mới hơn đứng trước

**Independent Test**: `uv run pytest tests/test_get_plans.py tests/test_add_subtask.py`. Ca chỉ tiêu đề `"giáo trình"` trả về kế hoạch. Ca khớp cả mục tiêu và nhiều tiêu đề trả một lần

### Tests for User Story 1

- [x] T003 [P] [US1] Sửa và thêm ca trong `tests/test_get_plans.py` (phụ thuộc T002). Đổi tên `test_keyword_in_subtask_only_does_not_match` thành `test_keyword_in_subtask_only_matches` (chỉ đổi tên) và đổi assertion: từ khóa `"giáo trình"` trên tiêu đề `"Mua giáo trình Nhật"` trả về đúng một kế hoạch đó, không còn `[]`. Ca từ khóa chỉ nằm trong một tiêu đề đặt từ khóa ở việc con cuối. Thêm ca: từ khóa nằm ở mục tiêu và ở nhiều tiêu đề thì kế hoạch xuất hiện một lần; hai kế hoạch chỉ khớp qua tiêu đề giữ thứ tự mới hơn đứng trước. Mỗi ca dương thêm một kế hoạch không khớp trong cùng `MemoryPlanStore` và assert kế hoạch đó vắng mặt. Mỗi test một `MemoryPlanStore`. Không sửa assertion của các test cũ khác trong file này

- [x] T004 [P] [US1] Sửa assertion trong `tests/test_add_subtask.py` (phụ thuộc T002). Đổi tên `test_keyword_matches_goal_not_new_title` thành `test_keyword_matches_goal_and_new_title` (chỉ đổi tên). Từ khóa `"giáo trình"` phải trả về kế hoạch vừa thêm việc `"Mua giáo trình"`. Assertion từ khóa `"Nhật"` giữ nguyên. Không sửa assertion nào khác trong file này

### Implementation for User Story 1

- [x] T005 [US1] Xét tiêu đề trong `filter_by_keyword` ở `src/core/plans.py`, và đổi docstring của `get_plans` trong `src/tools/plan_tools.py` (phụ thuộc T003, T004). `title` đi qua đúng hàm lồng của T002. Không viết lại NFC rồi `casefold`. Không `strip` tiêu đề. Không đọc `note`. Một `Plan` được append tối đa một lần khi từ khóa đã chuẩn hóa nằm trong `goal` hoặc trong ít nhất một `title`. Thứ tự tuple đầu vào giữ nguyên. `get_plans` không thêm bước chuẩn hóa riêng. Không đổi `PlanStore`

- [x] T006 [US1] Chạy `uv run pytest tests/test_get_plans.py tests/test_add_subtask.py` từ gốc repo (phụ thuộc T005). Kỳ vọng pass, exit code 0. Không sửa thêm assertion

**Checkpoint**: Tìm theo tên việc con trả về kế hoạch, một lần, mới hơn đứng trước

---

## Phase 4: User Story 2 - Kế hoạch khớp được trả nguyên (Priority: P1)

**Goal**: Kế hoạch khớp mang đủ việc con, kể cả việc không chứa từ khóa, đúng trạng thái và ghi chú. `pending`, `done`, và `skipped` đều được xét

**Independent Test**: `uv run pytest tests/test_get_plans.py`. Ca `done` và ca `skipped` trả về kế hoạch với đúng trạng thái. Ca ba việc con trả đủ cả việc không chứa từ khóa

### Tests for User Story 2

- [x] T007 [US2] Thêm ca vào `tests/test_get_plans.py` (phụ thuộc T006). Kế hoạch có ba việc, việc chứa từ khóa là việc con ở giữa: kết quả có đủ ba việc, đúng thứ tự. Việc giữa đang `done` thì trạng thái trả về vẫn `done` và ghi chú của việc đó giữ nguyên. Việc đang `skipped` có tiêu đề chứa từ khóa thì kế hoạch được trả về và việc đó vẫn `skipped`. Dựng `Subtask` với `SubtaskStatus.DONE` hoặc `SubtaskStatus.SKIPPED` rồi `MemoryPlanStore.add`. Không đi qua tool cập nhật. Không dùng helper `_plans` vì helper đó khẳng định mọi `status` là `pending`. Tự `json.loads(result.output)["plans"]` rồi kiểm `status` và `note` từng việc con. Không sửa `_plans`. Không sửa assertion cũ

### Implementation for User Story 2

- [x] T008 [US2] Chạy `uv run pytest tests/test_get_plans.py` (phụ thuộc T007). Kỳ vọng pass, exit code 0. Hàm lọc không được bỏ việc con và không được bỏ qua trạng thái. Nếu fail, chỉ sửa `filter_by_keyword` trong `src/core/plans.py`. Không viết hàm lọc thứ hai

**Checkpoint**: Kế hoạch khớp trả nguyên, mọi trạng thái đều được xét

---

## Phase 5: User Story 3 - Luật so khớp của tiêu đề giống luật của mục tiêu (Priority: P1)

**Goal**: Hoa thường, NFC, không bỏ dấu, khoảng trắng bên trong, và từ khóa trống áp cho tiêu đề đúng như mục tiêu. Ghi chú không được xét

**Independent Test**: `uv run pytest tests/test_get_plans.py`. `"tieng"` không khớp tiêu đề `"tiếng"`. Tiêu đề lưu dạng NFD khớp từ khóa NFC. Từ khóa không gửi, rỗng, hoặc chỉ khoảng trắng vẫn giống liệt kê không lọc

### Tests for User Story 3

- [x] T009 [US3] Thêm ca vào `tests/test_get_plans.py` (phụ thuộc T008). `"TIẾNG"` và `"  Nhật  "` khớp tiêu đề `"Học tiếng Nhật"` khi mục tiêu không chứa các từ đó. `"tieng"` không khớp tiêu đề đó. `"tiếng  Nhật"` không khớp tiêu đề `"tiếng Nhật"`. Tiêu đề đã lưu dạng NFD của `"Học tiếng Nhật"` khớp từ khóa NFC của `"tiếng"`: dựng `Subtask` rồi `store.add`, không đi qua `create_plan`. Ghi chú là chỗ duy nhất chứa từ khóa thì `plans` rỗng và `success` đúng. Không sửa `test_blank_keyword_matches_unfiltered_list`, `test_tieng_without_diacritic_does_not_match`, hay `test_keyword_inner_double_space_does_not_match`

### Implementation for User Story 3

- [x] T010 [US3] Chạy `uv run pytest tests/test_get_plans.py` (phụ thuộc T009). Kỳ vọng pass, exit code 0. Nếu fail, chỉ sửa hàm lồng và nhánh giữ kế hoạch trong `filter_by_keyword` ở `src/core/plans.py`. Không `strip` trong hàm lồng. Không xét `note`

**Checkpoint**: Luật chữ của tiêu đề trùng luật của mục tiêu. Test cũ về mục tiêu vẫn pass

---

## Phase 6: User Story 4 - Mô tả gửi cho mô hình và số phiên bản (Priority: P2)

**Goal**: Mô tả `get_plans` là đúng câu FR-009. `DEFINITIONS_VERSION` là số nguyên `2`. Schema đầu vào không đổi

**Independent Test**: `uv run pytest tests/test_tool_router.py tests/test_llm_turn.py`. Ba assertion router đã đổi thấy số `2` và câu mới. `tests/test_llm_turn.py` không bị sửa

### Tests for User Story 4

- [x] T011 [P] [US4] Sửa đúng ba assertion trong `tests/test_tool_router.py` (phụ thuộc T002). `tests/test_tool_router.py:97`: `assert DEFINITIONS_VERSION == 1` thành `== 2`. `tests/test_tool_router.py:86`: `assert logged["definitions_version"] == 1` thành `== 2`, vẫn so với số cứng, không đổi sang so với hằng. `tests/test_tool_router.py:109`: câu mô tả cũ của `get_plans` thành đúng `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.` Không sửa `isinstance` ở dòng 98. Không sửa assertion nào khác trong file này. Không sửa `tests/test_llm_turn.py`

### Implementation for User Story 4

- [x] T012 [US4] Sửa `src/tools/tool_definitions.py` (phụ thuộc T011). `DEFINITIONS_VERSION` thành số nguyên `2`. `description` của `get_plans` thành đúng câu ở T011. `input_schema` của `get_plans` giữ một trường `keyword` kiểu string, `required` rỗng, `additionalProperties` false. Năm tool kia không đổi câu. Không đổi khóa log

- [x] T013 [US4] Chạy `uv run pytest tests/test_tool_router.py tests/test_llm_turn.py` từ gốc repo (phụ thuộc T012). Kỳ vọng pass, exit code 0. Không sửa `tests/test_llm_turn.py`

**Checkpoint**: Mô hình đọc câu mới. Dòng log ghi phiên bản `2`

---

## Phase 7: Polish

**Purpose**: Chạy đúng lệnh quickstart trên cả lát

- [x] T014 Chạy từ gốc repo lệnh trong [quickstart.md](./quickstart.md): `uv run pytest tests/test_get_plans.py tests/test_add_subtask.py tests/test_tool_router.py tests/test_llm_turn.py` (phụ thuộc T006, T008, T010, T013). Kỳ vọng pass, exit code 0. Không sửa `docs/`, `AGENTS.md`, `evals/`, `src/db/`, `src/tools/schemas.py`, hay `src/core/system_prompt.py`. Không sửa assertion cũ ngoài năm chỗ

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không phụ thuộc task khác
- **Foundational (Phase 2)**: Phụ thuộc T001. Chặn mọi user story
- **US1 (Phase 3)**: Phụ thuộc T002. Không phụ thuộc US2, US3, US4
- **US2 (Phase 4)**: Phụ thuộc T006. Cùng file test với US1 nên đứng sau US1
- **US3 (Phase 5)**: Phụ thuộc T008. Cùng file test nên đứng sau US2
- **US4 (Phase 6)**: Phụ thuộc T002. Khác file với US1 đến US3, làm được song song với US1 sau T002
- **Polish (Phase 7)**: Phụ thuộc T006, T008, T010, T013

### User Story Dependencies

- **US1 (P1)**: Sau nền. MVP
- **US2 (P1)**: Sau US1 vì cùng `tests/test_get_plans.py` và vì ca nguyên vẹn cần hàm đã xét tiêu đề
- **US3 (P1)**: Sau US2 vì cùng file test
- **US4 (P2)**: Sau nền. Không cần luật tiêu đề để đổi catalog

### Within Each User Story

- Test viết trước và fail trước khi sửa luật hoặc catalog của story đó
- US2 và US3 kỳ vọng pass ngay nếu `filter_by_keyword` của US1 đã trả nguyên kế hoạch và đã dùng một hàm lồng. Chỉ sửa hàm đó khi fail

### Parallel Opportunities

- T003 và T004 song song, hai file test khác nhau
- Sau T002, US4 (T011 đến T013) song song với US1 (T003 đến T006)

---

## Parallel Example: User Story 1

```text
T003: Sửa và thêm ca trong tests/test_get_plans.py
T004: Sửa một assertion trong tests/test_add_subtask.py
```

Sau T002, có thể chạy cặp đó cùng lúc với T011 trên `tests/test_tool_router.py`.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 rồi T002
2. T003 và T004, thấy fail
3. T005 rồi T006
4. Dừng và kiểm US1 trước khi làm US2

### Incremental Delivery

1. Nền: đổi tên và một chỗ gập chữ, luật mục tiêu còn nguyên
2. US1: tiêu đề làm kế hoạch khớp
3. US2: trả nguyên kế hoạch, mọi trạng thái
4. US3: luật chữ và ghi chú
5. US4: câu mô tả và phiên bản `2`
6. T014 chạy cụm pytest của quickstart

---

## Notes

- Năm assertion: `test_keyword_in_subtask_only_matches` (đổi tên từ `test_keyword_in_subtask_only_does_not_match`), `test_keyword_matches_goal_and_new_title` (đổi tên từ `test_keyword_matches_goal_not_new_title`), `tests/test_tool_router.py` dòng 97, dòng 86, dòng 109
- Dòng 86 giữ số cứng `2`. Số dòng 97, 98, 109 không đổi so với hiện tại; dòng 97 và 109 là hai assertion được sửa, dòng 98 (`isinstance`) không sửa.
- B9 phải làm mutation check cho US2 và US3: xét `note`, `strip` tiêu đề, bỏ `casefold` tiêu đề, cắt bớt việc con
- Không commit trong các task này trừ khi người dùng yêu cầu
