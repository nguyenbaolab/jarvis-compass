# ARCHITECTURE

> Trạng thái code: src/app.py phục vụ /health, nạp db.plan_store, và gắn `POST /telegram`. Logic F04 đến F08 vẫn ở src/core/plans.py và src/tools/plan_tools.py. execute_tool điều phối chín tool khi người gọi đưa kho. Mỗi lời gọi kho trong tool có hạn chờ theo phần còn lại của ngân sách lượt (người gọi đưa remaining), kế hoạch có version và ghi bằng khóa lạc quan, và lượt không kết thúc bình thường sau khi đã ghi trả bản ghép những gì đã lưu (src/tools/saved_reply.py). Lượt mô hình nằm ở src/turns/llm_turn.py, gọi cổng src/core/llm.py rồi execute_tool. Webhook Telegram `POST /telegram` gọi `handle_update`, và `handle_update` gọi `run_turn`. Khóa mô hình do route đọc qua `require_anthropic_api_key` rồi đưa vào `run_turn`; `run_turn` không đọc settings. SupabasePlanStore do route dựng từ env của request khi xử lý update, không dựng lúc import app. Các module và luồng còn lại dưới đây là thiết kế mục tiêu; khi một tính năng làm xong, cập nhật mục liên quan trong cùng thay đổi.

## §0 Bối cảnh hệ thống

JARVIS Desktop (jarvis-desktop repo)

STT/TTS local, LLM local chỉ route ý định
Tool mới gọi sang jarvis-compass khi cần lập kế hoạch
│ HTTP API
▼
jarvis-compass (repo này)
Cloud-hosted, 24/7, độc lập máy Lenovo
Claude API qua model-agnostic layer
Database riêng (plans/subtasks) — single source of truth
Cron job proactive check-in, luôn remote push
▲ ▲
Telegram Bot App Android riêng
(MVP, Giai đoạn 1) (Giai đoạn 2, sau)

## §1 Tech stack

Stack bắt buộc: xem .specify/memory/constitution.md, mục Ràng buộc kỹ thuật. Chi tiết bổ sung:
- **Web framework:** FastAPI, chạy qua ASGI adapter có sẵn của Cloudflare Workers (`workers.asgi`)
- **LLM:** Claude API (anthropic SDK Python), model MVP: claude-haiku-5-5 (D-004)
- **Deploy:** Cloudflare Workers (`wrangler deploy` / `pywrangler deploy`)
- **Cron:** Cloudflare Cron Triggers (cho F10 proactive check-in)
- **MVP client:** Telegram Bot API

## §2 Module map

> **Lưu ý cấu trúc:** Cloudflare Python Workers chỉ bundle các module nằm cùng cấp hoặc bên trong thư mục chứa entry point (src/entry.py) — đặt package của Worker ở root sẽ gây `ModuleNotFoundError` khi deploy. Vì vậy mọi package của Worker nằm trong `src/`. `evals/` nằm ở root, ngoài bundle Worker, và `src/` không import nó. Chỉ src/entry.py được import workers (runtime Cloudflare); app FastAPI nằm ở src/app.py để test được trên Python thường.

- `src/api/` — FastAPI routes HTTP: endpoint jarvis-desktop lập kế hoạch (F14), `routes_telegram.py` nhận `POST /telegram`, `telegram_update.py` là `handle_update` (F11). Điều phối không import `db`, `clients`, hay `config`.
- `src/core/` — Logic lõi: clarify/orchestration (F01, F02). `llm.py` là cổng trung lập, chỉ thư viện chuẩn. `system_prompt.py` là hằng prompt và `PROMPT_VERSION` 8. `clock.py` định nghĩa `helsinki_clock`. `telegram_channel.py` là luật thuần của kênh: tách UTF-16, cửa sổ 20 tin / 24 giờ, quyết định nhận, hằng 90 giây. Model miền dùng chung (`Plan` có `version`, `Subtask`, `PlanStore`, `PlanConflictError`, chuẩn hóa NFC) ở `src/core/plans.py`. Hàm tải một ngày, quỹ, giờ và danh sách dời (`day_budget`, `task_hours`, `day_load`, `propose_load_moves`) cũng ở `src/core/plans.py`
- `src/turns/` — Vòng lặp của một lượt, gọi `execute_tool`, không import SDK.
- `src/tools/` — Planning tools phía server (F04–F09). `tool_definitions.py` là catalog tên, mô tả, schema đầu vào, chín tool và `DEFINITIONS_VERSION` 4. `tool_router.py` kiểm đầu vào rồi gọi `plan_tools`. `plan_tools` gọi core, đổi kết quả thành `ToolResult`, áp hạn chờ cho mỗi lời gọi kho bằng `asyncio.wait_for` (chỗ duy nhất trong `src/`) và đổi xung đột phiên bản thành câu từ chối. `saved_reply.py` giữ ba câu cố định, mười một mẫu dòng và hàm ghép bản tóm đã lưu cho lượt không kết thúc bình thường (D-021).
- `src/db/` — `client.py` là chỗ duy nhất trong `src/` gọi PostgREST, gồm năm RPC của kênh. `plan_store.py` là bản cổng kế hoạch. `telegram_channel_store.py` là bản cổng update và ngữ cảnh. `models.py` là dòng DB. Hai mốc thời gian chỉ ở bảng việc con. Session HTTP có trần 20 giây mỗi pha, chỉ để giải phóng kết nối, không phải hạn của lượt. Cột `plans.version` và hàm `replace_plan(..., expected_version)` khóa lạc quan (D-021). Hàm kênh không gọi `now()`. Mọi hàm RPC mà `client.py` gọi trả giá trị, không `void`, vì httpx trên Worker đọc body của mọi phản hồi và PostgREST trả 204 khi hàm SQL là `void` (D-023).
- `src/clients/` — Kênh client ngoài: `telegram.py` gửi `sendMessage` với đúng `chat_id` và `text`, timeout 10 giây một phần. Adapter Anthropic nằm cạnh Telegram và dịch cổng sang SDK.
- `src/scheduler/` — Proactive check-in cron (F10)
- `src/config/` — `settings.py` đọc `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_ID`, và `ANTHROPIC_API_KEY` từ nguồn người gọi truyền vào, dict hoặc env của Worker, không bằng `os.getenv`
- `evals/` — Bộ đánh giá tool-call, chạy bằng lệnh tay ngoài bundle Worker. `src/` không import package này.
- `tests/` — Unit tests

