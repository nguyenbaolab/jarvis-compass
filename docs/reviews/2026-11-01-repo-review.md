# Quét repo 2026-11-01

review-base: d32166e

Đọc toàn repo ba lượt, chỉ đọc, ở `main` `d32166e` (sau vòng 10). Mục đích: lần quét sau chỉ đọc phần đã đổi từ mốc này, cộng nhóm xuyên suốt, rồi kiểm lại các mục còn mở. Bằng chứng chi tiết từng mục nằm ở handoff của chat (project Claude), không chép vào đây.

## Phạm vi đã đọc

- Lượt 1, mã chạy thật: toàn bộ `src/` trừ sáu file stub, `supabase/migrations/`, `supabase/config.toml`, `wrangler.jsonc`, `pyproject.toml`, `pylock.toml`, `uv.lock`, `.env.example`, `.gitignore`, `tests/fakes/memory_plan_store.py`, mã postgrest 2.31.0 và httpx 0.28.1 trong `.venv`.
- Lượt 2, test, eval, script: 28 file test, `tests/helpers.py`, `tests/supabase_plan_db.py`, `tests/conftest.py`, `tests/fakes/`, `evals/*.py`, `evals/cases/v1.json`, `evals/datasets/`, `scripts/check.ps1`, `scripts/claude-b9-settings.json`, spec 009.
- Lượt 3, tài liệu so với code: `AGENTS.md`, `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/PRODUCT.md`, `.specify/memory/constitution.md`, `docs/architecture/architecture.json`, `.cursor/skills` (đường dẫn), `specs/001` đến `010`, `evals/results/`.

## Phát hiện

Mức: chặn, nên sửa, ghi nhận. Trạng thái: mở, đã sửa ở (nhánh hoặc commit), đóng (đã kiểm, không có vấn đề).

| ID | Mức | Chỗ | Tóm tắt | Trạng thái |
|---|---|---|---|---|
| L1-01 | nên sửa | src/db/client.py:21-25 | Gọi PostgREST không có timeout; lượt có thể treo quá ngân sách 20 giây | mở (spec độ bền ghi) |
| L1-02 | nên sửa | migration:132-138; src/tools/plan_tools.py | Hai lượt song song mất cập nhật do replace cả kế hoạch, không khóa, không version | mở (spec độ bền ghi) |
| L1-03 | nên sửa | src/turns/llm_turn.py:93-143 | Hết giờ hoặc chạm trần sau khi tool ghi đã xong vẫn trả câu lỗi | mở (spec độ bền ghi) |
| L1-04 | ghi nhận | src/turns/llm_turn.py:114-120 | max_tokens, refusal thành câu lỗi; end_turn text rỗng trả chuỗi rỗng | mở (F11) |
| L1-05 | nên sửa | src/tools/tool_definitions.py:40-77 | set_subtask_note không nói xóa bằng chuỗi rỗng; status không có enum | mở (prompt v2) |
| L1-06 | ghi nhận | src/db/plan_store.py:61-62 | Trạng thái lạ trong kho thành lỗi domain thay vì unexpected | mở |
| L1-07 | ghi nhận | src/core/plans.py:47 | Docstring PlanStore nói không có bản cài đặt trong src/ | đã sửa ở chore/review-fixes-2026-11-01 |
| L1-08 | suy đoán | pylock.toml | pylock khóa pydantic khác uv.lock; Worker có thể chạy bản khác test | mở |
| L2-01 | nên sửa | evals/turn.py:98-121; evals/runner.py:98-101 | Exception ngoài năm mã làm hỏng cả bộ, không ghi file | mở (bộ câu v2) |
| L2-02 | nên sửa | evals/result.py:86-130 | File kết quả không ghi phiên bản bộ chấm hay commit | mở (việc nhỏ runner) |
| L2-03 | nên sửa | tests/test_eval_score.py:196-216 | Sáu tiêu đề trong một lần chấm, chỉ nhánh đầu được kiểm; thiếu ca Markdown `+ ` | đã sửa ở chore/review-fixes-2026-11-01 |
| L2-04 | nên sửa | scripts/check.ps1:339-340 | git diff --name-only dò đổi tên, nguồn của file bị chuyển lọt kiểm | đã sửa ở chore/review-fixes-2026-11-01 |
| L2-05 | nên sửa | scripts/claude-b9-settings.json | git --output và git grep -O ghi file, chạy lệnh dưới dontAsk | đã sửa ở chore/review-fixes-2026-11-01 |
| L2-06 | ghi nhận | scripts/check.ps1:445-447 | Luật Env reads chỉ quét src/turns và adapter | mở (dọn check.ps1) |
| L2-07 | ghi nhận | tests/test_llm_turn.py, test_tool_router.py, test_plan_row_mapping.py | Test khóa đúng hành vi mà L1-04 đến L1-06 muốn đổi | mở |
| L2-08 | ghi nhận | nhiều file test | Khẳng định yếu: chỉ kiểm loại exception, done lặp không đếm replace | mở (dọn) |
| L2-09 | ghi nhận | test_eval_run.py:214; evals/summary.py:109; test_get_plans.py:178 | Tên test hoặc docstring lệch nội dung; chưa có ca từ khóa NFD | mở (dọn) |
| L2-10 | ghi nhận | tests/helpers.py:39-70 và hai file test | Bốn helper kiểm hình dạng kế hoạch gần trùng | mở (dọn) |
| L2-11 | ghi nhận | evals/score.py; evals/load.py:184-193 | Khe bộ chấm cần xét ở bộ câu v2 | mở (bộ câu v2) |
| L2-12 | suy đoán | scripts/check.ps1 | Git for Windows hiểu \s, \b trong git grep -E | đóng (đối chứng dương trên PowerShell) |
| L2-13 | suy đoán | scripts/claude-b9-settings.json | Phiên B9 đọc được .dev.vars bằng công cụ Read | đã sửa ở chore/review-fixes-2026-11-01 (deny Read) |
| L3-01 | nên sửa | scripts/claude-b9-settings.json:15; AGENTS.md:50 | Get-Content * cho B9 đọc .dev.vars; luật AGENTS chỉ trên giấy | đã sửa ở chore/review-fixes-2026-11-01 |
| L3-02 | nên sửa | scripts/claude-b9-settings.json:8, 13 | uv run pytest * cho qua --basetemp (xóa thư mục) và --junitxml | đã sửa ở chore/review-fixes-2026-11-01 |
| L3-03 | ghi nhận | AGENTS.md:41; scripts/check.ps1:2 | "Chỉ đọc" không nói giới hạn của dontAsk; check.ps1 nói không tạo file | đã sửa ở chore/review-fixes-2026-11-01 |
| L3-04 | nên sửa | specs/001, specs/003, specs/009/quickstart.md | Spec cũ nói ngược code, không có dòng trỏ ngược; mọi spec để Status: Draft | một phần: dòng đánh dấu ở chore/review-fixes-2026-11-01; quy ước Status còn mở |
| L3-05 | ghi nhận | docs/ARCHITECTURE.md:76 | Câu "loguru chưa chốt" trong khi log đã chốt không thư viện | đã sửa ở chore/review-fixes-2026-11-01 |
| L3-06 | ghi nhận | docs/DECISIONS.md D-003; docs/PRODUCT.md §5 | Hai con số chi phí; PRODUCT đúng theo giá Haiku 5.5 | mở (cần Starter) |
| L3-07 | ghi nhận | scripts/check.ps1 | Nguyên tắc III không có hàng kiểm; Tools, db, clients thiếu luật import | mở (dọn check.ps1) |
| L3-08 | ghi nhận | constitution, Quy ước mã nguồn | Luật đọc config không ghi phạm vi; tests/ đọc env không có ngoại lệ chính thức | mở (cần Starter) |
| L3-09 | ghi nhận | docs/PRODUCT.md F05 | "Active plans" trong khi kế hoạch không có trạng thái | mở (F10) |
| L3-10 | ghi nhận | docs/DECISIONS.md D-016 | evals/runner.py là composition root ngoài src/; D-016 không nói có tính không | mở (cần Starter) |

