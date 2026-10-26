# DECISIONS — Architectural Decision Records

> Format: D-XXX | Ngày | Tiêu đề | Status | Lý do | Supersedes

---

## D-001 — Tách planning service thành repo riêng, không nhét vào jarvis-desktop

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Planning/task-decomposition capability được xây thành project mới hoàn toàn tách biệt (repo riêng, backend cloud-hosted riêng), không phải một module bên trong jarvis-desktop.

**Lý do:**
- jarvis-desktop là voice pipeline local, gắn chặt với một máy Windows cụ thể; planning service cần chạy 24/7 độc lập với máy đó
- Tách repo giúp jarvis-desktop tiếp tục phát triển bình thường mà không bị pha trộn concern
- jarvis-desktop gọi sang planning service như một client, qua một tool mới trong tool_router — không thay đổi kiến trúc pipeline hiện có

**Trade-off:** Thêm một lớp HTTP call, thêm latency cần quản lý (xem D-005). Chấp nhận vì tách biệt concern quan trọng hơn.

---

## D-002 — Một nhân vật JARVIS duy nhất, không tạo AI thứ hai

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Không tạo nhân vật/persona AI riêng cho planning service (không có "Friday" hay tên khác). JARVIS là nhân vật duy nhất xuất hiện trên mọi điểm chạm — voice desktop, Telegram, app mobile sau này.

**Lý do:**
- Người dùng không cần biết/thấy có bao nhiêu service phía sau — giống mô hình Siri: một nhân vật, nhiều service ẩn
- Trải nghiệm nhất quán quan trọng hơn việc phân chia kỹ thuật rõ ràng cho người dùng thấy

**Trade-off:** Cần đảm bảo tone/persona nhất quán giữa response từ jarvis-desktop (local LLM) và jarvis-compass (Claude API) dù hai bên dùng model khác nhau.

---

## D-003 — Không self-host LLM 24/7 trên máy Lenovo cá nhân, dùng Claude API

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Planning service dùng Claude API (cloud) cho phần reasoning nặng, không biến máy Lenovo (đang chạy jarvis-desktop hàng ngày) thành server 24/7 tự host model.

**Lý do:**
- Máy Lenovo là laptop cá nhân đang dùng hàng ngày, không phải máy rảnh riêng — biến thành server nghĩa là không bao giờ được tắt/mang đi
- 8GB VRAM sát trần nếu chạy planning model cùng lúc với voice pipeline local
- Chi phí Claude API cho use case planning (không phải voice loop liên tục) rất thấp — ước tính ~2-7 USD/tháng ở mức 15 lượt/ngày tùy model, rẻ hơn nhiều so với hy sinh một laptop
- Đã cân nhắc Kimi K2.5/K2.6 (rẻ hơn Claude 5-20 lần) nhưng chênh lệch tuyệt đối chỉ vài USD/tháng ở scale cá nhân, và Kimi định vị mạnh cho agentic coding hơn là hội thoại clarify ý định — không đáng đánh đổi rủi ro (truy cập ngoài Trung Quốc lằng nhằng, model versioning không ổn định)

**Trade-off:** Phụ thuộc vào uptime/pricing của Anthropic thay vì tự chủ hoàn toàn. Chấp nhận vì chi phí thấp và độ tin cậy cao hơn self-host.

**Revisit khi:** Có test case thực tế để so sánh chất lượng Kimi song song, không quyết định vội theo benchmark chung chung.

---

## D-004 — Model-agnostic LLM layer, MVP dùng Claude Haiku 5.5

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Backend thiết kế theo interface chuẩn OpenAI-compatible để đổi model chỉ bằng đổi API key/endpoint, không đổi code logic. MVP bắt đầu với Claude Haiku 4.5 (rẻ/nhanh), có thể lên Sonnet 4.6 nếu cần reasoning sâu hơn.

**Lý do:**
- Tránh lock-in vào một provider cụ thể, dễ so sánh chất lượng/chi phí giữa các model sau này (kể cả Kimi)
- Haiku đủ rẻ để thử nghiệm nhanh MVP, chưa cần cam kết Sonnet ngay khi chưa rõ độ phức tạp thực tế của use case clarify + decompose

**Trade-off:** Interface trừu tượng hóa có thể bỏ lỡ tính năng đặc thù của từng provider (ví dụ extended thinking riêng của Claude). Chấp nhận vì ưu tiên tính linh hoạt hơn tối ưu sâu cho một model.

