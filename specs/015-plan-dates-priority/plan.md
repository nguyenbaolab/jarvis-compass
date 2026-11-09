# Implementation Plan: Ngày, ưu tiên và sức của kế hoạch

**Branch**: `015-plan-dates-priority` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-plan-dates-priority/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Kế hoạch có ưu tiên. Việc con có ngày lịch và sức. Hạn của kế hoạch là ngày muộn nhất trong các việc chưa làm có ngày. Đổi từ một ngày sang một ngày khác thì có một dòng lịch sử, do SQL chèn trong `replace_plan`. Ưu tiên ghi lúc tạo qua `add_plan`, và lúc sửa qua `plan_fields` của `replace_plan`. Mô hình nhận ngày hôm nay qua một dòng ghép vào lời hướng dẫn. Mốc nằm trên ngữ cảnh của một lần `run_turn`, cùng chỗ với cờ đã báo trùng. Chín tool. Lời hướng dẫn bản 7. Digest và `/next` thêm đoạn ngày do code dựng. Eval có bộ câu v2, ca trùng chạy hai lượt, và vẫn chạy bộ v1 để so với p3-d2.

Lựa chọn và lý do ở [research.md](./research.md). Cột và RPC ở [data-model.md](./data-model.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Giữ FastAPI, `postgrest`, `httpx`, `anthropic`, `zoneinfo`. Không thêm thư viện.

**Storage**: Supabase qua PostgREST, chỉ từ `src/db/client.py`. Một migration mới: cột `plans.priority`, `subtasks.scheduled_on`, `subtasks.effort`, bảng `subtask_date_moves`. `add_plan` thêm `priority text DEFAULT NULL` sau khi bỏ chữ ký hai tham số. `replace_plan` thêm `plan_fields`, `move_reason` và `moved_at`, cả ba `DEFAULT NULL`, sau khi bỏ chữ ký bốn tham số. Không sửa migration đã có.

**Testing**: `uv run pytest`. Logic miền, chữ prompt, digest, chấm v1, và đồ giả lịch sử không cần mạng. Test kho cần Supabase local. Eval là hai lệnh tay, không phải pytest. Danh sách ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython cho pytest. Worker qua `src/entry.py`. Không deploy ở implement. Đẩy cloud là thủ tục ở quickstart, sau khi chat duyệt migration.

**Project Type**: Web service. Thêm ba tool. Không thêm route. Không thêm cron.

**Performance Goals**: Một chủ bot. Ngân sách lượt 20 giây của D-021 giữ nguyên. Ước lượng token vào tăng khoảng 10% đến 20% so với 732.676 của p3-d2. Số đo là lần chạy eval v1.

**Constraints**: Nguyên tắc I đến VIII. D-011: core chỉ thư viện chuẩn. D-021: khóa version và bản ghép. Kết quả trùng không vào bản ghép. D-022: không có người dùng trên dòng lịch sử, và lịch sử lượt sau chỉ là tin chữ. D-023: RPC trả giá trị, không void. `add_plan` vẫn trả object. `replace_plan` vẫn trả boolean. D-024: không làm quét tải, không ưu tiên riêng của việc con, không form. D-025: không đụng digest cron. D-016: không sửa diagram. `instant` của `run_turn` không có mặc định. `src/tools` không import `db`.

**Scale/Scope**: Một chủ bot. Chín tool. Bộ câu v1 giữ cách chấm. Bộ câu v2 thêm các ca đã chốt trong spec.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

- **I. Một nhân vật**: lời hướng dẫn bản 7 giữ câu JARVIS. Không persona mới. Đạt.
- **II. Worker không giữ trạng thái**: ngày, ưu tiên, sức và lịch sử ở Supabase. `TurnContext`, gồm mốc và cờ đã báo trùng, chỉ sống trong một lần gọi `run_turn` và mất khi request xong. Đạt.
- **III. PostgREST**: ghi và đọc kế hoạch vẫn qua `src/db/client.py`. Test đọc bảng lịch sử bằng PostgREST trong `tests/`. Không driver TCP. Đạt.
- **IV. LLM qua cổng**: không thêm SDK. `run_turn` vẫn gọi `ModelClient`. Đạt.
- **V. Push chủ động**: digest vẫn do cron đã có. Không lịch ở client. Đạt.
- **VI. Database riêng**: không ghi Google Tasks. Đạt.
- **VII. Ba giây của desktop**: không phải đường giọng nói. Ngân sách lượt vẫn 20 giây. Đạt vì không áp VII.
- **VIII. Unit test**: danh sách ca ở quickstart. Đạt khi implement làm đúng danh sách đó.
- **Pydantic**: `PlanJson`, `SubtaskJson`, `PlanRow`, `SubtaskRow` thêm trường. Model miền vẫn dataclass, không Pydantic.
- **Config**: không khóa môi trường mới. Số giờ S/M/L là hằng trong core, không phải env.

### Sau Phase 1

`src/core/clock.py` chỉ thư viện chuẩn. `morning.py` re-export `helsinki_clock` và gọi `weekday_name_vi`. `llm_turn` ghép dòng ngày, dựng `TurnContext`, và không import `db` hay `workers`. Kiểu ngữ cảnh ở `src/tools/base.py`. `src/tools` không import `db`. Lịch sử do SQL trong RPC, không do một đường ghi thứ hai trong Python. `Plan` và `Subtask` thêm trường có mặc định. `PlanStore.add` thêm ưu tiên có mặc định. Gate vẫn đạt. Phần implement đụng schema và model core phải dừng để chat duyệt, theo mục dưới. Đó là cửa của AGENTS.md, không phải lỗi constitution.

## Project Structure

### Documentation (this feature)

```text
specs/015-plan-dates-priority/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── tools.md
│   ├── saved-lines.md
│   └── turn-date.md
├── spec.md
└── checklists/requirements.md
```

`tasks.md` và `allowed-files.txt` không tạo ở bước này.

### Source Code (repository root)

```text
src/core/clock.py                  # mới: helsinki_clock, weekday_name_vi, turn_date_line
src/core/morning.py                # re-export helsinki_clock; render_digest thêm đoạn ngày
src/core/plans.py                  # priority, scheduled_on, effort; hàm hạn, trùng, date_moves; add nhận priority
src/core/system_prompt.py          # PROMPT_VERSION 4, luật mới, hằng không chứa ngày
src/turns/llm_turn.py              # instant bắt buộc; dựng TurnContext; không đọc tên tool
src/tools/base.py                  # TurnContext: instant và cờ đã báo trùng
src/tools/tool_definitions.py      # DEFINITIONS_VERSION 3, chín tool
src/tools/tool_router.py           # boolean, null, object lồng; execute_tool nhận turn, mặc định trống
src/tools/schemas.py               # PlanJson, SubtaskJson
src/tools/plan_tools.py            # ba tool mới; reschedule đọc ngữ cảnh và tự đặt cờ
src/tools/saved_reply.py           # 11 mẫu
src/db/client.py                   # cột select; add_plan priority; replace_plan plan_fields
src/db/models.py                   # PlanRow, SubtaskRow
src/db/plan_store.py               # plan_from_row; replace luôn gửi priority
src/api/telegram_update.py         # truyền now vào run_turn
evals/runner.py                    # đường dẫn bộ câu, mặc định v1
evals/turn.py                      # truyền mốc; ca follow_up chạy hai lượt trên một kho
evals/model.py                     # Case.instant, Case.follow_up, seed ngày sức ưu tiên
evals/load.py                      # đọc khóa mới, khóa vắng là trống
evals/store.py                     # seed vào Subtask và Plan
evals/score.py                     # SCORER_VERSION 2; nhánh v1 giữ nguyên; ca trùng đọc hai ảnh kho
evals/cases/v2.json                # bộ câu mới
tests/fakes/memory_plan_store.py   # danh sách dòng lịch sử
tests/test_llm_turn.py             # đổi tên test prompt
tests/test_morning_text.py         # đoạn ngày
tests/test_eval_score.py           # v1 giống bản 1
supabase/migrations/<mới>.sql      # một file, không sửa file cũ
specs/014-morning-digest/spec.md
specs/014-morning-digest/contracts/digest-text.md
```

`specs/014-morning-digest/tasks.md` không nằm trong danh sách. `docs/DECISIONS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` sửa ở implement sau khi chat viết D-026. Diagram `docs/architecture/` không sửa.

**Structure Decision**: Giữ layout hiện tại. Module đồng hồ mới nằm trong `src/core` vì cả lượt mô hình và digest cần cùng một hàm tên thứ, và core không được import `db`.

## Chạm vùng cần duyệt

Implement không được bắt đầu các mục này trước khi chat duyệt.

- **Migration**. Thêm cột, bảng `subtask_date_moves`, trigger chặn sửa và xóa. Bỏ chữ ký `add_plan(text, jsonb)` rồi tạo lại với `priority` mặc định null. Bỏ chữ ký `replace_plan` bốn tham số rồi tạo lại với `plan_fields`, `move_reason` và `moved_at` mặc định null. `add_plan` vẫn trả object. `replace_plan` vẫn trả boolean. Đây là thay đổi schema. AGENTS.md bắt dừng.
- **Trường model `src/core`**. `Plan.priority`, `Subtask.scheduled_on`, `Subtask.effort`, hai enum, chữ ký `normalize_new_plan`, và `PlanStore.add` thêm `priority` keyword. AGENTS.md bắt dừng khi đổi trường hoặc kiểu trong `src/core`.
- **`docs/DECISIONS.md`**. Chat viết mục D-026 với bảy điểm liệt kê ở [research.md](./research.md) mục 12. Cursor chỉ chép chữ đã duyệt, không tự viết quyết định.
- **Không đụng**. Diagram archify (D-016). `specs/014-morning-digest/tasks.md`. Bốn file migration đã có. `.env` và `.dev.vars`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh. Cửa duyệt ở mục trên là luật repo, không phải ngoại lệ constitution.
