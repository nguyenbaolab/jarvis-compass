# Research: Bản tin sáng

**Branch**: `014-morning-digest` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

Mỗi mục là một lựa chọn để Starter duyệt. Bước này không sửa `src/`, `tests/`, `supabase/`, `docs/`.

## 1. Dòng digest không có mã update của Telegram

**Decision**: Mỗi ngày Helsinki là một dòng `telegram_updates`. Mã là số âm suy từ ngày: `-(năm * 10000 + tháng * 100 + ngày)`. Ngày 2026-11-07 là `-20261107`. Khóa chính `(update_id, role)` giữ nguyên. Digest chỉ ghi một dòng `telegram_context_messages` với `role = assistant`. Không có dòng `user`. Dùng lại `claim_telegram_update`, `save_telegram_reply`, `append_telegram_context`, `mark_telegram_sent`. Không bảng mới, không migration, không đổi khóa ngoại.

**Rationale**: `telegram_context_messages.update_id` tham chiếu `telegram_updates(update_id)`. Lượt sau đọc ngữ cảnh theo `chat_id` và `saved_at`, không theo dấu của mã, nên một mã âm vẫn vào cửa sổ 20 tin / 24 giờ (D-022). Migration `20261104143000_telegram_channel.sql` không có `CHECK (update_id > 0)`. Cột là `bigint` có dấu. Mã update thật của Telegram là số dương tăng dần, nên dải âm không đụng mã thật. `append_telegram_context` chỉ nhận `user` hoặc `assistant`; `assistant` hợp lệ. Một chủ bot, một cuộc trò chuyện: một mã mỗi ngày là đủ, vì khóa ngữ cảnh không có chỗ cho hai dòng `assistant` của cùng một mã.

Thứ tự một lần chạy, sau khi giờ Helsinki đã từ 08:00:

1. `claim`. Dòng đã có `sent_at`: dừng, không gửi.
2. `reply` đã có: không dựng lại. Gọi `append` cho đúng chữ đã lưu, vai `assistant`. Trùng khóa thì RPC không ghi lần hai. Gửi chữ đã lưu. Kênh xác nhận cả tin thì `mark_telegram_sent`.
3. `reply` còn null: đọc kế hoạch, dựng chữ, `save_telegram_reply`. Hàm trả false thì không gửi chữ vừa dựng. Lần sau thấy `reply` và đi nhánh 2. Hàm trả true thì `append` một dòng assistant, gửi, rồi `mark`.

`save` trả false, `append` ném lỗi, hoặc gửi lỗi: không `mark`. Lần sau trong ngày gửi lại chữ đã lưu nếu `reply` đã có, và dựng lại chỉ khi `reply` vẫn null. `mark` ném lỗi sau khi kênh đã nhận: `sent_at` vẫn null, lần sau gửi lại đúng chữ đã lưu. Chấp nhận trùng. Trùng cả tin khi chưa xác nhận là điều spec chấp nhận, cùng kiểu spec 013.

Trước 08:00 không `claim`. Một dòng tạo lúc 07:00 với `reply` null sẽ khiến lần 08:00 trông như lần thử lại của một claim bỏ dở.

**Alternatives considered**: Bảng riêng cho ngày digest, rồi đổi khóa ngoại của `telegram_context_messages` để dòng ngữ cảnh không cần `telegram_updates`. Lượt sau vẫn phải thấy chữ digest trong ngữ cảnh, nên vẫn cần một dòng ngữ cảnh. Đổi khóa ngoại đụng bảng đang chạy và cần RPC mới cho cùng một hành vi. Hướng mã âm không thêm SQL. Hướng bảng riêng bị loại.

Mã dương lấy từ một dải dành riêng cũng bị loại: mã update thật chỉ được biết là số dương, không có trần để chọn dải an toàn.

## 2. `decide_receive` và câu chưa chắc

**Decision**: Không sửa `decide_receive` trong `src/core/telegram_channel.py`. Digest dùng hàm thuần mới `decide_digest` trong `src/core/morning.py`, enum riêng, không có nhánh SaveUncertain.

