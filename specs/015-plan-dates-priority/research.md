# Research: Ngày, ưu tiên và sức của kế hoạch

Các mục dưới là quyết định của `/speckit-plan`. Hướng trong chat là gợi ý. Chỗ chọn khác gợi ý có lý do ngay trong mục đó. Spec FR-001 đến FR-020 không bị quyết lại.

## 1. Đưa ngày vào lượt

**Decision:** `run_turn` nhận `instant` là tham số keyword bắt buộc, không có giá trị mặc định. Hai chỗ gọi truyền mốc: `src/api/telegram_update.py` truyền `now` đã có trong `handle_update`, và `evals/turn.py` truyền mốc của ca (bộ v2) hoặc một mốc cố định của cả lần chạy bộ v1. Đầu lượt đọc `instant` một lần. Mọi lần gọi mô hình trong lượt đó dùng cùng mốc, kể cả khi lượt qua nửa đêm.

`run_turn` dựng một `TurnContext` và giữ nó đến khi lần gọi đó trả về. Đối tượng chứa `instant` vừa đọc và cờ `clash_reported` bắt đầu bằng false. `run_turn` đưa cùng một đối tượng vào mọi `execute_tool` của lượt, tham số keyword `turn`. `execute_tool` vẫn gọi được khi không truyền `turn`: sáu tool cũ không đọc nó. `reschedule_subtasks` không có `turn` thì lỗi tool, không đoán mốc, không ghi. `run_turn` không rẽ theo tên tool và không đọc chữ kết quả. Tool tự đặt cờ trên đối tượng nó nhận. Chi tiết cờ ở mục 6. `moved_at` của lần dời ngày là `instant` của ngữ cảnh này, không phải một lần đọc đồng hồ khác.

Kiểu `TurnContext` nằm ở `src/tools/base.py`, cạnh `ToolResult`. Dataclass không đóng băng, vì tool ghi cờ. File đổi: `src/tools/base.py`, `src/tools/tool_router.py`, `src/tools/plan_tools.py`, `src/turns/llm_turn.py`. `src/tools` không import `db`. Kiểu này chỉ có `datetime` của thư viện chuẩn và một boolean. `check.ps1` cấm `src/tools` import `db` và cấm `src/core` import `tools`. Đặt kiểu ở `tools` nên `llm_turn` import `tools`, việc file đó đã làm, và core không phải import `tools`. `src/turns` không được import `db`. Kiểu này không kéo `db` vào.

Dòng ngày là hàm thuần `turn_date_line(instant) -> str` trong module mới `src/core/clock.py`. `run_turn` ghép dòng đó vào sau hằng `SYSTEM_PROMPT`, không sửa hằng. Mốc không có `tzinfo` thì hàm ném `ValueError`, cùng luật với `helsinki_clock` hiện tại.

Tên thứ tiếng Việt nằm ở một hàm `weekday_name_vi(day: date) -> str` trong cùng file. Digest và dòng ngày đều gọi hàm này. Bảy chữ: thứ Hai, thứ Ba, thứ Tư, thứ Năm, thứ Sáu, thứ Bảy, Chủ nhật.

`helsinki_clock` chuyển sang `src/core/clock.py`. `src/core/morning.py` import rồi gán lại tên `helsinki_clock`, nên `from core.morning import helsinki_clock` vẫn đúng với test spec 014. File đổi vì tách module: `src/core/clock.py` (mới), `src/core/morning.py` (re-export và `render_digest`), `src/turns/llm_turn.py`.

Bộ v1 không thêm mốc vào từng ca. Lần chạy v1 dùng một mốc cố định `2026-11-06T08:00:00+02:00` (thứ Sáu, giờ Helsinki mùa đông). Cách chấm v1 không đọc mốc này.

Code không phân tích câu "cuối tuần này" hay "thứ Sáu tuần sau". Mô hình đọc dòng ngày và luật FR-019 trong lời hướng dẫn, rồi ghi ngày ISO vào tool. Eval chấm ngày đã lưu.

**Rationale:** `execute_tool` hôm nay có `remaining: Remaining = None`. Bỏ sót tham số thì hạn chờ biến mất mà không lỗi. D-021 đã ghi bài học đó. `instant` không được lặp lại kiểu mặc định: chỗ gọi bỏ sót phải lỗi lúc chạy test. Ghép dòng vào lời hướng dẫn giữ một kênh, và hằng prompt vẫn khóa được bằng test. Tách `clock.py` để lượt mô hình không phụ thuộc luật digest, trong khi test spec 014 không đổi câu import.

**Alternatives considered:** Để `instant` mặc định `datetime.now(timezone.utc)` — bỏ, vì test và eval sẽ đọc đồng hồ máy. Nhét ngày vào tin người dùng — bỏ, vì tin đó sẽ vào ngữ cảnh hội thoại và thành lời chủ bot. Để `helsinki_clock` chỉ ở `morning.py` và cho `llm_turn` import `morning` — bỏ, vì lượt không nên phụ thuộc bản tin sáng. Viết bộ phân tích tiếng Việt trong Python — bỏ, vì FR-019 là luật cho mô hình, và eval đã chấm ngày lưu ra. Đặt `TurnContext` trong `src/core` — bỏ, vì cờ trùng là việc của vòng tool, không phải trường của kế hoạch, và core không được import `tools` nên chiều phụ thuộc sẽ ngược. Để `run_turn` tự nhớ cờ bằng cách đọc tên tool — bỏ, ở mục 6.

## 2. Model `src/core`

**Decision:** `Plan` thêm `priority: Priority | None = None`. `Subtask` thêm `scheduled_on: date | None = None` và `effort: Effort | None = None`. Hai trường mới đứng cuối dataclass, có mặc định, nên mọi lời gọi hiện tại vẫn dựng được.

`Priority` là `StrEnum` với `HIGH = "high"`, `MEDIUM = "medium"`, `LOW = "low"`. `Effort` là `StrEnum` với `S`, `M`, `L`. Chữ chủ bot nghe là cao, vừa, thấp. Mã lưu map một-một. Số giờ nằm một chỗ: hằng `EFFORT_HOURS = {S: 1, M: 3, L: 6}` trong `src/core/plans.py`. Vòng này không cộng giờ.

Hàm thuần, chỉ thư viện chuẩn:

- `plan_deadline(plan) -> date | None`: ngày muộn nhất trong các việc `pending` có ngày. Xong và bỏ qua không tính. Không việc chưa làm nào có ngày thì `None`.
- `deadline_clash(after, others) -> Plan | None`: hạn của `after` sau lần dời, nếu là một ngày và bằng hạn của một kế hoạch trong `others`. Kế hoạch cùng id với `after` không tính. Không đổi hạn so với bản trước thì không gọi hàm này để chặn ghi.
- `date_moves(before, after) -> tuple[Subtask, ...]`: việc có ngày cũ và ngày mới đều khác `None` và khác nhau. Trống sang ngày, ngày sang trống, và đặt lại đúng ngày đang có không nằm trong kết quả.

