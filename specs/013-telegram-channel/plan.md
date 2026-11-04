# Implementation Plan: Kênh Telegram, phần logic

**Branch**: `013-telegram-channel` | **Date**: 2026-11-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-telegram-channel/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Chủ bot gửi một tin chữ trên Telegram và nhận một câu của lượt đã có, trong cùng cuộc trò chuyện, bằng chữ trơn. Kênh không thêm luật lập kế hoạch. Nhận một update là một RPC chèn theo khóa duy nhất. Lưu câu là so sánh-và-đặt. Ngữ cảnh và khoảng "lượt đã chết" dùng một đồng hồ do người gọi tiêm. Tách tin theo đơn vị UTF-16 nằm ở `src/core`. Ba câu của L1-04 thành hằng trong `src/turns/llm_turn.py`; chữ ký `run_turn` giữ nguyên. Chi tiết và các mục đã duyệt ở [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: FastAPI, `postgrest`, `anthropic` (SDK chỉ ở `src/clients/anthropic_model.py`). `httpx` chuyển từ `[dependency-groups].dev` sang `[project].dependencies` trong `pyproject.toml` và `uv.lock`. Đã duyệt. Không thêm gói và không thêm SDK Telegram.

**Storage**: Supabase qua PostgREST, chỉ từ `src/db/client.py`. Schema mô tả ở [data-model.md](./data-model.md). File migration tạo ở bước implement, không tạo trong bước plan. Không `db push`, không đụng migration cloud.

**Testing**: `uv run pytest`. Ca luật và ca luồng dùng đồ giả, không mở mạng. Client Telegram dùng `httpx.MockTransport`. Contract cổng chạy trên bản nhớ và bản Supabase local, theo mẫu `tests/test_plan_store_contract.py`. Eval offline không sửa.

**Target Platform**: CPython cho pytest. Cùng mã route chạy trên Cloudflare Python Workers qua `src/entry.py`. Vòng này không chạy `pywrangler dev`, không deploy, không `setWebhook`, không đổi `wrangler.jsonc` hay gói Cloudflare.

**Project Type**: Web service. Thêm webhook và client gửi. Không thêm tool.

**Performance Goals**: Một người dùng. Lượt giữ ngân sách 20 giây (D-015). Kho kế hoạch treo không nuốt ngân sách đó vì `run_turn` đã truyền `remaining` vào `execute_tool`. Chữ ký `execute_tool` không đổi.

**Constraints**: Nguyên tắc I đến VIII. D-011: core chỉ thư viện chuẩn; không đổi `Plan`, `Subtask`, `PlanStore`. D-012: cổng lưu là async. D-014 và D-015: bảy khóa log tool và tám khóa log mô hình giữ nguyên. Không đổi lời hướng dẫn, `PROMPT_VERSION`, bộ định nghĩa, `DEFINITIONS_VERSION`, bộ câu eval, cách chấm. `core/session.py` không dùng. Không `os.getenv` mới. Nguồn cấu hình của request là `request.scope["env"]`.

**Scale/Scope**: Một chủ bot, một cuộc trò chuyện riêng. Ngữ cảnh tối đa 20 tin đã lưu, mỗi tin tối đa 4096 đơn vị UTF-16, tuổi tối đa 24 giờ. Không thêm trần tổng ký tự.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Trước Phase 0

- **I. Một nhân vật**: câu người nhận là câu của lượt hoặc câu cố định đã chốt trong spec. Không thêm persona. Đạt.
- **II. Worker không giữ trạng thái**: bản ghi update và ngữ cảnh ở Supabase. Bộ nhớ giữa hai request không giữ hội thoại. Đồ giả chỉ trong `tests/`. Đạt.
- **III. PostgREST**: RPC mới đi qua `src/db/client.py`. Không driver TCP. Đạt.
- **IV. LLM qua cổng**: kênh gọi `run_turn`. SDK không ra khỏi `anthropic_model.py`. Khóa do người gọi đưa, adapter không đọc môi trường. Đạt.
- **V. Push chủ động**: lát này là webhook và câu trả lời, không phải lịch check-in. Không thêm lịch phía client. Đạt, ngoài phạm vi V.
- **VI. Database riêng**: không ghi kế hoạch sang Google Tasks hay Keep. Đạt.
- **VII. Ba giây của desktop**: ngân sách đó là đường giọng nói jarvis-desktop (D-005), không phải webhook này. Webhook dùng ngân sách 20 giây của lượt. Đạt vì không áp VII nhầm đường.
- **VIII. Unit test**: mỗi luật mới có test riêng, nêu ở mục Test. Đạt khi implement làm đúng danh sách đó.
- **Pydantic cho request**: body Telegram không phải schema của mình. Update không đọc được phải Bỏ qua và trả 2xx, không phải 422. Route đọc JSON bằng kiểm kiểu trên dict. Lý do ở Complexity Tracking.
- **Config chỉ qua settings**: bốn hàm đọc mới trong `src/config/settings.py`. Xóa dòng module `TELEGRAM_BOT_TOKEN` đang gọi `os.getenv`. Nếu `_get_str` không còn chỗ dùng thì xóa luôn, cùng `import os` nếu thừa.

### Sau Phase 1

Các cổng mới ở `src/core`, bản Supabase ở `src/db`, client HTTP ở `src/clients`, route ở `src/api`. Không cổng nào kéo SDK, PostgREST, hay `os.getenv` vào core hoặc vào `src/turns`. Điều phối không import `db`, `clients`, hay `config`. Gate vẫn đạt, với ngoại lệ Pydantic đã ghi.

## Project Structure

### Documentation (this feature)

```text
specs/013-telegram-channel/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── webhook.md
│   └── send-message.md
├── spec.md
└── checklists/requirements.md
```

`tasks.md` không tạo ở bước này.

### Source Code (repository root)

```text
src/core/telegram_channel.py       # luật thuần và ba cổng Protocol
src/db/client.py                   # thêm lời gọi RPC, không thêm đường DB khác
src/db/telegram_channel_store.py   # bản Supabase của cổng update và cổng ngữ cảnh
src/clients/telegram.py            # sendMessage bằng httpx
src/api/routes_telegram.py         # route mỏng, map kết quả sang HTTP
src/api/telegram_update.py         # điều phối
src/app.py                         # include_router
src/config/settings.py             # bốn hàm đọc
src/turns/llm_turn.py              # ba hằng L1-04, chữ ký run_turn giữ nguyên
tests/fakes/memory_telegram_channel.py
tests/test_telegram_channel_contract.py
tests/test_telegram_split.py
tests/test_telegram_context_window.py
tests/test_telegram_receive.py
tests/test_telegram_update_flow.py
tests/test_telegram_client.py
tests/test_telegram_route.py
tests/test_settings_telegram.py
tests/test_llm_turn.py             # chỉ ba chỗ đã duyệt
.env.example                       # chỉ thêm tên khóa mới, không giá trị
pyproject.toml và uv.lock          # chuyển httpx, đã duyệt
supabase/migrations/<mốc sau 20261103205500>_telegram_channel.sql
                                   # tạo lúc implement, không tạo lúc plan
docs/DECISIONS.md                  # task cuối, nguyên văn đã duyệt
docs/ARCHITECTURE.md               # cùng task docs
docs/reviews/2026-11-01-repo-review.md
```

**Structure Decision**: Không thêm gói mới trong `src/`. Điều phối đặt ở `src/api/telegram_update.py`. Lý do ở [research.md](./research.md). `src/turns` không import `clients`, `db`, `config`, `anthropic`. `src/tools` không import `db`. `execute_tool` không đổi.

## Design

### Cổng và luật thuần

File mới `src/core/telegram_channel.py`. Không sửa `src/core/plans.py`. Không import `fastapi`, `pydantic`, `tools`, `db`, `httpx`, `postgrest`, `anthropic`.

Một cổng ngữ cảnh, không hai. Đọc và ghi dùng chung khóa duy nhất `(update_id, role)`, nên tách hai Protocol không thêm bất biến nào.

- **UpdateStore**: `claim(update_id, started_at)`, `save_reply_if_absent(update_id, reply) -> bool`, `mark_sent(update_id, sent_at)`.
- **ContextStore**: `append_once(update_id, role, chat_id, body, saved_at)`, `list_recent(chat_id, saved_at_gte, limit)`.
- **TelegramSender**: `send_part(chat_id, text)`. Không tự tách. Người điều phối tách bằng luật thuần rồi gửi từng phần.

Luật thuần, đồng bộ, nhận đồng hồ từ ngoài:

- `split_utf16(text, limit=4096) -> tuple[str, ...]`. Đếm đơn vị UTF-16. Không cắt giữa một code point. Không phần rỗng. Đúng 4096 đơn vị là một phần. 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị) là hai phần.
- `select_context(rows, now) -> tuple`. Giữ tin `saved_at >= now - 24 giờ`, tính cả đúng 24 giờ. Lấy tối đa 20 tin mới nhất, trả theo thứ tự cũ tới mới. Tin mới của lượt không nằm trong danh sách này. `run_turn` tự nối tin mới vào sau.
- `decide_receive(record, now, dead_after) -> Run | Defer | Resend | SaveUncertain | Done`. `Done` khi đã gửi. `Resend` khi đã có câu mà chưa gửi. `Defer` khi chưa có câu và khoảng từ lúc bắt đầu đến `now` chưa quá `dead_after`, gồm đúng bằng `dead_after`. `SaveUncertain` khi chưa có câu và khoảng đó đã qua `dead_after`. `Run` chỉ khi `claim` báo chính lần này chèn được hàng.