- `sent_at` có: xong, không gửi.
- `reply` có, kể cả khi claim đã hơn 90 giây: gửi lại đúng chữ đã lưu.
- `reply` null, kể cả khi claim đã hơn 90 giây: dựng lại.

Digest không bao giờ ghi hay gửi `Chưa chắc tin này đã được xử lý.`

**Rationale**: `decide_receive` là luật của update thường. Quá `DEAD_AFTER` (90 giây) mà `reply` còn null thì SaveUncertain và câu đó. Đúng 90 giây vẫn là Defer. Digest không phải một update Telegram đang được gửi lại trong cửa sổ ngắn. Lần cron sau cách lần trước một giờ. Áp luật 90 giây sẽ biến một lần dựng lỗi thành câu "chưa chắc", rồi lần sau gửi lại câu đó thay vì bản tin. Đó trái FR-012.

Ví dụ chốt: claim lúc 08:00:00, lần chạy lúc 09:00:00, `reply` null. Digest dựng lại. Cùng tuổi đó trên một update thường vẫn là SaveUncertain. Hai hàm không gọi lẫn nhau.

`/next` là update thường. Lần Telegram gửi lại vẫn đi `decide_receive` ở nhánh `claimed.inserted` là false (`src/api/telegram_update.py`, trước khi dựng câu). Quá 90 giây mà chưa lưu được câu thì update đó vẫn SaveUncertain. Đó là hành vi cũ, không phải đường digest.

**Alternatives considered**: Thêm tham số "bỏ qua 90 giây" vào `decide_receive`. Một cờ dùng chung dễ làm update thường mất câu chưa chắc. Hàm riêng giữ nguyên mọi nhánh hiện có. Bị loại theo hướng sửa hàm cũ.

## 3. Chỗ cắm `/next`

**Decision**: Trong `handle_update`, sau nhánh tin không phải chữ (khoảng dòng 256–268) và trước ` _history` / `run_turn` (khoảng dòng 270–292). Nếu `is_next_command(inbound.text)` thì gọi `plans.list_newest_first()`, đưa tuple đó vào `render_digest`, rồi ` _save_context_send(..., remember=True)` với `done_reason` hiện có của câu trả lời thường. Không gọi `run_turn`. Không đọc lịch sử cho lệnh này.

File này thêm một import: `from core.morning import is_next_command, render_digest`. Không import `db`, `clients`, `config`, `anthropic`. Cổng "Update imports" trong `scripts/check.ps1` cấm đúng bốn tên đó trên `src/api/telegram_update.py`.

**Rationale**: Đọc lịch sử trước lệnh sẽ biến lỗi đọc ngữ cảnh thành lần hoãn, dù lệnh không cần lịch sử. `remember=True` đi qua `_remember`, ghi đúng chữ chủ bot rồi chữ trả lời. Đó là FR-015. `list_newest_first` trả `created_order` giảm dần. Hàm dựng tự sắp tăng dần. Không đổi `PlanStore`.

Đọc kế hoạch ném lỗi: `Outcome.Defer`, reason store-unavailable đã có, không gửi, không lưu câu, không `mark`. Không dùng câu chưa chắc. Đọc ra tập rỗng, hoặc không kế hoạch nào còn việc `pending`, là đọc thành công: chữ của cả tin là câu đã chốt trong spec.

Lệnh khớp khi `strip()` rồi `casefold()` bằng `"/next"`. `/next@bot`, `/next hôm nay`, `/start` không khớp và vẫn vào `run_turn`.

Dòng log kênh của `/next` dùng `write_channel_line` với các khóa cũ. Không có dòng log mô hình và không có dòng log tool, vì không gọi `run_turn`.

**Alternatives considered**: Cắm sau `run_turn` rồi bỏ câu của mô hình. Lệnh vẫn tốn một lượt mô hình và vẫn có thể ghi dòng log tám khóa. Trái FR-007 và mục G của clarify. Bị loại.