**Cập nhật 2026-10-18:** model MVP đổi từ Claude Haiku 4.5 sang Claude Haiku 5.5 (claude-haiku-5-5) vì đã có bản mới. Lý do chọn dòng Haiku cho MVP giữ nguyên.

**Cập nhật 2026-10-26:** lớp LLM là cổng trung lập trong `src/core/llm.py` cộng adapter theo nhà cung cấp (hiện là Anthropic, `src/clients/anthropic_model.py`), thay cho câu interface chuẩn OpenAI-compatible.

---

## D-005 — Latency budget khi jarvis-desktop gọi sang jarvis-compass

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Gọi HTTP từ jarvis-desktop sang jarvis-compass phải nằm trong ngân sách latency hiện có của jarvis-desktop (≤3s voice-in → voice-out, theo REQUIREMENTS §5 của jarvis-desktop), không được phá vỡ target này.

**Lý do:**
- jarvis-desktop đã có target latency riêng từ trước (D-005/REQUIREMENTS §5 của jarvis-desktop); thêm một dependency network mới không được làm xấu UX hiện có
- Việc dùng streaming response (F13) giúp giảm cảm nhận độ trễ dù network round-trip có tồn tại

**Trade-off:** Có thể cần thiết kế timeout/fallback rõ ràng khi planning service phản hồi chậm hoặc lỗi — chưa chốt chi tiết cơ chế fallback, để implement sau.

---

## D-006 — Bỏ Google Tasks/Keep khỏi MVP, tự build database riêng

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Không dùng Google Keep hay Google Tasks làm storage chính. Database riêng của jarvis-compass là single source of truth cho plans/subtasks.

**Lý do:**
- Google Keep: không có API chính thức đầy đủ, chỉ thư viện không chính thức, dễ bị Google chặn access
- Google Tasks: có API chính thức ổn định nhưng giới hạn chỉ 1 cấp subtask, không có priority/label, và quan trọng nhất — recurring task không lưu lịch sử hoàn thành (tick xong chỉ dịch due date sang lần kế tiếp, ghi đè cùng một task, không tạo record mới), mâu thuẫn với nhu cầu theo dõi tiến độ lâu dài
- Tự build tránh giới hạn của Tasks, giảm một lớp phụ thuộc bên ngoài (OAuth, quota, sync conflict)

**Trade-off:** Không có sẵn UI xem task quen thuộc như Google Tasks app. Có thể bù bằng one-way sync database → Tasks (display only, F15) ở giai đoạn sau, không phải core kiến trúc.

---

## D-007 — Proactive engagement luôn qua remote push, không bao giờ local-schedule

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Mọi proactive check-in (nhắc việc sáng, hỏi tiến độ tối) phải dùng remote push — server cloud tự giữ đồng hồ, tự chạy cron job độc lập, không phụ thuộc điện thoại/client có mở app hay không. Giai đoạn 1 dùng Telegram Bot API; Giai đoạn 2 (app Android riêng) dùng Firebase Cloud Messaging (FCM), tuyệt đối không dùng AlarmManager/WorkManager cục bộ.

**Lý do:**
- Quan sát thực tế từ app Chino's Store: bug "phải mở app trước 11h thì mới nhận thông báo lúc 11h" là triệu chứng của local scheduling (app tự đặt lịch bằng AlarmManager/WorkManager, chỉ hoạt động nếu app đã từng mở để đăng ký lịch) — không được lặp lại lỗi này
- Telegram app có background service ưu tiên cao từ hệ thống, nhận push ngay cả khi client chưa mở app hôm đó

**Trade-off:** Không có, đây là nguyên tắc bắt buộc không đánh đổi — do đã có tiền lệ lỗi thực tế.

---

## D-008 — Voice UX real-time: streaming turn-based (Mức 1), không audio-to-audio streaming

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Dùng streaming turn-based làm chuẩn thiết kế: STT có VAD tự động dừng ghi âm → gửi text lên Claude API dùng streaming response → TTS đọc từng câu ngay khi có, ghép liên tục → cộng thêm barge-in (ngắt lời JARVIS giữa chừng, dừng và lắng nghe ngay). Không theo đuổi audio-to-audio streaming thực sự (kiểu OpenAI Realtime API, Gemini Live).

**Lý do:**
- Độ trễ cảm nhận ~1-2s đủ tự nhiên cho use case task-oriented (không cần mượt như trò chuyện xã giao)
- Claude API không có sản phẩm audio-to-audio streaming; cần model/nhà cung cấp khác hoàn toàn tách biệt khỏi phần reasoning — phức tạp và tốn kém không tương xứng lợi ích cho use case planning/nhắc việc
- Áp dụng được cho cả jarvis-desktop (giải quyết luôn latency target đang treo ở Phase 2) và app mobile Giai đoạn 2

