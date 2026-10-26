---
description: "Task list for Điều phối tool kế hoạch"
---

# Tasks: Điều phối tool kế hoạch

**Input**: Design documents from `/specs/007-plan-tool-router/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Viết ba file test trước, chạy, và chép output lần fail vào báo cáo phiên trước khi sửa `src/`. Không sửa assertion test cũ. Không thêm dependency. Test async bằng `asyncio.run`. Không `pytest-asyncio`.

**Organization**: Thứ tự dưới đây là thứ tự thực hiện, không đảo. Ba file test và output fail xong thì mới sửa `src/`. Mutation check xong thì mới bật Supabase và chạy cả bộ. Docs xong thì mới chạy `check.ps1`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1 đến US6). Phase setup, test chung, và phase chốt không gắn story
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Mỗi task chỉ tạo hoặc sửa file có trong `specs/007-plan-tool-router/allowed-files.txt`. Không có task nào sửa file ngoài danh sách đó
- Không sửa `src/core/`, `src/db/`, `src/tools/plan_tools.py`, `src/tools/schemas.py`, `src/tools/base.py`, `src/config/settings.py`, `pyproject.toml`, `docs/PRODUCT.md`, mọi file test đã có
- Không thêm thư viện. Không `jsonschema`. Không dùng Pydantic cho đầu vào
- Không đọc, không ghi `.env` thật và `.dev.vars`. Không ghi `JARVIS_TEST_SUPABASE_URL` hay `JARVIS_TEST_SUPABASE_KEY` vào file nào. Không in khóa ra báo cáo
- Router không import `db`. `execute_tool` nhận `store` qua tham số
- Lệnh `pytest`, `npx`, và `check.ps1` không sửa file nguồn

## Phase 1: Setup

**Purpose**: Danh sách file được phép, trước mọi test và mọi sửa mã

- [x] T001 Tạo `specs/007-plan-tool-router/allowed-files.txt`. Mỗi dòng một đường dẫn tương đối, dấu `/`. Chép đúng tám dòng trong [plan.md](./plan.md) mục "File được tạo hoặc sửa", rồi thêm dòng `specs/007-plan-tool-router/**`. Không dùng `*` ở chỗ khác. Nội dung đúng là:

```text
src/tools/tool_definitions.py
src/tools/tool_router.py
src/app.py
tests/test_tool_router.py
tests/test_app_loads_plan_store.py
tests/test_supabase_plan_store_source.py
docs/ARCHITECTURE.md
docs/DECISIONS.md
specs/007-plan-tool-router/**
```

---

## Phase 2: Foundational (Tests trước mã)

**Purpose**: Ba file test và output lần fail. Chưa sửa `src/`

**⚠️ CRITICAL**: T006 trở đi chỉ bắt đầu sau khi output lần chạy T005 đã nằm trong báo cáo phiên

- [x] T002 [P] Viết `tests/test_tool_router.py` (phụ thuộc T001). Bám [contracts/execute-tool.md](./contracts/execute-tool.md), [contracts/tool-definitions.md](./contracts/tool-definitions.md), và thứ tự phân loại trong [data-model.md](./data-model.md). Dùng `MemoryPlanStore` hoặc kho giả trong chính file test. Không sửa `tests/fakes/memory_plan_store.py`. `asyncio.run`. Không LLM. Ca tên lạ và ca đầu vào sai không gọi phương thức kho. Câu đúng từng ký tự: `Không có tool với tên này.`, `Đầu vào phải là một object.`, `Đầu vào thiếu trường <tên>.`, `Đầu vào thừa trường <tên>.`, `Trường <tên> sai kiểu.`, `Một phần tử của trường subtasks sai kiểu.`, `Không thực hiện được yêu cầu này.` Ca tối thiểu: `create_plan` thiếu `goal` và `subtasks` là `["Học hiragana", null]`; `get_plans` thừa `limit` và `keyword` là số, object rỗng vẫn là liệt kê hết; `get_plan_detail` thiếu `plan_id` và `plan_id` là số; `update_subtask` thiếu `status` và `status` là số; `add_subtask` thiếu `title` và `title` là số; `set_subtask_note` thiếu `note` và `note` là số. `update_subtask` vừa thiếu `status` vừa thừa `limit` ra `Đầu vào thừa trường limit.` `goal` là `""` ra `Mục tiêu không được để trống.` `get_plan_detail` với `"khong-co"` trên kho trống ra `Không có kế hoạch với danh tính này.` `update_subtask` trên một kế hoạch đang có, với `subtask_id` không có, ra đúng `Kế hoạch này không có việc con với danh tính này.` Kho `get` ném `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")` thì `output` đúng câu đó. `RuntimeError` có thông điệp `secret-key-value`: `output` là câu chung, không chứa chuỗi đó và không chứa `RuntimeError`; log `detail` là `RuntimeError`. `KeyboardInterrupt` thoát khỏi `execute_tool`. `get_plans` sau khi kho đã có dữ liệu: `output` trùng lời gọi thẳng tool trên cùng kho. Log: một lần mỗi kết quả, `json.loads` được, `ensure_ascii=False` nên `Học tiếng Nhật` nằm nguyên trong dòng, bảy khóa đúng thứ tự `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`. `definitions_version` là số `1`. `duration_ms` là số nguyên `>= 0` và, khi không bịt đồng hồ, `< 3000`. Bịt `time.monotonic` để thấy làm tròn xuống. `log` truyền vào nhận một `str` không có xuống dòng. Không viết mã trong `src/` ở task này

- [x] T003 [P] Viết `tests/test_app_loads_plan_store.py` (phụ thuộc T001). Không đọc `sys.modules` của tiến trình pytest. Spawn tiến trình con bằng `sys.executable`, thư mục làm việc là gốc repo, `PYTHONPATH` của con là `src`, lệnh là `import app, sys; raise SystemExit(0 if 'db.plan_store' in sys.modules else 1)`. Mã thoát `0` là đạt. Không sửa `tests/test_health.py`. Không sửa `src/app.py` ở task này

- [x] T004 [P] Viết `tests/test_supabase_plan_store_source.py` (phụ thuộc T001). Bám [contracts/store-source.md](./contracts/store-source.md). Không đọc `_url` hay `_key`. Không cần kho chạy. `monkeypatch` đặt sentinel lên `SUPABASE_URL`, `SUPABASE_KEY`, `JARVIS_TEST_SUPABASE_URL`, và `JARVIS_TEST_SUPABASE_KEY`. Trong `db.plan_store`, thay `postgrest_client` bằng hàm ghi `url` và `key` rồi trả async context manager; thay `list_plans` bằng coroutine trả danh sách rỗng. Nguồn dict, và một object có attribute, đủ hai giá trị khác sentinel. Sau `SupabasePlanStore(source)`, `postgrest_client` chưa được gọi. Sau `await store.list_newest_first()`, nó được gọi đúng một lần với `url` và `key` của nguồn, không phải sentinel. Không sửa `src/db/` và không viết lại `test_store_requires_both_settings_before_network`

- [x] T005 Chạy `uv run pytest tests/test_tool_router.py tests/test_app_loads_plan_store.py tests/test_supabase_plan_store_source.py` (phụ thuộc T002, T003, T004). Chép toàn bộ output lần chạy này vào báo cáo phiên trước khi sửa bất kỳ file nào trong `src/`. Kỳ vọng tiến trình fail vì chưa có `execute_tool` và `app.py` chưa import `db.plan_store`. Nếu `tests/test_supabase_plan_store_source.py` đã pass vì constructor có sẵn thì ghi rõ trong báo cáo, không sửa `src/db/` để làm nó fail. Không coi lần chạy này là xong lát

**Checkpoint**: Ba file test đã có. Output fail đã nằm trong báo cáo phiên. `src/` chưa đổi

---

## Phase 3: User Story 5 - Một bộ định nghĩa (Priority: P1)

**Goal**: Sáu tool, mô tả, và schema đầu vào nằm một chỗ, phiên bản số nguyên `1`

**Independent Test**: Đọc catalog một lần. Đủ sáu tên, mỗi mô tả đúng câu trong contract, schema đúng trường bắt buộc và kiểu

- [x] T006 [US5] Tạo `src/tools/tool_definitions.py` (phụ thuộc T005). `DEFINITIONS_VERSION: int = 1`. `TOOL_DEFINITIONS` đúng sáu khóa theo thứ tự và đúng `description` cùng `input_schema` trong [contracts/tool-definitions.md](./contracts/tool-definitions.md). `type` là `object`, `additionalProperties` là `false`, `required` kể cả khi rỗng. `status` không có `enum`. File chỉ dùng thư viện chuẩn. Không import `plan_tools`, `db`, `pydantic`, hay `fastapi`. Không sửa `src/tools/schemas.py`

---

## Phase 4: User Story 1 - Gọi đúng tool (Priority: P1) 🎯 MVP

**Goal**: Tên hợp lệ và đầu vào đúng schema chạy đúng tool trên kho được truyền vào, trả `ToolResult` thành công

**Independent Test**: Với `MemoryPlanStore`, gọi sáu tool bằng đầu vào hợp lệ. Nội dung trùng tool đó trên cùng kho. Không cần mô hình

- [x] T007 [US1] Sửa `src/tools/tool_router.py` (phụ thuộc T006). Thêm `execute_tool(name, tool_input, *, store, log=None) -> ToolResult` đúng chữ ký trong [contracts/execute-tool.md](./contracts/execute-tool.md). Import `tools.tool_definitions`, `tools.plan_tools`, `tools.base`, và từ `core.plans` chỉ `PlanStore` cùng `PlanDomainError`. Không import `db`, `config`, `fastapi`, `pydantic`. Bảng tên sang hàm bằng đúng tập khóa catalog. Đầu vào hợp lệ gọi đúng hàm, bỏ khóa tùy chọn khi không có (`subtasks`, `keyword`). Trả nguyên `ToolResult` khi tool không ném. Task này chưa đủ US2 đến US4; các task sau sửa cùng file

---

## Phase 5: User Story 2 - Đầu vào sai thành lỗi tool (Priority: P1)

**Goal**: Tên lạ, không phải object, thiếu, thừa, hoặc sai kiểu trả một câu nêu trường, không ném `Exception`, không gọi kho

**Independent Test**: Mỗi tool một ca sai kiểu và một ca thiếu trường, trừ `get_plans` dùng ca thừa trường. Không exception thoát ra

- [x] T008 [US2] Sửa `src/tools/tool_router.py` (phụ thuộc T007). Hàm kiểm tự viết đọc schema trong catalog. Chỉ đọc `type`, `properties`, `required`, `additionalProperties`, và `items` của mảng chuỗi. Không `enum`. `string` là `str`. `array` là `list`, phần tử là `str`. Object là `dict`. `None` là sai kiểu. Chuỗi rỗng là đúng kiểu và đi vào tool. Thứ tự: tên không có; không phải `dict`; trường thừa đầu tiên theo thứ tự khóa của `dict` khi `additionalProperties` là `false`; trường thiếu đầu tiên theo `required`; trường sai kiểu đầu tiên theo `properties`, phần tử sai đầu tiên thắng câu phần tử. `success` là `False`. Không gọi kho

---

## Phase 6: User Story 3 - Lỗi miền giữ câu (Priority: P1)

**Goal**: `ToolError` và `PlanDomainError` giữ nguyên câu. `Exception` khác thành câu chung. Không bắt `BaseException`

**Independent Test**: Câu miền đi qua không đổi chữ. Lỗi có secret trong thông điệp không lộ secret. `KeyboardInterrupt` không thành `ToolResult`

- [x] T009 [US3] Sửa `src/tools/tool_router.py` (phụ thuộc T008). Bắt `(ToolError, PlanDomainError)` trước: `output` là `str(error)`, `error_type` là `domain`. Rồi bắt `Exception`: `output` đúng `Không thực hiện được yêu cầu này.`, không thử lại, không đọc `str(error)`. Không bắt `BaseException`

---

## Phase 7: User Story 4 - Một dòng nhật ký (Priority: P1)

**Goal**: Mỗi lần trả `ToolResult` ghi đúng một dòng JSON bảy khóa

**Independent Test**: Năm tình huống đạt, tên lạ, sai kiểu, miền, và unexpected mỗi cái một dòng. Dòng đọc lại đúng đầu vào tiếng Việt

- [x] T010 [US4] Sửa `src/tools/tool_router.py` (phụ thuộc T009). `log` là `None` thì `print(line, flush=True)`. Chuỗi đưa vào `log` là `json.dumps(..., ensure_ascii=False)`, không chứa xuống dòng. Bảy khóa đúng thứ tự trong [data-model.md](./data-model.md). `ok` theo `result.success`. `error_type` là `null` khi đạt. `detail` là `null` trừ `unexpected`; khi đó `detail` chỉ là `type(error).__name__`. `duration_ms` từ `time.monotonic()`, `int(elapsed * 1000)` khi `elapsed > 0`, ngược lại `0`. Đầu vào không dumps được thì khóa `input` của dòng là `null`, và hàm vẫn trả kết quả. Không dùng `default=str`. Không thêm thư viện log

---

## Phase 8: User Story 6 - Nạp module kho cùng ứng dụng (Priority: P1)

**Goal**: `app.py` nạp `db.plan_store` lúc import. Không dựng store và không mở mạng lúc nạp

**Independent Test**: Tiến trình con sạch với `PYTHONPATH=src` import `app` rồi thấy `db.plan_store` trong `sys.modules` của con

- [x] T011 [P] [US6] Sửa `src/app.py` (phụ thuộc T005, song song được với T006 đến T010 vì khác file). Thêm đúng một dòng `import db.plan_store` cạnh các dòng `import db` hiện có. Không sửa dòng nào khác. Không gọi `SupabasePlanStore(...)`. Không đọc cấu hình

- [x] T012 Chạy lại `uv run pytest tests/test_tool_router.py tests/test_app_loads_plan_store.py tests/test_supabase_plan_store_source.py` (phụ thuộc T010, T011). Kỳ vọng cả ba pass, exit code 0, không skip. Fail thì sửa trong các file task T006 đến T011, không sửa test để đổi kỳ vọng và không sửa file ngoài danh sách

**Checkpoint**: Sáu story có mã. Ba file test mới pass. Chưa chạy mutation, chưa chạy cả bộ với Supabase

---

## Phase 9: Mutation check

**Purpose**: Chứng minh test nạp app đỏ khi bỏ import, rồi trả cây về trạng thái có import

- [x] T013 Trong `src/app.py`, bỏ đúng dòng `import db.plan_store` (phụ thuộc T012). Chạy `uv run pytest tests/test_app_loads_plan_store.py`. Kỳ vọng test đỏ, exit code khác 0. Chép output lần đỏ vào báo cáo phiên. Trả lại đúng dòng import ngay sau lần chạy đó, trước mọi task sau. Không commit bản đã bỏ dòng. Chạy lại cùng lệnh và kỳ vọng pass

---

## Phase 10: Cả bộ với Supabase local

**Purpose**: 0 skipped khi kho local đang chạy. Có skip thì dừng, không coi là xanh

- [x] T014 Bật Supabase local rồi chạy cả bộ (phụ thuộc T013). CLI ghim `npx --yes supabase@2.122.0`. Chạy `start` nếu kho chưa chạy, rồi `status -o json`. Đặt `JARVIS_TEST_SUPABASE_URL` bằng `API_URL` và `JARVIS_TEST_SUPABASE_KEY` bằng `SERVICE_ROLE_KEY` trong tiến trình sẽ chạy pytest. Không ghi hai giá trị vào file. Không in khóa ra báo cáo. Host phải là `127.0.0.1` hoặc `localhost`. Chạy `uv run pytest -rs`. Kỳ vọng exit code 0 và dòng tổng kết có 0 skipped. Nếu có bất kỳ skip nào, kể cả `Kho local không chạy`, thì dừng và báo output, không đánh dấu task này xong. Không sửa assertion test cũ. Không sửa file ngoài danh sách được phép

---

## Phase 11: Docs

**Purpose**: ARCHITECTURE đúng ba chỗ, D-014 ở cuối DECISIONS

- [x] T015 [P] Sửa `docs/ARCHITECTURE.md` (phụ thuộc T014). Chỉ ba chỗ trong [plan.md](./plan.md) mục "Docs cần cập nhật khi implement": đoạn trạng thái đầu file; §2 dòng `src/tools/`; §6 thêm một câu về dòng JSON qua hàm ghi, mặc định in một dòng, không thêm thư viện log. Giữ câu loguru chưa chốt. Không sửa mục khác

- [x] T016 [P] Sửa `docs/DECISIONS.md` (phụ thuộc T014). Thêm D-014 vào cuối file, đúng chữ trong [plan.md](./plan.md). Không sửa D-010, D-011, D-012, D-013, hay mục nào khác

---

## Phase 12: Kiểm allow list

**Purpose**: Test, file đổi, và luật import

- [x] T017 Chạy `.\scripts\check.ps1 -AllowList specs/007-plan-tool-router/allowed-files.txt` (phụ thuộc T015, T016). Chép toàn bộ output vào báo cáo phiên. Mã 0 là đạt. Mã khác thì dừng và báo, không sửa file ngoài danh sách để làm lệnh xanh

---

## Dependencies

```text
T001 → T002, T003, T004 → T005 → T006 → T007 → T008 → T009 → T010
T005 → T011
T010 và T011 → T012 → T013 → T014 → T015, T016 → T017
```

US5 xong ở T006. US1 ở T007. US2 ở T008. US3 ở T009. US4 ở T010. US6 ở T011 và T004 (test constructor không cần mã mới trong `src/db`). Không story nào được sửa `src/` trước T005.

## Parallel example

```text
# Sau T001, ba file test cùng lúc:
T002 tests/test_tool_router.py
T003 tests/test_app_loads_plan_store.py
T004 tests/test_supabase_plan_store_source.py

# Sau T005, catalog và import app khác file:
T006 src/tools/tool_definitions.py
T011 src/app.py

# Sau T014, hai file docs:
T015 docs/ARCHITECTURE.md
T016 docs/DECISIONS.md
```

`src/tools/tool_router.py` không song song với chính nó: T007 rồi T008 rồi T009 rồi T010.

## Implementation strategy

MVP sau T007 là gọi được tool hợp lệ trên kho truyền vào, nhưng chưa được dừng ở đó để sửa `src/` khi T005 chưa có output fail. Lát này giao cả sáu story vì một hàm `execute_tool` và một dòng import. Chốt lát là T017 mã 0, và T014 đã có 0 skipped.

Không có task sửa file ngoài `specs/007-plan-tool-router/allowed-files.txt`.
