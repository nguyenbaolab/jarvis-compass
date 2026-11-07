---
description: "Task list for Bản tin sáng"
---

# Tasks: Bản tin sáng

**Input**: Design documents from `/specs/014-morning-digest/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Mỗi nhóm mã đi cùng test của nó. Viết test trước, test phải fail trước khi có mã. Không bớt ca nào trong quickstart.md.

**Organization**: Phase 1 là gói đã duyệt. Phase 2 là luật thuần dùng chung. Sau đó mỗi story một phase. US1, US4 và US5 cùng sửa `src/scheduler/morning.py` nên làm đúng thứ tự trong file này, không song song trên file đó.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: File khác nhau, không phụ thuộc task chưa xong
- **[Story]**: Story của phase đó
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- File được sửa hoặc tạo chỉ là các dòng trong `specs/014-morning-digest/allowed-files.txt`
- Thêm `tzdata` đã duyệt ở research mục 9. Không dừng vì điều kiện thêm thư viện. Mã không `import tzdata`
- `uv lock` chỉ đổi `uv.lock`. `pylock.toml` do `uv run pywrangler sync` tạo cho Pyodide, chỉ ở T002, không `--upgrade`. Không sửa hai file khóa bằng tay
- Không migration, không RPC mới, không đổi chữ ký RPC cũ
- Không deploy, không gọi API Cloudflare, không bắn cron. Không `pywrangler dev`, không `pywrangler deploy`. Chỉ `pywrangler sync`, và chỉ ở T002
- Không sửa `src/core/telegram_channel.py`, `src/core/plans.py`, `src/turns/llm_turn.py`, `src/clients/telegram.py`, `src/clients/anthropic_model.py`
- Không chuẩn hóa vai trong `_history`, `llm_turn`, hay adapter (research mục 11)
- Không sửa `docs/DECISIONS.md`, `docs/PRODUCT.md`, hay diagram trong `docs/architecture/`
- Không đọc, không ghi `.env` thật và `.dev.vars`
- Không copy route `/spike/tz` hay cron năm phút của hai nhánh spike

---

## Phase 1: Setup

**Purpose**: Thêm `tzdata` đã duyệt. Không thêm gói nào khác

- [X] T001 Thêm `tzdata` vào `[project].dependencies` của `pyproject.toml`. Không thêm gói khác. Không `import tzdata` ở task này. Đã duyệt ở research mục 9

- [X] T002 Hai bước, phụ thuộc T001. Không sửa `uv.lock` hay `pylock.toml` bằng tay. (1) `uv lock` để `uv.lock` có `tzdata`. (2) Trong WSL Ubuntu, `export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/jarvis-compass`, rồi `uv run pywrangler sync`, không `--upgrade`, để `pylock.toml` có `tzdata`. Diff của `pylock.toml` chỉ được thêm `tzdata`. Nếu gói khác đổi version thì dừng, dòng đầu `[DỪNG - CẦN CLAUDE CHAT]`

**Checkpoint**: `pyproject.toml` và `uv.lock` có `tzdata` sau `uv lock`. `pylock.toml` có `tzdata` sau `pywrangler sync`, và diff chỉ thêm gói đó. Chưa có mã digest

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Luật thuần trong `src/core/morning.py`. Chặn mọi story. US3 kiểm ở phase này: hai lần gọi cùng các kế hoạch ra cùng một chuỗi

**Independent Test**: Gọi quy tắc hai lần với cùng các kế hoạch. So chữ. Không mở kênh và không gọi mô hình

### Tests

- [X] T003 [P] Viết `tests/test_morning_text.py` trước khi có `src/core/morning.py`. Kỳ vọng fail. Đủ các ca quickstart về chữ, mỗi ca một hàm: kế hoạch `created_order` nhỏ hơn đứng trước; kế hoạch không còn việc `pending` không có đoạn; không còn đoạn nào thì cả chuỗi đúng `Không còn việc chưa làm.`; `is_next_command` đúng với `/Next` và ` /next `; `is_next_command` sai với `/next@bot`. Thêm hai lần `render_digest` cùng tuple `Plan` ra cùng chuỗi, và chuỗi đó không có ngày, thứ, hay múi giờ do quy tắc thêm. `render_digest` chỉ nhận plans, không nhận thời điểm. Đoạn là nguyên văn mục tiêu, xuống dòng, tiêu đề việc `pending` đầu tiên theo thứ tự đã lưu. Từ hai đoạn trở lên cách nhau một dòng trống. Bỏ `done` và `skipped`. Không đưa ghi chú vào chữ. Tiêu đề việc `pending` có ngày như `(thứ Sáu 06/11)` giữ nguyên từng ký tự. Việc `pending` đứng sau việc `pending` đầu tiên không vào chữ. Dấu `*`, `_` và `` ` `` trong mục tiêu hoặc tiêu đề giữ là ký tự. Không lời chào, lời kết, mã kế hoạch, mã việc, tên trạng thái

