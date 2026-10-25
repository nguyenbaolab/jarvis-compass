---
description: "Task list for Lưu kế hoạch vào kho Supabase"
---

# Tasks: Lưu kế hoạch vào kho Supabase

**Input**: Design documents from `/specs/006-supabase-plan-store/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Nguyên tắc VIII, [spec.md](./spec.md), và [quickstart.md](./quickstart.md) bắt pytest. Viết test trước. Test không cần kho phải fail đúng chỗ đã ghi rồi mới implement. Helper kho vẫn skip khi thiếu biến hoặc không nối được; host không phải local thì fail, không skip. Từ T002 đến hết lát, trừ T026, pytest chạy trong tiến trình đã có `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY`, kho local đang bật. Chỗ kỳ vọng fail của param `supabase` hoặc test kho là fail thật, không phải skip. Lệnh pytest của các chỗ đó dùng `-rs`. Thấy skip `Kho local không chạy` trong lúc implement thì dừng và báo.

**Organization**: Theo user story. Story sau dùng store của story trước. Ánh xạ dòng nằm ở US1 vì mọi lần đọc đều đi qua đó, và khóa luôn ca trạng thái lạ của US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: User story (US1, US2, US3, US4)
- Mỗi task có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- Không thêm thư viện Python. Không sửa `pyproject.toml`. Không tạo `package.json`
- Không sửa `src/core/plans.py`, `src/tools/`, `src/app.py`, `src/db/__init__.py`, `tests/helpers.py`
- Không sửa `docs/PRODUCT.md`, `.specify/memory/constitution.md`
- `docs/DECISIONS.md` chỉ T025 được sửa, và chỉ thêm D-013 ở cuối. Không sửa mục cũ
- Không đọc, không ghi `.env` thật và `.dev.vars`. Không dán khóa vào repo. Không ghi `JARVIS_TEST_SUPABASE_URL` hay `JARVIS_TEST_SUPABASE_KEY` vào file nào. Không in khóa ra báo cáo
- `Plan` và `Subtask` không thêm trường, không thêm lớp. `PlanStore` giữ đúng bốn phương thức async
- Trong `src/`, chỉ `src/db/client.py` được `import postgrest` và gọi `.from_()` hoặc `.rpc()`. `src/db/plan_store.py` không import `postgrest` và không import `src/tools`
- CLI: `npx --yes supabase@2.122.0`. Không cài bản khác
- File migration đổi thì chạy lại `npx --yes supabase@2.122.0 db reset` trước khi chạy test

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khung Supabase local, chưa có lược đồ kế hoạch

- [x] T001 Tạo khung Supabase local bằng `npx --yes supabase@2.122.0 init` tại gốc repo. Giữ `supabase/config.toml`. Nếu init tạo `supabase/.gitignore` thì giữ. Nếu init tạo `supabase/seed.sql` thì xóa, vì lược đồ không nằm ở seed. File nào khác do init tạo thì dừng và hỏi, không giữ. Không ghi khóa cloud vào `supabase/config.toml`. Không tạo `package.json`. Không sửa `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Kho local đang chạy, cấu hình, model dòng, factory PostgREST, migration đã được `db reset` áp, và helper test kho. Chưa có bốn phương thức store

**⚠️ CRITICAL**: Chưa xong phase này thì chưa làm user story

- [x] T002 Bật kho local (phụ thuộc T001). Bật Docker Desktop là việc của người dùng. Agent chạy `npx --yes supabase@2.122.0 start`, rồi `npx --yes supabase@2.122.0 status`. Từ output thật của `status`, lấy URL API và khóa secret local, đặt vào `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` trong tiến trình PowerShell đang dùng để chạy pytest. Không ghi hai giá trị này vào file nào. Không in khóa ra báo cáo. Mọi lần chạy pytest từ task này tới hết lát, trừ T026, dùng cùng tiến trình có hai biến này

