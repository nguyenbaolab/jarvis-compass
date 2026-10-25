# Implementation Plan: Lưu kế hoạch vào kho Supabase

**Branch**: `006-supabase-plan-store` | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-supabase-plan-store/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

F03: bản `PlanStore` trên Supabase, cùng bốn phương thức async đã chốt ở D-012, giữ hành vi bản trong bộ nhớ trừ câu lỗi khi `replace` một danh tính không có. Danh tính kế hoạch do Postgres cấp bằng `gen_random_uuid()`. Thứ tự tạo là cột identity. Thứ tự việc con là cột vị trí. Ghi chú trống là `NULL`. Hai mốc thời gian chỉ có trên dòng việc con. `src/core/plans.py` không đổi trường và không thêm lớp. `src/tools/` không sửa. Mọi lời gọi PostgREST của sản phẩm nằm trong `src/db/client.py`. Mỗi lần `add` và mỗi lần `replace` là một RPC. Trigger `BEFORE UPDATE` giữ `created_at` và chỉ đổi mốc trạng thái khi mã trạng thái đổi. Cột `status` có `CHECK` đúng ba mã. Test FR-011 gọi hàm ánh xạ với dòng giả, không cần kho. Test hợp đồng dùng `pytest.fixture` có sẵn, chạy cùng một coroutine trên hai bản. 129 test hiện có không đổi assertion và không cần Docker.

Đối chiếu từng lựa chọn nằm ở [research.md](./research.md). Phần dưới là bản rút để duyệt.

## Đã thấy và suy đoán

Đã thấy trong phiên này, ghi đủ ở [research.md](./research.md) mục 1:

- Commit `12079c0`: `request.scope.get("env")`, `getattr` cho `SUPABASE_URL` và `SUPABASE_KEY`, thiếu khi giá trị không phải `str` hoặc bằng `""`, header `apikey` cộng `DEFAULT_POSTGREST_CLIENT_HEADERS`, thêm `Authorization: Bearer` khi khóa bắt đầu bằng `eyJ`, `base_url` là URL bỏ slash cuối rồi cộng `/rest/v1`, `async with AsyncPostgrestClient`.
- `os.getenv` trong spike chỉ được ghi thành một cờ boolean. Client không đọc khóa từ `os.getenv`.
- Gói đã khóa: `postgrest` 2.31.0. `DEFAULT_POSTGREST_CLIENT_HEADERS` là `Accept` và `Content-Type` kiểu `application/json`. `rpc` POST gửi `params` làm thân JSON. `maybe_single().execute()` trả `None` khi kết quả rỗng. `order(..., foreign_table=)` có trong thư viện.
- `npm view supabase version` ngày 2026-10-25 trả `2.122.0`.

Suy đoán, chưa chạy lại Worker và chưa gọi PostgREST trong phiên này: service role của Supabase bỏ qua RLS; `gen_random_uuid()` in ra hex thường và là UUID phiên bản 4; một hàm Postgres trong một request PostgREST là một transaction; hình JSON mà RPC `returns jsonb` trả về có thể là object hoặc list một phần tử; `supabase status` in URL API và khóa service role dưới nhãn mà lệnh thực sự in. Test kho thật khóa các điểm này. Không đổi sang nhiều request ghi nếu hình RPC lệch.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: `postgrest` 2.31.0 đã có trong `pylock.toml`. Không thêm thư viện Python. Không thêm `package.json`. Supabase CLI chỉ qua `npx --yes supabase@2.122.0`. `src/core/plans.py` vẫn chỉ thư viện chuẩn. Pydantic cho dòng DB nằm ở `src/db/models.py`, Pydantic đã có qua FastAPI. Test async bằng `asyncio.run`. Không thêm `pytest-asyncio`.

**Storage**: Postgres local qua Supabase CLI, truy cập bằng PostgREST. Hai bảng `plans` và `subtasks`. Lược đồ chỉ trong `supabase/migrations/`. Không tạo bảng bằng tay trên dashboard.

