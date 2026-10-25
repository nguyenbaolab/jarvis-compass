# Research: Lưu kế hoạch vào kho Supabase

Quyết định cho F03. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Ràng buộc cách làm do người dùng chốt khi gọi `/speckit-plan`. Chiều phụ thuộc đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011. Cổng bốn phương thức async đã chốt ở D-012. Truy cập DB đã chốt ở constitution nguyên tắc III và D-010.

## 1. Spike 12079c0: đã thấy và suy đoán

**Đã thấy** khi `git show 12079c0` trong phiên lập plan. Commit đó thêm `src/api/routes_spike.py` và hai dòng gắn router trong `src/app.py`. Message commit nói nhánh giữ làm hồ sơ, không merge vào sản phẩm. Kiểm lại trên nhánh `006-supabase-plan-store`: `git grep -n -i spike -- src` không in dòng nào, `Test-Path src\api\routes_spike.py` là False. Cây `src/` của nhánh này không có file spike. Lát này không thêm route đó.

Trong `spike_db`:

- `env = request.scope.get("env")`. `env is None` thì trả 503, không đọc `os.environ`.
- `getattr(env, "SUPABASE_URL", None)` và `getattr(env, "SUPABASE_KEY", None)`.
- Giá trị không phải `str`, hoặc bằng `""`, được kể là thiếu. Spike không `strip`.
- Header là `{**DEFAULT_POSTGREST_CLIENT_HEADERS, "apikey": key_value}`. Khóa bắt đầu bằng `eyJ` thì thêm `Authorization: Bearer` cộng chính khóa đó. Nhánh kia chỉ có `apikey`.
- `base_url = url_value.rstrip("/") + "/rest/v1"`.
- `async with AsyncPostgrestClient(base_url, headers=headers)`.
- Ghi bằng `.from_("spike_ping").insert(...).execute()`. Đọc bằng `.select(...).order("created_at", desc=True).limit(3).execute()`, rồi dùng `read.data`.
- `os.getenv("SUPABASE_URL")` chỉ để điền cờ `os_getenv_sees_supabase_url`. Client không dùng giá trị đó.

**Đã thấy** ngoài commit, cùng phiên:

- `pylock.toml` khóa `postgrest` 2.31.0.
- Trong wheel đó, `DEFAULT_POSTGREST_CLIENT_HEADERS` là `Accept: application/json` và `Content-Type: application/json`.
- `AsyncPostgrestClient.rpc` với POST gán `params` vào thân JSON. Annotation viết `dict[str, str]`. Thân hàm không ép từng giá trị thành `str` trước khi đưa vào request.
- `AsyncMaybeSingleRequestBuilder.execute`: HTTP thành công và `data` rỗng thì trả `None`; đúng một phần tử thì trả phần tử đó.
- `BaseSelectRequestBuilder.order` có tham số `foreign_table`. Khi có, query param là `{bảng}.order`.
- `npm view supabase version` trả `2.122.0`.

**Lời trong commit và trong D-010, không chạy lại ở phiên này:** message commit nói `os.getenv` trống trên Worker. D-010 ghi một lần smoke `execute()` thất bại với ConnectError/DNS khi URL giả. Phiên plan không bật Worker và không gọi mạng tới Supabase.

**Suy đoán:**

- Role `service_role` của Supabase bỏ qua RLS. Grant và revoke vẫn cần, vì PostgREST từ chối role không được grant, và `anon` không có policy thì bị RLS chặn. Chưa kiểm trên kho local trong phiên này.
- `gen_random_uuid()` tạo UUID phiên bản 4 và PostgREST in hex chữ thường. `tests/helpers.py` đã khóa regex phiên bản 4 chữ thường cho id do store cấp. Test kho thật dùng cùng điều kiện đó. Nếu chuỗi đọc ra không khớp, dừng và hỏi, không nới regex.
- Một hàm SQL chạy trong một request PostgREST nằm trong một transaction của Postgres. Mạng đứt trước commit thì rollback. Response mất sau commit thì dữ liệu đã đủ và người gọi vẫn thấy lỗi. Chưa đo trên kho local.
- Hàm `returns jsonb` có thể về một object hoặc một list một phần tử. Spike chỉ cho thấy `read.data` của `.select()` là list. Bộ giải mã RPC khóa bằng test kho thật: nếu là list thì lấy phần tử đầu. Không thêm request ghi thứ hai để đọc lại.
- Nhãn mà `supabase status` in cho URL và khóa service role. Quickstart nói “giá trị lệnh status in ra”, không đoán tên biến của CLI. Implement đối chiếu output thật của `2.122.0` khi viết lệnh vào AGENTS.md.

