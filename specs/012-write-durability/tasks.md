---
description: "Task list for Độ bền ghi"
---

# Tasks: Độ bền ghi

**Input**: Design documents from `/specs/012-write-durability/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có, và viết trước mã tương ứng. Test cũ không đổi assertion, trừ ba hành vi ở Assumptions của spec. Thêm `version` vào chỗ dựng `Plan` thì được.

**Organization**: Ba story đều P1. Nền chặn mọi story vì `Plan.version` không có mặc định.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: File khác nhau, không phụ thuộc task chưa xong
- **[Story]**: Chỉ ở phase story
- Mỗi task một việc, có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- File được sửa hoặc tạo chỉ là các dòng trong `specs/012-write-durability/allowed-files.txt`
- Không thêm gói. Không sửa `pyproject.toml`, `uv.lock`, `pylock.toml`
- `docs/DECISIONS.md` chỉ được thêm D-021 và một dòng Cập nhật ở D-011, người dùng đã duyệt ở B10 (2026-11-04). Không sửa `.specify/memory/constitution.md`. Nếu một câu trong hai file đó thành sai, dừng, không sửa
- Không sửa lời hướng dẫn, `PROMPT_VERSION`, bộ định nghĩa tool, `DEFINITIONS_VERSION`, `evals/`, spec cũ
- Không task push, `db reset`, deploy, hay `pywrangler`. Không task nào ghi timeout trên Worker là đã kiểm chứng
- Không đọc, không ghi `.env` thật và `.dev.vars`

## Phase 1: Setup

**Purpose**: Không có task. Project, `httpx`, và `postgrest` đã có

**Checkpoint**: Không thêm gói

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `Plan.version` không mặc định, lớp xung đột, chuỗi cố định, trường trên `ToolResult`. Mọi story cần phase này

**Checkpoint**: `Plan(...)` thiếu `version` là lỗi. Khi phase này xong, T006 và T007 đã thêm `version` ở chỗ dựng trong test và kho giả, và T029 đã làm `plan_from_row` truyền `version`, nên suite cũ dựng lại được. Ca kho local vẫn chờ migration T025

### Tests

- [X] T001 Viết `test_plan_without_version_is_type_error` trong `tests/test_plan_store_contract.py`. Gọi `Plan` đủ `id`, `goal`, `subtasks`, `created_order` nhưng không có `version`, kỳ vọng `TypeError`. Không sửa hàm test cũ. Chạy hàm này trước khi sửa `src/core/plans.py`. Kỳ vọng fail, vì `Plan` hiện không có trường `version`

- [X] T002 Viết `test_plan_conflict_error_is_not_domain_error` trong `tests/test_plan_store_contract.py` (phụ thuộc T001). Import `PlanConflictError` từ `src/core/plans.py`, khẳng định nó không phải lớp con của `PlanDomainError`. Chạy trước khi thêm lớp. Kỳ vọng fail vì chưa có tên đó

- [X] T003 Viết `tests/test_saved_reply.py` (phụ thuộc không có). Khẳng định một module `src/tools/saved_reply.py` là chỗ duy nhất của ba câu và sáu mẫu. Ba câu đúng Assumptions của spec: `Chưa chắc thay đổi đã được lưu.`, `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`, `Không thực hiện được yêu cầu này.` Sáu mẫu đúng chữ trong Assumptions, gồm tạo có một việc, tạo có hai việc ngăn bằng dấu phẩy và một dấu cách, tạo không việc, thêm việc, đặt trạng thái đúng một trong `chưa làm` / `xong` / `bỏ qua`, ghi chú còn chữ, xóa ghi chú. Hàm ghép: các dòng đã lưu có số `1.` `2.` theo thứ tự, rồi câu chưa chắc nếu có lần ghi bị bỏ, rồi câu từ chối nếu có lần ghi bị từ chối, không dòng trống. Chỉ một phần thì chuỗi là đúng phần đó. Chạy trước khi tạo module. Kỳ vọng fail vì chưa có file

- [X] T004 Viết trong `tests/test_tool_router.py` một hàm: `ToolResult` có trường hiệu lực tùy chọn, mặc định trống; `ToolError` mang được cùng trường; `_failure` chép trường đó sang `ToolResult` (phụ thuộc không có). Dòng log tool vẫn đúng bảy khóa `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`. Không thêm giá trị `error_type`. `ToolError` vẫn là `domain`. `Exception` khác vẫn là `unexpected`. Chạy trước khi thêm trường. Kỳ vọng fail

### Implementation

- [X] T005 Thêm `version: int` không giá trị mặc định trên `Plan` trong `src/core/plans.py` (phụ thuộc T001). `_plan_with_subtasks` chép `version` từ plan đã đọc, không đặt `0`. Không import tools hay db

- [X] T006 [P] Thêm đối số `version` vào mọi `Plan(...)` trong `tests/test_plan_store_contract.py` và `tests/test_supabase_plan_store.py` (phụ thuộc T005). Không đổi assertion cũ

- [X] T007 [P] Trong `tests/fakes/memory_plan_store.py`, `add` dựng `Plan` với `version` bằng `0` (phụ thuộc T005). Chưa kiểm xung đột ở task này

`plan_from_row` ở `src/db/plan_store.py:72` dựng `Plan(...)` thiếu `version`. Sau T005, `tests/test_plan_row_mapping.py` đỏ cho tới khi T029 xong. Ba task sau nằm ở phase này để Checkpoint không nói suite cũ dựng lại được khi file đó còn đỏ.

- [X] T026 [P] Trong `src/db/models.py`, `PlanRow.version` là `int` bắt buộc, không mặc định (phụ thuộc T005). Không gọi `version` là mốc thời gian

- [X] T027 Viết trong `tests/test_plan_row_mapping.py` hai ca (phụ thuộc T026). Ca dòng thiếu `version` làm `plan_from_row` lỗi. Ca dòng có `version` bằng `7` thì `Plan.version` bằng `7`. Lý do: `plan_from_row` tự dựng dict bốn khóa cho `PlanRow.model_validate` (`src/db/plan_store.py` dòng 50 đến 57), nên sau T026 mọi lần gọi lỗi và ca thiếu `version` pass ngay. Ca `version` bằng `7` mới fail trước T029 và bắt lỗi truyền cứng số `0`. Kỳ vọng fail áp cho ca `version` bằng `7`. Không đổi assertion của `test_valid_row_becomes_plan` ngoài việc dữ liệu dòng có thêm `version`

- [X] T029 Trong `src/db/plan_store.py`, `plan_from_row` đọc `version` và đưa vào `Plan` (phụ thuộc T027). Trong `tests/test_plan_row_mapping.py`, `_row` có `version` để các test cũ còn chạy. Không đổi assertion cũ của các test đó

- [X] T008 Thêm `PlanConflictError` trong `src/core/plans.py` (phụ thuộc T002, T005). Không kế thừa `PlanDomainError`. Không chứa câu người dùng

- [X] T009 Tạo `src/tools/saved_reply.py` đúng các câu, sáu mẫu, và hàm ghép đã khóa ở T003 (phụ thuộc T003). Không bản sao chuỗi trong `src/core`, `src/turns`, hay `src/db`

- [X] T010 Thêm trường hiệu lực tùy chọn, mặc định trống, trên `ToolResult` trong `src/tools/base.py`, và để `ToolError` mang được trường đó (phụ thuộc T004). Trong `src/tools/tool_router.py`, `_failure` chép trường sang `ToolResult`. Không thêm khóa log. Không thêm giá trị `error_type`

---

## Phase 3: User Story 1 - Lời gọi kho quá giờ thì bỏ (Priority: P1)

**Goal**: Tool chờ từng lời gọi kho bằng `asyncio.wait_for` trên số giây còn lại. Lần ghi quá hạn trả câu chưa chắc. Lần đọc quá hạn trả câu đã có. Lượt có kho không trả lời vẫn trả trong hạn

**Independent Test**: Kho giả không mở mạng. Một ca tool bị bỏ trong hạn. Một ca `run_turn` với kho không trả lời, lượt trả trong hạn

### Tests

- [X] T011 [US1] Viết trong `tests/test_store_call_limit.py` ca kho giả không trả lời cho một lần ghi (phụ thuộc T009, T010). Hàm số giây còn lại trả một số nhỏ dương. Kỳ vọng tool bỏ lời gọi trong hạn, cờ lỗi bật, đúng `Chưa chắc thay đổi đã được lưu.`, và có cờ hiệu lực chưa chắc. Không mở mạng. Bọc lời gọi ngoài cùng bằng `asyncio.wait_for` với timeout 2 giây để ca không treo nếu mã sai. Trước khi có mã, ca fail vì `execute_tool` chưa nhận tham số hàm số giây còn lại.

- [X] T012 [US1] Viết trong `tests/test_store_call_limit.py` ca lời gọi đọc không trả lời (phụ thuộc T011). Kỳ vọng đúng `Không thực hiện được yêu cầu này.`, không phải câu chưa chắc, và không gửi lời ghi sau đó trong cùng tool. Không mở mạng. Bọc lời gọi ngoài cùng bằng `asyncio.wait_for` với timeout 2 giây để ca không treo nếu mã sai. Trước khi có mã, ca fail vì `execute_tool` chưa nhận tham số hàm số giây còn lại.

- [X] T013 [US1] Viết trong `tests/test_store_call_limit.py` ca tool đọc rồi ghi: lời gọi đọc trả về, lời gọi ghi không trả lời (phụ thuộc T012). Kỳ vọng đúng `Chưa chắc thay đổi đã được lưu.` Không mở mạng. Bọc lời gọi ngoài cùng bằng `asyncio.wait_for` với timeout 2 giây để ca không treo nếu mã sai. Trước khi có mã, ca fail vì `execute_tool` chưa nhận tham số hàm số giây còn lại.

- [X] T014 [US1] Viết trong `tests/test_store_call_limit.py` ca hàm số giây còn lại trả số nhỏ hơn hoặc bằng `0` trước khi gửi (phụ thuộc T011). Kỳ vọng không gọi kho, tool trả `Không thực hiện được yêu cầu này.`, không đặt cờ hiệu lực ghi. Chạy trước mã. Kỳ vọng fail

- [X] T015 [P] [US1] Viết trong `tests/test_llm_turn.py` ca đi qua `run_turn` với kho giả không trả lời (phụ thuộc T010). Bịt `turns.llm_turn._now` bằng các mốc sao cho lần tool hỏi số còn lại thì số đó nhỏ và dương. Kỳ vọng lượt trả mà không chờ đủ 20 giây đồng hồ thật. Không sửa `test_empty_text_is_success`, `test_budget_stops_further_calls`, `test_cancelled_error_propagates`. Không mở mạng. Bọc lời gọi ngoài cùng bằng `asyncio.wait_for` với timeout 2 giây. Trước khi có mã, ca không dùng tham số mới (T015) sẽ chờ mãi chứ không fail, nên kỳ vọng fail là `TimeoutError` sau 2 giây.

- [X] T016 [US1] Viết trong `tests/test_store_call_limit.py` ca kho ném lỗi mạng `httpx` không phải quá hạn, ví dụ kết nối bị ngắt, trong một lần ghi (phụ thuộc T010). Kỳ vọng router vẫn vào `except Exception`, `error_type` là `unexpected`, câu là `Không thực hiện được yêu cầu này.`, không đặt cờ hiệu lực chưa chắc. Đây là giới hạn đã biết. Test phải pass với router hiện tại, trước khi thêm `wait_for`. Nếu fail, dừng, không thêm nhánh

- [X] T040 [US1] Viết trong `tests/test_store_call_limit.py` ca FR-004 (phụ thuộc T010). Kho giả trả ngay, hàm số giây còn lại trả `20.0`. Một lần ghi thành công giữ đúng JSON thành công như khi không truyền hàm. Một lần ghi gặp lỗi miền hiện có (ví dụ kế hoạch không tồn tại) giữ đúng chữ và `error_type` `domain`. Một lần đọc thành công giữ đúng JSON. Không mở mạng. Chạy trước T017. Kỳ vọng fail vì `execute_tool` chưa nhận tham số

### Implementation

- [X] T017 [US1] Trong `src/tools/tool_router.py`, `execute_tool` thêm tham số mặc định `None` là hàm không đối số trả số giây còn lại (phụ thuộc T011, T016, T040). `None` nghĩa là không giới hạn, chỉ để test cũ. Khi có hàm, truyền vào tool. Không thêm giá trị `error_type`. Khóa log không đổi

- [X] T018 [US1] Trong `src/tools/plan_tools.py`, ngay trước mỗi `add`, `get`, `list_newest_first`, `replace`, gọi hàm số giây còn lại và chờ bằng `asyncio.wait_for` với số đó (phụ thuộc T017). Đây là chỗ bảo đảm FR-001. Quá hạn lúc đọc: câu `Không thực hiện được yêu cầu này.` từ `src/tools/saved_reply.py`, không gửi lời ghi sau. Quá hạn lúc ghi: câu chưa chắc và cờ hiệu lực chưa chắc. Số còn lại không dương: không gửi, câu `Không thực hiện được yêu cầu này.`, không cờ hiệu lực ghi. Không bắt lỗi mạng `httpx` không phải quá hạn. Không thử lại

- [X] T019 [US1] Trong `src/turns/llm_turn.py`, `run_turn` truyền `lambda: _remaining(started)` vào `execute_tool` (phụ thuộc T015, T017). Không truyền số tính sẵn. Không truyền mốc tuyệt đối. Chưa gọi hàm ghép ở task này

- [X] T039 [US1] Viết trong `tests/test_store_call_limit.py` ca không mở mạng (phụ thuộc không có). Gọi `postgrest_client("http://x.invalid", "key")` và khẳng định `client.session` có timeout 20 giây ở connect, read, write, pool; `follow_redirects` là `True`; `base_url` chứa `/rest/v1`; header `apikey` có; header `Authorization` chỉ có khi khóa bắt đầu bằng `eyJ`, thử hai khóa. Chữ ký `postgrest_client(url, key)` giữ nguyên vì `tests/test_supabase_plan_store_source.py` bịt hàm với chữ ký đó. Chạy trước T020. Kỳ vọng fail vì timeout hiện là `None`

- [X] T020 [US1] Trong `src/db/client.py`, `postgrest_client` tạo `httpx.AsyncClient` với mức trần cố định 20 giây, hằng riêng trong `src/db`, ghi chú là bằng ngân sách của lượt, truyền bằng `http_client` (phụ thuộc T039). `AsyncClient` tự dựng thay cho client mặc định của postgrest, nên phải truyền lại đúng các đối số postgrest dựng mặc định (đọc `.venv/Lib/site-packages/postgrest/_async/client.py` dòng 97 đến 105: `base_url`, `headers`, `follow_redirects=True`, `http2=True`), cộng timeout. `verify` và `proxy` là mặc định của httpx (bật xác minh, không proxy) nên không truyền. Không dùng đối số `timeout=` đã deprecated. Không thêm gói. Không driver TCP. Cổng `PlanStore` không nhận số còn lại. Trần này không bảo đảm FR-001. Không ghi timeout trên Worker là đã kiểm chứng

**Checkpoint**: Ca kho giả và ca `run_turn` pass. Worker vẫn chưa kiểm chứng

---

## Phase 4: User Story 2 - Hai lần ghi không xóa nhau trong im lặng (Priority: P1)

**Goal**: `replace` so `version` một cách atomic. Lệch thì `PlanConflictError`, kho không đổi. Tool đổi thành câu từ chối và không thử lại

**Independent Test**: Kho giả: version lệch thì không đổi bộ nhớ. Kho local: hai `replace` cùng lúc, đúng một lần thành công

### Tests

- [X] T021 [US2] Viết trong `tests/test_plan_store_contract.py` ca cho cả kho giả và kho local (phụ thuộc T008, T007). Đúng thứ tự đọc-đọc-ghi: lần A đọc, lần B đọc, lần A `replace` xong, lần B `replace` cùng `version` đã đọc thì lần B ném `PlanConflictError` và không đổi goal hay việc con của lần A. `replace` khớp thì lần đọc sau thấy `version` tăng `1`. Lần sau bắt đầu đọc sau khi lần trước đã trả về thì không bị từ chối, và kho có việc con của cả hai lần. Ca này khóa FR-006 khi cả hai cùng thành công. Hai kế hoạch khác nhau đều ghi được. Chạy trước `MemoryPlanStore` và trước migration. Kỳ vọng fail. Ca memory không mở mạng. Ca supabase không kèm lệnh `db reset` trong task này

- [X] T022 [P] [US2] Viết trong `tests/test_store_call_limit.py` ca tool gặp `PlanConflictError` (phụ thuộc T008, T010). Kỳ vọng đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`, không gọi `replace` lần thứ hai, `error_type` vẫn là `domain` vì đi qua `ToolError`. Không thêm giá trị `error_type`. Chạy trước `src/tools/plan_tools.py`. Kỳ vọng fail

