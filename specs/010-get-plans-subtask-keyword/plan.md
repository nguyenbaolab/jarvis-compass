# Implementation Plan: Từ khóa liệt kê khớp tiêu đề việc con

**Branch**: `010-get-plans-subtask-keyword` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-get-plans-subtask-keyword/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`get_plans` giữ một kế hoạch khi từ khóa còn nội dung nằm trong mục tiêu hoặc trong ít nhất một tiêu đề việc con. Luật chữ giữ nguyên: NFC, `casefold`, chuỗi con, không bỏ dấu. Kế hoạch khớp trả nguyên, một lần, mới hơn đứng trước. Hàm thuần đổi tên từ `filter_by_goal_keyword` thành `filter_by_keyword` trong `src/core/plans.py`. Bước NFC rồi `casefold` nằm một lần trong hàm đó. `get_plans` chỉ đổi docstring và tên hàm được gọi. Catalog chỉ đổi câu mô tả FR-009 và `DEFINITIONS_VERSION` thành `2`. Danh sách assertion được sửa là năm chỗ, ghi ở [research.md](./research.md) mục 5. Hai dòng router được người dùng cho sửa cùng lát này: dòng 86 so số cứng `2`, dòng 109 thành đúng câu FR-009. Mọi assertion cũ khác giữ nguyên.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `src/core/plans.py` chỉ dùng thư viện chuẩn đã có, gồm `unicodedata`. Không thêm package. JSON vẫn đi qua `_plans_json` và `PlansJson` đã có. `src/core/plans.py` không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

**Storage**: Đọc bằng `PlanStore.list_newest_first` đã có. Không sửa `PlanStore`, `MemoryPlanStore`, `SupabasePlanStore`, `src/db/`, truy vấn, hay migration.

**Testing**: pytest, lệnh `uv run pytest`. Test mới nằm ở `tests/test_get_plans.py` và dùng `MemoryPlanStore`. Không cần database, `.env`, hay mạng. Năm assertion được sửa như [research.md](./research.md) mục 5. Mọi assertion cũ khác giữ nguyên. Không bỏ test, không tắt test.

**Target Platform**: Logic thuần trong process CPython cho test. Cùng mã chạy trong Cloudflare Python Workers khi được gọi sau này. Lát này không đụng runtime Workers.

**Project Type**: Phần logic tool của một web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần liệt kê là một lần `list_newest_first` rồi một vòng lọc trong bộ nhớ. Hàm lọc không chờ mạng.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011: luật miền ở core, tool là lớp mỏng. Không đổi trường hay kiểu của `Plan` và `Subtask`. Không đổi schema JSON, khóa log, system prompt, `PROMPT_VERSION`, hay `evals/`. Không sửa `docs/PRODUCT.md`. Không sửa spec cũ.

**Scale/Scope**: Một hàm lọc đổi tên và nới chỗ so khớp. Một câu mô tả. Một số phiên bản catalog. Test mới trong một file đã có.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Không có câu người dùng mới. Mô tả tool không nêu tên nhân vật khác. |
| II. Worker không giữ trạng thái | Đạt | Hàm lọc không giữ danh sách. Store vẫn do người gọi truyền vào. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không sửa truy vấn. |
| IV. LLM qua lớp trung gian | Đạt | Không gọi LLM. Không đổi system prompt. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không có lời gọi HTTP mới. Lọc trên danh sách đã trả về. |
| VIII. Unit test bắt buộc | Đạt | Có test mới và năm assertion đổi kỳ vọng. Hai dòng router đã được cho sửa. Các assertion còn lại giữ nguyên. |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/keyword-filter.md](./contracts/keyword-filter.md), và [research.md](./research.md).

- `Plan` và `Subtask` không thêm trường và không đổi kiểu. `note` không tham gia so khớp. Trạng thái việc con không đổi nghĩa.
- `filter_by_keyword` là hàm thuần duy nhất. Hàm lồng NFC + `casefold` dùng cho từ khóa đã chuẩn hóa, mục tiêu, và tiêu đề. `get_plans` chỉ đổi docstring và tên hàm. `PlanStore` không thêm phương thức. Nguyên tắc II vẫn đạt.
- `src/core/plans.py` không import tools hay db. Chiều phụ thuộc giữ nguyên. D-011 không bị đảo.
- Contract cấm sửa `src/db/`, schema, khóa log, prompt, và `evals/`. Nguyên tắc III, IV, VI vẫn đạt.
- Nguyên tắc VIII vẫn đạt: test mới quan sát được bằng pytest và `MemoryPlanStore`. Năm assertion được sửa. Suite được kỳ vọng xanh sau lát này.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/010-get-plans-subtask-keyword/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── keyword-filter.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/core/
└── plans.py                     # đổi tên filter_by_keyword; một chỗ NFC + casefold; xét title

src/tools/
├── plan_tools.py                # docstring get_plans và tên hàm được gọi
├── tool_definitions.py          # câu FR-009 và DEFINITIONS_VERSION = 2
└── schemas.py                   # không đổi

tests/
├── fakes/
│   └── memory_plan_store.py     # không đổi
├── test_get_plans.py            # một assertion cũ đổi kỳ vọng; thêm ca mới
├── test_add_subtask.py          # một assertion trong test_keyword_matches_goal_and_new_title
└── test_tool_router.py          # ba assertion: hằng thành 2, log số cứng 2, câu mô tả FR-009
```

`src/db/`, `src/turns/`, `src/core/system_prompt.py`, và `evals/` không nằm trong lát này.

**Structure Decision**: Luật lọc là `filter_by_keyword` trong `src/core/plans.py`. Tool là lớp mỏng. Catalog chỉ đổi câu mô tả và số phiên bản.

### Chỗ gọi tên cũ

`git grep -n filter_by_goal_keyword` chỉ ra ba dòng, đã liệt kê ở [research.md](./research.md) mục 1. Không có dòng trong `docs/` hay `AGENTS.md`.

### Docs

`git grep -n -E "mục tiêu|goal|keyword|từ khóa|filter_by_goal_keyword" -- docs AGENTS.md` ra bốn dòng. Không câu nào thành sai sau lát này. Chi tiết ở [research.md](./research.md) mục 6. Không sửa `docs/`. Không sửa `AGENTS.md`. Không sửa `docs/PRODUCT.md`.

D-014 không cần dòng "Cập nhật 2026-11-01". Nguyên văn câu căn cứ:

> Đổi khóa thì tăng `DEFINITIONS_VERSION` hoặc ghi quyết định mới.

Lát này không đổi khóa dòng log. Câu đó không đòi một dòng cập nhật khi số phiên bản tăng vì mô tả và luật khớp đổi.

### Năm assertion được sửa

Danh sách nay là năm chỗ, chi tiết ở [research.md](./research.md) mục 5. Người dùng cho sửa cùng lát này đúng hai thay đổi sau, thêm vào ba chỗ đã có:

- `tests/test_tool_router.py:86`: `assert logged["definitions_version"] == 1` thành `== 2`. Giữ so với số cứng, không đổi sang so với hằng.
- `tests/test_tool_router.py:109`: câu mô tả cũ của `get_plans` thành đúng câu FR-009.

Mọi assertion cũ khác giữ nguyên. `tests/test_llm_turn.py:323` vẫn so với hằng. `isinstance` ở dòng 98 không sửa.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