Kiểm `scheduled_on` bằng `date.fromisoformat`. Sai thì `PlanDomainError`. Enum sai cũng `PlanDomainError`. Store không chuẩn hóa lại.

`_plan_with_subtasks` phải chép `priority=plan.priority`. Nếu chỉ dựng lại các trường cũ, ưu tiên bị rơi.

`normalize_new_plan` đổi đầu vào việc con từ `list[str] | None` sang danh sách đối tượng có tiêu đề, ngày và sức tùy chọn. `new_subtask` nhận thêm ngày và sức, mặc định trống.

Chỗ dựng `Plan` hoặc `Subtask` phải giữ được nhờ mặc định, và chỗ nào chép plan phải chép `priority`:

- `src/core/plans.py`: `new_subtask`, `_plan_with_subtasks`
- `src/db/plan_store.py`: `plan_from_row`
- `tests/fakes/memory_plan_store.py`: `add`, và `replace` nếu dùng `dataclasses.replace`
- `evals/store.py`: dựng `Subtask` từ seed
- Test gọi tường minh: `tests/test_llm_turn.py`, `tests/test_telegram_update_flow.py`, `tests/test_morning_run.py`, `tests/test_morning_text.py`, `tests/test_tool_router.py`, `tests/test_store_call_limit.py`, `tests/test_supabase_plan_store.py`, `tests/test_plan_store_contract.py`, `tests/test_eval_score.py`, `tests/test_get_plans.py`

`PlanJson` thêm `priority: Literal["high", "medium", "low"] | None`. `SubtaskJson` thêm `scheduled_on: str | None` (ngày ISO hoặc null) và `effort: Literal["S", "M", "L"] | None`. Không có lịch sử dời trong hai schema này.

**Rationale:** Mặc định `None` là cách duy nhất để hàng trăm lời dựng hiện tại không vỡ, và trống vẫn là giá trị hợp lệ của spec. Mã `high`/`medium`/`low` cùng kiểu với `pending`/`done`/`skipped`. Hàm thuần để test không cần kho.

**Alternatives considered:** Trường bắt buộc không mặc định — bỏ, vì mọi fixture vỡ. Lưu chữ "cao" trong cột — bỏ, vì trạng thái đang lưu mã và chữ hiển thị nằm ở biên tool. Nhét lịch sử vào `Plan` — bỏ, vì vòng này không có đường đọc lịch sử cho mô hình.

## 3. Đường ghi lịch sử

**Decision:** Chọn phương án (a). `replace_plan` trong SQL so ngày đang lưu với ngày trong payload. Việc nào đi từ một ngày sang một ngày khác thì câu lệnh INSERT một dòng trong cùng hàm, cùng transaction với UPDATE kế hoạch. Core vẫn có `date_moves` để test và để tool biết mình định ghi gì. Tool không thể ghi ngày mà bỏ dòng lịch sử, vì SQL tự chèn.

`move_reason text` và `moved_at timestamptz` là tham số của RPC, không gọi `now()` trong SQL. Tool dời ngày truyền lý do (null nếu chủ bot không nói) và mốc giờ của lần ghi. Đổi trạng thái hay ghi chú không đổi ngày nên không có dòng, dù hai tham số là null.

Khóa ngày sang trống và trống sang ngày không INSERT. Đặt lại đúng ngày đang có không INSERT.

Không khóa ngoại từ bảng lịch sử sang `subtasks` hay `plans`. Một trigger `BEFORE UPDATE OR DELETE` trên bảng lịch sử làm `RAISE EXCEPTION`. `replace_plan` hiện xóa việc con không còn trong payload. `ON DELETE CASCADE` sẽ xóa lịch sử, trái FR-007. `ON DELETE RESTRICT` sẽ làm lần ghi đang hợp lệ bị lỗi khi payload bỏ một việc đã từng dời ngày. Test kho hiện có ca bỏ một việc con. Không khóa ngoại thì dòng lịch sử còn, vẫn mang `subtask_id`. Trigger chặn sửa và xóa dòng đó.

`PlanStore.replace` thêm hai tham số keyword, mặc định `None`: `move_reason` và `moved_at`. Lời gọi hiện tại không truyền chúng vẫn chạy. Chỉ `reschedule_subtasks` truyền lý do và mốc. Mốc lấy từ `TurnContext.instant` của mục 1. `SupabasePlanStore` chuyển hai giá trị đó xuống RPC, và luôn gửi `plan.priority` trong `plan_fields` (mục 4). Đồ giả làm cùng hai việc.

`PlanStore.add` thêm `priority` keyword, mặc định `None`. Lời gọi đang có, hai tham số vị trí, vẫn chạy. `add_plan` đặt ngày lần đầu không viết lịch sử. Đúng FR-008.

Không tool đọc lịch sử. `PlanJson` không có lịch sử. Test Supabase đọc bảng bằng PostgREST trong `tests/`, đúng ngoại lệ constitution III. `MemoryPlanStore` giữ một danh sách dòng lịch sử trên instance và `replace` của đồ giả áp cùng luật `date_moves`, để bộ chấm eval đọc được. Class này vẫn chỉ ở `tests/fakes/`.

`empty_plan_tables` trong `tests/supabase_plan_db.py` xóa `subtasks` rồi `plans`. Nó không xóa được dòng `subtask_date_moves`: trigger chặn `DELETE`, và bảng không có khóa ngoại nên xóa kế hoạch cũng không xóa dòng lịch sử. Test kho kiểm lịch sử theo `plan_id` và `subtask_id` của chính lần ghi đó, không theo tổng số dòng trong bảng. Dòng sót của test trước được phép còn đến khi `db reset`. `db reset` dựng lại lược đồ và dọn bảng. Không sửa helper để tắt trigger.

**Rationale:** Bất biến nằm cạnh dữ liệu. Mọi đường gọi `replace_plan`, kể cả đường chưa nghĩ ra, đều không bỏ qua dòng lịch sử. Không `now()` trong SQL để test truyền mốc và để cùng kiểu với RPC kênh.

**Alternatives considered:** (b) core tính danh sách rồi store ghi kế hoạch và lịch sử trong một RPC mới — bỏ. RPC vẫn là một transaction, nhưng nếu một đường khác gọi `replace_plan` cũ thì mất dòng. Khóa ngoại `ON DELETE CASCADE` — bỏ, vì xóa lịch sử. `ON DELETE RESTRICT` — bỏ, vì chặn việc bỏ một việc con đã có lịch sử, khác hành vi kho hiện tại. Cho `empty_plan_tables` xóa lịch sử bằng cách tắt trigger — bỏ, vì helper test sẽ phá luật chỉ thêm mà migration vừa dựng.

## 4. Migration tương thích ngược

**Decision:** Một file migration mới. Không sửa bốn file migration đã có.

Cột mới, tất cả cho phép trống:

- `plans.priority text`, kiểm chỉ `high`, `medium`, `low` hoặc null
- `subtasks.scheduled_on date`
- `subtasks.effort text`, kiểm chỉ `S`, `M`, `L` hoặc null