- [x] T003 [P] Viết `tests/test_settings_supabase.py` (phụ thuộc T002). Test không mở mạng và không đọc `.env`. Đặt và xóa biến môi trường giả bằng fixture `monkeypatch` có sẵn của pytest. Không gán `os.environ` trực tiếp. Sentinel trên `SUPABASE_URL`, `SUPABASE_KEY`, `JARVIS_TEST_SUPABASE_URL`, và `JARVIS_TEST_SUPABASE_KEY`, rồi gọi cấu hình bằng `{}`: kỳ vọng lỗi, chứng minh hàm không đọc môi trường tiến trình. Dict và object attribute đều được. Thiếu, không phải `str`, hoặc `""` thì đúng một trong ba câu: `Thiếu SUPABASE_URL.`, `Thiếu SUPABASE_KEY.`, `Thiếu SUPABASE_URL và SUPABASE_KEY.` Chuỗi chỉ khoảng trắng vẫn là có giá trị, không `strip`. Lời lỗi không chứa giá trị đã truyền. Khi một khóa có giá trị và khóa kia thiếu, câu không chứa giá trị còn lại. Chạy `uv run pytest tests/test_settings_supabase.py`. Kỳ vọng fail vì chưa có hàm, cho đến T004

- [x] T004 Sửa `src/config/settings.py` (phụ thuộc T003). Thêm `SettingsError` và `require_supabase(source)`. `Mapping` thì `.get`. Không phải `Mapping` thì `getattr(source, name, None)`. Tên là `SUPABASE_URL` và `SUPABASE_KEY`. Xóa hai dòng module đang gọi `os.getenv` cho hai tên đó. Giữ `os.getenv` cho `ANTHROPIC_API_KEY` và `TELEGRAM_BOT_TOKEN`. Không gọi `os.getenv` cho `SUPABASE_URL` và `SUPABASE_KEY`. Grep lại; nếu file Python khác đang import hai hằng đó thì dừng và hỏi. Chạy `uv run pytest tests/test_settings_supabase.py`. Kỳ vọng pass, exit code 0

- [x] T005 [P] Thêm `PlanRow` và `SubtaskRow` trong `src/db/models.py`. Pydantic. `SubtaskRow.status` là `str`, không `Literal` và không `SubtaskStatus`. `SubtaskRow.note` là `str | None`. Có `position: int`, `created_at`, `status_changed_at`. `PlanRow` có `id: str`, `goal: str`, `created_order: int`, `subtasks`. Không import `src/tools`. Không dựng `Plan` trong file này

- [x] T006 [P] Thêm factory `postgrest_client(url, key)` trong `src/db/client.py`. Đây là chỗ duy nhất trong `src/` tạo `AsyncPostgrestClient`. Header là `DEFAULT_POSTGREST_CLIENT_HEADERS` cộng `apikey`. Khóa bắt đầu bằng `eyJ` thì thêm `Authorization: Bearer` và chính khóa đó. `base_url` là URL bỏ slash cuối rồi cộng `/rest/v1`. Dùng `async with`. Chưa gọi bảng `plans` hay `subtasks`. Chưa có hàm xóa