**Testing**: `uv run pytest`. Test hiện có giữ nguyên assertion và dùng `MemoryPlanStore`. Test kho thật đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ môi trường tiến trình, trong `tests/supabase_plan_db.py`. Không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Hai giá trị được đưa vào dict cấu hình dưới khóa `SUPABASE_URL` và `SUPABASE_KEY`, vì đó là tên trên env của Worker. Thiếu biến, hoặc không kết nối được, thì `pytest.skip` với câu ở [contracts/plan-store.md](./contracts/plan-store.md). Host của URL không phải `127.0.0.1` hoặc `localhost` thì test thất bại với câu `Test kho chỉ chạy trên kho local.`, trước mọi lời gọi mạng, và không skip. `APIError` sau khi đã nối được là lỗi thật, không skip. Docker tắt thì 129 test hiện có vẫn chạy, cùng test ánh xạ FR-011 và test chặn host.

**Target Platform**: Store chạy trên CPython trong pytest và phải dựng được với env của Worker theo dạng spike. Lát này không thêm route và không gọi store từ `src/app.py`.

**Project Type**: Phần lưu trữ của web service. Không có endpoint sản phẩm mới.

**Performance Goals**: Một người dùng, theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Một lần ghi là một request HTTP. Ngân sách 3 giây của nguyên tắc VII áp khi có route từ jarvis-desktop; lát này không thêm route đó.

**Constraints**: Nguyên tắc II, III, VI, VIII trong [.specify/memory/constitution.md](../../.specify/memory/constitution.md). D-010, D-011, D-012 trong [docs/DECISIONS.md](../../docs/DECISIONS.md). Nguyên tắc III áp cho code trong `src/`: trong `src/` chỉ `src/db/client.py` import `postgrest` và gọi PostgREST. Helper test trong `tests/supabase_plan_db.py` được gọi PostgREST qua client dựng bằng factory của `src/db/client.py`, chỉ sau khi đã kiểm host là `127.0.0.1` hoặc `localhost`, cho hai việc: xóa dòng hai bảng và đọc hai mốc thời gian. `src/db` import `src/core`. `src/core` không import `db`, `tools`, `pydantic`, hay `fastapi`. `src/db` không import `src/tools`. `src/tools` không sửa. `Plan` và `Subtask` không thêm trường. `PlanStore` giữ đúng bốn phương thức. Không `os.getenv` cho `SUPABASE_URL` và `SUPABASE_KEY`. Không đọc, không ghi `.env` thật và `.dev.vars`.

**Scale/Scope**: Một bản store, một migration, cấu hình Supabase local, test hợp đồng trên hai bản, test mốc thời gian trên kho local, test ánh xạ trạng thái lạ và test chặn host không cần kho, test thiếu cấu hình không cần mạng.

## Các lựa chọn đã so

Bản đầy đủ, gồm phương án đã bỏ, nằm ở [research.md](./research.md).

**a. `replace` ghi hai bảng.** Chọn một hàm Postgres `replace_plan`, gọi bằng `client.rpc`, một request. Hàm cập nhật dòng kế hoạch, xóa việc con không còn trong danh sách, `UPDATE` việc còn danh tính, `INSERT` việc mới. Không xóa hết việc con rồi chèn lại. `add` cùng kiểu, một hàm `add_plan`, vì cùng một kiểu rách dữ liệu nếu tách request. Nếu mạng đứt giữa hai request của cách nhiều lời gọi, kho có thể mất một phần việc con trong khi phần kia đã ghi. Với một RPC, Postgres giữ một transaction: hoặc cả lần ghi vào, hoặc không lần nào vào. Response mất sau khi server đã commit thì người gọi thấy lỗi và dữ liệu đã đủ, không bị xé đôi. Đọc vẫn là `select` kèm việc con, vì đọc không cần transaction ghi.

**b. Mốc đổi trạng thái.** Chọn trigger `BEFORE UPDATE` trên `subtasks`. `UPDATE` không gửi hai cột mốc. Trigger gán lại `created_at` từ dòng cũ, và chỉ gán `status_changed_at = now()` khi mã trạng thái khác. Cùng mã thì giữ mốc cũ, kể cả khi tiêu đề hoặc ghi chú đổi. `INSERT` dùng default `now()` cho cả hai. Store so trạng thái trong Python rồi tự ghi mốc bị bỏ: thêm một vòng đọc, và một `UPDATE` quên cột sẽ làm sai FR-012 hoặc FR-013. Trigger không cứu được việc xóa rồi chèn lại cùng danh tính; hàm `replace_plan` phải `UPDATE` dòng còn danh tính.

