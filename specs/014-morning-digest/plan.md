# Implementation Plan: Bản tin sáng

**Branch**: `014-morning-digest` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-morning-digest/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Mỗi sáng từ 08:00 giờ Helsinki, Worker gửi một bản tin việc chưa làm cho chủ bot, và lệnh `/next` trả cùng chữ đó ngay. Cả hai đường dùng một hàm thuần, không gọi mô hình. Ngày digest là một dòng `telegram_updates` mã âm, ngữ cảnh chỉ một dòng assistant, và bốn RPC kênh hiện có được dùng lại. Cron là 05:00, 06:00, 07:00 UTC. Code tự giữ cổng 08:00. Các lựa chọn và lý do ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Giữ FastAPI, `postgrest`, `httpx`, `anthropic`. Thêm `tzdata` vào `[project].dependencies` và `uv.lock`. Starter đã duyệt. Mã không `import tzdata`. `zoneinfo` là thư viện chuẩn.

**Storage**: Supabase qua PostgREST, chỉ từ `src/db/client.py`. Không migration, không RPC mới, không đổi chữ ký RPC. Mô hình dòng mã âm ở [data-model.md](./data-model.md).

**Testing**: `uv run pytest`. Luật chữ, đồng hồ, `decide_digest`, và lần chạy sáng dùng đồ giả. Không mạng. Danh sách ca ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython cho pytest. Worker qua `src/entry.py`. Ba cron trong `wrangler.jsonc`. Không deploy ở implement. Kiểm cloud là thủ tục ở quickstart, Starter tự chạy.

**Project Type**: Web service thêm một lối `scheduled`. Không thêm tool. Không thêm route.

**Performance Goals**: Một chủ bot. Digest và `/next` không mở lượt mô hình và không gọi `execute_tool`, nên không đụng ngân sách 20 giây (D-021).

**Constraints**: Nguyên tắc I đến VIII. D-011: core chỉ thư viện chuẩn; không đổi `Plan`, `Subtask`, `PlanStore`. D-007: lịch nằm trên server. D-018: khi đọc được mà không còn việc, vẫn gửi câu đã chốt, không im lặng. D-022: ngữ cảnh trước khi gửi. D-023: không thêm RPC void. D-024: không đổi `PROMPT_VERSION`. Không `os.getenv` trong `src/`. Lịch sử sau digest đi thẳng vào adapter, không chuẩn hóa vai (research mục 11).

**Scale/Scope**: Một cuộc trò chuyện riêng. Một bản tin mỗi ngày Helsinki sau khi kênh xác nhận. `/next` không đụng dấu ngày.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

- **I. Một nhân vật**: chữ là câu đã chốt hoặc mục tiêu và tiêu đề đang lưu. Không persona mới. Đạt.
- **II. Worker không giữ trạng thái**: dấu ngày và ngữ cảnh nằm ở Supabase. Đạt.
- **III. PostgREST**: bốn RPC cũ qua `src/db/client.py`. Không driver mới. Đạt.
- **IV. LLM qua cổng**: hai đường này không gọi mô hình. SDK không đổi chỗ. Đạt.
- **V. Push chủ động**: cron trên Worker, gửi bằng Bot API. Không lịch ở client. Đạt.
- **VI. Database riêng**: không ghi sang Google Tasks. Đạt.
- **VII. Ba giây của desktop**: không phải đường giọng nói. Đạt vì không áp VII.
- **VIII. Unit test**: danh sách ca ở quickstart. Đạt khi implement làm đúng danh sách đó.
- **Pydantic**: không body request mới. Cron không parse JSON đầu vào. Không cần schema Pydantic.
- **Config**: dùng `require_telegram_owner_id`, `require_telegram_bot_token`, `require_supabase`. Không khóa mới. Không đọc env trong `src/`.

### Sau Phase 1

Hàm chữ, đồng hồ, và `decide_digest` ở `src/core/morning.py`. Điều phối cron ở `src/scheduler/morning.py`, nơi được phép import `config`, `db`, `clients`. `scheduled` ở `src/entry.py` chỉ gọi một hàm và là chỗ duy nhất import `workers`. `telegram_update.py` chỉ thêm import `core.morning`. Không cổng nào kéo `workers`, PostgREST, hay `os.getenv` vào core. `decide_receive` không đổi. Gate vẫn đạt.

