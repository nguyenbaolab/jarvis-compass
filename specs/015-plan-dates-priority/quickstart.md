# Quickstart: kiểm spec 015

Bước plan không chạy các lệnh này. Implement chạy sau khi chat đã duyệt mục "Chạm vùng cần duyệt" trong [plan.md](./plan.md). Không có mã migration đầy đủ ở file này. Chi tiết cột và RPC ở [data-model.md](./data-model.md).

## Pytest

Từ gốc repo, sau khi có mã:

```text
uv run pytest tests/test_llm_turn.py tests/test_morning_text.py tests/test_eval_score.py tests/test_plan_store_contract.py tests/test_tool_router.py
```

Kỳ vọng chính, không phải danh sách test đầy đủ:

- `test_system_prompt_has_version_four_laws` thấy `PROMPT_VERSION` là 4, các câu bản 3 còn, và có luật ngày không vào tiêu đề cùng luật FR-019.
- `render_digest` không nhận mốc. Việc chưa làm đầu có ngày `2026-11-06` thì dòng tiêu đề kết thúc bằng ` (thứ Sáu 06/11)`. Không ngày thì không thêm đoạn. Không chữ quá hạn.
- Ca chấm v1 trên fixture cũ ra cùng kết quả luật với bản chấm 1.
- Đặt ngày lần đầu và bỏ ngày thì không có dòng lịch sử. Đổi từ một ngày sang một ngày khác thì có một dòng. Lần ghi bị từ chối vì version thì không có dòng mới.
- `run_turn` thiếu `instant` thì lỗi. Không có mặc định.
- `execute_tool` không truyền `turn` vẫn chạy sáu tool cũ. `reschedule_subtasks` không có `turn` thì lỗi tool và kho không đổi.
- `run_turn` không rẽ theo tên tool. Cờ đã báo trùng nằm trên `TurnContext` do tool dời ngày đặt.

Test kho local, khi đã có Supabase local và hai biến `JARVIS_TEST_SUPABASE_URL`, `JARVIS_TEST_SUPABASE_KEY` trỏ `127.0.0.1` hoặc `localhost`:

```text
uv run pytest tests/test_supabase_plan_store.py
```

Ca cần thấy:

- Khóa `scheduled_on` vắng trong payload `replace_plan` thì ngày đang lưu còn. JSON null thì ngày thành trống.
- Khóa `effort` vắng thì sức đang lưu còn. JSON null thì sức thành trống.
- `plan_fields` null, hoặc không có khóa `priority`, thì ưu tiên đang lưu còn. Khóa `priority` là JSON null thì ưu tiên thành trống.
- `add_plan` gọi với `priority` thì cột đó có đúng mức. Lời gọi không gửi `priority` thì cột trống.
- Đổi ngày sang ngày khác thì một dòng `subtask_date_moves` xuất hiện trong cùng lần ghi. Sửa hoặc xóa dòng đó thì lỗi.
- Assertion lịch sử lọc theo `plan_id` và `subtask_id` của lần ghi đó. Không đếm tổng số dòng bảng. `empty_plan_tables` xóa `subtasks` rồi `plans` và không xóa được `subtask_date_moves`, vì trigger chặn xóa và không có khóa ngoại. Dọn bảng bằng `db reset`.

Toàn bộ, không được skip:

```text
.\scripts\check.ps1 -AllowList specs/015-plan-dates-priority/allowed-files.txt
```

`allowed-files.txt` tạo ngay sau `/speckit-tasks`, không tạo ở bước plan.

## Eval

Hai lệnh, mỗi lệnh một bộ. Cần `JARVIS_EVAL_ANTHROPIC_KEY` trong môi trường tiến trình, không ghi vào repo. Đặt `PYTHONPATH` là `src` như `AGENTS.md`.

Bộ v1, so với p3-d2 (732.676 token vào, 150 lần). Cách chấm không đổi. Mốc cả lần chạy là `2026-11-06T08:00:00+02:00`.

```text
uv run python -m evals.runner evals/cases/v1.json
```

Bộ v2. Mỗi ca có mốc riêng. Ca trùng có `follow_up`: lượt hai dùng cùng kho. History của lượt hai gồm hai tin chữ của lượt một, tin chủ bot rồi câu trả lời của bot. `follow_up` là tin của lượt hai.

```text
uv run python -m evals.runner evals/cases/v2.json
```

Khi không truyền đường dẫn, runner vẫn đọc `evals/cases/v1.json`.

Cả hai ghi vào `evals/results/`. Chạy v1 trước. File không hậu tố là `p4-d3-<model>-<ngày>.json`. File bộ v2 cùng ngày có hậu tố `-2`. Trường `cases_version` trong JSON là 1 hoặc 2. So tổng token vào của file v1 với 732.676.

Ước lượng trước khi chạy: catalog thêm khoảng +10% đến +20% token vào trên nền đó, ở [research.md](./research.md) mục 11. Bộ v2 khoảng 48 lượt `run_turn` và khoảng 50 đến 70 lần gọi mô hình, vì ca trùng có hai lượt và một lượt có thể có vòng tool. Số lần gọi là ước lượng ở mục 10, không phải kết quả.

## Đẩy cloud

Chỉ sau khi implement xong và chat đã duyệt migration. Ghim CLI `npx --yes supabase@2.122.0`. Lệnh cloud luôn có `--linked`.

1. `db push --linked --dry-run`. Đọc danh sách migration. File mới của spec 015 phải nằm trong danh sách, và không có file lạ.
2. `db push --linked`. Một transaction thêm cột, bỏ chữ ký RPC cũ, và tạo lại `add_plan` cùng `replace_plan`. Tham số mới có `DEFAULT NULL`. Khóa ngày, sức hoặc ưu tiên vắng không xóa giá trị đang lưu.
3. Cửa sổ sau push, trước deploy: Worker bản cũ vẫn gọi `add_plan` với hai tham số và `replace_plan` với bốn tham số. Hai lời gọi đó phải thành công. Ngày, sức và ưu tiên đã lưu phải còn. Worker này không đặt được ba trường mới.
4. Deploy Worker sau push, từ WSL Ubuntu, với `UV_PROJECT_ENVIRONMENT` trỏ venv Linux như `AGENTS.md`: `uv run pywrangler deploy`.

Không deploy Worker bản mới trước bước 2. Bản mới gửi `priority`, `plan_fields`, `move_reason` và `moved_at`. Hàm SQL cũ không có các tên đó và sẽ lỗi.

Sau bước 2, `wrangler rollback` về Worker cũ là an toàn. Luật "khóa vắng thì giữ" giữ ngày, sức và ưu tiên. Worker cũ chỉ không đặt được các trường mới. Rollback DB, nghĩa là gỡ migration, không được hỗ trợ. Không có migration xuống.

Không sửa diagram trong `docs/architecture/`.