- [X] T023 [P] [US2] Viết trong `tests/test_supabase_plan_store.py` ca `asyncio.gather` hai `replace` cùng `version` đã đọc (phụ thuộc T006). Kỳ vọng đúng một lần thành công, một lần `PlanConflictError`, lần đọc lại là bản của lần thành công. Ca tuần tự không thay ca này. Chạy trước migration. Kỳ vọng fail. Task không chạy `db reset`

### Implementation

- [X] T024 [US2] Trong `tests/fakes/memory_plan_store.py`, `replace` ném `PlanConflictError` khi `plan.version` khác bản đang lưu và không gán đè (phụ thuộc T021). Khớp thì bản lưu có `version` tăng `1`. Bản người gọi đang cầm không tự tăng

- [X] T025 [US2] Tạo `supabase/migrations/20261103205500_plans_version.sql` (phụ thuộc T023). Không sửa `supabase/migrations/20261025021100_plans_and_subtasks.sql`. Cột `version integer not null default 0`, hàng có sẵn thành `0`. `add_plan` được `create or replace`, giữ chữ ký `(text, jsonb)`, JSON trả về có `version`, rồi `revoke all on function public.add_plan(text, jsonb) from public, anon, authenticated` và `grant execute on function public.add_plan(text, jsonb) to service_role`. Drop `replace_plan(uuid, text, jsonb)`. Tạo `replace_plan(uuid, text, jsonb, integer)`. Kiểm và tăng atomic: một `update ... where id = plan_id and version = expected_version`, không có hàng thì mới phân biệt `plan_missing` và `plan_version_conflict`; hoặc `select ... for update` rồi so. Không `select` rồi so mà không khóa. So bằng tay thì `is distinct from`. Lệch hoặc không có hàng thì không sửa `plans` và không sửa `subtasks`. Hàm mới không thừa hưởng quyền hàm cũ: `revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated`, rồi `grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role`

