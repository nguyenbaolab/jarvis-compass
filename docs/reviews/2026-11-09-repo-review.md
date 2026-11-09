# Quét repo 2026-11-09

review-base: 212c21a

Quét lần ba, chỉ đọc, ở `main` `212c21a` (sau merge 015, sau deploy `6c17f7f7`). Lần quét trước ở `2026-11-05-repo-review.md` (mốc `ed0c20c`) vẫn là nguồn trạng thái của các mục Q2; file này ghi phát hiện mới, phạm vi đã đọc và danh sách đã xét.

Hàng `Repo review` của `check.ps1` báo `due`: 22 file `src/` đổi từ `ed0c20c`, ngưỡng 15. Từ mốc đó có 32 commit và 125 file đổi (cả docs, specs, tests, evals). Hai nhóm thay đổi mã: F10 và các sửa nhỏ quanh nó (`core/morning.py`, `scheduler/morning.py`, `entry.py`, `log_line.py`, `telegram_update.py`, `routes_telegram.py`, `anthropic_model.py`, `config/settings.py`, `db/client.py`) và F17 mở rộng, spec 015 (`core/clock.py`, `core/plans.py`, `db/plan_store.py`, `db/models.py`, `tools/*`, `turns/llm_turn.py`, `core/system_prompt.py`, migration `20261109120000`).

## Phạm vi đã đọc

- Đọc từ `HEAD` bằng `git show`, không dùng `git diff` hay `git status` (để lại `.git/index.lock`). `git diff-tree --numstat` không kèm `--ignore-cr-at-eol` ra số dòng cả file trong máy ảo này (ví dụ `src/config/settings.py` 76 và 76, trong khi `git log --numstat` ra 1 và 1 và cả hai blob không có ký tự CR). Chưa rõ nguyên nhân. Số dòng ở đây lấy từ `--ignore-cr-at-eol` và `git log --numstat`.
- Đọc toàn bộ: migration `20261109120000_plan_dates_priority.sql`, `db/client.py`, `db/plan_store.py`, `tools/plan_tools.py`, `tools/tool_router.py`, `tools/tool_definitions.py`, `tools/saved_reply.py`, `tools/base.py`, `core/plans.py`, `core/clock.py`, `core/morning.py`, `scheduler/morning.py`, `entry.py`, `turns/llm_turn.py`, `api/telegram_update.py`, `core/system_prompt.py` (bản 7), `wrangler.jsonc`, `docs/DECISIONS.md` D-025 và D-026.
- Đọc phần đổi (diff): `api/routes_telegram.py`, `clients/anthropic_model.py`, `core/log_line.py`, `config/settings.py`, `tools/schemas.py`, `db/models.py`, `scripts/check.ps1`, `scripts/claude-b9-settings.json`, `pyproject.toml`, `pylock.toml`, `AGENTS.md`.
- So khớp: ba migration cũ (chỉ lấy dòng `revoke`, `grant`, `enable row level security`), `docs/ARCHITECTURE.md` (dòng về `PROMPT_VERSION`, catalog, §4, §6), tên test trong `tests/test_plan_store_contract.py` và `tests/test_supabase_plan_store.py`, `tests/test_telegram_update_flow.py` (nhóm `/next`).
- Quét chuỗi giống khóa bí mật (khóa Anthropic, `sb_secret`, JWT, token bot) trên toàn cây `HEAD` trừ `uv.lock`, `pylock.toml`: không có. `.gitignore` có `.env`, `.dev.vars`, `.venv-workers/`, `python_modules/`, `node_modules/`; file theo dõi giống file môi trường chỉ có `.env.example`.
- Không đọc lại: logic bộ chấm `evals/score.py` và các file eval khác (chỉ soát đọc biến môi trường, `redact` khóa trong `evals/result.py`, và `evals/results/` không chứa chuỗi giống khóa), test ngoài các tên ở trên, `specs/015-*`, `uv.lock`, `docs/architecture/*`, adapter `clients/anthropic_model.py` ngoài phần đổi. Chat không chạy test; số 748 test lấy từ handoff do Starter chạy `check.ps1`.
- Quan sát cloud dùng: bản xuất Observability sáu dòng `morning_digest` của 2026-11-08 và 2026-11-09 do Starter dán. Truy vấn quyền bảng và quyền hàm trên Supabase cloud do Starter chạy hai lần, trước và sau bản sửa Q3-01, kết quả ở mục Cập nhật. Chưa làm: tin 08:00 ngày 2026-11-10 (lần đầu của `6c17f7f7`).

