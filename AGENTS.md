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

Ngay sau `/speckit-tasks`: tạo `specs/<thư mục>/allowed-files.txt`, mỗi dòng một đường dẫn tương đối, dấu `/`, gồm mọi file mà `tasks.md` nêu sẽ sửa hoặc tạo, cộng dòng `specs/<thư mục>/**`. Không dùng `*` ở chỗ khác.

## Lệnh

- Cài dependency: `uv sync`
- Test: `uv run pytest`
- Kiểm (test, file thay đổi, luật import): `.\scripts\check.ps1 -AllowList specs/<thư mục>/allowed-files.txt` (mã 0 là đạt, 1 là có mục không đạt, 2 là lỗi cách dùng)
- Phiên kiểm B9 chỉ đọc bằng Claude Code: `claude --settings scripts\claude-b9-settings.json --permission-mode dontAsk` (chưa chạy thử)
- Dev (WSL Ubuntu: `wsl -d Ubuntu`; chạy trước `export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/jarvis-compass` để không đè .venv của Windows): `uv run pywrangler dev`
- Deploy (WSL Ubuntu, cùng biến trên): `uv run pywrangler deploy`. Lần deploy đầu có thể báo lỗi 10007 ở bước bật workers.dev; chạy lại là qua.

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
Báo "xong" phải kèm output thật của `.\scripts\check.ps1 -AllowList specs/<thư mục>/allowed-files.txt`.