- [x] T007 [P] Thêm một file `supabase/migrations/<timestamp>_plans_and_subtasks.sql` (phụ thuộc T001). Một file cho toàn bộ lược đồ. Ràng buộc chép đúng [data-model.md](./data-model.md): `plans.id` là `uuid` primary key default `gen_random_uuid()`; `plans.goal` là `text not null`; `plans.created_order` là `bigint generated always as identity` unique; không cột mốc trên `plans`. `subtasks.id` là `uuid` primary key; `plan_id` là `uuid not null` references `plans(id)` on delete cascade; `title` là `text not null`; `status` là `text not null` với `CHECK (status in ('pending', 'done', 'skipped'))`; `note` là `text` null với `CHECK (note IS NULL OR note <> '')`; `position` là `integer not null`, gốc 0, unique `(plan_id, position)` deferrable initially deferred; `created_at` và `status_changed_at` là `timestamptz not null default now()`. RLS bật trên cả hai bảng. Không policy cho `anon` hay `authenticated`. `revoke all` trên hai bảng và trên hai hàm RPC khỏi `public`, `anon`, `authenticated`. `service_role` được `select`, `insert`, `update`, `delete` trên hai bảng, `usage` và `select` trên sequence của `created_order`, `execute` trên `add_plan` và `replace_plan`. Hàm trigger không được `execute` qua PostgREST. Hàm ghi đặt `search_path = public`. Trigger `BEFORE UPDATE` trên `subtasks`: `NEW.created_at = OLD.created_at`; `NEW.status` khác `OLD.status` thì `NEW.status_changed_at = now()`, ngược lại giữ `OLD.status_changed_at`. `add_plan(goal text, subtasks jsonb) returns jsonb` và `replace_plan(plan_id uuid, goal text, subtasks jsonb) returns jsonb`, mỗi hàm một transaction. `replace_plan` không xóa hết việc con rồi chèn lại: không có kế hoạch thì `raise` mã ổn định `plan_missing`; cập nhật `goal`; không sửa `created_order`; xóa việc không còn trong mảng; `UPDATE` việc còn danh tính mà không đưa `created_at` hay `status_changed_at` vào `SET`; `INSERT` việc mới. `position` lấy từ thứ tự mảng. `note` JSON null thành SQL `NULL`. Không tạo bảng bằng tay

- [x] T008 Áp migration bằng `npx --yes supabase@2.122.0 db reset` (phụ thuộc T002, T007). Kho local đang chạy. Mỗi khi file migration đổi ở task sau, chạy lại `db reset` trước khi chạy test

- [x] T009 [P] Viết `test_remote_host_fails_before_network` trong `tests/test_supabase_plan_store.py` (phụ thuộc T002). Gọi helper ở `tests/supabase_plan_db.py` với URL host `https://example.supabase.co` và khóa giả. Kỳ vọng đúng câu `Test kho chỉ chạy trên kho local.` Factory `postgrest_client` trong `src/db/client.py` không được gọi. Không skip. Chạy `uv run pytest -rs tests/test_supabase_plan_store.py::test_remote_host_fails_before_network`. Kỳ vọng fail thật, không skip, vì chưa có helper, cho đến T010. Nếu thấy skip `Kho local không chạy` thì dừng và báo

- [x] T010 Thêm `tests/supabase_plan_db.py` (phụ thuộc T002, T006, T009). Đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY`. Không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Không đọc `.env` hay `.dev.vars`. Thiếu biến thì `pytest.skip` với đúng câu trong [contracts/plan-store.md](./contracts/plan-store.md): `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL.`, `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_KEY.`, hoặc `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL và JARVIS_TEST_SUPABASE_KEY.` Host phải là `127.0.0.1` hoặc `localhost`; `localhost` không phân biệt hoa thường. Host khác, gồm `[::1]` và URL không có host, ném lỗi đúng câu `Test kho chỉ chạy trên kho local.` trước khi tạo client và trước mọi lời gọi mạng. Không skip ca host. Hai giá trị đi vào dict dưới khóa `SUPABASE_URL` và `SUPABASE_KEY`. Hàm xóa nằm ở file này, không nằm trong `src/`: dựng client bằng `postgrest_client`, xóa `subtasks` rồi `plans`. Câu skip không chứa giá trị khóa và không chứa `str` của exception. Chạy lại test ở T009 với `uv run pytest -rs tests/test_supabase_plan_store.py::test_remote_host_fails_before_network`. Kỳ vọng pass, không skip. Nếu thấy skip `Kho local không chạy` thì dừng và báo

**Checkpoint**: Kho local đang chạy, migration đã được `db reset` áp, cấu hình, model dòng, factory, và chặn host đã có. Chưa có `SupabasePlanStore` đủ bốn phương thức

---

## Phase 3: User Story 1 - Kế hoạch còn sau khi lần làm việc kết thúc (Priority: P1) 🎯 MVP

**Goal**: Thêm, liệt kê mới hơn trước, mở đúng danh tính, mở danh tính không có thì không có kế hoạch. Chữ Việt và thứ tự việc con đọc lại đúng

**Independent Test**: Trên một kho trống vừa dựng từ repo, lưu hai kế hoạch, kết thúc lần ghi, rồi liệt kê và mở lại. Không cần HTTP, Telegram, hay LLM

### Tests for User Story 1 ⚠️

- [x] T011 [P] [US1] Viết `tests/test_plan_row_mapping.py` (phụ thuộc T005). Gọi hàm ánh xạ trong `src/db/plan_store.py` với dòng giả. Không tạo `SupabasePlanStore`, không đọc biến kho, không mở mạng. Dòng hợp lệ thành `Plan` và `Subtask`: `note` null thành `None`, `""` cũng thành `None`, `created_order` thành `int`, hai mốc không có trên `Subtask`. Thiếu khóa `subtasks` là lỗi ánh xạ. Mảng rỗng là kế hoạch không có việc. Mã không thuộc `pending`, `done`, `skipped` thì `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")`, không có `Plan`. Ca mã lạ này cũng là tình huống 4 của US3 và SC-007; US3 không viết lại. Chạy `uv run pytest tests/test_plan_row_mapping.py`. Kỳ vọng fail vì chưa có hàm, cho đến T013