`replace_plan` được tạo lại trong cùng transaction, vẫn `returns boolean`. Migration `drop function` đúng chữ ký bốn tham số đang có, rồi tạo hàm mới. `create or replace` không đổi được chữ ký, và nếu hàm bốn tham số còn thì lời gọi bốn tên vẫn trúng hàm cũ. Ba tham số mới đứng cuối và có `DEFAULT NULL`: `plan_fields jsonb`, `move_reason text`, `moved_at timestamptz`. Lời gọi bốn tham số của Worker bản cũ vẫn khớp hàm mới. PostgREST điền mặc định. Cấp lại `grant execute` cho `service_role` và `revoke` khỏi `public`, `anon`, `authenticated`, cùng kiểu migration `20261105150000`.

`plan_fields` null, hoặc object không có khóa `priority`, thì giữ `plans.priority` đang lưu. Khóa `priority` có mặt thì đặt giá trị đó. JSON null là xóa ưu tiên. `SupabasePlanStore.replace` luôn gửi khóa này, lấy từ `plan.priority`. `None` trên model thành JSON null. `MemoryPlanStore.replace` gán ưu tiên từ `Plan` cùng cách: `None` là xóa. Worker cũ không gửi `plan_fields`, nên ưu tiên đã lưu còn.

Trong vòng lặp việc con, cùng luật với `priority`. Khóa `scheduled_on` hoặc `effort` không có trong JSON thì giữ giá trị đang lưu. Khóa có mặt thì đặt. JSON null là xóa. Không được làm như `note`: `note` vắng mặt đang thành null. Nếu ngày vắng mặt thành null, Worker cũ sẽ xóa ngày vừa lưu ở khoảng giữa `db push` và deploy. Bản store mới luôn gửi hai khóa này từ `Subtask`, kể cả khi trường là `None`, để một lần xóa ngày hoặc xóa sức đi tới được SQL.

`add_plan` thêm `priority text DEFAULT NULL`. Migration `drop function` đúng chữ ký hai tham số `add_plan(text, jsonb)` rồi tạo hàm ba tham số. Giữ hàm cũ thì lời gọi hai tên thành mơ hồ hoặc vẫn trúng hàm không có cột ưu tiên. Lời gọi hai tham số của Worker cũ vẫn khớp nhờ mặc định. Hàm vẫn trả object kế hoạch, không void. Cấp lại quyền như hàm hiện tại. Ngày và sức vẫn là khóa tùy trong từng phần tử jsonb của lần tạo: khóa vắng thì ghi null, vì dòng việc chưa có giá trị để giữ. Worker cũ tạo kế hoạch không gửi hai khóa và không gửi `priority`, nên việc mới có ngày trống và kế hoạch mới không có ưu tiên. `PlanStore.add` nhận `priority` keyword, mặc định `None`, và bản Supabase đưa xuống tham số RPC. Đồ giả lưu cùng trường.

`wrangler rollback` về Worker cũ sau khi migration đã áp là an toàn. Worker cũ không gửi `plan_fields`, không gửi khóa `scheduled_on` và `effort`, và gọi `add_plan` với hai tham số. Luật "khóa vắng thì giữ" giữ ngày, sức và ưu tiên đã lưu. Worker cũ chỉ không đặt được ba trường đó. Rollback DB, nghĩa là gỡ migration này, không được hỗ trợ. Không viết migration xuống.

`_PLAN_COLUMNS` của `list_plans` và `get_plan` thêm `plans.priority`, `subtasks.scheduled_on`, `subtasks.effort`. `PlanRow` thêm `priority`. `SubtaskRow` thêm `scheduled_on` và `effort`, mặc định `None` để hàng cũ không khóa vẫn qua Pydantic trong lúc đọc. `plan_from_row` đưa ba trường vào model miền. Không select bảng lịch sử vào `Plan`.

RPC vẫn trả giá trị, không void. `replace_plan` trả `true`. Python bản mới vẫn không cần đọc boolean để biết thành công. Lỗi vẫn là `plan_missing` và `plan_version_conflict`.

Thứ tự đẩy cloud và cửa sổ an toàn nằm ở [quickstart.md](./quickstart.md).

**Rationale:** Trade-off D-021 nói lần đổi chữ ký `replace_plan` làm tool ghi của Worker cũ lỗi giữa `db push` và deploy. D-023 cấm RPC void và đã dùng `drop function` rồi tạo lại vì `create or replace` không đổi chữ ký. Default, việc bỏ đúng chữ ký cũ, và luật "khóa vắng thì giữ" đóng lỗ đó cho cả ngày, sức và ưu tiên. Ưu tiên không nằm trong jsonb việc con, nên nó cần một tham số riêng. `add_plan` nhận nó lúc tạo. `replace_plan` nhận nó lúc sửa, kể cả lần sửa không phải tool ưu tiên, vì mọi `replace` đều ghi lại cả kế hoạch.

**Alternatives considered:** Đổi tên RPC thành `replace_plan_v2` và để hàm cũ — bỏ, vì hai đường ghi. Bắt Worker mới deploy trước migration — bỏ, vì tham số lạ làm RPC cũ lỗi. Coi ngày vắng mặt là xóa ngày — bỏ, vì Worker cũ không gửi khóa ngày. Nhét `priority` vào jsonb việc con — bỏ, vì ưu tiên là cột của `plans` và FR-004 cấm ưu tiên trên việc con. Giữ cả hai chữ ký `add_plan` — bỏ, vì PostgREST không biết lời gọi hai tên phải vào hàm nào. Viết migration xuống để gỡ cột — bỏ, vì rollback được hỗ trợ là Worker cũ trên schema mới, không phải schema cũ dưới Worker mới.

## 5. Catalog tool phiên bản 3

