# Implementation Plan: Bỏ qua việc con và ghi chú

**Branch**: `005-subtask-skip-note` | **Date**: 2026-10-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-subtask-skip-note/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Lát cắt này làm nốt F07 trong [docs/PRODUCT.md](../../docs/PRODUCT.md): mã `skipped` và tối đa một ghi chú cho mỗi việc con. `SubtaskStatus` thêm `SKIPPED = "skipped"`. `Subtask` thêm `note: str | None` sau `status`, không có giá trị mặc định. Việc con mới vẫn do `new_subtask` dựng, với `note=None`. Bản đã đổi của một việc con đang có đi qua `dataclasses.replace`, không dựng lại `Subtask` bằng tay. Tìm việc con theo `id` và câu `Kế hoạch này không có việc con với danh tính này.` nằm ở một chỗ, dùng chung cho đổi trạng thái và đặt ghi chú. Ghi chú chuẩn hóa bằng `_nfc_strip`; `None`, rỗng, hoặc chỉ khoảng trắng thành `None`. Ghi chú không đổi thì trả đúng object `Plan` cũ và tool không gọi `replace`. Tool mới `set_subtask_note` cùng khuôn `update_subtask`, dùng lại `_MISSING_PLAN_MESSAGE` và `_plan_tool_result`. `SubtaskJson` thêm `note` sau `status`. `Plan` và `PlanStore` không đổi. `MemoryPlanStore` không sửa. Lý do từng lựa chọn nằm ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `src/core/plans.py` chỉ dùng thư viện chuẩn. Lát này thêm `replace` từ `dataclasses` đã import `dataclass`. Không thêm package. JSON thêm trường trên `SubtaskJson` đã có trong `src/tools/schemas.py` (Pydantic 2 qua FastAPI). `ToolResult` và `ToolError` ở `src/tools/base.py`. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

**Storage**: Dùng lại `PlanStore.get` và `PlanStore.replace`. Không thêm phương thức vào `PlanStore` hay `MemoryPlanStore`. Supabase qua PostgREST thuộc F03 và nằm ngoài lát cắt này.

**Testing**: pytest, lệnh `uv run pytest`. Không cần database, `.env`, hay `pywrangler`. Test mới nằm ở `tests/test_subtask_skip_note.py`. Test cũ chỉ sửa ba loại: câu từ chối trạng thái cũ thành câu nêu đủ ba mã; thêm `"note"` vào kỳ vọng JSON của việc con; trong `tests/test_update_subtask.py`, `test_bad_status_wins_before_lookup` bỏ giá trị `"skipped"` khỏi danh sách trạng thái sai. Các giá trị khác trong danh sách đó giữ nguyên. Không xóa test. Không loại sửa nào khác. “Không ghi lại dữ liệu đã lưu” được chứng minh bằng đếm lần gọi `replace`, theo khuôn `_ReplaceCounter` trong `tests/test_update_subtask.py`, đặt trong file test mới. Không dùng phép so object. Danh sách ca nằm ở [quickstart.md](./quickstart.md).

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã sẽ nằm trong Cloudflare Python Workers khi được gọi sau này. Lát cắt này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần đặt ghi chú hoặc đổi trạng thái là một lần `get`, rồi `replace` chỉ khi object `Plan` trả về khác object đã đọc. Hàm không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011 trong [docs/DECISIONS.md](../../docs/DECISIONS.md): luật miền và cổng ở core, tool là lớp mỏng, core không import tools. Không store tầm module. Không driver database. Type hint cho hàm public. Comment tiếng Việt. `note` không có giá trị mặc định. Không thêm thư viện. Không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md). Chiều phụ thuộc: `src/tools/` import `src/core/`; `src/core/` không import `src/tools/`.

**Scale/Scope**: Một hàm tool public mới `set_subtask_note`. `update_subtask` nhận thêm `skipped` và giữ ghi chú. Mọi tool đọc kế hoạch xuất `note`. Tạo, liệt kê, mở, thêm việc con, và đặt `pending` hoặc `done` giữ hành vi đã chốt, trừ câu trạng thái và trường `note`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Tool trả một kế hoạch hoặc một câu từ chối. Câu từ chối không nêu tên nhân vật AI khác. |
| II. Worker không giữ trạng thái | Đạt | Không thêm store tầm module. Hàm nhận `PlanStore` do người gọi truyền vào. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không mở kết nối database. Ghi bằng `PlanStore.replace` trên store được truyền vào. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Store trong test không phải nguồn sự thật của sản phẩm. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP. Hàm không chờ I/O. |
| VIII. Unit test bắt buộc | Đạt | Kiểm chứng là pytest trên CPython, mô tả ở [quickstart.md](./quickstart.md). |

Thêm `note` và `SKIPPED` là thay đổi model đã được duyệt trong lệnh plan này. `Plan` không đổi. Kiểu của `id`, `title`, và `status` không đổi. Không có cổng constitution nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/skip-and-note.md](./contracts/skip-and-note.md), và [research.md](./research.md).