- [x] T012 [P] [US1] Viết ca 1, 2, 3, và 6 của mục hợp đồng trong `tests/test_plan_store_contract.py` (phụ thuộc T008, T010). Một coroutine, fixture `params=["memory", "supabase"]`, `asyncio.run`. Không `pytest-asyncio`, không plugin pytest mới. Param `memory` dùng `MemoryPlanStore` và luôn chạy. Param `supabase` đi qua `tests/supabase_plan_db.py`: helper skip khi thiếu biến hoặc không nối được, fail khi host không phải local, xóa hai bảng trước mỗi ca. Phủ: thêm kế hoạch hai việc thì id kế hoạch là UUID chữ thường khớp regex phiên bản 4 trong `tests/helpers.py`, mục tiêu và từng việc giữ id, tiêu đề, `pending`, ghi chú trống, thứ tự. Thêm kế hoạch thứ hai thì liệt kê đặt kế hoạch đó trước. `get` đúng id trả đúng kế hoạch. `get` một UUID khác, `"1"`, và `"2"` trả `None`. Chữ Việt NFC đọc lại từng ký tự. Thứ tự việc con khi liệt kê và khi mở trùng thứ tự đã lưu. Param memory pass ngay vì bản bộ nhớ đã làm các ca này. Kho đang bật và hai biến đã đặt từ T002, nên param supabase kỳ vọng fail thật, không skip, cho đến T013. Chạy `uv run pytest -rs tests/test_plan_store_contract.py`. Nếu thấy skip `Kho local không chạy` thì dừng và báo. Không sửa assertion test cũ

### Implementation for User Story 1

- [x] T013 [US1] Thêm hàm ánh xạ và `add`, `list_newest_first`, `get` của `SupabasePlanStore` trong `src/db/plan_store.py`, lời gọi PostgREST trong `src/db/client.py` (phụ thuộc T004, T006, T007, T008, T010, T011, T012). `__init__` gọi `require_supabase` trước khi tạo client. `add` là một `rpc` `add_plan`. `get` và `list` là `select` kèm việc con, rồi ánh xạ. `get` và `replace` chỉ coi chuỗi là danh tính khi `uuid.UUID` phân tích được và `plan_id == str(uuid.UUID(plan_id))`. Chuỗi khác: `get` trả `None` và không gọi mạng. `maybe_single` rỗng là `None`. Sắp việc con theo `position` tăng dần trong mapper, và gọi `order(..., foreign_table="subtasks")`. Hình JSON của RPC chưa thấy trong spike: nếu là list thì lấy phần tử đầu. Không thêm request ghi thứ hai. Id đọc ra không khớp regex phiên bản 4 trong `tests/helpers.py` thì dừng và hỏi, không nới regex. Chưa làm `replace`. Chạy `uv run pytest -rs tests/test_plan_row_mapping.py tests/test_plan_store_contract.py tests/test_settings_supabase.py`. Kỳ vọng pass, không skip. Nếu thấy skip `Kho local không chạy` thì dừng và báo