## 4. `scheduled` và cron

**Decision**: `src/entry.py` thành lớp `Default(WorkerEntrypoint)` với `fetch` và `scheduled`. `fetch` ủy quyền ASGI như nhánh spike. `scheduled` chỉ gọi `run_morning(self.env)` trong `src/scheduler/morning.py`. Hàm đó nhận mapping env và, khi test, một đồng hồ tiêm vào. Không nhận kiểu của gói `workers`.

Cron khai trong `wrangler.jsonc`:

```json
"triggers": { "crons": ["0 5 * * *", "0 6 * * *", "0 7 * * *"] }
```

Ba mốc 05:00, 06:00, 07:00 UTC. Code chỉ gửi khi giờ địa phương Helsinki từ 08:00:00 trở đi và ngày đó chưa được xác nhận. Trước 08:00 không claim, không gửi, không mark.

**Rationale**: Cổng "Workers imports" cho phép `from workers` chỉ trong `src/entry.py`. Mọi file khác, kể cả `src/scheduler/`, dính cổng này nếu import `workers`. Vì vậy kiểu `controller` dừng ở entry. Mẫu trên `spike/cron-checkin` là:

```python
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await asgi.fetch(app, request, self.env)

    async def scheduled(self, controller, env, ctx):
        await send_checkin(self.env, controller.cron, controller.scheduledTime)
```

Nhánh đó cron `*/5 * * * *` và gọi `spike_cron`. Chưa kiểm trên Worker cloud. Mẫu chỉ chứng minh hình lớp trên `pywrangler dev`. Rủi ro còn lại là runtime cloud không gọi `scheduled`, hoặc chữ ký `asgi.fetch` đổi. Cách kiểm nằm ở mục 8. Implement không deploy.

Lịch UTC này là lịch được gợi ý, và plan chọn nó. Mùa đông (UTC+2): 05:00 UTC là 07:00 Helsinki, bỏ qua; 06:00 và 07:00 UTC là 08:00 và 09:00, hai lần từ 08:00. Mùa hè (UTC+3): 05:00 UTC đã là 08:00, đủ ba lần. Ngày chuyển mùa xuân 2026-03-29 nhảy lúc 01:00 UTC, nên từ 05:00 UTC đã là UTC+3, giống mùa hè. Ngày lùi 2026-10-25 cũng nhảy lúc 01:00 UTC, nên từ 05:00 UTC đã là UTC+2, giống mùa đông: vẫn hai lần từ 08:00. 08:00 địa phương không rơi vào giờ bị nhảy (nhảy lúc 03:00/04:00). Một cron đúng 06:00 UTC chỉ cho mùa đông một lần từ 08:00, không đủ lần thử lại trong ngày. Bộ 04/05/06 UTC cũng vậy.

**Alternatives considered**: Giữ `asgi.entrypoint(app)` và thêm cron ở nơi khác. Entrypoint đó không có `scheduled`, nên cron không có chỗ vào. Bị loại. Để `scheduler` import `workers` rồi đọc `controller` bên trong. Trái cổng Workers imports. Bị loại.

## 5. `chat_id` khi không có update

**Decision**: `chat_id` của digest là số nguyên suy từ `TELEGRAM_OWNER_ID` qua `require_telegram_owner_id`. Không biến mới. Không đọc một update cũ để đoán chat. Chuỗi phải thỏa cùng luật `owner_id_matches`: `int` của chuỗi, không phải bool, và `str(số)` đúng bằng chuỗi cấu hình, không strip. Chuỗi không đạt: lần chạy deferred, không gửi, không mark.

**Rationale**: Webhook chỉ nhận chat `private` của đúng chủ bot (`src/api/routes_telegram.py`). Với chat riêng, Telegram đặt `chat.id` bằng id người dùng. Id đó là chuỗi `TELEGRAM_OWNER_ID` đã khớp `str(user_id)`. Digest không có update nên không có `message.chat.id` riêng. Một biến thứ hai sẽ lệch khỏi luật chủ bot ở D-022.