**c. Trạng thái lạ.** Giữ `CHECK (status in ('pending', 'done', 'skipped'))` trên `subtasks.status`. CHECK chặn dữ liệu sai từ mọi nơi ghi. Ca thật của FR-011 là migration sau thêm mã mới trong khi code cũ đọc phải. Không có hàm ghi thẳng trạng thái trong `src/db/client.py`. `get` và `list` dùng chung một hàm ánh xạ trong `src/db`. Test gọi hàm đó với dòng giả có mã lạ, không cần kho, và ca đó luôn chạy. Câu lỗi giữ nguyên `Trạng thái việc con đã lưu không hợp lệ.` Câu đầu vào `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` không dùng cho dữ liệu đọc từ kho. Model Pydantic của dòng DB để `status: str`, không phải `Literal` ba mã, để lỗi Pydantic không thay câu này.

**d. Trạng thái đầu mỗi test kho.** Test tự xóa dòng `subtasks` rồi `plans` trong `tests/supabase_plan_db.py`, trước mỗi test kho. Helper dựng client bằng hàm factory của `src/db/client.py`. Hàm xóa không nằm trong `src/`. Trước lúc xóa và trước mọi lời gọi mạng, host phải là `127.0.0.1` hoặc `localhost`; host khác làm test thất bại, không skip. `npx --yes supabase@2.122.0 db reset` là cách dựng lại lược đồ, không phải bước bắt buộc trước mỗi `pytest`. FR-003 liệt kê mọi kế hoạch; dòng thừa làm sai kết quả nếu chỉ trông vào một lần reset tay.

**e. Hợp đồng trên hai bản.** Một coroutine các ca dùng chung. Một test pytest nhận fixture `params=["memory", "supabase"]`. Nhánh memory luôn chạy. Nhánh supabase skip khi thiếu `JARVIS_TEST_SUPABASE_URL` hoặc `JARVIS_TEST_SUPABASE_KEY`, hoặc khi host local không nối được. Host khác làm test thất bại, không skip. Không plugin pytest mới, không `pytest-asyncio`. `asyncio.run` như D-012.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

| Cổng | Kết quả | Cơ sở |
|------|---------|--------|
| I. Một nhân vật duy nhất | Đạt | Câu lỗi là hai câu trong spec. Không thêm tên nhân vật. |
| II. Worker không giữ trạng thái | Đạt | Store không giữ danh sách kế hoạch trong bộ nhớ tiến trình. Mỗi phương thức mở client rồi đóng. Không store tầm module. |
| III. Database qua PostgREST | Đạt | Không driver TCP. Nguyên tắc III áp cho code trong `src/`: chỉ `src/db/client.py` import `postgrest` và gọi PostgREST. Helper `tests/supabase_plan_db.py` gọi PostgREST qua client dựng bằng factory, chỉ sau khi host là `127.0.0.1` hoặc `localhost`, để xóa dòng hai bảng và đọc hai mốc thời gian. |
| IV. LLM qua lớp trung gian | Không áp dụng | Không gọi LLM. |
| V. Thông báo chủ động bằng remote push | Không áp dụng | Không gửi thông báo. |
| VI. Database riêng là nguồn sự thật | Đạt | Kế hoạch và việc con ghi vào Supabase. Không ghi Google Tasks hay Google Keep. |
| VII. Ngân sách độ trễ với jarvis-desktop | Không áp dụng | Không thêm lời gọi từ desktop. |
| VIII. Unit test bắt buộc | Đạt | Hợp đồng, mốc thời gian, ánh xạ trạng thái lạ, chặn host, và thiếu cấu hình có test. Cách chạy nằm ở [quickstart.md](./quickstart.md). |

Không có cổng thất bại. D-010 nói CRUD cơ bản không cần transaction phức tạp. `replace` của lát này cần một transaction để giữ `created_at` và không xé việc con. Đó vẫn là PostgREST. D-013 đã được người dùng duyệt ngày 2026-10-25 và được ghi ở T025.

### Sau Phase 1

Đã đối chiếu [research.md](./research.md), [data-model.md](./data-model.md), [contracts/plan-store.md](./contracts/plan-store.md), và [quickstart.md](./quickstart.md).