## 2. Chỗ đặt store và nguyên tắc III

**Decision**: Nguyên tắc III áp cho code trong `src/`. Trong `src/`, chỉ `src/db/client.py` import `postgrest` và gọi PostgREST. `src/db/plan_store.py` chứa `SupabasePlanStore` với đúng bốn phương thức. Nó gọi hàm của `client.py`, đổi dòng Pydantic thành `Plan`, và ném `PlanDomainError`. `src/db/models.py` chứa model Pydantic của dòng DB. `plan_store.py` không import `postgrest` và không import `src/tools`. Helper test trong `tests/supabase_plan_db.py` được gọi PostgREST qua client dựng bằng factory của `src/db/client.py`, chỉ sau khi đã kiểm host là `127.0.0.1` hoặc `localhost`, cho hai việc: xóa dòng hai bảng và đọc hai mốc thời gian.

**Rationale**: Nguyên tắc III áp cho code trong `src/`. Trong `src/`, lời gọi PostgREST là lời gọi HTTP và chỉ nằm ở `src/db/client.py`. Đổi dòng thành `Plan` không phải truy cập DB. Tách file giúp thấy chỗ nào được phép import `postgrest`. D-011 đã đặt bản cài đặt thật ở `src/db/`, và cho `src/db` import `src/core`. Helper test không nằm trong `src/`. Nó chỉ gọi PostgREST sau kiểm host, để xóa dòng hai bảng và đọc hai mốc thời gian.

**Alternatives considered**: Để cả lớp store trong `client.py`. Cũng đúng nguyên tắc III, và là phương án nếu giải thích trên không đứng. Giải thích đứng, nên tách. Để store tự dựng `AsyncPostgrestClient` trong `plan_store.py`. Đó là đường truy cập thứ hai, không đúng câu “chỉ qua `src/db/client.py`”.

## 3. replace và add là một RPC

**Decision**: Migration tạo `add_plan(goal text, subtasks jsonb) returns jsonb` và `replace_plan(plan_id uuid, goal text, subtasks jsonb) returns void`. Store gọi mỗi hàm bằng một `client.rpc(...).execute()`. `replace_plan` không đọc giá trị trả về. Thân JSON là object tham số. Mảng việc con là một giá trị trong object đó. Annotation `dict[str, str]` của thư viện không đổi được; runtime gửi nguyên object. Test kho thật là chỗ xác nhận PostgREST nhận mảng đó. Nếu hình tham số bị từ chối, sửa kiểu tham số SQL hoặc hình JSON. Không tách thành nhiều request ghi.

`replace_plan` làm trong một transaction:

1. Không có dòng `plans.id` thì `raise` với mã ổn định `plan_missing`. Store bắt mã đó và ném `PlanDomainError` với đúng câu `Không có kế hoạch với danh tính này.` Câu tiếng Việt không ghép từ message SQL.
2. `UPDATE plans.goal`. Không đụng `created_order`.
3. `DELETE` việc con của kế hoạch mà danh tính không còn trong mảng.
4. `UPDATE` việc còn danh tính: `title`, `status`, `note`, `position`. Không có `created_at` và không có `status_changed_at` trong danh sách `SET`.
5. `INSERT` việc chưa có. Hai mốc để default.

`position` lấy từ thứ tự phần tử mảng (`WITH ORDINALITY`, gốc 0), không lấy từ đồng hồ. `note` JSON `null` thành SQL `NULL`. Store không gửi `""`.

`add_plan` `INSERT` kế hoạch, để `id` và `created_order` do DB cấp, rồi `INSERT` việc con. Cùng một transaction.

