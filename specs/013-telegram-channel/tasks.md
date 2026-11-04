---
description: "Task list for Kênh Telegram, phần logic"
---

# Tasks: Kênh Telegram, phần logic

**Input**: Design documents from `/specs/013-telegram-channel/`

**Prerequisites**: plan.md (mục "Đã duyệt"), spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Có. Viết trước mã tương ứng. Mỗi ca một hàm mới. Không nhét nhiều ca vào một hàm.

**Organization**: Phase theo thứ tự đã chốt, không phải một phase một story. Nhãn `[USn]` chỉ để truy story. Năm story P1 là US1, US2, US3, US4, US8. Bốn story P2 là US5, US6, US7, US9. Cả chín story cần các phase sau nền.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: File khác nhau, không phụ thuộc task chưa xong
- **[Story]**: Chỉ để truy story. Phase không chia theo story
- Mỗi task một việc, có đường dẫn file

## Path Conventions

- Repo một project: `src/`, `tests/` ở gốc
- File được sửa hoặc tạo chỉ là các dòng trong `specs/013-telegram-channel/allowed-files.txt`
- Không thêm gói. `pyproject.toml` và `uv.lock` chỉ chuyển `httpx` từ nhóm dev sang `dependencies`. Việc này đã duyệt trong plan, mục "Đã duyệt" điều 7. Không cần dừng chỉ vì chuyển nhóm
- `pylock.toml` đã có `httpx` qua `postgrest`. Không sửa. Nếu `uv lock` hay lệnh nào buộc phải đổi `pylock.toml`, dừng. Dòng đầu câu trả lời là `[DỪNG - CẦN CLAUDE CHAT]` và một câu lý do
- `docs/DECISIONS.md` chỉ được thêm D-022 nguyên văn từ plan.md. Đã duyệt. Không sửa `docs/PRODUCT.md`. Không sửa `.specify/memory/constitution.md`. Nếu một câu constitution thành sai, dừng, không sửa
- Không sửa lời hướng dẫn, `PROMPT_VERSION`, bộ định nghĩa tool, `DEFINITIONS_VERSION`, `evals/`, `tests/test_eval_*`, spec cũ, `wrangler.jsonc`, `execute_tool`, `Plan`, `PlanStore`
- Không task push, `db push`, `db reset` lên cloud, deploy, `pywrangler`, `setWebhook`
- Không đọc, không ghi `.env` thật và `.dev.vars`
- Việc thật khác plan thì dừng, kể cả khi task này ghi là đã duyệt

---

## Phase 1: Setup

**Purpose**: Chuyển `httpx` đã duyệt. Không thêm gói

- [ ] T001 Trong `pyproject.toml`, chuyển `httpx>=0.28.1` từ `[dependency-groups].dev` sang `[project].dependencies`. Không thêm gói. Không thêm SDK Telegram. Đã duyệt trong plan. Không sửa `pylock.toml`

- [ ] T002 Chạy `uv lock` để `uv.lock` chuyển `httpx` cùng nhóm với T001 (phụ thuộc T001). Không sửa `uv.lock` bằng tay. Không sửa `pylock.toml`. Nếu lệnh đổi `pylock.toml`, hoàn tác và dừng

**Checkpoint**: Không có gói mới. `pylock.toml` không đổi

---

## Phase 2: Luật thuần và đồ giả

**Purpose**: `split_utf16`, `select_context`, `decide_receive`, hằng 90 giây một chỗ, ba Protocol, đồ giả. Chặn mọi story

**Checkpoint**: Ba hàm mốc 90 giây và ca UTF-16, cửa sổ ngữ cảnh, claim, so sánh-và-đặt, FR-013 pass trên đồ giả. Không mở mạng

### Tests

- [ ] T003 [P] [US6] Viết `test_exactly_4096_units_is_one_part` trong `tests/test_telegram_split.py`. Chuỗi đúng 4096 đơn vị UTF-16 là một phần. Không phần rỗng. Chạy trước khi có `src/core/telegram_channel.py`. Kỳ vọng fail

- [ ] T004 [US6] Viết `test_2049_non_bmp_emoji_is_two_parts` trong `tests/test_telegram_split.py` (phụ thuộc T003). 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị) là hai phần. Mỗi phần tối đa 4096 đơn vị. Ghép lại đúng chuỗi. Không cắt giữa một code point. Chạy trước mã. Kỳ vọng fail

- [ ] T005 [P] [US5] Viết `test_exactly_24h_kept_older_dropped` trong `tests/test_telegram_context_window.py`. `select_context` giữ `saved_at >= now - 24 giờ`, gồm đúng 24 giờ. Tin cũ hơn 24 giờ không vào. Không thêm trần tổng ký tự. Chạy trước mã. Kỳ vọng fail

- [ ] T006 [US5] Viết `test_20_newest_messages_old_to_new` trong `tests/test_telegram_context_window.py` (phụ thuộc T005). Hơn 20 tin trong 24 giờ thì chỉ 20 tin mới nhất, thứ tự cũ tới mới. Tin mới của lượt không nằm trong danh sách này. Không bỏ tin đầu khi danh sách mở đầu bằng `assistant`. Chạy trước mã. Kỳ vọng fail

- [ ] T007 [P] [US3] Viết `test_under_90_seconds_is_defer` trong `tests/test_telegram_receive.py`. `decide_receive` khi chưa có câu và khoảng từ `started_at` đến `now` nhỏ hơn hằng 90 giây thì `Defer` (nhánh Hoãn). Test import hằng đó, không chép số 90 chỗ thứ hai. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T008 [US3] Viết `test_exactly_90_seconds_is_defer` trong `tests/test_telegram_receive.py` (phụ thuộc T007). Đúng bằng hằng 90 giây vẫn là `Defer` (Hoãn), chưa phải `SaveUncertain`. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T009 [US3] Viết `test_past_90_seconds_is_save_uncertain` trong `tests/test_telegram_receive.py` (phụ thuộc T008). Qua hằng 90 giây, chưa có câu, là `SaveUncertain`. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T010 [US3] Viết `test_sent_record_is_done` trong `tests/test_telegram_receive.py` (phụ thuộc T009). `sent_at` có giá trị thì `Done`. Chạy trước mã. Kỳ vọng fail

