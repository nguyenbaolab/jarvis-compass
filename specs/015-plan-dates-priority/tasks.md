---
description: "Task list for Ngày, ưu tiên và sức của kế hoạch"
---

# Tasks: Ngày, ưu tiên và sức của kế hoạch

**Input**: Design documents from `/specs/015-plan-dates-priority/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Chữ ký hoặc file phải có trước task test dùng nó. Mỗi ca là một hàm. Không gộp assert của nhiều ca vào một hàm. Test đang khóa tập khóa được sửa trong cùng task đổi tập đó.

**Organization**: Ba lô theo thứ tự chat đã chốt, không phải một phase mỗi user story. Story nào nằm ở lô nào ghi ở mục Dependencies. Không task nào sửa `docs/DECISIONS.md`. Chat viết D-026 và Cursor chép trong một bước riêng, trước T001. File đó vẫn nằm trong `allowed-files.txt` để bước chép không bị check.ps1 chặn.

**Trước T001, không phải task implement**: Chat viết D-026 theo bảy điểm ở research.md mục 12. Cursor chỉ chép chữ đã duyệt vào `docs/DECISIONS.md`. Chưa có chữ đó thì không bắt đầu T001.

## Format: `[ID] [P?] Description`

- **[P]**: File khác nhau, không phụ thuộc task chưa xong trong cùng lô
- Không gắn nhãn story. Lô là thứ tự bắt buộc
- Mỗi task một việc, có đường dẫn file

## Path Conventions

- File được sửa hoặc tạo chỉ là các dòng trong `specs/015-plan-dates-priority/allowed-files.txt`
- Không thêm gói. Không sửa `pyproject.toml`, `uv.lock`, `pylock.toml`
- Không sửa bốn migration đã có. Không sửa `specs/014-morning-digest/tasks.md`. Không sửa diagram `docs/architecture/`
- Không sửa `.specify/memory/constitution.md`. Không đọc, không ghi `.env` và `.dev.vars`
- Không `db push`, không deploy, không `pywrangler` trong các task này
- `npx` supabase ghim `2.122.0`. `db reset` trong task kho là kho local

## Phase 1: Lô 1 — Tầng dữ liệu

**Purpose**: Migration, model `src/core`, `src/db`, cổng lưu và đồ giả, test kho. Hết lô thì dừng để chat đọc migration và `src/db`

**Independent check**: Pytest phần kho và hàm thuần xanh trên bộ nhớ và, khi Supabase local chạy, trên kho local. `test_latest_rpc_definitions_are_not_void` xanh mà không sửa file test đó

### Schema và model

- [ ] T001 Tạo `supabase/migrations/20261109120000_plan_dates_priority.sql`. Không sửa file migration khác. Trong một transaction: thêm `plans.priority text` null, kiểm chỉ `high`, `medium`, `low` hoặc null. Thêm `subtasks.scheduled_on date` null và `subtasks.effort text` null, kiểm chỉ `S`, `M`, `L` hoặc null. Tạo `subtask_date_moves` với cột `id uuid` khóa chính tự sinh, `plan_id uuid` not null, `subtask_id uuid` not null, `from_date date` not null, `to_date date` not null và khác `from_date`, `reason text` null, `moved_at timestamptz` not null. Không khóa ngoại. Trigger `BEFORE UPDATE OR DELETE` làm `RAISE EXCEPTION`. `drop function` đúng `public.add_plan(text, jsonb)` và `public.replace_plan(uuid, text, jsonb, integer)`, rồi tạo lại. `add_plan(goal text, subtasks jsonb, priority text DEFAULT NULL)` trả object kế hoạch, không void. Object đó có khóa `priority`. Mỗi phần tử `subtasks` trong object có khóa `scheduled_on` và `effort`. Không gửi thì hai khóa việc và `priority` là null. `replace_plan` trả `boolean`, tham số cuối `plan_fields jsonb DEFAULT NULL`, `move_reason text DEFAULT NULL`, `moved_at timestamptz DEFAULT NULL`. `plan_fields` null hoặc không có khóa `priority` thì giữ ưu tiên. Khóa có mặt thì đặt. JSON null là xóa. Trong từng việc, khóa `scheduled_on` hoặc `effort` vắng thì giữ. Khóa có mặt thì đặt. JSON null là xóa. Khóa `note` vắng vẫn thành null. Đổi từ một ngày sang một ngày khác thì `INSERT` một dòng trong cùng hàm. `moved_at` null mà có việc đổi ngày thì `raise` và không ghi kế hoạch. Không gọi `now()`. `revoke` khỏi `public`, `anon`, `authenticated`. `grant execute` cho `service_role` trên đúng chữ ký mới

- [ ] T002 Sửa `src/core/plans.py` (phụ thuộc T001 không bắt buộc để viết, nhưng cùng lô). `Priority` là `StrEnum` `high`, `medium`, `low`. `Effort` là `StrEnum` `S`, `M`, `L`. `EFFORT_HOURS` là S = 1, M = 3, L = 6. Không cộng giờ. `Subtask` thêm `scheduled_on: date | None = None` và `effort: Effort | None = None` đứng cuối. `Plan` thêm `priority: Priority | None = None` đứng cuối. `PlanStore.add` thêm `priority` keyword, mặc định `None`. `PlanStore.replace` thêm `move_reason: str | None = None` và `moved_at: datetime | None = None`, keyword. `normalize_new_plan` nhận danh sách đối tượng có tiêu đề, ngày và sức tùy chọn. `_plan_with_subtasks` chép `priority`. Thêm `plan_deadline`, `deadline_clash`, `date_moves` đúng data-model.md. Chuỗi ngày không phải `YYYY-MM-DD`, hoặc mã ưu tiên hay sức lạ, là `PlanDomainError`. Cùng task, trong `tests/test_plan_row_mapping.py` hàm `test_valid_row_becomes_plan`, đổi tập khóa dataclass của việc con thành `id`, `title`, `status`, `note`, `scheduled_on`, `effort`. Trong `tests/test_plan_store_contract.py`, `_written` chép `priority`. Không đổi assertion khác của các hàm cũ

- [ ] T003 [P] Sửa `src/db/models.py` (phụ thuộc T002). `PlanRow.priority: str | None = None`. `SubtaskRow.scheduled_on: str | None = None`. `SubtaskRow.effort: str | None = None`. Hàng thiếu khóa vẫn qua Pydantic

- [ ] T004 [P] Sửa `src/db/client.py` (phụ thuộc T002). `_PLAN_COLUMNS` thêm `plans.priority`, `subtasks.scheduled_on`, `subtasks.effort`. `add_plan` gửi `priority`, `None` thành JSON null. `replace_plan` gửi `plan_fields`, `move_reason`, `moved_at`. Vẫn không đọc boolean. Lỗi vẫn chỉ `plan_missing` và `plan_version_conflict`

- [ ] T005 Sửa `src/db/plan_store.py` (phụ thuộc T003, T004). `plan_from_row` đưa ba trường vào model. Khóa vắng trên dòng đọc là `None`. `add` đưa `priority` xuống client. `replace` luôn gửi `plan_fields` có khóa `priority`, `None` thành JSON null, và luôn gửi khóa `scheduled_on` cùng `effort` của từng việc. Chỉ lời gọi dời ngày truyền `move_reason` và `moved_at`. Cùng task thêm hai hàm trong `tests/test_plan_row_mapping.py`: `test_row_without_new_columns_is_empty` và `test_row_maps_priority_date_and_effort`. Mỗi hàm một ca

- [ ] T006 Sửa `tests/fakes/memory_plan_store.py` (phụ thuộc T002). `add` lưu `priority`. `replace` gán ưu tiên từ `Plan`, `None` là xóa, và ghi lịch sử bằng `date_moves` với lý do và mốc được truyền. `moved_at` là `None` mà `date_moves` không rỗng thì ném lỗi và không ghi kế hoạch, không gọi `datetime.now`. Cùng luật với `replace_plan` trong SQL. Danh sách dòng nằm trên instance. Không đếm lịch sử của instance khác

### Test kho

- [ ] T007 Viết `tests/test_plan_dates.py` (phụ thuộc T002). Mỗi tên dưới đây là một hàm, không gộp ca. `test_plan_deadline_is_latest_pending_date`. `test_plan_deadline_ignores_done_skipped_and_undated`. `test_plan_deadline_is_none_when_no_pending_date`. `test_deadline_clash_skips_the_same_plan_id`. `test_date_moves_includes_date_to_other_date`. `test_date_moves_excludes_empty_to_date`. `test_date_moves_excludes_date_to_empty`. `test_date_moves_excludes_same_date`. `test_bad_iso_date_is_domain_error`. `test_bad_priority_is_domain_error`. `test_effort_hours_are_one_three_six`

- [ ] T008 Thêm vào `tests/test_plan_store_contract.py` các hàm dùng fixture `plan_store` sẵn có, nên mỗi hàm chạy trên `MemoryPlanStore` và trên Supabase local (phụ thuộc T005, T006). Mỗi hàm một ca. Lịch sử chỉ xét `plan_id` và `subtask_id` của lần ghi, không đếm cả bảng. `test_date_to_other_date_writes_one_history_row`. `test_empty_to_date_writes_no_history_row`. `test_date_to_empty_writes_no_history_row`. `test_same_date_writes_no_history_row`. `test_several_date_changes_write_one_row_each`. `test_version_conflict_keeps_dates_and_writes_no_row`. `test_null_moved_at_on_date_change_errors_and_keeps_plan`. `test_dropped_subtask_keeps_its_history`. `test_add_returns_priority_date_and_effort`: `store.add` trả `Plan` mang đúng ưu tiên, và từng việc mang đúng ngày cùng sức vừa đặt. Trước lần chạy supabase: `npx --yes supabase@2.122.0 db reset` trên kho local, rồi đặt `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ `status -o json`. Host phải là `127.0.0.1` hoặc `localhost`

