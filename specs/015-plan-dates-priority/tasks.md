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

- [X] T001 Tạo `supabase/migrations/20261109120000_plan_dates_priority.sql`. Không sửa file migration khác. Trong một transaction: thêm `plans.priority text` null, kiểm chỉ `high`, `medium`, `low` hoặc null. Thêm `subtasks.scheduled_on date` null và `subtasks.effort text` null, kiểm chỉ `S`, `M`, `L` hoặc null. Tạo `subtask_date_moves` với cột `id uuid` khóa chính tự sinh, `plan_id uuid` not null, `subtask_id uuid` not null, `from_date date` not null, `to_date date` not null và khác `from_date`, `reason text` null, `moved_at timestamptz` not null. Không khóa ngoại. Trigger `BEFORE UPDATE OR DELETE` làm `RAISE EXCEPTION`. `drop function` đúng `public.add_plan(text, jsonb)` và `public.replace_plan(uuid, text, jsonb, integer)`, rồi tạo lại. `add_plan(goal text, subtasks jsonb, priority text DEFAULT NULL)` trả object kế hoạch, không void. Object đó có khóa `priority`. Mỗi phần tử `subtasks` trong object có khóa `scheduled_on` và `effort`. Không gửi thì hai khóa việc và `priority` là null. `replace_plan` trả `boolean`, tham số cuối `plan_fields jsonb DEFAULT NULL`, `move_reason text DEFAULT NULL`, `moved_at timestamptz DEFAULT NULL`. `plan_fields` null hoặc không có khóa `priority` thì giữ ưu tiên. Khóa có mặt thì đặt. JSON null là xóa. Trong từng việc, khóa `scheduled_on` hoặc `effort` vắng thì giữ. Khóa có mặt thì đặt. JSON null là xóa. Khóa `note` vắng vẫn thành null. Đổi từ một ngày sang một ngày khác thì `INSERT` một dòng trong cùng hàm. `moved_at` null mà có việc đổi ngày thì `raise` và không ghi kế hoạch. Không gọi `now()`. `revoke` khỏi `public`, `anon`, `authenticated`. `grant execute` cho `service_role` trên đúng chữ ký mới

- [X] T002 Sửa `src/core/plans.py` (phụ thuộc T001 không bắt buộc để viết, nhưng cùng lô). `Priority` là `StrEnum` `high`, `medium`, `low`. `Effort` là `StrEnum` `S`, `M`, `L`. `EFFORT_HOURS` là S = 1, M = 3, L = 6. Không cộng giờ. `Subtask` thêm `scheduled_on: date | None = None` và `effort: Effort | None = None` đứng cuối. `Plan` thêm `priority: Priority | None = None` đứng cuối. `PlanStore.add` thêm `priority` keyword, mặc định `None`. `PlanStore.replace` thêm `move_reason: str | None = None` và `moved_at: datetime | None = None`, keyword. `normalize_new_plan` nhận danh sách đối tượng có tiêu đề, ngày và sức tùy chọn. `_plan_with_subtasks` chép `priority`. Thêm `plan_deadline`, `deadline_clash`, `date_moves` đúng data-model.md. Chuỗi ngày không phải `YYYY-MM-DD`, hoặc mã ưu tiên hay sức lạ, là `PlanDomainError`. Cùng task, trong `tests/test_plan_row_mapping.py` hàm `test_valid_row_becomes_plan`, đổi tập khóa dataclass của việc con thành `id`, `title`, `status`, `note`, `scheduled_on`, `effort`. Trong `tests/test_plan_store_contract.py`, `_written` chép `priority`. Không đổi assertion khác của các hàm cũ

- [X] T003 [P] Sửa `src/db/models.py` (phụ thuộc T002). `PlanRow.priority: str | None = None`. `SubtaskRow.scheduled_on: str | None = None`. `SubtaskRow.effort: str | None = None`. Hàng thiếu khóa vẫn qua Pydantic

- [X] T004 [P] Sửa `src/db/client.py` (phụ thuộc T002). `_PLAN_COLUMNS` thêm `plans.priority`, `subtasks.scheduled_on`, `subtasks.effort`. `add_plan` gửi `priority`, `None` thành JSON null. `replace_plan` gửi `plan_fields`, `move_reason`, `moved_at`. Vẫn không đọc boolean. Lỗi vẫn chỉ `plan_missing` và `plan_version_conflict`

- [X] T005 Sửa `src/db/plan_store.py` (phụ thuộc T003, T004). `plan_from_row` đưa ba trường vào model. Khóa vắng trên dòng đọc là `None`. `add` đưa `priority` xuống client. `replace` luôn gửi `plan_fields` có khóa `priority`, `None` thành JSON null, và luôn gửi khóa `scheduled_on` cùng `effort` của từng việc. Chỉ lời gọi dời ngày truyền `move_reason` và `moved_at`. Cùng task thêm hai hàm trong `tests/test_plan_row_mapping.py`: `test_row_without_new_columns_is_empty` và `test_row_maps_priority_date_and_effort`. Mỗi hàm một ca

- [X] T006 Sửa `tests/fakes/memory_plan_store.py` (phụ thuộc T002). `add` lưu `priority`. `replace` gán ưu tiên từ `Plan`, `None` là xóa, và ghi lịch sử bằng `date_moves` với lý do và mốc được truyền. `moved_at` là `None` mà `date_moves` không rỗng thì ném lỗi và không ghi kế hoạch, không gọi `datetime.now`. Cùng luật với `replace_plan` trong SQL. Danh sách dòng nằm trên instance. Không đếm lịch sử của instance khác

### Test kho

- [X] T007 Viết `tests/test_plan_dates.py` (phụ thuộc T002). Mỗi tên dưới đây là một hàm, không gộp ca. `test_plan_deadline_is_latest_pending_date`. `test_plan_deadline_ignores_done_skipped_and_undated`. `test_plan_deadline_is_none_when_no_pending_date`. `test_deadline_clash_skips_the_same_plan_id`. `test_date_moves_includes_date_to_other_date`. `test_date_moves_excludes_empty_to_date`. `test_date_moves_excludes_date_to_empty`. `test_date_moves_excludes_same_date`. `test_bad_iso_date_is_domain_error`. `test_bad_priority_is_domain_error`. `test_effort_hours_are_one_three_six`