- [ ] T011 [US3] Viết `test_saved_unsent_is_resend` trong `tests/test_telegram_receive.py` (phụ thuộc T010). `reply` không null và `sent_at` null thì `Resend`. `reply` null là chưa có câu. Chuỗi rỗng không có nghĩa là chưa có câu. Chạy trước mã. Kỳ vọng fail

- [ ] T066 [US3] Viết `test_dead_after_is_90_seconds` trong `tests/test_telegram_receive.py` (phụ thuộc T011). Hằng khoảng lượt đã chết đúng bằng 90 giây. Đây là giá trị đã duyệt, test ghim nó. Chạy trước mã. Kỳ vọng fail

- [ ] T012 [P] [US3] Viết `test_claim_one_insert` trong `tests/test_telegram_channel_contract.py`. Fixture hai bản, như `plan_store` trong `tests/test_plan_store_contract.py`. Bản Supabase đi qua `prepare_local_source`. Host không phải `127.0.0.1` hoặc `localhost` thì fail trước mạng. Thiếu biến hoặc không nối được thì skip đúng câu helper hiện có. Hai lời gọi chồng cùng `update_id`: một `inserted` true, lời kia false, cùng `started_at` của lời chèn. Lời false không được hiểu là chạy lượt. Chạy trước đồ giả và trước migration. Kỳ vọng fail. Ca memory không mở mạng. Task không chạy `db reset`

- [ ] T013 [US3] Viết `test_save_reply_only_when_absent` trong `tests/test_telegram_channel_contract.py` (phụ thuộc T012). `save_reply_if_absent` trả true khi `reply` đang null và đúng một hàng đổi. Trả false khi đã có câu, và không đè câu cũ. Chạy trước đồ giả. Kỳ vọng fail

- [ ] T014 [US5] Viết `test_append_once_does_not_duplicate_role` trong `tests/test_telegram_channel_contract.py` (phụ thuộc T013). Đây là hàm riêng của FR-013. Cùng `(update_id, role)` lần thứ hai không thêm hàng và không đổi `body`. `role` chỉ `user` hoặc `assistant`. Chạy trước đồ giả. Kỳ vọng fail

- [ ] T015 [US5] Viết `test_list_recent_cutoff_and_limit` trong `tests/test_telegram_channel_contract.py` (phụ thuộc T014). `list_recent` giữ `saved_at >=` mốc người gọi đưa, tối đa 20, không gọi `now()` của kho. Chạy trước đồ giả. Kỳ vọng fail

### Implementation

- [ ] T016 Tạo `src/core/telegram_channel.py` (phụ thuộc T003 đến T011, T066). `split_utf16(text, limit=4096)`, `select_context(rows, now)`, `decide_receive(record, now, dead_after)`. Hằng 90 giây đúng một chỗ trong file này. `Defer` khi chưa có câu và khoảng chưa quá hằng, gồm đúng bằng hằng. `SaveUncertain` khi chưa có câu và đã qua hằng. Ba Protocol: `UpdateStore` (`claim`, `save_reply_if_absent`, `mark_sent`), `ContextStore` (`append_once`, `list_recent`), `TelegramSender` (`send_part`). Không sửa `src/core/plans.py`. Không import `fastapi`, `pydantic`, `tools`, `db`, `httpx`, `postgrest`, `anthropic`

- [ ] T017 Tạo `tests/fakes/memory_telegram_channel.py` (phụ thuộc T012 đến T016). `claim` không `await` giữa lúc thấy chưa có hàng và lúc chèn. `save_reply_if_absent` chỉ gán khi `reply is None`. `append_once` thua khóa thì không đổi `body`. Dict nằm trong một đối tượng. Bản nhớ không phải trạng thái giữa hai request sản xuất

---

## Phase 3: L1-04

**Purpose**: Ba câu trong `src/turns/llm_turn.py`. Chữ ký `run_turn` giữ nguyên. Chỉ ba assert đã duyệt

**Independent Test**: `tests/test_llm_turn.py` đổi đúng ba chỗ. Các assert khác giữ nguyên

- [ ] T018 [US4] Trong `tests/test_llm_turn.py`, `test_empty_text_is_success` dòng 156 đến 159: `""` thành `_NO_REPLY` (`Mình chưa có câu trả lời cho tin này.`). Đổi tên hàm nếu tên "success" không còn đúng (phụ thuộc không có). Không đổi assertion khác của file. Chạy trước khi sửa `src/turns/llm_turn.py`. Kỳ vọng fail

- [ ] T019 [US4] Trong `tests/test_llm_turn.py`, `test_max_tokens_does_not_run_tools_and_logs_empty_error_type` dòng 243 đến 256: kết quả `_MODEL_ERROR` thành `_CUT` (`Câu trả lời bị cắt vì quá dài.`) (phụ thuộc T018). Giữ assert log `stop_reason`, `error_type`, `model`, số lần gọi, số dòng log. Chạy trước mã. Kỳ vọng fail

- [ ] T020 [US4] Trong `tests/test_llm_turn.py`, `test_model_text_and_tool_message_stay_exact` dòng 985 và 986: `""` và `"   "` thành `_NO_REPLY` (phụ thuộc T019). Chạy trước mã. Kỳ vọng fail

- [ ] T060 [US4] Trong `tests/test_llm_turn.py` thêm hàm mới `test_refusal_without_effects_returns_refusal_sentence` (phụ thuộc T020). Mô hình giả dừng `refusal`, lượt không có lần ghi thành công, bị bỏ, hay bị từ chối: kết quả đúng chuỗi `Mình không trả lời được tin này.`, không phải `_MODEL_ERROR`, không có lần gọi tool. So với chuỗi nguyên văn, không import hằng. Không đổi assert của hàm có sẵn. Chạy trước mã. Kỳ vọng fail