- `Subtask` thêm `note: str | None` sau `status`, không giá trị mặc định. `SubtaskStatus` thêm `SKIPPED = "skipped"`. `Plan` không thêm trường. Việc con mới đi qua `new_subtask` với `note=None`. Bản đổi của việc đang có đi qua `dataclasses.replace`.
- Câu không có việc con và vòng tìm theo `id` nằm ở một hàm nội bộ. `replace_subtask_status` và `replace_subtask_note` cùng gọi hàm đó. Ghi chú không đổi thì trả đúng object `Plan` đã nhận.
- `set_subtask_note` nhận `store` keyword-only, không có giá trị mặc định. Ba bước chuẩn hóa chạy trước `store.get`. Ghi bằng `replace` đã có, và chỉ khi object mới khác object cũ. `PlanStore` và `MemoryPlanStore` không thêm phương thức. Nguyên tắc II vẫn đạt.
- Lớp tool gọi core, dùng lại `_plan_tool_result` và `_MISSING_PLAN_MESSAGE`. `SubtaskJson.note` luôn có mặt. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`. Chiều phụ thuộc giữ nguyên. D-011 không bị đảo.
- Contract cấm gọi PostgREST, LLM, HTTP, và Telegram. `src/db/` không đổi. Nguyên tắc III, IV, VI vẫn đạt. JSON đi qua `PlanJson`.
- Từ chối là `ToolError`, store không đổi. Thành công là `ToolResult`. Nguyên tắc VIII vẫn đạt. Test cũ chỉ đổi câu trạng thái, khóa `note`, và bỏ `"skipped"` khỏi danh sách trạng thái sai của `test_bad_status_wins_before_lookup`.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/005-subtask-skip-note/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── skip-and-note.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # SKIPPED; note; replace dùng chung; docstring SubtaskStatus và normalize_subtask_status

src/tools/
├── base.py                      # đã có: ToolResult, ToolError; không đổi
├── schemas.py                   # note sau status; Literal["pending", "done", "skipped"]; docstring bỏ "Đúng ba khóa"
└── plan_tools.py                # set_subtask_note; _plan_json truyền note

tests/
├── fakes/
│   └── memory_plan_store.py     # không đổi
├── test_subtask_skip_note.py    # test mới, kể cả _ReplaceCounter
├── test_create_plan.py          # chỉ thêm "note" vào kỳ vọng khóa JSON
├── test_get_plans.py            # chỉ thêm "note" vào kỳ vọng khóa JSON
├── test_get_plan_detail.py      # chỉ thêm "note" vào kỳ vọng khóa JSON
├── test_add_subtask.py          # chỉ thêm "note" vào kỳ vọng khóa JSON
├── test_update_subtask.py       # câu ba mã, khóa "note", bỏ "skipped" khỏi test_bad_status_wins_before_lookup
└── test_health.py               # không đổi
```

`src/tools/tool_router.py`, `src/api/`, `src/db/`, `src/clients/`, `src/scheduler/`, `src/app.py`, và các module `src/core/` khác không nằm trong lát cắt này.

**Structure Decision**: Luật trạng thái và ghi chú nằm ở `src/core/plans.py`. `set_subtask_note` trong `src/tools/plan_tools.py` là lớp mỏng. Hình JSON dùng lại `_plan_json`. `PlanStore` không thêm phương thức.

### Docs cần cập nhật

[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) câu trạng thái đầu file hiện nói logic F04 đến F08 đã có ở core và tools. Khi implement làm xong, câu đó phải nói F07 gồm cả `skipped` và ghi chú, vẫn chưa nối HTTP, LLM hay database. Câu đó hôm nay không viết “chỉ pending hoặc done”.

Trong `docs/` không có câu nào nói việc con chỉ có `pending` hoặc `done`. [docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên. Dòng F07 ở đó đã ghi done/skip/note.

Không sửa file nào trong `specs/003-update-subtask/`. Spec đó giữ làm biên bản.

Docstring cần cập nhật khi implement:

- `src/tools/schemas.py`: câu “Đúng ba khóa”. `Literal` trạng thái thêm `"skipped"`, khớp `SubtaskStatus`.
- `src/core/plans.py`: docstring của `SubtaskStatus` và của `normalize_subtask_status`.

## Giới hạn đã biết

- Đọc cả kế hoạch rồi ghi cả kế hoạch có thể mất một lần ghi khi hai yêu cầu đồng thời. Giới hạn này đã có từ `update_subtask`. Lát này không thêm khóa.
- Store thật ở F03 phải lưu ghi chú trống là NULL, không bao giờ là chuỗi rỗng. Lát này chưa có store đó. Trong bộ nhớ và trong JSON, ghi chú trống là `None` và `null`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
