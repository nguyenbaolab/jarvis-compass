---
description: "Task list for Lời hướng dẫn hệ thống phiên bản 2"
---

# Tasks: Lời hướng dẫn hệ thống phiên bản 2

**Input**: Design documents from `/specs/011-prompt-version-2/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có, và viết trước. Đổi một hàm trong `tests/test_llm_turn.py`, chạy thấy đỏ khi hằng còn bản 1, rồi mới ghi `src/core/system_prompt.py`. Nguyên tắc VIII.

**Organization**: US1 đến US6 là một chuỗi hằng. Không tách task theo từng story. Ba task, đúng thứ tự dưới đây. Không có task song song.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Không dùng. Ba task chạy nối tiếp
- **[Story]**: US1 trên hai task sửa mã, vì một chuỗi phục vụ cả US1 đến US6
- Phase kiểm cuối không gắn story
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- File được sửa chỉ là hai đường dẫn trong `specs/011-prompt-version-2/allowed-files.txt`, cộng dòng `specs/011-prompt-version-2/**`
- Không task nào sửa `docs/`, `src/turns/`, `src/tools/`, `evals/`, hay test khác
- Đồng bộ PRODUCT §9 không nằm trong file này. Làm ở B10, trên cùng branch `011-prompt-version-2`, trước merge
- Không đọc, không ghi `.env` thật và `.dev.vars`
- Không thêm package, không thêm file mã nguồn, không thêm hằng hay hàm

## Phase 1: Setup

**Purpose**: Khóa danh sách file. Không có task sửa mã

`specs/011-prompt-version-2/allowed-files.txt` đã có đúng ba dòng khi file tasks này được tạo. Không tạo thêm task cho file đó.

## Phase 2: Foundational

**Purpose**: Không có task nền. `PROMPT_VERSION` và `SYSTEM_PROMPT` đã có. Không có migration

**Checkpoint**: Hằng vẫn là bản 1. Chưa đổi test

---

## Phase 3: User Story 1 đến 6 - Một lời hướng dẫn phiên bản 2 (Priority: P1) MVP

**Goal**: `SYSTEM_PROMPT` là nguyên văn trong [plan.md](./plan.md) mục Nguyên văn SYSTEM_PROMPT. `PROMPT_VERSION` là `2`. Sáu luật US1 đến US6 nằm trong cùng chuỗi đó

**Independent Test**: `uv run pytest tests/test_llm_turn.py::test_system_prompt_has_six_laws`. US2 đến US6 không có test riêng. Cùng hàm này khóa chuỗi con của từng luật

### Tests

- [x] T001 [US1] Đổi tên `test_system_prompt_has_four_laws` thành `test_system_prompt_has_six_laws` trong `tests/test_llm_turn.py`. Thân mới là đúng danh sách mục Kiểm tra của [contracts/system-prompt.md](./contracts/system-prompt.md): `PROMPT_VERSION == 2`, không chứa `get_plan_detail`, không chứa `Friday`, `trợ lý lập kế hoạch` đếm một lần, và từng chuỗi con trong danh sách đó. Không thêm và không bớt khẳng định. Không sửa hàm nào khác trong file này, gồm các chỗ so `logged["prompt_version"] == PROMPT_VERSION` và `request.system == SYSTEM_PROMPT`. Không sửa `tests/test_eval_result.py` và `tests/test_eval_score.py`. Không sửa `src/core/system_prompt.py` trong task này. Chạy `uv run pytest tests/test_llm_turn.py::test_system_prompt_has_six_laws` từ gốc repo. Kỳ vọng fail, vì hằng còn bản 1. Nếu lệnh này pass, dừng, không ghi đè hằng cho qua

### Implementation

- [x] T002 [US1] Ghi `src/core/system_prompt.py` đúng nguyên văn khối Python trong [plan.md](./plan.md) mục Nguyên văn SYSTEM_PROMPT, kể cả dòng trống giữa các đoạn và dấu xuống dòng cuối chuỗi (phụ thuộc T001). `PROMPT_VERSION` là số nguyên `2`. Không thêm import, hằng, hay hàm. Không sửa file khác. Chạy lại `uv run pytest tests/test_llm_turn.py::test_system_prompt_has_six_laws`. Kỳ vọng pass, exit code 0

**Checkpoint**: Hàm test sáu luật pass. Các hàm khác trong `tests/test_llm_turn.py` chưa bị sửa assertion

---

## Phase 4: Kiểm toàn bộ

**Purpose**: Suite và `check.ps1`. Không sửa mã để đổi số lượng test

- [x] T003 Chạy `uv run pytest` từ gốc repo (phụ thuộc T002). Kỳ vọng 321 test pass, 0 skip, exit code 0. Rồi chạy `.\scripts\check.ps1 -AllowList specs/011-prompt-version-2/allowed-files.txt`. Kỳ vọng exit code 0. Mười hàng sau đều `pass`: Test, Changed files, Core imports, Workers imports, Turns imports, Tools imports, SDK imports, Env reads, Eval tests imports, Eval env reads. Hàng `Repo review` là hàng thông tin, không tính vào mười hàng. Không sửa `docs/`, `src/turns/`, `src/tools/`, `evals/`, hay test khác để đạt các hàng đó

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: Đã xong khi có `allowed-files.txt`. Không chặn T001
- **Foundational**: Không có task
- **Phase 3**: T001 rồi T002. T002 chỉ bắt đầu sau khi T001 đã fail đúng như mô tả
- **Phase 4**: T003 sau T002

### User Story Dependencies

- **US1 đến US6**: Một chuỗi, một hàm test. Không làm story sau bằng một task riêng. US2 đến US6 không phụ thuộc task nào ngoài T001 và T002

### Within Each User Story

- Test viết và fail trước khi ghi hằng
- Không có model, service, hay endpoint mới

### Parallel Opportunities

- Không có. T001, T002, T003 sửa hoặc kiểm cùng lát, theo thứ tự

---

## Parallel Example: User Story 1

Không có task chạy song song.

---

## Implementation Strategy

### MVP

Cả ba task. Tách US1 khỏi các luật còn lại sẽ viết một chuỗi khác với nguyên văn đã duyệt.

1. T001 thấy đỏ
2. T002 thấy hàm test sáu luật xanh
3. T003 thấy 321 test, 0 skip, và mười hàng `pass`

### Incremental Delivery

Không chia lát. Một hằng là cả sáu luật.

### Parallel Team Strategy

Một người, ba task nối tiếp.

---

## Notes

- [P] không dùng
- US2 đến US6 dùng chung T001 và T002
- Không commit trong các task này trừ khi người dùng yêu cầu
- Đồng bộ PRODUCT §9 là B10, không phải task ở đây