- [X] T004 [P] Viết `tests/test_morning_clock.py` trước khi có `src/core/morning.py`. Kỳ vọng fail. Sáu mốc UTC qua `helsinki_clock` ra độ lệch giờ 2, 3, 2, 3, 3, 2, đúng thứ tự: `2026-01-15T12:00Z`, `2026-07-15T12:00Z`, `2026-03-29T00:59Z`, `2026-03-29T01:00Z`, `2026-10-25T00:59Z`, `2026-10-25T01:00Z`. `digest_update_id` của ngày 2026-11-07 là `-20261107`, tức `-(năm * 10000 + tháng * 100 + ngày)`. Không đọc đồng hồ hệ thống

- [X] T005 [P] Viết `tests/test_decide_digest.py` trước khi có `src/core/morning.py`. Kỳ vọng fail. `reply` null sau hơn 90 giây thì `decide_digest` là dựng lại. Cùng bản ghi đó qua `decide_receive` vẫn `SaveUncertain` và vẫn là câu `Chưa chắc tin này đã được xử lý.`. `sent_at` có thì xong, không gửi. `reply` có thì gửi lại dù cũ hơn 90 giây. `decide_digest` không có nhánh SaveUncertain và không nhận đồng hồ. Không sửa `src/core/telegram_channel.py`

### Implementation

- [X] T006 Tạo `src/core/morning.py` cho T003, T004, T005 xanh (phụ thuộc T003, T004, T005). Chỉ thư viện chuẩn, gồm `zoneinfo`. Không `import tzdata`, `fastapi`, `pydantic`, `tools`, `db`. Có `render_digest`, `is_next_command`, `helsinki_clock`, `digest_update_id`, `decide_digest`. `is_next_command` là `strip()` rồi `casefold()` bằng `"/next"`. Không sửa `src/core/plans.py` hay `src/core/telegram_channel.py`

**Checkpoint**: Luật chữ, sáu mốc, và `decide_digest` xanh trên CPython. Chưa có cron và chưa có `/next`

---

## Phase 3: User Story 1 - Sáng nào cũng có một tin việc chưa làm (Priority: P1)

**Goal**: Từ 08:00 giờ Helsinki, nếu ngày chưa xác nhận, gửi một digest. Trước 08:00 không claim

**Independent Test**: Đặt giờ Helsinki là 08:00 một ngày mùa đông và một ngày mùa hè. Chạy lần gửi sáng. Đọc tin và đếm lần gọi mô hình

### Tests for User Story 1

