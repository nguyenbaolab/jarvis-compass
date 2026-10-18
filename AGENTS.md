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
- Test: chưa có lệnh test chạy được
- Dev (bắt buộc trong WSL): `uv run pywrangler dev` (chưa chạy thử)
- Deploy: `uv run pywrangler deploy` (chưa chạy thử)

## Quy tắc làm việc

- Làm trên branch riêng; không tự commit hay push, người dùng tự commit.
- Thay đổi nào làm một file docs sai thì sửa file đó trong cùng thay đổi.
- Không đọc và không ghi file `.env` thật; chỉ dùng `.env.example`.
- Không sửa `.specify/templates/` và `.cursor/skills/` trừ khi được yêu cầu.