- [X] T028 [US2] Trong `src/db/client.py`, `_PLAN_COLUMNS` có `version` (phụ thuộc T025, T027). Thiếu cột này thì mọi lần đọc lỗi vì `PlanRow.version` bắt buộc

- [X] T030 [US2] Trong `src/db/client.py`, `replace_plan` gửi `expected_version` (phụ thuộc T025, T028). `APIError` có message `plan_version_conflict` thành lỗi client riêng, không phải `StoredPlanMissing`, không phải câu người dùng. `plan_missing` giữ như hiện tại

- [X] T031 [US2] Trong `src/db/plan_store.py`, `replace` lấy version từ `plan.version` và gọi RPC với số đó (phụ thuộc T030, T029). Lỗi `plan_version_conflict` thành `PlanConflictError`. Không thêm phương thức `PlanStore`. Bốn phương thức giữ nguyên

- [X] T032 [US2] Trong `src/tools/plan_tools.py`, bắt `PlanConflictError` và đổi thành `ToolError` với đúng câu từ chối trong `src/tools/saved_reply.py` (phụ thuộc T022, T031). Không gọi `replace` lần thứ hai. `error_type` giữ `domain`. Không thêm giá trị `error_type`. JSON thành công không có khóa `version`

**Checkpoint**: Ca memory và ca `gather` khóa đúng nhánh từ chối. Không có task gộp hai lần ghi