## Cập nhật sau khi đọc log cloud (cùng ngày)

Sáu dòng `morning_digest`, hai ngày, mỗi ngày ba lần chạy cùng `update_id` (-20261108, -20261109). Lần 08/11 chạy bản `87aa5fbb`, lần 09/11 chạy bản `42eaa8b6`:

- Cron `0 5 * * *`: `local_time` 07:01, `outcome` `before_eight`.
- Cron `0 6 * * *`: `local_time` 08:00, `outcome` `sent`.
- Cron `0 7 * * *`: `local_time` 09:00, `outcome` `already_sent`; không có lần gửi thứ hai.

Chốt ba mục D-025 còn ghi "chưa quan sát": dòng `before_eight` của cron 05:00 UTC, dòng `already_sent` của cron 07:00 UTC, không có tin thứ hai lúc 09:00 Helsinki. Còn chưa quan sát: đường nhiều phần của `split_utf16` trên cloud (log không có trường số phần), đường mùa hè (UTC+3, đổi giờ 2027-03-28), và tin sáng của bản `6c17f7f7`.

Truy vấn quyền trên Supabase cloud (câu SQL ở mục "Cách kiểm Q3-01"):

- Cả năm bảng `public` có `rls` true.
- Bốn bảng cũ (`plans`, `subtasks`, `telegram_updates`, `telegram_context_messages`): `anon_select`, `anon_truncate`, `auth_select` đều false.
- `subtask_date_moves`: `anon_truncate` true; `anon_select` và `auth_select` false.
- `service_truncate` true ở cả năm bảng.
- Hàm `public.subtask_date_moves_block_change`: `anon_exec` true.

Hệ quả: Q3-01 được xác nhận một phần (xem hàng Q3-01), Q3-02 được xác nhận.

Sau bản sửa (cùng ngày): migration `20261109190000_date_moves_revoke.sql` (commit `a5f571f`, merge `ddee776`) được áp lên cloud bằng `db push --linked`; dry-run liệt kê đúng một migration. Chạy lại hai câu SQL:

- Cả năm bảng vẫn `rls` true; `anon_select`, `anon_truncate`, `auth_select` false ở cả năm bảng, gồm `subtask_date_moves`.
- `service_truncate`: false ở `subtask_date_moves`, true ở bốn bảng cũ.
- Hàm `public.subtask_date_moves_block_change`: `anon_exec` false.

Kết quả khớp lần chạy trên DB local sau `db reset`. Truy vấn vẫn chỉ hỏi `SELECT` và `TRUNCATE` của `anon`: các quyền còn lại (`INSERT`, `UPDATE`, `DELETE`, `REFERENCES`, `TRIGGER`) được thu bởi `revoke all` trong migration, nhưng chưa có truy vấn xác nhận từng quyền.

## Phát hiện

Mức: chặn, nên sửa, ghi nhận. Trạng thái: mở, đã sửa ở (nhánh hoặc commit), đóng (đã kiểm, không có vấn đề).

