---
description: "Task list for Bộ đánh giá gọi tool của một lượt"
---

# Tasks: Bộ đánh giá gọi tool của một lượt

**Input**: Design documents from `/specs/009-tool-call-eval/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Viết test trước code cho từng module. Mỗi lượt viết test có một bước `uv run pytest` và in nguyên output lần fail vào báo cáo phiên trước khi viết module đó. Không sửa test để làm nó pass. Không thêm dependency. Không sửa `src/`, `tests/fakes/`, file test cũ, `docs/PRODUCT.md`, diagram trong `docs/architecture/`. Không sửa `sys.path`.

**Organization**: Thứ tự dưới đây là thứ tự thực hiện. Output fail của một module phải có trong báo cáo phiên trước task viết module đó. T034 chờ người giữ. Không task nào khác điền câu vào `evals/cases/v1.json` hay `evals/datasets/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Không dùng. Mỗi module phải in output fail trước khi viết file của module đó
- **[Story]**: User story (US1 đến US7). Phase setup và phase chốt không gắn story
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `evals/`, `tests/` ở gốc
- Mỗi task chỉ tạo hoặc sửa file có trong `specs/009-tool-call-eval/allowed-files.txt`
- File JSON tạm của test nằm trong `tests/` hoặc trong bộ nhớ. Không ghi `evals/cases/v1.json` và không ghi `evals/datasets/` ở task khác T034
- Không đọc, không ghi `.env` thật và `.dev.vars`. Không ghi giá trị khóa vào file

## Phase 1: Setup

**Purpose**: Phạm vi file và gói rỗng, trước mọi test

- [x] T001 Phạm vi file của lát này là đúng danh sách [plan.md](./plan.md) mục "Phạm vi file", đã ghi vào `specs/009-tool-call-eval/allowed-files.txt`. Mỗi dòng một đường dẫn tương đối, dấu `/`, gồm `tests/test_eval_runner.py`, cộng dòng `specs/009-tool-call-eval/**`. Không dùng `*` ngoài hậu tố `/**`

- [x] T002 Tạo `evals/__init__.py` chỉ với docstring, không import (phụ thuộc T001). Chưa tạo module con

---

## Phase 2: User Story 1 - Chấm một lượt đã ghi sẵn, không mở mạng (Priority: P1) MVP

**Goal**: Sáu luật tự động trên phản hồi ghi sẵn: đúng tool, số lần `create_plan`, tham số bắt buộc, tiền tố, Markdown, tự xưng

**Independent Test**: `uv run pytest tests/test_eval_score.py`. Mỗi luật trong phase này có ca đạt và ca trượt. Không mở mạng

### Tests for User Story 1

- [x] T003 [US1] Viết `tests/test_eval_score.py` (phụ thuộc T002). Chưa viết `evals/score.py`. Bám [contracts/scoring.md](./contracts/scoring.md) và spec FR-002, FR-006, FR-007, FR-008, FR-009, FR-010. Ca dùng log và câu trả lời ghi sẵn, không gọi `run_turn`, không mở mạng. Sáu luật, mỗi luật một ca đạt và một ca trượt, đúng tên:
  - `test_update_group_rejects_set_note`: ca cập nhật trạng thái gọi `set_subtask_note` thì luật đúng tool trượt. Nhóm ghi chỉ đạt luật đúng tool khi mọi lần gọi là `get_plans`, `get_plan_detail`, hoặc đúng tool ghi của nhóm. Không gọi tool nào ở nhóm ghi vẫn đạt luật đúng tool
  - `test_list_group_rejects_other_tools`: hỏi danh sách đạt khi mọi lần gọi là `get_plans` và có ít nhất một lần. Xen `get_plan_detail` thì trượt
  - `test_detail_group_requires_get_plan_detail`: xem chi tiết đạt khi có ít nhất một `get_plan_detail` và mọi lần khác chỉ là `get_plans`. Chỉ `get_plans` thì trượt. Có `update_subtask` thì trượt
  - `test_create_plan_count_fail_on_two`: nhờ lập kế hoạch đạt khi đúng một `create_plan` và không tool khác; hai lần thì trượt. Mọi nhóm khác, kể cả nhóm ghi, đạt khi số lần `create_plan` là 0
  - `test_required_param_missing_goal`: `create_plan` thiếu `goal` thì trượt. `goal` có mặt và không có `subtasks` thì đạt. Không có dòng tool thì đạt. Đầu vào không phải object, hoặc tên không có trong `TOOL_DEFINITIONS`, thì trượt
  - `test_prefix_fails_on_ordinal_words`: `Ngày 1:`, `ngày 1:`, `Tuần 1:`, `1.`, `Bước 1`, `Giai đoạn 2:` trượt. So không phân biệt hoa thường sau NFC. Tiêu đề đã có trong bộ dữ liệu không bị xét. Không có tiêu đề mới thì đạt
  - `test_prefix_nfc_composed_and_combining`: một chuỗi dựng sẵn và một chuỗi tổ hợp cùng nội dung cho cùng một kết quả tiền tố
  - `test_markdown_allows_numbered_and_dash`: dòng `1. Chạy 2km` và dòng `- Nộp báo cáo` đạt khi không có dấu cấm
  - `test_markdown_rejects_star`: ba backtick, một backtick, `**`, `__`, `](`, dòng có ký tự khác khoảng trắng đầu tiên là `#`, hoặc dòng sau khoảng trắng đầu là `*` rồi một khoảng trắng, thì trượt
  - `test_self_name_rejects_phrase`: chứa đúng cụm `trợ lý lập kế hoạch` sau NFC thì trượt. Không `casefold` cụm này

