# Research: Kênh Telegram, phần logic

Các mục 4, 8, 9, 10, 11, 12, và 13 đã duyệt. Plan coi chúng là đã chốt.

## 1. Chỗ điều phối

**Decision:** `src/api/telegram_update.py`, hàm `handle_update`. Route ở `src/api/routes_telegram.py` chỉ đọc HTTP và map kết quả. Không thêm gói mới.

**Rationale:** `src/turns` không được import `clients`, `db`, `config`, hay `anthropic`. `src/core` chỉ luật thuần và Protocol, không gọi `run_turn`. `src/tools` không import `db`. Hàm điều phối nhận cổng đã dựng, nên bản thân nó không import `db`, `clients`, hay `config`. `src/app.py` là composition root, đã nạp `api.routes_telegram`. Để hàm trong `src/api` thì không tạo ranh giới gói mới.

**Alternatives considered:** Đặt trong `src/turns` (vỡ luật import). Đặt trong `src/core` (core phải gọi lượt và biết Telegram). Tạo `src/channels/` (thêm gói, D-016 bắt diagram ở commit riêng dù vẫn không sửa diagram trong tính năng này). Nhét hết vào file route (route không còn mỏng, thứ tự kiểm khó test không cần HTTP).

## 2. Một cổng ngữ cảnh

**Decision:** Một Protocol `ContextStore` với `append_once` và `list_recent`. Cổng update là Protocol khác. Cổng gửi là Protocol thứ ba. Cả ba đứng cạnh `PlanStore`, file mới `src/core/telegram_channel.py`. Không sửa `PlanStore`.

**Rationale:** FR-013 là một khóa duy nhất theo mã update và vai. Tách cổng đọc và cổng ghi làm hai kiểu cùng giữ một khóa, không thêm bất biến. Cổng update và cổng ngữ cảnh khác bảng và khác luật, nên không gộp.

**Alternatives considered:** Hai cổng ngữ cảnh (đọc, ghi). Một cổng cho cả update và ngữ cảnh (claim và hội thoại dính một kiểu, test contract phình).

## 3. Đồng hồ

**Decision:** Kênh nhận `Callable[[], datetime]` UTC có timezone. Mốc ghi xuống kho là giá trị hàm đó trả, tham số của RPC. Hàm SQL của lát này không gọi `now()` và cột không default `now()`. So tuổi 24 giờ và khoảng lượt đã chết trong Python, trên các mốc đó. Đồng hồ `time.monotonic` của `run_turn` chỉ tính 20 giây bên trong một lượt.

**Rationale:** Hai request không chia một mốc monotonic. Gọi `now()` trong SQL rồi so với mốc ứng dụng là trộn hai đồng hồ. Test đẩy callable, không ngủ.

**Alternatives considered:** `timestamptz default now()` rồi so trong SQL (trộn đồng hồ, test không đẩy được mà không ngủ). Chỉ dùng monotonic và ghi vào Postgres (mốc vô nghĩa ở request sau và ở isolate khác).

## 4. Khoảng lượt đã chết

**Decision (đã duyệt):** 90 giây. Tạm thời, đo lại ở vòng chạy thật. Hằng số đặt một chỗ. Đúng 90 giây vẫn là Hoãn. Qua 90 giây là SaveUncertain. Test ở hai phía và đúng 90 giây.

**Rationale:** Cửa sổ "chưa có câu" là bốn bước: claim, đọc ngữ cảnh, lượt, lưu câu. Gửi đứng sau khi câu đã lưu, nên không nằm trong cửa sổ đó. Trong `src/db/client.py`, `_HTTP_CEILING_SECONDS = 20.0` được đưa vào `httpx.Timeout(...)`. Comment ngay trên hằng ghi trần từng pha HTTP, không bảo đảm FR-001. Đó là trần mỗi pha (connect, read, write, pool), không phải tổng một lời gọi. Phép đếm của khoảng này lấy mỗi bước trong bốn bước là một lần chạm trần 20 giây: 4 × 20 = 80 giây, lề 10 giây, thành 90.

**Alternatives considered:** 45 giây. Câu chưa chắc tới sớm hơn, nhưng bốn bước mỗi bước chạm trần 20 giây đã là 80 giây, nên 45 giây tuyên bố chết nhầm. 180 giây. Khó chết nhầm hơn, và nếu Telegram bỏ cuộc trước 180 giây thì chủ bot không nhận câu nào. Lịch gửi lại chưa đo. Spec giao rủi ro đó cho vòng chạy thật.

## 5. Nhận nguyên tử và lưu câu