---

## Phase 5: User Story 3 - Lượt không kết thúc bình thường vẫn nói những gì đã lưu (Priority: P1)

**Goal**: Khi đã ghi, đã bỏ, hoặc đã từ chối, chuỗi lượt là bản ghép từ `src/tools/saved_reply.py`. Văn bản mô hình còn chữ khác khoảng trắng giữ nguyên

**Independent Test**: Mô hình giả ghi thành công rồi hết giờ, lỗi, trần ba vòng, bị cắt, bị từ chối, hoặc trả rỗng hay chỉ khoảng trắng. Đọc chuỗi lượt

### Tests

- [X] T033 [US3] Viết trong `tests/test_llm_turn.py` các ca bản ghép sau lần ghi thành công (phụ thuộc T009, T010). `create_plan` có một việc, có hai việc, và không việc; `add_subtask`; `update_subtask` ra `xong` không hiện mã; `set_subtask_note` còn chữ và xóa ghi chú; hai lần ghi ra `1.` rồi `2.` Đúng chữ Assumptions của spec. Các lối: hết giờ, mô hình lỗi, trần ba vòng, câu trả lời bị cắt, bị từ chối, văn bản rỗng, văn bản chỉ khoảng trắng. Chuỗi không phải `Chưa liên lạc được để trả lời lúc này.` và không phải `Chưa trả lời xong yêu cầu này.` Chạy trước khi `run_turn` gọi hàm ghép. Kỳ vọng fail. Không đổi assertion của `test_empty_text_is_success`