- [x] T004 [US1] Chạy `uv run pytest tests/test_eval_score.py --tb=short` (phụ thuộc T003). In nguyên output lần chạy này vào báo cáo phiên trước khi viết `evals/score.py`. Kỳ vọng fail vì chưa có module. Không sửa test để làm pass

### Implementation for User Story 1

- [x] T005 [US1] Viết sáu luật trong `evals/score.py` (phụ thuộc T004). Chưa viết luật kho. Một lần đạt khi mọi luật được xét đều đạt. Không so câu trả lời để nhận lỗi chạy. Không import `clients`, `anthropic`, `pydantic`. Không đọc `os.environ`

**Checkpoint**: Sáu luật chạy từ log ghi sẵn. Luật kho chưa có

---

## Phase 3: User Story 2 - Ca ghi được chấm bằng kho sau lượt (Priority: P1)

**Goal**: Luật kho thứ bảy cho ba nhóm ghi, xét riêng luật đúng tool

**Independent Test**: `test_store_update_requires_new_status` trong `tests/test_eval_score.py` có ca đạt và ca trượt. Không mở mạng

### Tests for User Story 2

- [x] T006 [US2] Thêm ca luật kho vào `tests/test_eval_score.py` (phụ thuộc T005). `test_store_update_requires_new_status`: ca cập nhật đạt khi việc con chỉ bởi mục tiêu và tiêu đề có đúng trạng thái kỳ vọng `pending`, `done`, hoặc `skipped`. Ca thêm việc đạt khi kế hoạch chỉ bởi mục tiêu có một việc con mang tiêu đề kỳ vọng mà bộ dữ liệu chưa có. Ca ghi chú đạt khi việc đó có đúng ghi chú kỳ vọng; ghi chú rỗng hoặc chỉ khoảng trắng sau NFC và strip nghĩa là không còn ghi chú, cùng `normalize_subtask_note`. Việc không được nêu trong kỳ vọng không đổi kết quả luật. Không gọi tool ở nhóm ghi: luật đúng tool đạt và luật kho trượt nếu kho không khớp kỳ vọng. Ca `update_status` mà trạng thái kỳ vọng đã bằng dữ liệu gốc, ca `set_note` mà ghi chú kỳ vọng đã bằng dữ liệu gốc, hoặc ca `add_subtask` mà tiêu đề đã có: không phải ca chấm, là sai định dạng ở T009

- [x] T007 [US2] Chạy `uv run pytest tests/test_eval_score.py --tb=short` (phụ thuộc T006). In nguyên output vào báo cáo phiên. Kỳ vọng các ca luật kho fail. Không sửa test để làm pass

### Implementation for User Story 2

- [x] T008 [US2] Thêm luật kho vào `evals/score.py` (phụ thuộc T007). Luật này chỉ xét ba nhóm ghi. `not_applicable` với nhóm khác

**Checkpoint**: Bảy luật chấm được từ log và kho ghi sẵn

---

## Phase 4: User Story 3 - Bộ câu và bộ dữ liệu dựng lại được (Priority: P1)