- [ ] T021 [US4] Trong `src/turns/llm_turn.py`, thêm `_NO_REPLY`, `_CUT`, `_REFUSAL` (`Mình không trả lời được tin này.`) cạnh `_MODEL_ERROR` (phụ thuộc T018, T019, T020, T060). `_normal_text`: còn chữ khác khoảng trắng thì giữ nguyên. Rỗng hoặc chỉ khoảng trắng, `effects` không rỗng thì `compose`. `effects` rỗng thì `_NO_REPLY`. `_finish`: `max_tokens` thành `_abnormal(effects, _CUT)`, `refusal` thành `_abnormal(effects, _REFUSAL)`. `effects` không rỗng vẫn `compose`. Hết ngân sách và lỗi mô hình vẫn `_MODEL_ERROR` khi không có effects. Chữ ký `run_turn` và kiểu trả về `str` không đổi. Không đổi bảy khóa, tám khóa, `SYSTEM_PROMPT`, `PROMPT_VERSION`, `TOOL_DEFINITIONS`, `DEFINITIONS_VERSION`. Không đổi dòng 744 đến 753. Không đổi `test_missing_or_empty_key_skips_client`, `test_budget_stops_further_calls`, `test_model_error_hides_message`, `test_cancelled_error_propagates`. Cần đổi assert nào khác thì dừng, không sửa thêm

**Checkpoint**: Ba chỗ đã duyệt pass. Không file eval nào đổi

---

## Phase 4: Cổng Supabase và migration

**Purpose**: Schema và RPC đúng data-model.md. File migration tạo ở bước này, đã duyệt trong plan. Không `db push`, không `db reset` lên cloud

- [ ] T022 [US3] Tạo `supabase/migrations/20261104143000_telegram_channel.sql` (phụ thuộc T017). Mốc này đứng sau `20261103205500`. Đã duyệt trong plan: mô tả schema ở data-model.md, file tạo lúc implement. Không sửa migration cũ. Không `db push`. Không `db reset` lên cloud. Không gọi `now()` và không `default now()`. Bảng `telegram_updates`: `update_id bigint` khóa chính, `started_at timestamptz not null`, `reply text` null khi chưa có câu, `sent_at timestamptz` null khi chưa gửi xong. Bảng `telegram_context_messages`: khóa chính `(update_id, role)`, `update_id bigint not null` khóa ngoài, `role text not null` với `check (role in ('user', 'assistant'))`, `chat_id bigint not null`, `body text not null`, `saved_at timestamptz not null`. RLS bật. `revoke all` từ `public`, `anon`, `authenticated`. `grant` cho `service_role`. Không policy cho `anon` hay `authenticated`. Hàm, mỗi hàm revoke rồi `grant execute` cho `service_role`: `claim_telegram_update(bigint, timestamptz)` là `insert ... on conflict (update_id) do nothing` rồi trả hàng và `inserted` trong cùng hàm. `save_telegram_reply(bigint, text)` là `update ... set reply = p_reply where update_id = p_update_id and reply is null`, trả true khi đúng một hàng đổi. `mark_telegram_sent(bigint, timestamptz)` chỉ khi `reply is not null` và `sent_at is null`. `append_telegram_context(bigint, text, bigint, text, timestamptz)` là `insert ... on conflict (update_id, role) do nothing`. `list_telegram_context(bigint, timestamptz, integer)` lọc `saved_at >= p_saved_at_gte`, `order by saved_at desc, role desc`, `limit p_limit`. Nếu việc thật cần cột, hàm, hoặc quyền khác data-model.md, dừng

- [ ] T023 [US3] Trong `src/db/client.py`, thêm lời gọi năm RPC của T022 (phụ thuộc T022). Không thêm đường DB khác. Không driver TCP. Không gọi `now()`

- [ ] T024 [US3] Tạo `src/db/telegram_channel_store.py` (phụ thuộc T023). Bản Supabase của `UpdateStore` và `ContextStore`, đi qua `src/db/client.py`. Cùng ca `tests/test_telegram_channel_contract.py`. Test xóa dòng của mình, không xóa trong `src/`. Lỗi RPC khi lưu câu không phải false

**Checkpoint**: Contract pass trên đồ giả. Bản Supabase local pass khi có biến test. Không đụng cloud

---

## Phase 5: Client gửi

**Purpose**: `sendMessage` chỉ `chat_id` và `text`. Timeout 10 giây. Đã duyệt

- [ ] T025 [US6] Viết `test_send_message_json_has_chat_id_and_text_only` trong `tests/test_telegram_client.py`. `httpx.MockTransport`. JSON đúng hai khóa `chat_id` và `text`. Không `parse_mode`. Không mở socket. Chạy trước `src/clients/telegram.py`. Kỳ vọng fail

- [ ] T026 [US6] Viết `test_send_failure_raises_without_token` trong `tests/test_telegram_client.py` (phụ thuộc T025). Timeout 10 giây một phần. HTTP không 2xx, body `ok` không phải true, hoặc lỗi vận chuyển: ném lỗi. Thông điệp không chứa token. Chạy trước mã. Kỳ vọng fail

- [ ] T027 [US6] Tạo `src/clients/telegram.py` (phụ thuộc T025, T026, T001). `POST https://api.telegram.org/bot<token>/sendMessage`. Không tự tách. Không phân loại lỗi vĩnh viễn. Mọi lỗi gửi là lỗi để người điều phối Hoãn

**Checkpoint**: MockTransport pass. Không gọi Telegram thật

---

## Phase 6: Settings

**Purpose**: Bốn hàm đọc. Xóa `os.getenv` của token. `.env.example` chỉ thêm tên, đã duyệt

- [ ] T028 [US2] Viết `test_require_telegram_settings_missing_raises` trong `tests/test_settings_telegram.py`. Bốn hàm `require_telegram_webhook_secret`, `require_telegram_bot_token`, `require_telegram_owner_id`, `require_anthropic_api_key`. Nguồn là dict. Thiếu hoặc `str` rỗng thì `SettingsError` đúng `Thiếu TELEGRAM_WEBHOOK_SECRET.`, `Thiếu TELEGRAM_BOT_TOKEN.`, `Thiếu TELEGRAM_OWNER_ID.`, `Thiếu ANTHROPIC_API_KEY.`. Không strip. Không gọi `os.getenv`. Chạy trước khi sửa `src/config/settings.py`. Kỳ vọng fail

- [ ] T029 [US2] Viết `test_owner_id_match_rules` trong `tests/test_settings_telegram.py` (phụ thuộc T028). Hàm so mã trong `src/config/settings.py`: `user_id` là `int` và không phải `bool`. `"123"` khớp `123`. `" 123"` không khớp. Không cắt khoảng trắng. Chạy trước hàm đó. Kỳ vọng fail