- [X] T008 Thêm vào `tests/test_plan_store_contract.py` các hàm dùng fixture `plan_store` sẵn có, nên mỗi hàm chạy trên `MemoryPlanStore` và trên Supabase local (phụ thuộc T005, T006). Mỗi hàm một ca. Lịch sử chỉ xét `plan_id` và `subtask_id` của lần ghi, không đếm cả bảng. `test_date_to_other_date_writes_one_history_row`. `test_empty_to_date_writes_no_history_row`. `test_date_to_empty_writes_no_history_row`. `test_same_date_writes_no_history_row`. `test_several_date_changes_write_one_row_each`. `test_version_conflict_keeps_dates_and_writes_no_row`. `test_null_moved_at_on_date_change_errors_and_keeps_plan`. `test_dropped_subtask_keeps_its_history`. `test_replace_adds_new_subtask_with_date_and_effort`. `test_replace_adds_new_subtask_without_date_or_effort_keeps_them_empty`. `test_new_subtask_with_date_writes_no_history_row`. `test_add_returns_priority_date_and_effort`: `store.add` trả `Plan` mang đúng ưu tiên, và từng việc mang đúng ngày cùng sức vừa đặt. Trước lần chạy supabase: `npx --yes supabase@2.122.0 db reset` trên kho local, rồi đặt `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ `status -o json`. Host phải là `127.0.0.1` hoặc `localhost`

- [X] T009 Thêm vào `tests/test_supabase_plan_store.py` các lời gọi RPC thô, không đi qua client Python bản mới (phụ thuộc T001, T008). Mỗi hàm một ca. `test_add_plan_two_args_is_not_ambiguous`. `test_replace_plan_four_args_runs`. `test_missing_scheduled_on_keeps_stored_date`. `test_missing_effort_keeps_stored_effort`. `test_missing_plan_fields_keeps_priority`. `test_json_null_clears_scheduled_on`. `test_json_null_clears_effort`. `test_json_null_clears_priority`. `test_missing_note_becomes_null`. `test_add_plan_stores_priority`. `test_clocks_stay_when_status_unchanged` cho FR-010: đổi ngày, sức hoặc ưu tiên không đổi `created_at` và không đổi `status_changed_at`. Đổi `status` vẫn đổi `status_changed_at`. `test_history_trigger_blocks_update`. `test_history_trigger_blocks_delete`. `test_new_subtask_via_replace_plan_keeps_date_and_effort`. `test_new_subtask_without_keys_has_null_date_and_effort`. Không sửa `empty_plan_tables` để xóa lịch sử

- [X] T010 Chạy `uv run pytest tests/test_rpc_returns.py::test_latest_rpc_definitions_are_not_void` (phụ thuộc T001, T004). Không sửa `tests/test_rpc_returns.py`. Đỏ thì sửa migration cho định nghĩa cuối của `add_plan` và `replace_plan` không phải `void`, rồi chạy lại

### Đột biến lô 1

Mỗi đột biến: trước khi sửa, chép file sang thư mục tạm và ghi SHA256. Sửa đúng chỗ, chạy đúng hàm, thấy đỏ, hoàn tác. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task.

- [X] T011 Trong `supabase/migrations/20261109120000_plan_dates_priority.sql`, mọi nhánh "khóa vắng thì giữ" của `replace_plan` đổi thành gán null, gồm `scheduled_on`, `effort` và `priority` (phụ thuộc T009). `test_missing_scheduled_on_keeps_stored_date` phải đỏ. Hoàn tác

  Kết quả: đỏ `assert None == '2026-11-06'`. SHA256 trước `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`. SHA256 sau `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`.

- [X] T012 Trong cùng file migration, bỏ trigger `BEFORE UPDATE OR DELETE` của `subtask_date_moves` (phụ thuộc T009). `test_history_trigger_blocks_delete` phải đỏ. Hoàn tác

  Kết quả: đỏ `Failed: DID NOT RAISE APIError`. SHA256 trước `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`. SHA256 sau `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`.

- [X] T013 Trong cùng file migration, bỏ lệnh `INSERT` vào `subtask_date_moves` (phụ thuộc T008). `test_date_to_other_date_writes_one_history_row` phải đỏ trên Supabase. Hoàn tác

  Kết quả: đỏ trên Supabase `assert 0 == 1`. SHA256 trước `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`. SHA256 sau `d612ffe15e9ac02fe6a9a6fb71f3f369487d3cd9684b3dd2264f6918332b966e`.

- [X] Đột biến thêm, dưới T013, không đổi số task. Trong nhánh việc mới của `scheduled_on`, đổi về `new_on := null`. `test_new_subtask_via_replace_plan_keeps_date_and_effort` phải đỏ. Hoàn tác

  Kết quả: đỏ `assert None == '2026-11-06'`. SHA256 trước `b3c170ac0d683c6723b23c3558f09bf5a5e06636d66a405be3362f870a7da3b1`. SHA256 sau `b3c170ac0d683c6723b23c3558f09bf5a5e06636d66a405be3362f870a7da3b1`.

### Điểm dừng lô 1

- [ ] T014 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T001 đến T013). Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T016

- [ ] T015 DỪNG: chat đọc migration, `src/db`, `src/core/plans.py` và `tests/fakes/memory_plan_store.py` trên đĩa. Không bắt đầu lô 2 trước khi chat nói tiếp

---

## Phase 2: Lô 2 — Hành vi

**Purpose**: Đồng hồ, lượt, ngữ cảnh, chín tool, mười một mẫu, lời hướng dẫn bản 4. Hết lô thì dừng để chat đọc diff

**Independent check**: `run_turn` thiếu `instant` là `TypeError`. Catalog là 3 và chín tên. Sáu tool cũ vẫn gọi được khi không truyền `turn`. Chín tool đều tới handler qua `execute_tool`

- [X] T016 Tạo `src/core/clock.py` (phụ thuộc T015). Đặt `helsinki_clock` và `_helsinki_zone` vào đây. Chưa xóa bản trong `src/core/morning.py`. Thêm `weekday_name_vi(day: date) -> str` với bảy chữ: thứ Hai, thứ Ba, thứ Tư, thứ Năm, thứ Sáu, thứ Bảy, Chủ nhật. Thêm `turn_date_line(instant) -> str`. Mốc không có `tzinfo` thì `ValueError`. Dòng có năm và chữ `Europe/Helsinki`, dạng `Hôm nay là thứ Sáu 06/11/2026, múi giờ Europe/Helsinki.`

- [X] T017 Sửa `src/core/morning.py` (phụ thuộc T016). Xóa `helsinki_clock` và `_helsinki_zone` cục bộ. Import từ `core.clock` và gán lại tên `helsinki_clock` để `from core.morning import helsinki_clock` còn đúng. Chưa sửa `render_digest`. Cùng task sửa câu vị trí hàm trong `specs/014-morning-digest/contracts/digest-text.md`: `helsinki_clock` định nghĩa ở `src/core/clock.py`, `core.morning` vẫn export. Chưa sửa câu cấm thêm ngày. Cùng task sửa `tests/test_morning_clock.py`: `test_import_does_not_need_zone_data` nạp lại `core.clock` dưới `ZoneInfo` giả và xóa cache `core.clock._helsinki_zone`, không còn đọc `morning._helsinki_zone`. Giữ import `helsinki_clock` từ `core.morning` ở đầu file. Thêm hàm `test_helsinki_clock_imports_from_morning` nếu import đó chưa có assert riêng

- [X] T018 Thêm `TurnContext` vào `src/tools/base.py` (phụ thuộc T015). Dataclass không đóng băng. Có `instant: datetime` và `clash_reported: bool = False`. Không import `db`

- [X] T019 Sửa `src/tools/tool_router.py` (phụ thuộc T018). `execute_tool` nhận `turn: TurnContext | None = None` và `_invoke` đưa `turn` vào mọi handler đang có. Sáu handler nhận `turn` và bỏ qua khi chưa dùng. Không thêm tool. Không sửa `_type_error` ở task này. Không thêm khóa log

- [X] T020 Sửa `src/turns/llm_turn.py` (phụ thuộc T016, T018, T019). `run_turn` nhận `instant` keyword, không mặc định. Đầu lượt dựng một `TurnContext` và ghép `turn_date_line` sau hằng `SYSTEM_PROMPT`. Mọi `execute_tool` của lượt nhận cùng đối tượng qua `turn`. Không rẽ theo tên tool và không đọc chữ kết quả. Cùng task sửa lời gọi cho suite không đỏ: `src/api/telegram_update.py` truyền `now`. `evals/turn.py` truyền `2026-11-06T08:00:00+02:00` cho đến khi T042 đọc mốc của ca. `tests/test_llm_turn.py` truyền cùng mốc đó vào mọi `run_turn` đang có. Rồi thêm năm hàm, mỗi hàm một ca: `test_run_turn_without_instant_is_type_error`. `test_turn_date_line_ignores_a_later_clock`: đồng hồ giả nhảy sang ngày hôm sau giữa hai lần gọi mô hình, cả hai request vẫn thấy dòng của mốc đầu. `test_date_line_winter` với `2026-11-06T08:00:00+02:00` ra `thứ Sáu 06/11/2026`. `test_date_line_summer` với `2026-07-01T08:00:00+03:00` ra `thứ Tư 01/07/2026`. `test_sunday_name_is_chu_nhat` với `2026-11-08T08:00:00+02:00` chứa `Chủ nhật` và không chứa `thứ Chủ nhật`

- [X] T021 Sửa `src/core/system_prompt.py` (phụ thuộc T020). `PROMPT_VERSION` là 4. Giữ mọi câu bản 3, gồm luật goal ngắn và câu ví dụ báo cáo thứ Sáu. Thêm luật: ngày vào trường ngày, không vào tiêu đề. Hạn tương đối theo FR-019, gồm "thứ X tuần sau". Khi đã chọn ngày thì nói ngày đó. Trùng thì báo, không ghi, hỏi, chỉ gọi lại với cờ ở lượt sau. Hằng không chứa dòng ngày. Cùng task, trong `tests/test_llm_turn.py`, đổi tên `test_system_prompt_has_seven_laws` thành `test_system_prompt_has_version_four_laws`. Hàm khóa số 4, khóa các câu bản 3 còn nguyên, và khóa các câu luật mới. Không gọi mô hình thật

- [X] T022 Sửa `src/tools/tool_definitions.py` (phụ thuộc T015). `DEFINITIONS_VERSION` là 3. Giữ sáu tool. Thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks` đúng `contracts/tools.md`. Mô tả một dòng: `Đặt hoặc xóa ưu tiên của một kế hoạch.`, `Đặt hoặc xóa sức của một việc con.`, `Dời ngày của các việc trong một kế hoạch.` `create_plan` nhận `priority` tùy chọn và `subtasks` là mảng object, không còn mảng chuỗi. Cùng task sửa `tests/test_tool_router.py`: `test_catalog_matches_contract` khóa số 3, chín tên, và schema object của `create_plan`. Hàm `_run` khóa `definitions_version` bằng hằng `DEFINITIONS_VERSION`, không khóa số 2