`dead_after` là **90 giây**, một hằng số một chỗ. Đã duyệt, tạm thời, đo lại ở vòng chạy thật. Đúng 90 giây vẫn là Hoãn. Qua 90 giây là SaveUncertain. Test ở dưới 90 giây, đúng 90 giây, và trên 90 giây.

### Điều phối

`handle_update` trong `src/api/telegram_update.py` là `async def`. Nó await cổng và `run_turn`, và chỉ trả kết quả sau khi gửi xong hoặc sau khi đã quyết định không gửi. Không trả 200 rồi xử lý nền. Hàm này không import `db`, `clients`, hay `config`. Route đưa vào: giá trị đã đọc, factory mở cổng, đồng hồ, `PlanStore`, `ModelClient`.

Thứ tự, đúng spec:

1. Thiếu hoặc sai secret webhook: Từ chối. Không mở cổng.
2. Thiếu token bot: Từ chối. Không mở cổng.
3. Body không phải một update đọc được, không phải tin mới, không phải cuộc riêng, hoặc người gửi không phải chủ bot, hoặc thiếu danh tính chủ bot: Bỏ qua. Không mở cổng.
4. Mở cổng. Factory ném lỗi thiếu cấu hình kho, hoặc claim không đọc hay ghi được: Hoãn. Không gọi mô hình, không đụng kho kế hoạch, không gửi.
5. `claim` không chèn được hàng: `decide_receive`. Defer thì Hoãn, không ghi câu "chưa chắc" đè lên lượt đang chạy. Done thì không gửi. Resend thì không chạy lượt: `append_once` hai vai trước khi gửi, rồi gửi đúng câu đã lưu. SaveUncertain thì so sánh-và-đặt câu `Chưa chắc tin này đã được xử lý.`; khi lần này ghi được câu, cũng `append_once` hai vai trước khi gửi. Ghi ngữ cảnh lỗi thì Hoãn, không gửi, câu đã lưu giữ nguyên, mô hình không bị gọi lại (FR-022). Thua so sánh-và-đặt thì lần này không gửi câu của mình.
6. `claim` chèn được hàng: tin không phải chữ, hoặc chữ chỉ khoảng trắng, thì lưu và gửi `Mình chỉ đọc được tin chữ.`, không gọi mô hình, không đụng kho kế hoạch, không ghi ngữ cảnh. Tin chữ thì gọi `run_turn`.