- [ ] T030 [US2] Trong `src/config/settings.py`, thêm bốn hàm của T028 và hàm so mã của T029, cùng `_read_setting` và `_present` của `require_supabase` (phụ thuộc T028, T029). Mapping thì `.get`, nguồn khác thì `getattr`. Xóa dòng module `TELEGRAM_BOT_TOKEN`. Nếu `_get_str` không còn chỗ dùng thì xóa, cùng `import os` nếu thừa. Không thêm `os.getenv`

- [ ] T031 [US2] Trong `.env.example`, chỉ thêm hai dòng tên `TELEGRAM_WEBHOOK_SECRET` và `TELEGRAM_OWNER_ID`, không giá trị (phụ thuộc không có). Không viết lại dòng `TELEGRAM_BOT_TOKEN` và `ANTHROPIC_API_KEY` đã có. Đã duyệt trong plan. Không đọc, không ghi `.env` và `.dev.vars`

---

## Phase 7: Điều phối

**Purpose**: `handle_update` trả sau khi gửi xong. Không tác vụ nền. Các hàm FR-020, FR-021, FR-022 mỗi hàm một task

**Independent Test**: Kho giả, mô hình giả, client giả. Không mở mạng. Không ngủ thật

### Tests

- [ ] T032 [US1] Viết `test_owner_text_sends_one_plain_sentence` trong `tests/test_telegram_update_flow.py`. Tin chữ của chủ bot, mô hình giả trả một câu có dấu sao, gạch dưới, và backtick. Client giả nhận đúng câu đó một lần, nguyên văn, cùng cuộc trò chuyện, không `parse_mode`. `/start` đi cùng đường. Kho kế hoạch không bị đụng khi mô hình không gọi tool. Chạy trước `src/api/telegram_update.py`. Kỳ vọng fail. Đây là SC-001

- [ ] T033 [US3] Viết `test_overlap_while_running_defers` trong `tests/test_telegram_update_flow.py` (phụ thuộc T032). Lần nhận chồng khi lượt đang chạy: Hoãn, không chạy lượt thứ hai, không ghi câu chưa chắc đè. Chạy trước mã. Kỳ vọng fail

- [ ] T034 [US4] Viết `test_unexpected_exception_saves_uncertain_immediately` trong `tests/test_telegram_update_flow.py` (phụ thuộc T033). Đây là hàm riêng của FR-020. Ngoại lệ không phải thiếu khóa: lưu ngay `Chưa chắc tin này đã được xử lý.`, ghi ngữ cảnh hai vai, rồi gửi. Không chờ 90 giây. Không chạy lại. Câu không chứa tên lớp hay thông điệp lỗi. `CancelledError` không bị nuốt. Chạy trước mã. Kỳ vọng fail

- [ ] T035 [US3] Viết `test_save_reply_failure_defers_then_uncertain` trong `tests/test_telegram_update_flow.py` (phụ thuộc T034). Đây là hàm riêng của FR-021. Lượt đã xong, `save_reply_if_absent` ném lỗi: 0 lần gửi, Hoãn, đúng một kế hoạch, mô hình không bị gọi lại. Lần nhận sau, đồng hồ kênh đẩy qua 90 giây, không ngủ thật: gửi đúng một lần `Chưa chắc tin này đã được xử lý.`, mô hình không bị gọi thêm. Chạy trước mã. Kỳ vọng fail

- [ ] T036 [US5] Viết `test_context_write_failure_sends_nothing` trong `tests/test_telegram_update_flow.py` (phụ thuộc T035). Hàm FR-022 thứ nhất. Ghi ngữ cảnh lỗi ở lượt mới: 0 lần gửi, Hoãn, một lượt, câu giữ nguyên, mô hình không bị gọi lại. Chạy trước mã. Kỳ vọng fail

- [ ] T037 [US5] Viết `test_next_receive_writes_both_roles_then_sends_saved` trong `tests/test_telegram_update_flow.py` (phụ thuộc T036). Hàm FR-022 thứ hai. Lần nhận sau: ghi đủ hai vai một lần rồi gửi đúng câu đã lưu. Chạy trước mã. Kỳ vọng fail

- [ ] T038 [US5] Viết `test_resend_does_not_duplicate_context` trong `tests/test_telegram_update_flow.py` (phụ thuộc T037). Hàm FR-022 thứ ba. Gửi lại khi ngữ cảnh đã có: không nhân đôi. Không chạy lượt. Chạy trước mã. Kỳ vọng fail

- [ ] T039 [US7] Viết `test_non_text_fixed_sentence_skips_context` trong `tests/test_telegram_update_flow.py` (phụ thuộc T038). Parametrize, mỗi `id` một ca: `voice`, `photo`, `file`, `captioned_photo`, `sticker`, `location`, `contact`, `poll`, `empty_text`, `whitespace_text`. Danh sách lấy từ spec.md dòng 160 và dòng 166: voice, ảnh, file, ảnh có chú thích, sticker, vị trí, danh thiếp, cuộc bình chọn, cộng chữ rỗng và chữ chỉ khoảng trắng. Mỗi ca lưu và gửi đúng `Mình chỉ đọc được tin chữ.` Không gọi mô hình, không đụng kho kế hoạch, không ghi ngữ cảnh. Chạy trước mã. Kỳ vọng fail

- [ ] T040 [US8] Viết `test_hung_plan_store_stays_inside_turn_budget` trong `tests/test_telegram_update_flow.py` (phụ thuộc T039). Kho kế hoạch không trả về. Đẩy `turns.llm_turn._now` như test lượt hiện có. Câu không rỗng được gửi. Nhật ký của chính ca này không có token bot và không có secret webhook. Không ngủ 20 giây thật. Không đổi chữ ký `execute_tool`. Chạy trước mã. Kỳ vọng fail. Đây là US8.2

- [ ] T041 [US3] Viết `test_store_down_at_receive_defers` trong `tests/test_telegram_update_flow.py` (phụ thuộc T040). Kho không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho: Hoãn, không lượt, không mô hình, không kho kế hoạch, không gửi. Chạy trước mã. Kỳ vọng fail

- [ ] T042 [US4] Viết `test_missing_key_saves_sentence_without_key_value` trong `tests/test_telegram_update_flow.py` (phụ thuộc T041). `require_anthropic_api_key` thiếu thì `api_key=None`. Bắt `MissingKeyError`, lưu `str(error)`, ghi ngữ cảnh hai vai, rồi gửi. Câu là `Thiếu ANTHROPIC_API_KEY.` Không chứa giá trị khóa. Ghi ngữ cảnh lỗi thì Hoãn, không gửi. Chạy trước mã. Kỳ vọng fail