**Decision:** `claim` là một hàm SQL: `insert ... on conflict (update_id) do nothing` rồi trả hàng trong cùng hàm. Ứng dụng không đọc rồi mới ghi. `save_reply_if_absent` là `update ... where update_id = $1 and reply is null`. Không hàng nào đổi thì hàm trả false và lần đó không gửi câu của mình.

**Rationale:** Hai lần nhận chồng không được cùng chạy lượt. Lượt chậm hơn khoảng lượt đã chết có thể thua lần nhận sau đã ghi `Chưa chắc tin này đã được xử lý.` Nếu lần chậm vẫn gửi, chủ bot nhận hai nội dung. So sánh-và-đặt giữ một câu.

**Alternatives considered:** `select` rồi `insert` trong Python (thua cuộc đua). Khóa lời khuyên trong bộ nhớ Worker (mất khi request khác ở isolate khác, trái nguyên tắc II). Ghi đè câu đã có (hai nội dung, hoặc câu chưa chắc đè câu thật).

## 6. Đếm 4096

**Decision:** `split_utf16` trong core, đếm đơn vị UTF-16, không cắt giữa một code point. Người gửi không tự tách.

**Rationale:** Đếm code point có thể vượt trần nếu Telegram đếm UTF-16. Phần bị từ chối thì update kẹt ở trạng thái đã có câu chưa gửi. Một emoji ngoài mặt phẳng cơ bản là hai đơn vị. Tách bằng `len` của Python sai ca 2049 emoji.

**Alternatives considered:** Cắt 4000 ký tự như spike (sai trần, và spike không được chép). Cắt theo code point (có thể vượt trần).

## 7. L1-04 nằm trong lượt

**Decision:** Ba hằng cạnh `_MODEL_ERROR`. Đổi `_normal_text` và `_finish`. `effects` không rỗng vẫn `compose`. Chữ ký và kiểu trả về `str` không đổi.

**Rationale:** Chuỗi trả về là chỗ duy nhất còn lý do dừng. Kênh không đọc `stop_reason`. Sửa ở kênh sẽ không cứu đường gọi `run_turn` khác, và eval gọi thẳng lượt. Ba assert đã duyệt khóa đúng hành vi cũ. Các assert bản ghép và `_MODEL_ERROR` cho lỗi mô hình, quá hạn, thiếu khóa không thuộc ba câu mới.

**Alternatives considered:** Để kênh đoán câu rỗng (eval và test lượt vẫn thấy chuỗi rỗng). Đổi kiểu trả về để mang `stop_reason` (trái ràng buộc chữ ký).

## 8. HTTP

**Decision (đã duyệt):** Từ chối 401. Hoãn 503. Bỏ qua và xong đều 200. Body rỗng.

**Rationale:** Telegram gửi lại khi webhook không trả 2xx (D-018). Hoãn phải không phải 2xx thì lần gửi lại mới chạy. Từ chối khác Hoãn nên khác mã. Bỏ qua phải là 2xx thì Telegram không gửi lại chỉ vì lần này bị bỏ. Body rỗng để response không chứa secret, chữ tin, hay câu trả lời. Spike trả 503 khi thiếu secret và 401 khi sai secret. Spec gộp cả hai thành Từ chối, nên không lấy bảng mã của spike.

**Alternatives considered:** Từ chối cũng 200 (Telegram không gửi lại request giả, nhưng Từ chối và Bỏ qua cùng mã, trái đề xuất hai mã khác nhau). 400 cho Từ chối và 409 cho Hoãn (cùng phân biệt được. 503 nói "chưa xong" sát nghĩa Hoãn hơn 409).

## 9. Lỗi gửi vĩnh viễn

**Decision (đã duyệt):** Mọi lần gửi thất bại, kể cả HTTP 200 với `ok` không phải true, đều Hoãn. Câu giữ trong bản ghi. Không thêm nhánh dừng gửi. Update lặp ở trạng thái đã có câu chưa gửi cho tới khi Telegram bỏ cuộc.

**Rationale:** Spec không tách lỗi vĩnh viễn và lỗi tạm. Tự thêm nhánh "dừng gửi" là đổi spec. Chấp nhận vòng lặp là đúng chữ spec hiện tại.

**Alternatives considered:** Mã 403 của Telegram, hoặc `ok: false` với mô tả chặn bot, thì `mark_sent` kèm một cờ "bỏ" và lần sau không gửi. Hết vòng lặp, nhưng chủ bot không nhận câu báo, và phải thêm trạng thái spec chưa có.

## 10. Kích thước ngữ cảnh

**Decision (đã duyệt):** Không thêm trần tổng ký tự. Trần spec là 20 tin và 4096 đơn vị mỗi tin khi gửi. 20 tin đã lưu, mỗi tin 4096 đơn vị UTF-16, là 81920 đơn vị, cộng tin mới. Với chữ trong mặt phẳng cơ bản đó là khoảng 80 nghìn ký tự, cỡ vài trăm KiB, dưới trần bộ nhớ 128 MiB của một isolate (D-018).