Đọc `get` và `list` dùng `.from_("plans").select(...)` kèm việc con, rồi store sắp xếp việc con theo `position`. `order(..., foreign_table="subtasks")` được gọi thêm. Mapper vẫn sắp theo `position` vì tham số `foreign_table` mới thấy trong chữ ký thư viện, chưa thấy chạy trên server.

**Rationale**: FR-012 giữ `created_at` của việc còn danh tính, nên không được xóa hết rồi chèn lại. Nhiều request PostgREST là nhiều transaction. Đứt mạng sau khi xóa việc thừa và trước khi cập nhật việc còn lại để lại một kế hoạch cụt. Một RPC thì hoặc đủ hoặc không có gì. `add` tách “insert kế hoạch” và “insert việc con” cũng cụt cùng kiểu, nên `add` dùng một RPC luôn. Đọc không ghi, nên `select` đủ.

**Alternatives considered**: `DELETE` mọi việc con của kế hoạch rồi `INSERT` lại. Mất `created_at`. Vài lời gọi `.update()` và `.insert()` từ Python. Đúng PostgREST từng request, và sai khi request giữa chừng mất. Store tự mở transaction bằng driver TCP. Constitution cấm.

## 4. Mốc thời gian do trigger

**Decision**: `created_at` và `status_changed_at` là `timestamptz not null default now()`. Trigger `BEFORE UPDATE` trên `subtasks`: `NEW.created_at = OLD.created_at`; nếu `NEW.status is distinct from OLD.status` thì `NEW.status_changed_at = now()`, ngược lại `NEW.status_changed_at = OLD.status_changed_at`. `INSERT` không cần trigger vì default chạy trong cùng statement, hai cột cùng một `now()` của transaction.

Hàm SQL ghi không gửi hai cột này trong `UPDATE`. Trigger vẫn chỉnh lại nếu một `UPDATE` sau này gửi nhầm.

**Rationale**: FR-013 đòi mốc trạng thái đổi khi và chỉ khi mã đổi. Đặt luật đó cạnh dòng thì lớp Python không có đường quên. `now()` trong một transaction là một mốc. Lần ghi sau là transaction sau, nên mốc mới khác mốc cũ khi trạng thái đổi. So “giữ nguyên” trong test là so đúng giá trị API trả về.

**Alternatives considered**: Store `SELECT` trạng thái cũ, so trong Python, rồi `UPDATE` kèm mốc. Thêm một request, và một lần quên cột làm sai FR-012. Dùng `clock_timestamp()` để đổi trong cùng transaction. Spec so hai lần ghi khác nhau; `now()` đủ, và hai default lúc insert bằng nhau đúng chuyện “cả hai là thời điểm của lần ghi đó”.

## 5. CHECK trạng thái; cách test FR-011

**Decision**: Cột `subtasks.status` là `text not null` với `CHECK (status in ('pending', 'done', 'skipped'))`. `src/db/client.py` không có hàm ghi thẳng trạng thái. `SubtaskRow.status` là `str`, không phải `Literal` ba mã, để lỗi Pydantic không thay câu đọc. `get` và `list` cùng gọi một hàm ánh xạ trong `src/db/plan_store.py`. Hàm đó chỉ nhận `pending`, `done`, `skipped`. Mã khác thì `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")` cho cả kế hoạch. Không trả `Plan`. Không sửa mã đó thành mã hợp lệ.

Test FR-011 nằm ở `tests/test_plan_row_mapping.py`. Nó gọi hàm ánh xạ với một dòng giả có mã lạ. Không tạo store, không đọc biến kho, không mở mạng. Ca này luôn chạy, kể cả khi Docker tắt.

`note` có `CHECK (note IS NULL OR note <> '')`. Ghi chú trống được kiểm trên kho thật: cột là `NULL`, miền là `None`.

**Rationale**: CHECK chặn dữ liệu sai từ mọi nơi ghi. Ca thật của FR-011 là migration sau thêm mã mới trong khi code cũ đọc phải. Dòng giả là dữ liệu đọc từ kho chứa trạng thái lạ, đúng tình huống bản đọc chưa biết mã mới. Không ghi mã lạ vào kho đang có CHECK.