- [ ] T043 [US6] Viết `test_partial_send_retries_whole_sentence` trong `tests/test_telegram_update_flow.py` (phụ thuộc T042). Câu hai phần. Phần thứ hai thất bại thì không `mark_sent`, Hoãn, câu giữ nguyên. Lần sau gửi lại cả chuỗi gốc, tách cùng luật, từ phần đầu. Mô hình không bị gọi. Chạy trước mã. Kỳ vọng fail. Đây là US6.4

- [ ] T061 [US5] Viết `test_yes_after_bot_question_sees_the_question` trong `tests/test_telegram_update_flow.py` (phụ thuộc T043). Mô hình giả ghi lại danh sách messages nó nhận. Đồ giả ngữ cảnh được gieo sẵn, mốc `saved_at` tính từ đồng hồ kênh tiêm vào. Ngữ cảnh có câu của bot "Bạn muốn mình lập kế hoạch không?" chưa quá 24 giờ. Chủ bot gửi "có". Mô hình thấy câu đó đúng thứ tự cũ tới mới, rồi "có" là tin cuối. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T062 [US5] Viết `test_only_20_newest_stored_messages_reach_model` trong `tests/test_telegram_update_flow.py` (phụ thuộc T061). Mô hình giả ghi lại danh sách messages nó nhận. Đồ giả ngữ cảnh được gieo sẵn, mốc `saved_at` tính từ đồng hồ kênh tiêm vào. 25 tin trong 24 giờ. Mô hình nhận đúng 20 tin mới nhất, cũ tới mới, rồi tin mới. Tổng 21. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T063 [US5] Viết `test_stored_message_older_than_24h_is_not_sent_to_model` trong `tests/test_telegram_update_flow.py` (phụ thuộc T062). Mô hình giả ghi lại danh sách messages nó nhận. Đồ giả ngữ cảnh được gieo sẵn, mốc `saved_at` tính từ đồng hồ kênh tiêm vào. Tin lưu cũ hơn 24 giờ một giây so với đồng hồ kênh không vào danh sách. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T064 [US5] Viết `test_stored_message_at_exactly_24h_is_sent_to_model` trong `tests/test_telegram_update_flow.py` (phụ thuộc T063). Mô hình giả ghi lại danh sách messages nó nhận. Đồ giả ngữ cảnh được gieo sẵn, mốc `saved_at` tính từ đồng hồ kênh tiêm vào. Tin lưu đúng 24 giờ vào danh sách. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T065 [US5] Viết `test_fresh_handler_same_store_sees_previous_pair` trong `tests/test_telegram_update_flow.py` (phụ thuộc T064). Mô hình giả ghi lại danh sách messages nó nhận. Đồ giả ngữ cảnh được gieo sẵn, mốc `saved_at` tính từ đồng hồ kênh tiêm vào. Lần nhận một xong. Lần nhận hai dựng đối tượng cổng và handler mới trên cùng đồ giả kho bền, không chia bộ nhớ trong tiến trình. Mô hình lần hai thấy tin chữ và câu trả lời lần một, mỗi thứ đúng một lần, rồi tin mới. Không ngủ thật. Chạy trước mã. Kỳ vọng fail

- [ ] T067 [US4] Viết `test_fixed_sentence_reaches_owner` trong `tests/test_telegram_update_flow.py` (phụ thuộc T065). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Đẩy `turns.llm_turn._now` khi ca cần hết ngân sách. Không ngủ thật. Parametrize, mỗi `id` một ca: `empty_text`, `whitespace_text`, `max_tokens`, `refusal`, `model_error`, `budget_exhausted`, `three_rounds_exhausted`. Chủ bot nhận đúng một lần, đúng nguyên văn lần lượt `Mình chưa có câu trả lời cho tin này.`, `Mình chưa có câu trả lời cho tin này.`, `Câu trả lời bị cắt vì quá dài.`, `Mình không trả lời được tin này.`, `Chưa liên lạc được để trả lời lúc này.`, `Chưa liên lạc được để trả lời lúc này.`, `Chưa trả lời xong yêu cầu này.` Câu đã lưu bằng câu đó. So với chuỗi nguyên văn, không import hằng. Chạy trước mã. Kỳ vọng fail. Đây là US4.1 đến US4.4, US4.6, US4.7, FR-010, SC-004

- [ ] T068 [US4] Viết `test_composed_reply_wins_over_max_tokens_and_refusal` trong `tests/test_telegram_update_flow.py` (phụ thuộc T067). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Parametrize, mỗi `id` một ca: `max_tokens`, `refusal`. Lượt có một lần ghi kế hoạch thành công rồi dừng bằng lý do đó. Chủ bot nhận đúng bản ghép spec 012, không nhận câu cắt hay câu từ chối. Chạy trước mã. Kỳ vọng fail. Đây là US4.5, FR-011

- [ ] T069 [US3] Viết `test_one_turn_one_plan_one_reply_then_done` trong `tests/test_telegram_update_flow.py` (phụ thuộc T068). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Mô hình giả tạo một kế hoạch rồi trả một câu. Lần nhận đầu: một lượt, một kế hoạch, một nội dung gửi, bản ghi đã gửi xong. Cùng mã update tới lại: không lượt, không kế hoạch mới, không gửi. Chạy trước mã. Kỳ vọng fail. Đây là US3.1, US3.6, FR-006

- [ ] T070 [US3] Viết `test_resend_sends_saved_text_exactly` trong `tests/test_telegram_update_flow.py` (phụ thuộc T069). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Parametrize, mỗi `id` một ca: `d021_sentence` là `Chưa chắc thay đổi đã được lưu.`, `composed_multiline` là một bản ghép nhiều dòng của spec 012. Bản ghi có câu, chưa gửi xong. Cùng update tới: client nhận đúng nguyên văn, mô hình không bị gọi, không ghi kế hoạch mới. Chạy trước mã. Kỳ vọng fail. Đây là US3.3, US3.4, SC-003

- [ ] T071 [US3] Viết `test_different_update_ids_same_text_are_two_turns` trong `tests/test_telegram_update_flow.py` (phụ thuộc T070). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Hai mã update khác nhau, cùng chữ: hai lượt. Chạy trước mã. Kỳ vọng fail. Đây là US3.9, FR-006