| ID | Mức | Chỗ | Tóm tắt | Trạng thái |
|---|---|---|---|---|
| Q3-01 | nên sửa | `supabase/migrations/20261109120000_plan_dates_priority.sql` dòng 29 đến 46 | Bảng `subtask_date_moves` bật RLS và cấp quyền cho `service_role`, nhưng không có `revoke all on table ... from public, anon, authenticated`. Bốn bảng cũ (`plans`, `subtasks`, `telegram_updates`, `telegram_context_messages`) đều có dòng này. Hàm trigger `public.subtask_date_moves_block_change` nằm ở schema `public` và không bị thu quyền thực thi, trong khi trigger của lần đầu (`internal.subtasks_keep_clocks`) nằm ở `internal` và có `revoke`. Đã kiểm trên cloud 2026-11-09: `anon` có quyền `TRUNCATE` trên `subtask_date_moves` (bốn bảng cũ không có) và `anon_exec` của hàm trigger là true. `anon_select` và `auth_select` của bảng là false, nên mặc định của dự án không cấp mọi quyền như suy đoán ban đầu; truy vấn chỉ hỏi `SELECT` và `TRUNCATE` của `anon`, nên chưa biết `anon` và `authenticated` còn quyền nào khác (`INSERT`, `UPDATE`, `DELETE`, `REFERENCES`, `TRIGGER`). Không có đường khai thác qua PostgREST: không có endpoint `TRUNCATE`, RLS bật và không có policy. Vậy đây là chỗ lệch mẫu và thiếu một lớp bảo vệ, chưa phải lỗ hổng đã dùng được. Chưa có test nào kiểm quyền hay RLS của bất kỳ bảng nào. Hướng sửa ở mục dưới bảng | đóng: sửa ở `a5f571f` (merge `ddee776`), áp lên cloud và kiểm lại 2026-11-09 |
| Q3-02 | ghi nhận | cùng migration dòng 31 và 43 đến 46; D-026 mục 3 | "Chỉ thêm" dựa vào một cơ chế: trigger theo hàng `before update or delete`. `service_role` được cấp UPDATE và DELETE (test dựa vào đó để thấy trigger chặn); không có trigger `before truncate`. Ai giữ khóa `service_role` (secret của Worker) xóa được lịch sử bằng `TRUNCATE` (đã quan sát: `service_truncate` true ở cả năm bảng). Với một chủ bot duy nhất thì chấp nhận được; D-026 nói trigger chặn sửa và xóa mà không nêu `TRUNCATE`. Đã xử lý cùng bản sửa Q3-01: `service_role` mất `TRUNCATE` trên bảng này (`service_truncate` false trên cloud) và D-026 mục 3 nêu điều đó; `UPDATE` và `DELETE` của `service_role` giữ nguyên, trigger chặn | đóng (cùng bản sửa Q3-01) |
| Q3-03 | ghi nhận | `api/telegram_update.py` nhánh `/next` (dòng 271 đến 284), `core/telegram_channel.py` `decide_receive` | Lỗi đọc kế hoạch sau khi đã claim ghi `defer` với `reason` `store_unavailable`, cùng mã với lỗi trước claim, nhưng hàng claim còn lại không có câu. Telegram gửi lại thì gặp `in_flight` (503) tới 90 giây, sau đó `decide_receive` chọn `SaveUncertain` và chủ bot nhận "Chưa chắc tin này đã được xử lý." cho một lệnh chỉ đọc chưa chạy xong. Suy ra từ mã và lịch gửi lại của Q2-18 (lần nhận lại đến +231 giây); chưa chạy trên cloud. Test `test_next_plan_read_error_defers_without_the_uncertain_sentence` chốt nửa đầu (không gửi câu chưa chắc ngay, hàng chưa có câu) và không chạy lần gửi lại. Cùng dạng với nhánh `context_failed` có từ trước | mở (ghi nhận) |
| Q3-04 | ghi nhận | `tools/plan_tools.py` (`get_plans`, `reschedule_subtasks`), `tools/schemas.py`, `db/client.py` (`list_plans`) | `get_plans` không giới hạn: trả mọi kế hoạch, kể cả kế hoạch đã xong hết việc; `list_plans` không phân trang; `reschedule_subtasks` đọc toàn bộ kế hoạch mỗi khi hạn của kế hoạch đổi. JSON của tool luôn mang `priority`, `scheduled_on`, `effort` kể cả khi null (`model_dump_json` không bỏ null). Kích thước kết quả tool tăng theo số kế hoạch, cộng vào mức token vào đã gấp khoảng 2,3 lần p3-d2 (handoff 016). Chưa đo ở số kế hoạch nào thì thành vấn đề | mở (ghi nhận; liên quan việc nhỏ (iv) của handoff 016) |
| Q3-05 | ghi nhận | `tools/plan_tools.py` `_apply_changes`, `reschedule_subtasks` | Ba chỗ chỉ đúng nhờ router: (a) khóa `scheduled_on` vắng trong một thay đổi bị đọc là null, tức bỏ ngày, và bỏ ngày không sinh dòng lịch sử; schema bắt buộc khóa này nên router chặn trước; (b) phần tử không phải object ném `_DUPLICATE_CHANGE`, sai câu; router chặn bằng kiểm kiểu từ trước; (c) `PlanDomainError` ném ngoài `_domain_as_tool_error` ở dòng 443 và 448, được đổi thành lỗi tool nhờ `_run` của router. Gọi trực tiếp (test, eval) mới thấy | mở (ghi nhận) |
| Q3-06 | ghi nhận | `core/plans.py` `date_moves` | Không còn đường production nào gọi hàm này; chỉ đồ giả `tests/fakes/memory_plan_store.py` gọi (eval chỉ đọc danh sách `date_moves` của đồ giả đó). Hàm lặp luật SQL "chỉ ngày sang ngày" mà D-026 mục 3 giao cho `replace_plan`. Lệch được chặn bởi `test_plan_store_contract.py` chạy cùng ca trên cả hai kho (ngày sang ngày, trống sang ngày, ngày sang trống, cùng ngày) | mở (ghi nhận) |
| Q3-07 | ghi nhận | `docs/DECISIONS.md` D-025, `docs/ARCHITECTURE.md` §6 | (a) D-025 còn ghi "chưa quan sát" ba mục đã quan sát (mục Cập nhật), và còn ghi chưa đo `Worker Startup Time` sau `tzdata` (handoff 016 có số: 2.429 ms, upload 15.855 KiB). (b) D-025 nói `tzdata` "ghim trong `pyproject.toml`", nhưng `pyproject.toml` chỉ liệt kê `tzdata` không kèm số bản; số bản 2026.6 ghim ở `pylock.toml` (và `uv.lock`). (c) ARCHITECTURE §6 nói dòng `morning_digest` luôn có bảy khóa. Mã đúng (bảy khóa, null vẫn ghi); bản xuất Observability chỉ có năm khóa, thiếu `error_type` và `error_code` (suy ra: Observability không hiện giá trị null), nên đọc log thì khóa vắng nghĩa là null | mở (docs) |
| Q3-08 | ghi nhận | `core/system_prompt.py` bản 7 | Ví dụ trong lời hướng dẫn dùng ngày cụ thể gần ngày thật (2026-11-16, 11/11, 13/11, 14/11). Câu "chỉ đặt priority hoặc effort khi người dùng nói rõ mức hoặc nhờ ước lượng" rộng hơn mô tả tool ("chỉ đặt khi người dùng nói rõ"). Chưa có bằng chứng hai điểm này gây lỗi: p7 có tự đặt ưu tiên 1 trên 30 lần tạo, nguyên nhân chưa tách | mở (ghi nhận) |