**Decision:** `DEFINITIONS_VERSION = 3`. Chín tool: sáu tool hiện có (`create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, `add_subtask`, `set_subtask_note`) cộng `set_plan_priority`, `set_subtask_effort`, `reschedule_subtasks`. Schema đầy đủ ở [contracts/tools.md](./contracts/tools.md).

`_type_error` hôm nay chỉ nhận `string` và `array` của chuỗi, rồi ném `TypeError` với kiểu khác. Phải mở:

- `boolean`
- `null` cho ưu tiên, sức và ngày được phép trống
- `array` mà phần tử là object, không chỉ chuỗi
- object lồng với `additionalProperties: false`, kiểm đệ quy

Dòng log tool giữ bảy khóa, đúng thứ tự `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`. Dòng log mô hình giữ tám khóa, đúng thứ tự `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`. Chỉ giá trị `definitions_version` và `prompt_version` đổi số.

**Rationale:** Tên ba tool nói đúng một việc mỗi tool, đúng FR-018. Mở kiểm kiểu là điều kiện để `create_plan` nhận mảng đối tượng và cờ xác nhận là boolean. Giữ tập khóa log vì spec 008 đã khóa tập đó.

**Alternatives considered:** Nhét ưu tiên, sức và ngày vào `update_subtask` — bỏ, vì FR-018 cấm tool đổi trạng thái đụng ba trường đó. Để catalog nhận object mà không kiểm `additionalProperties` của object lồng — bỏ, vì mô hình có thể nhét ngày vào một khóa lạ và tool bỏ qua im lặng.

## 6. Ca trùng và cờ xác nhận

**Decision:** Kết quả trùng là một `ToolResult` thành công, `effect` là `None`, chữ trả cho mô hình nêu kế hoạch kia và hạn. Không phải `ToolError`, không phải `Saved`, không phải `Abandoned`, không phải `Rejected`. `compose` của D-021 chỉ ghép ba hiệu lực đó, nên kết quả trùng không lọt vào bản ghép.

Tìm trùng: tool gọi `list_newest_first`, core tính `plan_deadline` của các kế hoạch khác. Không thêm phương thức store. Phép đọc này không cùng transaction với lần ghi. Khóa `version` chỉ bảo vệ kế hoạch đang dời. Hạn kế hoạch khác có thể đổi giữa lúc đọc và lúc ghi. Với một chủ bot, cửa sổ đó chấp nhận được. Không bịa thêm RPC khóa nhiều kế hoạch.

Cờ `confirm` không chứng minh chủ bot đã đồng ý. Eval chấm ca trùng bằng kho, trên hai lượt của mục 10: lượt một không có cờ và kho không đổi trước khi chủ bot trả lời. Lượt hai mới ghi.

Chốt trong lượt: chọn làm, và chốt nằm trên `TurnContext`, không nằm trong `run_turn`. `reschedule_subtasks` khi trả kết quả trùng thì đặt `clash_reported` trên ngữ cảnh nó nhận. Lần gọi sau trong cùng `run_turn`, với `confirm: true` trong khi cờ đã đặt, là lỗi tool và không ghi. Lượt sau là một lần gọi `run_turn` mới, một ngữ cảnh mới, cờ về false, và cờ xác nhận được nhận. Router không giữ trạng thái giữa các lần gọi `execute_tool`. Ngữ cảnh chỉ sống trong một request, đúng nguyên tắc II. `run_turn` không biết tên tool và không đọc chữ kết quả, nên nó không tự đặt cờ.

Thiếu `turn` thì `reschedule_subtasks` báo lỗi tool, không gọi `datetime.now`, không ghi. Sáu tool cũ gọi `execute_tool` không có `turn` vẫn chạy.

Eval bắt được, khi ca có `follow_up`: lượt một không có lần gọi dời ngày với `confirm` true, và kho sau lượt một không đổi. Lượt hai ghi đúng các việc đang mang ngày hạn. Eval không bắt được: mô hình đặt `confirm` true ngay lần gọi đầu của một lượt thật khi chủ bot chưa đồng ý. Ca eval viết sẵn câu đồng ý ở lượt hai, nên nó không chứng minh sự đồng ý ngoài kịch bản. Spec đã nói cờ không phải bằng chứng. Eval cũng không có ca "cờ trong cùng lượt". Chốt này bịt lỗ đó trong code, không phải trong điểm eval.

**Rationale:** Bản ghép D-021 chỉ dành cho ghi thành công, ghi quá hạn, và ghi bị từ chối. Trùng không ghi gì. Cờ nằm trên đối tượng ngữ cảnh nên `run_turn` không phải hiểu tên tool, và router không thành máy trạng thái. Tham số `turn` có mặc định trống để test sáu tool cũ không phải dựng ngữ cảnh.

**Alternatives considered:** Trả `Rejected` — bỏ, vì câu "Thay đổi chưa được áp dụng" sẽ vào bản ghép dù không có lần ghi. Thêm RPC đọc-và-ghi atomic trên mọi kế hoạch — bỏ, vì spec không đòi, và một chủ bot không cần khóa cả kho. Bỏ chốt cùng lượt — cân rồi không chọn. Chốt rẻ. Để `run_turn` đọc tên tool hoặc chữ "trùng" rồi tự nhớ — bỏ, vì vòng lặp tool sẽ phụ thuộc chữ và tên, và một tool mới có thể làm lệch chốt. Để router giữ cờ trên một biến module — bỏ, vì biến đó sống qua request, trái nguyên tắc II.

## 7. Mẫu dòng bản ghép

**Decision:** `create_plan` giữ mẫu hiện tại, không nêu ngày. Ngày chủ bot cần nghe nằm trong câu trả lời của mô hình. Bản ghép là biên bản lần ghi khi lượt gãy, và tiêu đề đã đủ để nhận ra việc.

Ba tool mới, mỗi tool một mẫu khi đặt giá trị, cộng mẫu xóa khi giá trị về trống. Cộng mẫu dời ngày. Tổng 11 mẫu. Chữ ở [contracts/saved-lines.md](./contracts/saved-lines.md). Chỉ `src/tools/saved_reply.py` chứa các chuỗi này.

`docs/ARCHITECTURE.md` §2 đang ghi "sáu mẫu dòng". Implement phải sửa thành 11. Không sửa ở bước plan.

**Rationale:** Mẫu xóa ghi chú đã tách khỏi mẫu ghi chú vì trống là một lần ghi thật. Ưu tiên và sức cũng vậy. Nhét ngày vào dòng `create_plan` làm mẫu phụ thuộc trường tùy chọn và dễ lệch với tiêu đề.

**Alternatives considered:** Một mẫu chung "Đã lưu." cho cả ba tool — bỏ, vì D-021 muốn bản ghép nói được việc gì đã lưu. Nêu ngày trong dòng tạo kế hoạch — bỏ, lý do ở trên.

## 8. Lời hướng dẫn bản 4

**Decision:** `PROMPT_VERSION = 4`. Hằng giữ nguyên mọi câu bản 3, gồm luật goal ngắn và câu ví dụ báo cáo thứ Sáu. Thêm luật: ngày dự kiến vào trường ngày, không vào tiêu đề; hạn tương đối theo FR-019, gồm "thứ X tuần sau"; khi đã chọn ngày thì nói ngày đó; trùng thì báo, không ghi, hỏi chủ bot, chỉ gọi lại với cờ ở lượt sau. Dòng ngày không nằm trong hằng. Hàm đồng hồ ghép sau hằng.

`tests/test_llm_turn.py` đổi `test_system_prompt_has_seven_laws` thành `test_system_prompt_has_version_four_laws`. Test khóa số 4, khóa các câu bản 3 còn nguyên, và khóa các câu luật mới. Không gọi mô hình thật. Tiền lệ spec 011: test khóa chữ đổi trong cùng thay đổi.

**Rationale:** Tách dòng ngày khỏi hằng để test chữ luật không phụ thuộc hôm nay, và để một lượt qua nửa đêm vẫn dùng mốc đầu.

**Alternatives considered:** Viết lại cả prompt — bỏ, vì FR-013 bắt giữ luật bản 3. Để số phiên bản 3 — bỏ, vì spec buộc số 4.

## 9. Digest và `/next`

**Decision:** `render_digest` vẫn chỉ nhận `tuple[Plan, ...]`, không nhận mốc. Với việc `pending` đầu tiên, nếu `scheduled_on` có ngày, cuối dòng tiêu đề thêm một dấu cách và `(<tên thứ> DD/MM)`. Tên thứ lấy từ `weekday_name_vi`. Ví dụ ngày 2026-11-06 là `(thứ Sáu 06/11)`. Chủ nhật là `Chủ nhật`, không có chữ "thứ" phía trước. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không thêm gì. Tiêu đề đã lưu không sửa. Thứ tự `created_order` tăng dần giữ nguyên. `/next` gọi cùng hàm.

Sửa đúng ba file FR-016: `specs/014-morning-digest/spec.md`, `specs/014-morning-digest/contracts/digest-text.md`, `tests/test_morning_text.py`. `specs/014-morning-digest/tasks.md` không sửa.

**Rationale:** FR-016 đã chốt chữ, và đã cấm nhận thời điểm hiện tại. Hàm tên thứ dùng chung với dòng ngày nên hai chỗ không lệch bảng tên.

**Alternatives considered:** Truyền `instant` vào `render_digest` để đánh dấu quá hạn — bỏ, vì FR-016 cấm đánh dấu quá hạn và cấm nhận thời điểm. Sửa `tasks.md` của spec 014 — bỏ, vì file đó là biên bản vòng F10.

## 10. Eval phiên bản 2

**Decision:** `evals/runner.py` nhận đường dẫn bộ câu. Mặc định khi không truyền là `evals/cases/v1.json`, cùng thư mục kết quả `evals/results/` và thư mục dataset `evals/datasets/`. Một lệnh thứ hai truyền `evals/cases/v2.json`. Mỗi bộ một lần chạy.

`Case` thêm `instant: datetime | None = None`. Bộ v2 bắt buộc có mốc trên từng ca. Bộ v1 để `None` và lần chạy dùng mốc cố định ở mục 1. `SubtaskSeed` thêm `scheduled_on: str | None = None` và `effort: str | None = None`. `PlanSeed` thêm `priority: str | None = None`. `load.py` đọc các khóa này, khóa vắng thì `None`, nên file v1 không phải viết lại.

`SCORER_VERSION = 2`. Ca `cases_version == 1` đi đúng hàm chấm bản 1, không đọc ngày, sức, ưu tiên hay lịch sử. Một test trong `tests/test_eval_score.py` lấy một ca v1 và chứng minh kết quả luật trùng với bản chấm 1 trên cùng fixture. Ca v2 đọc ngày, sức, ưu tiên và dòng lịch sử trên `MemoryPlanStore`. Seed ca trùng có sẵn một kế hoạch khác với hạn đã biết.

`Case` thêm `follow_up: str | None = None`. Chỉ ca cần lượt thứ hai, tình huống 2 của User Story 8 và SC-008, đặt chữ này. Đó là tin thứ hai của chủ bot, câu đồng ý trong kịch bản. `run_once` hôm nay gọi một `run_turn` với lịch sử rỗng, nên nó không có lượt chủ bot trả lời. Khi `follow_up` có chữ, runner chạy lượt một trên kho của ca, lấy câu trả lời của bot, chụp kho, rồi chạy lượt hai trên cùng một kho. Hình history, các trường Outcome của ca hai lượt và cách chấm ca trùng nằm ở mục 10a. Không có khối kết quả tool. Đúng sản phẩm: D-022 mục 3 nói ngữ cảnh hội thoại là tin chữ của chủ bot và câu trả lời của bot. Kết quả tool chỉ sống trong một lượt, không đi sang lượt sau. Mỗi lượt là một `run_turn`, nên mỗi lượt có một `TurnContext` riêng. Cờ trùng của lượt một không còn ở lượt hai.

`Outcome` của ca một lượt giữ năm trường đang có trong `evals/turn.py`: `kind`, `reply`, `lines`, `rounds`, `laws`. `lines` là log của đúng lượt đó. Ca v1 không có `follow_up`, nên hình này không đổi và test "chấm giống bản 1" vẫn đọc `laws`.

Tên file kết quả giữ công thức hiện có: `p{prompt}-d{definitions}-{model}-{ngày}.json`. Lần chạy v1 ra `p4-d3-<model>-<ngày>.json`. Lần chạy v2 cùng ngày ra cùng gốc với hậu tố `-2`, vì `evals/result.py` đã tăng số khi trùng tên. Trường `cases_version` trong file phân biệt hai lần. Chạy v1 trước để file không hậu tố là lần so với p3-d2.

Ước lượng chi phí: bộ v1 là 150 lần gọi mô hình, cùng cỡ p3-d2. Bộ v2 đúng 14 ca, hai ca hai lượt. Số lượt `run_turn` là 12 ca một lượt nhân 3, cộng 2 ca hai lượt nhân 2 lượt nhân 3, tức 48 lượt. Một lượt có thể gọi mô hình hơn một lần vì vòng tool, trần `TOOL_ROUND_CAP` là 3. Ước lượng thô số lần gọi mô hình của bộ v2 là khoảng 50 đến 70, vẫn nhỏ hơn một nửa lần chạy v1. Cộng thêm token ở mục 11. Không đổi giá đô la ở plan này. Hai lần chạy là hai lần gọi API thật, không phải pytest.

Ca một việc gộp và ca sửa lời có mặt trong báo cáo và không có đạt hay trượt, đúng câu 11.

**Rationale:** Mặc định vẫn là v1 để một lệnh quên cờ không nuốt chi phí bộ mới và vẫn so được với p3-d2. Mốc nằm trong ca v2 vì các ca hạn tương đối cần những thứ khác nhau. Giữ hàm chấm v1 nguyên nhánh là cách chứng minh "giống hệt" mà không cần mô hình.

**Alternatives considered:** Một lệnh chạy cả hai bộ — bỏ, vì spec nói một lần chạy mỗi bộ và hai file kết quả. Nhét `cases_version` vào tên file — bỏ, vì công thức tên đang có và trường trong JSON đã phân biệt. Sửa cách chấm v1 cho đủ chín tool — bỏ, vì câu 10 bắt giữ cách chấm để so với p3-d2. Việc chọn tool đo bằng log, không bằng cách đổi điểm luật cũ. Nhét kết quả tool của lượt một vào lịch sử lượt hai — bỏ, vì D-022 chỉ đưa tin chữ sang lượt sau, và eval sẽ không còn giống sản phẩm. Gộp log hai lượt thành một `lines` — bỏ, vì số vòng tool được tính trong một lượt, và ca lỗi cần biết lượt nào gãy.

## 10a. Mô hình kỳ vọng của eval v2 (chat chốt ở T037, 2026-11-09)

Nguyên tắc: không thêm tên luật. LAW_NAMES và các khóa by_case, by_rule, by_group giữ nguyên. summary.py và result.py chỉ thêm xử lý kind observed, lượt hai và ảnh kho cuối ca. Hành vi mới của v2 nằm trong luật tool và luật store của các nhóm mới. Một ca v2 đạt khi không luật nào là fail, như v1.

### Ca và bộ dữ liệu
- Case thêm instant (chuỗi ISO 8601 có độ lệch múi giờ, ví dụ 2026-11-11T10:00:00+02:00, đọc thành datetime có múi giờ; thiếu thì None) và follow_up (tin thứ hai; thiếu thì None). Bộ có cases_version 2: loader từ chối khi một ca thiếu instant. Ca v1 không có hai khóa; runner dùng mốc v1 cố định.
- SubtaskSeed thêm scheduled_on (ngày ISO hoặc None) và effort (S, M, L hoặc None). PlanSeed thêm priority (high, medium, low hoặc None). Khóa vắng là None, nên file v1 không phải viết lại. build_store đưa chúng vào Subtask và Plan.
- Năm file mới trong evals/datasets/: trung_han.json, trung_han_san.json, ke_hoach_khong_ngay.json, bang_chu_cai_tach.json, bang_chu_cai_gop.json. Nội dung ở mục Seed.

### Nhóm và loại kỳ vọng mới
Thêm vào Group và vào _KIND của evals/load.py, mỗi nhóm đúng một loại:
- "hạn tương đối: lưu ngày" -> create_with_deadline. Trường: deadline (ngày ISO).
- "hạn tương đối: hỏi lại" -> ask_back_no_write. Không trường.
- "nhóm việc mơ hồ" -> ask_back_no_write. Không trường.
- "hạn cả kế hoạch" -> set_deadline_existing. Trường: goal, deadline.
- "dời hạn trùng" -> clash_two_turn. Trường: goal, other_goal, dates, history_moves. Ca bắt buộc có follow_up và bộ dữ liệu.
- "dời ngày không cần xác nhận" -> reschedule_no_confirm. Trường: goal, dates, history_moves.
- "tin dài có ngày" -> long_message_goal. Không trường.
- "liệt kê tiêu đề" -> verbatim_titles. Trường: titles (danh sách chuỗi).
- "ghi nhận" -> observe. Không trường.
- "ưu tiên do người dùng nêu" -> create_with_priority. Trường: priority.
- "đặt ưu tiên" -> set_priority_existing. Trường: goal, priority.
- "đặt sức" -> set_effort_existing. Trường: goal, title, effort.
Expectation thêm: deadline (str hoặc None), titles (tuple[str, ...] hoặc None), other_goal (str hoặc None), dates (tuple các cặp (tiêu đề, ngày ISO) hoặc None), history_moves (int hoặc None), priority (high, medium, low hoặc None) và effort (S, M, L hoặc None). Loader kiểm: trường bắt buộc theo loại; ngày ISO hợp lệ; goal, other_goal và mọi tiêu đề trong dates có trong bộ dữ liệu của ca; clash_two_turn có follow_up và bộ dữ liệu.

### Luật tool (names là tên tool theo thứ tự gọi của mọi lượt của ca; READ là get_plans và get_plan_detail)
- create_with_deadline, long_message_goal, verbatim_titles: names bằng đúng ["create_plan"], như nhóm "nhờ lập kế hoạch" của v1.
- create_with_priority: names bằng đúng ["create_plan"].
- set_priority_existing: names là tập con của READ cộng set_plan_priority, và có ít nhất một set_plan_priority.
- set_effort_existing: names là tập con của READ cộng set_subtask_effort, và có ít nhất một set_subtask_effort.
- ask_back_no_write: names là tập con của READ (rỗng cũng được).
- set_deadline_existing: names là tập con của READ cộng reschedule_subtasks, và có ít nhất một reschedule_subtasks.
- reschedule_no_confirm: như set_deadline_existing, và không lần gọi reschedule_subtasks nào có confirm bằng true.
- clash_two_turn: lượt 1: names là tập con của READ cộng reschedule_subtasks, có ít nhất một reschedule_subtasks, không lần gọi nào có confirm true. Lượt 2: names là tập con của READ cộng reschedule_subtasks, và có ít nhất một reschedule_subtasks với confirm true.
- create_plan_count: bằng 1 với create_with_deadline, long_message_goal, verbatim_titles và create_with_priority, bằng 0 với mọi nhóm v2 khác.
- required, prefix, markdown, self_name: như v1. markdown và self_name chấm cả hai câu trả lời của ca hai lượt.

### Luật store
Ảnh kho là tuple các kế hoạch, mỗi kế hoạch gồm goal, priority và từng việc (title, status, note, scheduled_on, effort) theo thứ tự; hai ảnh so bằng ==. Lịch sử đọc từ date_moves của kho.
- create_with_deadline: kho có đúng một kế hoạch; plan_deadline của nó bằng deadline; việc mang ngày đó là việc chưa làm đứng cuối; priority trống và mọi effort trống.
- long_message_goal: kho có đúng một kế hoạch; goal chỉ một dòng, dưới 80 ký tự, không có mẫu ngày hay giờ; tiêu đề các việc không có mẫu ngày; priority trống và mọi effort trống. Mẫu ngày: dd/mm hoặc dd/mm/yyyy, yyyy-mm-dd; thứ viết hoa từ thứ Hai đến thứ Bảy; thứ viết thường chỉ khi đứng sau vào, trước, đến, hết, hạn hoặc sau; chủ nhật, hôm nay, ngày mai, tuần này, tuần sau và cuối tuần không phân biệt hoa thường. "thứ hai" và "thứ ba" dùng như số thứ tự không phải mẫu ngày. Mẫu giờ: một số liền trước "giờ" hoặc "tiếng", hoặc "h" sát số.
- verbatim_titles: kho có đúng một kế hoạch; mỗi tiêu đề trong titles có mặt trong kế hoạch đó đúng từng chữ (NFC, bỏ khoảng trắng hai đầu); priority trống và mọi effort trống.
- create_with_priority: kho có đúng một kế hoạch; priority bằng giá trị kỳ vọng; mọi effort trống.
- set_priority_existing: ưu tiên của kế hoạch goal bằng giá trị kỳ vọng; ngày, sức, tiêu đề, trạng thái và các kế hoạch khác giống ảnh lúc mở.
- set_effort_existing: effort của việc title bằng giá trị kỳ vọng; mọi thứ khác giống ảnh lúc mở.
- ask_back_no_write: ảnh kho sau ca bằng ảnh lúc mở; không có dòng lịch sử.
- set_deadline_existing: số kế hoạch không đổi; kế hoạch goal có việc chưa làm đứng cuối với scheduled_on bằng deadline; mọi việc khác giữ scheduled_on lúc mở; goal và tiêu đề các việc không đổi.
- reschedule_no_confirm: scheduled_on của từng việc trong kế hoạch goal bằng dates; kế hoạch khác không đổi; số dòng lịch sử bằng history_moves.
- clash_two_turn: ảnh sau lượt 1 bằng ảnh lúc mở; sau lượt 2: scheduled_on của từng việc trong kế hoạch goal bằng dates (việc xong và việc có ngày sớm hơn giữ nguyên), kế hoạch other_goal không đổi, số dòng lịch sử bằng history_moves.
- observe: không chấm.

### Ca ghi nhận
Ca observe không có đạt hay trượt. Outcome.kind là "observed" và laws là None. evals/summary.py loại kind observed khỏi _scored và khỏi run_errors, nên tỉ lệ của nhóm là None. Báo cáo và file kết quả vẫn ghi câu trả lời của từng lượt, dòng log của từng lượt, và ảnh kho cuối ca ở dạng JSON, để đọc được hành vi.

### Ca hai lượt
Nếu follow_up khác None: chạy lượt 1; nếu kind là kind lỗi thì dừng và báo kind đó; nếu không thì chạy lượt 2 với user_message là follow_up và history chỉ gồm chữ (tin chủ bot của lượt 1 và câu trả lời của bot ở lượt 1, không có khối tool). Cùng một kho và cùng mốc instant của ca. Outcome thêm earlier (Outcome của lượt 1), opening (ảnh kho lúc mở) và after_first (ảnh kho sau lượt 1). Outcome chính là lượt 2. Luật tool và luật store của clash_two_turn đọc cả hai lượt.

### Seed (nội dung chính xác)
- trung_han: kế hoạch "Ôn thi vật lý": "Đọc xong tài liệu chương 1" (done, 2026-11-13); "Làm xong bài tập chương 1" (pending, 2026-11-11); "Làm xong đề thi thử" (pending, 2026-11-13). Kế hoạch "Nộp luận văn": "Nộp bản cuối cho giáo viên" (pending, 2026-11-14).
- trung_han_san: "Ôn thi vật lý": "Làm xong bài tập chương 1" (pending, 2026-11-11); "Làm xong đề thi thử" (pending, 2026-11-14). "Nộp luận văn": "Nộp bản cuối cho giáo viên" (pending, 2026-11-14).
- ke_hoach_khong_ngay: "Chạy được 10km": "Chạy 6km không nghỉ", "Chạy 8km không nghỉ", "Chạy 10km không nghỉ" (cả ba pending, không ngày).
- bang_chu_cai_tach: "Học tiếng Nhật cơ bản": "Học thuộc bảng Hiragana", "Học thuộc bảng Katakana" (pending).
- bang_chu_cai_gop: "Học tiếng Nhật cơ bản": "Học thuộc bảng Hiragana và Katakana", "Học 50 chữ Kanji đầu tiên" (pending).

### Ca của bộ v2
V2-01 | hạn tương đối: lưu ngày | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, xong trước cuối tuần này." | deadline 2026-11-15.
V2-02 | hạn tương đối: hỏi lại | 2026-11-13T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, xong trước thứ Sáu."
V2-03 | hạn tương đối: lưu ngày | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, xong vào tuần sau." | deadline 2026-11-22.
V2-04 | hạn tương đối: lưu ngày | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, hạn là thứ Hai." | deadline 2026-11-16.
V2-05 | hạn tương đối: lưu ngày | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, xong trước thứ Sáu tuần sau." | deadline 2026-11-20.
V2-06 | hạn cả kế hoạch | 2026-11-11T10:00:00+02:00 | dataset ke_hoach_khong_ngay | "Kế hoạch Chạy được 10km phải xong trước ngày 20/11." | goal "Chạy được 10km", deadline 2026-11-20.
V2-07 | dời hạn trùng | 2026-11-11T10:00:00+02:00 | dataset trung_han | "Cho kế hoạch Ôn thi vật lý thêm một ngày nữa nhé." | follow_up "Ừ, cứ dời đi." | goal "Ôn thi vật lý", other_goal "Nộp luận văn", dates: "Đọc xong tài liệu chương 1" 2026-11-13, "Làm xong bài tập chương 1" 2026-11-11, "Làm xong đề thi thử" 2026-11-14; history_moves 1.
V2-08 | dời ngày không cần xác nhận | 2026-11-11T10:00:00+02:00 | dataset trung_han_san | "Dời việc Làm xong bài tập chương 1 của kế hoạch Ôn thi vật lý sang ngày 12/11." | goal "Ôn thi vật lý", dates: "Làm xong bài tập chương 1" 2026-11-12, "Làm xong đề thi thử" 2026-11-14; history_moves 1.
V2-09 | tin dài có ngày | 2026-11-06T08:00:00+02:00 | "Mình cần học xong learning path Get started with AI applications and agents on Azure trước hết ngày Chủ nhật 08/11/2026, bắt đầu từ thứ Sáu 06/11, khoảng 8 tiếng mỗi ngày. Lập kế hoạch giúp mình."
V2-10 | tin dài có ngày | 2026-11-09T09:00:00+02:00 | "Mình cần ôn xong AZ-900 để thi vào ngày 20/11, bắt đầu từ ngày mai, mỗi ngày khoảng 2 tiếng. Lập kế hoạch giúp mình."
V2-11 | liệt kê tiêu đề | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch học tiếng Nhật với các việc: Học thuộc bảng Hiragana, Học thuộc bảng Katakana, Học 50 chữ Kanji đầu tiên." | titles: ba tiêu đề đó.
V2-12 | nhóm việc mơ hồ | 2026-11-11T10:00:00+02:00 | dataset bang_chu_cai_tach | "Mình học xong bảng chữ cái rồi."
V2-13 | ghi nhận | 2026-11-11T10:00:00+02:00 | dataset bang_chu_cai_gop | "Mình học xong bảng chữ cái rồi."
V2-14 | ghi nhận | 2026-11-11T10:00:00+02:00 | dataset bang_chu_cai_gop | "Mình học xong bảng chữ cái rồi." | follow_up "À không, mình mới học xong Hiragana thôi."
V2-15 | ưu tiên do người dùng nêu | 2026-11-11T10:00:00+02:00 | "Lập kế hoạch giúp mình ôn thi giải tích, ưu tiên cao." | priority high.
V2-16 | đặt ưu tiên | 2026-11-11T10:00:00+02:00 | dataset ke_hoach_khong_ngay | "Đặt ưu tiên thấp cho kế hoạch Chạy được 10km." | goal "Chạy được 10km", priority low.
V2-17 | đặt sức | 2026-11-11T10:00:00+02:00 | dataset ke_hoach_khong_ngay | "Việc Chạy 10km không nghỉ của kế hoạch Chạy được 10km là việc nặng, ghi sức L giúp mình." | goal "Chạy được 10km", title "Chạy 10km không nghỉ", effort L.
Mười bảy ca, mỗi ca chạy ba lần; V2-07 và V2-14 là hai lượt.

### Phần sửa mà mục này kéo theo
evals/summary.py (kind observed), evals/model.py, evals/load.py, evals/store.py, evals/turn.py, evals/score.py, evals/runner.py, năm file evals/datasets/, evals/cases/v2.json. evals/result.py chỉ sửa khi bắt buộc và nêu lý do. Test: mỗi nhóm mới có một hàm đạt và một hàm trượt cho luật tool và cho luật store; loader từ chối ca v2 thiếu instant, thiếu trường bắt buộc theo loại, goal hay tiêu đề không có trong bộ dữ liệu; hai lượt (lịch sử chỉ chữ, lượt 1 lỗi thì bỏ lượt 2, Outcome có earlier, opening, after_first); summary không đếm observed vào tỉ lệ; mỗi seed nạp được.

## 11. Chi phí token

**Decision:** Lần đo p4-d3 ghi 1.199.053 token vào cho 150 lượt bộ v1, so với 732.676 của p3-d2. Cộng khoảng 1.630 token vào mỗi lần gọi, 64% trên bộ v1. Lần đo đó dùng lời hướng dẫn bản 4 và catalog bản 3. Bộ v2 không dùng làm nền, vì số ca khác 150.

**Rationale:** Số đo thật thay cho ước lượng theo bề rộng schema. Catalog, lời hướng dẫn và khối ngày đi vào mọi lần gọi.

**Alternatives considered:** Giữ ước lượng 500 đến 900 token mỗi lần gọi — bỏ, vì p4-d3 đã có số đo. Coi lần v2 là lần đo token — bỏ, vì không cùng số lần gọi với p3-d2.

## 12. Docs khi implement

**Decision:** Bước plan không sửa `docs/`. Implement sửa:

- `docs/PRODUCT.md` §3 hàng F17: không còn chỉ "ngày dự kiến cho việc con". Nêu ngày, ưu tiên kế hoạch, sức, lịch sử dời, và xác nhận khi hạn sau lần dời trùng hạn kế hoạch khác. §9: ngày nằm ở trường ngày, không ở tiêu đề mới. Tiêu đề cũ giữ nguyên. Trùng hạn thì báo và chưa ghi cho đến khi chủ bot đồng ý. Khớp đúng một tên vẫn cập nhật ngay.
- `docs/ARCHITECTURE.md` §2: chín tool, `DEFINITIONS_VERSION` 3, `PROMPT_VERSION` 5, 11 mẫu dòng trong `saved_reply.py`.

Chat viết một mục D-026 trong `docs/DECISIONS.md`. Cursor chỉ chép chữ chat đã duyệt, không tự viết quyết định. Các điểm đáng vào D-026:

1. Mốc lượt là tham số bắt buộc của `run_turn`. Một `TurnContext` sống trong lần gọi đó, mang mốc và cờ đã báo trùng, và được đưa vào `execute_tool`. Một hàm tên thứ dùng cho dòng ngày và digest. `helsinki_clock` nằm ở `src/core/clock.py` và vẫn import được từ `core.morning`.
2. `Plan.priority`, `Subtask.scheduled_on`, `Subtask.effort`, mặc định trống. Hạn và trùng là hàm thuần. `PlanStore.add` nhận ưu tiên keyword, mặc định trống.
3. Dòng lịch sử do SQL trong `replace_plan` chèn khi ngày đổi từ một ngày sang một ngày khác. Không khóa ngoại. Trigger chặn sửa và xóa. Không `now()` trong SQL.
4. Tham số RPC mới có `DEFAULT NULL`, gồm `add_plan.priority` và `replace_plan.plan_fields`. Chữ ký cũ bị `drop` rồi tạo lại, nếu không lời gọi cũ không đi vào hàm mới. Khóa vắng không xóa ngày, sức hay ưu tiên đang lưu. JSON null là xóa.
5. Chín tool, catalog bản 3, lời hướng dẫn bản 5.
6. Kết quả trùng không vào bản ghép D-021. Cờ xác nhận không phải sự đồng ý. Tool dời ngày tự đặt cờ trên ngữ cảnh của lượt. `run_turn` không đọc tên tool. Cờ trong cùng lượt sau một lần báo trùng thì từ chối. Ca eval trùng có lượt thứ hai, lịch sử chỉ là tin chữ.
7. Digest thêm đoạn ngày do code dựng, không nhận thời điểm hiện tại. Rollback được hỗ trợ là Worker cũ trên schema mới. Gỡ migration không được hỗ trợ.

Diagram trong `docs/architecture/` không sửa, theo D-016.

**Rationale:** Constitution bắt sửa doc nào trở thành sai trong cùng thay đổi implement. Plan chỉ liệt kê, không viết doc đó. D-026 là quyết định, nên chữ thuộc về chat.

**Alternatives considered:** Viết D-026 ngay trong plan — bỏ, vì người dùng đã tách: chat viết, Cursor chép. Sửa PRODUCT ở bước plan — bỏ, vì bước này chỉ tạo tài liệu trong thư mục spec 015.

## Kết quả p5-d3

v1: tool 134/150, create_plan_count 149/150, nhóm nhờ lập kế hoạch 0,967, tự đặt ưu tiên 1/30 và sức 3/209, token vào 1.440.734. v2: các nhóm hạn tương đối, tin dài và hạn trùng chưa đạt, nguyên nhân là bốn điểm bản 6 sửa.

## Kết quả p6-d3

v1: tool 135/150, create_plan_count 150/150, nhóm nhờ lập kế hoạch 1,000, create_plan invalid_input 0, tự đặt sức 0, ưu tiên tự đặt 4/54. v2: V2-05, V2-06, V2-09 đạt 1,0; V2-07 đạt 2/3 với luồng xác nhận hoạt động; còn V2-03, V2-04, V2-10, V2-01 như đã nêu. Token vào v1 1.650.032 và v2 700.997.

## Kết quả p7-d3 và việc còn mở

Bản được chọn: lời hướng dẫn bản 7, catalog bản 3 (p7-d3, 2026-11-09). Các bản 4, 5, 6 chỉ dùng cho p4-d3, p5-d3, p6-d3.
v1 (150 lượt): tool 136/150, create_plan_count 150/150, required, prefix, markdown, self_name 150/150, store 45/45; nhóm nhờ lập kế hoạch 1,000; 14 lượt tool trượt còn lại là nhóm xem chi tiết (có từ p3-d2) và một lượt M02; token vào 1.684.520 (p3-d2: 732.676).
v2 (51 lượt): hạn tương đối: hỏi lại 1,0, lưu ngày 0,833; hạn cả kế hoạch 1,0; dời ngày không cần xác nhận 1,0; liệt kê tiêu đề 1,0; nhóm việc mơ hồ 1,0; ưu tiên nêu rõ, đặt ưu tiên, đặt sức 1,0; dời hạn trùng 0,333; tin dài có ngày 0,667; ghi nhận không chấm. create_plan invalid_input 0; sức tự đặt 0; ưu tiên tự đặt ngoài V2-15 là 3 trên 51 lần tạo.
Việc còn mở: (1) hạn trùng: mô hình có lượt hỏi trước khi gọi tool, rồi gửi confirm true ở lượt sau mà chủ bot chưa được báo trùng (cờ không là bằng chứng, D-026 mục 6); (2) ở một lượt V2-04 hạn không được lưu lúc tạo dù câu trả lời nói đã đặt, kèm đoạn tiếng Anh ở đầu; (3) ưu tiên tự đặt cho kế hoạch kiểu phỏng vấn, kỳ thi (3 trên 51), hiện chưa nơi nào đọc ưu tiên; (4) get_plans lọc từ khóa nguyên chữ nên "bảng chữ cái" không khớp tên việc (V2-13, V2-14); (5) nhóm xem chi tiết 0/15 từ p3-d2: mô hình dùng get_plans thay get_plan_detail; (6) token vào mỗi lượt gấp khoảng 2,3 lần p3-d2; prompt caching phần cố định (lời hướng dẫn và catalog) là hướng giảm chi phí.