**Goal**: Đọc JSON tạm, từ chối bộ sai, dựng `MemoryPlanStore` từ bộ dữ liệu

**Independent Test**: `uv run pytest tests/test_eval_load.py tests/test_eval_store.py`. Hai lần cùng một câu dựng hai kho trùng bộ dữ liệu gốc

### Tests for User Story 3

- [x] T009 [US3] Viết `tests/test_eval_load.py` (phụ thuộc T002). Chưa viết `evals/model.py` và `evals/load.py`. File tạm trong `tests/`. Ràng buộc nguyên văn từ [data-model.md](./data-model.md): `cases_version` là số nguyên, bộ v1 là `1`; `cases` là mảng, id không trùng; `id` không rỗng sau NFC và strip; `group` là một trong mười chữ enum, đúng nguyên chữ sau NFC; `user_message` NFC khi đọc; `dataset` NFC, rỗng sau strip nghĩa là không có bộ dữ liệu; `expectation.kind` khớp nhóm. `kind` và trường thêm: `no_tool` không trường thêm; `one_create_plan` không; `read_plans` không; `read_detail` không; `update_status` có `goal`, `title`, `status`; `add_subtask` có `goal`, `title`; `set_note` có `goal`, `title`, `note`. `status` là `pending`, `done`, hoặc `skipped`. Bộ dữ liệu: `name` bằng tên file không tính `.json`; `plans` theo thứ tự `add`; việc con có `title`, `status` một trong ba mã, `note` chuỗi hoặc JSON `null`; mục tiêu không trùng trong một file; tiêu đề không trùng trong một kế hoạch; không có trường id. Tên `dataset` không có `/`. Ca sai định dạng bị từ chối và không chạy lượt

- [x] T010 [US3] Chạy `uv run pytest tests/test_eval_load.py --tb=short` (phụ thuộc T009). In nguyên output vào báo cáo phiên trước khi viết `evals/model.py` và `evals/load.py`. Kỳ vọng fail. Không sửa test để làm pass

### Implementation for User Story 3

- [x] T011 [US3] Viết `evals/model.py` và `evals/load.py` (phụ thuộc T010). `group` là `StrEnum` đúng mười chữ này: `nhờ lập kế hoạch`, `chỉ kể việc`, `hỏi danh sách`, `xem chi tiết`, `cập nhật trạng thái việc con`, `thêm việc con`, `ghi chú`, `chào hỏi`, `câu mơ hồ`, `câu ngoài phạm vi`. Không dùng Pydantic. Parse bằng `json` và dataclass

- [x] T012 [US3] Viết `tests/test_eval_store.py` (phụ thuộc T011). Chưa viết `evals/store.py`. Dựng kho bằng `normalize_new_plan(goal, None)`, `new_subtask(title)`, `normalize_subtask_note`, và `Subtask(...)` với `SubtaskStatus` khi trạng thái không phải pending hoặc khi có ghi chú. Không gọi hàm `_`. Hai lần dựng cùng một câu cho hai kho trùng bộ dữ liệu gốc. Tên dataset rỗng là kho không có kế hoạch. Thứ tự kế hoạch là thứ tự trong file

- [x] T013 [US3] Chạy `uv run pytest tests/test_eval_store.py --tb=short` (phụ thuộc T012). In nguyên output vào báo cáo phiên trước khi viết `evals/store.py`. Kỳ vọng fail. Không sửa test để làm pass

- [x] T014 [US3] Viết `evals/store.py` (phụ thuộc T013). Một dòng import kho: `from tests.fakes.memory_plan_store import MemoryPlanStore`. Không import `tests` theo kiểu khác

**Checkpoint**: Đọc và dựng kho từ JSON tạm. `evals/cases/` và `evals/datasets/` vẫn chưa có chữ

---

## Phase 5: User Story 4 - Ba lần độc lập, lỗi hạ tầng không làm dừng bộ (Priority: P2)

**Goal**: Ba lần mỗi câu, phân loại lỗi chạy theo dòng log cuối, hết lượt tool vẫn được chấm

**Independent Test**: `uv run pytest tests/test_eval_run.py`. Một lần lỗi chạy không chặn lần sau. Không mở mạng

### Tests for User Story 4