- [X] T007 [US1] Viết trong `tests/test_morning_run.py`, trước `src/scheduler/morning.py`. Kỳ vọng fail. Tiêm `datetime` aware, không ngủ, không đọc đồng hồ hệ thống. 07:59 giờ Helsinki: không `claim`, không gửi, không `mark`, outcome `before_eight`. 08:00:00 giờ Helsinki: có `claim`, gửi đúng các phần của `split_utf16` theo thứ tự bằng sender giả, rồi `mark`. Dòng log của lần 07:59 có đúng bảy khóa theo thứ tự `event`, `outcome`, `helsinki_date`, `local_time`, `update_id`, `error_type`, `error_code`, luôn có mặt, và không chứa tiêu đề kế hoạch. `event` là `morning_digest`. `update_id` vẫn là mã âm của ngày dù chưa ghi dòng. `error_type` và `error_code` là JSON null khi không có lỗi. `chat_id` lấy từ `TELEGRAM_OWNER_ID` theo luật research mục 5, không strip. Chuỗi không phải số nguyên thập phân thì `deferred`, không gửi, không `mark`

### Implementation for User Story 1

- [X] T008 [US1] Tạo `src/scheduler/__init__.py` và `src/scheduler/morning.py` với `run_morning(env)` (phụ thuộc T006, T007). Làm xanh T007. Đồng hồ tiêm được; khi không tiêm thì lấy UTC hiện tại rồi `helsinki_clock`. Trước 08:00 dừng sau log. Từ 08:00 thì `claim` mã âm, `reply` null thì `render_digest` rồi lưu. Sau khi lưu chữ, gửi bằng `split_utf16` và `send_part`, rồi `mark_sent`. Ngữ cảnh chưa ghi ở T008. T010 chèn `append_once` trước lúc gửi. Không import `workers`, `anthropic`. Không gọi `run_turn` hay `execute_tool`. Ghi log bằng `write_json_line` sẵn có trong `src/core/log_line.py`. Không sửa `src/core/log_line.py`. Không sửa `src/db/client.py`. Không mở lượt mô hình

**Checkpoint**: Cổng 07:59 / 08:00 và bảy khóa log xanh. Chưa xong ngữ cảnh và lần thử lại

---

## Phase 4: User Story 4 - Trả lời "xong việc đầu" ngay sau digest (Priority: P1)

**Goal**: Ghi một tin assistant bằng cả chuỗi trước khi gửi. Không có tin user giả. Lỗi ghi thì không gửi và không mark

**Independent Test**: Chạy lần gửi thành công, đọc ngữ cảnh trước khi phát tin. Ca riêng: ghi ngữ cảnh thất bại thì đếm tin đã phát bằng 0

### Tests for User Story 4

- [X] T009 [US4] Thêm vào `tests/test_morning_run.py` (phụ thuộc T007). Kỳ vọng fail trên các ca mới. Một dòng `telegram_context_messages` vai `assistant`, không dòng `user`. `body` đúng chuỗi `reply`. `chat_id` là số nguyên của `TELEGRAM_OWNER_ID`. Ghi ngữ cảnh lỗi: không gửi, không `mark`, outcome `deferred`. `append` không ném lỗi, kể cả khi dòng đã có, thì vẫn gửi. Tin dài tách bằng `split_utf16` sẵn có; ngữ cảnh vẫn một chuỗi. Sau khi ghi, `select_context` sẵn có thấy tin assistant đó. Không gọi mô hình. Test lỗi dựng bằng lớp con của `MemoryTelegramChannel` và `RecordingSender` như `tests/test_telegram_update_flow.py`. T010 chỉ cần các ca `FailAppendOnce` và ca ghi ngữ cảnh xanh. Ca gửi lỗi (`fail_on`) và `FailSaveOnce` thuộc T011 và xanh ở T012. Không sửa `tests/fakes`. Không sửa `src/turns/llm_turn.py` hay `src/clients/anthropic_model.py`

### Implementation for User Story 4

- [X] T010 [US4] Sửa `src/scheduler/morning.py` cho các ca `FailAppendOnce` và ca ghi ngữ cảnh của T009 xanh (phụ thuộc T008, T009). Ca `fail_on` và `FailSaveOnce` không thuộc T010; chúng xanh ở T012. `append_once` một lần, `role` là `assistant`, trước khi gửi. Không gọi `_remember` hay `_resend`. Lỗi `append` thì không gửi và không `mark`. Không thêm tin user

**Checkpoint**: Digest đã gửi có đúng một tin assistant trong ngữ cảnh trước lúc gửi