- [ ] T009 Thêm vào `tests/test_supabase_plan_store.py` các lời gọi RPC thô, không đi qua client Python bản mới (phụ thuộc T001, T008). Mỗi hàm một ca. `test_add_plan_two_args_is_not_ambiguous`. `test_replace_plan_four_args_runs`. `test_missing_scheduled_on_keeps_stored_date`. `test_missing_effort_keeps_stored_effort`. `test_missing_plan_fields_keeps_priority`. `test_json_null_clears_scheduled_on`. `test_json_null_clears_effort`. `test_json_null_clears_priority`. `test_missing_note_becomes_null`. `test_add_plan_stores_priority`. `test_clocks_stay_when_status_unchanged` cho FR-010: đổi ngày, sức hoặc ưu tiên không đổi `created_at` và không đổi `status_changed_at`. Đổi `status` vẫn đổi `status_changed_at`. `test_history_trigger_blocks_update`. `test_history_trigger_blocks_delete`. Không sửa `empty_plan_tables` để xóa lịch sử

- [ ] T010 Chạy `uv run pytest tests/test_rpc_returns.py::test_latest_rpc_definitions_are_not_void` (phụ thuộc T001, T004). Không sửa `tests/test_rpc_returns.py`. Đỏ thì sửa migration cho định nghĩa cuối của `add_plan` và `replace_plan` không phải `void`, rồi chạy lại

