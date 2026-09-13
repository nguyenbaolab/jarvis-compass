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

## D-004 — Model-agnostic LLM layer, MVP dùng Claude Haiku 4.5

**Date:** 2026-09-13
**Status:** Accepted

**Quyết định:** Backend thiết kế theo interface chuẩn OpenAI-compatible để đổi model chỉ bằng đổi API key/endpoint, không đổi code logic. MVP bắt đầu với Claude Haiku 4.5 (rẻ/nhanh), có thể lên Sonnet 4.6 nếu cần reasoning sâu hơn.

**Lý do:**
- Tránh lock-in vào một provider cụ thể, dễ so sánh chất lượng/chi phí giữa các model sau này (kể cả Kimi)
- Haiku đủ rẻ để thử nghiệm nhanh MVP, chưa cần cam kết Sonnet ngay khi chưa rõ độ phức tạp thực tế của use case clarify + decompose

**Trade-off:** Interface trừu tượng hóa có thể bỏ lỡ tính năng đặc thù của từng provider (ví dụ extended thinking riêng của Claude). Chấp nhận vì ưu tiên tính linh hoạt hơn tối ưu sâu cho một model.

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