---

## Phase 5: User Story 5 - Chạy lại trong ngày không gửi digest thứ hai (Priority: P1)

**Goal**: `mark` không ném lỗi mới là đã xác nhận. Chưa xác nhận thì lần sau gửi đúng chữ đã lưu, không ghi ngữ cảnh lần hai. Đọc kế hoạch lỗi thì không mark

**Independent Test**: Xác nhận xong rồi chạy lại. Rồi một lần gửi lỗi khi chữ đã nằm trong ngữ cảnh. Hai lần không chung bộ nhớ tiến trình

### Tests for User Story 5

- [X] T011 [US5] Thêm vào `tests/test_morning_run.py` (phụ thuộc T009). Kỳ vọng fail trên các ca mới. Đã có `reply` và `sent_at` null: gửi đúng chữ đó, `append` không thêm dòng, không dựng lại. Gửi lỗi: `sent_at` vẫn null. `mark` không ném lỗi thì outcome `sent` hoặc `resend`. `mark` ném lỗi sau khi gửi thì outcome `deferred`, `sent_at` vẫn null, lần chạy sau gửi lại đúng chữ đã lưu. `sent_at` đã có: không gửi thêm, outcome `already_sent`. `save_telegram_reply` trả false: không gửi chữ vừa dựng. Đọc kế hoạch lỗi: không dựng, không gọi mô hình, không `mark`, outcome `deferred`. Ngày Helsinki hôm sau dùng mã âm khác và không bị mốc hôm trước chặn. Test lỗi dựng bằng lớp con của `MemoryTelegramChannel` và `RecordingSender` như `tests/test_telegram_update_flow.py` (`FailSaveOnce`, `FailAppendOnce`, `fail_on`). Không sửa `tests/fakes`. Không sửa RPC và không thêm migration

### Implementation for User Story 5

- [X] T012 [US5] Sửa `src/scheduler/morning.py` cho T011 xanh (phụ thuộc T010, T011). Chỉ còn nhánh gửi lại chữ đã lưu, đọc boolean của `save_reply_if_absent`, `mark` ném lỗi, và đọc kế hoạch lỗi. `mark` và `append` chỉ xét có ném lỗi hay không. Không đổi đường update thường. Không sửa `src/clients/telegram.py`

**Checkpoint**: US1, US4, US5 xanh trên đồ giả. Chưa có `/next` và chưa có cron trong `wrangler.jsonc`

---

## Phase 6: User Story 2 - Gõ /next để xem lại đúng việc đó (Priority: P1)

**Goal**: Lệnh khớp thì trả `render_digest`, không gọi `run_turn`. Lần Telegram gửi lại vẫn qua `decide_receive`

**Independent Test**: Cùng một bộ kế hoạch, một lần digest và một lần `/next`. So từng ký tự. Rồi gửi `/start` và thấy tin đó vẫn vào lượt

### Tests for User Story 2

- [X] T013 [US2] Thêm ca vào `tests/test_telegram_update_flow.py` trước khi sửa `src/api/telegram_update.py` (phụ thuộc T006). Không đổi kỳ vọng các ca cũ. Kỳ vọng fail trên ca mới. `/next` không gọi `run_turn`. Vẫn hai dòng ngữ cảnh, user rồi assistant. Một dòng log kênh chỉ các khóa cũ `outcome`, `reason`, và khi có thì `update_id`, `error_type`, `error_code`. Không có dòng log mô hình. Chữ trả lời bằng `render_digest` của cùng các kế hoạch. Đọc kế hoạch lỗi: hoãn, không gửi, không gửi câu `Chưa chắc tin này đã được xử lý.`. `/next` không ghi `sent_at` của mã âm ngày digest. Lần gửi lại của chính update `/next` vẫn qua `decide_receive`. `/start`, `/next hôm nay`, và `/next@bot` đều vào `run_turn` như tin chữ thường. Người không phải chủ bot, hoặc không ở chat riêng, bị lọc ở `src/api/routes_telegram.py` dòng 118 đến 121, trước `handle_update`. Feature này không đổi chỗ đó. Chốt chặn là test sẵn có `test_skip_is_200_empty` (nhóm và `user_id` 999, chủ bot là `123`) và `test_supergroup_and_channel_touch_nothing` trong `tests/test_telegram_route.py`. Không thêm file test mới