### Đột biến lô 1

Mỗi đột biến: sửa đúng chỗ, chạy đúng hàm, thấy đỏ, hoàn tác, `git diff` của file đó rỗng. Ghi một dòng kết quả ngay dưới task khi làm.

- [ ] T011 Trong `supabase/migrations/20261109120000_plan_dates_priority.sql`, mọi nhánh "khóa vắng thì giữ" của `replace_plan` đổi thành gán null, gồm `scheduled_on`, `effort` và `priority` (phụ thuộc T009). `test_missing_scheduled_on_keeps_stored_date` phải đỏ. Hoàn tác

- [ ] T012 Trong cùng file migration, bỏ trigger `BEFORE UPDATE OR DELETE` của `subtask_date_moves` (phụ thuộc T009). `test_history_trigger_blocks_delete` phải đỏ. Hoàn tác

- [ ] T013 Trong cùng file migration, bỏ lệnh `INSERT` vào `subtask_date_moves` (phụ thuộc T008). `test_date_to_other_date_writes_one_history_row` phải đỏ trên Supabase. Hoàn tác

### Điểm dừng lô 1

- [ ] T014 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T001 đến T013). Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T016

- [ ] T015 DỪNG: chat đọc migration, `src/db`, `src/core/plans.py` và `tests/fakes/memory_plan_store.py` trên đĩa. Không bắt đầu lô 2 trước khi chat nói tiếp

---

## Phase 2: Lô 2 — Hành vi

**Purpose**: Đồng hồ, lượt, ngữ cảnh, chín tool, mười một mẫu, lời hướng dẫn bản 4. Hết lô thì dừng để chat đọc diff

**Independent check**: `run_turn` thiếu `instant` là `TypeError`. Catalog là 3 và chín tên. Sáu tool cũ vẫn gọi được khi không truyền `turn`. Chín tool đều tới handler qua `execute_tool`

- [ ] T016 Tạo `src/core/clock.py` (phụ thuộc T015). Đặt `helsinki_clock` và `_helsinki_zone` vào đây. Chưa xóa bản trong `src/core/morning.py`. Thêm `weekday_name_vi(day: date) -> str` với bảy chữ: thứ Hai, thứ Ba, thứ Tư, thứ Năm, thứ Sáu, thứ Bảy, Chủ nhật. Thêm `turn_date_line(instant) -> str`. Mốc không có `tzinfo` thì `ValueError`. Dòng có năm và chữ `Europe/Helsinki`, dạng `Hôm nay là thứ Sáu 06/11/2026, múi giờ Europe/Helsinki.`

- [ ] T017 Sửa `src/core/morning.py` (phụ thuộc T016). Xóa `helsinki_clock` và `_helsinki_zone` cục bộ. Import từ `core.clock` và gán lại tên `helsinki_clock` để `from core.morning import helsinki_clock` còn đúng. Chưa sửa `render_digest`. Cùng task sửa câu vị trí hàm trong `specs/014-morning-digest/contracts/digest-text.md`: `helsinki_clock` định nghĩa ở `src/core/clock.py`, `core.morning` vẫn export. Chưa sửa câu cấm thêm ngày. Cùng task sửa `tests/test_morning_clock.py`: `test_import_does_not_need_zone_data` nạp lại `core.clock` dưới `ZoneInfo` giả và xóa cache `core.clock._helsinki_zone`, không còn đọc `morning._helsinki_zone`. Giữ import `helsinki_clock` từ `core.morning` ở đầu file. Thêm hàm `test_helsinki_clock_imports_from_morning` nếu import đó chưa có assert riêng

- [ ] T018 Thêm `TurnContext` vào `src/tools/base.py` (phụ thuộc T015). Dataclass không đóng băng. Có `instant: datetime` và `clash_reported: bool = False`. Không import `db`

- [ ] T019 Sửa `src/tools/tool_router.py` (phụ thuộc T018). `execute_tool` nhận `turn: TurnContext | None = None` và `_invoke` đưa `turn` vào mọi handler đang có. Sáu handler nhận `turn` và bỏ qua khi chưa dùng. Không thêm tool. Không sửa `_type_error` ở task này. Không thêm khóa log

- [ ] T020 Sửa `src/turns/llm_turn.py` (phụ thuộc T016, T018, T019). `run_turn` nhận `instant` keyword, không mặc định. Đầu lượt dựng một `TurnContext` và ghép `turn_date_line` sau hằng `SYSTEM_PROMPT`. Mọi `execute_tool` của lượt nhận cùng đối tượng qua `turn`. Không rẽ theo tên tool và không đọc chữ kết quả. Cùng task sửa lời gọi cho suite không đỏ: `src/api/telegram_update.py` truyền `now`. `evals/turn.py` truyền `2026-11-06T08:00:00+02:00` cho đến khi T042 đọc mốc của ca. `tests/test_llm_turn.py` truyền cùng mốc đó vào mọi `run_turn` đang có. Rồi thêm năm hàm, mỗi hàm một ca: `test_run_turn_without_instant_is_type_error`. `test_turn_date_line_ignores_a_later_clock`: đồng hồ giả nhảy sang ngày hôm sau giữa hai lần gọi mô hình, cả hai request vẫn thấy dòng của mốc đầu. `test_date_line_winter` với `2026-11-06T08:00:00+02:00` ra `thứ Sáu 06/11/2026`. `test_date_line_summer` với `2026-07-01T08:00:00+03:00` ra `thứ Tư 01/07/2026`. `test_sunday_name_is_chu_nhat` với `2026-11-08T08:00:00+02:00` chứa `Chủ nhật` và không chứa `thứ Chủ nhật`