**Checkpoint**: User Story 1 kiểm bằng `uv run pytest -rs tests/test_plan_store_contract.py tests/test_plan_row_mapping.py`

---

## Phase 4: User Story 2 - Sửa việc con và đọc lại đúng chữ đã lưu (Priority: P1)

**Goal**: Đổi trạng thái, thêm việc, đặt và xóa ghi chú, đọc lại đúng. Ghi chú trống là `NULL`

**Independent Test**: Lưu một kế hoạch có hai việc con. Đổi trạng thái việc thứ nhất, thêm một việc, đặt ghi chú, rồi xóa ghi chú. Mỗi lần đọc lại kế hoạch

### Tests for User Story 2 ⚠️

- [x] T014 [P] [US2] Thêm ca 5 vào coroutine trong `tests/test_plan_store_contract.py` (phụ thuộc T013). Cùng fixture hai bản. Đổi một việc qua `done`, `skipped`, rồi `pending`. Việc kia giữ nguyên. Thêm một việc thì việc đó đứng cuối, `pending`, ghi chú trống. Đặt ghi chú rồi xóa: lần đọc là không có ghi chú, không phải chuỗi rỗng. Param memory pass ngay. Kho đang bật và hai biến đã đặt từ T002, nên param supabase kỳ vọng fail thật, không skip, cho đến T016. Chạy `uv run pytest -rs tests/test_plan_store_contract.py`. Nếu thấy skip `Kho local không chạy` thì dừng và báo

- [x] T015 [P] [US2] Thêm ca cột `note` là `NULL` vào `tests/test_supabase_plan_store.py` (phụ thuộc T013). Đọc cột bằng client của helper, không thêm hàm xóa hay hàm ghi trạng thái trong `src/`. Miền là `None` và cột SQL là `NULL`. Host không phải local thì fail theo helper, không skip. Kho đang bật và hai biến đã đặt từ T002, nên kỳ vọng fail thật, không skip, cho đến T016, vì `replace` chưa có. Chạy `uv run pytest -rs tests/test_supabase_plan_store.py`. Nếu thấy skip `Kho local không chạy` thì dừng và báo

### Implementation for User Story 2

- [x] T016 [US2] Thêm `replace` trong `src/db/plan_store.py` và một `rpc` `replace_plan` trong `src/db/client.py` (phụ thuộc T014, T015). Một request cho một lần `replace`. Không xóa hết việc con rồi chèn lại. Không đổi `created_order`. Không gửi hai cột mốc trong `UPDATE`. Ghi chú miền `None` thành JSON null. Chạy `uv run pytest -rs tests/test_plan_store_contract.py tests/test_supabase_plan_store.py`. Kỳ vọng pass, không skip. Nếu thấy skip `Kho local không chạy` thì dừng và báo

**Checkpoint**: User Story 2 kiểm bằng `uv run pytest -rs tests/test_plan_store_contract.py tests/test_supabase_plan_store.py`

---

## Phase 5: User Story 3 - Dữ liệu không dùng được thì dừng rõ (Priority: P1)

**Goal**: `replace` một danh tính không có thì cùng một câu trên cả hai bản, không tạo kế hoạch. `"1"` và `"2"` không mở được kế hoạch. Dữ liệu đọc từ kho chứa trạng thái lạ thì đúng câu lỗi

**Independent Test**: Lưu một kế hoạch trên bản trong bộ nhớ và trên kho thật. Thay bằng một danh tính khác không có. Mở bằng "1" và bằng "2". Với dữ liệu đọc từ kho chứa trạng thái lạ, đọc kế hoạch đó

### Tests for User Story 3 ⚠️

