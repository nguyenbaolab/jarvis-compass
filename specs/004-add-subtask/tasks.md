---
description: "Task list for Thêm một việc con vào kế hoạch đang có"
---

# Tasks: Thêm một việc con vào kế hoạch đang có

**Input**: Design documents from `/specs/004-add-subtask/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII và [plan.md](./plan.md) bắt pytest. Test mới nằm ở `tests/test_add_subtask.py`. `tests/test_create_plan.py` không sửa assertion. Viết test trước, thấy fail, rồi mới implement phần còn thiếu của story đó.

**Organization**: Theo user story để mỗi story làm và kiểm được riêng.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Bản giả store là file `tests/fakes/memory_plan_store.py`, class `MemoryPlanStore`. Không sửa file đó. Không thêm phương thức vào `PlanStore` hay `MemoryPlanStore`
- Không sửa `pyproject.toml`. Không thêm package. Không tạo module mới. Không sửa `spec.md`. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md). Không sửa `src/app.py`, `src/db/`, `src/tools/tool_router.py`, `src/tools/base.py`, `src/tools/schemas.py`, `src/api/`, `src/clients/`, `src/scheduler/`, hay `src/core/llm.py`, `src/core/planning.py`, `src/core/session.py`
- Không sửa `tests/test_health.py`, `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, hay `tests/test_update_subtask.py`
- Không đổi trường hay kiểu của `Plan`, `Subtask`, hay `SubtaskStatus`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Không thêm dependency. Repo đã có khung; research mục 6 không sửa `pyproject.toml`