**Alternatives considered**: Lưu `chat_id` của tin gần nhất rồi đọc lại. Trước tin đầu tiên thì không có gì để đọc, và thêm một truy vấn cho một giá trị đã nằm trong cấu hình. Bị loại.

## 6. Migration và D-023

**Decision**: Không migration mới. Không RPC mới. Không đổi chữ ký bốn RPC kênh đang có. `tests/test_rpc_returns.py` không cần sửa: test đó thất bại khi định nghĩa mới nhất của một RPC mà `client.py` gọi là `void`. Vòng này không thêm định nghĩa.

**Rationale**: Bốn RPC đã trả giá trị. `claim_telegram_update` trả jsonb. `save_telegram_reply` trả boolean. `mark_telegram_sent` và `append_telegram_context` được tạo lại ở `20261105150000_rpc_return_values.sql` để trả boolean, vì Pyodide httpx gãy trên 204 (D-023). Digest chỉ đọc boolean của `save_reply_if_absent`. `mark` và `append` được xét theo có ném lỗi hay không. `UpdateStore.mark_sent` và `ContextStore.append_once` trả `None`. `src/db/client.py` bỏ giá trị boolean vì giá trị không được đọc. Bản Supabase và đồ giả cũng trả `None`. Boolean của `mark` và `append` không thêm thông tin: `append` không ném lỗi thì dòng đã ghi hoặc vừa ghi, vẫn gửi; `mark` không ném lỗi thì mốc đã ghi, vì lời gọi chỉ không đổi hàng khi `sent_at` đã có và nhánh đó đã dừng từ trước. Đọc boolean đó phải sửa `src/core/telegram_channel.py`, `src/db/client.py`, `src/db/telegram_channel_store.py`, và `tests/fakes/memory_telegram_channel.py`. Các file đó đang cấm sửa hoặc ngoài allow-list. Đường update thường vẫn không đọc boolean của `mark`. Không đổi chỗ đó.

`save` trả false nghĩa là không được quyền chữ vừa dựng. Không gửi chữ đó. `mark` không ném lỗi: outcome `sent` hoặc `resend`. `mark` ném lỗi sau khi gửi: outcome `deferred`, `sent_at` vẫn null, lần sau gửi lại đúng chữ đã lưu. Chấp nhận trùng. Spec chấp nhận trùng khi kết quả xác nhận không rõ.

**Alternatives considered**: RPC `claim_digest_day` riêng, trả boolean. Thêm một hàm void là trái D-023. Thêm một hàm trả boolean trong khi bốn RPC cũ đã đủ thì đụng schema mà không thêm hành vi. Bị loại. Nếu lúc implement phát hiện một CHECK `update_id > 0` mà bước này không thấy, dừng và không tự thêm migration.

## 7. Dòng log của lần chạy sáng

**Decision**: Một dòng JSON mới, không đi qua `write_channel_line`. Khóa, đúng thứ tự, luôn có mặt:

| Khóa | Giá trị |
| --- | --- |
| `event` | `morning_digest` |
| `outcome` | `before_eight`, `already_sent`, `sent`, `resend`, hoặc `deferred` |
| `helsinki_date` | `YYYY-MM-DD` theo lịch Helsinki của đồng hồ được tiêm |
| `local_time` | `HH:MM` theo cùng phép đổi |
| `update_id` | mã âm của ngày đó, kể cả khi trước 08:00 chưa ghi dòng |
| `error_type` | tên lớp exception, hoặc JSON null |
| `error_code` | cùng luật `error_code_of`, hoặc JSON null |

Không có chữ tin, mục tiêu, tiêu đề, `chat_id`, token, secret, hay thông điệp exception. Ghi bằng `write_json_line` trong `src/core/log_line.py`. Hàm đó nuốt lỗi ghi, trừ `CancelledError`.