- [X] T034 [US3] Viết trong `tests/test_llm_turn.py` ca thứ tự ghép (phụ thuộc T033). Đã lưu rồi câu chưa chắc. Đã lưu rồi câu từ chối. Chỉ câu chưa chắc. Chỉ câu từ chối. Cả ba: dòng đã lưu, rồi chưa chắc, rồi từ chối, không dòng trống. Chạy trước mã ghép của lượt. Kỳ vọng fail

- [X] T035 [US3] Viết trong `tests/test_llm_turn.py` ca văn bản mô hình (phụ thuộc T033). Còn chữ khác khoảng trắng thì trả đúng văn bản đó, kể cả đã ghi, và kể cả sau khi tool đã trả câu chưa chắc hoặc câu từ chối. Rỗng khi không có lần ghi thành công, lần ghi bị bỏ, và lần ghi bị từ chối vẫn `""`. Chỉ khoảng trắng khi không có cả ba trả đúng văn bản đó. Chưa có lần ghi thành công, chưa bỏ, chưa từ chối thì hết giờ và trần ba vòng vẫn là hai câu spec lượt mô hình. Khi lượt còn chạy tiếp sau lỗi tool, `ToolResultMessage` gửi lại mô hình có `output` đúng chữ tool trả, gồm câu chưa chắc và câu từ chối. Trường hiệu lực không có trong tin đó. Không sửa test hủy tác vụ và test thiếu khóa. Chạy trước mã. Kỳ vọng fail ở ca đã ghi mà văn bản rỗng