- [x] T015 [US4] Viết `tests/test_eval_run.py` (phụ thuộc T014). Chưa viết `evals/turn.py`. Bịt `socket.socket` để ném `AssertionError` nếu bị gọi. Client giả. Mỗi lần một `MemoryPlanStore` mới và lịch sử rỗng. Không so câu trả lời. Ca riêng cho từng mã, đúng thứ tự ở [contracts/scoring.md](./contracts/scoring.md):
  - `test_run_error_missing_key`: `run_turn` ném `MissingKeyError`. Mã `missing_key`. Không vào mẫu số. Lần sau vẫn chạy
  - `test_run_error_no_model_log`: không có dòng tám khóa và không phải `MissingKeyError`. Mã `no_model_log`
  - `test_run_error_ended_on_tool_log`: dòng log cuối là dòng bảy khóa. Mã `ended_on_tool_log`
  - `test_run_error_model_error`: dòng cuối là dòng tám khóa, `error_type` khác JSON `null`. Mã `model_error`
  - `test_run_error_bad_stop_reason_max_tokens`: dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `max_tokens`. Mã `bad_stop_reason`
  - `test_run_error_bad_stop_reason_tool_use_without_requests`: dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `tool_use`, không có `tool_requests`, và trước dòng đó chưa đủ ba vòng. Mã `bad_stop_reason`
  - `test_cap_counted_outside_rate`: dòng cuối là dòng tám khóa, `stop_reason` là `tool_use`, `error_type` là `null`, trước đó đúng ba vòng. Không phải lỗi chạy. Vẫn chấm luật. Có trong số đếm hết lượt tool, số đếm không thay tỉ lệ
  - Cả ba lần lỗi chạy: tỉ lệ câu là `null`, `run_errors` là `3`, câu sau vẫn chạy

- [x] T016 [US4] Chạy `uv run pytest tests/test_eval_run.py --tb=short` (phụ thuộc T015). In nguyên output vào báo cáo phiên trước khi viết `evals/turn.py`. Kỳ vọng fail. Không sửa test để làm pass

### Implementation for User Story 4

- [x] T017 [US4] Viết `evals/turn.py` (phụ thuộc T016). Gọi `run_turn` đã có. Ba lần độc lập. Phân loại đúng bảy hàng của bảng trong [contracts/scoring.md](./contracts/scoring.md). `kind` của lần lỗi là đúng một trong năm mã, không gộp

**Checkpoint**: Bộ test thường chấm và phân loại mà không mở mạng

---

## Phase 6: User Story 5 - Báo cáo tỉ lệ và một file đường cơ sở (Priority: P2)

**Goal**: Tỉ lệ, token, giấu khóa, một file kết quả mới

**Independent Test**: `uv run pytest tests/test_eval_result.py`. Một lần chạy đủ ghi đúng một file. File không chứa khóa không rỗng

### Tests for User Story 5

- [x] T018 [US5] Viết phần tỉ lệ trong `tests/test_eval_result.py` (phụ thuộc T017). Chưa viết `evals/summary.py`. Tỉ lệ câu là số lần đạt trên số lần được chấm. Lần lỗi chạy không vào mẫu số. Ba lần lỗi chạy thì tỉ lệ `null` và `run_errors` là `3`. Tỉ lệ luật trên số lần luật đó được xét. Tỉ lệ nhóm trên số lần được chấm trong nhóm. `cap_stops` theo câu và theo nhóm, đứng riêng, không làm tử số hay mẫu số. Lần hết lượt tool đã chấm vẫn nằm trong tỉ lệ. Hai tổng token cộng `input_tokens` và `output_tokens` trên mọi dòng tám khóa, kể cả lần lỗi chạy. Trống cộng `0`

- [x] T019 [US5] Chạy `uv run pytest tests/test_eval_result.py --tb=short` (phụ thuộc T018). In nguyên output vào báo cáo phiên trước khi viết `evals/summary.py`. Kỳ vọng fail. Không sửa test để làm pass

- [x] T020 [US5] Viết `evals/summary.py` (phụ thuộc T019)

- [x] T021 [US5] Thêm `test_redact_replaces_nonempty_key` vào `tests/test_eval_result.py` (phụ thuộc T020). Chưa viết `evals/redact.py`. Khóa không rỗng và không chỉ khoảng trắng bị thay bằng đúng cụm `đã giấu khóa` trong câu trả lời và trong chuỗi dòng log. Không thêm, không bớt khóa JSON của dòng log. Khóa rỗng hoặc chỉ khoảng trắng không bị thay