### Cách kiểm Q3-01

Chạy trong SQL Editor của Supabase cloud (chỉ đọc):

```sql
select c.relname,
       c.relrowsecurity as rls,
       has_table_privilege('anon', c.oid, 'SELECT') as anon_select,
       has_table_privilege('anon', c.oid, 'TRUNCATE') as anon_truncate,
       has_table_privilege('authenticated', c.oid, 'SELECT') as auth_select,
       has_table_privilege('service_role', c.oid, 'TRUNCATE') as service_truncate
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by c.relname;
```

Kết quả 2026-11-09 ở mục Cập nhật. Câu thứ hai, cho hàm trigger:

```sql
select p.proname, has_function_privilege('anon', p.oid, 'EXECUTE') as anon_exec
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname = 'subtask_date_moves_block_change';
```

Hướng sửa (đã làm ở `a5f571f`, migration `20261109190000_date_moves_revoke.sql`): một migration mới, đúng mẫu của bốn bảng cũ, thu quyền bảng và quyền hàm của `public`, `anon`, `authenticated`: `revoke all on table public.subtask_date_moves from public, anon, authenticated` và `revoke all on function public.subtask_date_moves_block_change() from public, anon, authenticated`. Thu quyền thực thi không làm trigger ngừng chạy: quyền `EXECUTE` của hàm trigger chỉ kiểm lúc tạo trigger, không kiểm lúc kích hoạt (hàm trigger `internal.subtasks_keep_clocks` của migration đầu đã bị thu quyền như vậy mà vẫn chạy). Cho Q3-02: `revoke truncate on table public.subtask_date_moves from service_role`; không đụng UPDATE và DELETE của `service_role` vì test dựa vào chúng để thấy trigger chặn. Kiểm sau khi áp: chạy lại hai câu trên; `anon_truncate` và `anon_exec` phải false, và `service_truncate` của bảng này cũng false. Kết quả trên cloud sau khi áp: cả ba false (mục Cập nhật). Đây là thay đổi migration nên theo AGENTS.md phải qua chat trước.