### Implementation

- [X] T036 [US3] Trong `src/tools/plan_tools.py`, lần ghi thành công gắn cờ hiệu lực đã lưu để `src/tools/saved_reply.py` ghép đúng mẫu (phụ thuộc T033, T032). `output` gửi mô hình giữ nguyên chữ JSON hiện có. JSON không có `version`

- [X] T037 [US3] Trong `src/turns/llm_turn.py`, khi lượt không kết thúc bình thường và đã có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối, trả đúng hàm ghép (phụ thuộc T034, T035, T036, T019). Tin nhắn gửi mô hình chỉ lấy `output`, không lấy trường hiệu lực. Hủy tác vụ vẫn đi ra. Thiếu khóa vẫn lỗi trước mọi lời gọi

**Checkpoint**: Ba story pass trên kho giả. Ca `gather` là ca kho local, không chạy ở task này

---

## Phase 6: Polish

**Purpose**: Đồng bộ docs. Không push, không deploy, không `pywrangler`

- [X] T038 Sửa `docs/PRODUCT.md` mục §7 thứ tự làm tiếp, mục 1: `L1-01 đến L1-04` thành `L1-01 đến L1-03` (phụ thuộc T037, T020, T025). Trong `docs/reviews/2026-11-01-repo-review.md`, L1-01 thành `đã sửa ở 012-write-durability (timeout trên Worker chưa kiểm chứng)`. L1-02 và L1-03 thành `đã sửa ở 012-write-durability`. Không đổi L1-04. Không ghi timeout trên Worker là đã kiểm chứng. Rà `docs/ARCHITECTURE.md` và `AGENTS.md`: câu nào thành sai sau lát này thì sửa câu đó. `docs/DECISIONS.md` chỉ được thêm D-021 và một dòng Cập nhật ở D-011, người dùng đã duyệt ở B10 (2026-11-04). Không sửa `.specify/memory/constitution.md`. Nếu một câu trong hai file đó thành sai, dừng, không sửa

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: Không có task
- **Foundational**: T001 rồi T005. T002 rồi T008. T003 rồi T009. T004 rồi T010. T006, T007, và T026 sau T005, song song với nhau. T027 sau T026. T029 sau T027. T029 xong thì `tests/test_plan_row_mapping.py` dựng lại được. Chặn mọi story
- **US1**: Sau foundational. T011 đến T016 và T040 trước T017. T017 đến T019 sau T040. T039 trước T020. T015 song song với T011
- **US2**: Sau foundational. T028 ở lại phase này, phụ thuộc T025 và T027. Không cần US1 để thử kho giả, nhưng tool từ chối dùng `wait_for` và `ToolError` của US1 nên T032 sau T018
- **US3**: Sau US1 và US2, vì bản ghép đọc cờ hiệu lực do hai story đó đặt
- **Polish**: Sau T037, T020, và T025