- [ ] T072 [US3] Viết `test_receive_after_dead_turn_is_not_blocked_by_earlier_overlap` trong `tests/test_telegram_update_flow.py` (phụ thuộc T071). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Lần nhận chồng trong khoảng 90 giây thì Hoãn. Sau khi đồng hồ qua 90 giây, lần nhận sau gửi đúng một lần `Chưa chắc tin này đã được xử lý.` Chạy trước mã. Kỳ vọng fail. Đây là US3.8

- [ ] T073 [US7] Viết `test_redelivered_after_sent_fixed_sentence_sends_nothing` trong `tests/test_telegram_update_flow.py` (phụ thuộc T072). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Tin không phải chữ đã được trả `Mình chỉ đọc được tin chữ.` Cùng update tới lại: không gửi, không gọi mô hình. Chạy trước mã. Kỳ vọng fail. Đây là US7.2, SC-007

- [ ] T074 [US5] Viết `test_non_text_and_its_fixed_sentence_never_reach_model` trong `tests/test_telegram_update_flow.py` (phụ thuộc T073). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Tin không phải chữ rồi tin chữ: danh sách messages của lượt sau không có tin không phải chữ và không có câu cố định đó. Chạy trước mã. Kỳ vọng fail. Đây là US5.5

- [ ] T075 [US5] Viết `test_uncertain_pairs_enter_context_like_normal_pairs` trong `tests/test_telegram_update_flow.py` (phụ thuộc T074). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Parametrize, mỗi `id` một ca: `crashed_update`, `unexpected_exception`, `d021_sentence`. Lượt sau thấy tin chữ của chủ bot và câu `Chưa chắc tin này đã được xử lý.` hoặc `Chưa chắc thay đổi đã được lưu.` như một cặp thường. Chạy trước mã. Kỳ vọng fail. Đây là US5.7

- [ ] T076 [US6] Viết `test_long_reply_parts_reach_client_in_order` trong `tests/test_telegram_update_flow.py` (phụ thuộc T075). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Parametrize, mỗi `id` một ca: `exact_4096` là một phần, `emoji_2049` là 2049 emoji ngoài mặt phẳng cơ bản và hai phần. Mỗi phần từ 1 đến 4096 đơn vị UTF-16. Ghép theo thứ tự ra đúng chuỗi gốc. Không phần rỗng. Không cắt giữa một code point. Chạy trước mã. Kỳ vọng fail. Đây là US6.1, US6.2, FR-014, SC-006

- [ ] T077 [US6] Viết `test_long_reply_is_one_context_message` trong `tests/test_telegram_update_flow.py` (phụ thuộc T076). Gọi `handle_update` với mô hình giả, kho giả, client gửi giả ghi lại từng phần nhận. Đồng hồ kênh tiêm vào. Không ngủ thật. Sau câu hai phần, kho ngữ cảnh có đúng một hàng `assistant` bằng chuỗi gốc. Lượt sau thấy một tin của bot. Chạy trước mã. Kỳ vọng fail. Đây là US6.3

### Implementation

- [ ] T044 Tạo `src/api/telegram_update.py`, hàm `handle_update` là `async def` (phụ thuộc T032 đến T043, T061 đến T065, T067 đến T077, T016, T017, T021, T027, T030). Trả sau khi gửi xong hoặc sau khi đã quyết không gửi. Không trả 200 rồi xử lý nền. Không import `db`, `clients`, `config`. Hằng 90 giây lấy từ `src/core/telegram_channel.py`, không chép số. Ngữ cảnh lấy bằng `list_recent(chat_id, saved_at_gte = đồng hồ kênh trừ 24 giờ, limit = 20)`, qua `select_context`, rồi truyền vào `run_turn` làm `history`. Tin mới của lượt không nằm trong danh sách đó. Resend và SaveUncertain khi lần này ghi được câu: `append_once` hai vai trước khi gửi. Ghi lỗi thì Hoãn, không gửi. Câu `Mình chỉ đọc được tin chữ.` không ghi ngữ cảnh. Thua `save_reply_if_absent` thì không gửi câu của mình. `mark_sent` chỉ sau mọi phần. Đồng hồ là `Callable[[], datetime]` UTC có timezone. Không so `now()` của Postgres

**Checkpoint**: Ca luồng pass trên đồ giả, gồm ba hàm FR-022, FR-021, FR-020

---

## Phase 8: Route

**Purpose**: `POST /telegram`. Từ chối 401, Hoãn 503, Bỏ qua và xong 200, body rỗng. Đã duyệt

- [ ] T045 [P] [US2] Viết `test_reject_is_401_empty` trong `tests/test_telegram_route.py`. `POST /telegram`. Thiếu secret, sai secret, header không phải `str`, hoặc thiếu token: 401, body rỗng. Đếm đủ năm số 0 của SC-002: 0 lần đụng kho kế hoạch, 0 lần gọi mô hình, 0 lần gửi, 0 lần ghi ngữ cảnh, 0 lần ghi bản ghi update. Không ghi hai giá trị secret. So bằng `hmac.compare_digest`. Chạy trước `src/api/routes_telegram.py`. Kỳ vọng fail

- [ ] T046 [US2] Viết `test_skip_is_200_empty` trong `tests/test_telegram_route.py` (phụ thuộc T045). Không phải tin mới, không phải cuộc riêng, không phải chủ bot, thiếu danh tính chủ bot, hoặc body không đọc được: 200, body rỗng. Cùng năm số 0 của SC-002: 0 lần đụng kho kế hoạch, 0 lần gọi mô hình, 0 lần gửi, 0 lần ghi ngữ cảnh, 0 lần ghi bản ghi update. Chạy trước mã. Kỳ vọng fail

- [ ] T047 [US3] Viết `test_defer_is_503_done_is_200` trong `tests/test_telegram_route.py` (phụ thuộc T046). Hoãn là 503. Đã gửi xong là 200. Body rỗng cả hai. Chạy trước mã. Kỳ vọng fail