- [ ] T021 Sửa `src/core/system_prompt.py` (phụ thuộc T020). `PROMPT_VERSION` là 4. Giữ mọi câu bản 3, gồm luật goal ngắn và câu ví dụ báo cáo thứ Sáu. Thêm luật: ngày vào trường ngày, không vào tiêu đề. Hạn tương đối theo FR-019, gồm "thứ X tuần sau". Khi đã chọn ngày thì nói ngày đó. Trùng thì báo, không ghi, hỏi, chỉ gọi lại với cờ ở lượt sau. Hằng không chứa dòng ngày. Cùng task, trong `tests/test_llm_turn.py`, đổi tên `test_system_prompt_has_seven_laws` thành `test_system_prompt_has_version_four_laws`. Hàm khóa số 4, khóa các câu bản 3 còn nguyên, và khóa các câu luật mới. Không gọi mô hình thật

- [ ] T022 Sửa `src/tools/tool_definitions.py` (phụ thuộc T015). `DEFINITIONS_VERSION` là 3. Giữ sáu tool. Thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks` đúng `contracts/tools.md`. Mô tả một dòng: `Đặt hoặc xóa ưu tiên của một kế hoạch.`, `Đặt hoặc xóa sức của một việc con.`, `Dời ngày của các việc trong một kế hoạch.` `create_plan` nhận `priority` tùy chọn và `subtasks` là mảng object, không còn mảng chuỗi. Cùng task sửa `tests/test_tool_router.py`: `test_catalog_matches_contract` khóa số 3, chín tên, và schema object của `create_plan`. Hàm `_run` khóa `definitions_version` bằng hằng `DEFINITIONS_VERSION`, không khóa số 2

- [ ] T023 Sửa `src/tools/schemas.py` và `_plan_json` trong `src/tools/plan_tools.py` (phụ thuộc T002, T005). `PlanJson` thêm `priority`, thứ tự khóa `id`, `goal`, `priority`, `subtasks`. `SubtaskJson` thêm `scheduled_on` và `effort`, thứ tự `id`, `title`, `status`, `note`, `scheduled_on`, `effort`. `_plan_json` điền ba trường đó, trống thành null. Cùng task sửa các chỗ đang khóa tập khóa cũ, không để test đỏ rồi vá: `tests/helpers.py` trong `pending_or_done_plan` và `pending_plan`. `tests/test_get_plans.py` trong `_plans`. `tests/test_subtask_skip_note.py` ở hai chỗ so tập khóa kế hoạch và danh sách khóa việc. Giá trị trống là JSON null

- [ ] T024 Sửa `src/tools/saved_reply.py` (phụ thuộc T015). Giữ sáu mẫu cũ đúng chữ trong `contracts/saved-lines.md`. Thêm năm mẫu: đặt ưu tiên, bỏ ưu tiên, đặt sức, bỏ sức, dời ngày. Dòng tạo kế hoạch không nêu ngày. Dòng dời ngày một dòng cho cả lần ghi, nhiều tiêu đề nối bằng dấu phẩy, không có ngày cũ, ngày mới, hay lý do. Cùng task sửa `tests/test_saved_reply.py`: docstring còn nói sáu mẫu thì sửa thành mười một. Giữ assert của `test_sentences_and_templates_match_spec`. Thêm năm hàm: `test_saved_set_priority_line`, `test_saved_clear_priority_line`, `test_saved_set_effort_line`, `test_saved_clear_effort_line`, `test_saved_reschedule_line`. `test_fixed_strings_live_only_in_saved_reply` cũng thấy năm chuỗi mới chỉ ở `tools/saved_reply.py`

- [ ] T025 Sửa `src/tools/plan_tools.py` (phụ thuộc T005, T006, T019, T023, T024). `create_plan` nhận ưu tiên tùy chọn và việc là đối tượng có `title`, `scheduled_on`, `effort`. Chuỗi tiêu đề vẫn được bọc thành đối tượng chỉ có title, để lời gọi `list[str]` của test cũ không vỡ. Ưu tiên là `None` thì `create_plan` gọi `store.add(goal, subtasks)`, đúng hai tham số vị trí, không có keyword. Chỉ khi có ưu tiên thì gọi `store.add(goal, subtasks, priority=...)`. Không sửa các lớp test ghi đè `add` hay `replace`. Lý do: các lớp đó giữ chữ ký cố định ở `tests/test_llm_turn.py`, `tests/test_store_call_limit.py`, `tests/test_tool_router.py`, `tests/helpers.py`, `tests/test_telegram_route.py` và `tests/test_telegram_update_flow.py`. Chỉ lời gọi dời ngày truyền `move_reason` và `moved_at` cho `replace`. `add_subtask` thêm `scheduled_on` và `effort` keyword, mặc định `None`. Không kiểm trùng ở hai tool này. Không sinh lịch sử. Thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks`. Tool dời ngày không có `turn` thì `ToolError`, không ghi, không gọi `datetime.now`. `moved_at` là `turn.instant`. Trùng và `confirm` không true: thành công, không ghi, `effect` là `None`, đặt `clash_reported`. `confirm` true khi cờ đã đặt: `ToolError`, không ghi. `confirm` true trên ngữ cảnh mới: ghi. Không trùng thì ghi dù không cờ. Hạn sau lần dời không đổi thì không đòi xác nhận. Kế hoạch cùng id không đưa vào phép so. Hạn chỉ tính việc `pending` có ngày. `update_subtask` và `set_subtask_note` không nhận ngày, sức, ưu tiên. Cùng task thêm hàm vào `tests/test_create_plan.py`: `test_create_plan_stores_date_effort_and_priority`. `test_create_plan_without_priority_calls_add_with_two_arguments`: một store ghi lại lời gọi, đúng hai tham số vị trí và không có keyword. `test_create_plan_with_priority_passes_it_to_add`. Thêm hàm vào `tests/test_add_subtask.py`: `test_add_subtask_stores_date_and_effort`. Mỗi hàm một ca