- [x] T017 [US3] Thêm ca 4 vào coroutine trong `tests/test_plan_store_contract.py` (phụ thuộc T016). `replace` một id không có, gồm `"1"`, `"2"`, và UUID viết hoa, ném `PlanDomainError("Không có kế hoạch với danh tính này.")`. Số kế hoạch không tăng. Kế hoạch đang có không đổi. `get("1")` và `get("2")` vẫn là `None`. Ca trạng thái lạ không viết lại; nó nằm ở `tests/test_plan_row_mapping.py` từ T011. Chạy `uv run pytest -rs tests/test_plan_store_contract.py`. Kỳ vọng param memory fail cho đến T018. Kho đang bật và hai biến đã đặt từ T002, nên param supabase của ca này kỳ vọng fail thật, không skip, cho đến T019. Nếu thấy skip `Kho local không chạy` thì dừng và báo. Nếu một test cũ phụ thuộc `replace` im lặng khi thiếu id thì dừng và hỏi, không sửa assertion test đó

### Implementation for User Story 3

- [x] T018 [US3] Sửa đúng một hành vi trong `tests/fakes/memory_plan_store.py` (phụ thuộc T017). `replace` không thấy id thì `PlanDomainError("Không có kế hoạch với danh tính này.")` và không thêm dòng. Import `PlanDomainError`. Không sửa `add`, `list_newest_first`, `get`. Không sửa `tests/helpers.py`. Chạy lại test T017 bằng `uv run pytest -rs tests/test_plan_store_contract.py`. Param memory pass. Kho đang bật và hai biến đã đặt từ T002, nên param supabase còn fail thật, không skip, cho đến T019. Nếu thấy skip `Kho local không chạy` thì dừng và báo

- [x] T019 [US3] Khớp `replace` thiếu id trên Supabase trong `src/db/plan_store.py` (phụ thuộc T018). Mã `plan_missing` từ RPC thành đúng câu `Không có kế hoạch với danh tính này.` Câu tiếng Việt không ghép từ message SQL. Id không canonical: `replace` ném câu đó và không gọi mạng. Không thêm kế hoạch. Chạy `uv run pytest -rs tests/test_plan_store_contract.py tests/test_plan_row_mapping.py`. Kỳ vọng pass, không skip. Nếu thấy skip `Kho local không chạy` thì dừng và báo

**Checkpoint**: User Story 3 kiểm bằng `uv run pytest -rs tests/test_plan_store_contract.py tests/test_plan_row_mapping.py`

---

## Phase 6: User Story 4 - Hai mốc thời gian chỉ để dùng sau (Priority: P2)

**Goal**: Mỗi việc con trong kho có hai mốc. Mốc trạng thái chỉ đổi khi mã trạng thái đổi. Tool không thấy hai mốc

**Independent Test**: Lưu một việc con, đọc hai mốc trong kho, đọc kế hoạch qua tool. Ghi lại cùng trạng thái, rồi ghi một trạng thái khác. So hai mốc trước và sau mỗi lần ghi

### Tests for User Story 4 ⚠️