`run_turn` giữ chữ ký `(user_message, history, *, store, api_key, client, log) -> str`. Kênh truyền `remaining` gián tiếp vì `run_turn` đã đưa `remaining` vào `execute_tool`. US8 là một test đầu-cuối của đường webhook: kho kế hoạch không trả về, đồng hồ lượt do test đẩy, câu không rỗng được gửi, không ngủ 20 giây thật.

Sau khi lượt trả chuỗi:

- Lưu câu bằng `save_reply_if_absent`. Thua (hàm trả false) thì lần này không gửi câu của mình.
- Lưu ném lỗi: Hoãn, không gửi câu chưa lưu (FR-021). Lần nhận sau thấy đã bắt đầu, chưa có câu. Khi đồng hồ qua `dead_after` thì nhánh SaveUncertain của FR-008.
- Ghi được câu: trước khi gửi, `append_once` cho vai `user` và vai `assistant`. Cùng luật đó cho mọi đường gửi một câu đã lưu: lượt vừa xong, gửi lại câu đã lưu, và câu `Chưa chắc tin này đã được xử lý.` Ghi ngữ cảnh lỗi thì Hoãn, không gửi, câu đã lưu giữ nguyên, mô hình không bị gọi lại (FR-022). Mỗi `append_once` thua khóa duy nhất thì bỏ qua, không nhân đôi (FR-013). Câu `Mình chỉ đọc được tin chữ.` và tin không phải chữ không ghi ngữ cảnh (FR-012).
- Gửi hết các phần xong thì `mark_sent`. Một phần thất bại thì không `mark_sent`, Hoãn, câu giữ nguyên. Lần sau gửi lại cả chuỗi gốc, sau khi ghi ngữ cảnh hai vai nếu chưa có.
- `MissingKeyError`: bắt riêng, lưu `str(error)`, ghi ngữ cảnh hai vai, rồi gửi. Câu đó là `Thiếu ANTHROPIC_API_KEY.` Không chứa giá trị khóa. Không chạy lại. Ghi ngữ cảnh lỗi thì Hoãn, không gửi.
- `asyncio.CancelledError`: raise lại. Không nuốt.
- `Exception` khác: lưu ngay `Chưa chắc tin này đã được xử lý.`, ghi ngữ cảnh hai vai, rồi gửi (FR-020). Không chờ `dead_after`, không chạy lại. Câu không chứa tên lớp hay thông điệp lỗi. Ghi ngữ cảnh lỗi thì Hoãn, không gửi.