- [x] T022 [US5] Chạy `uv run pytest tests/test_eval_result.py --tb=short` (phụ thuộc T021). In nguyên output vào báo cáo phiên trước khi viết `evals/redact.py`. Kỳ vọng ca giấu khóa fail. Không sửa test để làm pass

- [x] T023 [US5] Viết `evals/redact.py` (phụ thuộc T022)

- [x] T024 [US5] Thêm ca file kết quả vào `tests/test_eval_result.py` (phụ thuộc T023). Chưa viết `evals/result.py`. Bám [contracts/result-file.md](./contracts/result-file.md). Mọi ca ghi file truyền `tmp_path` vào tham số thư mục ra và truyền một ngày cố định vào tham số ngày. Ca không gọi `date.today()`. Đúng một file mới trong `tmp_path`. Không ghi đè: file đã có thì thêm `-2`, `-3` trước `.json`. Tên `p<prompt_version>-d<definitions_version>-<model>-<YYYY-MM-DD>.json`. Ba nhãn lệch thì phần lệch là `lech`. Không có dòng tám khóa thì ba nhãn là `trong`. `kind` của từng lần là một trong `scored`, `cap`, `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`. UTF-8, `ensure_ascii=False`. File không chứa giá trị khóa không rỗng

- [x] T025 [US5] Chạy `uv run pytest tests/test_eval_result.py --tb=short` (phụ thuộc T024). In nguyên output vào báo cáo phiên trước khi viết `evals/result.py`. Kỳ vọng ca file fail. Không sửa test để làm pass

- [x] T026 [US5] Viết `evals/result.py` (phụ thuộc T025). Hàm ghi nhận thư mục ra và ngày là hai tham số bắt buộc, không có giá trị mặc định. Hàm không gọi `date.today()`. Model trong tên chỉ giữ chữ, số, dấu chấm, dấu gạch ngang; ký tự khác thành `-`

**Checkpoint**: Báo cáo và file kết quả chạy từ dữ liệu ghi sẵn

---

## Phase 7: User Story 6 - Chỗ đánh dấu tay cho điểm kết thúc đo được (Priority: P3)

**Goal**: Mỗi tiêu đề bị luật tiền tố xét có một chỗ đánh dấu, bắt đầu `unmarked`. Đổi chỗ đó không đổi tỉ lệ

**Independent Test**: Ca trong `tests/test_eval_result.py` đọc `manual_titles` và xác nhận đổi `mark` không đổi tỉ lệ

### Tests for User Story 6

- [x] T027 [US6] Thêm ca chỗ đánh dấu vào `tests/test_eval_result.py` (phụ thuộc T026). Ca ghi file dùng `tmp_path`. Mỗi tiêu đề bị luật tiền tố xét có `{title, mark}`. `mark` ban đầu là `unmarked`. Giá trị người đọc ghi sau này là `pass` hoặc `fail`. Đổi `mark` không đổi tỉ lệ tự động. Luật điểm kết thúc đo được không nằm trong tỉ lệ

- [x] T028 [US6] Chạy `uv run pytest tests/test_eval_result.py --tb=short` (phụ thuộc T027). In nguyên output vào báo cáo phiên trước khi sửa `evals/result.py` cho chỗ đánh dấu. Kỳ vọng ca mới fail. Không sửa test để làm pass

### Implementation for User Story 6

- [x] T029 [US6] Sửa `evals/result.py` để ghi `manual_titles` (phụ thuộc T028). Nếu tỉ lệ đang đọc `mark`, sửa `evals/summary.py` để tỉ lệ không phụ thuộc `mark`

**Checkpoint**: File kết quả có chỗ đánh dấu tay. Tỉ lệ không đổi khi sửa chỗ đó

---

## Phase 8: User Story 7 - Lần chạy API thật là lệnh tay (Priority: P3)

**Goal**: Runner đọc khóa từ mapping, dừng đúng cách, và chỉ `main` đụng môi trường thật. Bộ câu v1 chờ nguyên văn. Lệnh tay đứng sau bộ câu

**Independent Test**: `uv run pytest tests/test_eval_runner.py` không dựng `AnthropicModel` và không đọc khóa thật. Lệnh tay không nằm trong pytest

### Tests for User Story 7