- [X] T001 Giữ nguyên `pyproject.toml`. Không thêm package. Không tạo module mới. File được phép sửa ở các phase sau chỉ là `src/core/plans.py`, `src/tools/plan_tools.py`, `tests/test_add_subtask.py`, và câu trạng thái đầu `docs/ARCHITECTURE.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Một hàm dựng việc con mới dùng chung, và một hàm ghép việc đó vào cuối kế hoạch. Cả hai story đều chặn ở đây

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [X] T002 Thêm `new_subtask` và `append_subtask`, rồi đổi `normalize_new_plan` gọi `new_subtask`, trong `src/core/plans.py` (phụ thuộc T001). Không thêm trường cho `Plan`, `Subtask`, hay `SubtaskStatus`. Không thêm phương thức vào `PlanStore`. Chỉ dùng thư viện chuẩn (`dataclasses`, `enum`, `typing`, `unicodedata`, `uuid`). Không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Type hint cho hàm public. Comment tiếng Việt. Không biến store tầm module. `new_subtask(title: str | None) -> Subtask` là đúng một chỗ cho bốn việc: chuẩn hóa tiêu đề bằng `_nfc_strip` đã có (NFC rồi bỏ khoảng trắng hai đầu, chữ bên trong giữ nguyên), từ chối tiêu đề thiếu hoặc rỗng, cấp `id` bằng `str(uuid.uuid4())`, gán `SubtaskStatus.PENDING`. `title` là `None`, hoặc `_nfc_strip(title)` còn rỗng, thì `PlanDomainError` với đúng câu `Việc con không được để trống.` Kiểm `None` đứng trước `_nfc_strip`. Hàm không nhận trạng thái. `normalize_new_plan` không còn tự dựng `Subtask` trong vòng lặp. Mỗi phần tử danh sách tiêu đề đi qua `new_subtask`. Danh sách `None` hoặc rỗng vẫn trả tuple rỗng và không gọi `new_subtask`. Luật mục tiêu trống giữ nguyên trong `normalize_new_plan`, đúng câu `Mục tiêu không được để trống.` `replace_subtask_status` không gọi `new_subtask`. `append_subtask(plan: Plan, subtask: Subtask) -> Plan` không gọi store, không chuẩn hóa, không cấp lại `id`. Trả về `Plan` mới, cùng `id`, cùng `goal`, cùng `created_order`. Tuple mới là các việc cũ theo thứ tự, cùng object cũ, rồi `subtask` ở cuối. Không có `add_subtask` trong task này

- [X] T003 Chạy `uv run pytest tests/test_create_plan.py tests/test_health.py` từ gốc repo (phụ thuộc T002). Kỳ vọng pass, exit code 0, mà không sửa assertion nào trong `tests/test_create_plan.py`. Không tạo `.env`

**Checkpoint**: Tạo kế hoạch vẫn pass với assertion cũ. Chưa có `add_subtask`

---

## Phase 3: User Story 1 - Thêm một việc con vào cuối và thấy lại (Priority: P1) 🎯 MVP

**Goal**: `add_subtask` thêm đúng một việc con vào cuối và trả về kế hoạch sau khi thêm, cùng hình với `get_plan_detail`

**Independent Test**: Lưu một kế hoạch có hai việc con, một việc `pending` và một việc `done`. Thêm một tiêu đề hợp lệ. Đối chiếu kết quả trả về, lần mở kế hoạch, và lần liệt kê: ba việc con, việc mới ở cuối, hai việc cũ không đổi

### Tests for User Story 1 ⚠️

> Viết test này trước. `uv run pytest tests/test_add_subtask.py` phải fail vì `add_subtask` chưa có

- [X] T004 [US1] Viết ca thành công trong `tests/test_add_subtask.py` (phụ thuộc T003). Mỗi test tạo `MemoryPlanStore` mới và truyền `store=`. Parse `ToolResult.output` thành JSON rồi so trường, không so nguyên văn chuỗi. Phủ: tạo mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana" đang `pending`, "Luyện 10 phút mỗi ngày" đang `done`. Thêm `"Mua giáo trình"`. Kết quả thêm, lần `get_plan_detail`, và lần `get_plans` đều có ba việc. Hai việc cũ giữ `id`, `title`, và `status`. Việc mới đứng cuối, `title` là `"Mua giáo trình"`, `status` là `"pending"`, `id` khác `id` kế hoạch và khác `id` hai việc cũ. Kế hoạch chỉ có mục tiêu "Viết báo cáo" và không có việc con: thêm `"Soạn dàn ý"` cho đúng một việc `pending`. Thêm `"Mua sách"` rồi `"Đọc chương 1"`: thứ tự là việc cũ, `"Mua sách"`, `"Đọc chương 1"`. `id` của việc thêm lần đầu giữ nguyên. Tiêu đề `"  Mua giáo trình  "` được lưu thành `"Mua giáo trình"`. Tiêu đề `"Học  hiragana"` giữ khoảng trắng đôi bên trong. Tiêu đề có dấu phẩy và xuống dòng, `"Mua sách,\nđọc một chương"`, vẫn là đúng một việc con, và tiêu đề giữ nguyên các ký tự đó. Tiêu đề trùng `"Ôn bài"` vẫn thành hai việc, hai `id`, việc mới đứng sau. Ba kế hoạch tạo lần lượt A, B, C. Thêm vào B. `get_plans` không lọc vẫn xếp C, B, A. Việc cũ của B giữ `status`. Việc mới của B là `"pending"`. `plan_id` có khoảng trắng hai đầu vẫn trúng đúng kế hoạch. Từ khóa liệt kê chỉ nằm trong tiêu đề việc vừa thêm thì kế hoạch không khớp. Từ khóa nằm trong mục tiêu thì vẫn khớp. Chưa viết ca từ chối (T006)

### Implementation for User Story 1

- [X] T005 [US1] Hiện nhánh thành công của `add_subtask` trong `src/tools/plan_tools.py` (phụ thuộc T002, T004). Chữ ký: `add_subtask(plan_id: str | None, title: str | None, *, store: PlanStore) -> ToolResult`. Hai đối số đầu bắt buộc phải được truyền. Hàm không nhận trạng thái và không nhận danh sách tiêu đề. `store` keyword-only, bắt buộc, không giá trị mặc định. Trước `store.get`, gọi đúng thứ tự `normalize_plan_id` rồi `new_subtask`. Khi cả hai trả về, gọi `store.get` với danh tính kế hoạch đã `strip`. `get` trả `Plan` thì gọi `append_subtask` với `Plan` đó và `Subtask` vừa dựng, rồi `store.replace` với `Plan` mà `append_subtask` trả về. Không gọi `store.add`. Trả `ToolResult(success=True, output=...)` từ đúng `_plan_json` mà `get_plan_detail` đang dùng, rồi `model_dump_json(ensure_ascii=False)`. Không viết hàm dựng JSON thứ hai. Không bọc trong khóa `plans`. Không sửa `src/tools/schemas.py`. Import module không tạo store và không đọc hay ghi biến module. Không gọi LLM, HTTP, Telegram, hay PostgREST. `src/core/plans.py` không import file này. Chưa đổi `PlanDomainError` và `None` từ `get` thành `ToolError` (T007)

**Checkpoint**: User Story 1 chạy riêng bằng `uv run pytest tests/test_add_subtask.py`

---

## Phase 4: User Story 2 - Từ chối rõ khi không thêm được (Priority: P1)

**Goal**: Ba tình huống từ chối là `ToolError` với đúng câu của tình huống đầu tiên. Store giữ nguyên và lần thêm sau bằng dữ liệu đúng vẫn được

**Independent Test**: Lưu một kế hoạch có một việc con. Gọi thêm với danh tính kế hoạch bỏ trống, với danh tính không tồn tại nhưng tiêu đề hợp lệ, với tiêu đề chỉ gồm khoảng trắng trên kế hoạch có thật, và với tiêu đề trống kèm danh tính không tồn tại. Mỗi lần bị từ chối bằng đúng câu của tình huống đó. Sau đó thêm một tiêu đề hợp lệ và mở lại thấy đúng hai việc

### Tests for User Story 2 ⚠️

> Thêm test trước khi nối nhánh từ chối. Ca `create_plan` với tiêu đề `None` qua ngay sau T002. Chỉ các ca từ chối của `add_subtask` phải fail cho đến T007.

- [X] T006 [US2] Thêm ca từ chối vào `tests/test_add_subtask.py` (phụ thuộc T005). Cùng quy ước store mới mỗi test và parse JSON khi lần thêm thành công. So câu `ToolError` đúng từng ký tự. Phủ, theo thứ tự câu đầu tiên: `plan_id` là `None`, `""`, hoặc chỉ khoảng trắng thì đúng câu `Danh tính kế hoạch chưa được đưa.`, kể cả khi tiêu đề cũng trống. Danh tính kế hoạch còn nội dung nhưng không trùng kế hoạch nào, tiêu đề `"Mua giáo trình"`: đúng câu `Không có kế hoạch với danh tính này.` Tiêu đề là `None`, `""`, hoặc chỉ khoảng trắng, trên kế hoạch có thật: đúng câu `Việc con không được để trống.` Số việc con không tăng. Danh tính không tồn tại và tiêu đề trống: đúng câu `Việc con không được để trống.` Đưa mục tiêu của kế hoạch, hoặc cùng `id` đã lưu nhưng khác hoa thường, làm `plan_id`, cùng tiêu đề hợp lệ: đúng câu `Không có kế hoạch với danh tính này.` `create_plan` với một phần tử tiêu đề `None`: đúng câu `Việc con không được để trống.`, và store không thêm kế hoạch đó. Ca này qua ngay sau T002. Sau mỗi lần từ chối, `get_plans` không đổi. Sau một lời từ chối trên kế hoạch có thật, `get_plan_detail` trả về kế hoạch không đổi. Một lần thêm hợp lệ sau đó vẫn thành công. Không trả `ToolResult` cho ba tình huống từ chối

### Implementation for User Story 2

- [X] T007 [US2] Nối từ chối trong `add_subtask` ở `src/tools/plan_tools.py` (phụ thuộc T005, T006). `PlanDomainError` đổi thành `ToolError` và mang nguyên câu của lỗi miền. Khi `normalize_plan_id` ném lỗi, không gọi `new_subtask` và không gọi `store.get`. Khi `new_subtask` ném lỗi, không gọi `store.get`. `store.get` trả `None` thì ném `ToolError` với đúng câu `Không có kế hoạch với danh tính này.`, và không gọi `store.replace`. Không trả `ToolResult` cho ba tình huống đó. Store giữ nguyên. Không sửa thân `create_plan`, `get_plans`, `get_plan_detail`, hay `update_subtask`

**Checkpoint**: Cả hai story pass. `uv run pytest tests/test_add_subtask.py tests/test_create_plan.py`

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Sửa câu trạng thái kiến trúc, rồi chạy đúng lệnh quickstart. Không chép lại luật. Không sửa `docs/PRODUCT.md`

- [X] T008 [P] Sửa câu trạng thái đầu `docs/ARCHITECTURE.md` (phụ thuộc T007). Câu hiện tại nói logic F04, F05, F06, và F07 đã có ở `src/core/plans.py` và `src/tools/plan_tools.py`. Sửa để nói logic F04, F05, F06, F07, và F08 đã có ở hai file đó, chưa nối HTTP, LLM hay database. Giữ nguyên §2 và các mục khác. Không liệt kê phương thức của `PlanStore`. Không sửa `docs/DECISIONS.md`. Không sửa `docs/PRODUCT.md`

- [X] T009 [P] Chạy `uv run pytest` theo `specs/004-add-subtask/quickstart.md`, từ gốc repo (phụ thuộc T007). Kỳ vọng toàn bộ pass, gồm `tests/test_health.py`, `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, `tests/test_update_subtask.py`, và `tests/test_add_subtask.py`, exit code 0. Không tạo `.env`, không gọi `pywrangler`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc phase khác
- **Foundational (Phase 2)**: phụ thuộc T001. Chặn mọi user story
- **User Stories (Phase 3+)**: phụ thuộc xong Phase 2
- **Polish (Phase 5)**: phụ thuộc xong T007. `T008` và `T009` không phụ thuộc lẫn nhau