- [X] T023 Sửa `src/tools/schemas.py` và `_plan_json` trong `src/tools/plan_tools.py` (phụ thuộc T002, T005). `PlanJson` thêm `priority`, thứ tự khóa `id`, `goal`, `priority`, `subtasks`. `SubtaskJson` thêm `scheduled_on` và `effort`, thứ tự `id`, `title`, `status`, `note`, `scheduled_on`, `effort`. `_plan_json` điền ba trường đó, trống thành null. Cùng task sửa các chỗ đang khóa tập khóa cũ, không để test đỏ rồi vá: `tests/helpers.py` trong `pending_or_done_plan` và `pending_plan`. `tests/test_get_plans.py` trong `_plans`. `tests/test_subtask_skip_note.py` ở hai chỗ so tập khóa kế hoạch và danh sách khóa việc. Giá trị trống là JSON null

- [X] T024 Sửa `src/tools/saved_reply.py` (phụ thuộc T015). Giữ sáu mẫu cũ đúng chữ trong `contracts/saved-lines.md`. Thêm năm mẫu: đặt ưu tiên, bỏ ưu tiên, đặt sức, bỏ sức, dời ngày. Dòng tạo kế hoạch không nêu ngày. Dòng dời ngày một dòng cho cả lần ghi, nhiều tiêu đề nối bằng dấu phẩy, không có ngày cũ, ngày mới, hay lý do. Cùng task sửa `tests/test_saved_reply.py`: docstring còn nói sáu mẫu thì sửa thành mười một. Giữ assert của `test_sentences_and_templates_match_spec`. Thêm năm hàm: `test_saved_set_priority_line`, `test_saved_clear_priority_line`, `test_saved_set_effort_line`, `test_saved_clear_effort_line`, `test_saved_reschedule_line`. `test_fixed_strings_live_only_in_saved_reply` cũng thấy năm chuỗi mới chỉ ở `tools/saved_reply.py`