- [x] T030 [US7] Viết `tests/test_eval_runner.py` (phụ thuộc T029). Chưa viết `evals/runner.py`. Test gọi hàm nhận `Mapping[str, str]`, client giả, thư mục ra, và ngày. Mọi ca ghi file truyền `tmp_path` vào thư mục ra và truyền một ngày cố định. Không đọc `os.environ` để lấy khóa. Không dựng `AnthropicModel`. Không gọi `date.today()`. Năm ca:
  - `test_runner_rejects_missing_empty_and_whitespace_key`: khóa thiếu, khóa `""`, và khóa chỉ khoảng trắng. Dừng trước lượt đầu, không gọi client, không ghi file. Câu báo đúng `Thiếu JARVIS_EVAL_ANTHROPIC_KEY.` ra stderr, mã `2`
  - `test_runner_keyboard_interrupt_writes_no_file`: client giả ném `KeyboardInterrupt` giữa bộ. Dừng, không ghi file, mã `130`
  - `test_runner_cancelled_error_writes_no_file`: client giả ném `asyncio.CancelledError` giữa bộ. Dừng, không ghi file, mã `130`
  - `test_runner_full_run_writes_one_file`: bộ nhỏ với client giả chạy đủ. Ghi đúng một file trong `tmp_path`
  - `test_runner_leaves_evals_results_unchanged`: ghi danh sách file của `evals/results/` trước khi ca chạy, chạy hàm chạy cả bộ với `tmp_path`, rồi ghi lại danh sách. Hai danh sách trùng nhau

- [x] T031 [US7] Chạy `uv run pytest tests/test_eval_runner.py --tb=short` (phụ thuộc T030). In nguyên output vào báo cáo phiên trước khi viết `evals/runner.py`. Kỳ vọng fail. Không sửa test để làm pass

### Implementation for User Story 7

- [x] T032 [US7] Sửa `.specify/memory/constitution.md` và `docs/DECISIONS.md` (phụ thuộc T031, đứng trước T033). Không viết `evals/runner.py` trong task này. Constitution: `**Version**: 1.1.0` thành `1.2.0`, `**Last Amended**` thành ngày sửa file, và thêm đúng câu này vào mục Quy ước mã nguồn:

> Ngoại lệ: file `evals/runner.py` được đọc biến `JARVIS_EVAL_ANTHROPIC_KEY` từ môi trường tiến trình của lệnh chạy tay, rồi truyền giá trị đó vào lượt. Không file nào khác trong `evals/` được đọc biến môi trường. `src/` không đọc biến này.

  Cập nhật comment Sync Impact Report ở đầu file: version `1.1.0` → `1.2.0`, phần thêm là câu ngoại lệ đó. Không sửa nguyên tắc I đến VIII. Trong `docs/DECISIONS.md` thêm mục, `Status` là `Accepted`, `Date` là ngày sửa file, ba đoạn sau đúng chữ plan:

> **Bối cảnh:** Quy ước mã nguồn nói config chỉ đọc qua `src/config/settings.py` và không ghi phạm vi. Lệnh eval chạy tay cần khóa. Nguyên tắc IV cấm lượt và adapter đọc môi trường. Ràng buộc đã duyệt: không sửa `src/`, và chỉ `evals/runner.py` đọc `JARVIS_EVAL_ANTHROPIC_KEY`.

> **Quyết định:** Ngoại lệ nằm trong constitution, đúng câu đề xuất ở plan này. Chỉ ghi trong AGENTS.md là không đủ.

> **Phương án đã bỏ:** thêm khóa vào `src/config/settings.py`. Để runner đọc môi trường mà không sửa constitution.

  Tiêu đề mục là `D-017 — Runner eval đọc một biến môi trường`

- [x] T033 [US7] Viết `evals/runner.py` (phụ thuộc T032). Bám [contracts/runner.md](./contracts/runner.md). Hàm kiểm khóa, hàm chạy cả bộ, và hàm xử lý `KeyboardInterrupt` nhận `Mapping[str, str]` và `ModelClient`. Hàm chạy cả bộ còn nhận thư mục ra và ngày, cả hai là tham số bắt buộc, không có giá trị mặc định. Hàm chạy cả bộ truyền đúng hai giá trị đó vào hàm ghi của `evals/result.py`. Các hàm này không đọc `os.environ`, không dựng `AnthropicModel`, và không gọi `date.today()`. `asyncio.CancelledError` đi cùng đường với `KeyboardInterrupt`: không chạy lần tiếp, không ghi file, mã `130`. Chỉ `main` đọc `os.environ`, gọi `AnthropicModel()`, gọi `date.today()`, và truyền ngày đó cùng `evals/results/` vào hàm chạy cả bộ. `from clients.anthropic_model import AnthropicModel` nằm trong `main`. Không sửa `sys.path`. Sai định dạng bộ câu: mã `2`, không ghi file. Hết bộ: mã `0` kể cả khi tỉ lệ thấp

