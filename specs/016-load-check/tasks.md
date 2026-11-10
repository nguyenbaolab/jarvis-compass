---
description: "Task list for Quét tải"
---

# Tasks: Quét tải

**Input**: Design documents from `/specs/016-load-check/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Chữ ký hoặc file phải có trước task test dùng nó. Mỗi ca là một hàm. Không gộp assert của nhiều ca vào một hàm.

**Organization**: Ba lô theo thứ tự plan.md, không phải một phase mỗi user story. Story nào nằm ở lô nào ghi ở mục Dependencies. Không gắn nhãn story. Lô là thứ tự bắt buộc.

## Format: `[ID] [P?] Description`

- **[P]**: File khác nhau, không phụ thuộc task chưa xong trong cùng lô
- Không gắn nhãn story
- Mỗi task một việc, có đường dẫn file

## Path Conventions

- File được sửa hoặc tạo chỉ là các dòng trong `specs/016-load-check/allowed-files.txt`
- Không thêm gói. Không sửa `pyproject.toml`, `uv.lock`, `pylock.toml`
- Không sửa migration. Không sửa `src/db/client.py`, `src/db/models.py`, `src/db/plan_store.py`
- Không sửa `docs/DECISIONS.md` trong lô 3. Không sửa diagram `docs/architecture/`
- Không sửa `.specify/memory/constitution.md`. Không đọc, không ghi `.env` và `.dev.vars`
- Không `db push`, không deploy, không `pywrangler`
- Không `db reset`. Vòng này không có migration

## Phase 1: Lô 1 — Hàm thuần

**Purpose**: `day_budget`, giờ, tải, thứ tự dời và ngày đích trong `src/core/plans.py`. Hết lô thì dừng để chat đọc diff

**Independent check**: `uv run pytest tests/test_load_check.py` xanh. Không gọi kho.

- [X] T001 DỪNG: chưa có chữ D-029 do chat viết thì không sửa `src/` và không sửa `docs/DECISIONS.md`. Chat viết mục đó theo sáu điểm ở `research.md` mục 6. Cursor không tự viết. Khi chat đã đưa chữ, Cursor chép đúng chữ đó vào `docs/DECISIONS.md`, rồi mới được T002

- [X] T002 Sửa `src/core/plans.py` (phụ thuộc T001). Không thêm trường hay kiểu của `Plan` và `Subtask`. Thêm hàm thuần, chỉ thư viện chuẩn. `day_budget(day) -> int` trả 8 với mọi ngày. `task_hours`: việc chưa làm S = 1, M = 3, L = 6, không sức = 3. Việc đã xong và bỏ qua = 0. `day_load(plans, day, today)`: ngày trước `today` có tổng 0 và số việc tính tạm 0. Hôm nay và ngày sau cộng mọi việc chưa làm mang đúng ngày đó, mọi kế hoạch. Hàm chọn việc dời theo `data-model.md`: ứng viên chỉ là việc chưa làm đã có trên ngày vượt từ trước lần ghi. Việc vừa đặt không phải ứng viên và vẫn nằm trong tổng. Thứ tự thấp, rồi trống cùng vừa, rồi cao. Giá trị ưu tiên đã lưu không đổi. Cùng mức thì hạn muộn hơn trước. Cùng hạn thì `created_order` nhỏ hơn đứng trước. Cùng kế hoạch thì việc đứng sau trong `subtasks` đứng trước. Số giờ không đổi thứ tự. Đoạn đề xuất là đoạn đầu ngắn nhất để tổng còn lại không còn lớn hơn quỹ. Không tách giờ của một việc. Ngày đích là ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau ngày vượt. Hết bảy ngày thì việc ở lại ngày gốc và không vào danh sách. Không tìm ngày thứ tám. Core không đọc đồng hồ và không import `tools` hay `db`

- [X] T003 Tạo `tests/test_load_check.py` (phụ thuộc T002). Mỗi tên dưới đây là một hàm. `test_day_budget_is_eight_for_every_date`. `test_task_hours_are_one_three_six_and_missing_is_three`. `test_done_and_skipped_add_zero`. `test_past_day_load_is_zero`. `test_today_load_counts`. `test_equal_budget_is_not_overload`. `test_move_order_low_then_empty_with_medium_then_high`. `test_same_plan_later_stored_order_moves_first`. `test_destination_is_nearest_day_within_seven`. `test_no_room_in_seven_days_stays`. `test_newly_placed_task_is_not_a_candidate`. `test_same_level_later_plan_deadline_moves_first`. `test_same_level_and_deadline_earlier_created_plan_moves_first`. `test_empty_priority_stays_empty_after_ordering`. `test_earlier_proposed_moves_count_toward_destination`. `test_no_prefix_clears_the_day_proposes_nothing`. `test_reserved_hours_count_toward_destination`. Không gọi kho

### Đột biến lô 1

Chép file sang thư mục tạm và ghi SHA256. Sửa đúng một chỗ, chạy đúng hàm, thấy đỏ, hoàn tác. SHA256 sau khi hoàn tác phải bằng bản chép. Ghi SHA256 trước và sau vào dòng kết quả dưới task.

- [X] T004 Trong `src/core/plans.py`, `day_budget` trả 7 (phụ thuộc T003). `test_day_budget_is_eight_for_every_date` phải đỏ. Hoàn tác

  Kết quả: đỏ `assert 7 == 8`. SHA256 trước F7DA78F8CCB589B82695D4F6C76E3CB2CC74A6C04534B35D26EB222035788572. SHA256 sau F7DA78F8CCB589B82695D4F6C76E3CB2CC74A6C04534B35D26EB222035788572.

- [X] T005 DỪNG: chat đọc diff `src/core/plans.py` và `tests/test_load_check.py`. Không bắt đầu lô 2 trước khi chat nói tiếp

## Phase 2: Lô 2 — Ba tool và hai bản số

**Purpose**: `create_plan`, `add_subtask`, `reschedule_subtasks`, router, catalog bản 4, lời hướng dẫn bản 8, câu cảnh báo khớp `contracts/load-warning.md`. Hết lô thì dừng để chat đọc diff

**Independent check**: Lần gọi đầu khi vượt không ghi. Câu tool khớp contract. Hai ca cùng một kế hoạch xanh trên cả bộ nhớ và Supabase local khi fixture chạy.

- [X] T006 Tạo `tests/test_load_tools.py` (phụ thuộc T005). Dùng `MemoryPlanStore`, không Supabase. Mỗi tên một hàm. `test_overload_first_call_does_not_write`. `test_overload_sentence_matches_contract` khóa đúng câu mẫu trong `contracts/load-warning.md`, gồm `06/11` khi ngày là 6 tháng 11. `test_same_turn_confirm_does_not_write` và câu lỗi vẫn là câu `_CONFIRM_SAME_TURN` đang có. `test_past_only_write_is_saved`. `test_empty_move_list_invents_no_task`. `test_many_days_open_once`. `test_many_days_do_not_share_one_destination`. `test_confirmed_write_runs_request_then_moves_in_list_order`. `test_reschedule_to_the_same_date_on_a_full_day_does_not_warn`. `test_moves_stop_at_first_error_and_report_done_and_not_done` (dùng một lớp bọc kho định nghĩa ngay trong file test, ném lỗi ở lần replace thứ hai, không sửa tests/fakes; phần đã ghi còn nguyên; câu báo khớp contracts/load-warning.md). `test_confirmed_write_does_not_warn_the_same_day_again`. `test_reschedule_over_and_clash_reports_load_then_clash_in_one_result`. `test_load_moves_skip_clash_check`. `test_create_and_add_skip_clash_check`. `test_write_on_today_runs_the_check`. `test_load_move_on_missing_or_done_task_writes_nothing`. `test_owner_removing_a_task_from_the_list_keeps_its_date` (load_moves thiếu một việc so với danh sách đề xuất, việc đó không đổi ngày và không có dòng lịch sử). Ca này được phép đỏ cho đến T007 và T008

- [X] T007 Sửa `src/tools/plan_tools.py` (phụ thuộc T006). Ba tool gọi hàm thuần của T002. `today` là ngày lịch Helsinki của `turn.instant`. Tool dựng câu, không để core dựng câu. `create_plan` và `add_subtask` nhận `confirm: bool = False`, `load_moves` không bắt buộc, và `turn`. `reschedule_subtasks` giữ `confirm` và nhận `load_moves`. `changes` vẫn là lần chủ bot xin. Không `confirm` thì bỏ qua `load_moves`, tính lại, và không ghi khi vượt. `confirm` true ở lượt sau ghi lần đang xin trước, rồi đúng các phần tử `load_moves` theo thứ tự mảng. Code không thêm phần tử. Cùng lượt, cả cảnh báo tải và trùng hạn đều đặt `turn.clash_reported`. Không thêm cờ. Không có `turn` thì không xét tải và lần ghi đi đường cũ. Router luôn truyền `turn`; trường hợp này chỉ có khi gọi trực tiếp, trong test hoặc eval. `reschedule_subtasks` vẫn lỗi khi không có `turn` như trước. Không ngày cần xét thì `turn` trống vẫn ghi. `create_plan` và `add_subtask` không kiểm trùng hạn. Việc trong `load_moves` không kiểm trùng hạn. Vừa vượt vừa trùng: câu tải trước, câu trùng sau, một lần `Lần này chưa ghi.` Ngày trong câu trùng hạn giữ ISO của `_clash_text`. Lần chỉ trùng hạn giữ nguyên câu `_clash_text`. Mỗi lần `replace` của cùng một kế hoạch dựng từ bản trong bộ nhớ đã áp mọi lần ghi trước trong lần gọi này, gồm các việc và `version`, không chỉ `version`. `version` cộng 1 sau mỗi lần thành công. Không dùng bản gốc của `list_plans` cho lần `replace` thứ hai trở đi. Không đọc lại kho giữa hai lần ghi. `PlanStore.replace` vẫn trả `None`. Một lần xét tải là một `list_newest_first`. Ngày đã qua không gọi thêm list. Lần lỗi giữa chừng dùng câu `Đã ghi lần đang xin` trong contract. Trước lần ghi đầu của lượt xác nhận, kiểm mọi phần tử load_moves với danh sách vừa đọc: kế hoạch phải còn, việc phải còn và còn chưa làm. Sai thì lỗi tool và không ghi gì. Xung đột version chỉ xảy ra khi một kế hoạch đổi giữa lần đọc list_plans và lần replace trong cùng lần gọi.

- [X] T008 Sửa `src/tools/tool_router.py` (phụ thuộc T007). `_create` và `_add` thôi bỏ `turn`. Truyền `turn`, `confirm` và `load_moves` khi khóa có trong input

- [X] T009 [P] Sửa `src/tools/tool_definitions.py` (phụ thuộc T005). `DEFINITIONS_VERSION` là 4. Vẫn chín tool. `create_plan` và `add_subtask` thêm `confirm` và `load_moves` đúng `contracts/tools.md`. `reschedule_subtasks` thêm `load_moves`. `additionalProperties` vẫn false. Cùng task sửa `tests/test_tool_router.py`: khóa số 4 thay cho số 3, và schema mới của ba tool

- [X] T010 [P] Sửa `src/core/system_prompt.py` (phụ thuộc T005). `PROMPT_VERSION` là 8. Giữ mọi câu bản 7. Thêm một đoạn: không cộng giờ và không tự chọn việc dời. Nói lại nguyên câu tool trả. Hỏi chủ bot. `confirm` true chỉ ở lượt sau. Một cờ đó bao cả tải và trùng hạn khi cùng một câu tool đã nêu cả hai. Gửi lại `load_moves` đúng danh sách chủ bot đã chốt, không thêm việc. Hằng không chứa ngày. Cùng task, trong `tests/test_llm_turn.py`, đổi `test_system_prompt_has_version_seven_laws` thành `test_system_prompt_has_version_eight_laws`. Khóa số 8 và khóa đoạn mới. Không gọi mô hình thật

- [X] T011 Thêm hai hàm vào `tests/test_plan_store_contract.py` (phụ thuộc T007, T008). Fixture `plan_store` đã chạy mỗi ca trên bộ nhớ và trên Supabase local, nên hai ca này dùng fixture đó, không viết kho thứ hai. Gọi tool, không gọi `replace` bằng tay với bản đã sửa sẵn. `test_two_moves_on_one_plan_keep_both_destinations`: hai phần tử `load_moves` cùng một kế hoạch. Kết quả có đúng ngày đích của cả hai và đúng hai dòng lịch sử. `test_owner_add_and_one_move_on_the_same_plan`: lần xin của chủ bot và một việc dời cùng kế hoạch. Việc vừa thêm còn, đúng ngày. Dòng lịch sử của việc vừa thêm là 0. Dòng lịch sử của việc dời là 1. Lịch sử đọc bằng `_history` đang có

### Đột biến lô 2

Cùng cách T004. Hai chỗ, hai file lần lượt.

- [X] T012 Trong `src/tools/plan_tools.py`, lần gọi đầu vẫn ghi khi vượt (phụ thuộc T006, T007). `test_overload_first_call_does_not_write` phải đỏ. Hoàn tác

  Kết quả: đỏ `assert 'Lần này chưa ghi.' in result.output`. SHA256 trước 72731F13A1AF8BD97D372018A6590BEE316FD74D5ED8218FA7F136A32C68812E. SHA256 sau 72731F13A1AF8BD97D372018A6590BEE316FD74D5ED8218FA7F136A32C68812E.

- [X] T013 Trong `src/tools/plan_tools.py`, lần `replace` thứ hai của cùng kế hoạch dựng từ bản gốc của `list_plans` (phụ thuộc T011). `test_two_moves_on_one_plan_keep_both_destinations` phải đỏ. Hoàn tác

  Kết quả: đỏ `assert (datetime.date(2026, 11, 8), datetime.date(2026, 11, 8), 2, 0) == (datetime.date(2026, 11, 9), datetime.date(2026, 11, 10), 1, 1)`. SHA256 trước 348B177509E8BCFCB47B056F71974178C0B6EE5AF9E8E65F73AD3E84A2AF6554. SHA256 sau 348B177509E8BCFCB47B056F71974178C0B6EE5AF9E8E65F73AD3E84A2AF6554.

- [ ] T014 DỪNG: chat đọc diff `src/tools/plan_tools.py`, `src/tools/tool_router.py`, `src/tools/tool_definitions.py`, `src/core/system_prompt.py`, `tests/test_load_tools.py` và `tests/test_plan_store_contract.py`. Không bắt đầu lô 3 trước khi chat nói tiếp

## Phase 3: Lô 3 — Đo và docs

**Purpose**: Bộ eval v3 tám ca, chạy lại bộ v1 và bộ v2, hàng F20, kiến trúc. Ba lần chạy eval là của Starter. Không sửa `docs/DECISIONS.md`

**Independent check**: Pytest của scorer: nhánh v1 và v2 không đổi luật. Ca từ chối trượt khi kho đổi. `docs/PRODUCT.md` có hàng F20. `docs/ARCHITECTURE.md` §2 nói bản 8 và catalog 4.

- [ ] T015 Sửa `evals/model.py` (phụ thuộc T014). `cases_version` 3 được nhận. Thêm trường kỳ vọng chỉ khi tám ca của User Story 7 chưa diễn được bằng trường bản 2. Trường mới có mặc định trống và bản 1, bản 2 không đọc. Không đổi thứ tự `LAW_NAMES` của bản 1

- [ ] T016 Sửa `evals/load.py` (phụ thuộc T015). `cases_version` 3 hợp lệ. Bộ 1 và bộ 2 vẫn từ chối hay nhận đúng như hiện tại. Khóa mới vắng là trống

- [ ] T017 Sửa `evals/score.py` (phụ thuộc T015, T016). `SCORER_VERSION` là 3. `cases_version` 1 đi đúng hàm bản 1. `cases_version` 2 đi đúng hàm bản 2. Bộ 3 chấm tám ca của User Story 7. Ca vượt không lấy bản thân cờ `confirm` làm chuẩn đạt. Ca thứ tám: kho sau lượt hai bằng kho lúc mở thì đạt. Kho đổi thì trượt. Không sửa `evals/runner.py` nếu đối số đường dẫn bộ câu đã có

- [ ] T018 Tạo `evals/cases/v3.json` và `evals/datasets/qua_tai.json` (phụ thuộc T016). `cases_version` là 3. Đủ tám ca của User Story 7, không thêm không bớt. Ca 8 có lượt hai, câu từ chối là thôi không thêm nữa. Seed nằm ở `qua_tai.json`. Không sửa `evals/store.py` nếu seed đã nhận `scheduled_on`, `effort` và `priority`

- [ ] T019 Sửa `tests/test_eval_score.py` và `tests/test_eval_load.py` (phụ thuộc T017, T018). Một hàm đạt và một hàm trượt cho ca từ chối: kho không đổi thì đạt, kho đổi thì trượt. Một hàm khóa bộ v3 có tám ca. Không đổi assert của ca v1 và ca v2

- [ ] T020 [P] Sửa `docs/PRODUCT.md` (phụ thuộc T014). Thêm hàng F20 ở §3: quét tải, cảnh báo mềm khi ngày vượt quỹ, không tự dời. §7 mục 5 gọi tên F20. §8 bỏ quét tải khỏi nhóm chưa cấp số

- [ ] T021 [P] Sửa `docs/ARCHITECTURE.md` §2 (phụ thuộc T009, T010). Chín tool, `DEFINITIONS_VERSION` 4, `PROMPT_VERSION` 8, hàm tải trong `src/core/plans.py`. Không sửa diagram

### Đột biến lô 3

Cùng cách T004.

- [ ] T022 Trong `evals/score.py`, ca từ chối coi cờ `confirm` là đạt (phụ thuộc T019). Hàm ca từ chối trong `tests/test_eval_score.py` phải đỏ vì chuẩn đạt là kho không đổi. Hoàn tác

- [ ] T023 Chạy `.\scripts\check.ps1 -AllowList specs/016-load-check/allowed-files.txt` (phụ thuộc T019, T020, T021, T022). Ghi mã thoát và cả bảng. Không chạy eval. Không `db push`. Không deploy

- [ ] T024 DỪNG: Starter chạy ba lệnh, mỗi lệnh một bộ, vì Cursor không giữ khóa API. Không gộp. Từ gốc repo:

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi vào repo>"
uv run python -m evals.runner evals/cases/v1.json
uv run python -m evals.runner evals/cases/v2.json
uv run python -m evals.runner evals/cases/v3.json
```