## Mục mở của lần quét trước, kiểm lại

- Mã tại các chỗ đó không đổi, vẫn mở: Q2-03 (`_deliver` gửi lại mọi phần), Q2-09 (`except Exception` của `run_turn` không ghi `error_type`), Q2-10 (hai chỗ cùng chặn `bool` cho `update_id`: `channel_update_id` và `_inbound`), Q2-18 (`DEAD_AFTER` 90 giây; đường digest dùng `decide_digest` nên không đi qua đây), Q2-19 (`AnthropicModel` vẫn chỉ giữ tên lớp; `anthropic_model.py` chỉ thêm bộ lọc cảnh báo), L1-05 (`update_subtask.status` vẫn `{"type": "string"}` không enum), L1-06 (`plan_from_row` vẫn ném `PlanDomainError` với trạng thái lạ).
- Q2-04 (lịch sử mở đầu bằng `assistant`): đóng một phần. D-025 mục 7 đo 2026-11-07 với `claude-haiku-5-5`: lịch sử bắt đầu bằng `assistant` và hai `assistant` liền nhau đều HTTP 200, mỗi dạng một lần. Đổi model thì đo lại.
- Q2-11 (Worker Python 3.14, test 3.13): `requires-python` và `wrangler.jsonc` `compatibility_date` không đổi; vẫn chưa chạy test dưới 3.14.
- Q2-01, Q2-06, Q2-07, Q2-12, Q2-15, Q2-16: các sửa còn nguyên trong mã (`reason` trên mọi dòng kênh, ba mẫu deny `--op`, `--no-ind`, `--no-exc`, hàng `Update imports` và `Env reads` quét cả `src`, `error_code_of`, bộ lọc cảnh báo Emscripten). Q2-12: `replace_plan` mới vẫn trả `boolean`.
- Không kiểm lại (file không nằm trong phạm vi lần này): Q2-13, Q2-17, L1-09 đến L1-13, L2-01, L2-07 đến L2-11, L3-04, L3-09.

## Đã xét, không có vấn đề (ở mốc 212c21a)

File nào không đổi từ mốc thì lần sau không cần đọc lại cho các mục này.