### Implementation for User Story 2

- [X] T014 [US2] Sửa `src/api/telegram_update.py` cho T013 xanh (phụ thuộc T013). Sau nhánh tin không phải chữ và trước `_history` / `run_turn`, nếu `is_next_command` thì `list_newest_first`, `render_digest`, rồi `_save_context_send` với `remember=True` và reason trả lời thường. Chỉ thêm import `core.morning`. Không import `clients`, `db`, `config`, `anthropic`. Không đổi `write_channel_line`. Không sửa `src/turns/llm_turn.py`

**Checkpoint**: `/next` và digest cùng một chuỗi. `/next@bot` vẫn vào lượt

---

## Phase 7: User Story 3 - Hai đường không lệch chữ (Priority: P1)

**Goal**: Không có hàm dựng thứ hai. `/next` và digest đều gọi `render_digest`

**Independent Test**: Đã nằm ở T003. T013 khẳng định chữ `/next` bằng chính hàm đó

- [X] T015 [US3] Không thêm hàm dựng khác trong `src/scheduler/morning.py` hay `src/api/telegram_update.py` (phụ thuộc T012, T014). Nếu một trong hai đường ghép chữ riêng, sửa lại để gọi `render_digest` trong `src/core/morning.py`. Chạy `tests/test_morning_text.py` và ca `/next` trong `tests/test_telegram_update_flow.py`

**Checkpoint**: Hai đường dùng một hàm. Chữ không phụ thuộc thời điểm

---

## Phase 8: Polish

**Purpose**: Nối cron và sửa đúng hai chỗ trong ARCHITECTURE. Không deploy

- [X] T016 Sửa `src/entry.py` thành `Default(WorkerEntrypoint)` với `fetch` và `scheduled` (phụ thuộc T012). `fetch` ủy quyền ASGI như `asgi.fetch(app, request, self.env)`. `scheduled` chỉ gọi `run_morning(self.env)`. Không đưa kiểu `workers` vào `src/scheduler/`. Sửa `wrangler.jsonc`: `triggers.crons` đúng `0 5 * * *`, `0 6 * * *`, `0 7 * * *`. Không thêm route. Không deploy. Không viết test import `workers`

- [X] T017 [P] Sửa `docs/ARCHITECTURE.md` chỉ §3 và §6 (phụ thuộc T012, T016). §3: đường cron là `entry.scheduled` rồi `scheduler/morning.py` rồi luật thuần, không gọi mô hình. §6: thêm dòng `morning_digest` với bảy khóa đúng thứ tự ở T007. Giữ nguyên câu của dòng kênh, dòng tool bảy khóa, và dòng mô hình tám khóa. Không sửa `docs/DECISIONS.md`. Không sửa `docs/PRODUCT.md`. Không sửa diagram trong `docs/architecture/`

- [X] T018 Chạy `uv run pytest` rồi `.\scripts\check.ps1 -AllowList specs/014-morning-digest/allowed-files.txt` (phụ thuộc T015, T016, T017). `tests/test_rpc_returns.py` và các test log tool, log mô hình phải xanh mà không sửa kỳ vọng của chúng. Không deploy

**Checkpoint**: Pytest và check.ps1 mã 0. Dừng ở đây. Không bắn cron

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: bắt đầu ngay
- **Foundational (Phase 2)**: sau Phase 1. Chặn mọi story
- **US1 (Phase 3)**: sau Phase 2
- **US4 (Phase 4)**: sau US1, cùng file scheduler
- **US5 (Phase 5)**: sau US4, cùng file scheduler
- **US2 (Phase 6)**: sau Phase 2. Song song được với Phase 3 đến Phase 5 vì khác file
- **US3 (Phase 7)**: sau US5 và US2
- **Polish (Phase 8)**: sau US3. `entry.py` cần `run_morning` đã có