**Trade-off:** Không đạt độ mượt hội thoại xã giao thời gian thực thật sự. Chấp nhận vì use case chính là task-oriented, không phải trò chuyện phiếm.

---

## D-009 — Tên project: jarvis-compass

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Đặt tên repo/project là `jarvis-compass`.

**Lý do:**
- Giữ tiền tố `jarvis-` nhất quán với `jarvis-desktop`, dễ nhận diện cùng hệ sinh thái
- "Compass" phản ánh đúng chức năng — định hướng, giúp biết nên làm gì tiếp theo — sát với vai trò decompose/lập kế hoạch hơn các gợi ý khác (Ledger, Tempo, Cadence)

**Trade-off:** Tên có thể khiến người ngoài nhầm là sub-module của jarvis-desktop chứ không phải service độc lập 24/7. Chấp nhận vì đây là chi tiết hạ tầng người dùng cuối không thấy (xem D-002).

---

## D-010 — Deploy target: Cloudflare Python Workers; DB access qua PostgREST thay vì driver TCP

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** MVP deploy trên Cloudflare Workers dùng Python Workers runtime (hỗ trợ FastAPI native qua ASGI, chạy trên nền Pyodide/WebAssembly). Database dùng Supabase (Postgres), nhưng truy cập qua **PostgREST** (package `postgrest-py`, HTTP client) thay vì driver TCP trực tiếp (asyncpg/psycopg) — do driver TCP không tương thích Pyodide. Railway được ghi nhận là phương án dự phòng nếu phát sinh vấn đề tương thích khác không giải quyết được.

**Lý do:**
- Cloudflare Workers hỗ trợ Python cấp độ nhất đẳng, FastAPI chạy được không cần patch, giữ nguyên toàn bộ code Python đã quen thuộc từ jarvis-desktop
- Chi phí ở mức traffic thấp (~15 lượt/ngày) có thể gần như miễn phí hoàn toàn trên Cloudflare
- Cold start đã cải thiện mạnh nhờ memory snapshot (~1 giây thay vì ~10 giây)
- Use case F03-F09 (CRUD cơ bản trên plans/subtasks) không cần SQL phức tạp hay transaction phức tạp — PostgREST hoàn toàn đủ, không mất năng lực gì đáng kể so với driver TCP

**Kết quả smoke test (2026-09-13; spike nằm ở commit 8076fef trên nhánh spike/cloudflare-workers-test, không merge vào main; khung app được commit riêng vào main ở 506b1db):**

Môi trường: WSL Ubuntu (uv 0.12.13, Node 22.23.2, wrangler 4.131.1, workers-py 1.17.2, Pyodide cpython-3.14.2-emscripten-wasm32-musl). Lưu ý: `pywrangler dev` KHÔNG chạy được trên Windows native trong môi trường test này (lỗi venv Pyodide + version workers-py cũ hơn yêu cầu Windows) — dev workflow thực tế cho project này cần qua WSL.

- FastAPI cơ bản: chạy được, HTTP 200
- `anthropic` SDK: import + khởi tạo client OK, gọi `messages.create()` ra mạng thật thành công (401 vì test bằng key giả — đúng hành vi kỳ vọng)
- `asyncpg`: FAIL lúc resolve dependency (`pywrangler sync`) — không có wheel WebAssembly tương thích (`cp314`/`wasm32`), môi trường Pyodide bắt buộc `--no-build` nên không compile từ source được
- `psycopg[binary]` và `psycopg2-binary`: cùng fail lý do tương tự (không có wheel platform tag phù hợp)
- `postgrest` (postgrest-py, HTTP client dựa trên httpx): resolve OK, import OK, khởi tạo `AsyncPostgrestClient` OK, gọi `execute()` thất bại với ConnectError/DNS do dùng URL giả trong test — đây là lỗi kỳ vọng (domain không tồn tại), KHÔNG phải lỗi môi trường; Worker không crash ở bất kỳ bước nào

**Kết luận:** Hai dependency quan trọng nhất (LLM call qua anthropic SDK, DB access qua PostgREST) đều xác nhận chạy được. Rào cản duy nhất (driver TCP trực tiếp) có đường vòng hợp lý và không mất năng lực cần thiết cho use case này.