- [ ] T026 Sửa `_type_error` trong `src/tools/tool_router.py` (phụ thuộc T022, T025). Nhận `boolean`, `null`, mảng object, và `additionalProperties: false` đệ quy trên object lồng. Không đụng chữ ký `turn` đã có từ T019. Không thêm khóa log. Bảy khóa tool và tám khóa mô hình giữ nguyên thứ tự

- [ ] T027 Sửa các lời gọi router đang gửi `subtasks` là chuỗi (phụ thuộc T025, T026). Số dòng là file hiện tại, trước khi T022 chèn dòng vào `tests/test_tool_router.py`. Nếu số trượt thì khớp đúng payload. Dòng 156 đổi `["Học hiragana", None]` thành `[{"title": "Học hiragana"}, None]`, câu kỳ vọng vẫn `Một phần tử của trường subtasks sai kiểu.` Dòng 157 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`, câu kỳ vọng vẫn `Đầu vào thiếu trường goal.` Dòng 269 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`. Dòng 322 giữ `[object()]` để log input là null, câu kỳ vọng vẫn `Một phần tử của trường subtasks sai kiểu.` Dòng 435 đổi `("Một",)` thành `({"title": "Một"},)`, câu kỳ vọng vẫn `Trường subtasks sai kiểu.` Dòng 446 giữ `subtasks: None`, câu kỳ vọng vẫn `Trường subtasks sai kiểu.` Dòng 522 và dòng 526 cùng đổi `["Hiragana", "Katakana"]` thành `[{"title": "Hiragana"}, {"title": "Katakana"}]`, kể cả object so với log. Dòng 581 đổi payload cùng kiểu đó. `tests/test_store_call_limit.py` dòng 107 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`. Không gộp các ca này vào một hàm mới

- [ ] T028 Sửa `src/tools/tool_router.py` (phụ thuộc T019, T022, T025, T026). `_DISPATCH` thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks`. `_create` chuyển `priority`, `scheduled_on`, `effort` từ object xuống `create_plan`. `_add` chuyển `scheduled_on` và `effort`. Mọi handler, cũ và mới, nhận `turn`. Cùng task thêm `test_each_of_nine_tools_reaches_its_handler` vào `tests/test_tool_router.py`: gọi từng tool trong chín tool qua `execute_tool` và thấy handler chạy

- [ ] T029 Thêm bốn hàm vào `tests/test_tool_router.py` (phụ thuộc T026, T028). Mỗi hàm một ca. `test_boolean_confirm_is_accepted`. `test_null_priority_is_accepted`. `test_array_of_objects_is_accepted`. `test_nested_unknown_key_is_invalid_input`: khóa lạ trong phần tử `changes` hoặc `subtasks` là lỗi đầu vào, không gọi kho

- [ ] T030 Viết `tests/test_reschedule_subtasks.py` (phụ thuộc T024, T025, T028). Dùng `MemoryPlanStore`. Mỗi hàm một ca. `test_reschedule_without_turn_context_does_not_write`. `test_clash_without_confirm_does_not_write`: không ghi, đặt cờ, `effect` là `None`, `compose` không nhận chữ trùng vì không có `Saved`, `Abandoned`, hay `Rejected`. `test_confirm_after_flag_in_same_context_is_tool_error`. `test_confirm_on_a_new_context_writes`. `test_no_clash_writes_without_confirm`. `test_unchanged_deadline_does_not_ask`. `test_moved_plan_is_not_compared_with_itself`. `test_deadline_ignores_done_and_undated`. Lịch sử của ca có ghi: mỗi việc đổi từ ngày sang ngày khác đúng một dòng

- [ ] T031 Viết `tests/test_plan_field_tools.py` và thêm ba hàm vào `tests/test_tool_router.py` (phụ thuộc T026, T028). Mỗi hàm một ca. Trong file mới: `test_set_plan_priority_sets`. `test_set_plan_priority_null_clears`. `test_set_plan_priority_leaves_date_and_effort`. `test_set_subtask_effort_sets`. `test_set_subtask_effort_null_clears`. `test_set_subtask_effort_leaves_priority_and_date`. `test_update_subtask_keeps_priority_date_and_effort`. `test_add_subtask_keeps_priority_date_and_effort`. `test_set_subtask_note_keeps_priority_date_and_effort`. `test_reschedule_keeps_priority`. Trong `tests/test_tool_router.py`, qua `execute_tool`, lỗi đầu vào, không gọi kho: `test_update_subtask_rejects_scheduled_on`, `test_update_subtask_rejects_effort`, `test_update_subtask_rejects_priority`