## Project Structure

### Documentation (this feature)

```text
specs/014-morning-digest/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── digest-text.md
│   └── morning-run.md
├── spec.md
└── checklists/requirements.md
```

`tasks.md` và `allowed-files.txt` không tạo ở bước này. Allow-list tạo ngay sau `/speckit-tasks`.

### Source Code (repository root)

```text
src/core/morning.py                # chữ, lệnh, đồng hồ Helsinki, mã ngày, decide_digest
src/scheduler/__init__.py
src/scheduler/morning.py           # run_morning(env); không import workers
src/entry.py                       # Default(WorkerEntrypoint): fetch và scheduled
src/api/telegram_update.py         # một nhánh /next trước run_turn
wrangler.jsonc                     # ba cron UTC
pyproject.toml và uv.lock          # thêm tzdata, đã duyệt
tests/test_morning_text.py
tests/test_morning_clock.py
tests/test_decide_digest.py
tests/test_morning_run.py
tests/test_telegram_update_flow.py # thêm ca /next, không đổi kỳ vọng cũ
```

Không tạo file trong `supabase/migrations/`. Không sửa `src/core/telegram_channel.py`, `src/core/plans.py`, `src/turns/llm_turn.py`, `src/clients/telegram.py`, `write_channel_line`.

Đồng bộ docs, cùng lúc implement, không phải lúc plan:

```text
docs/ARCHITECTURE.md               # §3 đường cron, §6 bảy khóa dòng sáng
```

Mục D-025 do Claude chat viết và giao Cursor chép ở một nhánh docs-only sau implement, vì AGENTS.md bắt dừng khi chạm `docs/DECISIONS.md`. Không sửa `docs/PRODUCT.md`. Không sửa diagram trong `docs/architecture/` (D-016).

**Structure Decision**: Luật thuần ở `src/core` vì `zoneinfo` là thư viện chuẩn và `telegram_update.py` không được import `db`, `clients`, `config`. Phần có I/O ở `src/scheduler/` vì cổng Workers imports chỉ mở cho `src/entry.py`. So sánh với bảng digest riêng nằm ở research mục 1.

## Complexity Tracking

Không có vi phạm constitution cần biện minh. `tzdata` là phụ thuộc đã được duyệt, không bị import trong `src/core`.

## Design

### Hàm thuần

`src/core/morning.py` như [contracts/digest-text.md](./contracts/digest-text.md). `render_digest` sắp bản sao theo `created_order` tăng dần. `decide_digest` không biết tới 90 giây. `decide_receive` giữ nguyên, kể cả câu `Chưa chắc tin này đã được xử lý.`

### Lần chạy sáng

`run_morning` làm đúng [contracts/morning-run.md](./contracts/morning-run.md). Không gọi `_resend` hay `_remember`: hai hàm đó ghi cả vai `user`. Digest gọi `append_once` một lần với `assistant`.

Trước 08:00 dừng sau khi ghi log. Từ 08:00 thì claim dòng mã âm, rồi một trong ba nhánh: đã có `sent_at`, gửi lại `reply`, hoặc dựng rồi lưu. `mark` không ném lỗi mới là `sent` hoặc `resend`.

### `/next`

Nhánh mới trong `handle_update` đứng sau nhánh tin không phải chữ và trước `_history`. Khớp lệnh thì không gọi `run_turn`. Lần gửi lại của chính update đó vẫn qua `decide_receive`.

### Nhật ký

Dòng sáng là bảy khóa ở research mục 7, ghi bằng `write_json_line`. Ba dòng log cũ không thêm khóa. Việc chép bảy khóa vào ARCHITECTURE §6 chờ bước đồng bộ docs.

### Kiểm sau deploy

Không chạy ở plan hay implement. Thủ tục ép cron `0 5 * * *` và cách đọc `local_time` ở [quickstart.md](./quickstart.md). `spike/cron-checkin` chưa được kiểm trên cloud. Đó là rủi ro đã ghi, không phải mẫu để copy nguyên.
