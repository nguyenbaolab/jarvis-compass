# ARCHITECTURE

> Trạng thái code: src/app.py phục vụ /health. Logic F04, F05, F06, và F07 đã có ở src/core/plans.py và src/tools/plan_tools.py, chưa nối HTTP, LLM hay database. Các module và luồng còn lại dưới đây là thiết kế mục tiêu; khi một tính năng làm xong, cập nhật mục liên quan trong cùng thay đổi.

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

> **Lưu ý cấu trúc:** Cloudflare Python Workers chỉ bundle các module nằm cùng cấp hoặc bên trong thư mục chứa entry point (src/entry.py) — đặt package ở root sẽ gây `ModuleNotFoundError` khi deploy. Vì vậy toàn bộ package nằm trong `src/`, không phải root. Chỉ src/entry.py được import workers (runtime Cloudflare); app FastAPI nằm ở src/app.py để test được trên Python thường.

- `src/api/` — FastAPI routes HTTP: endpoint jarvis-desktop lập kế hoạch (F14), webhook Telegram Bot API (F11)
- `src/core/` — Logic lõi: clarify/orchestration (F01, F02); gọi LLM qua `src/core/llm.py` (F12); model miền dùng chung (`Plan`, `Subtask`, `PlanStore`, chuẩn hóa NFC) ở `src/core/plans.py`
- `src/tools/` — Planning tools phía server (F04–F09) và dispatch tool; `plan_tools` là lớp mỏng gọi core
- `src/db/` — Truy cập Supabase qua `src/db/client.py`
- `src/clients/` — Kênh client ngoài: Telegram Bot API (trả lời / check-in)
- `src/scheduler/` — Proactive check-in cron (F10)
- `src/config/` — Configuration qua `src/config/settings.py`
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

- Mọi response cho client phải qua field text rõ ràng, tương thích cả jarvis-desktop (JSON) và Telegram (text đơn giản)
- Luật về DB, LLM và trạng thái: xem constitution, nguyên tắc II đến IV.

## §6 Logging

- Chưa chốt: loguru chưa chắc chạy được trên Pyodide (chưa có trong pyproject.toml); kiểm khi làm tính năng đầu tiên cần log. Các quy ước code khác: xem constitution, mục Quy ước mã nguồn.

## §7 Điểm khác biệt quan trọng so với jarvis-desktop (lưu ý khi code)

Khác biệt với jarvis-desktop: xem constitution nguyên tắc II, III và docs/DECISIONS.md D-010.
