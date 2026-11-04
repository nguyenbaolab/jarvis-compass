# Data model: Kênh Telegram, phần logic

Schema dưới đây là mô tả. File migration tạo ở bước implement, trong `supabase/migrations/`, mốc thời gian sau `20261103205500`. Bước plan không tạo file đó.

Quyền theo `supabase/migrations/20261025021100_plans_and_subtasks.sql`: bật RLS, `revoke all` từ `public`, `anon`, `authenticated`, `grant` cho `service_role`. Hàm mới không thừa hưởng quyền. Mỗi hàm: revoke rồi `grant execute` cho `service_role`. Không policy cho `anon` hay `authenticated`. Mọi thao tác nguyên tử là một hàm SQL gọi bằng RPC qua `src/db/client.py`.

Không gọi `now()` trong các hàm này. Không `default now()` trên các cột thời điểm. Giá trị thời điểm là tham số ứng dụng đưa xuống.

`Plan` và `Subtask` không đổi. Không thêm cột người dùng vào `plans` hay `subtasks`.

## TelegramUpdate

Một lần Telegram giao một việc.

| Cột | Kiểu | Luật |
|-----|------|------|
| `update_id` | `bigint` | Khóa chính. Mã update. |
| `started_at` | `timestamptz not null` | Mốc đồng hồ ứng dụng lúc claim. |
| `reply` | `text` | Null khi chưa có câu đã lưu. Không dùng chuỗi rỗng để nghĩa là chưa có câu. |
| `sent_at` | `timestamptz` | Null khi chưa xác nhận gửi cả câu. |

Không có cột từng phần đã gửi.

### Trạng thái nhìn từ các cột

- Chưa từng thấy: không có hàng. `claim` chèn hàng.
- Đã bắt đầu, chưa có câu: có hàng, `reply` null, `sent_at` null.
- Đã có câu, chưa gửi xong: `reply` không null, `sent_at` null.
- Đã gửi xong: `sent_at` không null.

`decide_receive` trong core đọc các cột này cùng đồng hồ. SQL không quyết định Hoãn hay gửi.

### claim_telegram_update(p_update_id bigint, p_started_at timestamptz)

Một giao dịch. `insert` vào `telegram_updates` với `on conflict (update_id) do nothing`. Rồi trong cùng hàm, đọc hàng đó và trả JSON: `update_id`, `started_at`, `reply`, `sent_at`, và `inserted` (true khi chính lần insert này thêm hàng).

Ứng dụng gọi một RPC. Không `select` ở Python rồi mới `insert`.

Hai lời gọi chồng cùng mã: một `inserted` true, lời kia false, cùng một `started_at` của lời chèn được. Lời `inserted` false không chạy lượt.

### save_telegram_reply(p_update_id bigint, p_reply text)

`update telegram_updates set reply = p_reply where update_id = p_update_id and reply is null`.

Trả true khi đúng một hàng đổi. Trả false khi không hàng nào đổi (chưa có hàng, hoặc đã có câu). Lời gọi nhận false không gửi câu của mình.

`p_reply` là câu đã chốt, không phải chuỗi rỗng. Hàm không kiểm chữ. Kênh không gọi hàm với chuỗi rỗng.

Lỗi RPC (mạng, kho từ chối) không phải "false". Kênh coi đó là lưu thất bại: không gửi, Hoãn (FR-021). Hàng vẫn chưa có câu nếu update không commit.

### mark_telegram_sent(p_update_id bigint, p_sent_at timestamptz)

`update ... set sent_at = p_sent_at where update_id = p_update_id and reply is not null and sent_at is null`.

Chỉ gọi sau khi mọi phần đã gửi xong. Gửi thất bại thì không gọi.

## TelegramContextMessage

Một tin ngữ cảnh. Câu trả lời dài là một hàng, bằng chuỗi gốc, không phải từng phần Telegram.

| Cột | Kiểu | Luật |
|-----|------|------|
| `update_id` | `bigint not null` | Khóa ngoài tới `telegram_updates.update_id`. |
| `role` | `text not null` | `check (role in ('user', 'assistant'))`. |
| `chat_id` | `bigint not null` | Cuộc trò chuyện riêng. |
| `body` | `text not null` | Chữ đã lưu. |
| `saved_at` | `timestamptz not null` | Mốc đồng hồ ứng dụng. |

Khóa chính `(update_id, role)`. Đó là khóa duy nhất của FR-013. Cùng update tới lại không thêm hàng thứ hai cho cùng vai.

Chỉ cuộc riêng của chủ bot được ghi. Không có `session_id`. Không có trạng thái đang chờ câu trả lời.

Tin không phải chữ và câu `Mình chỉ đọc được tin chữ.` không có hàng.

### append_telegram_context(p_update_id bigint, p_role text, p_chat_id bigint, p_body text, p_saved_at timestamptz)

`insert ... on conflict (update_id, role) do nothing`.

Một RPC một hàng. Mọi đường gửi một câu đã lưu gọi một lần cho `user` và một lần cho `assistant` trước khi gửi: lượt vừa xong, gửi lại câu đã lưu, và câu `Chưa chắc tin này đã được xử lý.` khi lần này ghi được câu. Lần thua khóa thì không đổi `body` đã có. RPC ném lỗi thì kênh không gửi, Hoãn, câu đã lưu giữ nguyên (FR-022). Câu `Mình chỉ đọc được tin chữ.` không gọi hàm này.

### list_telegram_context(p_chat_id bigint, p_saved_at_gte timestamptz, p_limit integer)

`select` các hàng `chat_id = p_chat_id and saved_at >= p_saved_at_gte`, `order by saved_at desc, role desc`, `limit p_limit`.

`p_saved_at_gte` do Python tính: đồng hồ tiêm trừ 24 giờ. So sánh dùng tham số, không dùng `now()` của Postgres. `p_limit` là 20. `role desc` chỉ để lần cắt ở cùng một mốc thời điểm có thứ tự ổn định. Python sắp các hàng đã lấy theo `(saved_at, user trước assistant)`. Tin đúng mốc `p_saved_at_gte` vẫn được chọn vì dùng `>=`. Cắt giữa một cặp vẫn có thể làm danh sách mở đầu bằng `assistant`, hoặc kết thúc bằng `user` rồi `run_turn` nối thêm tin `user`. Không thêm bộ lọc ở 013. Hai lượt cùng vai liền nhau được Messages API gộp thành một lượt. Danh sách mở đầu bằng `assistant` chưa kiểm. Vòng chạy thật gọi thật một lần để xem API trả gì.

## Quan hệ

- Một `TelegramUpdate` có không quá hai `TelegramContextMessage`, một `user` và một `assistant`.
- `TelegramUpdate` không phải một `Plan`. Lượt tạo kế hoạch qua `PlanStore` như hôm nay. Cổng update không gọi `add_plan`.

## Đồ giả

`tests/fakes/memory_telegram_channel.py` giữ dict trong một đối tượng. `claim` không `await` giữa kiểm và chèn, nên trên một event loop hai task không xen vào giữa. `save_reply_if_absent` chỉ gán khi `reply is None`. Contract test dùng chung các ca với bản Supabase.

Bản nhớ không phải trạng thái giữa hai request sản xuất. Test tạo đối tượng mới khi muốn chứng minh hai lần nhận không chia bộ nhớ kênh, và đưa cùng một đồ giả khi muốn chứng minh kho bền.