### Đột biến lô 2

- [ ] T032 Trong `src/tools/plan_tools.py`, bỏ nhánh từ chối `confirm` true khi `clash_reported` đã đặt (phụ thuộc T030). `test_confirm_after_flag_in_same_context_is_tool_error` phải đỏ. Hoàn tác. `git diff` của file rỗng. Ghi một dòng kết quả dưới task

- [ ] T033 Trong `src/tools/plan_tools.py`, bỏ nhánh bỏ qua kiểm trùng khi hạn của chính kế hoạch không đổi (phụ thuộc T030). `test_unchanged_deadline_does_not_ask` phải đỏ. Hoàn tác. `git diff` của file rỗng. Ghi một dòng kết quả dưới task

### Điểm dừng lô 2

- [ ] T034 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T016 đến T033). Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T036

- [ ] T035 DỪNG: chat đọc diff lô 2. Không bắt đầu lô 3 trước khi chat nói tiếp

---

## Phase 3: Lô 3 — Đo và docs

**Purpose**: Digest, eval, PRODUCT, ARCHITECTURE. Hai lần chạy eval là tay của Starter. Không tự chạy

**Independent check**: Digest không nhận mốc. Bộ chấm bản 2 trên một ca v1 ra cùng luật với bản 1. Đọc tiêu đề từ object không đổi luật v1. `docs/DECISIONS.md` không có diff từ các task này

- [ ] T036 Sửa `render_digest` trong `src/core/morning.py` (phụ thuộc T035, T016). Vẫn chỉ nhận `tuple[Plan, ...]`. Việc `pending` đầu có `scheduled_on` thì cuối dòng tiêu đề thêm một dấu cách và `(<tên thứ> DD/MM)` từ `weekday_name_vi`. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không thêm. Tiêu đề đã lưu không sửa. Thứ tự `created_order` tăng dần giữ nguyên. Cùng task sửa `specs/014-morning-digest/spec.md` và `specs/014-morning-digest/contracts/digest-text.md`: câu cấm thêm ngày được thay bằng đoạn ngày này. Giữ câu T017: `helsinki_clock` định nghĩa ở `src/core/clock.py`, `core.morning` vẫn export. Không sửa `specs/014-morning-digest/tasks.md`. Trong `tests/test_morning_text.py` thêm năm hàm, không sửa assert của `test_pending_title_keeps_a_stored_date` và `test_oldest_created_order_comes_first`: `test_dated_pending_title_ends_with_friday_suffix` cho ngày `2026-11-06` kết thúc bằng ` (thứ Sáu 06/11)`. `test_sunday_suffix_has_no_thu`. `test_undated_pending_title_has_no_suffix`. `test_title_date_text_stays_verbatim_when_field_empty`. `test_past_date_has_no_overdue_word`

- [ ] T037 DỪNG: chat chốt mô hình kỳ vọng của eval v2 (nhóm, loại kỳ vọng, trường của Expectation, luật tool, tên các file `evals/datasets/` mới, có phải sửa `evals/summary.py` hay `evals/result.py` không). Chưa có chữ chốt thì không bắt đầu task eval nào (phụ thuộc T035)

- [ ] T038 Sửa `evals/model.py` (phụ thuộc T037). Làm đúng chữ chat đã chốt ở T037 cho nhóm, loại kỳ vọng, trường của Expectation và luật tool. Giữ các trường dưới đây nếu chữ chốt không bỏ: `Case.instant: datetime | None = None`. `Case.follow_up: str | None = None`. `SubtaskSeed` thêm `scheduled_on` và `effort`, mặc định `None`. `PlanSeed` thêm `priority`, mặc định `None`

- [ ] T039 Tạo các file seed trong `evals/datasets/` (phụ thuộc T037, T038). Đúng các tên chat đã chốt ở T037, cho seed của ca trùng và seed của ca bảng chữ cái. Trước khi tạo file, thêm đúng các đường dẫn đó vào `specs/015-plan-dates-priority/allowed-files.txt`. Nếu chữ T037 cho sửa `evals/summary.py` hoặc `evals/result.py`, thêm đúng file đó vào allow list rồi sửa theo chữ đã chốt. Không thêm và không sửa file chat không nêu

- [ ] T040 [P] Sửa `evals/load.py` (phụ thuộc T037, T038). Khóa `instant`, `follow_up`, `scheduled_on`, `effort`, `priority` vắng thì `None`. File v1 không phải viết lại

- [ ] T041 [P] Sửa `evals/store.py` (phụ thuộc T037, T038, T039). Seed đưa ngày, sức và ưu tiên vào `Subtask` và `Plan`, và đọc seed ca trùng cùng seed bảng chữ cái từ các file T039. Đồ giả là `MemoryPlanStore` đã có lịch sử từ T006

- [ ] T042 Sửa `evals/turn.py` (phụ thuộc T037, T038, T040, T041, T020). Ca có `instant` thì truyền mốc đó. Ca v1 để trống thì giữ mốc `2026-11-06T08:00:00+02:00`. `follow_up` có chữ: chạy lượt một, chụp kho, chạy lượt hai trên cùng kho. Lịch sử lượt hai là ba tin chữ: tin chủ bot, câu trả lời, tin thứ hai. Không đưa kết quả tool sang lượt hai. `Outcome` một lượt giữ `kind`, `reply`, `lines`, `rounds`, `laws`. Ca hai lượt thêm `earlier: TurnLog | None` và `opening_store`. `TurnLog` có `kind`, `reply`, `lines`, `rounds` của riêng lượt đó. Lượt một lỗi thì không gọi lượt hai, `laws` là `None`. Ca một lượt trong `tests/test_eval_run.py` không sửa assertion