Mỗi lệnh ghi một file trong `evals/results/`, tên `p{prompt}-d{definitions}-{model}-{ngày}.json` do runner đặt. Cursor không chạy ba lệnh này. Khi Starter đưa ba đường dẫn, thêm đúng ba đường đó vào `specs/016-load-check/allowed-files.txt`, không dùng `*`. Rồi chat đọc diff lô 3 và ba file kết quả. Không deploy. Không `db push`

## Dependencies & Execution Order

### Phase Dependencies

- T001 đứng trước mọi sửa `src/` và trước mọi sửa `docs/DECISIONS.md`
- Lô 2 bắt đầu sau T005, khi chat đã đọc `src/core/plans.py` và `tests/test_load_check.py`
- Lô 3 bắt đầu sau T014, khi chat đã đọc diff lô 2
- T024 chỉ sau T023. Ba lệnh eval chỉ Starter chạy
- Không task nào trong lô 3 sửa `docs/DECISIONS.md`

### User stories

Lô 1 làm luật tính của User Story 1, 2 và 4. Lô 2 làm User Story 3, 5 và 6, cùng câu cảnh báo. Lô 3 làm User Story 7 và hàng F20. Không có story nào giao độc lập trước lô của nó.

### Trong một lô

- T002 có hàm trước T003
- T006 có test tool trước T007
- T008 nối router sau T007
- T009 và T010 song song sau T005, không chờ T007
- T011 sau T007 và T008, vì hai ca gọi tool trên hai kho
- T012 sau câu cảnh báo đã xanh. T013 sau hai ca cùng kế hoạch đã xanh
- T015 trước T016 và T017. T018 sau T016. T019 sau T017 và T018
- T020 song song với T015. T021 sau T009 và T010
- T022 sau T019. T023 sau docs và sau đột biến đã hoàn tác
- T005, T014 và T024 là điểm dừng của từng lô