### User Story Dependencies

- **US1**: Sau nền. Không cần version để chứng minh kho giả bị bỏ
- **US2**: Sau nền. Task tool T032 sau US1
- **US3**: Sau US1 và US2

### Within Each User Story

- Test viết và fail trước mã tương ứng, trừ T016: test đó khóa hành vi hiện có và phải pass trước khi sửa router
- Không đổi assertion cũ ngoài ba hành vi spec đã nêu

### Parallel Opportunities

- T006, T007, và T026 sau T005
- T015 với T011
- T022 và T023

---

## Parallel Example: Foundational

```text
T006: tests/test_plan_store_contract.py và tests/test_supabase_plan_store.py thêm version
T007: tests/fakes/memory_plan_store.py
T026: src/db/models.py PlanRow.version
```

Ba file khác nhau, cùng sau T005. T027 chờ T026. T029 chờ T027.

## Parallel Example: User Story 2

```text
T022: tests/test_store_call_limit.py câu từ chối
T023: tests/test_supabase_plan_store.py asyncio.gather
```

Hai file khác nhau. Cả hai viết trước migration và trước nhánh bắt xung đột trong tool. T028 không song song: chờ T025 và T027.

---

## Implementation Strategy

### MVP

US1 sau nền: lời gọi kho không kéo lượt quá hạn trên kho giả. US2 và US3 cùng priority P1. Lát này chưa xong nếu chỉ có US1.

1. Phase 2
2. US1, dừng để xem ca kho giả và ca `run_turn`
3. US2, gồm file migration. Không `db reset` trong tasks
4. US3
5. T038

### Incremental Delivery

Nền làm `Plan(...)` thiếu `version` lỗi ngay. US1 thêm hạn. US2 thêm từ chối. US3 thêm bản ghép.

### Parallel Team Strategy

Một người. Không chia story cho người khác trước khi nền xong.

---

## Notes