**Alternatives considered**: Bỏ CHECK để test cắm mã lạ bằng PostgREST. Mọi nơi ghi đều đưa được dữ liệu sai vào kho. Tạm thả CHECK trong test. Kho test lệch migration. Coi lỗi CHECK lúc ghi là đủ cho FR-011. FR-011 là luật lúc đọc.

## 6. Danh tính UUID và so chuỗi

**Decision**: `plans.id` và `subtasks.id` là `uuid`. `plans.id` default `gen_random_uuid()`. Id việc con là id miền đã cấp, store ghi nguyên. `get` và `replace` chỉ coi một chuỗi là danh tính khi `uuid.UUID` phân tích được và `plan_id == str(uuid.UUID(plan_id))`. Chuỗi khác: `get` trả `None` và không gọi mạng; `replace` ném câu không có kế hoạch và không gọi mạng. UUID viết hoa không khớp vì `str(uuid.UUID)` là hex thường.

**Rationale**: Cột `uuid` của Postgres so không phân biệt hoa thường. Bản trong bộ nhớ so `==`. Test mở bằng id viết hoa đang kỳ vọng không có kế hoạch, trên bản bộ nhớ. Hợp đồng hai bản phải cùng kết quả. Chặn trước query giữ so chuỗi, và tránh phụ thuộc mã 400 mà PostgREST trả khi lọc `uuid` bằng `"1"`. Mã 400 đó là suy đoán; thiết kế không cần nó.

**Alternatives considered**: Cột `text`. Khớp so chuỗi mà không cần bước canonical, và yếu hơn kiểu `uuid` mà spec yêu cầu cho danh tính kế hoạch. Gửi mọi chuỗi xuống PostgREST rồi đổi 400 thành `None`. Phụ thuộc hình lỗi chưa thấy trong repo.

## 7. Cấu hình

**Decision**: `src/config/settings.py` thêm `SettingsError` và `require_supabase(source)`. `source` là `Mapping` thì đọc bằng `.get`. Không phải `Mapping` thì `getattr(source, name, None)`, cùng kiểu spike. Giá trị dùng được khi là `str` khác `""`. Ngược lại kể là thiếu, kể cả khi kiểu khác `str`. Không `strip`, vì spike không `strip`. Thiếu thì `SettingsError` với đúng một trong ba câu: `Thiếu SUPABASE_URL.`, `Thiếu SUPABASE_KEY.`, `Thiếu SUPABASE_URL và SUPABASE_KEY.` Câu không chứa giá trị nào đã truyền.

`SupabasePlanStore.__init__` gọi `require_supabase` trước mọi lời tạo `AsyncPostgrestClient`. Header và `base_url` lắp đúng công thức spike, trong `client.py`.

Xóa hai dòng module `SUPABASE_URL` và `SUPABASE_KEY` đang gọi `os.getenv`. `ANTHROPIC_API_KEY` và `TELEGRAM_BOT_TOKEN` giữ `os.getenv`. Phiên này không thấy file Python nào khác đọc hai hằng Supabase. Implement grep lại; nếu có người gọi, dừng và hỏi.

Test luôn chạy: truyền `{}` trong khi `os.environ` của tiến trình đang có hai biến sentinel. Kỳ vọng `SettingsError`, chứng minh hàm không đọc môi trường tiến trình. Truyền dict và truyền object attribute đều được. Giá trị khóa sentinel không xuất hiện trong `str(error)`.

Test kho thật, trong `tests/supabase_plan_db.py`, đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ môi trường tiến trình. Không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Helper đưa hai giá trị vào dict dưới khóa `SUPABASE_URL` và `SUPABASE_KEY`, rồi truyền dict đó cho `require_supabase`. Đó là người gọi, đúng FR-015. `settings.py` vẫn không gọi `os.getenv` cho hai khóa này. Test `{}` đặt sentinel vào cả bốn tên trong `os.environ` và vẫn kỳ vọng `SettingsError`.