### Parallel

- T009 và T010 song song sau T005
- T016 chạy sau T015, không song song với T015. T020 song song với T015
- T020 và T021 song song với nhau khi T021 đã có bản 4 và bản 8

## Parallel Example: Lô 2

```text
Sau T005:
Task T009 src/tools/tool_definitions.py và tests/test_tool_router.py
Task T010 src/core/system_prompt.py và tests/test_llm_turn.py
```

## Implementation Strategy

Lô 1 khóa phép tính trước khi có tool. Chat đọc diff rồi mới cho tool ghi. Lô 2 khóa câu tool bằng pytest và khóa hai lần ghi cùng một kế hoạch trên cả hai kho. Lô 3 sửa doc sản phẩm và kiến trúc, rồi dừng để Starter chạy ba bộ eval. Không deploy ở cuối tasks.

## Notes

- [P] là file khác nhau, không phụ thuộc task chưa xong
- Đột biến phải hoàn tác trước task sau. SHA256 sau bằng SHA256 trước
- Ca mô hình nói lại câu cảnh báo đo bằng eval, không bằng assert pytest 100%
- `quickstart.md` vẫn ghi "Chưa viết tasks.md". File này thay câu đó. Không sửa quickstart trong các task trên
- Spec FR-009 đã khớp: xung đột version chỉ khi kế hoạch đổi giữa list_plans và replace trong cùng lần gọi. Việc đổi giữa lượt báo và lượt xác nhận được bắt trước lần ghi đầu bằng kiểm tra việc còn tồn tại và còn chưa làm ở T007.