- `replace_plan` mới: ba nhánh của ngày và sức (việc mới, việc đã có và khóa vắng, việc đã có và khóa có mặt) khớp D-026 mục 4; dòng lịch sử chỉ chèn khi cả ngày cũ và mới khác null và khác nhau, `moved_at` null thì ném `moved_at_required`; khóa `version` khóa dòng `plans` trước khi xóa và upsert việc con, nên hai lần ghi chồng nhau chỉ một lần thắng; thứ tự xóa việc vắng rồi cập nhật rồi chèn; `add_plan` trả jsonb có thêm khóa mới, Worker cũ bỏ qua khóa lạ (`PlanRow` và `SubtaskRow` ở bản `ed0c20c` là `BaseModel` không cấu hình `extra`, mặc định bỏ qua khóa thừa).
- Tương thích ngược: `drop function` chữ ký cũ rồi tạo lại với tham số mặc định null; test `test_supabase_plan_store.py` gọi RPC trực tiếp với tham số kiểu cũ.
- `db/client.py` ánh xạ ba thông điệp `plan_missing`, `plan_version_conflict`, `moved_at_required`; `moved_at.isoformat()` mang múi giờ vì mốc lượt từ `_utc_now()` hoặc `clock()` có múi giờ.
- `plan_store.replace` luôn gửi đủ khóa `scheduled_on`, `effort`, `priority` từ bản đọc cùng `version`, nên luật "khóa vắng thì giữ" chỉ để Worker cũ sống chung, đúng ý D-026.
- `reschedule_subtasks`: chỉ kiểm trùng khi hạn kế hoạch đổi; `deadline_clash` bỏ qua chính kế hoạch đang dời; việc xong, bỏ qua không tính vào hạn; lần gọi đầu thấy trùng không ghi và đặt cờ; lần gọi có `confirm` trong cùng lượt sau khi báo trùng bị từ chối. Khớp D-026 mục 6, gồm cả điều D-026 đã nói: cờ không chứng minh chủ bot đồng ý.
- `tool_router`: chỉ chuyển chuỗi JSON thành mảng cho thuộc tính cấp cao nhất kiểu mảng, chỉ khi chuỗi bắt đầu bằng `[` và parse ra list; khóa lạ bị chặn khi `additionalProperties` là false; input đã chuyển được ghi vào log. Chuyển tại chỗ trên chính dict `tool_input`, nên (suy ra, chưa đọc adapter) các vòng sau gửi lại cho mô hình bản mảng thay vì chuỗi gốc; vô hại.
- `core/clock.py` và `scheduler/morning.py`: `ZoneInfo` dựng lười, `helsinki_clock` từ chối mốc không có múi giờ, cổng 08:00 ở code. Phép tính D-025 mục 4 đúng cho cả hai mùa (đổi giờ 01:00 UTC, trước cả ba cron). Log 08/11 và 09/11 khớp.
- `llm_turn`: `instant` bắt buộc, một mốc cho cả lượt, khối ngày ghép sau hằng lời hướng dẫn nên không phá phần đầu cố định của prompt; ngân sách 20 giây và tối đa ba vòng tool không đổi.
- `routes_telegram`: thứ tự kiểm secret, token, body, người gửi không đổi; mọi đường từ chối và bỏ qua có dòng `reason`; không log secret, token hay chữ tin. (Tool vẫn log `input` đầy đủ, gồm tiêu đề và ghi chú kế hoạch; theo thiết kế, nằm trong tài khoản Cloudflare của chủ bot.)
- `check.ps1` (hàng `Update imports`, `Env reads` cả `src`) và `claude-b9-settings.json` (sáu mẫu deny mới) khớp mô tả trong `AGENTS.md`.
- `docs/ARCHITECTURE.md` dòng về `PROMPT_VERSION` 7, catalog chín tool `DEFINITIONS_VERSION` 3, §4 ba cron: khớp mã. `docs/DECISIONS.md` D-026 mục 3, 4, 6: khớp mã và SQL.
- Đã biết, không tính phát hiện mới: stub `src/scheduler/checkin.py` (một dòng docstring), `docs/architecture/architecture.html/.json` chưa cập nhật (D-016).

## Lần quét sau

Khi nào: `check.ps1` báo hàng `Repo review | due` (từ 15 file `src/` đổi so với `review-base`), trước deploy để dùng hằng ngày, trước khi viết case study. Cách làm: như mục "Lần quét sau" của `2026-11-01-repo-review.md`, với `review-base` của file này. Các thay đổi sau `212c21a` (gồm commit ghi file này và migration `20261109190000`) tính vào lần quét sau.