- [ ] T043 Sửa `evals/score.py` (phụ thuộc T037, T042). `SCORER_VERSION` là 2. `cases_version` thiếu hoặc bằng 1 đi đúng hàm chấm bản 1, không đọc ngày, sức, ưu tiên, lịch sử. Ca v2 đọc bốn thứ đó. Ca trùng đọc ảnh kho sau lượt một và kho sau lượt hai. Không lấy cờ làm bằng chứng đồng ý. Luật tool thêm theo chữ T037. `_new_titles` đọc tiêu đề từ object có khóa `title` và vẫn nhận chuỗi của fixture cũ. Cùng hàm cho nhánh v1 và v2. Đây là đổi cách đọc đầu vào vì catalog bản 3 gửi object, không đổi luật chấm của v1. Grep trong `evals/` chỉ thấy `str(item)` trên `subtasks` của `create_plan` ở `_new_titles`. `evals/result.py` gọi `_new_titles`. Không sửa `evals/result.py` hay `evals/summary.py` ở task này. Phần đó thuộc T039 khi T037 cho sửa. Các `subtasks` còn lại trong `evals/` là seed có `.title`, không phải đầu vào tool

- [ ] T044 Sửa `evals/runner.py` (phụ thuộc T037, T042). Nhận đường dẫn bộ câu. Không truyền thì `evals/cases/v1.json`. Thư mục kết quả vẫn `evals/results/`. Không gộp hai bộ vào một lệnh

- [ ] T045 Tạo `evals/cases/v2.json` (phụ thuộc T037, T039, T040). `cases_version` là 2. Mỗi ca có `instant`. Đủ bảy tình huống User Story 8. Tình huống 1 đúng ba ca: "cuối tuần này", tên một thứ vào đúng ngày đó, "tuần sau" không kèm thứ. Không thêm ca thứ tư cho "thứ X tuần sau". Tình huống 2 có `follow_up` và seed một kế hoạch khác với hạn đã biết, lấy từ file seed T039. Tình huống 3 chấm hạn đặt lên việc chưa làm cuối. Tình huống 4 chấm luật goal. Tình huống 5 chấm tiêu đề từng chữ. Tình huống 6 chấm seed Hiragana và Katakana tách riêng, lấy từ file seed T039. Ca một việc gộp và tình huống 7 có mặt để ghi nhận, không có đạt hay trượt

- [ ] T046 Thêm hàm vào `tests/test_eval_score.py` (phụ thuộc T037, T043, T045). Không sửa assert của các hàm cũ. `test_scorer_v2_scores_v1_case_like_v1`: cùng một ca v1, luật của nhánh `cases_version == 1` trùng luật bản 1. `test_two_turn_case_reads_store_between_turns`: ảnh sau lượt một không đổi so với seed, kho sau lượt hai chỉ dịch các việc chưa làm đang mang đúng ngày hạn, mỗi việc một dòng lịch sử. `test_prefix_law_reads_title_on_object`: đầu vào `create_plan` có `subtasks` là `[{"title": "Ngày 1: Hiragana"}]`, luật prefix là fail. `test_prefix_law_still_reads_plain_string`: cùng tiêu đề là chuỗi, luật prefix vẫn fail

- [ ] T047 Thêm hàm, không sửa assert của hàm cũ (phụ thuộc T037, T040, T042, T044, T045). Trong `tests/test_eval_run.py`: `test_follow_up_history_is_three_text_messages` thấy lượt hai chỉ có ba tin chữ, không có khối tool. `test_first_turn_error_does_not_call_second_turn`. Trong `tests/test_eval_runner.py`: `test_runner_defaults_to_v1_cases` và `test_runner_reads_case_path`. Trong `tests/test_eval_load.py`: `test_absent_new_keys_are_none`, `test_reads_instant_follow_up_date_effort_priority`, và `test_v2_file_loads_seven_situations` thấy `cases_version` 2, mỗi ca có `instant`, đủ bảy tình huống. Mỗi tên là một hàm

### Đột biến lô 3

- [ ] T048 Trong `evals/score.py`, nhánh ca v1 đọc thêm ngày đã lưu và tính vào luật (phụ thuộc T037, T046). `test_scorer_v2_scores_v1_case_like_v1` phải đỏ. Hoàn tác. `git diff` của file rỗng. Ghi một dòng kết quả dưới task

- [ ] T049 Trong `evals/score.py`, hàm `_new_titles`, đổi chỗ đọc khóa `title` thành `str(item)` như bản cũ (phụ thuộc T037, T046). `test_prefix_law_reads_title_on_object` phải đỏ. `test_prefix_law_still_reads_plain_string` không phải hàm phải đỏ, vì chuỗi qua `str` vẫn ra chính nó. Hoàn tác. `git diff` của file rỗng. Ghi một dòng kết quả dưới task. Đột biến này chỉ chứng minh cách đọc đầu vào, không đổi luật prefix

### Docs

- [ ] T050 Sửa `docs/PRODUCT.md` (phụ thuộc T036, T043). §3 hàng F17 nêu ngày, ưu tiên kế hoạch, sức, lịch sử dời, và xác nhận khi hạn sau lần dời trùng hạn kế hoạch khác. §9: ngày nằm ở trường ngày. Tiêu đề cũ giữ nguyên. Trùng hạn thì báo và chưa ghi cho đến khi chủ bot đồng ý. Khớp đúng một tên vẫn cập nhật ngay. Không sửa `docs/DECISIONS.md`