- [X] T025 Sửa `src/tools/plan_tools.py` (phụ thuộc T005, T006, T019, T023, T024). `create_plan` nhận ưu tiên tùy chọn và việc là đối tượng có `title`, `scheduled_on`, `effort`. Chuỗi tiêu đề vẫn được bọc thành đối tượng chỉ có title, để lời gọi `list[str]` của test cũ không vỡ. Ưu tiên là `None` thì `create_plan` gọi `store.add(goal, subtasks)`, đúng hai tham số vị trí, không có keyword. Chỉ khi có ưu tiên thì gọi `store.add(goal, subtasks, priority=...)`. Không sửa các lớp test ghi đè `add` hay `replace`. Lý do: các lớp đó giữ chữ ký cố định ở `tests/test_llm_turn.py`, `tests/test_store_call_limit.py`, `tests/test_tool_router.py`, `tests/helpers.py`, `tests/test_telegram_route.py` và `tests/test_telegram_update_flow.py`. Chỉ lời gọi dời ngày truyền `move_reason` và `moved_at` cho `replace`. `add_subtask` thêm `scheduled_on` và `effort` keyword, mặc định `None`. Không kiểm trùng ở hai tool này. Không sinh lịch sử. Thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks`. Tool dời ngày không có `turn` thì `ToolError`, không ghi, không gọi `datetime.now`. `moved_at` là `turn.instant`. Trùng và `confirm` không true: thành công, không ghi, `effect` là `None`, đặt `clash_reported`. `confirm` true khi cờ đã đặt: `ToolError`, không ghi. `confirm` true trên ngữ cảnh mới: ghi. Không trùng thì ghi dù không cờ. Hạn sau lần dời không đổi thì không đòi xác nhận. Kế hoạch cùng id không đưa vào phép so. Hạn chỉ tính việc `pending` có ngày. `update_subtask` và `set_subtask_note` không nhận ngày, sức, ưu tiên. Cùng task thêm hàm vào `tests/test_create_plan.py`: `test_create_plan_stores_date_effort_and_priority`. `test_create_plan_without_priority_calls_add_with_two_arguments`: một store ghi lại lời gọi, đúng hai tham số vị trí và không có keyword. `test_create_plan_with_priority_passes_it_to_add`. Thêm hàm vào `tests/test_add_subtask.py`: `test_add_subtask_stores_date_and_effort`. Mỗi hàm một ca. `reschedule_subtasks`: chữ trả cho mô hình khi báo trùng phải nói rõ lần này chưa ghi, nêu mục tiêu của kế hoạch kia và hạn của nó theo ngày `YYYY-MM-DD`, không có mã kế hoạch hay mã việc, và bảo hỏi chủ bot rồi chỉ gọi lại với `confirm` ở lượt sau. Mọi ngày trong `changes` đã bằng ngày đang lưu thì không ghi kho, không có `effect`, cùng mẫu `_replace_subtask_field` chỉ ghi khi plan đổi. `changes` rỗng, hai phần tử cùng `subtask_id`, hoặc `subtask_id` không có trong kế hoạch là `PlanDomainError` và cả lời gọi không ghi gì

- [X] T026 Sửa `_type_error` trong `src/tools/tool_router.py` (phụ thuộc T022, T025). Nhận `boolean`, `null`, mảng object, và `additionalProperties: false` đệ quy trên object lồng. Không đụng chữ ký `turn` đã có từ T019. Không thêm khóa log. Bảy khóa tool và tám khóa mô hình giữ nguyên thứ tự

- [X] T027 Sửa các lời gọi router đang gửi `subtasks` là chuỗi (phụ thuộc T025, T026). Số dòng là file hiện tại, trước khi T022 chèn dòng vào `tests/test_tool_router.py`. Nếu số trượt thì khớp đúng payload. Dòng 156 đổi `["Học hiragana", None]` thành `[{"title": "Học hiragana"}, None]`, câu kỳ vọng vẫn `Một phần tử của trường subtasks sai kiểu.` Dòng 157 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`, câu kỳ vọng vẫn `Đầu vào thiếu trường goal.` Dòng 269 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`. Dòng 322 giữ `[object()]` để log input là null, câu kỳ vọng vẫn `Một phần tử của trường subtasks sai kiểu.` Dòng 435 đổi `("Một",)` thành `({"title": "Một"},)`, câu kỳ vọng vẫn `Trường subtasks sai kiểu.` Dòng 446 giữ `subtasks: None`, câu kỳ vọng vẫn `Trường subtasks sai kiểu.` Dòng 522 và dòng 526 cùng đổi `["Hiragana", "Katakana"]` thành `[{"title": "Hiragana"}, {"title": "Katakana"}]`, kể cả object so với log. Dòng 581 đổi payload cùng kiểu đó. `tests/test_store_call_limit.py` dòng 107 đổi `["Học hiragana"]` thành `[{"title": "Học hiragana"}]`. Không gộp các ca này vào một hàm mới

- [X] T028 Sửa `src/tools/tool_router.py` (phụ thuộc T019, T022, T025, T026). `_DISPATCH` thêm `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks`. `_create` chuyển `priority`, `scheduled_on`, `effort` từ object xuống `create_plan`. `_add` chuyển `scheduled_on` và `effort`. Mọi handler, cũ và mới, nhận `turn`. Cùng task thêm `test_each_of_nine_tools_reaches_its_handler` vào `tests/test_tool_router.py`: gọi từng tool trong chín tool qua `execute_tool` và thấy handler chạy

- [X] T029 Thêm bốn hàm vào `tests/test_tool_router.py` (phụ thuộc T026, T028). Mỗi hàm một ca. `test_boolean_confirm_is_accepted`. `test_null_priority_is_accepted`. `test_array_of_objects_is_accepted`. `test_nested_unknown_key_is_invalid_input`: khóa lạ trong phần tử `changes` hoặc `subtasks` là lỗi đầu vào, không gọi kho

- [X] T030 Viết `tests/test_reschedule_subtasks.py` (phụ thuộc T024, T025, T028). Dùng `MemoryPlanStore`. Mỗi hàm một ca. `test_reschedule_without_turn_context_does_not_write`. `test_clash_without_confirm_does_not_write`: không ghi, đặt cờ, `effect` là `None`, `compose` không nhận chữ trùng vì không có `Saved`, `Abandoned`, hay `Rejected`. `test_confirm_after_flag_in_same_context_is_tool_error`. `test_confirm_on_a_new_context_writes`. `test_no_clash_writes_without_confirm`. `test_unchanged_deadline_does_not_ask`. `test_moved_plan_is_not_compared_with_itself`. `test_deadline_ignores_done_and_undated`. `test_reschedule_with_no_change_does_not_write`. `test_reschedule_empty_changes_is_domain_error`. `test_reschedule_duplicate_subtask_id_is_domain_error`. `test_reschedule_unknown_subtask_id_is_domain_error`. Ca báo trùng kiểm chữ có `chưa ghi` và có mục tiêu kế hoạch kia, và không có mã. Lịch sử của ca có ghi: mỗi việc đổi từ ngày sang ngày khác đúng một dòng

- [X] T031 Viết `tests/test_plan_field_tools.py` và thêm ba hàm vào `tests/test_tool_router.py` (phụ thuộc T026, T028). Mỗi hàm một ca. Trong file mới: `test_set_plan_priority_sets`. `test_set_plan_priority_null_clears`. `test_set_plan_priority_leaves_date_and_effort`. `test_set_subtask_effort_sets`. `test_set_subtask_effort_null_clears`. `test_set_subtask_effort_leaves_priority_and_date`. `test_update_subtask_keeps_priority_date_and_effort`. `test_add_subtask_keeps_priority_date_and_effort`. `test_set_subtask_note_keeps_priority_date_and_effort`. `test_reschedule_keeps_priority`. Trong `tests/test_tool_router.py`, qua `execute_tool`, lỗi đầu vào, không gọi kho: `test_update_subtask_rejects_scheduled_on`, `test_update_subtask_rejects_effort`, `test_update_subtask_rejects_priority`

### Đột biến lô 2

- [X] T032 Trong `src/tools/plan_tools.py`, bỏ nhánh từ chối `confirm` true khi `clash_reported` đã đặt (phụ thuộc T030). `test_confirm_after_flag_in_same_context_is_tool_error` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task
  Kết quả: đỏ `Failed: DID NOT RAISE ToolError`. SHA256 trước `a28b74d6ae0931471a3199346d428384769b30cc719d210a2c2a330153ed06b1`. SHA256 sau `a28b74d6ae0931471a3199346d428384769b30cc719d210a2c2a330153ed06b1`.

- [X] T033 Trong `src/tools/plan_tools.py`, bỏ nhánh bỏ qua kiểm trùng khi hạn của chính kế hoạch không đổi (phụ thuộc T030). `test_unchanged_deadline_does_not_ask` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task
  Kết quả: đỏ `assert 'chưa ghi' not in result.output`. SHA256 trước `a28b74d6ae0931471a3199346d428384769b30cc719d210a2c2a330153ed06b1`. SHA256 sau `a28b74d6ae0931471a3199346d428384769b30cc719d210a2c2a330153ed06b1`.

### Điểm dừng lô 2

- [X] T034 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T016 đến T033). Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T036

  Sửa sau T034, trước lô 3, không đổi số task:
  - Lời hướng dẫn bản 4 thêm ba đoạn sau câu ngày không vào tiêu đề: tham số tool cho ngày, sức, ưu tiên; hạn cả kế hoạch đặt lên việc chưa làm đứng cuối; dời thêm một ngày chỉ dời việc chưa làm đang mang đúng ngày hạn, và đặt hoặc dời ngày dùng `reschedule_subtasks`.
  - Mô tả `create_plan`, `add_subtask`, `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks` đổi đúng chữ trong `contracts/tools.md`. `DEFINITIONS_VERSION` vẫn 3.
  - `turn_date_line` thêm ngày ISO trong ngoặc, dạng `Hôm nay là thứ Sáu 06/11/2026 (2026-11-06), múi giờ Europe/Helsinki.`
  - `normalize_move_reason` trong `src/core/plans.py`, dùng ở `reschedule_subtasks`. Test `test_reschedule_blank_reason_is_stored_as_none` và `test_reschedule_reason_is_trimmed`.
  - Docstring đầu `src/tools/tool_router.py` đổi thành chín tool.

- [X] T035 DỪNG: chat đọc diff lô 2. Không bắt đầu lô 3 trước khi chat nói tiếp

---

## Phase 3: Lô 3 — Đo và docs

**Purpose**: Digest, eval, PRODUCT, ARCHITECTURE. Hai lần chạy eval là tay của Starter. Không tự chạy

**Independent check**: Digest không nhận mốc. Bộ chấm bản 2 trên một ca v1 ra cùng luật với bản 1. Đọc tiêu đề từ object không đổi luật v1. Bộ v2 đúng mười bốn ca của mục 10a. `kind` `observed` không vào tỉ lệ. `docs/DECISIONS.md` không có diff từ các task này

- [X] T036 Sửa `render_digest` trong `src/core/morning.py` (phụ thuộc T035, T016). Vẫn chỉ nhận `tuple[Plan, ...]`. Việc `pending` đầu có `scheduled_on` thì cuối dòng tiêu đề thêm một dấu cách và `(<tên thứ> DD/MM)` từ `weekday_name_vi`. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không thêm. Tiêu đề đã lưu không sửa. Thứ tự `created_order` tăng dần giữ nguyên. Cùng task sửa `specs/014-morning-digest/spec.md` và `specs/014-morning-digest/contracts/digest-text.md`: câu cấm thêm ngày được thay bằng đoạn ngày này. Giữ câu T017: `helsinki_clock` định nghĩa ở `src/core/clock.py`, `core.morning` vẫn export. Không sửa `specs/014-morning-digest/tasks.md`. Trong `tests/test_morning_text.py` thêm năm hàm, không sửa assert của `test_pending_title_keeps_a_stored_date` và `test_oldest_created_order_comes_first`: `test_dated_pending_title_ends_with_friday_suffix` cho ngày `2026-11-06` kết thúc bằng ` (thứ Sáu 06/11)`. `test_sunday_suffix_has_no_thu`. `test_undated_pending_title_has_no_suffix`. `test_title_date_text_stays_verbatim_when_field_empty`. `test_past_date_has_no_overdue_word`

- [X] T037 DỪNG: chat chốt mô hình kỳ vọng của eval v2 (nhóm, loại kỳ vọng, trường của Expectation, luật tool, tên các file `evals/datasets/` mới, có phải sửa `evals/summary.py` hay `evals/result.py` không). Chưa có chữ chốt thì không bắt đầu task eval nào (phụ thuộc T035)
  Chat đã chốt: research.md mục 10a

- [X] T038 Sửa `evals/model.py` (phụ thuộc T037). Đúng research.md mục 10a. Thêm chín nhóm vào `Group`: `hạn tương đối: lưu ngày`, `hạn tương đối: hỏi lại`, `nhóm việc mơ hồ`, `hạn cả kế hoạch`, `dời hạn trùng`, `dời ngày không cần xác nhận`, `tin dài có ngày`, `liệt kê tiêu đề`, `ghi nhận`. `Case.instant: datetime | None = None`. `Case.follow_up: str | None = None`. `SubtaskSeed` thêm `scheduled_on` và `effort`, mặc định `None`. `PlanSeed` thêm `priority`, mặc định `None`. `Expectation` thêm `deadline: str | None = None`, `titles: tuple[str, ...] | None = None`, `other_goal: str | None = None`, `dates: tuple[tuple[str, str], ...] | None = None`, `history_moves: int | None = None`. Không thêm tên luật

- [X] T039 [P] Sửa `evals/load.py` (phụ thuộc T038). `_KIND` mỗi nhóm mới đúng một loại: `create_with_deadline`, `ask_back_no_write`, `ask_back_no_write`, `set_deadline_existing`, `clash_two_turn`, `reschedule_no_confirm`, `long_message_goal`, `verbatim_titles`, `observe`. Khóa `instant`, `follow_up`, `scheduled_on`, `effort`, `priority` vắng thì `None`. File v1 không viết lại. Bộ `cases_version` 2 từ chối ca thiếu `instant`. Từ chối ngày ISO không hợp lệ. Trường bắt buộc: `create_with_deadline` có `deadline`; `set_deadline_existing` có `goal` và `deadline`; `clash_two_turn` có `goal`, `other_goal`, `dates`, `history_moves`, và ca phải có `follow_up` cùng bộ dữ liệu; `reschedule_no_confirm` có `goal`, `dates`, `history_moves`; `verbatim_titles` có `titles`. `ask_back_no_write`, `long_message_goal`, `observe` không trường. `goal`, `other_goal` và mọi tiêu đề trong `dates` phải có trong bộ dữ liệu của ca

- [X] T040 [P] Tạo năm file seed (phụ thuộc T038). Đường dẫn đã có trong `allowed-files.txt`. Nội dung đúng mục Seed của research.md mục 10a, không thêm việc và không thêm ngày: `evals/datasets/trung_han.json`, `evals/datasets/trung_han_san.json`, `evals/datasets/ke_hoach_khong_ngay.json`, `evals/datasets/bang_chu_cai_tach.json`, `evals/datasets/bang_chu_cai_gop.json`

- [X] T041 Sửa `evals/store.py` (phụ thuộc T038, T040). `build_store` đưa `scheduled_on`, `effort`, `priority` vào `Subtask` và `Plan`. Khóa vắng là `None`. Đọc năm file T040. Đồ giả là `MemoryPlanStore` đã có `date_moves` từ T006

- [X] T042 Sửa `evals/turn.py` (phụ thuộc T038, T039, T041, T020). Ca có `instant` thì truyền mốc đó. Ca v1 để trống thì giữ mốc `2026-11-06T08:00:00+02:00`. `follow_up` khác `None`: chạy lượt 1; `kind` thuộc kind lỗi thì dừng và trả kind đó, không gọi lượt 2. Lượt 2 có `user_message` là `follow_up` và history chỉ hai tin chữ: tin chủ bot của lượt 1 và câu trả lời của bot. Không có khối tool. Không đưa `follow_up` vào history. Cùng một kho và cùng mốc `instant` của ca. `Outcome` thêm `earlier` (Outcome của lượt 1), `opening` (ảnh kho lúc mở) và `after_first` (ảnh kho sau lượt 1). Outcome chính là lượt 2. Không thêm `TurnLog`. Không dùng tên `opening_store`. Ca một lượt trong `tests/test_eval_run.py` không sửa assertion. Chỉ lần chạy có `kind` `scored` mới đổi thành `observed` khi nhóm có loại kỳ vọng `observe`. Kind lỗi giữ nguyên là kind lỗi và vẫn tính vào `run_errors`

- [X] T043 Sửa `evals/score.py` (phụ thuộc T042). `SCORER_VERSION` là 2. `cases_version` thiếu hoặc bằng 1 đi đúng hàm chấm bản 1, không đọc ngày, sức, ưu tiên, lịch sử. Không thêm tên luật. `LAW_NAMES` giữ nguyên thứ tự. Luật tool và luật store đúng mục 10a: `READ` là `get_plans` và `get_plan_detail`; ba nhóm tạo kế hoạch có `names` đúng `["create_plan"]` và `create_plan_count` bằng 1; mọi nhóm v2 khác có `create_plan_count` bằng 0; `ask_back_no_write`, `set_deadline_existing`, `reschedule_no_confirm`, `clash_two_turn` theo các ràng buộc tên tool và `confirm` của mục 10a, kể cả tách lượt 1 và lượt 2 của `clash_two_turn`. Ảnh kho là tuple goal, priority và từng việc theo thứ tự, so bằng `==`. Lịch sử đọc `date_moves`. `plan_deadline` dùng cho `create_with_deadline`. Mẫu ngày và mẫu giờ của `long_message_goal` đúng mục 10a. `verbatim_titles` so NFC rồi bỏ khoảng trắng hai đầu. `observe` không chấm. `required`, `prefix`, `markdown`, `self_name` như v1. `markdown` và `self_name` chấm cả hai câu trả lời khi có `earlier`. `_new_titles` đọc khóa `title` và vẫn nhận chuỗi của fixture cũ. Cùng hàm cho nhánh v1 và v2. Đây là đổi cách đọc đầu vào vì catalog bản 3 gửi object, không đổi luật chấm của v1. Không sửa `evals/result.py` hay `evals/summary.py` ở task này

- [X] T044 Sửa `evals/summary.py` (phụ thuộc T037). `kind` `observed` ra khỏi `_scored` và khỏi `run_errors`, nên tỉ lệ của nhóm đó là `None`. `LAW_NAMES` và các khóa `by_case`, `by_rule`, `by_group` không thêm và không đổi thứ tự. Cùng task thêm `test_observed_kind_is_out_of_the_rate` vào `tests/test_eval_result.py`: một lần `kind` là `observed`, `laws` là `None`, không vào mẫu số tỉ lệ và không tăng `run_errors`. Không sửa assert của hàm cũ

- [X] T045 Sửa `evals/runner.py` (phụ thuộc T042). Nhận đường dẫn bộ câu. Không truyền thì `evals/cases/v1.json`. Thư mục kết quả vẫn `evals/results/`. Không gộp hai bộ vào một lệnh

- [X] T046 Tạo `evals/cases/v2.json` (phụ thuộc T039, T040). `cases_version` là 2. Đúng mười bốn ca V2-01 đến V2-14 của mục 10a: id, nhóm, `instant`, câu người dùng, dataset, `follow_up`, và trường kỳ vọng đã liệt kê. V2-07 và V2-14 có `follow_up`. Không thêm ca và không bớt ca

- [X] T047 Sửa `evals/result.py` (phụ thuộc T042, T044). Bắt buộc: file kết quả hôm nay chỉ ghi một `reply` và một `lines` cho mỗi lần chạy, và không có ảnh kho. Mục 10a bắt file kết quả ghi câu trả lời của từng lượt, dòng log của từng lượt, và ảnh kho cuối ca ở dạng JSON. Ca hai lượt lấy lượt 1 từ `earlier`. Không đổi `LAW_NAMES`. Không đổi khóa `by_case`, `by_rule`, `by_group`. Cùng task thêm `test_result_file_stores_both_turns_and_final_store` vào `tests/test_eval_result.py`. Cùng task thêm `test_v1_result_shape_is_unchanged`: khóa và kiểu của một lần chạy v1 (`reply`, `lines`, `laws`, `kind`) giống hệt trước khi sửa `result.py`. Phần lượt hai và ảnh kho chỉ có ở các lần chạy v2. Không sửa assert của hàm cũ

- [X] T048 Thêm hàm vào `tests/test_eval_score.py` (phụ thuộc T043, T046). Không sửa assert của hàm cũ. Giữ bốn hàm: `test_scorer_v2_scores_v1_case_like_v1` chứng minh nhánh `cases_version == 1` trùng luật bản 1. `test_two_turn_case_reads_store_between_turns`: `after_first` bằng `opening`, sau lượt 2 `scheduled_on` khớp `dates` và số dòng lịch sử bằng `history_moves`. `test_prefix_law_reads_title_on_object`: `subtasks` là `[{"title": "Ngày 1: Hiragana"}]`, luật prefix là fail. `test_prefix_law_still_reads_plain_string`: cùng tiêu đề là chuỗi, luật prefix vẫn fail. Tám nhóm được chấm, mỗi nhóm một hàm đạt và một hàm trượt cho luật tool và cho luật store. Khuôn tên `test_<loại>_tool_passes`, `test_<loại>_tool_fails`, `test_<loại>_store_passes`, `test_<loại>_store_fails` với loại `create_with_deadline`, `set_deadline_existing`, `clash_two_turn`, `reschedule_no_confirm`, `long_message_goal`, `verbatim_titles`. Nhóm `hạn tương đối: hỏi lại` dùng `test_ask_back_relative_tool_passes`, `test_ask_back_relative_tool_fails`, `test_ask_back_relative_store_passes`, và `test_ask_back_no_write_fails_when_store_changes` cho luật store trượt khi kho đổi. Nhóm `nhóm việc mơ hồ` dùng `test_ask_back_ambiguous_tool_passes`, `test_ask_back_ambiguous_tool_fails`, `test_ask_back_ambiguous_store_passes`, `test_ask_back_ambiguous_store_fails`. Nhóm `ghi nhận` không có hàm đạt hay trượt. Mỗi tên là một hàm

- [X] T049 Thêm hàm vào `tests/test_eval_load.py` (phụ thuộc T039, T046). Không sửa assert của hàm cũ. `test_absent_new_keys_are_none`. `test_reads_instant_follow_up_date_effort_priority`. `test_v2_file_has_fourteen_cases`: `cases_version` 2, đúng id V2-01 đến V2-14, mỗi ca có `instant`. `test_v2_case_without_instant_is_rejected`. `test_v2_missing_required_field_is_rejected`. `test_v2_unknown_goal_or_title_is_rejected`. `test_v2_instants_have_expected_weekdays`: V2-01 đến V2-05 và V2-06 đến V2-08 có `instant` đúng thứ đã nói trong mục 10a (2026-11-11 là thứ Tư, 2026-11-13 là thứ Sáu). `test_v2_expected_dates_follow_the_rules`: deadline kỳ vọng của V2-01 là Chủ nhật của tuần chứa hôm nay, V2-04 là thứ Hai kế tiếp, V2-05 là thứ Sáu của tuần lịch kế tiếp, tính từ `instant` của chính ca theo FR-019. Mỗi tên là một hàm

- [X] T050 Thêm hàm vào `tests/test_eval_run.py` (phụ thuộc T042). Không sửa assert của hàm cũ. `test_follow_up_history_is_two_text_messages`: history của lượt 2 đúng hai tin chữ, `user_message` là `follow_up`, không có khối tool. `test_first_turn_error_does_not_call_second_turn`. `test_two_turn_outcome_has_earlier_opening_and_after_first`. Mỗi tên là một hàm

- [X] T051 Thêm hàm vào `tests/test_eval_store.py` (phụ thuộc T040, T041). Không sửa assert của hàm cũ. `test_trung_han_loads`, `test_trung_han_san_loads`, `test_ke_hoach_khong_ngay_loads`, `test_bang_chu_cai_tach_loads`, `test_bang_chu_cai_gop_loads`. Mỗi hàm thấy đúng goal, tiêu đề, trạng thái và ngày của mục Seed. Mỗi tên là một hàm

- [X] T052 Thêm hàm vào `tests/test_eval_runner.py` (phụ thuộc T045). Không sửa assert của hàm cũ. `test_runner_defaults_to_v1_cases`. `test_runner_reads_case_path`. Mỗi tên là một hàm

### Đột biến lô 3

- [X] T053 Trong `evals/score.py`, nhánh ca v1 đọc thêm ngày đã lưu và tính vào luật (phụ thuộc T048). `test_scorer_v2_scores_v1_case_like_v1` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task
  SHA256 trước và sau: 90CB15D651092CBEF8860A7337CEACB0561865B0A222531733912D486C2D1092. Test phải đỏ đã đỏ, rồi hoàn tác.

- [X] T054 Trong `evals/score.py`, hàm `_new_titles`, đổi chỗ đọc khóa `title` thành `str(item)` như bản cũ (phụ thuộc T048). `test_prefix_law_reads_title_on_object` phải đỏ. `test_prefix_law_still_reads_plain_string` không phải hàm phải đỏ, vì chuỗi qua `str` vẫn ra chính nó. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task. Đột biến này chỉ chứng minh cách đọc đầu vào, không đổi luật prefix
  SHA256 trước và sau: 90CB15D651092CBEF8860A7337CEACB0561865B0A222531733912D486C2D1092. Test phải đỏ đã đỏ, rồi hoàn tác.

- [X] T055 Trong `evals/score.py`, luật store `ask_back_no_write`, bỏ so ảnh kho (phụ thuộc T048). `test_ask_back_no_write_fails_when_store_changes` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task
  SHA256 trước và sau: 90CB15D651092CBEF8860A7337CEACB0561865B0A222531733912D486C2D1092. Test phải đỏ đã đỏ, rồi hoàn tác.

- [X] T063 Trong `evals/score.py`, hằng `_TIME_MARK`, đổi mẫu về dạng không khoảng trắng `r"\d+(?:giờ|tiếng)|\b\d+h\b"` vẫn `re.IGNORECASE` (phụ thuộc test giờ có khoảng trắng). `test_long_message_goal_store_fails_when_goal_has_spaced_hours` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task
  SHA256 trước và sau: 43853439BF98787BDB381D9E4AB944AC8B1EA03F2912CFEBB0B4E0E86E523507. Test phải đỏ đã đỏ (`assert 'pass' == 'fail'`), rồi hoàn tác.

### Docs

- [X] T056 Sửa `docs/PRODUCT.md` (phụ thuộc T036, T043). §3 hàng F17 nêu ngày, ưu tiên kế hoạch, sức, lịch sử dời, và xác nhận khi hạn sau lần dời trùng hạn kế hoạch khác. §9: ngày nằm ở trường ngày. Tiêu đề cũ giữ nguyên. Trùng hạn thì báo và chưa ghi cho đến khi chủ bot đồng ý. Khớp đúng một tên vẫn cập nhật ngay. Không sửa `docs/DECISIONS.md`

- [X] T057 Sửa `docs/ARCHITECTURE.md` (phụ thuộc T017, T022, T024). Dòng trạng thái đầu file nói `execute_tool` điều phối chín tool. §2 nêu `src/core/clock.py` là nơi định nghĩa `helsinki_clock`, và nêu chín tool, `DEFINITIONS_VERSION` 3, `PROMPT_VERSION` 4, 11 mẫu dòng trong `saved_reply.py`. Không sửa diagram

### Điểm dừng lô 3

- [X] T058 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T036 đến T057). Ghi mã thoát và cả bảng. Mã khác 0 thì không đưa lệnh eval cho Starter
  Kết quả: mã thoát 0. pytest 707 passed, 0 failed, 0 skipped. Changed files pass, 70 files allowed. Mọi hàng import và env pass. Repo review due: 21 src files changed since ed0c20c (threshold 15).

- [X] T059 Dừng chờ Starter, không tự chạy (phụ thuộc T037, T058). Ghi lệnh, cần `JARVIS_EVAL_ANTHROPIC_KEY` trong tiến trình và `PYTHONPATH` là `src`. Không ghi khóa vào repo. Chạy bộ v1 trước:

```text
uv run python -m evals.runner evals/cases/v1.json
```

File không hậu tố kỳ vọng `p4-d3-<model>-<ngày>.json` trong `evals/results/`. So tổng token vào với 732.676

- [X] T060 Dừng chờ Starter, không tự chạy (phụ thuộc T037, T059). Lệnh bộ v2:

```text
uv run python -m evals.runner evals/cases/v2.json
```

Cùng ngày thì file có hậu tố `-2`. Không chạy lệnh này trong Cursor
Starter đã chạy p4-d3, p5-d3, p6-d3, p7-d3; p7-d3 là bản được chọn

- [X] T061 Sau khi Starter đã chạy T059 và T060 (phụ thuộc T060). Thêm đúng đường dẫn hai file kết quả mới trong `evals/results/` vào `specs/015-plan-dates-priority/allowed-files.txt`. Rồi chạy lại `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt`. Ghi mã thoát và cả bảng. Mã khác 0 thì không sang T062
  Kết quả bước đóng: mã thoát 0. pytest 748 passed, 0 failed, 0 skipped. Changed files pass, 78 files allowed. Mọi hàng import và env pass. Repo review due: 21 src files changed since ed0c20c (threshold 15).

- [X] T062 DỪNG: chat đọc diff lô 3 và hai file kết quả. Không deploy. Không `db push`

### Vòng sửa sau lần đo p4-d3

- [X] T064 Sửa `evals/score.py`, nhánh v2 (phụ thuộc lần đo p4-d3). `_DATE_MARK` không dùng cờ `IGNORECASE` toàn cục. Tên thứ viết thường chỉ khớp sau vào, trước, đến, hết, hạn hoặc sau. Thứ viết hoa vẫn là mẫu ngày. Số thứ tự như "thứ hai" không phải mẫu ngày. Sửa `test_long_message_goal_store_fails_when_title_has_lowercase_weekday` thành tiêu đề "Nộp bài vào thứ sáu". Thêm `test_long_message_goal_store_passes_when_title_has_ordinal_thu_hai`, `test_long_message_goal_store_passes_when_title_has_ordinal_thu_ba`, `test_long_message_goal_store_fails_when_title_has_capitalized_weekday`. Giữ test chủ nhật viết thường

- [X] T065 Thêm ba nhóm và ba loại kỳ vọng (phụ thuộc T064). `ưu tiên do người dùng nêu` -> `create_with_priority`. `đặt ưu tiên` -> `set_priority_existing`. `đặt sức` -> `set_effort_existing`. `Expectation` thêm `priority` và `effort`. Các nhóm tạo kế hoạch của v2 chỉ đạt luật store khi priority trống và mọi effort trống, trừ `create_with_priority` thì priority bằng giá trị kỳ vọng và mọi effort vẫn trống. Luật tool: `create_with_priority` cùng luật tạo; `set_priority_existing` và `set_effort_existing` là tập con của READ cộng tool tương ứng, có ít nhất một lần gọi tool đó. Ba ca V2-15, V2-16, V2-17 trong `evals/cases/v2.json`. Test đạt và trượt cho tool và store của từng nhóm mới. Test loader. Test file v2 có mười bảy ca. Test luật không tự đặt ưu tiên hay sức trên từng nhóm tạo

- [X] T066 Sửa `src/core/system_prompt.py` (phụ thuộc T065). `PROMPT_VERSION` là 5. Thay các đoạn từ câu ngày không vào tiêu đề tới hết bằng bảy đoạn đã chốt. Hằng không chứa `Europe/Helsinki` và `Hôm nay là thứ`. Đổi `test_system_prompt_has_version_four_laws` thành `test_system_prompt_has_version_five_laws`

- [X] T067 Sửa `turn_date_line` trong `src/core/clock.py` (phụ thuộc T066). Trả ba dòng: hôm nay, tuần này, tuần sau. Sửa `contracts/turn-date.md` và test dòng ngày. Thêm `test_turn_date_block_lists_both_weeks`, `test_turn_date_block_on_sunday`, `test_turn_date_block_across_year_end`

- [X] T068 Sửa mô tả `create_plan` và `add_subtask` trong `src/tools/tool_definitions.py` (phụ thuộc T066). Chỉ đặt priority hoặc effort khi người dùng nói rõ. Sửa `test_catalog_matches_contract` và `contracts/tools.md`. Bốn mô tả còn lại giữ nguyên

- [X] T069 Trong `evals/score.py`, đổi `_DATE_MARK` về dạng `IGNORECASE` toàn cục (phụ thuộc T064). `test_long_message_goal_store_passes_when_title_has_ordinal_thu_hai` phải đỏ. Hoàn tác. Trước khi sửa, chép file sang thư mục tạm và ghi SHA256. SHA256 sau khi hoàn tác phải bằng bản chép
  SHA256 trước và sau: A3E0B880934B03F328C5E2874C7735AE786E91C2298FD9337B6D8D359B6E535A. Test phải đỏ đã đỏ (`assert 'fail' == 'pass'`), rồi hoàn tác.

- [X] T070 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T064 đến T069). Ghi mã thoát và cả bảng. Không chạy eval. T059 đến T062 vẫn mở
  Kết quả: mã thoát 0. pytest 741 passed, 0 failed, 0 skipped. Changed files pass, 72 files allowed. Mọi hàng import và env pass. Repo review due: 21 src files changed since ed0c20c (threshold 15).

- [X] T071 Thêm khóa `description` vào thuộc tính catalog trong `src/tools/tool_definitions.py` (phụ thuộc bước 0). Router bỏ qua khóa này. Không đổi kiểu hay `required`. Đúng các chữ: `create_plan.subtasks` "Mảng các đối tượng. Mỗi đối tượng có title; scheduled_on và effort không bắt buộc."; `create_plan.priority` "high, medium hoặc low. Chỉ đặt khi người dùng nói rõ."; `scheduled_on` trong phần tử `create_plan.subtasks`, `add_subtask` và `changes` của `reschedule_subtasks` "Ngày YYYY-MM-DD, hoặc null."; `effort` của `create_plan.subtasks`, `add_subtask` và `set_subtask_effort` "S, M hoặc L. Chỉ đặt khi người dùng nói rõ."; `set_plan_priority.priority` "high, medium hoặc low, hoặc null để xóa."; `reschedule_subtasks.confirm` "true chỉ khi chủ bot vừa đồng ý tiếp tục dời sau khi bạn báo trùng hạn. Mặc định false." Sửa `test_catalog_matches_contract` cho khớp. `contracts/tools.md` ghi cùng các chữ đó

- [X] T072 Trong `src/tools/tool_router.py`, trước `_invalid_input`, chuyển tham số (phụ thuộc T071). Với mỗi thuộc tính cấp cao nhất có `type` là `array`, nếu giá trị là chuỗi (bỏ khoảng trắng hai đầu) bắt đầu bằng "[" và `json.loads` ra list thì thay bằng list đó. Chuỗi khác, JSON hỏng, hay JSON không phải list thì để nguyên. Handler và dòng log nhận input đã chuyển. Sáu test, mỗi ca một hàm: `test_stringified_subtasks_array_is_accepted`, `test_stringified_changes_array_is_accepted`, `test_stringified_array_with_bad_json_is_invalid_input`, `test_stringified_non_array_json_is_invalid_input`, `test_plain_string_subtasks_is_still_invalid_input`, `test_real_array_is_unchanged`

- [X] T073 Trong `src/tools/tool_router.py`, bỏ lời gọi bước chuyển (phụ thuộc T072). `test_stringified_subtasks_array_is_accepted` phải đỏ. Hoàn tác bằng sửa đúng dòng, không chép file tạm đè. SHA256 trước và sau phải bằng nhau
  SHA256 trước và sau: F1C9513009600E83A41AC830D794BBD931FEA9FE8569DC5DE2D5B0EFB53F4A43. Test phải đỏ đã đỏ (`assert False is True`, output `Trường subtasks sai kiểu.`), rồi hoàn tác.

- [X] T074 `PROMPT_VERSION` lên 6 trong `src/core/system_prompt.py` (phụ thuộc bước 0). Giữ mọi câu bản 3 và bản 5. Thêm "Goal không chứa bất kỳ ngày nào, kể cả ngày thi hay ngày nộp." ngay sau câu ngày của việc con. Cuối đoạn ngày, sức và ưu tiên thêm "Số giờ mỗi ngày người dùng nói không phải sức của từng việc: không đặt effort từ đó." Thay đoạn hạn cả kế hoạch bằng câu việc cuối có `scheduled_on` đúng ngày hạn, ví dụ 2026-11-16, và không hỏi xác nhận trước khi dời kế hoạch đã có. Cuối đoạn hạn tương đối thêm hai trường hợp hỏi lại là ngoại lệ duy nhất, kèm ví dụ thứ Sáu là hôm nay. Cuối đoạn trùng hạn thêm ví dụ "ừ, cứ dời đi" với `confirm` true. Hằng không chứa "Europe/Helsinki" và "Hôm nay là thứ". Đổi `test_system_prompt_has_version_five_laws` thành `test_system_prompt_has_version_six_laws`, `PROMPT_VERSION == 6`, và assert từng câu mới

- [X] T075 Sửa mọi chỗ trong `tests/` kiểm `DEFINITIONS` hay prompt cho khớp bản 6 (phụ thuộc T071 và T074). Không sửa `evals/`

- [X] T076 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T071 đến T075). Ghi mã thoát và cả bảng. Không chạy eval. T059 đến T062 vẫn mở
  Kết quả: mã thoát 0. pytest 747 passed, 0 failed, 0 skipped. Changed files pass, 74 files allowed. Mọi hàng import và env pass. Repo review due: 21 src files changed since ed0c20c (threshold 15).

- [X] T077 `PROMPT_VERSION` lên 7 trong `src/core/system_prompt.py` (phụ thuộc bước 0). Giữ mọi câu khác. Cuối đoạn ngày, sức và ưu tiên thêm "Phỏng vấn, kỳ thi hay hạn gần không phải lý do để đặt priority." Trong đoạn hạn tương đối, thay câu "Tuần sau" hỏi lại bằng "Tuần sau" không kèm thứ là Chủ nhật của tuần sau, lưu ngày đó và nói ngày đã chọn, và đổi "Hai trường hợp hỏi lại" thành "Trường hợp hỏi lại". Giữ ví dụ "xong trước thứ Sáu". Hằng không chứa "Europe/Helsinki" và "Hôm nay là thứ". Đổi `test_system_prompt_has_version_six_laws` thành `test_system_prompt_has_version_seven_laws`, `PROMPT_VERSION == 7`, assert hai câu mới, và assert câu cũ "Tuần sau" hỏi lại không còn

- [X] T078 Sửa `evals/cases/v2.json` (phụ thuộc bước 0). V2-03 sang nhóm "hạn tương đối: lưu ngày", kind `create_with_deadline`, deadline 2026-11-22, câu người dùng giữ nguyên. V2-04 đổi câu thành "Lập kế hoạch giúp mình ôn thi giải tích, hạn là thứ Hai." Giữ mười bảy ca và thứ tự. `test_v2_relative_deadline_groups`: nhóm hỏi lại chỉ có V2-02, nhóm lưu ngày có V2-01, V2-03, V2-04, V2-05. `test_v2_expected_dates_follow_the_rules` kiểm deadline V2-03 là Chủ nhật của tuần lịch kế tiếp tính từ instant của ca

- [X] T079 Chạy `.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt` (phụ thuộc T077 và T078). Ghi mã thoát và cả bảng. Không chạy eval. T059 đến T062 vẫn mở
  Kết quả: mã thoát 0. pytest 748 passed, 0 failed, 0 skipped. Changed files pass, 76 files allowed. Mọi hàng import và env pass. Repo review due: 21 src files changed since ed0c20c (threshold 15).

---

## Dependencies & Execution Order

### Phase Dependencies

- Bước chép D-026 đứng trước T001 và không phải task trong file này
- Lô 2 bắt đầu sau T015, khi chat đã đọc migration, `src/db`, `src/core/plans.py` và `tests/fakes/memory_plan_store.py`
- Lô 3 bắt đầu sau T035, khi chat đã đọc diff lô 2
- Task eval bắt đầu sau T037, khi chat đã chốt mô hình kỳ vọng ở research.md mục 10a
- T059 và T060 chỉ sau T058 mã 0, và chỉ Starter chạy
- T061 chỉ sau khi hai file kết quả đã có. T062 là task dừng cuối lô 3

### User stories

Lô 1 mở đường cho User Story 2, 3, 4, 5, 6: trường, hạn, lịch sử, dữ liệu cũ còn. Lô 2 làm User Story 1 và 7, cùng tool của User Story 2, 3, 4, 5. Lô 3 làm User Story 8 và đoạn ngày của FR-016. Không có story nào giao độc lập trước lô của nó.

### Trong một lô

- File và chữ ký trước test dùng chúng
- T019 có `turn` trước T020
- T024 có mười một mẫu trước T025
- T025 nhận object trước T026 từ chối mảng chuỗi, và T027 sửa lời gọi ngay sau đó
- T028 nối `_DISPATCH` sau T025, và phụ thuộc T022 cùng T026
- T029 kiểm đầu vào được nhận sau T028
- T037 đã chốt mô hình eval. T038 và mọi task eval sau đó làm đúng mục 10a
- T039 và T040 song song sau T038. T041 đọc seed sau T040
- T042 đọc mốc và `follow_up` trước T043, T045, T047, T050
- T046 có mười bốn ca trước T048 và T049
- Đột biến T053, T054, T055 sau test T048, và trước `check.ps1` của lô
- T063 sau mẫu giờ có khoảng trắng, và trước lệnh eval tay
- T064 đến T069 là vòng sửa sau p4-d3. T070 là check trước lệnh eval tay. T071 đến T075 là vòng sửa sau p5-d3. T076 là check trước lệnh eval tay. T077 và T078 là vòng cuối chữ, bản 7. T079 là check trước lệnh eval tay. T059 đến T062 đã xong sau p7-d3
- `check.ps1` trước lệnh eval tay
- T015, T035 và T062 là task dừng cuối của từng chặng. T037 đã chốt

### Parallel

- T003 và T004 song song sau T002
- T007 song song với T005 và T006 sau T002
- T039 và T040 song song sau T038

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
- `evals/turn.py` bị T020 đụng để `instant` bắt buộc không làm đỏ suite, rồi T042 đọc mốc của ca và `follow_up`. History lượt 2 là hai tin chữ, đúng mục 10a
- `create_plan` gọi `add` với hai tham số vị trí khi ưu tiên trống. Keyword `priority` chỉ khi có ưu tiên. Các lớp ghi đè `add` không sửa
- Năm tên file trong `evals/datasets/` đã chốt ở mục 10a và đã nằm trong allow list. T040 tạo đúng năm file đó
- `_new_titles` đổi cách đọc đầu vào. Luật prefix, và mọi luật v1 khác, không đổi
- T047 sửa `evals/result.py` vì file kết quả phải ghi từng lượt và ảnh kho cuối ca. Cấu trúc `by_case`, `by_rule`, `by_group` không đổi
- `tests/test_rpc_returns.py` không sửa
- `docs/DECISIONS.md` không có task sửa