### User Story Dependencies

- **User Story 1 (P1)**: sau Phase 2. Không cần US2
- **User Story 2 (P1)**: sau T005. Từ chối là nhánh thêm của `add_subtask` và các ca thêm trong `tests/test_add_subtask.py`. Không cần route HTTP hay database

### Within Each User Story

- Test viết trước và fail trước implementation của story đó
- `new_subtask` và `append_subtask` xong trước `add_subtask`
- `tests/test_create_plan.py` pass với assertion cũ trước khi viết test F08
- Nhánh thành công xong trước ca từ chối
- Luật dựng việc con mới chỉ ở `new_subtask` trong `src/core/plans.py`. Hình JSON một kế hoạch chỉ đi qua `_plan_json`

### Parallel Opportunities

- T008 và T009 song song sau T007
- Không song song các task cùng sửa `src/core/plans.py` (chỉ T002), cùng sửa `src/tools/plan_tools.py` (T005 rồi T007), hay cùng sửa `tests/test_add_subtask.py` (T004 rồi T006)

---

## Parallel Example: User Story 1

```text
Sau Phase 2, US1 làm tuần tự một file test rồi một hàm tool:
T004: tests/test_add_subtask.py ca thành công
T005: src/tools/plan_tools.py add_subtask nhánh thành công
```

