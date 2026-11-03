# Implementation Plan: Lời hướng dẫn hệ thống phiên bản 2

**Branch**: `011-prompt-version-2` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-prompt-version-2/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`PROMPT_VERSION` thành số nguyên `2`. `SYSTEM_PROMPT` là một chuỗi Python hằng, nguyên văn ở mục dưới, thay cho bốn luật của bản 1. File `src/core/system_prompt.py` không thêm import, không thêm hằng, không thêm hàm, và không đọc file lúc chạy. `src/turns/llm_turn.py` đã gửi `SYSTEM_PROMPT` và ghi `PROMPT_VERSION` vào dòng nhật ký, nên không sửa file đó: log sẽ ghi `prompt_version` `2` khi hằng đổi. Trong `tests/test_llm_turn.py` chỉ đổi tên và thân `test_system_prompt_has_four_laws`. Mọi assertion khác giữ nguyên. `DEFINITIONS_VERSION` giữ `2`.

## Nguyên văn SYSTEM_PROMPT

Đây là cả file `src/core/system_prompt.py` sẽ ghi khi triển khai. Chuỗi hằng gồm cả dòng trống giữa các đoạn và dấu xuống dòng sau câu cuối.

```python
"""Hằng lời hướng dẫn hệ thống. Không đọc file lúc chạy."""

PROMPT_VERSION: int = 2

SYSTEM_PROMPT = """Bạn là JARVIS. Không dùng tên nhân vật nào khác.

Trả lời bằng tiếng Việt.

Khi người dùng chỉ kể việc sắp làm và chưa nhờ lập kế hoạch, không gọi tool. Tóm tắt lại những việc họ vừa nói, rồi hỏi họ có muốn lập kế hoạch không. Ví dụ người dùng nói "Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3": không gọi tool. Luật này không áp khi người dùng báo một việc đã xong hoặc bỏ; trường hợp đó theo đoạn cuối.

Không tự xưng "trợ lý lập kế hoạch".

Câu trả lời là chữ trơn. Không in đậm bằng **. Không dùng tiêu đề mở đầu bằng #. Không dùng bảng. Được đánh số "1." và gạch "- ". Muốn chia ngày thì viết một dòng chữ trơn như "Ngày 1" trước nhóm. Dòng đó không phải tiêu đề việc con.

Tiêu đề việc con do bạn tự đặt không có tiền tố thứ tự như "Ngày 1:", "Tuần 1:", "Bước 1", "1.". Thứ tự là vị trí trong danh sách.

Tiêu đề việc con do bạn tự đặt phải có điểm kết thúc đo được. Không tự đặt việc kiểu thói quen suốt một khoảng thời gian.

Tiêu đề do người dùng tự đưa được giữ nguyên từng chữ. Không viết lại tiêu đề đó để thêm điểm kết thúc hay để gỡ tiền tố.

Không hiện mã kế hoạch hay mã việc con. Không hỏi người dùng mã. Cần mã thì tự tìm bằng get_plans với tên việc. Trong câu trả lời, gọi trạng thái là chưa làm, xong, bỏ qua. Không dùng pending, done, skipped trong câu trả lời. Giá trị trạng thái gửi vào tool là mã trong mô tả tool, không phải chưa làm, xong, hay bỏ qua.

Người dùng báo một việc đã xong hoặc bỏ: gọi get_plans với tên việc họ nói. Khớp đúng một việc thì cập nhật ngay, không hỏi xác nhận. Không khớp hoặc khớp nhiều việc thì hỏi lại. Không đòi bằng chứng.
"""
```

Cụm `trợ lý lập kế hoạch` đứng một lần, trong câu cấm tự xưng. Chuỗi có `get_plans` và không chứa `get_plan_detail`. Chuỗi `get_plans` không chứa `get_plan_detail`. Chuỗi không chứa `Friday`.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Không thêm package. `src/core/system_prompt.py` không import. `src/turns/llm_turn.py` đã import `PROMPT_VERSION` và `SYSTEM_PROMPT`; lát này không sửa file đó.

**Storage**: Không đụng kho, schema, hay migration.

**Testing**: pytest, lệnh `uv run pytest`. Một hàm test đổi tên trong `tests/test_llm_turn.py`. Không gọi mô hình thật, không cần Supabase, không đọc `.env`. Assertion của mọi test khác giữ nguyên, gồm các chỗ so với hằng `PROMPT_VERSION` và `SYSTEM_PROMPT`, và dữ liệu mẫu `prompt_version` `1` trong `tests/test_eval_result.py` cùng `tests/test_eval_score.py`.

**Target Platform**: Hằng chuỗi trong process CPython cho test, và cùng chuỗi đó khi Worker gọi lượt. Lát này không đụng runtime Workers.

**Project Type**: Một hằng của web service. Không có route HTTP mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Không thêm lời gọi mạng. Độ dài chuỗi tăng trong cùng một request đã có.

