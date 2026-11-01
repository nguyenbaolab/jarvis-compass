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
- Test: `uv run pytest`. Thêm `--fail-on-skip` thì test bị skip làm pytest trả mã 6 (check.ps1 luôn bật cờ này)
- Eval tool-call, từ gốc repo, chưa chạy thử:

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi vào repo>"
uv run python -m evals.runner
```
- Supabase local, ghim `npx --yes supabase@2.122.0`: `init`, `start`, `db reset`, `status`. `status -o json` của bản 2.122.0 in `API_URL` và `SERVICE_ROLE_KEY`. Pytest đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` trong tiến trình, không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Host phải là `127.0.0.1` hoặc `localhost`, nếu không test thất bại trước khi gọi mạng. `db reset` dựng lại lược đồ. Test tự xóa dòng trong `tests/`, không trong `src/`.
- Đặt biến cho pytest trong PowerShell bằng `$s = npx --yes supabase@2.122.0 status -o json | ConvertFrom-Json`, rồi `$env:JARVIS_TEST_SUPABASE_URL = $s.API_URL` và `$env:JARVIS_TEST_SUPABASE_KEY = $s.SERVICE_ROLE_KEY`; phiên Claude Code B9 phải mở từ cùng cửa sổ đó.
- Lệnh Supabase nhắm project cloud luôn ghi `--linked` (`db push --linked`, `migration list --linked`). Từ bản major tới, `db push` không cờ sẽ trỏ DB local.
- Trước `db push --linked` luôn chạy `db push --linked --dry-run` và kiểm danh sách migration.
- Kiểm (test không được skip, file thay đổi, luật import): `.\scripts\check.ps1 -AllowList specs/<thư mục>/allowed-files.txt` (mã 0 là đạt, 1 là có mục không đạt, 2 là lỗi cách dùng)
- Phiên kiểm B9 chỉ đọc bằng Claude Code: `claude --settings scripts\claude-b9-settings.json --permission-mode dontAsk`
- Dev (WSL Ubuntu: `wsl -d Ubuntu`; chạy trước `export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/jarvis-compass` để không đè .venv của Windows): `uv run pywrangler dev`
- Deploy (WSL Ubuntu, cùng biến trên): `uv run pywrangler deploy`. Lần deploy đầu có thể báo lỗi 10007 ở bước bật workers.dev; chạy lại là qua.

## Quy tắc làm việc

- Làm trên branch riêng; không tự commit hay push, người dùng tự commit.
- Thay đổi nào làm một file docs sai thì sửa file đó trong cùng thay đổi.
- Diagram trong `docs/architecture/` không sửa cùng thay đổi code; khi nào cập nhật xem D-016.
- Không đọc và không ghi file `.env` thật và `.dev.vars`; chỉ dùng `.env.example`.
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
