# ARCHITECTURE

## §1 Tech stack

- **Language:** Python 3.13+ (yêu cầu bởi Pyodide/Cloudflare Python Workers)
- **Runtime:** Cloudflare Python Workers (Pyodide/WebAssembly), qua `pywrangler`
- **Web framework:** FastAPI, chạy qua ASGI adapter có sẵn của Cloudflare Workers (`workers.asgi`)
- **LLM:** Claude API (anthropic SDK Python), model MVP: claude-haiku-4-5
- **Database:** Supabase (Postgres), truy cập qua PostgREST (`postgrest-py`) — KHÔNG dùng driver TCP (asyncpg/psycopg không tương thích Pyodide, xem D-010)
- **Deploy:** Cloudflare Workers (`wrangler deploy` / `pywrangler deploy`)
- **Cron:** Cloudflare Cron Triggers (cho F10 proactive check-in)
- **MVP client:** Telegram Bot API
- **Dev environment:** WSL Ubuntu bắt buộc cho `pywrangler dev` (Windows native chưa tương thích, xem D-010)
- **Package management:** uv + pyproject.toml

## §2 Module map

> **Lưu ý cấu trúc:** Cloudflare Python Workers chỉ bundle các module nằm cùng cấp hoặc bên trong thư mục chứa entry point (src/entry.py) — đặt package ở root sẽ gây `ModuleNotFoundError` khi deploy. Vì vậy toàn bộ package nằm trong `src/`, không phải root.

- `src/api/` — FastAPI routes, entry point HTTP
  - `routes_planning.py` — endpoint cho jarvis-desktop gọi vào khi cần lập kế hoạch (F14)
  - `routes_telegram.py` — webhook nhận message/update từ Telegram Bot API (F11)
- `src/core/` — Logic lõi
  - `llm.py` — Claude API client wrapper (model-agnostic layer, F12), tool calling
  - `planning.py` — Orchestration: nhận yêu cầu → clarify loop (F01, F02) → gọi planning tools → trả kết quả
  - `session.py` — Quản lý session_id cho multi-turn clarify (F02) — lưu trạng thái qua db/, không giữ in-memory (khác jarvis-desktop, vì Worker không giữ process thường trực)
- `src/tools/` — Định nghĩa planning tools mà Claude gọi (tương đương tools/ + core/tool_router.py bên jarvis-desktop nhưng phía server)
  - `base.py` — ToolResult, ToolError (giữ pattern giống jarvis-desktop để nhất quán)
  - `plan_tools.py` — create_plan, get_plans, get_plan_detail, update_subtask, add_subtask, revise_plan (F04-F09)
  - `tool_router.py` — TOOL_DEFINITIONS + execute_tool dispatch
- `src/db/` — Lớp truy cập Supabase
  - `client.py` — Khởi tạo AsyncPostgrestClient, wrapper các thao tác CRUD cơ bản
  - `models.py` — Định nghĩa schema plan/subtask (Pydantic models dùng chung cho API + DB layer)
- `src/clients/` — Logic đặc thù từng kênh client bên ngoài
  - `telegram.py` — Xử lý message Telegram, gọi Telegram Bot API để trả lời/gửi check-in
- `src/scheduler/` — Proactive check-in cron job (F10)
  - `checkin.py` — Logic chạy khi Cloudflare Cron Trigger kích hoạt, quét plans cần nhắc, gửi qua clients/telegram.py
- `src/config/` — Configuration
  - `settings.py` — Load env vars (ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, v.v.)
- `tests/` — Unit tests

## §3 Request flow (HTTP từ client)

Client (jarvis-desktop hoặc Telegram)
→ api/routes_*.py nhận request
→ core/planning.py orchestrate
→ core/llm.py generate (+ tool calling nếu cần)
→ tools/tool_router.py execute_tool nếu LLM gọi tool
→ db/client.py đọc/ghi Supabase qua PostgREST
→ core/session.py cập nhật session state (nếu đang clarify dở)
→ Trả response về client


## §4 Proactive check-in flow (cron, không phải HTTP)

Cloudflare Cron Trigger (giờ cấu hình sẵn)
→ scheduler/checkin.py
→ db/client.py query plans cần nhắc hôm nay
→ core/llm.py (tuỳ chọn, nếu cần LLM soạn message nhắc thông minh)
→ clients/telegram.py gửi message qua Telegram Bot API


## §5 Data flow patterns

- Mọi truy cập DB đi qua `db/client.py` — không gọi PostgREST trực tiếp ở nơi khác
- LLM call luôn qua `core/llm.py` — model-agnostic, đổi model chỉ sửa config
- KHÔNG giữ conversation/session state trong memory Python — Worker không đảm bảo process sống giữa các request, mọi state phải lưu Supabase qua `core/session.py`
- Mọi response cho client phải qua field text rõ ràng, tương thích cả jarvis-desktop (JSON) và Telegram (text đơn giản)

## §6 Conventions

- Comment tiếng Việt (nhất quán với jarvis-desktop)
- Type hints bắt buộc cho mọi function public
- Pydantic models cho mọi request/response body và DB schema
- Logger qua loguru (nếu tương thích Pyodide — cần xác nhận khi implement; fallback: print có cấu trúc nếu loguru không chạy được trên Workers)
- Mọi config qua `config/settings.py`, không hardcode
- Tool pattern giữ giống jarvis-desktop: ToolResult(success, output) + ToolError — để dễ đối chiếu khi jarvis-desktop gọi sang

## §7 Điểm khác biệt quan trọng so với jarvis-desktop (lưu ý khi code)

- Không có process thường trực — mỗi request là một lần chạy Worker riêng biệt, không giữ state qua các lần gọi (khác `core/pipeline.py` bên jarvis-desktop giữ memory in-process)
- Không dùng driver TCP cho DB — mọi query qua HTTP (PostgREST), cú pháp khác SQL/ORM quen thuộc
- Dev workflow qua WSL, không chạy trực tiếp Windows