Không có hai task US1 khác file để chạy cùng lúc.

---

## Parallel Example: User Story 2

```text
US2 tuần tự vì test và hàm nằm trên file đã sửa ở US1:
T006: ca từ chối trong tests/test_add_subtask.py
T007: nhánh ToolError trong src/tools/plan_tools.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2
2. Xong Phase 3 (US1)
3. Dừng và chạy `uv run pytest tests/test_add_subtask.py`
4. US1 là lát cắt nhỏ nhất vẫn thêm được một việc con vào cuối và đọc lại thấy việc đó

### Incremental Delivery

1. Setup + Foundational: `new_subtask` dùng chung, test tạo kế hoạch cũ vẫn pass
2. US1 → test riêng → MVP
3. US2 → ba câu từ chối. FR-010 cần US2
4. Phase 5: câu trạng thái kiến trúc, rồi `uv run pytest`

### Parallel Team Strategy

1. Cùng xong Phase 1 rồi T002 rồi T003. Không có hai file nền để chia người
2. US1 rồi US2 trên `src/tools/plan_tools.py` và `tests/test_add_subtask.py`, vì mỗi story dùng lại hai file đó
3. Sau T007, một người sửa `docs/ARCHITECTURE.md`, một người chạy `uv run pytest`

---

## Notes

- [P] chỉ khi khác file và không phụ thuộc task chưa xong
- [US1] và [US2] chỉ gắn task trong phase story
- Mỗi test một `MemoryPlanStore` mới, truyền `store=`
- `tests/test_health.py` đã có và phải vẫn pass
- Phạm vi dừng ở F08. Không có task cho chèn vào vị trí bất kỳ, sửa tiêu đề, xóa việc con, thêm nhiều việc trong một lần, đổi trạng thái, route HTTP, LLM, hay kho thật
- `docs/PRODUCT.md` giữ nguyên dòng F08 gốc
