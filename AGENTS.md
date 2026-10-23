# AGENTS.md

## Repo này

Planning service cloud-hosted ("bộ não" lập kế hoạch) cho hệ sinh thái JARVIS: decompose/hỏi lại/điều chỉnh plan, lưu tiến độ, check-in chủ động.

## Đọc trước khi làm

- `.specify/memory/constitution.md` — luật bắt buộc, đứng trên mọi thứ khác
- `docs/PRODUCT.md` — sản phẩm là gì, danh sách tính năng
- `docs/ARCHITECTURE.md` — code tổ chức thế nào
- `docs/DECISIONS.md` — vì sao chọn như vậy
- `specs/` — spec, plan, tasks của từng tính năng (tạo bởi Spec Kit)

Mỗi thông tin chỉ nằm ở một nơi; chỉ trỏ tới, không chép.

## Làm một tính năng

Theo thứ tự: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. Dừng sau mỗi bước để người dùng duyệt.

## Lệnh

- Cài dependency: `uv sync`
- Test: `uv run pytest`
- Dev (bắt buộc trong WSL): `uv run pywrangler dev` (chưa chạy thử)
- Deploy: `uv run pywrangler deploy` (chưa chạy thử)

## Quy tắc làm việc

- Làm trên branch riêng; không tự commit hay push, người dùng tự commit.
- Thay đổi nào làm một file docs sai thì sửa file đó trong cùng thay đổi.
- Không đọc và không ghi file `.env` thật; chỉ dùng `.env.example`.
- Không sửa `.specify/templates/` và `.cursor/skills/` trừ khi được yêu cầu.

## Khi nào dừng và chuyển cho người
Gặp một trong các trường hợp dưới đây thì dừng, không tự xử lý. Dòng đầu tiên của câu trả lời phải đúng là: [DỪNG - CẦN CLAUDE CHAT] <lý do một câu>. Sau đó tóm tắt tình hình kèm output thật của lệnh.
- Hai tài liệu trong repo nói ngược nhau.
- Cần thêm thư viện, dịch vụ hoặc công cụ mới.
- Test chỉ qua khi sửa chính test, bỏ qua hoặc tắt test.
- Thay đổi chạm schema DB hoặc migration, constitution, docs/DECISIONS.md, secret, xác thực, xóa dữ liệu hoặc deploy.
- Thay đổi đi ngược hướng phụ thuộc của D-011, hoặc đổi trường hay kiểu của model trong src/core.
- /speckit-converge quá 3 vòng, hoặc cùng một lỗi quay lại lần thứ hai.
- Lỗi môi trường chưa hiểu (quyền file, khóa git, import runtime). Không nới quyền, không tắt kiểm tra để vượt qua.
Báo "xong" phải kèm output thật của uv run pytest.