### User Story Dependencies

- **US1**: sau luật thuần. Không cần `/next`
- **US4**: sau lát gửi của US1
- **US5**: sau ngữ cảnh của US4
- **US2**: sau luật thuần. Không cần cron
- **US3**: test chữ ở Phase 2; khóa hai đường ở Phase 7

### Within Each User Story

- Test viết trước và fail
- Rồi mới sửa mã của story đó
- Không đánh dấu story xong khi test của nó còn fail

### Parallel Opportunities

- T003, T004, T005 song song
- Sau T006, nhánh US2 (T013, T014) song song với nhánh scheduler (T007 đến T012)
- T017 song song với việc đọc kết quả T016, không song song với sửa `src/entry.py` nếu cùng một người đang sửa entry. T017 chỉ đụng `docs/ARCHITECTURE.md`

---

## Parallel Example: Sau Phase 2

```text
Nhánh A: T007 rồi T008, T009, T010, T011, T012 trong src/scheduler/morning.py
Nhánh B: T013 rồi T014 trong src/api/telegram_update.py
```

Hai nhánh không sửa cùng một file.

---

## Implementation Strategy

### MVP

1. Phase 1 và Phase 2
2. Phase 3 đến Phase 5: một lần chạy sáng đủ cổng giờ, ngữ cảnh, và lần thử lại
3. Dừng và chạy pytest của `tests/test_morning_run.py`
4. Phase 6 và Phase 7 cho `/next`
5. Phase 8 cho entry, wrangler, ARCHITECTURE, rồi check.ps1
6. Không deploy ở cuối implement

### Không làm trong các task trên

- Không `db push`, không file trong `supabase/migrations/`
- Không gọi API Cloudflare và không bắn cron
- Không viết mục D-025. Claude chat viết mục đó và giao Cursor chép ở một nhánh docs-only sau implement

---

## Notes

- `[P]` nghĩa là khác file và không chờ task chưa xong
- Ca quickstart nào cũng có tên trong T003, T004, T005, T007, T009, T011, hoặc T013
- Commit do người dùng. Không tự commit trong lúc làm task
- Việc thật khác plan thì dừng. Dòng đầu câu trả lời là `[DỪNG - CẦN CLAUDE CHAT]` và một câu lý do. Riêng `tzdata` đã duyệt, không dừng vì thêm thư viện đó

---

## Việc của Starter sau deploy, không thuộc implement

Không đánh số. Không giao Cursor. Implement không chạy các bước này.

Sau khi Starter tự deploy, kiểm zoneinfo và `scheduled` trên Worker thật (research mục 8, quickstart.md):

1. Pytest và `pywrangler dev` không chứng minh edge cloud. Sáu mốc ở T004 chỉ chứng minh CPython có `tzdata`.
2. Trên `uv run pywrangler dev`, ứng viên là `GET /__scheduled?cron=0+5+*+*+*`. Đối chiếu đường dẫn với bản `pywrangler` đang cài và với tài liệu Cron Triggers trước khi gọi.
3. Trên Worker đã deploy, bắn lịch `0 5 * * *` từ dashboard hoặc từ API trigger của tài liệu lúc kiểm. Đọc một dòng JSON `event` bằng `morning_digest`. Mùa đông kỳ vọng `local_time` `07:00` và `outcome` `before_eight`, không có tin mới. `0 6 * * *` mới được phép gửi. Mùa hè thì `0 5 * * *` đã là 08:00 địa phương.
4. `spike/cron-checkin` chưa được kiểm trên cloud. Lệch `local_time` nghĩa là zoneinfo trên Worker cloud chưa đúng dù pytest đã xanh.
5. Đổi model khỏi `claude-haiku-5-5` thì kiểm lại ba hình lịch sử ở research mục 11 trước khi deploy. Implement không gọi API đó.
