---
description: "Task list for Lượt trả lời có gọi mô hình"
---

# Tasks: Lượt trả lời có gọi mô hình

**Input**: Design documents from `/specs/008-llm-tool-turn/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Viết test trước mã. Mỗi lượt viết test có một bước `uv run pytest` và in output lần fail trước khi sửa `src/`. Không sửa assertion của test cũ. Không thêm dependency. Test async bằng `asyncio.run`. Không `pytest-asyncio`.

**Organization**: Thứ tự dưới đây là thứ tự thực hiện. Hai lần pytest fail xong thì mới sửa `src/`. Mã xong thì mới sửa docs. Docs xong thì mới chạy `check.ps1`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1 đến US6). Phase setup, test, cổng, và phase chốt không gắn story
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Mỗi task chỉ tạo hoặc sửa file có trong `specs/008-llm-tool-turn/allowed-files.txt`. Không có task nào sửa file ngoài danh sách đó
- Không sửa `src/tools/tool_router.py`, `src/tools/tool_definitions.py`, `src/core/plans.py`, `src/app.py`, `src/clients/telegram.py`, `pyproject.toml`, `uv.lock`, `.env.example`, `docs/architecture/architecture.json`, `docs/architecture/architecture.html`, mọi file test đã có
- Không thêm thư viện. `anthropic` đã có trong dependency chính
- Không đọc, không ghi `.env` thật và `.dev.vars`
- Lượt không import `anthropic`, `db`, hay adapter. Adapter không import `turns` hay `tools`
- Lệnh `pytest` và `check.ps1` không sửa file nguồn

## Phase 1: Setup

**Purpose**: Phạm vi file, trước mọi test và mọi sửa mã

- [x] T001 Phạm vi file của lát này là đúng danh sách cuối [plan.md](./plan.md) mục "File được tạo hoặc sửa", đã ghi vào `specs/008-llm-tool-turn/allowed-files.txt`. Mỗi dòng một đường dẫn tương đối, dấu `/`. Không dùng `*` ngoài dòng thư mục spec. Nội dung đúng là:

```text
src/core/llm.py
src/core/system_prompt.py
src/turns/__init__.py
src/turns/llm_turn.py
src/clients/anthropic_model.py
src/config/settings.py
tests/test_llm_turn.py
tests/test_anthropic_model.py
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/PRODUCT.md
specs/008-llm-tool-turn/**
```

---

## Phase 2: Foundational (Tests trước mã)

**Purpose**: Hai lượt viết test. Mỗi lượt chạy pytest và in output fail. Chưa sửa `src/`

**⚠️ CRITICAL**: T006 trở đi chỉ bắt đầu sau khi output T003 và T005 đã nằm trong báo cáo phiên

- [x] T002 [P] Viết `tests/test_llm_turn.py` (phụ thuộc T001). Bám [contracts/llm-turn.md](./contracts/llm-turn.md), [contracts/model-port.md](./contracts/model-port.md), [contracts/system-prompt.md](./contracts/system-prompt.md), và [data-model.md](./data-model.md). Không import `anthropic`. Client giả có `model: str` và `async def complete`. `asyncio.run`. Không mở mạng. Không sửa test cũ. Bịt `turns.llm_turn._now`, không bịt `time.monotonic`. Kho giả trong file test. Năm hàm riêng, đúng các ca sau:
  - `test_fourth_round_runs_no_tools`: bốn phản hồi liên tiếp, mỗi phản hồi một tool. Ba vòng đầu chạy hết tool. Phản hồi thứ tư không gọi `execute_tool` và không gọi `complete` thêm. Kết quả đúng `Chưa trả lời xong yêu cầu này.`
  - `test_missing_or_empty_key_skips_client`: khóa `None` và khóa `""` ném lỗi có `str` đúng `Thiếu ANTHROPIC_API_KEY.`. Client giả không được gọi. Môi trường tiến trình có khóa khác cũng không được đọc. Chuỗi chỉ khoảng trắng không bị strip và vẫn được đưa vào `complete`
  - `test_budget_stops_further_calls`: đồng hồ bịt cho `_now() - mốc > 20` trước lần gọi tiếp. Kết quả đúng `Chưa liên lạc được để trả lời lúc này.` Không có `complete` sau mốc đó
  - `test_cancelled_error_propagates`: client giả ném `CancelledError`. Lỗi đó đi ra khỏi `run_turn`. Kết quả không phải câu lỗi phía mô hình và không phải câu hết vòng
  - `test_model_error_hides_message`: client giả ném lỗi có `secret-key-value`, `http://example.invalid`, và `429` trong thông điệp. Kết quả đúng `Chưa liên lạc được để trả lời lúc này.` và không chứa ba mảnh đó. Dòng log lấy `model` từ `client.model`, `error_type` là tên lớp, không chứa thông điệp
  - Thêm trong cùng file: lịch sử rỗng, client trả văn bản và không đòi tool, kết quả đúng văn bản đó, kho không bị gọi. Lịch sử một tin `user` rồi một tin `assistant` được gửi đúng thứ tự rồi mới tới tin mới, và list người gọi đưa không bị sửa. Văn bản rỗng là kết quả thành công. Vòng đầu đòi `get_plans` rồi `get_plan_detail`: cả hai chạy theo thứ tự đó, `complete` kế tiếp nhận cả hai kết quả, `output` gửi lại không đổi chữ kể cả khi `success` là false. `execute_tool` nhận đúng `store` và đúng cùng object `log`. `stop_reason` `max_tokens` không chạy tool và không gọi `complete` thêm, và cho một dòng log có `stop_reason` `"max_tokens"` cùng `error_type` trống. Một lần thành công không tool: một dòng log, tám khóa đúng thứ tự `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`. `model` của dòng đó lấy từ `ModelResponse.model`. `prompt_version` và `definitions_version` là số. `error_type` trống khi thành công. `duration_ms` là số nguyên không âm, có thể bằng 0. `ensure_ascii=False` nên chữ tiếng Việt nằm nguyên. Một tool rồi văn bản: hai dòng mô hình và một dòng tool bảy khóa. Hai loại dòng phân biệt bằng khóa `model` và khóa `tool`. Hàm log ném `Exception` thì lượt vẫn trả văn bản. Mỗi `complete` nhận `system` là `SYSTEM_PROMPT`, `tools` là chính `TOOL_DEFINITIONS`, không có tool thứ bảy, không có `revise_plan`. Đọc `SYSTEM_PROMPT` thấy bốn luật, đúng câu ví dụ `Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3`, dòng `Trả lời bằng tiếng Việt.`, và không có tên nhân vật khác JARVIS. Không viết mã trong `src/` ở task này

- [x] T003 Chạy `uv run pytest tests/test_llm_turn.py --tb=short` (phụ thuộc T002). In toàn bộ output lần chạy này vào báo cáo phiên trước khi sửa bất kỳ file nào trong `src/`. Kỳ vọng fail vì chưa có `run_turn`. Không sửa test để làm nó pass. Không coi lần chạy này là xong lát

- [x] T004 [P] Viết `tests/test_anthropic_model.py` (phụ thuộc T001). Bám [contracts/anthropic-adapter.md](./contracts/anthropic-adapter.md). Thay `AsyncAnthropic` ở chỗ adapter gọi bằng lớp giả dùng được trong `async with`. `__aenter__` trả đúng đối tượng có `messages.create`. Assertion đọc `kwargs` của constructor và của `messages.create`. Không đọc attribute của instance adapter. Không mở socket. Ca bắt buộc: `model` là `claude-haiku-5-5`, `thinking` là `{"type": "disabled"}`, `api_key` là khóa đưa vào `complete`, `max_retries` là `0`, `max_tokens` là `2048`, không có `stream`. Một ca: một yêu cầu có một vòng gồm hai tool, một kết quả có `is_error` true. `messages` gồm lịch sử văn bản, rồi một tin assistant có hai khối `tool_use` đúng `id`, `name`, `input` theo thứ tự, rồi một tin user có hai khối `tool_result` đúng `tool_use_id`, `content` và `is_error` theo cùng thứ tự. Exception của SDK thành `ModelError` với `class_name` là tên lớp và không có thông điệp SDK. `CancelledError` đi tiếp. `stop_reason` khác `tool_use` thì `tool_requests` rỗng. Không viết mã trong `src/` ở task này

- [x] T005 Chạy `uv run pytest tests/test_anthropic_model.py --tb=short` (phụ thuộc T004). In toàn bộ output lần chạy này vào báo cáo phiên trước khi sửa `src/clients/anthropic_model.py`. Kỳ vọng fail vì chưa có adapter. Không sửa test để làm nó pass. Không coi lần chạy này là xong lát

**Checkpoint**: Hai file test đã có. Hai output fail đã nằm trong báo cáo phiên. `src/` chưa đổi

---

## Phase 3: Cổng và prompt

**Purpose**: Kiểu cổng và hằng prompt. Chưa có vòng lặp

- [x] T006 [P] Viết `src/core/llm.py` (phụ thuộc T003, T005). Thay docstring hiện có. Chỉ thư viện chuẩn. Không import `anthropic`, `tools`, `db`, `fastapi`, `pydantic`. Kiểu đúng [data-model.md](./data-model.md) và [contracts/model-port.md](./contracts/model-port.md): `TextMessage.role` chỉ `user` hoặc `assistant`, `text` là str được rỗng. `ToolRequest` có `id` str, `name` str, `tool_input` dict. `ToolResultMessage` có `tool_use_id` str, `output` str, `is_error` bool. `ModelRequest` có `system` str, `messages` tuple `TextMessage`, `tools`, `rounds`. `ModelResponse` có `text` str được rỗng, `tool_requests` tuple, `stop_reason` str hoặc trống, `input_tokens` và `output_tokens` int hoặc trống, `model` str. `ModelError` là `Exception`, thuộc tính `class_name` str, thông điệp đúng `class_name`. Protocol có `model: str` và `async def complete(self, request, *, api_key: str, timeout: float) -> ModelResponse`. File này không tạo client SDK và không gọi mạng

- [x] T007 [P] Viết `src/core/system_prompt.py` (phụ thuộc T003, T005). Không import. Không đọc file lúc chạy. `PROMPT_VERSION: int = 1`. `SYSTEM_PROMPT` đúng văn bản trong [contracts/system-prompt.md](./contracts/system-prompt.md), gồm hai câu đầu `Bạn là JARVIS. Không dùng tên nhân vật nào khác.`, dòng `Trả lời bằng tiếng Việt.`, bốn luật, và đúng câu ví dụ về báo cáo thứ Sáu và chương 3

- [x] T008 Tạo `src/turns/__init__.py` (phụ thuộc T003, T005). Docstring gói. Không import SDK

---

## Phase 4: User Story 1 - Một tin nhắn ra một câu trả lời (Priority: P1) 🎯 MVP

**Goal**: Tin mới và lịch sử văn bản ra đúng một câu khi mô hình không đòi tool

**Independent Test**: Client giả trả một văn bản, lịch sử rỗng và lịch sử hai tin. Kho không bị gọi. Không mở mạng

- [x] T009 [US1] Viết `src/turns/llm_turn.py` (phụ thuộc T006, T007, T008). `async def run_turn(user_message, history, *, store, api_key, client, log=None) -> str`. `asyncio`, không thêm plugin. Không import adapter, `anthropic`, `db`, hay `settings`. Không sửa list `history`. Gửi đúng thứ tự lịch sử rồi tin mới. `stop_reason` `end_turn`: trả `text`, kể cả chuỗi rỗng, không gọi `execute_tool`. `system` của request là `SYSTEM_PROMPT`. `tools` là chính object `TOOL_DEFINITIONS`, không chép. Chưa cần đủ vòng tool, khóa, ngân sách, và log ở task này nếu các task sau thêm. Không gọi mạng

**Checkpoint**: Ca văn bản và lịch sử của `tests/test_llm_turn.py` có thể còn đỏ cho tới khi các nhánh sau xong

---

## Phase 5: User Story 2 - Mô hình đòi tool thì chạy rồi hỏi lại (Priority: P1)

**Goal**: Một phản hồi đòi tool là một vòng. Tối đa ba vòng

**Independent Test**: Client giả trả chuỗi phản hồi. Đếm vòng và số lần `execute_tool`. Không mở mạng

- [x] T010 [US2] Sửa `src/turns/llm_turn.py` (phụ thuộc T009). `stop_reason` `tool_use` và còn dưới 3 vòng: gọi `execute_tool(name, tool_input, store=store, log=cùng hàm log)` theo thứ tự yêu cầu, rồi `complete` một lần với mọi kết quả. `output` gửi lại không đổi chữ. `is_error` là ngược của `success`. Phản hồi thứ tư còn đòi tool: không chạy tool nào của phản hồi đó, không gọi `complete` thêm, trả đúng `Chưa trả lời xong yêu cầu này.` `stop_reason` khác `end_turn` và `tool_use`, gồm `max_tokens` và giá trị trống: không chạy tool, không gọi thêm, trả đúng `Chưa liên lạc được để trả lời lúc này.` Không sửa `src/tools/tool_router.py`

**Checkpoint**: Ca một tool, ca hai tool trong một phản hồi, và ca vòng thứ tư chạy được trên client giả

---

## Phase 6: User Story 3 - Prompt và danh sách tool chỉ có một chỗ (Priority: P1)

**Goal**: Mỗi lần gọi mô hình dùng cùng hằng prompt và đúng catalog sẵn có

**Independent Test**: Đọc `SYSTEM_PROMPT` một lần, không gọi mô hình. Request ghi lại trùng `TOOL_DEFINITIONS`

- [x] T011 [US3] Sửa `src/turns/llm_turn.py` và đối chiếu `src/core/system_prompt.py` (phụ thuộc T007, T010). Mỗi `complete` của cùng lượt gửi cùng `SYSTEM_PROMPT` và cùng object `TOOL_DEFINITIONS`. `prompt_version` sẽ là `PROMPT_VERSION`. Không có bộ định nghĩa thứ hai trong `src/turns/` hay `src/core/`. Prompt không đọc file lúc chạy

**Checkpoint**: Ca đọc prompt và ca sáu tool pass khi chạy riêng các assertion đó

---

## Phase 7: User Story 4 - Khóa, model, và lỗi được gọi tên (Priority: P1)

**Goal**: Thiếu khóa thì dừng trước client. Adapter gửi đúng model và không bật suy nghĩ

**Independent Test**: Không đưa khóa, client giả không bị gọi. Adapter bịt SDK, không mở mạng

- [x] T012 [US4] Sửa `src/turns/llm_turn.py` (phụ thuộc T011). `api_key is None` hoặc `api_key == ""`: ném exception có `str` đúng `Thiếu ANTHROPIC_API_KEY.` trước mọi `complete`. Không đọc `os.environ`. Không strip. `Exception` từ `complete`, trừ lỗi đã thành câu hết vòng, trả đúng `Chưa liên lạc được để trả lời lúc này.` và không đưa thông điệp exception vào kết quả. Chỉ bắt `Exception`. `CancelledError` không bị bắt

- [x] T013 [P] [US4] Viết `src/clients/anthropic_model.py` (phụ thuộc T006, T005). Thuộc tính `model` là `claude-haiku-5-5`. Mỗi `complete` dùng `async with AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0) as client:`. Không bỏ `api_key`. `messages.create` gửi `model` `claude-haiku-5-5`, `max_tokens` `2048`, `thinking` `{"type": "disabled"}`, không gửi `stream`. Tools lấy `name`, `description`, `input_schema` từ `request.tools`. Messages: lịch sử văn bản, rồi mỗi vòng một tin assistant các khối `tool_use` và một tin user các khối `tool_result` cùng thứ tự. `stop_reason` `tool_use` mới tạo `ToolRequest` khi có `id` str, `name` str, và `input` dict. `stop_reason` khác thì `tool_requests` rỗng. Mọi `Exception` khi vào `async with`, khi `create`, hoặc khi đóng client thành `raise ModelError(type(error).__name__) from None`. Không import `turns` hay `tools`. File này là chỗ duy nhất của lát import `anthropic`

- [x] T014 [P] [US4] Sửa `src/config/settings.py` (phụ thuộc T005). Xóa dòng `ANTHROPIC_API_KEY`. Giữ `TELEGRAM_BOT_TOKEN` và `_get_str`. Không sửa `require_supabase`

**Checkpoint**: Ca khóa và `tests/test_anthropic_model.py` pass. `TELEGRAM_BOT_TOKEN` còn nguyên

---

## Phase 8: User Story 5 - Cả lượt có ngân sách, hủy tác vụ thì đi tiếp (Priority: P1)

**Goal**: Cả lượt nằm trong 20 giây. Hủy tác vụ đi tiếp

**Independent Test**: Bịt `_now` để vượt 20 giây. Một ca ném `CancelledError`. Không mở mạng

- [x] T015 [US5] Sửa `src/turns/llm_turn.py` (phụ thuộc T010, T012). `_now` trả `time.monotonic()`. Hết giờ khi `_now() - mốc > 20`. Trước mỗi `complete` và mỗi `execute_tool`, hết giờ thì không bắt đầu việc đó và trả đúng `Chưa liên lạc được để trả lời lúc này.` `timeout` đưa vào `complete` là `20 - (_now() - mốc)`. Không dùng `asyncio.wait_for`. Không hủy `execute_tool` đã bắt đầu. Không bịt `time.monotonic` trong test. `CancelledError` đi ra, lần dang dở không bắt buộc có dòng log

**Checkpoint**: `test_budget_stops_further_calls` và `test_cancelled_error_propagates` pass

---

## Phase 9: User Story 6 - Một dòng nhật ký cho mỗi lần gọi mô hình (Priority: P1)

**Goal**: Mỗi lần gọi mô hình đã kết thúc có một dòng tám khóa, cùng hàm log với dòng tool

**Independent Test**: Hàm ghi nhận từng dòng. Một ca hàm ghi ném lỗi. Không mở mạng

- [x] T016 [US6] Sửa `src/turns/llm_turn.py` (phụ thuộc T015). Khi `log` là `None`, tạo một hàm in một dòng và truyền đúng hàm đó vào mọi `execute_tool`. Dòng mô hình ghi khi `complete` kết thúc, trước tool của phản hồi đó. `json.dumps(..., ensure_ascii=False)`. Khóa đúng thứ tự `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`. Lần trả `ModelResponse`: `model` lấy từ `ModelResponse.model`. Lần `complete` ném lỗi: `model` lấy từ `client.model`, `error_type` là `ModelError.class_name` hoặc `type(error).__name__`, không có thông điệp. `prompt_version` là `PROMPT_VERSION`. `definitions_version` là `DEFINITIONS_VERSION`. `duration_ms` là số nguyên không âm từ hai lần `_now` quanh `complete`, bằng 0 khi hiệu không dương. Ghi log nằm trong `try/except Exception` riêng. Nuốt lỗi của hàm log. Không nuốt `CancelledError`. Không lắp dòng bảy khóa của tool. Không sửa `src/tools/tool_router.py`

**Checkpoint**: Ca log tám khóa, ca dòng tool bảy khóa, và ca hàm log ném lỗi pass

---

## Phase 10: Polish

**Purpose**: Hai file test pass, docs B10, rồi kiểm allow list

- [x] T017 Chạy `uv run pytest tests/test_llm_turn.py tests/test_anthropic_model.py --tb=short` (phụ thuộc T011, T013, T014, T016). In output. Kỳ vọng pass, exit code 0, không có skipped. Nếu fail, sửa mã trong allow list, không sửa assertion để cho pass

- [x] T018 Cập nhật docs (phụ thuộc T017). Chỉ các chỗ sau.
  - `docs/ARCHITECTURE.md`: giữ câu trạng thái về `/health`, `db.plan_store`, F04 đến F08, và `execute_tool`. Thêm rằng lượt mô hình nằm ở `src/turns/llm_turn.py`, gọi cổng `src/core/llm.py` rồi `execute_tool`. Route và Telegram chưa gọi lượt này. Khóa mô hình do người gọi đưa, không đọc từ `settings`. §2 dòng `src/core/`: `llm.py` là cổng trung lập, chỉ thư viện chuẩn. `system_prompt.py` là hằng prompt và `PROMPT_VERSION`. Thêm dòng `src/turns/`: vòng lặp của một lượt, gọi `execute_tool`, không import SDK. Dòng `src/clients/`: thêm adapter Anthropic bên cạnh Telegram. §3: mũi tên gọi mô hình trỏ `turns/llm_turn.py` qua cổng `core/llm.py`, rồi `execute_tool` khi phản hồi đòi tool. §6: mỗi lần gọi mô hình đã kết thúc ghi một dòng JSON tám khóa qua cùng hàm log được truyền vào `execute_tool`. Giữ câu loguru chưa chốt
  - `docs/PRODUCT.md`: hàng F12 bỏ chữ OpenAI-compatible, ghi cổng trung lập và adapter Anthropic. Dòng ước tính chi phí không thuộc task này, không sửa dòng đó
  - `docs/DECISIONS.md`: thêm D-015 vào cuối file, đúng khối trong [plan.md](./plan.md) mục docs. Không sửa D-010 đến D-014, trừ D-004 chỉ thêm dòng, không xóa câu cũ. D-004 thêm dòng `Cập nhật 2026-10-26:` ghi rằng lớp LLM là cổng trung lập trong `src/core/llm.py` cộng adapter theo nhà cung cấp (hiện là Anthropic, `src/clients/anthropic_model.py`), thay cho câu interface chuẩn OpenAI-compatible

- [x] T019 Chạy `.\scripts\check.ps1 -AllowList specs/008-llm-tool-turn/allowed-files.txt` (phụ thuộc T018). In output. Kỳ vọng mã thoát 0. Không nới allow list để qua. Không sửa test cũ

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: bắt đầu ngay
- **Tests (Phase 2)**: phụ thuộc T001. Chặn mọi sửa `src/`
- **Cổng và prompt (Phase 3)**: phụ thuộc hai output fail
- **US1 đến US6**: theo số task. Cùng sửa `llm_turn.py` nên không song song với nhau
- **Polish**: T017 sau mã. T018 sau T017. T019 sau T018

### User Story Dependencies

- **US1**: sau cổng, prompt, và gói `turns`
- **US2**: sau US1, cùng file `llm_turn.py`
- **US3**: prompt đã có ở T007. T011 chỉ nối request với hằng đó và với `TOOL_DEFINITIONS`
- **US4**: T012 phụ thuộc T011. T013 song song với T012 vì khác file, sau T006 và T005. T014 song song với T013
- **US5**: sau T012
- **US6**: sau T015

### Within Each User Story

- Test của lát nằm ở Phase 2 và đã fail trước mọi task mã
- Cổng trước vòng lặp
- Vòng văn bản trước vòng tool
- Không sửa assertion để đổi một task đỏ thành xanh

### Parallel Opportunities

- T002 và T004 viết hai file test song song
- T006 và T007 song song sau hai output fail
- T013 và T014 song song với nhau, và song song với T012
- T010, T011, T012, T015, T016 cùng một file, chạy tuần tự

---

## Parallel Example: Phase 2 và User Story 4

```text
T002: viết tests/test_llm_turn.py
T004: viết tests/test_anthropic_model.py

T013: viết src/clients/anthropic_model.py
T014: xóa dòng ANTHROPIC_API_KEY trong src/config/settings.py
```

T003 chỉ chạy sau T002. T005 chỉ chạy sau T004. Mỗi lần in output fail trước khi sửa file mã mà lần đó kiểm.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2, gồm hai output fail
2. Xong Phase 3
3. Xong T009
4. Dừng và đọc ca văn bản trong `tests/test_llm_turn.py`. Các ca khác còn đỏ là đúng cho tới task của story đó

### Incremental Delivery

1. Hai file test và hai lần fail
2. Cổng, prompt, rồi văn bản một lượt
3. Vòng tool, rồi khóa và adapter
4. Ngân sách, log, rồi T017 pass
5. Docs B10, rồi `check.ps1`

### Parallel Team Strategy

1. Cùng xong T001, T003, và T005
2. Một người viết cổng và vòng lặp
3. Người khác viết adapter và xóa dòng khóa sau T005
4. Docs chỉ sau T017

---

## Notes

- [P] là khác file và không phụ thuộc task chưa xong
- Không task nào sửa file ngoài `allowed-files.txt`
- In output thật của T003 và T005. Không tóm tắt thay cho output
- `duration_ms` có thể bằng 0. Không bịt `time.monotonic` toàn tiến trình
- Timeout httpx trên Worker chưa kiểm. Không thêm task đo ở lát này