**Trade-off / rủi ro còn lại:**
- Toàn bộ tương tác database phải viết qua REST interface (`postgrest-py`) thay vì SQL/ORM quen thuộc — cần làm quen cú pháp `.from_().select().eq()...` thay vì raw SQL hoặc SQLAlchemy
- Row Level Security (RLS) của Supabase cần cấu hình đúng vì giờ đi qua REST layer có auth riêng (anon/service key), khác cơ chế connection string trực tiếp
- Dev workflow hàng ngày cần qua WSL (không chạy `pywrangler dev` trên Windows native được trong setup hiện tại) — cần xác nhận lại khi upgrade `workers-py` lên bản hỗ trợ Windows tốt hơn (changelog Cloudflare ghi cần workers-py >= 1.72.0 cho Windows, PyPI hiện tại là 1.17.2)
- Tính năng FastAPI-trên-Python-Workers vẫn còn mới, ít tiền lệ thực chiến dài hạn

**Kế hoạch dự phòng:** Nếu phát sinh vấn đề tương thích khác (ví dụ package cần cho F10 cron, hoặc PostgREST không đủ cho nhu cầu query phức tạp hơn về sau), chuyển sang Railway (Hobby $5/tháng) — code logic FastAPI giữ nguyên, chỉ đổi deploy target và cách kết nối DB (có thể quay lại driver TCP thường trên Railway).

**Supersedes:** Bản D-010 trước đó (chưa có kết quả smoke test thực tế).

**Cập nhật 2026-10-26:** nguyên tắc III chỉ áp cho code trong `src/`. Lý do cấm driver TCP là Pyodide, nên ràng buộc thuộc về code chạy trên Worker; helper trong `tests/` chạy trên máy và gọi PostgREST trực tiếp tới kho local (chốt ở bước analyze của F03).

---

## D-011 — Model miền và cổng lưu trữ đặt ở src/core; tool chỉ là lớp mỏng

**Date:** 2026-10-23
**Status:** Accepted

**Bối cảnh:** F04 và F05 cần kiểu Plan, luật chuẩn hóa và cổng lưu trữ. Các tool F06 đến F09 và scheduler F10 cũng sẽ cần chúng.

**Quyết định:** Model miền (Plan, Subtask), luật chuẩn hóa, lọc và cổng PlanStore đặt ở src/core/plans.py, chỉ dùng thư viện chuẩn. src/tools/plan_tools.py là lớp mỏng: gọi core, đổi kết quả thành ToolResult và lỗi miền thành ToolError. Chiều phụ thuộc: tools import core; core không import tools hay db. Bản cài đặt PlanStore thật sẽ nằm ở src/db/ (nguyên tắc III).

**Lý do:**
- Scheduler (F10) và các tool F06 đến F09 dùng lại Plan mà không phải import ngược vào tools.
- Core không phụ thuộc Pydantic hay database, nên test được bằng store giả trong bộ nhớ.

**Phương án đã bỏ:** đặt Plan và PlanStore trong src/tools/. Gọn hơn cho F04 và F05, nhưng scheduler sẽ phải import từ tools.

## D-012 — Cổng PlanStore và tool có lưu trữ là bất đồng bộ

**Date:** 2026-10-25
**Status:** Accepted

**Bối cảnh:** F03 sẽ cài PlanStore bằng PostgREST. Spike khâu 2 (branch spike/supabase-postgrest) chạy được với AsyncPostgrestClient trên Worker; gọi HTTP đồng bộ trên Worker chưa thử.

**Quyết định:** Bốn phương thức của PlanStore là async def. Tool trong src/tools/plan_tools.py có gọi store là async def. Hàm chuẩn hóa và luật miền trong src/core/plans.py giữ đồng bộ. Test chạy hàm async bằng asyncio.run, không thêm plugin pytest.

**Lý do:**
- App chạy qua ASGI; gọi mạng đồng bộ chặn vòng sự kiện trong lúc chờ DB.
- Đổi cổng trước F03, tách khỏi việc cài store thật, để lỗi của hai việc không lẫn nhau.

**Phương án đã bỏ:** giữ cổng đồng bộ và dùng client PostgREST đồng bộ (chưa biết chạy được trên Worker, và chặn request khi chờ DB); thêm pytest-asyncio (thêm dependency trong khi asyncio.run đã đủ).

## D-013 — F03 ghi kế hoạch bằng một RPC PostgREST; trạng thái việc con có CHECK

**Date:** 2026-10-25
**Status:** Accepted