- `Plan`, `Subtask`, `SubtaskStatus`, và bốn chữ ký `PlanStore` giữ nguyên. Hai mốc không vào miền và không vào JSON tool.
- `src/db/plan_store.py` không import `postgrest` và không import `src/tools`. Lời gọi sản phẩm đi qua hàm của `src/db/client.py`. Helper test trong `tests/supabase_plan_db.py` là chỗ duy nhất ngoài `src/` gọi PostgREST, qua client dựng bằng factory, chỉ sau khi host là `127.0.0.1` hoặc `localhost`, để xóa dòng hai bảng và đọc hai mốc thời gian. Nguyên tắc III vẫn đạt. Chiều D-011 không đảo.
- `require_supabase` đọc dict hoặc object có attribute, đúng dạng spike. Không gọi `os.getenv` cho hai khóa. Thiếu hoặc `""` thì ném lỗi trước khi tạo `AsyncPostgrestClient`. Lời lỗi không chứa giá trị khóa.
- `MemoryPlanStore.replace` thêm một nhánh: không thấy id thì `PlanDomainError("Không có kế hoạch với danh tính này.")`. Các phương thức kia và assertion test cũ không đổi.
- Không phát sinh vi phạm mới.

## Project Structure

### Documentation (this feature)

```text
specs/006-supabase-plan-store/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── plan-store.md
└── tasks.md             # /speckit-tasks, không tạo ở bước này
```

### Source Code (repository root)

```text
src/config/
└── settings.py                  # require_supabase; bỏ os.getenv của SUPABASE_URL và SUPABASE_KEY

src/db/
├── client.py                    # chỗ duy nhất import postgrest và gọi PostgREST
├── models.py                    # Pydantic cho dòng plans và subtasks
└── plan_store.py                # SupabasePlanStore, bốn phương thức

src/core/
└── plans.py                     # không sửa

src/tools/                       # không sửa

supabase/
├── config.toml                  # do supabase init, không chứa khóa cloud
└── migrations/
    └── <timestamp>_plans_and_subtasks.sql

tests/
├── fakes/
│   └── memory_plan_store.py     # đúng một hành vi replace khi thiếu id
├── helpers.py                   # không sửa
├── supabase_plan_db.py          # đọc JARVIS_TEST_*, chặn host, xóa dòng hai bảng và đọc hai mốc bằng client của src/db/client.py
├── test_plan_store_contract.py  # cùng ca trên memory và supabase
├── test_supabase_plan_store.py  # mốc thời gian, NULL; skip hoặc thất bại host
├── test_plan_row_mapping.py     # FR-011 với dòng giả; luôn chạy, không kho
└── test_settings_supabase.py    # thiếu cấu hình, không mạng
```

`git grep -n -i spike -- src` không có dòng nào. `Test-Path src\api\routes_spike.py` là False. Nhánh này không có file spike trong `src/`. Lát này không thêm route và không nối `SupabasePlanStore` vào `src/app.py`.

**Structure Decision**: Nguyên tắc III áp cho code trong `src/`. Trong `src/`, chỉ `src/db/client.py` import `postgrest` và gọi PostgREST. `plan_store.py` là bản cài đặt cổng: đổi dòng thành `Plan`, ném `PlanDomainError`. File đó không mở HTTP và không import `postgrest`. Vì vậy đặt store ngoài `client.py` vẫn đúng nguyên tắc III. Model dòng DB ở `src/db/models.py` theo quy ước Pydantic cho schema DB trong constitution. Helper test trong `tests/supabase_plan_db.py` được gọi PostgREST qua client dựng bằng factory của `src/db/client.py`, chỉ sau khi đã kiểm host là `127.0.0.1` hoặc `localhost`, cho hai việc: xóa dòng hai bảng và đọc hai mốc thời gian. Factory vẫn là chỗ duy nhất tạo `AsyncPostgrestClient`.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.

## D-013 đã duyệt

D-013 đã được người dùng duyệt ngày 2026-10-25 và được ghi ở T025, vào cuối [docs/DECISIONS.md](../../docs/DECISIONS.md), cùng định dạng D-012. Bước plan không sửa file đó. Bản dưới là nội dung T025 ghi.

**D-013 — F03 ghi kế hoạch bằng một RPC PostgREST; trạng thái việc con có CHECK.**

Bối cảnh: D-010 chọn PostgREST vì CRUD không cần transaction phức tạp. FR-012 cấm làm mất `created_at` của việc còn danh tính. Mỗi request PostgREST là một transaction riêng, nên nhiều request cho một lần `replace` có thể dừng giữa chừng.

