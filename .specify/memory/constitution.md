<!--
Sync Impact Report
- Version change: 1.0.0 → 1.0.1
- Modified principles: IV. Gọi LLM qua lớp trung gian
- Added sections: none
- Removed sections: none
- Follow-up TODOs:
  - none
-->

# jarvis-compass Constitution

## Core Principles

### I. Một nhân vật duy nhất
Mọi nội dung người dùng thấy đều là JARVIS; không được tạo tên hay persona AI khác (D-002).

### II. Worker không giữ trạng thái
Không lưu session hay hội thoại trong bộ nhớ Python giữa các request; mọi trạng thái phải lưu ở Supabase (D-010).

### III. Truy cập database qua PostgREST
Mọi truy cập DB chỉ qua `src/db/client.py` và chỉ bằng PostgREST (`postgrest-py`); cấm driver TCP như asyncpg hay psycopg (D-010).

### IV. Gọi LLM qua lớp trung gian
Mọi lời gọi LLM đi qua cổng trung lập trong `src/core/llm.py`. SDK của nhà cung cấp chỉ được import trong adapter nằm ngoài `src/core`; model và endpoint đặt trong adapter (D-004, D-015). API key do người gọi truyền vào từ cấu hình runtime; code của lượt và adapter không đọc biến môi trường.

### V. Thông báo chủ động bằng remote push
Mọi thông báo chủ động phải đi bằng remote push từ server (Telegram Bot API, sau này FCM); cấm lên lịch phía client (D-007).

### VI. Database riêng là nguồn sự thật
Database riêng là nguồn sự thật duy nhất cho plan và subtask; Google Tasks và Google Keep không bao giờ là nơi lưu chính (D-006).

### VII. Ngân sách độ trễ với jarvis-desktop
Lời gọi từ jarvis-desktop sang compass phải nằm trong ngân sách độ trễ của desktop: tối đa 3 giây từ lúc nói tới lúc nghe trả lời (D-005).

### VIII. Unit test bắt buộc cho logic
Mỗi thay đổi logic phải có unit test trong `tests/` và chạy qua trước khi coi là xong.

## Ràng buộc kỹ thuật

Stack bắt buộc: Python 3.13+, Cloudflare Python Workers (Pyodide), FastAPI qua ASGI, Supabase qua PostgREST, Claude API, Telegram Bot API; quản lý package bằng uv; `pywrangler dev` chạy trong WSL (D-010).

## Quy ước mã nguồn

Type hints bắt buộc cho mọi function public; Pydantic cho request, response và schema DB; config chỉ đọc qua `src/config/settings.py`; tool dùng mẫu `ToolResult` và `ToolError`; comment tiếng Việt.

## Governance

Constitution đứng trên mọi plan và spec.

Mỗi thông tin chỉ nằm ở một nơi: luật ở constitution này; lý do ở `docs/DECISIONS.md`; sản phẩm là gì ở `docs/PRODUCT.md`; code tổ chức thế nào ở `docs/ARCHITECTURE.md`; từng tính năng ở `specs/`. Không chép thông tin từ nơi này sang nơi khác, chỉ trỏ tới.

Thay đổi nào làm một file docs sai thì phải sửa file đó trong cùng thay đổi.

Sửa một luật thì cập nhật quyết định tương ứng trong `docs/DECISIONS.md`.

**Version**: 1.0.1 | **Ratified**: 2026-10-18 | **Last Amended**: 2026-10-26
