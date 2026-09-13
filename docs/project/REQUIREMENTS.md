# REQUIREMENTS

## §1 Tổng quan

jarvis-compass là planning service cloud-hosted, đóng vai trò "bộ não" lập kế hoạch cho hệ sinh thái JARVIS. Nhận yêu cầu từ bất kỳ client nào (JARVIS desktop, Telegram bot, sau này app mobile), dùng Claude API để decompose/hỏi lại/điều chỉnh plan, lưu trữ tiến độ, và chủ động trigger check-in hàng ngày.

Đây KHÔNG phải một nhân vật AI riêng — JARVIS vẫn là nhân vật duy nhất xuất hiện trên mọi điểm chạm. jarvis-compass là hạ tầng kỹ thuật phía sau, người dùng không thấy, không cần biết (giống Siri: một nhân vật, nhiều service ẩn phía sau).

Repo jarvis-desktop tiếp tục phát triển độc lập, không bị thay thế. jarvis-desktop sẽ gọi sang jarvis-compass qua một tool mới (manage_plan hoặc tên tương tự) khi cần lập kế hoạch — LLM local trong jarvis-desktop chỉ cần đủ giỏi để nhận diện ý định và route, không cần tự lập kế hoạch phức tạp.

Vấn đề cốt lõi cần giải quyết: không phải "AI lập kế hoạch giỏi hay không", mà là engagement hàng ngày — một trợ lý chủ động nhắc việc, đề xuất ưu tiên, nghe phản hồi và điều chỉnh lại kế hoạch, dùng được mọi lúc mọi nơi (không chỉ khi ngồi máy tính).

## §2 Người dùng

- Solo dev (Nguyen Bao) — dùng cá nhân hàng ngày, đồng thời là dự án portfolio.
- Truy cập từ nhiều điểm chạm: máy tính (qua jarvis-desktop), điện thoại (qua Telegram, sau này app Android riêng).

## §3 Feature list

| ID | Tên | Trạng thái | Mô tả ngắn |
|----|-----|-----------|-----------|
| F01 | Plan creation via clarifying dialogue | Planned | Nhận yêu cầu lập kế hoạch, chủ động hỏi lại (scope, deadline, constraints) trước khi chốt plan, không tự đoán khi thiếu thông tin |
| F02 | Multi-turn clarify session tracking | Planned | Track trạng thái hội thoại dang dở qua session_id, nối tiếp câu trả lời clarify qua nhiều lượt nói/nhắn |
| F03 | Plan storage (own database) | Planned | Lưu plans/subtasks trong database riêng — single source of truth, không sync Google Tasks/Keep |
| F04 | Planning tool — create_plan | Planned | Tạo plan mới với goal + subtasks, gọi bởi LLM ở planning service |
| F05 | Planning tool — get_plans | Planned | List active plans / tìm theo keyword |
| F06 | Planning tool — get_plan_detail | Planned | Xem chi tiết một plan |
| F07 | Planning tool — update_subtask | Planned | Đánh dấu done/skip/note cho subtask |
| F08 | Planning tool — add_subtask | Planned | Thêm subtask vào plan đang có |
| F09 | Planning tool — revise_plan | Planned | Xem lại và đề xuất điều chỉnh plan |
| F10 | Proactive check-in (remote push) | Planned | Cron job server-side nhắc việc sáng/tối, luôn remote push, không phụ thuộc client có mở app hay không |
| F11 | Telegram Bot interface (MVP client) | Planned | Text hoặc voice message (Telegram tự transcribe), nhận scheduled check-in qua Telegram Bot API |
| F12 | Model-agnostic LLM layer | Planned | Interface chuẩn OpenAI-compatible, đổi model chỉ bằng đổi API key/endpoint |
| F13 | Streaming response + barge-in support | Planned | Hỗ trợ streaming response cho client voice (Mức 1 real-time: STT VAD → streaming → TTS từng câu → barge-in) |
| F14 | HTTP API cho jarvis-desktop client | Planned | Endpoint để jarvis-desktop gọi sang khi cần lập kế hoạch, qua tool mới trong tool_router |
| F15 | One-way sync to Google Tasks (display only) | Future | Đồng bộ một chiều database → Google Tasks để xem cho tiện, không phải core kiến trúc, không phải MVP |
| F16 | Android app với hardware-key trigger | Future | Giai đoạn 2 — Accessibility Service, Power + Volume Up trigger overlay, nhận push qua FCM |

