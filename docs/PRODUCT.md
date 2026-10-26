# PRODUCT

## §1 Tổng quan

jarvis-compass là planning service cloud-hosted, đóng vai trò "bộ não" lập kế hoạch cho hệ sinh thái JARVIS. Nhận yêu cầu từ bất kỳ client nào (JARVIS desktop, Telegram bot, sau này app mobile), dùng Claude API để decompose/hỏi lại/điều chỉnh plan, lưu trữ tiến độ, và chủ động trigger check-in hàng ngày.

Đây KHÔNG phải một nhân vật AI riêng — JARVIS vẫn là nhân vật duy nhất xuất hiện trên mọi điểm chạm. jarvis-compass là hạ tầng kỹ thuật phía sau, người dùng không thấy, không cần biết (giống Siri: một nhân vật, nhiều service ẩn phía sau).

Repo jarvis-desktop tiếp tục phát triển độc lập, không bị thay thế. jarvis-desktop sẽ gọi sang jarvis-compass qua một tool mới (manage_plan hoặc tên tương tự) khi cần lập kế hoạch — LLM local trong jarvis-desktop chỉ cần đủ giỏi để nhận diện ý định và route, không cần tự lập kế hoạch phức tạp.

Vấn đề cốt lõi cần giải quyết: không phải "AI lập kế hoạch giỏi hay không", mà là engagement hàng ngày — một trợ lý chủ động nhắc việc, đề xuất ưu tiên, nghe phản hồi và điều chỉnh lại kế hoạch, dùng được mọi lúc mọi nơi (không chỉ khi ngồi máy tính).

## §2 Người dùng

- Solo dev (Nguyen Bao) — dùng cá nhân hàng ngày, đồng thời là dự án portfolio.
- Truy cập từ nhiều điểm chạm: máy tính (qua jarvis-desktop), điện thoại (qua Telegram, sau này app Android riêng).

## §3 Feature list

| ID | Tên | Mô tả ngắn |
|----|-----|-----------|
| F01 | Plan creation via clarifying dialogue | Nhận yêu cầu lập kế hoạch, chủ động hỏi lại (scope, deadline, constraints) trước khi chốt plan, không tự đoán khi thiếu thông tin |
| F02 | Multi-turn clarify session tracking | Track trạng thái hội thoại dang dở qua session_id, nối tiếp câu trả lời clarify qua nhiều lượt nói/nhắn |
| F03 | Plan storage (own database) | Lưu plans/subtasks trong database riêng — single source of truth, không sync Google Tasks/Keep |
| F04 | Planning tool — create_plan | Tạo plan mới với goal + subtasks, gọi bởi LLM ở planning service |
| F05 | Planning tool — get_plans | List active plans / tìm theo keyword |
| F06 | Planning tool — get_plan_detail | Xem chi tiết một plan |
| F07 | Planning tool — update_subtask | Done và skip đặt qua update_subtask; note đặt qua set_subtask_note |
| F08 | Planning tool — add_subtask | Thêm subtask vào plan đang có |
| F09 | Planning tool — revise_plan | Xem lại và đề xuất điều chỉnh plan |
| F10 | Proactive check-in (remote push) | Cron job server-side nhắc việc sáng/tối, luôn remote push, không phụ thuộc client có mở app hay không |
| F11 | Telegram Bot interface (MVP client) | Text hoặc voice message (Telegram tự transcribe), nhận scheduled check-in qua Telegram Bot API |
| F12 | Model-agnostic LLM layer | Cổng trung lập và adapter Anthropic |
| F13 | Streaming response + barge-in support | Hỗ trợ streaming response cho client voice (Mức 1 real-time: STT VAD → streaming → TTS từng câu → barge-in) |
| F14 | HTTP API cho jarvis-desktop client | Endpoint để jarvis-desktop gọi sang khi cần lập kế hoạch, qua tool mới trong tool_router |
| F15 | One-way sync to Google Tasks (display only) | Đồng bộ một chiều database → Google Tasks để xem cho tiện, không phải core kiến trúc, không phải MVP |
| F16 | Android app với hardware-key trigger | Giai đoạn 2 — Accessibility Service, Power + Volume Up trigger overlay, nhận push qua FCM |

## §4 Negative scope — cố ý KHÔNG làm

- KHÔNG có nhân vật AI thứ hai (D-002)
- KHÔNG self-host LLM 24/7 trên máy Lenovo cá nhân (D-003)
- KHÔNG dùng Google Keep (D-006)
- KHÔNG dùng Google Tasks làm nơi lưu chính (D-006)
- KHÔNG lên lịch thông báo phía client như AlarmManager hay WorkManager (D-007)
- KHÔNG dùng template kế hoạch cứng trong MVP — LLM-driven trước, đánh giá chất lượng thực tế rồi mới cân nhắc thêm heuristics/template
- KHÔNG theo đuổi audio-to-audio streaming kiểu Realtime API hay Gemini Live (D-008)
- KHÔNG always-listening/wake-word bằng giọng nói trên app mobile Giai đoạn 2 — tốn pin, dễ bị OS kill; dùng hardware-key + Accessibility Service thay thế

## §5 Non-functional requirements

- Cost: MVP dùng Claude Haiku 5.5 (D-004). Ở mức 15 lượt/ngày khoảng 0,1 đến 0,4 USD/tháng, tính từ token đo ở smoke test 2026-10-26 (lượt không tool khoảng 1.500 token, lượt có một lần tool khoảng 5.200 token) theo giá 0,10 USD vào và 0,50 USD ra mỗi triệu token.
- Các yêu cầu còn lại (thông báo chủ động, chạy 24/7, độ trễ khi desktop gọi sang, giữ ngữ cảnh session, đổi model) nằm trong .specify/memory/constitution.md và docs/DECISIONS.md.

## §6 Kiến trúc tổng thể (tham chiếu)

Xem docs/ARCHITECTURE.md §0.

## §7 Versioning

- v0.0.x — MVP development (Telegram bot + core planning tools + proactive check-in)
- v0.1.0 — MVP complete, validated engagement pattern qua Telegram
- v0.2.0 — Android app Giai đoạn 2

## §8 Pending — chưa chốt

- Tên tool cụ thể trong jarvis-desktop tool_router (`manage_plan` hoặc tên khác) — cần viết prompt implement riêng cho jarvis-desktop sau khi jarvis-compass có hình hài cơ bản