Nghĩa outcome: `before_eight` là chưa claim. `already_sent` là đã có `sent_at`. `sent` là lần này dựng, gửi, và `mark` không ném lỗi. `resend` là gửi chữ đã lưu và `mark` không ném lỗi. Mọi dừng khác là `deferred`.

Dòng kênh giữ khóa `outcome`, `reason`, và các khóa tùy chọn `update_id`, `error_type`, `error_code`. Dòng tool giữ bảy khóa. Dòng mô hình giữ tám khóa, gồm `prompt_version` và `definitions_version`. `PROMPT_VERSION` không đổi. Digest và `/next` không mở lượt mô hình, không gọi `execute_tool`, không truyền `remaining()` (D-021 không áp vào hai đường này).

Ghi các khóa trên vào `docs/ARCHITECTURE.md` §6 là việc của bước đồng bộ docs, không phải bước này.

**Rationale**: Dùng lại dòng kênh sẽ thêm khóa hoặc nhét `event` vào một reason của webhook. Cả hai làm đổi dòng spec 013 đang khóa. Dòng riêng giữ nguyên ba dòng cũ. `local_time` là cách đọc độ lệch Helsinki trên log mà không chờ 08:00 và không ghi nội dung tin.

**Alternatives considered**: Thêm khóa `kind` vào `write_channel_line`. Đổi chữ ký hàm log kênh. Bị loại vì D-015 và spec 013.

## 8. Kiểm zoneinfo và `scheduled` trên Worker thật

**Decision**: Kiểm này là thủ tục cho Starter sau khi tự deploy. Plan và implement không deploy, không gọi API Cloudflare, không bắn cron.

Ba lớp:

1. Pytest trên CPython, đồng hồ tiêm, gói `tzdata` đã cài. Sáu mốc của nhánh `spike/zoneinfo-pyodide` phải ra độ lệch giờ 2, 3, 2, 3, 3, 2: `2026-01-15T12:00Z`, `2026-07-15T12:00Z`, `2026-03-29T00:59Z`, `2026-03-29T01:00Z`, `2026-10-25T00:59Z`, `2026-10-25T01:00Z`. Lớp này không chứng minh Worker.
2. `uv run pywrangler dev` đã chạy sáu mốc đó trên nhánh spike, qua route tạm `/spike/tz`. Route đó không được mang vào nhánh này. Lớp dev của lịch `scheduled` cũng chỉ mới thấy trên `spike/cron-checkin`, cron năm phút, chưa phải ba mốc UTC này.
3. Sau deploy, bắn một cron không chờ 08:00. Ứng viên trên `wrangler dev` là `GET /__scheduled?cron=0+5+*+*+*`. Đối chiếu đường dẫn với bản `pywrangler` lúc kiểm và với tài liệu Cron Triggers hiện hành trước khi gọi. Trên Worker đã deploy, bắn từ dashboard Cron Triggers hoặc API `schedules/.../trigger` của bản tài liệu lúc kiểm. Đọc dòng `morning_digest`. Mùa đông, cron `0 5 * * *` phải có `local_time` `07:00`, `outcome` `before_eight`, và không có tin mới. Cron `0 6 * * *` mới được phép gửi. Mùa hè, `0 5 * * *` là 08:00 địa phương và được phép gửi. Lệch giờ sai nghĩa là zoneinfo trên Worker cloud chưa đúng, dù pytest đã xanh.

**Rationale**: Pytest và `pywrangler dev` không chạy lịch của edge cloud. Bắn `0 5 * * *` phân biệt "scheduled có chạy" và "đồng hồ Helsinki đúng" mà không cần đợi buổi sáng, vì dòng log có `local_time` và lần 07:00 không được gửi.

**Alternatives considered**: Route tạm `/spike/tz` trên bản deploy. Thêm một đường HTTP chỉ để đo đồng hồ, rồi phải nhớ gỡ. Bị loại. Sửa cổng 08:00 thành một biến môi trường để ép gửi. Thêm một đường cấu hình không có trong spec. Bị loại.

## 9. Chỗ đặt đồng hồ và gói `tzdata`