**Rationale:** Trần 128 MiB không bị 20 tin đẩy tới. Rủi ro còn lại là số token và 20 giây của lượt, chưa đo. Thêm trần tổng là đổi spec.

**Alternatives considered:** Trần tổng 32000 ký tự trước khi gọi mô hình (cắt hội thoại spec bảo phải đưa). Đo token ở vòng chạy thật rồi mới đặt trần.

## 11. Tin bot đứng đầu danh sách messages

**Decision (đã duyệt):** Không thêm bộ lọc ở 013. `select_context` có thể trả một danh sách mở đầu bằng câu của bot, khi cắt 24 giờ hoặc cắt 20 tin giữa một cặp. Cùng một nhát cắt có thể bỏ câu bot và giữ tin chủ bot ở cuối danh sách. `run_turn` nối tin mới của chủ bot vào sau, nên hai tin `user` đứng liền. `_messages` trong `src/clients/anthropic_model.py` chuyển từng `TextMessage` thành `{"role", "content"}` theo thứ tự, không thêm và không xóa phần tử.

Tài liệu Messages API, tham số `messages` ([platform.claude.com/docs/en/api/messages](https://platform.claude.com/docs/en/api/messages)): các lượt `user` hoặc `assistant` liền nhau được gộp thành một lượt. Câu "hai `user` liền nhau bị từ chối" là sai. Danh sách mở đầu bằng `assistant` có bị từ chối không: tài liệu không nói, chưa kiểm. Vòng chạy thật gọi thật một lần với danh sách mở đầu bằng `assistant` để xem API trả gì.

**Rationale:** Tự bỏ tin bot đứng đầu, hoặc tựa thêm một tin user giả, đổi ngữ cảnh spec đã chốt. Lát này không thêm bộ lọc.

**Alternatives considered:** Bỏ các tin đầu cho tới khi gặp tin `user` (mất câu bot, đổi FR-012). Chèn một tin user rỗng (đổi nội dung mô hình thấy, và chữ rỗng trái luật tin). Để lỗi mô hình thành `Chưa liên lạc được để trả lời lúc này.` (chủ bot mất ngữ cảnh mà không thấy vì sao).

## 12. Handler và request

**Decision (đã duyệt):** Route là `async def`. Kết quả HTTP trả sau khi gửi xong hoặc sau khi đã quyết không gửi. Không có tác vụ nền sau response. "Đồng bộ" ở đây là vòng đời request, không phải `def` chặn vòng sự kiện. D-012 bắt cổng lưu là async. httpx của client cũng async.

**Rationale:** `def` đồng bộ gọi Postgres hay Telegram sẽ chặn Worker. Trả 200 rồi xử lý nền thuộc vòng chạy thật, và làm Hoãn không còn nghĩa vì Telegram đã được bảo là xong.

**Alternatives considered:** `def` đồng bộ và client HTTP đồng bộ (spike dùng SDK đồng bộ, không đưa vào lát này). Trả 200 ngay (trái Hoãn và trái "trả kết quả sau khi gửi xong").

## 13. httpx

**Decision (đã duyệt):** Chuyển `httpx` từ `[dependency-groups].dev` sang `[project].dependencies`. Không thêm gói. Không thêm SDK Telegram. Đây là chuyển nhóm đã duyệt, không cần dừng.

**Rationale:** `src/db/client.py` đã import `httpx` để đưa `AsyncClient` vào `AsyncPostgrestClient`. Client Telegram cũng cần `httpx`. Để ở nhóm dev thì môi trường chỉ cài dependency sản xuất không có gói mà `src/` import.

**Alternatives considered:** Gọi Telegram bằng `urllib` trong thư viện chuẩn (thêm một đường HTTP, trong khi PostgREST đã dùng httpx). Thêm SDK Telegram (trái ràng buộc một thay đổi thư viện).

## 14. Spike

**Decision:** Chỉ lấy ba sự kiện đã quan sát ở `spike/telegram-haiku:src/api/routes_spike.py`: tên header `X-Telegram-Bot-Api-Secret-Token`, `hmac.compare_digest`, và `request.scope["env"]`. Không merge, không cherry-pick, không chép hàm.

**Rationale:** Spike dùng SDK Anthropic đồng bộ, kho trong RAM, cắt 4000 ký tự, không kiểm chủ bot, và map thiếu secret thành 503. Bốn điểm đó trái spec hoặc trái D-012.

**Alternatives considered:** Mang nguyên route spike vào rồi sửa (kéo theo kho RAM và SDK đồng bộ, khó gỡ).