- [x] T020 [US4] Thêm ca mốc vào `tests/test_supabase_plan_store.py` (phụ thuộc T019). Đọc hai cột bằng helper, không thêm trường vào `Plan` hay `Subtask`, không sửa `src/tools/`. Sau `add`, hai mốc của mỗi việc bằng nhau. `replace` cùng mã, có đổi tiêu đề hoặc ghi chú, giữ nguyên từng giá trị hai mốc. `replace` đổi mã thì `created_at` giữ nguyên và `status_changed_at` đổi. Thêm việc chỉ đặt mốc mới trên việc đó. Gọi `create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, `add_subtask`, và `set_subtask_note` với store Supabase: JSON không có hai mốc. So mốc là so đúng giá trị API trả về. Host không phải local thì fail theo helper, không skip. Kho đang bật và hai biến đã đặt từ T002, nên kỳ vọng fail thật, không skip, cho đến T021 nếu trigger hoặc câu select chưa đúng. Chạy `uv run pytest -rs tests/test_supabase_plan_store.py`. Nếu thấy skip `Kho local không chạy` thì dừng và báo

### Implementation for User Story 4

- [x] T021 [US4] Đọc hai mốc trong `tests/supabase_plan_db.py` bằng client factory (phụ thuộc T020). Không thêm hàm này vào `src/`. Nếu ca T020 fail vì trigger, sửa trigger trong file migration của T007, rồi chạy lại `npx --yes supabase@2.122.0 db reset` trước khi chạy test. `UPDATE` của `replace_plan` vẫn không gửi hai cột mốc. Không đưa mốc vào `Subtask(...)`. Chạy `uv run pytest -rs tests/test_supabase_plan_store.py tests/test_plan_store_contract.py`. Kỳ vọng pass, không skip. Nếu thấy skip `Kho local không chạy` thì dừng và báo

**Checkpoint**: User Story 4 kiểm bằng `uv run pytest -rs tests/test_supabase_plan_store.py`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs và xác nhận quickstart. Không nối store vào route

- [x] T022 [P] Sửa dòng Trạng thái code và mục `src/db`, `src/config` trong `docs/ARCHITECTURE.md` (phụ thuộc T021). Logic F04 đến F08 vẫn ở core và tools. Bản `PlanStore` Supabase nằm ở `src/db/` và chưa được route sản phẩm, Telegram, hay LLM gọi. Bỏ ý chưa nối database. `client.py` là chỗ duy nhất trong `src/` gọi PostgREST. `plan_store.py` là bản cổng. `models.py` là dòng DB. Hai mốc chỉ ở bảng việc con. `settings.py` đọc `SUPABASE_URL` và `SUPABASE_KEY` từ nguồn người gọi truyền vào, dict hoặc env của Worker, không bằng `os.getenv`

- [x] T023 [P] Sửa `AGENTS.md` (phụ thuộc T021). Thêm lệnh `npx --yes supabase@2.122.0` cho `init`, `start`, `db reset`, và `status`. Pytest đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY`, không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Host phải là `127.0.0.1` hoặc `localhost`, nếu không test thất bại trước khi gọi mạng. `db reset` là dựng lược đồ. Test tự xóa dòng trong `tests/`, không trong `src/`. Tên nhãn mà `status` in ra lấy từ output thật của bản `2.122.0`. Thêm `.dev.vars` vào luật không đọc không ghi file secret, cạnh `.env` thật

- [x] T024 [P] Sửa chú thích `SUPABASE_KEY` trong `.env.example` (phụ thuộc T021). Bản store cần khóa service role vì `anon` không được grant. Không điền khóa thật

- [x] T025 [P] Ghi D-013 vào cuối `docs/DECISIONS.md` (phụ thuộc T021). D-013 đã được duyệt. Nội dung đúng bản đề xuất trong `specs/006-supabase-plan-store/plan.md`, cùng định dạng D-012: tiêu đề `## D-013 — ...`, rồi **Date:** là ngày ghi, **Status:** Accepted, **Bối cảnh:**, **Quyết định:**, **Phương án đã bỏ:**. Không thêm mục mà bản đề xuất không có, kể cả **Lý do:**. Không sửa D-010, D-011, D-012, hay mục nào khác

- [x] T026 Chạy quickstart không kho (phụ thuộc T022, T023, T024, T025). Bỏ `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` khỏi tiến trình rồi chạy `uv run pytest` từ gốc repo. Đây là lần cố ý không có hai biến. 129 test hiện có pass. Test ánh xạ và test host xa pass. Test kho skip với câu bắt đầu bằng `Kho local không chạy:`. Exit code 0. Không sửa assertion test cũ để làm xanh

- [x] T027 Chạy toàn bộ pytest với kho local đang bật (phụ thuộc T026). Đặt lại `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` trong cùng tiến trình PowerShell. Nếu tiến trình không còn hai biến, lấy lại URL API và khóa secret local từ output thật của `npx --yes supabase@2.122.0 status`. Không ghi hai giá trị vào file nào. Không in khóa ra báo cáo. Chạy `uv run pytest -rs` từ gốc repo. Kỳ vọng: mọi test pass, 0 test bị skip. Liệt kê số test kho đã chạy theo tên file, gồm `tests/test_supabase_plan_store.py` và các ca param `supabase` trong `tests/test_plan_store_contract.py`. In nguyên dòng tổng kết của pytest

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: bắt đầu ngay
- **Foundational (Phase 2)**: phụ thuộc T001. T002 chặn mọi pytest của lát, trừ T026. T008 chặn test ghi vào kho. Chặn mọi user story
- **User Story 1 (Phase 3)**: sau Phase 2
- **User Story 2 (Phase 4)**: sau US1, vì `replace` cần `add`
- **User Story 3 (Phase 5)**: sau US2, vì ca supabase của `replace` thiếu id dùng đường `replace` đã có. Ca ánh xạ trạng thái lạ đã khóa ở T011
- **User Story 4 (Phase 6)**: sau US3, vì so mốc trước và sau `replace`
- **Polish**: sau US4. T027 sau T026