**Decision**: `zoneinfo.ZoneInfo("Europe/Helsinki")` nằm trong `src/core/morning.py`. Không câu `import tzdata`. Gói `tzdata` thêm vào `[project].dependencies` của `pyproject.toml`, rồi khóa lại trong `uv.lock`, lúc implement. Starter đã duyệt gói này.

**Rationale**: `zoneinfo` là thư viện chuẩn, nên core vẫn chỉ import thư viện chuẩn (D-011, cổng Core imports). Trên Pyodide và Windows, dữ liệu múi giờ không đi kèm runtime. Cài `tzdata` là cách `ZoneInfo` tìm được `Europe/Helsinki` mà không import gói đó trong mã. Sáu mốc ở mục 8 đã đúng trên `pywrangler dev` của nhánh spike. Worker đã deploy chưa được đo. Đó là rủi ro mục 8, không phải lý do để chọn thư viện đồng hồ khác.

**Alternatives considered**: Tự bảng lệch UTC trong mã, không dùng `tzdata`. Lệch mùa hè đổi theo năm. Bị loại. Đặt `ZoneInfo` trong `src/scheduler/` và để core nhận ngày giờ đã đổi. Luật "từ 08:00" và ngày của mã update sẽ nằm ngoài chỗ test thuần của chữ bản tin. Một hàm trong core nhận `datetime` UTC và trả ngày, giờ, mã. Scheduler chỉ gọi.

## 10. Những việc đồng bộ docs, chưa làm

**Decision**: Không sửa docs trong bước plan. Lúc đồng bộ docs, cùng thay đổi implement:

- `docs/ARCHITECTURE.md` §3: đoạn cron đang ghi `scheduler/checkin.py` và có thể gọi LLM. Đường này là `entry.scheduled` → `scheduler/morning.py` → luật thuần, không gọi mô hình.
- `docs/ARCHITECTURE.md` §6: thêm dòng `morning_digest` và bảy khóa ở mục 7. Ba dòng log cũ giữ nguyên câu chữ.
- `docs/DECISIONS.md` không sửa trong implement. Mục mới ghi mã update âm theo ngày Helsinki, gói `tzdata` cùng `zoneinfo`, ba cron UTC và cổng 08:00, viết ở nhánh docs-only sau implement, số D-025. Không sửa D-007, D-011, D-018, D-021, D-022, D-023, D-024.
- Không sửa `docs/PRODUCT.md`: câu F10 vòng đầu vẫn là 08:00 Helsinki và `/next`.
- Không sửa diagram trong `docs/architecture/` (D-016).

## 11. Lịch sử gửi cho mô hình sau digest

**Decision**: Không chuẩn hóa vai trong `_history`, `llm_turn`, hay `anthropic_model`. Digest vào lịch sử như một tin assistant thường (FR-011). Không sửa `src/clients/anthropic_model.py`.

**Rationale**: Digest là một dòng assistant đứng một mình, nên lịch sử gửi mô hình có thể bắt đầu bằng assistant, hoặc có hai assistant liền nhau (tin cuối hôm qua rồi digest). `src/turns/llm_turn.py:185` ghép history với tin mới và đưa thẳng vào adapter, không chuẩn hóa. Kiểm ngày 2026-11-07, Starter chạy tay ba request tới API với model `claude-haiku-5-5`, `anthropic-version` `2023-06-01`: (a) tin đầu là assistant, rồi user: HTTP 200; (b) user, assistant, assistant, user: HTTP 200; (c) user, assistant, user (đối chứng): HTTP 200. API hiện tại nhận cả ba hình, nên không thêm mã để gộp vai hay chèn tin user giả.

**Rủi ro**: Mỗi ca chạy một lần, chỉ cho `claude-haiku-5-5`. Đổi model thì kiểm lại ba hình đó trước khi deploy.

**Alternatives considered**: Gộp các tin cùng vai ở adapter, và thêm một tin user giả khi tin đầu là assistant. Bị loại vì thêm mã mà API hiện tại không đòi.
