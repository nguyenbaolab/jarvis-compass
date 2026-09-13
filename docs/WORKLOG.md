# WORKLOG

## 2026-09-13 — Project init: scaffold + REQUIREMENTS + DECISIONS

**Bối cảnh:** Khởi tạo jarvis-compass — planning/task-decomposition service cho hệ sinh thái JARVIS, tách riêng khỏi jarvis-desktop, sau buổi brainstorm kiến trúc tổng thể (xem docs/project/DECISIONS.md D-001 đến D-009 cho đầy đủ lý do).

**Đã làm:**
- Recon toàn bộ codebase jarvis-desktop (cấu trúc thư mục, tools/base.py, core/tool_router.py, core/llm.py, config/settings.py, main.py, docs/project/REQUIREMENTS.md + DECISIONS.md + CONTEXT.md, docs/KNOWN_ISSUES.md) để nắm convention trước khi thiết kế project mới
- Scaffold cấu trúc thư mục ban đầu: docs/project/ (CONTEXT, DECISIONS, PATTERNS, PROMPT_TEMPLATES, REQUIREMENTS, WORKFLOW), docs/phases/, docs/WORKLOG_archive/, docs/BLOCKERS.md, docs/CURRENT.md, docs/FUTURE_WORK.md, docs/KNOWN_ISSUES.md, docs/RUNBOOK.md, docs/USER_GUIDE.md, docs/WORKLOG.md, .gitignore, README.md
- Viết đầy đủ docs/project/REQUIREMENTS.md (§1–§8: tổng quan, người dùng, F01–F16, negative scope, NFR, kiến trúc tham chiếu, versioning, pending items)
- Viết đầy đủ docs/project/DECISIONS.md (D-001 đến D-009: tách repo, một nhân vật JARVIS duy nhất, Claude API thay vì self-host, model-agnostic layer + Haiku 4.5 cho MVP, latency budget khi gọi từ jarvis-desktop, bỏ Google Tasks/Keep, remote push bắt buộc, voice UX Mức 1 streaming turn-based, tên project jarvis-compass)

**Còn treo (xem docs/project/REQUIREMENTS.md §8):**
- Deploy target (Railway/Fly.io/Cloudflare Workers) — chưa chốt
- Database (SQLite/Postgres) — chưa chốt
- Framework backend — FastAPI được đề xuất, cần xác nhận
- Tên tool cụ thể trong jarvis-desktop tool_router (manage_plan hoặc tên khác) — cần prompt implement riêng cho jarvis-desktop sau khi jarvis-compass có hình hài cơ bản