Khóa mô hình: `require_anthropic_api_key` thiếu thì đưa `api_key=None` vào `run_turn` để vẫn ném `MissingKeyError`. Không chép câu thiếu khóa ra module khác.

Đồng hồ của kênh là `Callable[[], datetime]`, UTC có timezone, do route và test đưa vào. Tuổi 24 giờ và `dead_after` chỉ so với đồng hồ này. `started_at` và `saved_at` là giá trị hàm đó trả, đưa xuống RPC dưới dạng tham số. Hàm SQL của lát này không gọi `now()` và không đặt default `now()`. Không so `now()` của Postgres với mốc của ứng dụng. Đồng hồ monotonic của `run_turn` vẫn chỉ để tính 20 giây trong một lượt. Test kênh đẩy đồng hồ kênh. Test US8 đẩy `turns.llm_turn._now` như các test lượt hiện có. Không ngủ thật.

### Route và cấu hình

`src/api/routes_telegram.py` đọc body, gọi `handle_update`, trả `Response` rỗng. Không echo secret, token, chữ tin, hay câu trả lời.

Header secret: `X-Telegram-Bot-Api-Secret-Token`. So bằng `hmac.compare_digest` khi cả hai bên là `str`. Header thiếu, giá trị không phải `str`, hoặc `compare_digest` ném lỗi: Từ chối. Không ghi hai giá trị secret.

`src/config/settings.py`, cùng `_read_setting` và `_present` của `require_supabase` (có mặt khi là `str` khác rỗng, không strip):

- `require_telegram_webhook_secret(source)`
- `require_telegram_bot_token(source)`
- `require_telegram_owner_id(source)`
- `require_anthropic_api_key(source)`