**Bối cảnh:** D-010 chọn PostgREST vì CRUD không cần transaction phức tạp. FR-012 cấm làm mất `created_at` của việc còn danh tính. Mỗi request PostgREST là một transaction riêng, nên nhiều request cho một lần `replace` có thể dừng giữa chừng.

**Quyết định:** `add` và `replace` mỗi cái một hàm SQL, gọi bằng RPC của `postgrest`. Đọc bằng `select`. `status_changed_at` do trigger. Cột `status` có `CHECK (status in ('pending', 'done', 'skipped'))`. CHECK chặn dữ liệu sai từ mọi nơi ghi. Lần đọc vẫn báo trạng thái lạ khi dữ liệu đọc từ kho chứa mã mà bản code đang chạy chưa biết, như khi migration sau thêm mã trong khi code cũ còn đọc. RLS bật; `service_role` được grant; `anon` và `authenticated` không.

**Phương án đã bỏ:** nhiều lời gọi bảng cho một lần `replace`; store tự ghi mốc thời gian; bỏ `CHECK` để ghi một mã lạ vào kho lúc test.

**D-014 — execute_tool là lối vào tool call; log bảy khóa là hợp đồng eval**

**Date:** 2026-10-26

**Status:** Accepted

**Bối cảnh:** Sáu tool đã có. Vòng sau nối LLM vào `execute_tool`. Bộ eval cần một dòng log ổn định.

**Quyết định:** `execute_tool` là lối vào duy nhất cho tool call từ LLM. Dòng log bảy khóa của FR-009 trong spec 007 là hợp đồng cho eval. Đổi khóa thì tăng `DEFINITIONS_VERSION` hoặc ghi quyết định mới. `detail` của lỗi unexpected chỉ là tên lớp exception. Hàm log ném Exception thì bị nuốt và kết quả vẫn trả về, nên eval có thể thiếu dòng log khi kênh log hỏng; catalog hỏng đi đường unexpected.

**Phương án đã bỏ:** ghi thông điệp exception vào `detail` rồi tìm cách che secret. Router không biết giá trị secret.

---

## D-015 — Vòng lượt mô hình ở src/turns; dòng log tám khóa là hợp đồng eval

**Date:** 2026-10-26

**Status:** Accepted

**Bối cảnh:** Cổng mô hình ở `src/core/llm.py` không được import `tools`, trong khi lượt phải gọi `execute_tool`. Bộ eval cần một dòng log cho mỗi lần gọi mô hình, tách khỏi bảy khóa D-014.

**Quyết định:** Vòng lặp của một lượt nằm ở `src/turns`. Dòng log tám khóa của lần gọi mô hình là hợp đồng cho eval. Đổi khóa của dòng log mô hình thì ghi một quyết định mới.

**Phương án đã bỏ:** đặt vòng lặp trong `src/core/llm.py`. Luật import không cho core import tools.

## D-016 — Diagram Archify là ảnh chụp, chỉ cập nhật khi hình dạng kiến trúc đổi

**Date:** 2026-10-26
**Status:** Accepted

**Bối cảnh:** Diagram trong `docs/architecture/` do skill Archify sinh, kiểm nguồn trên một commit đã ghim. Luật "docs sửa cùng thay đổi" khiến mọi vòng tính năng đều phải chạy lại Archify, và bước kiểm B9 báo lệch mỗi khi code đổi. Lần cập nhật sau vòng 8 tốn khoảng 12 phút và 95 đến 100 nghìn token, gấp khoảng 4 lần vòng 7, mà chỉ chép lại code.

**Quyết định:** Diagram là ảnh chụp tại commit đã ghim, không thuộc luật "docs sửa cùng thay đổi". Chỉ cập nhật khi hình dạng kiến trúc đổi: thêm gói hoặc ranh giới mới trong `src/`, nối hai cụm code chưa nối, thêm composition root. Vòng chỉ thêm tool hay sửa logic trong gói có sẵn thì không cập nhật. Khi cập nhật: commit code trước, rồi commit diagram riêng. `docs/ARCHITECTURE.md` vẫn theo luật cũ.

**Lý do:**
- Giá trị chính của Archify là lần chạy đầu và các lần ranh giới đổi; lần chép lại code không cho thêm thông tin.
- B9 không phải báo lệch giả mỗi vòng.

**Phương án đã bỏ:** cập nhật mỗi vòng (tốn thời gian và token, không thêm thông tin); chỉ cập nhật khi viết case study portfolio (diagram cũ quá lâu, mất tác dụng khi duyệt kiến trúc).