- [ ] T048 [US9] Viết `test_channel_log_has_no_secret_or_text` trong `tests/test_telegram_route.py` (phụ thuộc T045). Nhật ký kênh không có token, secret, chữ tin, câu trả lời. Lần từ chối không ghi secret đúng hay secret request đưa. Trên một ca đi qua kênh có gọi tool và gọi mô hình, khẳng định đúng tập khóa và đúng thứ tự của bảy khóa dòng tool và tám khóa dòng mô hình. Tám khóa lấy từ `_LOG_KEYS` và assert `list(logged) == list(_LOG_KEYS)` đang có trong `tests/test_llm_turn.py`. Bảy khóa tool không có tuple trong file đó. Lấy từ `_LOG_KEYS` đang có trong `tests/test_tool_router.py`. Không chép tay danh sách vào test mới. Không sửa `tests/test_tool_router.py`. Chạy trước mã. Kỳ vọng fail. Đây là SC-009

- [ ] T049 Trong `src/api/routes_telegram.py`, đọc body bằng kiểm kiểu trên dict, gọi `handle_update`, trả `Response` rỗng (phụ thuộc T044, T045 đến T048). Không model Pydantic cho body. Trong `src/app.py`, `include_router`. Import app không đọc env Telegram. Không sửa `tests/test_app_loads_plan_store.py`. File đó vẫn pass. Cấu hình lấy từ `request.scope["env"]`

**Checkpoint**: Bốn mã HTTP đã duyệt. App vẫn nạp `db.plan_store`

---

## Phase 9: Sáu mutation

**Purpose**: Sau khi test mới đang xanh. Mỗi task: sửa một chỗ, chạy đúng hàm, thấy đỏ, trả lại mã, dán output thật của pytest. Không để mutation ở lại

- [ ] T050 [US3] Mutation nhận nguyên tử, rồi trả lại `tests/fakes/memory_telegram_channel.py` (phụ thuộc T049). Trong đồ giả, `await` giữa lúc đọc chưa có hàng và lúc chèn. Hai task chồng đều chạy lượt. `test_claim_one_insert` trong `tests/test_telegram_channel_contract.py` phải đỏ. Trả lại. Dán output

- [ ] T051 [US3] Mutation lưu câu, rồi trả lại `tests/fakes/memory_telegram_channel.py` (phụ thuộc T050). Bỏ điều kiện chỉ ghi khi `reply is None`. Lượt chậm ghi đè `Chưa chắc tin này đã được xử lý.` và vẫn gửi. `test_save_reply_only_when_absent` phải đỏ. Trả lại. Dán output

- [ ] T052 [US5] Mutation biên ngữ cảnh, rồi trả lại `src/core/telegram_channel.py` (phụ thuộc T051). Đếm 21 tin trong 24 giờ, hoặc so `>` thay vì `>=` với đúng 24 giờ. `test_20_newest_messages_old_to_new` và `test_exactly_24h_kept_older_dropped` phải đỏ. Trả lại. Dán output

- [ ] T053 [US6] Mutation UTF-16, rồi trả lại `src/core/telegram_channel.py` (phụ thuộc T052). Tách bằng số code point. 2049 emoji ngoài mặt phẳng cơ bản thành một phần. `test_2049_non_bmp_emoji_is_two_parts` phải đỏ. Trả lại. Dán output

- [ ] T054 [US3] Mutation thứ tự lưu rồi gửi, rồi trả lại `src/api/telegram_update.py` (phụ thuộc T053). Gọi gửi khi `save_reply_if_absent` ném lỗi. `test_save_reply_failure_defers_then_uncertain` phải đỏ vì chờ 0 lần gửi, Hoãn, và đúng một kế hoạch. Trả lại. Dán output

- [ ] T055 [US5] Mutation gửi trước khi ghi ngữ cảnh, rồi trả lại `src/api/telegram_update.py` (phụ thuộc T054). Gọi gửi khi `append_once` ném lỗi. `test_context_write_failure_sends_nothing` phải đỏ vì chờ 0 lần gửi, Hoãn, một lượt, và câu giữ nguyên. Trả lại. Dán output

**Checkpoint**: Sáu chỗ đã trả lại. Cây làm việc không còn mutation

---

## Phase 10: Docs

**Purpose**: Đồng bộ docs sau code. Không push, không deploy, không `pywrangler`. Không sửa diagram

- [ ] T056 Thêm D-022 vào `docs/DECISIONS.md`, nguyên văn khối trong plan.md mục Docs (phụ thuộc T055). Đã duyệt. Số là D-022 vì D-021 đang là quyết định cuối. Nếu trước lúc ghi đã có số đó, dùng số kế tiếp, không đổi nội dung. Không sửa `docs/PRODUCT.md`. Không sửa `.specify/memory/constitution.md`. Nếu một câu constitution thành sai, dừng, không sửa

- [ ] T057 [P] Sửa `docs/ARCHITECTURE.md` (phụ thuộc T055). Sửa câu "Route và Telegram chưa gọi lượt này" và các mục module, luồng HTTP, logging cho khớp kênh. Không sửa `docs/PRODUCT.md`. Không sửa diagram trong `docs/architecture/`

- [ ] T058 [P] Sửa `docs/reviews/2026-11-01-repo-review.md` (phụ thuộc T055). L1-04 đóng. L1-13 chỉ đóng phần độ dài (tách 4096 đơn vị UTF-16). Dòng trống trong bản ghép và câu "Đã lưu" khi việc con không đổi vẫn mở. L1-12 đóng cho đường Telegram vì đường đó đi qua `run_turn` và `run_turn` đã truyền `remaining`. `execute_tool` vẫn mặc định `remaining=None` và mục đó vẫn mở cho F10

---

## Phase 11: Kiểm

- [ ] T059 Chạy `.\scripts\check.ps1 -AllowList specs/013-telegram-channel/allowed-files.txt` từ gốc repo (phụ thuộc T056, T057, T058). Dán output thật. Mã 0 là đạt. Không tắt cờ. Không sửa test để bỏ skip

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: T001 rồi T002. T002 chặn nếu `pylock.toml` đổi
- **Luật thuần và đồ giả**: T003 đến T011, T066, và T012 đến T015 viết trước T016 và T017. Chặn L1-04 không bị chặn bởi phase này về file, nhưng thứ tự đã chốt là làm phase này trước
- **L1-04**: T018, T019, T020, T060 trước T021. Dừng nếu assert của hàm có sẵn, ngoài ba chỗ đã duyệt, phải đổi
- **Supabase**: T022 trước T023 trước T024. Không đụng cloud
- **Client**: T025, T026 trước T027. T027 sau T001
- **Settings**: T028, T029 trước T030. T031 không đụng file `.env` thật
- **Điều phối**: Mọi test T032 đến T043, T061 đến T065, và T067 đến T077 trước T044
- **Route**: T045 đến T048 trước T049. T049 sau T044
- **Mutation**: Chỉ khi test mới đang xanh, sau T049. T050 đến T055 tuần tự vì có task sửa cùng file
- **Docs**: Sau T055. T057 và T058 song song được. T056 không song song với hai task kia về nội dung, nhưng khác file
- **Kiểm**: T059 sau docs