**Rationale**: Trên Worker, spike lấy secret từ `request.scope["env"]` vì môi trường tiến trình không phải chỗ đó. Test cần truyền dict. Một hàm nhận nguồn người gọi phủ cả hai. Đọc `os.getenv` bên trong `settings.py` sẽ lấy nhầm môi trường tiến trình khi Worker để trống, và test “dict trống phải thất bại” sẽ không đứng nếu tiến trình lại có biến.

**Alternatives considered**: Giữ hằng module và thêm hàm mới song song. Hai đường đọc, dễ gọi nhầm `os.getenv`. Đọc `os.environ` trong `require_supabase` khi dict thiếu khóa. Trái “thiếu là thất bại” và trái lệnh không dùng `os.getenv` cho hai tên này.

## 8. Test kho bắt đầu từ bảng rỗng

**Decision**: Hàm xóa hai bảng nằm ở `tests/supabase_plan_db.py`, không nằm trong `src/`. Helper dựng client bằng hàm factory của `src/db/client.py`, rồi xóa `subtasks` rồi `plans`. Cùng file đó, sau cùng kiểm host, đọc hai mốc thời gian bằng client của factory. Không thêm hàm đọc này vào `src/`. Fixture gọi helper sau khi host đã được chấp nhận và sau khi probe nối được, trước mỗi test kho. `db reset` không phải bước pytest.

Trước mọi lời gọi mạng, và trước lúc tạo client: host của `JARVIS_TEST_SUPABASE_URL` phải là `127.0.0.1` hoặc `localhost`. Tên `localhost` không phân biệt hoa thường. Host khác, gồm `[::1]` và URL không có host, làm test thất bại với đúng câu `Test kho chỉ chạy trên kho local.` Không skip. Một test luôn chạy gọi kiểm tra này với URL host xa và khóa giả, kỳ vọng câu đó, và factory không được gọi.

Probe là một `select` giới hạn 0 dòng, chỉ khi host đã là local. `httpx.ConnectError` và `httpx.TimeoutException` thì skip với câu `Kho local không chạy: không kết nối được.` Thiếu biến thì skip với câu nêu `JARVIS_TEST_SUPABASE_URL` hoặc `JARVIS_TEST_SUPABASE_KEY`, mở đầu `Kho local không chạy:`. Không chèn `str(exception)` vào câu skip, vì message lỗi có thể chứa secret. `APIError` sau khi đã nối, gồm bảng chưa có hoặc grant sai, làm test thất bại.

`httpx` đã có trong nhóm dev của `pyproject.toml`. Không thêm gói. D-010 ghi `execute()` có thể nổi ConnectError; phiên này không chạy lại. Nếu Docker tắt mà exception là kiểu khác, implement thêm đúng kiểu đó vào nhánh skip. Không bắt `Exception` rồi skip hết.

**Rationale**: FR-003 trả mọi kế hoạch đang có. Dòng sót làm liệt kê sai. Reset tay dễ quên. `db reset` áp lại migration, nặng hơn một lần xóa dòng, và là việc của người khi đổi lược đồ. Xóa nằm trong `tests/` để `src/` không có đường xóa hết bảng. Kiểm host trước mạng để biến trỏ nhầm kho cloud không bị xóa.

**Alternatives considered**: Hàm xóa trong `src/db/client.py`. Đường xóa nằm trong mã sản phẩm. Đọc `SUPABASE_URL` của tiến trình cho test. Trùng tên secret của Worker, dễ trỏ nhầm kho cloud. Host lạ thì skip. Skip giấu việc biến đang trỏ ra ngoài máy. Viết trong quickstart “hãy reset trước khi pytest” và không xóa trong test. Một lần quên là fail giả.

## 9. Một bộ ca, hai bản, không plugin mới

**Decision**: `tests/test_plan_store_contract.py` có một coroutine nhận `PlanStore`. Fixture trong chính file đó, `params=["memory", "supabase"]`. `memory` trả `MemoryPlanStore()`. `supabase` gọi `tests/supabase_plan_db.py`: đọc hai biến `JARVIS_TEST_*`, chặn host, probe, xóa bảng, trả `SupabasePlanStore`. Skip nằm trong fixture của riêng param supabase khi thiếu biến hoặc không nối được. Host không phải local thì param đó thất bại, không skip. Test gọi `asyncio.run` trên coroutine. Không `conftest.py` mới, không thư viện pytest mới.