Thiếu hoặc rỗng thì `SettingsError("Thiếu <TÊN>.")`. Mapping thì `.get`, nguồn khác thì `getattr`. Test đưa dict. Request thật đưa `request.scope["env"]`.

Mã chủ bot: `str(user_id) ==` chuỗi cấu hình, `user_id` là `int` và không phải `bool`. Không cắt khoảng trắng. `"123"` khớp `123`. `" 123"` không khớp.

`src/app.py` gọi `include_router`. Import app không đọc env Telegram. `tests/test_app_loads_plan_store.py` không sửa và vẫn pass.

`.env.example` chỉ thêm dòng tên `TELEGRAM_WEBHOOK_SECRET` và `TELEGRAM_OWNER_ID`, không giá trị. Dòng `TELEGRAM_BOT_TOKEN` và `ANTHROPIC_API_KEY` đã có, không viết lại.

### L1-04

Trong `src/turns/llm_turn.py`, cạnh `_MODEL_ERROR`:

- `_NO_REPLY = "Mình chưa có câu trả lời cho tin này."`
- `_CUT = "Câu trả lời bị cắt vì quá dài."`
- `_REFUSAL = "Mình không trả lời được tin này."`

`_normal_text`: còn chữ khác khoảng trắng thì giữ nguyên từng ký tự. Rỗng hoặc chỉ khoảng trắng, và `effects` không rỗng, thì `compose` như hiện tại. `effects` rỗng thì `_NO_REPLY`, không trả chuỗi rỗng.

`_finish`: `max_tokens` thành `_abnormal(effects, _CUT)`. `refusal` thành `_abnormal(effects, _REFUSAL)`. `stop_reason` khác, kể cả nhánh cuối hiện trả `_MODEL_ERROR`, vẫn `_abnormal(effects, _MODEL_ERROR)`. `effects` không rỗng thì vẫn `compose` (FR-011). Hết ngân sách và lỗi mô hình trong `run_turn` không đổi, vẫn `_MODEL_ERROR` khi không có effects.

Không đổi bảy khóa, tám khóa, `SYSTEM_PROMPT`, `PROMPT_VERSION`, `TOOL_DEFINITIONS`, `DEFINITIONS_VERSION`.

### Client gửi

`src/clients/telegram.py`: `POST https://api.telegram.org/bot<token>/sendMessage` với JSON đúng hai khóa `chat_id` và `text`. Không có `parse_mode`. Timeout 10 giây một phần. HTTP không 2xx, body `ok` không phải true, hoặc lỗi vận chuyển: ném lỗi, không chứa token trong thông điệp. Test `httpx.MockTransport` kiểm đúng các khóa JSON và không mở socket.

Gửi là ít nhất một lần. Không có khóa chống trùng. Đứt giữa các phần, hoặc hai lần nhận chồng lúc gửi, có thể làm cùng một câu tới hai lần. Lát này chấp nhận điều đó.

### Test

Mỗi ca một hàm mới. Không nhét vào test lớn có sẵn.

Khoảng 90 giây, một hằng số: dưới 90 giây là Hoãn, đúng 90 giây là Hoãn, qua 90 giây là SaveUncertain. Ba hàm, không ngủ thật.

Ghi ngữ cảnh, mỗi ca một hàm:

- Ghi lỗi ở lượt mới: 0 lần gửi, Hoãn, một lượt, câu giữ nguyên.
- Lần nhận sau: ghi đủ hai vai một lần rồi gửi đúng câu đã lưu.
- Gửi lại khi ngữ cảnh đã có: không nhân đôi.

`tests/test_llm_turn.py` đổi ba chỗ đã duyệt và thêm một hàm mới cho refusal không có lần ghi.

- `test_empty_text_is_success`, dòng 156 đến 159: `""` thành `_NO_REPLY`. Đổi tên hàm nếu tên "success" không còn đúng.
- `test_max_tokens_does_not_run_tools_and_logs_empty_error_type`, dòng 243 đến 256: kết quả `_MODEL_ERROR` thành `_CUT`. Giữ các assert log (`stop_reason`, `error_type`, `model`, số lần gọi, số dòng log).
- `test_model_text_and_tool_message_stay_exact`, dòng 985 và 986: `""` và `"   "` thành `_NO_REPLY`.