### User Story Dependencies

- **US1 (P1)**: T032, T044. Cần luật thuần, L1-04, cổng, client, settings
- **US2 (P1)**: T028 đến T031, T045, T046, T049
- **US3 (P1)**: T007 đến T017, T066, T022 đến T024, T033, T035, T041, T047, T050, T051, T054, T069 đến T072
- **US4 (P1)**: T018 đến T021, T060, T034, T042, T067, T068
- **US5 (P2)**: T005, T006, T014, T015, T036 đến T038, T052, T055, T061 đến T065, T074, T075
- **US6 (P2)**: T003, T004, T025 đến T027, T043, T053, T076, T077
- **US7 (P2)**: T039, T073
- **US8 (P1)**: T040. Không đổi `execute_tool`
- **US9 (P2)**: T048

### Within Each Phase

- Test viết và fail trước mã tương ứng
- Một ca một hàm. Parametrize có `id` rõ thì mỗi `id` là một ca. Ba mốc 90 giây là T007, T008, T009. Hằng 90 giây là T066. Ba hàm FR-022 là T036, T037, T038. FR-021 là T035. FR-020 là T034. FR-013 là T014. Refusal không có lần ghi là T060. Ngữ cảnh tới mô hình là T061 đến T065. Bốn câu US4 ra client là T067. Bản ghép thắng là T068. Một lượt một kế hoạch là T069. Gửi lại đúng câu đã lưu là T070. Hai mã update là T071. Lượt chết sau lần chồng là T072. Tin không phải chữ tới lại là T073. Tin sau không thấy câu đó là T074. Cặp chưa chắc là T075. Phần dài tới client là T076. Một tin ngữ cảnh là T077

### Parallel Opportunities

- T003, T005, T007, T012: bốn file test khác nhau
- T057 và T058: hai file docs khác nhau, sau T055

---

## Parallel Example: Luật thuần

```text
T003: tests/test_telegram_split.py
T005: tests/test_telegram_context_window.py
T007: tests/test_telegram_receive.py
T012: tests/test_telegram_channel_contract.py
```

Bốn file khác nhau. Trong mỗi file, hàm sau chờ hàm trước.

---

## Implementation Strategy

### MVP

Lát này chưa xong nếu chỉ có luật thuần. Đường dùng được là sau T049: tin chữ của chủ bot đi hết route. Không deploy ở task nào.

1. Phase 1
2. Phase 2 đến phase 8
3. Phase 9, sáu mutation, mỗi cái trả lại mã
4. Phase 10
5. T059

### Incremental Delivery

Luật thuần và đồ giả đứng trước. L1-04 không đụng kênh. Cổng Supabase không đụng route. Route là chỗ các story gặp nhau.

### Parallel Team Strategy

Một người. Không chia story trước khi T017 xong.

---

## Notes

- ID mới T060 đến T066 chèn vào giữa để các ID cũ không đổi.
- ID mới T067 đến T077 chèn giữa.
- Parametrize có `id` rõ thì mỗi `id` là một ca, đúng luật "mỗi ca một hàm".
- FR-005 và phần "0 thay đổi" của SC-009. Sáu thứ, file giữ nội dung, và allow list:
  - Lời hướng dẫn: `src/core/system_prompt.py` (`SYSTEM_PROMPT`). Ngoài allow list. T059 khóa. Assert nội dung đang có trong `tests/test_llm_turn.py`.
  - Số phiên bản lời hướng dẫn: cùng file (`PROMPT_VERSION`). Ngoài allow list. T059 khóa. Assert `PROMPT_VERSION == 2` đang có trong `tests/test_llm_turn.py`.
  - Bộ định nghĩa tool: `src/tools/tool_definitions.py` (`TOOL_DEFINITIONS`). Ngoài allow list. T059 khóa. Assert danh sách tool đang có trong `tests/test_tool_router.py`.
  - Số phiên bản bộ định nghĩa: cùng file (`DEFINITIONS_VERSION`). Ngoài allow list. T059 khóa. Assert `DEFINITIONS_VERSION == 2` đang có trong `tests/test_tool_router.py`.
  - Bộ eval và cách chấm: `evals/cases/v1.json`, `evals/datasets/`, `evals/score.py` (`SCORER_VERSION`), `evals/turn.py`. Ngoài allow list. T059 khóa. Không sửa `evals/` và `tests/test_eval_*`.
  - Mô hình: `src/clients/anthropic_model.py` (`_MODEL`). Ngoài allow list. T059 khóa. Assert `claude-haiku-5-5` đang có trong `tests/test_anthropic_model.py`.
  - `src/turns/llm_turn.py` nằm trong allow list nhưng chỉ import và truyền lời hướng dẫn cùng bộ định nghĩa. Không giữ sáu thứ. Không thêm T078.
- Không task gọi mô hình thật với danh sách mở đầu bằng `assistant`. Việc đó thuộc vòng chạy thật, không thuộc lát này
- Không task sửa `docs/PRODUCT.md`, `AGENTS.md`, `.specify/memory/constitution.md`, `wrangler.jsonc`, `evals/`, `tests/test_eval_*`
- `tests/test_app_loads_plan_store.py` không có trong allowed-files. Không sửa. T049 phải để file đó vẫn pass
- Dừng, không tự xử lý, khi: assert khác ba chỗ trong `tests/test_llm_turn.py` phải đổi; `uv lock` đổi `pylock.toml`; migration cần khác data-model.md; D-022 phải đổi nội dung; constitution thành sai; cần thư viện hoặc dịch vụ mới
- Sáu task mutation dán output pytest lúc đỏ, rồi output không còn trong diff
- T059 dán output thật của `check.ps1`