- Nhánh chồng nhau là từ chối, không gộp. Ca cả hai cùng thành công trên cùng một kế hoạch là T021, khi lần sau bắt đầu đọc sau khi lần trước đã trả về
- FR-013 và SC-007 không có test riêng vì kiểm file thay đổi theo allowed-files.txt (AGENTS.md dòng 40) chặn file ngoài danh sách; system_prompt, tool_definitions, evals không có trong danh sách
- Mục Worker và mục thứ tự lên production trong `quickstart.md` không có task. Không chạy `pywrangler`, không deploy
- Lỗi mạng `httpx` không phải quá hạn không có xử lý riêng. T016 khóa điều đó
- Timeout trên Worker để quickstart ghi là chưa kiểm chứng. Không task nào đổi nhãn đó thành đạt

---

## Phase 7: Sửa sau B9

- [X] T041 Sửa văn bản rỗng hoặc chỉ khoảng trắng theo G16. File chính `src/turns/llm_turn.py`. Spec và các câu quy tắc cũ trong `specs/012-write-durability/` sửa trước. Test trong `tests/test_llm_turn.py` chạy đỏ ở so chuỗi trước khi sửa `_normal_text`

- [X] T042 [B1] Trong `tests/test_store_call_limit.py`, `add_subtask` với `remaining` trả `[20.0, 0.0]`. `get` chạy, `replace` không gửi. `success` sai, câu không thực hiện được, không hiệu lực, `remaining` đúng hai lần

- [X] T043 [B2] Trong `tests/test_store_call_limit.py`, `remaining` trả `[20.0, 0.05]` và `replace` treo. Câu chưa chắc, hiệu lực uncertain, đủ `get` rồi `replace`, `remaining` đúng hai lần, `time.monotonic` dưới 1 giây

- [X] T044 [C1] Trong `tests/test_tool_router.py`, A thêm "Mua vở" và B đặt "Học hiragana" xong, B đọc trước khi A trả về. A thành công. B từ chối đúng câu. Kho còn "Mua vở", hiragana chưa làm, "Nghe hội thoại" còn, version tăng 1

- [X] T045 [C2] Trong `tests/test_tool_router.py`, A đặt hiragana xong và B đặt bỏ qua, cùng thứ tự. B từ chối. Hiragana là xong. "Nghe hội thoại" không mất

- [X] T046 [C3] Trong `tests/test_llm_turn.py`, vòng sau nhận tool message `output` đúng câu từ chối và `is_error` đúng. Chưa có test này trước vòng sửa

- [X] T047 [D1] Trong `tests/test_store_call_limit.py`, `create_plan` treo ở `add`. Hủy task sau khi kho đã nhận `add`. `await` ném `CancelledError`

- [X] T048 [D2] Trong `tests/test_llm_turn.py`, một lần `create` thành công rồi `complete` ném `CancelledError`. `run_turn` ném `CancelledError`, không trả bản ghép

- [X] T049 [E1] Trong `tests/test_llm_turn.py`, xóa hai assert chết và biến `added` không dùng của `test_saved_lines_replace_abnormal_endings`. Ca `update_subtask` đã assert "xong" và không chứa "done" hay "pending"

- [X] T050 [E2] Trong `tests/test_plan_row_mapping.py`, thiếu khóa `version` kỳ vọng `KeyError` khớp "version". `plan_from_row` ném `KeyError`, không phải `ValueError`. Không sửa `src`

- [X] T051 [F] `Remaining` công khai ở `src/tools/base.py`. `plan_tools.py` và `tool_router.py` import từ đó và xóa hai bí danh riêng. Không đổi chữ ký hay hành vi

---

## Phase 8: Đồng bộ docs (B10)

- [X] T052 `docs/PRODUCT.md`: bỏ mục độ bền ghi ở §7, đánh số lại 1 đến 4, và trỏ F11 tới L1-04, L1-12, L1-13

- [X] T053 `docs/ARCHITECTURE.md`: dòng trạng thái code, bullet `src/core/`, `src/tools/`, `src/db/`

- [X] T054 `docs/DECISIONS.md`: D-021 và dòng Cập nhật ở D-011. Cùng `specs/012-write-durability/allowed-files.txt` và câu Assumptions của `spec.md`

- [X] T055 `docs/reviews/2026-11-01-repo-review.md`: năm hàng L1-09 đến L1-13

- [X] T056 `AGENTS.md` và `docs/architecture/` đã xét, không đổi