- [ ] T051 Sửa `docs/ARCHITECTURE.md` (phụ thuộc T017, T022, T024). Dòng trạng thái đầu file nói `execute_tool` điều phối chín tool. §2 nêu `src/core/clock.py` là nơi định nghĩa `helsinki_clock`, và nêu chín tool, `DEFINITIONS_VERSION` 3, `PROMPT_VERSION` 4, 11 mẫu dòng trong `saved_reply.py`. Không sửa diagram

### Điểm dừng lô 3

- [ ] T052 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T036 đến T051). Ghi mã thoát và cả bảng. Mã khác 0 thì không đưa lệnh eval cho Starter

- [ ] T053 Dừng chờ Starter, không tự chạy (phụ thuộc T037, T052). Ghi lệnh, cần `JARVIS_EVAL_ANTHROPIC_KEY` trong tiến trình và `PYTHONPATH` là `src`. Không ghi khóa vào repo. Chạy bộ v1 trước:

```text
uv run python -m evals.runner evals/cases/v1.json
```

File không hậu tố kỳ vọng `p4-d3-<model>-<ngày>.json` trong `evals/results/`. So tổng token vào với 732.676

- [ ] T054 Dừng chờ Starter, không tự chạy (phụ thuộc T037, T053). Lệnh bộ v2:

```text
uv run python -m evals.runner evals/cases/v2.json
```

Cùng ngày thì file có hậu tố `-2`. Không chạy lệnh này trong Cursor

- [ ] T055 Sau khi Starter đã chạy T053 và T054 (phụ thuộc T054). Thêm đúng đường dẫn hai file kết quả mới trong `evals/results/` vào `specs/015-plan-dates-priority/allowed-files.txt`. Rồi chạy lại `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt`. Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T056

- [ ] T056 DỪNG: chat đọc diff lô 3 và hai file kết quả. Không deploy. Không `db push`

---

## Dependencies & Execution Order

### Phase Dependencies

- Bước chép D-026 đứng trước T001 và không phải task trong file này
- Lô 2 bắt đầu sau T015, khi chat đã đọc migration, `src/db`, `src/core/plans.py` và `tests/fakes/memory_plan_store.py`
- Lô 3 bắt đầu sau T035, khi chat đã đọc diff lô 2
- Task eval bắt đầu sau T037, khi chat đã chốt mô hình kỳ vọng
- T053 và T054 chỉ sau T052 mã 0, và chỉ Starter chạy
- T055 chỉ sau khi hai file kết quả đã có. T056 là task dừng cuối lô 3

### User stories

Lô 1 mở đường cho User Story 2, 3, 4, 5, 6: trường, hạn, lịch sử, dữ liệu cũ còn. Lô 2 làm User Story 1 và 7, cùng tool của User Story 2, 3, 4, 5. Lô 3 làm User Story 8 và đoạn ngày của FR-016. Không có story nào giao độc lập trước lô của nó.

### Trong một lô

- File và chữ ký trước test dùng chúng
- T019 có `turn` trước T020
- T024 có mười một mẫu trước T025
- T025 nhận object trước T026 từ chối mảng chuỗi, và T027 sửa lời gọi ngay sau đó
- T028 nối `_DISPATCH` sau T025, và phụ thuộc T022 cùng T026
- T029 kiểm đầu vào được nhận sau T028
- T037 chốt mô hình eval trước T038 và mọi task eval sau đó
- T039 tạo file seed sau khi T037 đã có tên
- Đột biến sau test, và trước `check.ps1` của lô
- `check.ps1` trước lệnh eval tay
- T015, T035 và T056 là task dừng cuối của từng chặng. T037 là cửa dừng giữa lô 3

### Parallel

- T003 và T004 song song sau T002
- T007 song song với T005 và T006 sau T002
- T040 và T041 song song sau T038 và T039

## Parallel Example: Lô 1

```text
Sau T002:
Task T003 src/db/models.py
Task T004 src/db/client.py
Task T007 tests/test_plan_dates.py
```

## Implementation Strategy

Lô 1 là cửa schema và model core. Chat duyệt trên đĩa trước khi có tool. Lô 2 khóa lời hướng dẫn và catalog bằng test, không gọi mô hình thật. Lô 3 sửa doc sản phẩm và kiến trúc. Hai lần eval đo hồi quy so với p3-d2 và đo bộ v2. Không deploy ở cuối tasks.

## Notes

- Ca "thứ tự đoạn không đổi" của digest là `test_oldest_created_order_comes_first` đã có. Không nhét assert ngày vào hàm đó
- `create_plan` ở Python vẫn nhận `list[str]` bằng cách bọc thành đối tượng chỉ có title. Schema tool và lời gọi qua router là mảng object, đúng contracts/tools.md
- `evals/turn.py` bị T020 đụng để `instant` bắt buộc không làm đỏ suite, rồi T042 đọc mốc của ca và `follow_up`
- `create_plan` gọi `add` với hai tham số vị trí khi ưu tiên trống. Keyword `priority` chỉ khi có ưu tiên. Các lớp ghi đè `add` không sửa
- Tên file trong `evals/datasets/` do chat chốt ở T037. T039 ghi các tên đó vào allow list khi tạo file
- `_new_titles` đổi cách đọc đầu vào. Luật prefix, và mọi luật v1 khác, không đổi
- `tests/test_rpc_returns.py` không sửa
- `docs/DECISIONS.md` không có task sửa