Quyết định: `add` và `replace` mỗi cái một hàm SQL, gọi bằng RPC của `postgrest`. Đọc bằng `select`. `status_changed_at` do trigger. Cột `status` có `CHECK (status in ('pending', 'done', 'skipped'))`. CHECK chặn dữ liệu sai từ mọi nơi ghi. Lần đọc vẫn báo trạng thái lạ khi dữ liệu đọc từ kho chứa mã mà bản code đang chạy chưa biết, như khi migration sau thêm mã trong khi code cũ còn đọc. RLS bật; `service_role` được grant; `anon` và `authenticated` không.

Phương án đã bỏ: nhiều lời gọi bảng cho một lần `replace`; store tự ghi mốc thời gian; bỏ `CHECK` để ghi một mã lạ vào kho lúc test.

T025 ghi đúng bản này vào cuối `docs/DECISIONS.md`. Không sửa D-010, D-011, D-012, hay mục nào khác.

## Docs cần cập nhật khi implement

Chưa sửa các file này ở bước plan.

- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), dòng Trạng thái code: nói logic F04 đến F08 vẫn ở core và tools; bản `PlanStore` Supabase nằm ở `src/db/` và chưa được route sản phẩm, Telegram, hay LLM gọi. Bỏ ý “chưa nối database” vì lúc đó store đã có.
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), mục `src/db`: `client.py` là chỗ duy nhất gọi PostgREST; `plan_store.py` là bản cổng; `models.py` là dòng DB. Hai mốc thời gian chỉ ở bảng việc con.
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), mục `src/config`: `settings.py` đọc `SUPABASE_URL` và `SUPABASE_KEY` từ nguồn người gọi truyền vào. Nguồn đó là dict hoặc env của Worker. Không đọc hai khóa đó bằng `os.getenv`.
- [AGENTS.md](../../AGENTS.md), lệnh: bật Supabase local, dựng lại DB, xem status, chạy pytest khi đã export URL và khóa service role vào tiến trình test dưới tên `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY`. Không dùng `SUPABASE_URL` hay `SUPABASE_KEY` cho pytest. Ghi rõ host phải là `127.0.0.1` hoặc `localhost`, nếu không test thất bại trước khi gọi mạng. `db reset` là dựng lược đồ; test tự xóa dòng trước mỗi ca kho, trong `tests/`, không trong `src/`. Ghim `npx --yes supabase@2.122.0`.
- [AGENTS.md](../../AGENTS.md), luật secret: thêm `.dev.vars` cạnh `.env` thật. Vẫn chỉ dùng `.env.example` làm mẫu tên biến. Không đọc, không ghi `.dev.vars`.
- [.env.example](../../.env.example): dòng `SUPABASE_KEY` đang nói anon hoặc service key. Sau lát này bản store cần khóa service role vì `anon` không được grant. Sửa lời chú thích. Không điền khóa thật.

[docs/PRODUCT.md](../../docs/PRODUCT.md) không sửa. Constitution không sửa ở lát này.

## Giới hạn đã biết

- Hai lần ghi cùng lúc có thể mất một lần. Spec đã chấp nhận. Không khóa, không thử lại.
- `created_order` là `GENERATED ALWAYS AS IDENTITY`. `replace` không đổi cột đó. Bản trong bộ nhớ thay cả object, nên một `Plan` tự dựng với `created_order` khác sẽ dính ở bộ nhớ và không dính ở Postgres. Không có người gọi hiện tại làm vậy. Hợp đồng không dựa vào `replace` đổi thứ tự tạo. Không sửa thêm `MemoryPlanStore` để khít điểm này, vì lát này chỉ được đổi một hành vi của file đó.
- Danh tính kế hoạch so đúng chuỗi canonical mà `str(uuid.UUID(...))` trả về, chữ thường, có gạch. `"1"`, `"2"`, và UUID viết hoa không thành một lần mở. Cột vẫn là `uuid`. Chi tiết ở research mục 6.
- Đưa lược đồ lên project Supabase cloud nằm ngoài lát này. `supabase start` và `db reset` chỉ cho kho local.
- Commit `12079c0` không có mặt trong cây `src/` của nhánh này. Lát này không thêm route spike.