### User Story Dependencies

- **US1**: sau foundational. Không phụ thuộc US2, US3, US4
- **US2**: sau US1
- **US3**: sau US2 cho phần kho. Phần dòng giả đã xong ở T011
- **US4**: sau US3

### Within Each User Story

- Test viết trước phần implement của chính story đó
- Param memory của hợp đồng US1 và US2 pass trước khi có store Supabase
- Param memory của ca `replace` thiếu id fail cho đến T018
- Param supabase và test kho fail thật, không skip, khi kho đang bật

### Parallel Opportunities

- Sau T001: T002, T005, T006, T007 song song
- T003 sau T002, song song với T005, T006, T007. T004 sau T003
- T008 sau T002 và T007. T009 sau T002. T010 sau T006 và T009
- T011 và T012 song song sau Phase 2
- T014 và T015 song song sau T013
- T022, T023, T024, T025 song song sau T021

---

## Parallel Example: User Story 1

```text
T011 tests/test_plan_row_mapping.py
T012 tests/test_plan_store_contract.py
```

Hai file khác nhau. Cùng chờ T013 để xanh.

## Parallel Example: Foundational

```text
T002 kho local và hai biến trong tiến trình PowerShell
T005 src/db/models.py
T006 src/db/client.py
T007 supabase/migrations/<timestamp>_plans_and_subtasks.sql
T009 tests/test_supabase_plan_store.py
```

T008 chạy `db reset` sau T002 và T007, trước test ghi vào kho.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Xong Phase 1 và Phase 2, gồm kho đang bật và `db reset`
2. Xong Phase 3
3. Dừng và kiểm US1 bằng `uv run pytest -rs tests/test_plan_store_contract.py tests/test_plan_row_mapping.py`
4. Chưa cần `replace`, mốc thời gian, hay route HTTP

### Incremental Delivery

1. Setup + foundational
2. US1: kế hoạch còn sau khi tiến trình ghi tắt
3. US2: sửa việc con và ghi chú
4. US3: replace thiếu id trên cả hai bản, cộng ca trạng thái lạ đã có từ T011
5. US4: hai mốc chỉ trong kho
6. Polish docs, ghi D-013 ở T025
7. T026 quickstart không kho, rồi T027 toàn bộ pytest với kho bật và 0 skip

### Parallel Team Strategy

Một người nên đi tuần tự vì `src/db/client.py`, `src/db/plan_store.py`, và `tests/test_plan_store_contract.py` được sửa ở nhiều story. Song song chỉ các task đánh [P] ở trên.

---

## Notes

- [P] là khác file và không phụ thuộc task chưa xong
- Không nối `SupabasePlanStore` vào `src/app.py`
- `httpx.ConnectError` và `httpx.TimeoutException` thì skip với câu `Kho local không chạy: không kết nối được.` Kiểu exception khác khi Docker tắt thì thêm đúng kiểu đó vào nhánh skip. Không bắt `Exception` rồi skip hết. `APIError` sau khi đã nối là fail. Trong lát này kho đang bật, nên skip câu đó lúc implement là dừng và báo. T026 là lần cố ý bỏ hai biến
- File migration đổi thì `npx --yes supabase@2.122.0 db reset` trước khi chạy test
- Hai lần ghi cùng lúc có thể mất một lần. Không thêm khóa
- Commit từng cụm task là việc của người dùng. Agent không tự commit
