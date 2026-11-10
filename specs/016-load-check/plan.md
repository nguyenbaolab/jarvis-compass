# Implementation Plan: Quét tải

**Branch**: `016-load-check` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-load-check/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Khi `create_plan`, `add_subtask` hoặc `reschedule_subtasks` đặt việc chưa làm lên hôm nay hoặc một ngày sau, code cộng giờ mọi việc chưa làm đúng ngày đó. Tổng lớn hơn quỹ thì lần gọi đầu không ghi. Tool dựng câu cảnh báo, cùng kiểu `_clash_text`. Mô hình nói lại câu đó. Chủ bot xác nhận ở lượt sau bằng cờ `confirm` đang có. Cờ `turn.clash_reported` chặn `confirm` trong cùng lượt, cho cả tải và trùng hạn.

Không thêm thư viện. Không migration. Không thêm trường `Plan` hay `Subtask`. Phép cộng, chọn việc dời và chọn ngày đích là hàm thuần trong `src/core/plans.py`. Mọi đọc và ghi kho vẫn qua `src/db/client.py`. Lời gọi ghi vẫn trả giá trị. Khóa `version` giữ nguyên.

Năm điểm bắt buộc:

1. Ba tool nhận `confirm` và `load_moves`. Catalog lên bản 4. Lời hướng dẫn lên bản 8. Chi tiết ở [contracts/tools.md](./contracts/tools.md).
2. Mỗi lần xét tải là một `list_plans`. Bảng đọc thêm và subrequest thêm ở [research.md](./research.md) mục 2. Thân list lớn theo số kế hoạch (Q3-04) và không trả cho mô hình.
3. Câu cảnh báo do tool dựng và khóa ở [contracts/load-warning.md](./contracts/load-warning.md). FR-006 đo bằng tỉ lệ eval bộ v3, không phải bảo đảm 100% trong pytest.
4. Chat viết D-029 trước khi sửa `src/`. Implement sau đó sửa hàng F20 trong `docs/PRODUCT.md` và §2 của `docs/ARCHITECTURE.md`. Điểm dừng ở mục dưới.
5. Ba lô. Hết mỗi lô thì dừng để chat đọc diff. Mỗi lô một đột biến, cách làm ở [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Giữ FastAPI, `postgrest`, `httpx`, `anthropic`, `zoneinfo`. Không thêm thư viện.

**Storage**: Supabase qua PostgREST, chỉ từ `src/db/client.py`. Không migration. `add_plan` vẫn trả object. `replace_plan` vẫn trả boolean và vẫn không được đọc. `version` vẫn tăng 1 trong SQL.

**Testing**: `uv run pytest`. Hàm thuần và ba tool trên `MemoryPlanStore` không cần mạng. Eval là ba lệnh tay. Danh sách ở [quickstart.md](./quickstart.md).

**Target Platform**: CPython cho pytest. Worker qua `src/entry.py`. Không deploy ở implement.

**Project Type**: Web service. Không thêm tool. Không thêm route. Không thêm cron.

**Performance Goals**: Một chủ bot. Ngân sách lượt 20 giây của D-021 giữ nguyên. Một lần xét tải thêm đúng một `list_plans`. Không đọc lại giữa các lần dời của cùng một lần gọi tool.

**Constraints**: Nguyên tắc I đến VIII. D-011: core chỉ thư viện chuẩn. D-021: khóa version và hạn chờ từng lời gọi kho. D-022: không người dùng trên dòng cảnh báo. D-023: không RPC void. D-024: cảnh báo mềm, không tự dời. D-026: dùng lại `confirm` và `clash_reported`. D-027: không gọi routine. D-016: không sửa diagram. `src/tools` không import `db`. `src/core` không import `tools`.

**Scale/Scope**: Một chủ bot. Chín tool. Bộ v1 và bộ v2 giữ cách chấm. Bộ v3 thêm tám ca của User Story 7.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

- **I. Một nhân vật**: lời hướng dẫn bản 8 giữ câu JARVIS. Câu cảnh báo là lời tool, không persona mới. Đạt.
- **II. Worker không giữ trạng thái**: tải tính từ Supabase trong một lần gọi. `TurnContext` vẫn chết khi request xong. Đạt.
- **III. PostgREST**: đọc và ghi vẫn qua `src/db/client.py`. Không driver TCP. Đạt.
- **IV. LLM qua cổng**: không thêm SDK. `run_turn` vẫn gọi `ModelClient`. Đạt.
- **V. Push chủ động**: không lịch mới. Đạt.
- **VI. Database riêng**: không ghi Google Tasks. Đạt.
- **VII. Ba giây của desktop**: không phải đường giọng nói. Ngân sách lượt vẫn 20 giây. Đạt vì không áp VII.
- **VIII. Unit test**: ca hàm thuần, ca câu tool, ca lần gọi đầu không ghi. Đạt khi implement làm đúng [quickstart.md](./quickstart.md).
- **Pydantic**: không trường mới trên `PlanJson`. `load_moves` chỉ là đầu vào tool. Model miền vẫn dataclass.
- **Config**: không khóa môi trường mới. Quỹ là hàm trong core, không phải env.

### Sau Phase 1

Hàm tải nằm trong `src/core/plans.py`, chỉ thư viện chuẩn, không thêm trường. Tool gọi core rồi dựng câu. `list_plans` là đường đọc duy nhất của lần xét tải. Không RPC mới. `Plan` và `Subtask` giữ nguyên kiểu. Gate vẫn đạt.

Cửa AGENTS.md không phải lỗi constitution: trước khi sửa `src/`, chat phải viết D-029. Implement không tự viết `docs/DECISIONS.md`.

## Project Structure

### Documentation (this feature)

```text
specs/016-load-check/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── load-warning.md
│   └── tools.md
├── spec.md
└── checklists/requirements.md
```

`tasks.md` và `allowed-files.txt` không tạo ở bước này.

### Source Code (repository root)

```text
src/core/plans.py                  # day_budget, task_hours, day_load, chọn việc, chọn ngày đích
src/core/system_prompt.py          # PROMPT_VERSION 8
src/tools/plan_tools.py            # ba tool gọi core; câu cảnh báo cạnh _clash_text
src/tools/tool_definitions.py      # DEFINITIONS_VERSION 4; confirm và load_moves
src/tools/tool_router.py           # _create và _add truyền turn, confirm, load_moves
evals/score.py                     # SCORER_VERSION 3; nhánh v1 và v2 giữ nguyên
evals/cases/v3.json                # tám ca
tests/test_llm_turn.py             # khóa lời hướng dẫn bản 8
tests/test_tool_router.py          # khóa catalog bản 4
docs/PRODUCT.md                    # hàng F20, sau khi chat viết D-029
docs/ARCHITECTURE.md               # §2: bản 8, catalog 4, hàm tải
docs/DECISIONS.md                  # chỉ chép D-029 chat đã viết
```

Không sửa `src/db/client.py`, `src/db/models.py`, `src/db/plan_store.py`, migration, hay diagram.

**Structure Decision**: Giữ layout hiện tại. Không module mới. Hàm thuần vào `plans.py` vì hạn, sức và thứ tự việc đã ở đó.

## Ba tool, hai bản số

`create_plan`, `add_subtask` và `reschedule_subtasks` nhận `load_moves`. Hai tool đầu nhận thêm `confirm`, mặc định false. `reschedule_subtasks` giữ `confirm` đang có. `changes` của lần dời vẫn là lần chủ bot xin. `load_moves` là danh sách đã chốt, có thể nằm ở nhiều kế hoạch.

`DEFINITIONS_VERSION` từ 3 lên 4. `PROMPT_VERSION` từ 7 lên 8. Vẫn chín tool. Schema và đoạn prompt ở [research.md](./research.md) mục 3 và 4, và [contracts/tools.md](./contracts/tools.md).

## Đọc kho

Một lần xét tải bằng một `list_plans`. Ngày đã qua không xét và không đọc thêm. Bảng từng loại lần gọi ở [research.md](./research.md) mục 2.

Tóm tắt phần tăng: `create_plan` có ngày cần xét thêm một subrequest khi vẫn ghi, và đổi subrequest ghi thành subrequest đọc khi lần đầu bị chặn. `add_subtask` và `reschedule_subtasks` không thêm lần đọc. Chúng đổi `get` một kế hoạch thành `list_plans` mọi kế hoạch. Lượt xác nhận có M việc dời thì thêm M lần `replace`. Q3-04: thân `list_plans` không phân trang. Thân đó không vào tin gửi mô hình.

## Câu cảnh báo

Tool dựng câu. Chữ ở [contracts/load-warning.md](./contracts/load-warning.md). Pytest khóa câu tool. FR-006 không được viết thành assert rằng mô hình luôn nói đúng 100%. Bộ v3 đo tỉ lệ nói lại.

## Docs và điểm dừng

Implement không tự viết quyết định.

- **[DỪNG - CẦN CLAUDE CHAT]** Chưa có chữ D-029 thì không sửa `src/` và không sửa `docs/DECISIONS.md`. Chat viết mục đó theo sáu điểm ở [research.md](./research.md) mục 6. Cursor chỉ chép chữ đã duyệt.
- **`docs/PRODUCT.md`**: hàng F20 ở §3. §7 mục 5 gọi tên F20. §8 bỏ quét tải khỏi nhóm chưa cấp số. Sửa ở lô 3, sau khi D-029 đã có chữ.
- **`docs/ARCHITECTURE.md` §2**: chín tool, `DEFINITIONS_VERSION` 4, `PROMPT_VERSION` 8, hàm tải trong `src/core/plans.py`. Sửa ở lô 3.
- **Không đụng**. Diagram (D-016). Constitution. Migration. `.env` và `.dev.vars`.

Không đổi trường hay kiểu của model trong `src/core`, nên cửa "đổi trường model" của AGENTS.md không mở. Cửa schema không mở vì mục [research.md](./research.md) 1 đã cho thấy không cần schema.

## Chia lô

Thứ tự bắt buộc. Không bắt đầu lô sau khi chưa có lời chat cho điểm dừng của lô trước. Mỗi lô một đột biến: chép file, ghi SHA256, sửa một chỗ, thấy test đỏ, hoàn tác, SHA256 khớp. Chỗ sửa ghi ở [quickstart.md](./quickstart.md).

### Lô 1 — Hàm thuần

`src/core/plans.py` và test hàm thuần. Không tool, không prompt, không kho.

**DỪNG:** chat đọc diff `src/core/plans.py` và test mới. Không bắt đầu lô 2 trước khi chat nói tiếp.

### Lô 2 — Ba tool và hai bản số

`plan_tools.py`, `tool_router.py`, `tool_definitions.py`, `system_prompt.py`. Câu tool khớp contract. Lần gọi đầu không ghi khi vượt. Cùng lượt có `confirm` thì không ghi. Lần `replace` thứ hai trở đi của cùng một kế hoạch dựng từ bản đã áp lần trước (research.md mục 2).

**DỪNG:** chat đọc diff lô 2. Không bắt đầu lô 3 trước khi chat nói tiếp.

### Lô 3 — Đo và docs

Bộ v3, một lần chạy lại bộ v1, một lần chạy lại bộ v2. `SCORER_VERSION` 3 với hai nhánh cũ giữ nguyên. `docs/PRODUCT.md` và `docs/ARCHITECTURE.md`. Không sửa `docs/DECISIONS.md` trong lô này.

**DỪNG:** chat đọc diff lô 3 và các file kết quả eval. Không deploy. Không `db push`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh. Cửa D-029 là luật repo, không phải ngoại lệ constitution.