Ca dùng chung là những việc cả hai bản làm được: thêm, thứ tự liệt kê, mở đúng id, mở id không có kể cả `"1"` và `"2"`, `replace` id không có thì đúng câu và không thêm kế hoạch, vòng trạng thái, thêm việc, ghi chú và xóa ghi chú thành không có ghi chú, chữ Việt, thứ tự việc con khi liệt kê và khi mở.

Mốc thời gian và cột `note` là `NULL` nằm ở `tests/test_supabase_plan_store.py`. Những test đó skip khi thiếu biến hoặc không nối được, và thất bại trước mạng khi host không phải local. Trạng thái lạ không nằm ở file đó. Ca FR-011 nằm ở `tests/test_plan_row_mapping.py` và luôn chạy. Bản bộ nhớ không có cột mốc. `Subtask.status` không chứa mã lạ nếu không đổi miền; dòng giả đi qua hàm ánh xạ trong `src/db`, không qua `MemoryPlanStore`.

`MemoryPlanStore.replace`: hết vòng mà không thấy id thì ném `PlanDomainError("Không có kế hoạch với danh tính này.")`. Import thêm `PlanDomainError`. Không sửa phương thức khác. Phiên này đọc `tests/` và không thấy test nào `replace` một id không có. `ReplaceCounter` trong `tests/helpers.py` gọi `super().replace` sau khi đếm; các ca đếm hiện chỉ replace kế hoạch đang có, hoặc không gọi replace. Nếu lúc implement thấy một test cũ phụ thuộc im lặng, dừng và hỏi. Không sửa assertion test đó.

**Rationale**: Pytest có sẵn param trên fixture. Một coroutine khóa “cùng các tình huống”. D-012 đã cấm thêm plugin pytest khi `asyncio.run` đủ.

**Alternatives considered**: Hai file test chép ca. Lệch ngay lần sửa thứ nhất. `pytest-asyncio`. Thêm dependency, D-012 đã bỏ. Hook `pytest_generate_tests` trong `conftest.py`. Cũng không cần plugin, và khó thấy hơn một fixture nằm cạnh test.

## 10. RLS, grant, CLI

**Decision**: Một file migration. `enable row level security` trên cả hai bảng. Không tạo policy cho `anon` hay `authenticated`. `revoke all` trên hai bảng và trên hai hàm RPC khỏi `public`, `anon`, `authenticated`. `grant select, insert, update, delete` hai bảng cho `service_role`. `grant usage, select` trên sequence identity cho `service_role`. `grant execute` hai hàm RPC cho `service_role`. Hàm trigger `revoke execute` khỏi mọi role PostgREST dùng, để nó không thành RPC. Hàm ghi đặt `search_path = public`.

`unique (plan_id, position) deferrable initially deferred` để một transaction xếp lại vị trí mà không vướng unique giữa chừng. `created_order` unique. Xóa kế hoạch kéo việc con bằng `on delete cascade`. Test vẫn xóa việc con trước, cho rõ.

`npx --yes supabase@2.122.0 init` tạo `supabase/config.toml`. Không tạo `package.json`. Lược đồ không viết vào `config.toml` hay `seed.sql`. Không ghi khóa cloud vào `config.toml`. JWT local mà CLI sinh cho máy dev được nằm trong `config.toml` nếu `init` viết nó; đó không phải khóa project cloud và không phải nội dung `.dev.vars`.

**Rationale**: Người dùng chốt RLS, grant rõ cho `service_role`, không cấp cho `anon` hay `authenticated`, lược đồ chỉ trong `supabase/migrations/`, CLI qua npx với phiên bản ghim. `2.122.0` là bản `npm view` trả về ngày lập plan.

**Alternatives considered**: Policy RLS cho `service_role`. Role này được mô tả là bỏ qua RLS; đó là suy đoán, nên grant tường minh vẫn là phần bắt buộc, và policy không thay grant. Cài CLI bằng `package.json`. Người dùng cấm thêm file đó.