Không đổi dòng 744 đến 753 (có lần ghi thì ra bản ghép, kể cả `max_tokens`, `refusal`, và chữ trắng). Không đổi các test `_MODEL_ERROR` cho lỗi mô hình, quá hạn, và thiếu khóa (`test_missing_or_empty_key_skips_client`, `test_budget_stops_further_calls`, `test_model_error_hides_message`, `test_cancelled_error_propagates`). Cần đổi assert nào khác thì dừng, không sửa thêm.

`tests/test_eval_*` không sửa.

Mutation để implement chứng minh test đỏ được, mỗi cái một lần, rồi trả lại:

- Nhận nguyên tử: trong đồ giả, `await` giữa lúc đọc "chưa có hàng" và lúc chèn. Hai task chồng đều chạy lượt. Test chờ đúng một lượt và một kế hoạch thì đỏ.
- Lưu câu: bỏ điều kiện "chỉ ghi khi chưa có câu". Lượt chậm ghi đè câu `Chưa chắc tin này đã được xử lý.` và vẫn gửi. Test chờ một nội dung và lần thua không gửi thì đỏ.
- Biên ngữ cảnh: đếm 21 tin trong 24 giờ, hoặc so `>` thay vì `>=` với đúng 24 giờ. Test 20 tin và test đúng 24 giờ thì đỏ.
- UTF-16: tách bằng số code point. Chuỗi 2049 emoji ngoài mặt phẳng cơ bản thành một phần. Test chờ hai phần, mỗi phần tối đa 4096 đơn vị, ghép lại đúng chuỗi, thì đỏ.
- Thứ tự lưu rồi gửi: gọi gửi khi `save_reply_if_absent` ném lỗi. Test FR-021 chờ 0 lần gửi, Hoãn, và đúng một kế hoạch đã tạo thì đỏ.
- Gửi trước khi ghi ngữ cảnh: gọi gửi khi `append_once` ném lỗi. Test FR-022 chờ 0 lần gửi, Hoãn, một lượt, và câu giữ nguyên thì đỏ.

Contract: một fixture hai bản, như `plan_store` trong `tests/test_plan_store_contract.py`. Bản Supabase đi qua `prepare_local_source`. Host không phải local thì fail trước mạng. Thiếu biến hoặc không nối được thì skip đúng câu helper hiện có. Test xóa dòng của mình, không xóa trong `src/`.

### Docs, task cuối

Làm sau code, trong cùng tính năng. Nguyên văn dưới đây đã duyệt. Số là D-022 vì D-021 đang là quyết định cuối. Nếu trước lúc ghi đã có số đó, dùng số kế tiếp, không đổi nội dung.

```markdown
## D-022 — Kênh Telegram: danh tính chủ bot, một update một lần, ngữ cảnh hội thoại

**Date:** 2026-11-04
**Status:** Accepted

**Bối cảnh:** F11 đưa tin chữ của chủ bot vào lượt đã có và gửi câu trả lời về cùng cuộc trò chuyện. F10 và F18 dùng lại ba luật này. Kho kế hoạch không có khái niệm người dùng.

**Quyết định:**
1. Danh tính chủ bot là mã số người gửi trên Telegram, không phải tên người dùng. So khớp đúng mã số. Chuỗi thập phân của cùng mã đó được coi là khớp. Không cắt khoảng trắng.
2. Một update, nhận bằng mã update, chỉ chạy lượt một lần và không tạo hai kế hoạch. Trạng thái nằm ở kho bền, không nằm trong bộ nhớ Worker giữa hai request. Câu `Chưa chắc tin này đã được xử lý.` là kết quả đã lưu khi update đứt hoặc khi lượt ném ngoại lệ không phải thiếu khóa. Câu này khác câu `Chưa chắc thay đổi đã được lưu.` của D-021.
3. Ngữ cảnh là các tin chữ của chủ bot và câu trả lời của bot trong cuộc trò chuyện riêng, tối đa 20 tin đã lưu, không quá 24 giờ, theo thứ tự cũ tới mới, rồi tới tin mới. Ngữ cảnh nằm ở kho bền. Không dùng `session_id`. Chỉ câu `Mình chỉ đọc được tin chữ.` đứng ngoài ngữ cảnh. Mọi đường gửi câu đã lưu ghi ngữ cảnh trước khi gửi, ghi lỗi thì Hoãn.

**Lý do:** Ba luật này là hợp đồng các vòng sau dùng lại. Nhét người dùng vào kế hoạch, hoặc nhớ hội thoại trong Worker, làm sai nguyên tắc II và làm F10 không dùng lại được.

**Phương án đã bỏ:** nhận diện bằng tên người dùng Telegram; chống trùng bằng bộ nhớ của một isolate; ngữ cảnh theo `session_id` của F02 (`src/core/session.py`).
```