- [x] T034 [US7] Đưa bộ câu v1 và bộ dữ liệu kho nguyên văn vào `evals/cases/v1.json` và `evals/datasets/` (phụ thuộc T033). Task này chờ người giữ cung cấp chữ. Không bịa câu. Không task nào khác điền câu vào hai đường này. Khi có chữ: `cases_version` là `1`, mỗi câu đúng trường ở [data-model.md](./data-model.md), mỗi tên `dataset` không rỗng có một file `evals/datasets/<tên>.json` với `name` bằng tên file không tính `.json`. Bộ sai định dạng thì dừng và hỏi lại, không sửa chữ người giữ

- [ ] T035 [US7] Lệnh chạy tay (phụ thuộc T034). Chỉ chạy khi T034 đã có nguyên văn và tiến trình đã có `JARVIS_EVAL_ANTHROPIC_KEY`. Không ghi giá trị khóa vào file. Lệnh, từ gốc repo:

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi vào repo>"
uv run python -m evals.runner
```

  Chưa chạy thì task này chưa xong, và chữ trong `AGENTS.md` vẫn là "chưa chạy thử". Không chạy lệnh này trong bước tạo tasks

**Checkpoint**: Pytest của runner xanh mà không gọi API. Lệnh tay chờ bộ câu và một lần chạy thật

---

## Phase 9: Polish

**Purpose**: Mutation, `check.ps1`, docs B10

- [x] T036 Làm hỏng từng luật chấm trong `evals/score.py` đúng một lần, rồi hai mutation trên `evals/turn.py` (phụ thuộc T008 và T017). Lần lượt, xong một lần trả lại rồi mới sang lần sau. Với mỗi luật trong `evals/score.py`: làm hỏng đúng một chỗ; chạy đúng test chuyên trách; in output đỏ vào báo cáo phiên và ghi tên ca nào đỏ; ca của luật khác không được là ca duy nhất đổi; trả lại chỗ vừa hỏng. Sau mỗi lần trả lại, `git diff -- evals/score.py` rỗng. File chưa được theo dõi thì so với bản đã chép trước lúc làm hỏng, hai bản trùng. Test chuyên trách: `test_update_group_rejects_set_note`, `test_create_plan_count_fail_on_two`, `test_required_param_missing_goal`, `test_prefix_fails_on_ordinal_words` cùng `test_prefix_nfc_composed_and_combining`, `test_markdown_allows_numbered_and_dash` cùng `test_markdown_rejects_star`, `test_self_name_rejects_phrase`, `test_store_update_requires_new_status`. Hai mutation trên `evals/turn.py`: bỏ nhánh nhận `bad_stop_reason` để lần đó thành `scored`; coi dòng log cuối là dòng bảy khóa như lần được chấm. Mỗi mutation ghi tên ca đỏ. Nếu không ca nào đỏ thì dừng và báo, không thêm test để vá. Trả lại xong, `git diff -- evals/turn.py` rỗng; file chưa được theo dõi thì so với bản đã chép, hai bản trùng

- [x] T037 Sửa `scripts/check.ps1` (phụ thuộc T033, T036). Thêm tham số tùy chọn `-Allow` cho `Invoke-GrepCheck`. Sáu hàng hiện có không truyền `-Allow`. Sau `git grep`, lấy phần mã nguồn sau tiền tố `đường-dẫn:số-dòng:` rồi bỏ dòng nào phần đó khớp `-Allow` bằng `-notmatch`. Ba hàng:
  - `SDK imports`: giữ hai mẫu `^\s*(from|import)\s+anthropic\b` và `^\s*from\s+\.+anthropic\b`. Pathspec thành `src`, `:!src/clients/anthropic_model.py`, `evals`. Không truyền `-Allow`
  - Hàng mới `Eval tests imports`, pathspec `evals`. Mẫu cấm `^\s*(from|import)\s+tests\b`. `-Allow` là `^\s*(from|import)\s+tests\.fakes\.memory_plan_store(\s|$)`
  - Hàng mới `Eval env reads`, pathspec `evals` và `:!evals/runner.py`. Hai mẫu `\bos\.(getenv|environ)\b` và `^\s*from\s+os\s+import\s+.*\b(getenv|environ)\b`. Không truyền `-Allow`
  Thêm dòng `Write-Host` và nhánh `$anyFail` theo đúng kiểu sáu hàng hiện có. Thử mỗi trong ba hàng bằng một file tạm vi phạm và một file tạm hợp lệ, ghi bảng vào báo cáo phiên, rồi xóa file tạm. Cuối cùng bật kho local `npx --yes supabase@2.122.0`, đặt `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ `status -o json`, host là `127.0.0.1` hoặc `localhost`, rồi chạy `.\scripts\check.ps1 -AllowList specs/009-tool-call-eval/allowed-files.txt`. Kỳ vọng mã 0, pytest 0 skip, mọi hàng pass. Không tắt `--fail-on-skip`