## Đã xét, không có vấn đề (ở mốc d32166e)

File nào không đổi từ mốc thì lần sau không cần đọc lại cho các mục này.

- Hướng phụ thuộc D-011 trong `src/`; `core` chỉ thư viện chuẩn.
- MemoryPlanStore so với SupabasePlanStore: id lạ, kho rỗng, thứ tự, replace nguyên tử (một hàm plpgsql).
- Migration so với models: CHECK, FK cascade, RLS, grant chỉ service_role, timestamptz.
- Router kiểm mọi trường đầu vào trước khi gọi tool; log chỉ ghi tên lớp exception; NFC nhất quán.
- Env chỉ đọc ở `config/settings.py` (`TELEGRAM_BOT_TOKEN` là có chủ ý tới F11); không trạng thái cấp module dùng chung.
- Bộ chấm khớp FR-002 đến FR-016 của spec 009; redact; loader; baseline 150/150 scored.
- ARCHITECTURE, constitution I đến IV, D-010 đến D-017, PRODUCT §5 khớp code; mọi đường dẫn trong docs tồn tại.
- Lệnh eval ở AGENTS.md và quickstart 009 khớp runner.
- `evals/results/`: không khóa, JWT, URL, email hay dữ liệu cá nhân; bộ câu v1 là câu dựng sẵn.

## Lần quét sau

Khi nào: `check.ps1` báo hàng `Repo review | due` (từ 15 file `src/` đổi so với `review-base`), trước F11 chạy thật, trước deploy để dùng hằng ngày, trước khi viết case study.

Cách làm:
1. `git diff --stat --no-renames <review-base>..HEAD`, đọc kỹ file đã đổi.
2. Luôn đọc lại nhóm xuyên suốt: `scripts/claude-b9-settings.json`, `scripts/check.ps1`, `AGENTS.md`, constitution, `docs/DECISIONS.md` so với code.
3. Kiểm lại mọi mục còn mở trong bảng trên.
4. Ghi một file mới `docs/reviews/<ngày>-repo-review.md` có dòng `review-base:` mới; file cũ giữ nguyên làm lịch sử.