## §3 Request flow (HTTP từ client)

Client (jarvis-desktop hoặc Telegram)
→ api/routes_*.py nhận request
→ Với Telegram: so secret, rồi token, rồi loại update. `handle_update` claim, gọi `turns/llm_turn.py` khi là tin chữ, ghi ngữ cảnh, rồi `clients/telegram.py` gửi từng phần
→ core/planning.py orchestrate trên đường desktop
→ turns/llm_turn.py qua cổng core/llm.py
→ tools/tool_router.py execute_tool khi phản hồi đòi tool
→ db/client.py đọc/ghi Supabase qua PostgREST
→ core/session.py cập nhật session state (nếu đang clarify dở)
→ Trả response về client. Telegram trả body rỗng: 401 từ chối, 503 hoãn, 200 bỏ qua hoặc xong


## §4 Proactive check-in flow (cron, không phải HTTP)

Cloudflare Cron Trigger (`0 5 * * *`, `0 6 * * *`, `0 7 * * *`)
→ `entry.scheduled`
→ `scheduler/morning.py`
→ luật thuần trong `core/morning.py`
→ Không gọi mô hình


## §5 Data flow patterns

- Mọi response cho client phải qua field text rõ ràng, tương thích cả jarvis-desktop (JSON) và Telegram (text đơn giản)
- Luật về DB, LLM và trạng thái: xem constitution, nguyên tắc II đến IV.

## §6 Logging

- Mỗi lần nhận `POST /telegram` ghi đúng một dòng JSON của kênh: khóa `outcome` (`reject`, `ignore`, `defer`, `done`) và `reason` (mã đóng, định nghĩa ở `src/api/telegram_update.py`), thêm `update_id` khi body là object có `update_id` kiểu int, `error_type` (tên lớp exception) khi dòng đến từ một exception bị bắt, và `error_code` khi có mã. `error_code` đọc thuộc tính `code` bằng duck typing ở `core/log_line.py` vì `api/` không import `db`. Không có token, secret, chữ tin, câu trả lời, thông điệp exception, hint, hay details.
- Lần chạy sáng ghi một dòng JSON `event` là `morning_digest`. Mã luôn ghi bảy khóa, đúng thứ tự, kể cả khi giá trị là null: `event`, `outcome`, `helsinki_date`, `local_time`, `update_id`, `error_type`, `error_code`. Observability của Cloudflare không hiện khóa có giá trị null, nên lần chạy không lỗi chỉ hiện năm khóa đầu; khóa vắng trong Observability nghĩa là null.
- Mỗi lần gọi tool ghi một dòng JSON bảy khóa. Mỗi lần gọi mô hình đã kết thúc ghi một dòng JSON tám khóa. Cả hai đi qua hàm log được truyền vào `run_turn`. Không thêm khóa, không thêm thư viện log.
- `src/clients/telegram.py` đặt logger `httpx` và `httpcore` ở mức WARNING khi import, vì URL `sendMessage` chứa token bot và logger `httpx` ở mức INFO in nguyên URL (FR-017). Việc này chỉ hạ mức log của thư viện, không thêm thư viện log và không thêm dòng log của dự án.
- Không dùng thư viện log: mỗi dòng JSON đi qua hàm được truyền vào (spec 007, 008), loguru không thêm. Các quy ước code khác: xem constitution, mục Quy ước mã nguồn.

## §7 Điểm khác biệt quan trọng so với jarvis-desktop (lưu ý khi code)

Khác biệt với jarvis-desktop: xem constitution nguyên tắc II, III và docs/DECISIONS.md D-010.