- [x] T038 Docs B10 (phụ thuộc T033). `AGENTS.md`: thêm lệnh ở T035, kèm chữ "chưa chạy thử" cho tới khi T035 chạy thật. Không ghi giá trị khóa. `docs/ARCHITECTURE.md`: thêm `evals/` ở mục module. Sửa câu "Vì vậy toàn bộ package nằm trong `src/`, không phải root." để nói `evals/` nằm ngoài bundle Worker và `src/` không import nó. Không sửa diagram trong `docs/architecture/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: không phụ thuộc task khác
- **US1 (Phase 2)**: phụ thuộc Setup. MVP
- **US2 (Phase 3)**: phụ thuộc US1 vì cùng `evals/score.py`
- **US3 (Phase 4)**: phụ thuộc Setup. Đọc JSON không cần sáu luật đã xanh, nhưng thứ tự thực hiện đặt sau US2
- **US4 (Phase 5)**: phụ thuộc US3 vì một lần chạy cần kho đã dựng
- **US5 (Phase 6)**: phụ thuộc US4 vì báo cáo đọc mã lần chạy
- **US6 (Phase 7)**: phụ thuộc US5 vì chỗ đánh dấu nằm trong file kết quả
- **US7 (Phase 8)**: test runner phụ thuộc US6. T032 đứng trước T033. T034 đứng sau mọi task test và code của phần thuần và sau T033, trước T035
- **Polish (Phase 9)**: T036 phụ thuộc luật kho và phân loại lần chạy đã có. T037 và T038 phụ thuộc runner đã có

### User Story Dependencies

- **US1 (P1)**: sau Setup
- **US2 (P1)**: sau US1
- **US3 (P1)**: sau Setup về mặt file, sau US2 trong thứ tự thực hiện
- **US4 (P2)**: sau US3
- **US5 (P2)**: sau US4
- **US6 (P3)**: sau US5
- **US7 (P3)**: sau US6. Lệnh tay còn chờ T034

### Within Each User Story

- Test của module viết trước và fail trước khi viết module
- In nguyên output lần fail vào báo cáo phiên
- Không sửa assertion để đổi fail thành pass

### Parallel Opportunities

Không có task `[P]`. Output fail của một file phải có trước task viết file đó, nên không chạy hai module đè lên nhau.

---

## Parallel Example: User Story 1

```text
Không chạy song song.
T003 viết tests/test_eval_score.py
T004 in nguyên output fail
T005 mới viết evals/score.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1
2. Phase 2: sáu luật từ log ghi sẵn
3. Dừng và chạy `uv run pytest tests/test_eval_score.py`

### Incremental Delivery

1. US1 sáu luật
2. US2 luật kho
3. US3 đọc JSON và dựng kho
4. US4 ba lần và năm mã lỗi chạy
5. US5 báo cáo, giấu khóa, file
6. US6 chỗ đánh dấu
7. T032 constitution và D-017, rồi T033 runner
8. T034 chờ nguyên văn, rồi T035 lệnh tay
9. T036 mutation, T037 check.ps1, T038 docs

### Parallel Team Strategy

Một người làm lần lượt. Không chia story song song vì mỗi module khóa bởi output fail của chính nó.

---

## Notes

- Không điền 50 câu ở task khác T034
- Không sửa `src/`
- Không chạy lệnh API ở bước tạo tasks
- Commit do người giữ, không tự commit trong các task này