**Constraints**: Nguyên tắc I và VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-011: không đổi trường hay kiểu của model trong `src/core`. Không sửa `src/turns/`, `src/tools/tool_definitions.py`, adapter Anthropic, cổng, `evals/`, hay migration. Không sửa `docs/` ở bước specify và plan. Không thêm file mã nguồn. Mỗi luật một lần, câu ngắn, tiếng Việt. Luật chữ trơn nêu dấu `**`. Luật tiền tố nêu đúng `"Ngày 1:"`, `"Tuần 1:"`, `"Bước 1"`, `"1."`.

**Scale/Scope**: Hai file mã nguồn. File trong `specs/011-prompt-version-2/` là tài liệu của lát này. `tasks.md` và `allowed-files.txt` không tạo ở bước plan.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

PRODUCT §9 được đồng bộ ở B10 trên cùng branch 011-prompt-version-2, trước merge; ràng buộc không sửa docs/ chỉ áp cho bước specify và plan.

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Chuỗi mở đầu bằng JARVIS và cấm tên khác. Không có Friday. |
| II. Worker không giữ trạng thái | Đạt | Hằng không giữ hội thoại. |
| III. Database qua PostgREST | Đạt | Không import `src/db` và không sửa truy vấn. |
| IV. LLM qua lớp trung gian | Đạt | Không sửa cổng, adapter, hay `src/turns/`. Lượt đã gửi hằng qua cổng. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Không ghi Google Tasks hay Google Keep. Không đổi schema. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không thêm lời gọi. Không đổi vòng tool. |
| VIII. Unit test bắt buộc | Đạt | Hàm test đang khóa bản 1 được đổi tên và khóa chuỗi con của bản 2. |

Không có cổng nào thất bại.

### Sau Phase 1

Đã đối chiếu [data-model.md](./data-model.md), [contracts/system-prompt.md](./contracts/system-prompt.md), và [research.md](./research.md).

- `Plan` và `Subtask` không thêm trường và không đổi kiểu. Ba mã trạng thái trong kho giữ nguyên. D-011 không bị đảo.
- `src/core/system_prompt.py` vẫn không import. Chiều phụ thuộc giữ nguyên: `src/turns/` import hằng, core không import tools.
- Contract cấm sửa `src/turns/llm_turn.py`, `src/tools/tool_definitions.py`, `evals/`, và adapter. Nguyên tắc III, IV, VI vẫn đạt.
- Dòng nhật ký vẫn tám khóa. `prompt_version` lấy từ hằng, nên thành `2` mà không sửa `src/turns/llm_turn.py:65`. `definitions_version` vẫn là hằng `2` ở `src/turns/llm_turn.py`.
- Nguyên tắc VIII vẫn đạt: một hàm test đọc hằng, không mở mạng. Các assertion còn lại không sửa.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/011-prompt-version-2/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── system-prompt.md
├── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
└── allowed-files.txt    # Tạo ngay sau /speckit-tasks, không tạo ở bước plan
```

### Source Code (repository root)

```text
src/core/
└── system_prompt.py             # PROMPT_VERSION = 2 và SYSTEM_PROMPT nguyên văn ở trên

tests/
└── test_llm_turn.py             # chỉ đổi tên và thân test_system_prompt_has_four_laws
```

`src/turns/`, `src/tools/tool_definitions.py`, `src/clients/`, `src/core/plans.py`, `src/db/`, và `evals/` không nằm trong lát mã này. `docs/` không sửa ở bước specify và plan.

**Structure Decision**: Lời hướng dẫn là hai tên đã có trong `src/core/system_prompt.py`. Không thêm module. Test đọc hai tên đó.

### Chỗ dùng hằng

`src/turns/llm_turn.py` là chỗ dùng duy nhất trong `src/`:

- dòng 17 import `PROMPT_VERSION`, `SYSTEM_PROMPT`
- dòng 65 ghi `"prompt_version": PROMPT_VERSION`
- dòng 145 gửi `system=SYSTEM_PROMPT`

Không sửa ba dòng đó. Test `test_success_log_has_eight_keys_and_keeps_vietnamese` so `logged["prompt_version"] == PROMPT_VERSION`. Test `test_each_call_sends_prompt_and_catalog` so `request.system == SYSTEM_PROMPT`. Hai assertion đó giữ nguyên chữ.

### Docs

Bước specify và plan không sửa `docs/`. [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) vẫn đúng khi nói `system_prompt.py` là hằng prompt và `PROMPT_VERSION`; câu đó không ghim số `1`. Ảnh trong `docs/architecture/` có chữ `PROMPT_VERSION = 1` và là ảnh chụp theo D-016, không sửa cùng thay đổi code. PRODUCT §9 được đồng bộ ở B10 trên cùng branch, trước merge.

`specs/008-llm-tool-turn/` giữ nguyên làm biên bản bản 1.

### Allow list khi tới tasks

`specs/011-prompt-version-2/allowed-files.txt`, mỗi dòng một đường dẫn, dấu `/`:

```text
src/core/system_prompt.py
tests/test_llm_turn.py
specs/011-prompt-version-2/**
```

Không có `*` ở dòng khác. File này chưa tạo ở bước plan.