`docs/ARCHITECTURE.md`: sửa câu "Route và Telegram chưa gọi lượt này" và các mục module, luồng HTTP, logging cho khớp kênh. Không sửa `docs/PRODUCT.md`.

`docs/reviews/2026-11-01-repo-review.md`: L1-04 đóng. L1-13 chỉ đóng phần độ dài (tách 4096 đơn vị UTF-16); dòng trống trong bản ghép và câu "Đã lưu" khi việc con không đổi vẫn mở. L1-12 đóng cho đường Telegram vì đường đó đi qua `run_turn`, và `run_turn` đã truyền `remaining`. `execute_tool` vẫn mặc định `remaining=None`, nghĩa là không giới hạn, và mục đó vẫn mở cho F10.

D-016: lát này không thêm gói `src/`. Nó nối webhook với lượt, tức nối hai cụm trước đây chưa nối, nên hình dạng kiến trúc có đổi. Diagram trong `docs/architecture/` không sửa trong tính năng này. Commit diagram, nếu làm, là commit riêng sau commit code.

### Ngoài phạm vi

Migration lên cloud, deploy, `wrangler.jsonc`, `pywrangler dev`, `setWebhook`, đổi gói Cloudflare, SDK Telegram, sửa `Plan` hoặc `PlanStore`, sửa `execute_tool`, sửa bộ eval. Vòng chạy thật gọi một lần danh sách mở đầu bằng `assistant` để xem API trả gì. Lát này không thêm bộ lọc.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Body webhook không dùng model Pydantic | Spec bắt update không đọc được phải Bỏ qua, mã 2xx. Model chặt biến body lạ thành 422, tức không phải Bỏ qua. | Pydantic đủ cho schema mình sở hữu. Update Telegram không phải schema đó, và nhánh Bỏ qua phải nuốt thân lạ. |

## Đã duyệt

1. Khoảng lượt đã chết: 90 giây, tạm thời, đo lại ở vòng chạy thật. Hằng số đặt một chỗ. Đúng 90 giây vẫn là Hoãn, qua 90 giây là SaveUncertain. Có test ở hai phía và test ở đúng 90 giây.
2. HTTP: Từ chối 401, Hoãn 503, Bỏ qua và xong 200, body rỗng.
3. Lỗi gửi vĩnh viễn: mọi lỗi gửi là Hoãn, đúng spec. Không thêm nhánh dừng gửi.
4. Ngữ cảnh: không thêm trần tổng ký tự.
5. Danh sách messages: không thêm bộ lọc ở 013. Ghi vào danh sách vòng chạy thật: gọi thật một lần với danh sách mở đầu bằng assistant để xem API trả gì.
6. Handler: async def, trả HTTP sau khi gửi xong, không tác vụ nền.
7. httpx: chuyển từ dev sang dependencies, không thêm gói. Đây là chuyển nhóm đã duyệt, không cần dừng.
8. D-022: duyệt nguyên văn, cộng một câu: mọi đường gửi câu đã lưu ghi ngữ cảnh trước khi gửi, ghi lỗi thì Hoãn.

Cũng đã duyệt: POST /telegram, timeout 10 giây mỗi sendMessage, body rỗng, quickstart.md.