## §4 Negative scope — cố ý KHÔNG làm

- KHÔNG tách thành nhân vật AI thứ hai (không có "Friday" hay tên riêng khác) — chỉ một nhân vật JARVIS duy nhất trên mọi điểm chạm
- KHÔNG self-host LLM 24/7 trên máy Lenovo cá nhân — máy đó vẫn dùng hàng ngày, không biến thành server
- KHÔNG dùng Google Keep — không có API chính thức đầy đủ, chỉ thư viện không chính thức dễ bị chặn
- KHÔNG dùng Google Tasks làm nguồn lưu trữ chính — giới hạn 1 cấp subtask, không priority/label, và quan trọng nhất: recurring task không lưu lịch sử hoàn thành (ghi đè due date, không tạo record mới), mâu thuẫn với nhu cầu theo dõi tiến độ lâu dài
- KHÔNG dùng local scheduling (AlarmManager/WorkManager) cho bất kỳ proactive notification nào — đã có tiền lệ lỗi ở Chino's Store (chỉ nhận thông báo nếu app từng mở trước giờ hẹn)
- KHÔNG dùng template kế hoạch cứng trong MVP — LLM-driven trước, đánh giá chất lượng thực tế rồi mới cân nhắc thêm heuristics/template
- KHÔNG theo đuổi audio-to-audio streaming thực sự (kiểu OpenAI Realtime API/Gemini Live) — phức tạp và tốn kém không tương xứng lợi ích cho use case planning/nhắc việc
- KHÔNG always-listening/wake-word bằng giọng nói trên app mobile Giai đoạn 2 — tốn pin, dễ bị OS kill; dùng hardware-key + Accessibility Service thay thế

## §5 Non-functional requirements

- Cost: MVP dùng Claude Haiku 4.5; ước tính ~2.2 USD/tháng ở mức 15 lượt/ngày
- Proactive delivery reliability: mọi check-in chủ động phải đến được client bất kể app có đang mở hay không — bắt buộc remote push (Telegram Bot API ở Giai đoạn 1, FCM ở Giai đoạn 2)
- Availability: service chạy 24/7 độc lập với máy Lenovo cá nhân — không phụ thuộc máy có bật hay không
- Voice latency (khi gọi từ jarvis-desktop): giữ trong ngân sách latency hiện có của jarvis-desktop (≤3s voice-in → voice-out, theo REQUIREMENTS §5 của jarvis-desktop) — gọi HTTP sang planning service không được phá vỡ target này
- Session continuity: multi-turn clarify phải giữ đúng ngữ cảnh qua session_id, không mất context giữa các lượt hỏi lại
- Model portability: không hardcode vào một LLM provider cụ thể — đổi model/API key/endpoint không cần đổi kiến trúc

## §6 Kiến trúc tổng thể (tham chiếu)

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

## §7 Versioning

- v0.0.x — MVP development (Telegram bot + core planning tools + proactive check-in)
- v0.1.0 — MVP complete, validated engagement pattern qua Telegram
- v0.2.0 — Android app Giai đoạn 2

## §8 Pending — chưa chốt

- Framework backend cụ thể: FastAPI được đề xuất trước đó, cần xác nhận
- Tên tool cụ thể trong jarvis-desktop tool_router (`manage_plan` hoặc tên khác) — cần viết prompt implement riêng cho jarvis-desktop sau khi jarvis-compass có hình hài cơ bản
