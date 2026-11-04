# Feature Specification: Kênh Telegram, phần logic

**Feature Branch**: `013-telegram-channel`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "F11, phần logic: kênh Telegram cho jarvis-compass. Chủ bot nhắn chữ cho bot trên Telegram và nhận câu trả lời của JARVIS, qua đúng lượt mô hình đã có, để dùng được hằng ngày trên điện thoại. Hiện chưa có đường nào từ Telegram vào lượt. Tính năng không thêm hành vi lập kế hoạch nào: lời hướng dẫn hệ thống, định nghĩa tool, bộ câu eval và mô hình không đổi. Một người dùng duy nhất là chủ bot. Kho kế hoạch không có khái niệm người dùng. Worker không giữ trạng thái giữa các request (constitution II). Trạng thái bền nằm ở Supabase, truy cập qua PostgREST (constitution III). Một lượt có ngân sách 20 giây (D-015, D-021). Telegram gửi lại một update khi webhook không trả 2xx (D-018), nên cùng một update có thể tới nhiều lần. Câu trả lời là chữ trơn, Telegram gửi không parse mode (PRODUCT §9). Chỉ làm phần logic, test được trên máy bằng đồ giả: kho kế hoạch trong bộ nhớ, mô hình giả, client Telegram giả. Không gọi Telegram thật, không deploy, không đổi gói Cloudflare, không chạy migration lên cloud. Tính năng đặt luật cho F10 và F18 (danh tính chủ bot, chống trùng, ngữ cảnh hội thoại), nên spec không cấm ghi thêm một D-xxx ở bước đồng bộ docs. Hành vi: chỉ chủ bot; chỉ request có secret webhook; một tin chữ ra một câu trả lời ở cùng cuộc trò chuyện; ngữ cảnh là các tin gần nhất, giới hạn số tin và tuổi là giả định cho Starter duyệt, không phải F02; một update chỉ xử lý một lần, đủ bốn trạng thái; mọi tin chữ ra một câu không rỗng nói đúng chuyện đã xảy ra (phần còn lại của L1-04); câu dài hơn 4096 ký tự vẫn tới đủ (L1-13, chỉ phần độ dài); tin không phải chữ có một câu cố định; kho treo không làm lượt vượt 20 giây (L1-12 cho đường này); log không chứa token, secret, nội dung tin hay câu trả lời, hai dòng log hiện có không đổi."

## User Scenarios & Testing *(mandatory)*

Chủ bot nhắn chữ cho bot trên điện thoại và nhận một câu trả lời của JARVIS ở đúng cuộc trò chuyện đó. Câu trả lời đi qua lượt đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md) và [spec độ bền ghi](../012-write-durability/spec.md). Lượt đó hôm nay chưa được kênh nào gọi. Kênh này không thêm cách lập kế hoạch mới.

Người dùng của kênh là một người, chủ bot, đúng [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Kho kế hoạch không có khái niệm người dùng, và lát này không thêm khái niệm đó vào kế hoạch. Danh tính chủ bot, secret của webhook, và token của bot là cấu hình đưa lúc chạy. Ba giá trị đó không nằm trong repo và không nằm trong spec này.

Ba kết quả người gọi webhook nhìn thấy, dùng xuyên suốt spec:

- **Từ chối**: người gọi bị báo là chưa được chấp nhận. Không đọc kế hoạch, không ghi kế hoạch, không gọi mô hình, không gửi câu trả lời, không ghi ngữ cảnh, không ghi bản ghi update.
- **Bỏ qua**: người gọi bị báo là đã nhận, nên Telegram không gửi lại update đó chỉ vì lần này bị coi là thất bại. Cùng các điều không được đụng như lúc từ chối.
- **Hoãn**: người gọi bị báo là chưa xong, để Telegram gửi lại. Khác Từ chối ở chỗ bản ghi update có thể đã tồn tại và lần gửi lại là cách duy nhất để update hoàn tất. Hoãn dùng cho năm trường hợp. (a) Lần nhận chồng khi lượt của update đang chạy. (b) Gửi câu trả lời thất bại: câu giữ nguyên trong bản ghi. (c) Kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho: không chạy lượt, không gọi mô hình, không đụng kho kế hoạch, không gửi câu. (d) Lượt đã xong nhưng lưu câu trả lời thất bại: không gửi câu chưa lưu, người gọi bị hoãn, mô hình không bị gọi lại. (e) Câu đã lưu nhưng ghi ngữ cảnh thất bại: không gửi câu, người gọi bị hoãn, câu đã lưu giữ nguyên, mô hình không bị gọi lại.

### User Story 1 - Chủ bot nhắn chữ và nhận một câu (Priority: P1)

Chủ bot gửi một tin chữ trong cuộc trò chuyện riêng với bot. Bot trả đúng một nội dung câu trả lời, gửi lại cùng cuộc trò chuyện đó, bằng chữ trơn theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §9. Nội dung là kết quả của lượt đã có, sau khi áp các câu ở User Story 4. Lượt nhận tin mới và các tin ngữ cảnh còn hiệu lực ở User Story 5. Lệnh như `/start` là tin chữ bình thường.

**Why this priority**: Chưa có đường này thì điện thoại không nói chuyện được với JARVIS. Đây là giá trị dùng hằng ngày của lát này.

**Independent Test**: Mô hình giả trả một câu văn. Kho kế hoạch giả trong bộ nhớ. Client Telegram giả ghi lại mỗi lần gửi. Không mở mạng. Gửi một tin chữ của chủ bot trong cuộc trò chuyện riêng. Đọc câu client giả đã gửi, cuộc trò chuyện đích, và việc mô hình nhận đúng tin mới.

**Acceptance Scenarios**:

1. **Given** cấu hình đủ và chưa có ngữ cảnh, mô hình giả trả "Bạn muốn mình lập kế hoạch cho hai việc đó không?", **When** chủ bot gửi "Tuần này mình nộp báo cáo và học xong chương 3" trong cuộc trò chuyện riêng, **Then** chủ bot nhận đúng câu đó, một lần, trong cùng cuộc trò chuyện. Câu đi bằng chữ trơn: dấu sao, gạch dưới, và dấu backtick giữ nguyên, không thành in đậm hay in nghiêng.
2. **Given** cùng cấu hình, **When** chủ bot gửi `/start`, **Then** tin đó đi vào lượt như một tin chữ, và chủ bot nhận một câu không rỗng ở cùng cuộc trò chuyện.
3. **Given** mô hình giả không gọi tool, **When** xử lý một tin chữ, **Then** kho kế hoạch không bị đọc và không bị ghi.

---

### User Story 2 - Chỉ chủ bot, chỉ request có secret đúng (Priority: P1)

Thiếu secret hoặc secret không khớp thì mọi request bị từ chối, kể cả khi thân request là tin của chủ bot. Thiếu danh tính chủ bot thì mọi tin bị bỏ qua. Tin của người khác bị bỏ qua. Cả hai lối đó không chạy lượt, không đọc hay ghi kế hoạch, không gọi mô hình, không trả lời, không ghi ngữ cảnh, không ghi bản ghi update.

**Why this priority**: Webhook là cửa công khai. Một request giả hoặc một người lạ không được tạo kế hoạch hay tốn một lượt mô hình.

**Independent Test**: Bốn request riêng: thiếu secret, sai secret, thiếu danh tính chủ bot, và đúng secret nhưng người gửi khác chủ bot. Mỗi request mang một tin chữ. Đếm lần gọi mô hình, lần đụng kho kế hoạch, lần gửi Telegram, và lần ghi ngữ cảnh. Tất cả bằng không. Request thiếu hoặc sai secret bị từ chối. Hai request kia bị bỏ qua.

**Acceptance Scenarios**:

1. **Given** secret chưa được cấu hình, **When** một request tới, kể cả request có dạng tin của chủ bot, **Then** request bị từ chối và không chạm vào lượt, kho kế hoạch, mô hình, câu trả lời, ngữ cảnh, hay bản ghi update.
2. **Given** secret đã cấu hình, **When** request thiếu secret hoặc đưa secret khác, **Then** cùng cách từ chối như trên. Giá trị secret đúng và giá trị secret request đưa không xuất hiện trong nhật ký của lần đó.
3. **Given** secret đúng và danh tính chủ bot chưa được cấu hình, **When** một tin chữ tới, **Then** tin bị bỏ qua. Không có câu trả lời.
4. **Given** secret đúng và danh tính chủ bot đã cấu hình, **When** một tin chữ của người khác tới, **Then** tin bị bỏ qua. Không có câu trả lời. Telegram không gửi lại update đó chỉ vì lần này bị bỏ qua.
5. **Given** secret sai và người gửi không phải chủ bot, **When** request tới, **Then** request bị từ chối, không đi tới nhánh bỏ qua.

---

### User Story 3 - Một update chỉ được xử lý một lần (Priority: P1)

Mỗi update có một mã. Cùng mã là cùng một update, dù Telegram gửi lại hay hai lần tới sát nhau. Hai tin cùng chữ nhưng khác mã là hai update. Chủ bot nhận đúng một nội dung câu trả lời cho một update. Một update không chạy lượt quá một lần và không tạo hai kế hoạch.

Bản ghi của một update nằm ở kho bền, không nằm trong bộ nhớ giữa hai lần nhận. Bốn trạng thái:

1. **Chưa từng thấy**: chưa có bản ghi. Lần nhận này nhận xử lý, chạy đúng một lượt với tin chữ, lưu câu trả lời, gửi câu đó, rồi đánh dấu đã gửi.
2. **Đã bắt đầu, chưa có kết quả**: đã có mốc bắt đầu, chưa có câu trả lời đã lưu, và không còn lượt nào đang chạy cho update đó. Lần nhận không chạy lượt. Câu của update trở thành `Chưa chắc tin này đã được xử lý.` rồi câu đó được gửi. Câu này không khẳng định đã lưu hay chưa lưu. Chạy lại có thể tạo một kế hoạch nữa, nên không chạy lại.
3. **Đã có câu, chưa gửi xong**: lượt đã xong hoặc câu cố định đã được lưu, việc gửi chưa được xác nhận. Lần nhận gửi lại đúng câu đã lưu, không chạy lượt. Câu đã lưu là câu "chưa chắc" của [D-021](../../docs/DECISIONS.md) (`Chưa chắc thay đổi đã được lưu.`), một bản ghép của spec 012, hoặc bất kỳ câu nào đã lưu, đều cùng luật này. Gửi câu đó thất bại thì câu giữ nguyên trong bản ghi và người gọi bị hoãn.
4. **Đã gửi xong**: lần nhận không chạy lượt và không gửi thêm. Người gọi được báo đã nhận.

Hai lần tới sát nhau khi chưa có bản ghi vẫn chỉ một lượt và một nội dung câu trả lời. Lần không chạy lượt đó không ghi câu "chưa chắc" đè lên lượt đang chạy, và hoãn người gọi. Nhờ đó, nếu lần đang chạy chết trước khi có câu, một lần nhận sau vẫn gửi được câu "chưa chắc".

**Why this priority**: Webhook bị cắt thì Telegram gửi lại (D-018). Chạy lại lượt có thể tạo một kế hoạch nữa. Câu "chưa chắc" của D-021 đã là một kết quả xong, không phải một lượt bị đứt.

**Independent Test**: Kho bền giả do test giữ, hai lần gọi handler không chia sẻ bộ nhớ kênh. Mô hình giả tạo một kế hoạch rồi trả một câu. Gửi cùng một update hai lần tuần tự sau khi lần đầu đã gửi xong. Rồi đặt sẵn từng trạng thái và gửi lại, trong đó trạng thái đã bắt đầu mà chưa có kết quả được dựng là không còn lượt nào đang chạy, không cần ngủ thật. Rồi hai lần gọi chồng nhau từ trạng thái chưa từng thấy. Rồi một lần gửi thất bại khi câu đã nằm trong bản ghi. Rồi một lần nhận khi kho bền không đọc hoặc ghi được, gồm thiếu cấu hình kho. Đếm lượt, kế hoạch, lần gửi, và kết quả người gọi nhìn thấy.

**Acceptance Scenarios**:

1. **Given** một update chữ của chủ bot chưa từng thấy, và mô hình giả tạo một kế hoạch rồi trả một câu, **When** update đó được nhận, **Then** có đúng một lượt, đúng một kế hoạch, và đúng một nội dung câu trả lời ở cuộc trò chuyện. Bản ghi chuyển sang đã gửi xong.
2. **Given** update đó đã gửi xong, **When** cùng mã update tới lần nữa, **Then** không có lượt mới, không có kế hoạch mới, và không có tin gửi thêm. Người gọi được báo đã nhận.
3. **Given** bản ghi đã có câu `Chưa chắc thay đổi đã được lưu.` và chưa gửi xong, **When** cùng update tới, **Then** client Telegram nhận lại đúng câu đó, mô hình không bị gọi, và không có lần ghi kế hoạch mới.
4. **Given** bản ghi đã có một bản ghép nhiều dòng của spec 012 và chưa gửi xong, **When** cùng update tới, **Then** client nhận lại đúng nguyên văn bản ghép đó và mô hình không bị gọi.
5. **Given** bản ghi đã bắt đầu, chưa có câu đã lưu, và không còn lượt nào đang chạy cho update đó, **When** cùng update tới, **Then** mô hình không bị gọi, kho kế hoạch không bị ghi thêm, câu đã lưu trở thành `Chưa chắc tin này đã được xử lý.`, và câu đó được gửi một lần.
6. **Given** câu ở scenario 5 đã được lưu và đã gửi xong, **When** cùng update tới nữa, **Then** không chạy lượt và không gửi thêm.
7. **Given** chưa có bản ghi, **When** hai lần nhận cùng một update chạy chồng nhau, **Then** mô hình chạy một lần, chỉ một kế hoạch được tạo nếu lượt có tạo kế hoạch, và chủ bot chỉ nhận một nội dung câu trả lời. Lần không chạy lượt không ghi câu "chưa chắc" đè lên lượt đang chạy, và người gọi của lần đó bị hoãn.
8. **Given** lần đang chạy đã chết sau khi có bản ghi bắt đầu và trước khi có câu đã lưu, **When** một lần nhận sau tới, **Then** kết quả đúng scenario 5. Lần nhận chồng ở scenario 7 không được chặn lần nhận sau này.
9. **Given** hai tin chữ cùng nội dung và khác mã update, **When** cả hai được nhận, **Then** đó là hai update. Mỗi update có lượt của nó.
10. **Given** bản ghi đã có một câu đã lưu và chưa gửi xong, **When** việc gửi câu đó thất bại, **Then** câu giữ nguyên trong bản ghi, bản ghi vẫn ở trạng thái đã có câu chưa gửi xong, người gọi bị hoãn, mô hình không bị gọi, và không có lần ghi kế hoạch mới.
11. **Given** secret và token bot đã cấu hình, và kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho, **When** một tin chữ của chủ bot ở cuộc trò chuyện riêng tới, **Then** người gọi bị hoãn. Không chạy lượt, không gọi mô hình, không đụng kho kế hoạch, không gửi câu.
12. **Given** kho bền giả ném lỗi ở lần ghi câu trả lời, sau khi mô hình giả đã tạo một kế hoạch, **When** lần nhận đó xử lý một tin chữ của chủ bot, **Then** có 0 câu gửi, người gọi bị hoãn, đúng 1 kế hoạch, và mô hình không bị gọi lại. Câu chưa lưu không được gửi. **When** lần nhận sau tới, với đồng hồ khoảng lượt đã chết được đẩy qua và không ngủ thật, **Then** lần đó thấy trạng thái đã bắt đầu, không còn lượt đang chạy, chưa có câu, gửi đúng một lần `Chưa chắc tin này đã được xử lý.`, và mô hình không bị gọi thêm.

---

### User Story 4 - Mọi tin chữ ra một câu không rỗng, đúng chuyện đã xảy ra (Priority: P1)

Chủ bot không nhận một tin rỗng, và không nhận một câu nói sai nguyên nhân. Hôm nay lượt trả chuỗi rỗng khi mô hình kết thúc bằng `end_turn` với văn bản rỗng mà chưa có lần ghi thành công, lần ghi bị bỏ, hay lần ghi bị từ chối. Telegram không nhận tin rỗng. Hôm nay lượt bị cắt vì `max_tokens` hoặc bị từ chối (`refusal`), khi chưa có ba loại lần ghi đó, đều ra `Chưa liên lạc được để trả lời lúc này.` Câu đó nói như thể chưa liên lạc được, trong khi mô hình đã trả lời và đã dừng vì quá dài hoặc vì từ chối.

Khi lượt đã có bản ghép của spec 012, chủ bot thấy đúng bản ghép đó. Khi lý do thực sự là chưa liên lạc được, hết ngân sách 20 giây, hoặc hết ba vòng tool, chủ bot thấy đúng câu spec 008 đã chốt cho lý do đó. Lát này không chọn chỗ sửa trong mã. Chỗ sửa thuộc bước plan.

**Why this priority**: Một tin rỗng làm lần gửi thất bại và Telegram gửi lại. Một câu sai nguyên nhân làm chủ bot tưởng mạng hỏng trong khi câu bị cắt hoặc bị từ chối.

**Independent Test**: Mô hình giả lần lượt trả văn bản rỗng, văn bản chỉ khoảng trắng, dừng `max_tokens`, dừng `refusal`, lỗi mô hình, và hết ba vòng. Một ca `max_tokens` sau khi một lần ghi đã thành công. Một ca lượt ném ngoại lệ không phải thiếu khóa, không đẩy đồng hồ khoảng lượt đã chết. Đọc câu client Telegram giả gửi và câu đã lưu. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** mô hình kết thúc `end_turn` bằng văn bản rỗng, và lượt không có lần ghi thành công, lần ghi bị bỏ, hay lần ghi bị từ chối, **When** xử lý tin chữ, **Then** chủ bot nhận đúng `Mình chưa có câu trả lời cho tin này.` Client không nhận chuỗi rỗng.
2. **Given** cùng tình huống nhưng văn bản chỉ gồm khoảng trắng, **When** xử lý tin chữ, **Then** chủ bot nhận đúng câu ở scenario 1, không nhận chuỗi khoảng trắng.
3. **Given** mô hình dừng vì `max_tokens`, và lượt không có ba loại lần ghi trên, **When** xử lý tin chữ, **Then** chủ bot nhận đúng `Câu trả lời bị cắt vì quá dài.` Câu đó không phải `Chưa liên lạc được để trả lời lúc này.`
4. **Given** mô hình dừng vì `refusal`, và lượt không có ba loại lần ghi trên, **When** xử lý tin chữ, **Then** chủ bot nhận đúng `Mình không trả lời được tin này.` Câu đó không phải câu chưa liên lạc được.
5. **Given** mô hình dừng vì `max_tokens` hoặc `refusal` sau khi một lần ghi đã thành công, **When** xử lý tin chữ, **Then** chủ bot nhận đúng bản ghép spec 012 của lần ghi đó, không nhận câu bị cắt và không nhận câu từ chối của scenario 3 và 4.
6. **Given** lượt trả `Chưa liên lạc được để trả lời lúc này.` vì lỗi mô hình hoặc vì hết ngân sách 20 giây, **When** xử lý tin chữ, **Then** chủ bot nhận đúng câu đó.
7. **Given** lượt trả `Chưa trả lời xong yêu cầu này.` vì hết ba vòng, **When** xử lý tin chữ, **Then** chủ bot nhận đúng câu đó.
8. **Given** khóa mô hình thiếu hoặc là chuỗi rỗng, **When** xử lý tin chữ, **Then** chủ bot nhận đúng `Thiếu ANTHROPIC_API_KEY.` Câu đó không chứa giá trị khóa. Update được coi là đã có câu đó, nên lần gửi lại không chạy lượt mới.
9. **Given** mô hình trả một câu còn chữ khác khoảng trắng, **When** xử lý tin chữ, **Then** chủ bot nhận đúng câu đó.
10. **Given** lượt ném một ngoại lệ không phải thiếu khóa, **When** xử lý tin chữ, **Then** câu đã lưu trở thành `Chưa chắc tin này đã được xử lý.` ngay trong lần nhận đó và câu đó được gửi. Không chờ khoảng lượt đã chết. Không chạy lại. Lần gửi lại không chạy lượt mới. Câu không chứa tên loại lỗi hay thông điệp lỗi.

---

### User Story 5 - Tin sau còn hiểu tin trước (Priority: P2)

Lượt của một tin chữ nhận các tin gần nhất của cùng cuộc trò chuyện riêng: tin chữ của chủ bot và câu trả lời của bot. Nhờ đó tin "có" đứng sau câu "Bạn muốn mình lập kế hoạch không?" vẫn còn nghĩa. Ngữ cảnh nằm ở kho bền. Hai lần nhận không dùng bộ nhớ còn lại của lần trước. Đây là các tin đã lưu, không có `session_id` và không có trạng thái "đang chờ trả lời câu hỏi lại".

Số tin tối đa và tuổi tối đa là giả định ở Assumptions, để Starter duyệt. Lỗi bất ngờ là lượt ném ngoại lệ không phải thiếu khóa. Tin chữ của chủ bot và câu `Chưa chắc tin này đã được xử lý.` từ update đứt hoặc lỗi bất ngờ vào ngữ cảnh như một cặp thường, cùng luật với câu `Chưa chắc thay đổi đã được lưu.` và các câu cố định khác của lượt. Tin không phải chữ không vào ngữ cảnh. Chỉ câu `Mình chỉ đọc được tin chữ.` đứng ngoài ngữ cảnh.

**Why this priority**: Không có ngữ cảnh thì mỗi tin là một cuộc mới, và câu trả lời ngắn của chủ bot mất nghĩa. Vẫn đứng sau chuyện nhận được một câu an toàn.

**Independent Test**: Kho bền giả có một tin cũ hơn 24 giờ, một tin đúng 24 giờ, và nhiều hơn 20 tin trong 24 giờ, trong đó có câu của bot "Bạn muốn mình lập kế hoạch không?". Gửi "có". Đọc đúng danh sách mô hình giả nhận. Gọi handler lần thứ hai bằng một đối tượng kênh mới, cùng kho bền. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** ngữ cảnh đã có câu của bot "Bạn muốn mình lập kế hoạch không?" và chưa quá 24 giờ, **When** chủ bot gửi "có", **Then** lượt nhận câu đó như tin trước, rồi "có" như tin mới. Mô hình giả thấy đúng thứ tự đó.
2. **Given** một tin đã lưu quá 24 giờ và một tin đã lưu đúng 24 giờ, **When** một tin chữ mới tới, **Then** tin quá 24 giờ không có trong danh sách đưa vào lượt, và tin đúng 24 giờ còn trong danh sách nếu nó nằm trong 20 tin mới nhất.
3. **Given** hơn 20 tin đã lưu còn trong 24 giờ, **When** một tin chữ mới tới, **Then** lượt chỉ nhận 20 tin mới nhất trong số đó, rồi tin mới. Tin mới luôn được đưa vào dù trần đã đủ.
4. **Given** một tin chữ đã xử lý xong, **When** một lần nhận khác dùng kênh không giữ bộ nhớ của lần trước và cùng kho bền, **Then** lượt mới thấy tin chữ đó và câu trả lời đã lưu, mỗi thứ một lần.
5. **Given** một tin không phải chữ đã được trả bằng câu cố định, **When** một tin chữ sau đó tới, **Then** lượt không thấy tin không phải chữ và không thấy câu cố định đó.
6. **Given** cùng một update chữ đã có câu trả lời trong ngữ cảnh, **When** cùng update tới lại, **Then** ngữ cảnh vẫn một tin của chủ bot và một câu trả lời cho update đó, và lượt không chạy lại.
7. **Given** ngữ cảnh còn trong 24 giờ có một tin chữ của chủ bot cùng câu `Chưa chắc tin này đã được xử lý.` từ update đứt, một tin chữ cùng câu đó từ lỗi bất ngờ, và một tin chữ cùng câu `Chưa chắc thay đổi đã được lưu.`, **When** một tin chữ mới tới, **Then** lượt nhận mỗi cặp đó như một cặp thường, cùng luật với các câu cố định khác của lượt. Câu `Mình chỉ đọc được tin chữ.` không nằm trong danh sách.
8. **Given** câu trả lời của một tin chữ đã lưu và ghi ngữ cảnh thất bại, **When** kênh sắp gửi câu đó, **Then** không gửi câu, người gọi bị hoãn, câu đã lưu giữ nguyên, và mô hình không bị gọi lại.

---

### User Story 6 - Câu dài vẫn tới đủ chữ (Priority: P2)

Câu trả lời dài hơn một tin Telegram vẫn tới đủ, không mất chữ, thành các tin liên tiếp trong cùng cuộc trò chuyện. Trần một tin là 4096 đơn vị UTF-16. Mỗi phần từ 1 đến 4096 đơn vị UTF-16, không cắt giữa một code point. Lý do đếm UTF-16 nằm ở Assumptions. Ghép các phần theo đúng thứ tự thì ra đúng câu gốc, không thêm và không bớt ký tự. Câu đúng 4096 đơn vị UTF-16 là một tin. Câu gồm 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị) là hai tin.

Trong ngữ cảnh, cả câu vẫn là một tin của bot, không phải từng phần.

**Why this priority**: Bản ghép hoặc một câu kế hoạch dài bị cắt ở trần Telegram thì chủ bot mất phần cuối mà không biết.

**Independent Test**: Mô hình giả trả một chuỗi dài đúng 4096 đơn vị UTF-16, một chuỗi 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị), và một chuỗi ngắn. Đọc các phần client giả gửi và ghép lại. Đọc ngữ cảnh. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** câu trả lời dài đúng 4096 đơn vị UTF-16, **When** gửi, **Then** client nhận một tin, đúng nguyên văn.
2. **Given** câu trả lời gồm 2049 emoji ngoài mặt phẳng cơ bản, tức 4098 đơn vị UTF-16, **When** gửi, **Then** client nhận hai tin liên tiếp, mỗi tin từ 1 đến 4096 đơn vị UTF-16, không tin nào bị cắt giữa một code point, không tin nào rỗng, và ghép theo thứ tự gửi ra đúng chuỗi gốc.
3. **Given** câu trả lời đã được tách thành nhiều tin, **When** đọc ngữ cảnh, **Then** câu đó là một tin của bot, bằng đúng chuỗi gốc.
4. **Given** việc gửi cả câu chưa được xác nhận, **When** cùng update tới lại, **Then** client được gửi lại đúng chuỗi gốc, tách theo cùng luật, và lượt không chạy lại.

---

### User Story 7 - Tin không phải chữ, và update không phải tin mới (Priority: P2)

Tin của chủ bot trong cuộc trò chuyện riêng mà không phải chữ, gồm voice, ảnh, và file, được trả bằng đúng một câu cố định `Mình chỉ đọc được tin chữ.` Lượt không chạy. Câu đó không vào ngữ cảnh. Ảnh có chú thích, sticker, vị trí, danh thiếp, và cuộc bình chọn cũng là tin không phải chữ. Tin không có chữ, hoặc chỉ khoảng trắng, dùng cùng câu đó.

Update không phải một tin mới thì bị bỏ qua, gồm tin được sửa, nút bấm, và các loại còn lại. Cuộc trò chuyện nhóm, siêu nhóm, và kênh cũng bị bỏ qua, kể cả khi người gửi là chủ bot. Telegram không gửi lại các update bị bỏ qua chỉ vì chúng bị bỏ qua.

**Why this priority**: Chủ bot cần biết vì sao voice không được trả lời bằng một kế hoạch. Người lạ và nhóm không được đi vào lượt. Phần chạy mô hình vẫn là User Story 1.

**Independent Test**: Gửi voice, ảnh, file, và ảnh có chú thích từ chủ bot. Gửi một tin đã sửa, một nút bấm, và một tin chữ trong nhóm từ chính chủ bot. Đếm lần gọi mô hình và các tin trong ngữ cảnh. Đọc câu client giả gửi, nếu có.

**Acceptance Scenarios**:

1. **Given** chủ bot gửi voice, ảnh, hoặc file trong cuộc trò chuyện riêng, **When** update được nhận, **Then** chủ bot nhận đúng `Mình chỉ đọc được tin chữ.` một lần, ở cùng cuộc trò chuyện. Mô hình không bị gọi. Kho kế hoạch không bị đụng. Ngữ cảnh không có tin này và không có câu cố định.
2. **Given** câu cố định đó đã gửi xong, **When** cùng update tới lại, **Then** không gửi thêm và không gọi mô hình.
3. **Given** một tin bị sửa, một lần bấm nút, hoặc một tin chữ của chủ bot trong nhóm, **When** update được nhận, **Then** update bị bỏ qua. Không có câu trả lời và không có lượt.

---

### User Story 8 - Kho kế hoạch treo không nuốt ngân sách của lượt (Priority: P1)

Đường từ webhook tới lượt vẫn nằm trong ngân sách 20 giây của lượt khi kho kế hoạch không trả về. Chủ bot vẫn nhận một câu không rỗng. Lát này không đổi chữ ký của `execute_tool` thành bắt buộc tham số thời gian còn lại. Đường này phải đưa phần ngân sách còn lại vào lượt, vì bỏ qua thì lời gọi kho hết hạn chờ.

**Why this priority**: Một kho treo trên điện thoại làm chủ bot chờ mãi rồi nhắn lại, và lần nhắn lại có thể thành một update mới.

**Independent Test**: Một test đầu-cuối: update chữ của chủ bot, mô hình giả gọi một tool, kho kế hoạch giả không trả về. Đồng hồ ngân sách của lượt do test điều khiển. Câu trả lời được gửi trong khi kho vẫn chưa trả về, và đồng hồ đó không vượt 20 giây. Không ngủ 20 giây thật. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** kho kế hoạch không trả về và mô hình giả gọi một tool cần kho, **When** xử lý tin chữ của chủ bot trên đường webhook, **Then** chủ bot nhận một câu không rỗng ở cùng cuộc trò chuyện trước khi ngân sách 20 giây của lượt hết. Lời gọi kho không được đợi đến lúc kho trả về.
2. **Given** cùng ca, **When** đọc nhật ký, **Then** token bot và secret webhook không có trong nhật ký.

---

### User Story 9 - Nhật ký không chứa bí mật hay nội dung hội thoại (Priority: P2)

Nhật ký của kênh không chứa token bot, secret webhook, nội dung tin, hay câu trả lời. Hai dòng nhật ký đã có giữ nguyên: bảy khóa của tool ở spec 007, và tám khóa của lần gọi mô hình ở spec 008. Lát này không thêm, không bớt, không đổi tên, và không đổi thứ tự các khóa đó.

Dòng tool vẫn ghi `input` là đầu vào của tool, đúng spec 007. Khi mô hình đưa chữ của chủ bot vào đối số tool, chữ đó vẫn nằm ở `input` vì dòng này không đổi. Ca kiểm "nội dung tin không vào nhật ký" dùng một lượt không gọi tool, để chữ tin và chữ câu trả lời không trùng với đầu vào tool.

**Why this priority**: Webhook và câu trả lời đi qua kênh mới. Một dòng nhật ký chép tin hoặc secret làm lộ hội thoại và cửa vào.

**Independent Test**: Cấu hình mang chuỗi mồi cho token và secret. Tin chữ và câu mô hình giả trả mang hai chuỗi mồi khác. Mô hình không gọi tool. Đọc mọi dòng nhật ký. Rồi một lượt có tool, đọc dòng bảy khóa và dòng tám khóa.

**Acceptance Scenarios**:

1. **Given** một tin chữ được trả lời không qua tool, **When** đọc mọi dòng nhật ký của lần xử lý, **Then** không có token bot, secret webhook, nội dung tin, hay câu trả lời.
2. **Given** một lượt có gọi tool và có gọi mô hình, **When** đọc dòng tool và dòng mô hình, **Then** dòng tool có đúng bảy khóa spec 007 theo đúng thứ tự đã chốt, và dòng mô hình có đúng tám khóa spec 008 theo đúng thứ tự đã chốt.
3. **Given** request bị từ chối vì sai secret, **When** đọc nhật ký của lần đó, **Then** secret đúng và secret request đưa đều không có trong nhật ký.

---

### Edge Cases

- Thiếu token bot thì request bị từ chối trước khi có bản ghi update và trước khi chạy lượt. Không đọc hay ghi kế hoạch, không gọi mô hình. Khi token được cấu hình, một lần gửi lại của update chưa từng được nhận vẫn xử lý bình thường.
- Secret được so khớp đúng nguyên văn. Secret đưa vào thiếu, rỗng, hoặc khác thì từ chối. Danh tính chủ bot là mã số người gửi, so khớp đúng, không cắt khoảng trắng. Mã số và chuỗi thập phân của cùng mã đó được coi là khớp. Giá trị này không ghi trong repo.
- Thứ tự kiểm: secret, rồi token bot, rồi loại update, rồi cuộc trò chuyện riêng, rồi danh tính chủ bot, rồi bản ghi update. Bước sau không chạy khi bước trước đã từ chối hoặc bỏ qua.
- Secret đúng nhưng thân request không phải một update đọc được: bỏ qua, không đụng gì khác.
- Tin chữ là tin có phần chữ chính. Chú thích của ảnh không phải phần chữ chính.
- `/start` và mọi lệnh khác là tin chữ. Không có lệnh riêng.
- Cuộc trò chuyện nhóm, siêu nhóm, và kênh bị bỏ qua dù người gửi là chủ bot.
- Hủy tác vụ giữa chừng không thành một câu trả lời của lần nhận đó. Bản ghi nếu đã bắt đầu mà chưa có câu, và không còn lượt nào đang chạy, thì lần nhận sau gửi `Chưa chắc tin này đã được xử lý.` và không chạy lượt.
- Lần nhận chồng khi lượt đang chạy thì người gọi bị hoãn. Lần đó không ghi câu "chưa chắc" đè lên lượt đang chạy. Nếu lần đang chạy chết trước khi có câu, lần nhận sau vẫn gửi được câu chưa chắc.
- Gửi câu trả lời thất bại thì câu giữ nguyên trong bản ghi và người gọi bị hoãn. Lần sau gửi đúng câu đã lưu, không chạy lượt.
- Kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho: người gọi bị hoãn. Không chạy lượt, không gọi mô hình, không đụng kho kế hoạch, không gửi câu.
- Lượt đã xong nhưng lưu câu trả lời thất bại: không gửi câu chưa lưu, người gọi bị hoãn, mô hình không bị gọi lại. Lần nhận sau thấy trạng thái đã bắt đầu, không còn lượt đang chạy, chưa có câu, nên câu đã lưu thành `Chưa chắc tin này đã được xử lý.` rồi được gửi.
- Lượt ném ngoại lệ không phải thiếu khóa thì câu đã lưu thành `Chưa chắc tin này đã được xử lý.` ngay rồi được gửi. Không chờ khoảng lượt đã chết, không chạy lại. Câu không chứa tên loại lỗi hay thông điệp lỗi. Thiếu khóa vẫn ra `Thiếu ANTHROPIC_API_KEY.`
- Xác nhận đã gửi là cho cả câu. Lần nhận khi chưa xác nhận gửi lại cả câu, tách theo luật độ dài. Đứt sau khi một phần đã tới có thể làm phần đó xuất hiện lần nữa lúc gửi lại. Đã xác nhận thì không gửi thêm.
- Câu `Chưa chắc tin này đã được xử lý.` là kết quả đã lưu. Lần sau không chạy lượt. Câu này khác câu `Chưa chắc thay đổi đã được lưu.` của D-021. Câu D-021, khi đã là câu của lượt, cũng là kết quả đã lưu.
- Hai update khác mã không bị gộp chỉ vì cùng chữ.
- Tin của chủ bot không bị cắt bớt trước khi đưa vào lượt.
- Ngữ cảnh một cuộc trò chuyện riêng không lẫn tin của cuộc khác. Trong phạm vi lát này chỉ cuộc riêng của chủ bot được ghi.
- Câu trả lời gửi cho chủ bot không chứa mã kế hoạch, mã việc con, hay giá trị khóa, secret, hoặc token, ngoài đúng câu `Thiếu ANTHROPIC_API_KEY.` khi thiếu khóa. Câu đó không chứa giá trị khóa.
- `stop_reason` khác `end_turn`, `tool_use`, `max_tokens`, và `refusal`, khi không có bản ghép, vẫn ra câu spec 008 đã chốt. Lát này không đặt câu mới cho các lý do đó.
- Văn bản của mô hình còn chữ khác khoảng trắng được giữ nguyên từng ký tự, rồi mới xét trần 4096 đơn vị UTF-16. Không cắt giữa một code point.
- Một lượt không gọi tool thì kho kế hoạch không bị đụng.
- Bộ câu eval gọi lượt trực tiếp. Lát này không đổi bộ câu đó và không đổi cách chấm.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Request thiếu secret webhook, hoặc secret không khớp cấu hình, MUST bị từ chối. Thiếu cấu hình secret MUST làm mọi request bị từ chối. Request bị từ chối MUST NOT đọc hay ghi kho kế hoạch, MUST NOT gọi mô hình, MUST NOT gửi câu trả lời, MUST NOT ghi ngữ cảnh, và MUST NOT ghi bản ghi update.
- **FR-002**: Thiếu token bot MUST bị từ chối trước khi ghi bản ghi update và trước khi chạy lượt, với cùng các điều không được đụng như FR-001.
- **FR-003**: Tin của người không phải chủ bot, tin khi thiếu cấu hình danh tính chủ bot, update không phải một tin mới, và tin không ở cuộc trò chuyện riêng MUST bị bỏ qua. Bỏ qua MUST NOT chạy lượt, MUST NOT đụng kho kế hoạch, MUST NOT gọi mô hình, MUST NOT gửi câu trả lời, MUST NOT ghi ngữ cảnh, và MUST NOT ghi bản ghi update. Người gọi MUST được báo đã nhận.
- **FR-004**: Một tin chữ của chủ bot ở cuộc trò chuyện riêng MUST đưa vào lượt đã có và MUST dẫn tới đúng một nội dung câu trả lời không rỗng, gửi lại cùng cuộc trò chuyện, bằng chữ trơn. Dấu sao, gạch dưới, và dấu backtick MUST được giữ là ký tự, không thành định dạng. `/start` MUST đi cùng đường với tin chữ.
- **FR-005**: Lời hướng dẫn hệ thống, số phiên bản lời hướng dẫn, bộ định nghĩa tool, số phiên bản bộ định nghĩa, bộ câu eval, cách chấm, và mô hình MUST giữ nguyên. Lát này MUST NOT thêm hành vi lập kế hoạch và MUST NOT thêm khái niệm người dùng vào kho kế hoạch.
- **FR-006**: Mỗi update MUST được nhận diện bằng mã update, so khớp đúng. Cùng mã MUST NOT chạy lượt quá một lần và MUST NOT tạo hai kế hoạch. Hai mã khác nhau MUST được xử lý như hai update dù cùng chữ.
- **FR-007**: Trạng thái chưa từng thấy của một tin chữ MUST chạy một lượt, lưu câu trả lời, gửi câu đó, rồi chuyển sang đã gửi xong. Hai lần nhận chồng nhau từ trạng thái chưa từng thấy MUST chỉ một lượt và một nội dung câu trả lời.
- **FR-008**: Trạng thái đã bắt đầu mà chưa có câu đã lưu, khi không còn lượt nào đang chạy cho update đó, MUST NOT chạy lượt. Câu đã lưu MUST trở thành đúng `Chưa chắc tin này đã được xử lý.` rồi câu đó MUST được gửi. Lần nhận chồng với một lượt đang chạy MUST NOT chạy lượt thứ hai, MUST NOT gửi một nội dung thứ hai, MUST NOT ghi câu đó đè lên lượt đang chạy, và người gọi MUST bị hoãn.
- **FR-009**: Trạng thái đã có câu mà chưa gửi xong MUST gửi lại đúng nguyên văn câu đã lưu, gồm câu `Chưa chắc thay đổi đã được lưu.` và bản ghép spec 012, và MUST NOT chạy lượt. Khi gửi câu đó thất bại, câu MUST giữ nguyên trong bản ghi và người gọi MUST bị hoãn. Trạng thái đã gửi xong MUST NOT chạy lượt và MUST NOT gửi thêm. Khi lần nhận không bị hoãn, người gọi MUST được báo đã nhận.
- **FR-010**: Khi kết quả lượt là chuỗi rỗng hoặc chỉ khoảng trắng, và lượt không có lần ghi thành công, lần ghi bị bỏ, hay lần ghi bị từ chối, câu chủ bot nhận MUST là đúng `Mình chưa có câu trả lời cho tin này.` Khi mô hình dừng vì `max_tokens` trong tình huống không có ba loại lần ghi đó, câu MUST là đúng `Câu trả lời bị cắt vì quá dài.` Khi mô hình dừng vì `refusal` trong tình huống đó, câu MUST là đúng `Mình không trả lời được tin này.` Hai câu đó MUST NOT là `Chưa liên lạc được để trả lời lúc này.`
- **FR-011**: Khi lượt có bản ghép spec 012, câu chủ bot nhận MUST là đúng bản ghép đó, kể cả nếu lý do dừng là `max_tokens` hoặc `refusal`. Câu spec 008 đã chốt cho lỗi mô hình, hết ngân sách, hết ba vòng, và thiếu khóa MUST được giữ nguyên khi đó đúng là lý do. Câu thiếu khóa MUST NOT chứa giá trị khóa, và MUST được lưu thành câu của update.
- **FR-012**: Ngữ cảnh đưa vào lượt MUST là tối đa 20 tin đã lưu của cùng cuộc trò chuyện riêng, mới nhất, mỗi tin không quá 24 giờ tính tới lúc nhận tin mới, theo thứ tự cũ tới mới, rồi tới tin mới. Tin đã lưu gồm tin chữ của chủ bot và câu trả lời của bot cho các tin chữ đó. Tin chữ của chủ bot và câu `Chưa chắc tin này đã được xử lý.` từ update đứt hoặc lỗi bất ngờ (ngoại lệ không phải thiếu khóa) MUST vào ngữ cảnh như một cặp thường, cùng luật với câu `Chưa chắc thay đổi đã được lưu.` và các câu cố định khác của lượt. Một câu trả lời dài vẫn MUST là một tin ngữ cảnh. Tin không phải chữ MUST NOT vào ngữ cảnh. Chỉ câu `Mình chỉ đọc được tin chữ.` đứng ngoài ngữ cảnh. Ngữ cảnh và bản ghi update MUST nằm ở kho bền, MUST NOT nằm trong bộ nhớ kênh giữa hai lần nhận, và MUST NOT dùng `session_id` hay trạng thái đang chờ câu trả lời.
- **FR-013**: Cùng một update MUST NOT thêm ngữ cảnh quá một lần cho tin của chủ bot và một lần cho câu trả lời. Lần gửi lại sau khi đã có câu MUST NOT nhân đôi hai tin đó.
- **FR-014**: Câu dài hơn 4096 đơn vị UTF-16 MUST được gửi thành các tin liên tiếp, mỗi tin từ 1 đến 4096 đơn vị UTF-16, không cắt giữa một code point. Ghép các phần theo thứ tự gửi MUST ra đúng chuỗi gốc. Câu dài đúng 4096 đơn vị UTF-16 MUST là một tin. Câu gồm 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị UTF-16) MUST là hai tin. Chưa xác nhận gửi xong thì lần sau MUST gửi lại cả chuỗi gốc theo luật này. Đã gửi xong thì MUST NOT gửi thêm.
- **FR-015**: Tin không phải chữ của chủ bot ở cuộc trò chuyện riêng MUST được trả bằng đúng `Mình chỉ đọc được tin chữ.` một lần, MUST NOT gọi mô hình, MUST NOT đụng kho kế hoạch, và MUST NOT đưa tin đó hay câu đó vào ngữ cảnh. Cùng update sau khi đã gửi xong MUST NOT gửi thêm.
- **FR-016**: Trên đường webhook, một kho kế hoạch không trả về MUST NOT làm xử lý vượt ngân sách 20 giây của lượt. Chủ bot MUST vẫn nhận một câu không rỗng. Lời gọi kho MUST NOT được đợi đến lúc kho trả về. Lát này MUST NOT đổi tham số thời gian còn lại của `execute_tool` thành bắt buộc cho mọi nơi gọi.
- **FR-017**: Nhật ký MUST NOT chứa token bot, secret webhook, nội dung tin Telegram, hay câu trả lời, với ngoại lệ duy nhất là `input` của dòng tool bảy khóa khi mô hình đưa chữ đó vào đối số tool. Dòng tool MUST giữ đúng bảy khóa spec 007, đúng thứ tự đã chốt. Dòng lần gọi mô hình MUST giữ đúng tám khóa spec 008, đúng thứ tự đã chốt. Lần từ chối vì sai secret MUST NOT ghi secret đúng hay secret request đưa.
- **FR-018**: Bộ test của lát này MUST chạy trên máy bằng kho kế hoạch giả trong bộ nhớ, mô hình giả, client Telegram giả, và kho bền giả do test giữ. Bộ test MUST NOT gọi Telegram thật, MUST NOT mở mạng, MUST NOT deploy, và MUST NOT chạy migration lên cloud.
- **FR-019**: Khi kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho, người gọi MUST bị hoãn. Lần nhận đó MUST NOT chạy lượt, MUST NOT gọi mô hình, MUST NOT đụng kho kế hoạch, và MUST NOT gửi câu.
- **FR-020**: Khi lượt ném ngoại lệ không phải thiếu khóa, câu đã lưu MUST trở thành đúng `Chưa chắc tin này đã được xử lý.` ngay trong lần nhận đó, rồi câu đó MUST được gửi. Lần nhận MUST NOT chờ khoảng coi lượt đã chết và MUST NOT chạy lại. Câu đó MUST NOT chứa tên loại lỗi hay thông điệp lỗi.
- **FR-021**: Khi lượt đã xong nhưng lưu câu trả lời thất bại, kênh MUST NOT gửi câu chưa lưu. Câu gửi đi luôn là câu đã lưu, theo thứ tự lưu rồi gửi của FR-007. Người gọi MUST bị hoãn. Mô hình MUST NOT bị gọi lại. Lần nhận sau thấy trạng thái đã bắt đầu, không còn lượt đang chạy, chưa có câu, nên theo FR-008 câu đã lưu MUST trở thành đúng `Chưa chắc tin này đã được xử lý.` rồi câu đó MUST được gửi.
- **FR-022**: Khi câu đã lưu nhưng ghi ngữ cảnh thất bại, kênh MUST NOT gửi câu. Người gọi MUST bị hoãn. Câu đã lưu giữ nguyên, mô hình MUST NOT bị gọi lại. Mọi đường gửi một câu đã lưu (lượt vừa xong, gửi lại câu đã lưu, câu `Chưa chắc tin này đã được xử lý.`) MUST ghi ngữ cảnh cho cả hai vai trước khi gửi, cùng luật không nhân đôi của FR-013, trừ câu `Mình chỉ đọc được tin chữ.` (FR-012).

### Key Entities

- **Update**: Một lần Telegram giao một việc, nhận diện bằng mã update. Có mốc bắt đầu, câu trả lời đã lưu khi đã có, và việc gửi đã được xác nhận hay chưa. Không phải một kế hoạch.
- **Tin ngữ cảnh**: Một tin chữ của chủ bot hoặc một câu trả lời của bot trong cuộc trò chuyện riêng, với lúc lưu và mã update đã sinh ra nó. Cặp tin chữ và câu `Chưa chắc tin này đã được xử lý.` từ update đứt hoặc lỗi bất ngờ là một cặp thường, cùng luật với câu `Chưa chắc thay đổi đã được lưu.` và các câu cố định khác của lượt. Câu trả lời dài là một tin. Chỉ câu `Mình chỉ đọc được tin chữ.` không phải tin ngữ cảnh. Không có trạng thái hỏi lại.
- **Cấu hình kênh**: Mã số chủ bot, secret webhook, và token bot. Có lúc chạy, không nằm trong repo, không phải dữ liệu kế hoạch.
- **Lượt**: Lượt đã chốt ở spec 008 và spec 012. Nhận tin mới, các tin trước, và kho kế hoạch. Cho ra một chuỗi. Lát này không thêm luật lập kế hoạch vào lượt.
- **Kế hoạch và việc con**: Đúng thực thể đã có. Không thêm người dùng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% tin chữ của chủ bot ở cuộc trò chuyện riêng nhận đúng một nội dung câu trả lời không rỗng ở cùng cuộc trò chuyện, bằng chữ trơn. 100% lệnh `/start` đi cùng đường đó.
- **SC-002**: 100% request thiếu secret, sai secret, hoặc thiếu cấu hình secret bị từ chối và có 0 lần đụng kho kế hoạch, 0 lần gọi mô hình, 0 câu trả lời, 0 lần ghi ngữ cảnh, 0 bản ghi update. 100% tin của người khác, tin khi thiếu danh tính chủ bot, update không phải tin mới, và tin ngoài cuộc trò chuyện riêng bị bỏ qua với cùng các số 0 đó, và người gọi được báo đã nhận.
- **SC-003**: 100% cặp lần nhận cùng một mã update chỉ chạy tối đa một lượt và tạo tối đa một kế hoạch. 100% update đã gửi xong không gửi thêm. 100% update đã có câu, gồm câu `Chưa chắc thay đổi đã được lưu.` và bản ghép spec 012, được gửi lại đúng nguyên văn khi chưa gửi xong và không chạy lượt. 100% lần gửi câu thất bại giữ nguyên câu trong bản ghi và hoãn người gọi. 100% update đã bắt đầu, không còn lượt đang chạy, chưa có câu, nhận đúng `Chưa chắc tin này đã được xử lý.` và không chạy lượt. 100% lần nhận chồng khi lượt đang chạy không ghi câu đó đè lên lượt đang chạy, không gửi một nội dung thứ hai, và hoãn người gọi. 100% lần kho bền không đọc hoặc ghi được lúc nhận, gồm thiếu cấu hình kho, bị hoãn và có 0 lượt, 0 lần gọi mô hình, 0 lần đụng kho kế hoạch, 0 câu gửi. 100% lần lượt đã xong nhưng lưu câu trả lời thất bại, sau khi đã tạo một kế hoạch, có 0 câu gửi, hoãn người gọi, không gọi lại mô hình, và vẫn đúng 1 kế hoạch. 100% lần nhận sau của trường hợp đó, khi không còn lượt đang chạy và chưa có câu, gửi đúng một lần `Chưa chắc tin này đã được xử lý.` và không gọi mô hình thêm.
- **SC-004**: 100% kết quả lượt rỗng hoặc chỉ khoảng trắng, khi không có lần ghi thành công, lần ghi bị bỏ, hay lần ghi bị từ chối, thành đúng `Mình chưa có câu trả lời cho tin này.` 100% lần dừng `max_tokens` và 100% lần dừng `refusal` trong tình huống đó thành đúng câu nguyên nhân của riêng nó, và 0 lần trong tình huống đó thành câu chưa liên lạc được. 100% lần đã có bản ghép thì câu chủ bot nhận là đúng bản ghép. 100% lượt ném ngoại lệ không phải thiếu khóa lưu ngay đúng `Chưa chắc tin này đã được xử lý.`, gửi câu đó, không chờ khoảng lượt đã chết, không chạy lại, và câu không chứa tên loại lỗi hay thông điệp lỗi.
- **SC-005**: 100% lượt của tin chữ nhận đúng các tin ngữ cảnh còn trong 20 tin và 24 giờ, cũ tới mới, rồi tin mới. 0 tin quá tuổi. 0 tin không phải chữ trong ngữ cảnh. 0 lần nhận sau thấy ngữ cảnh chỉ nhờ bộ nhớ kênh của lần trước. 0 update có hai bản ngữ cảnh của cùng tin hoặc cùng câu trả lời. 100% câu `Chưa chắc tin này đã được xử lý.` từ update đứt hoặc lỗi bất ngờ, khi còn trong 20 tin và 24 giờ, vào ngữ cảnh như một cặp thường, cùng luật với câu `Chưa chắc thay đổi đã được lưu.` và các câu cố định khác của lượt. 0 lần câu `Mình chỉ đọc được tin chữ.` nằm trong ngữ cảnh.
- **SC-006**: 100% câu dài hơn 4096 đơn vị UTF-16 tới đủ: ghép các phần theo thứ tự ra đúng chuỗi gốc, mỗi phần từ 1 đến 4096 đơn vị UTF-16, không cắt giữa một code point. 100% câu dài đúng 4096 đơn vị UTF-16 là một tin. 100% câu gồm 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị) là hai tin. 100% câu như vậy vẫn là một tin trong ngữ cảnh.
- **SC-007**: 100% tin không phải chữ của chủ bot ở cuộc trò chuyện riêng nhận đúng một lần câu `Mình chỉ đọc được tin chữ.` và có 0 lần gọi mô hình. 100% update loại khác và 100% tin nhóm bị bỏ qua với 0 câu trả lời.
- **SC-008**: 100% lần kho kế hoạch không trả về, trên đường webhook, vẫn có một câu không rỗng gửi cho chủ bot trước khi ngân sách 20 giây của lượt hết, và lời gọi kho không được đợi đến lúc kho trả về.
- **SC-009**: 100% dòng nhật ký của kênh không chứa token bot, secret webhook, nội dung tin, hay câu trả lời, trừ `input` của dòng tool khi đối số tool mang chữ đó. 100% dòng tool và 100% dòng mô hình giữ đúng các khóa và thứ tự đã chốt. 0 thay đổi ở lời hướng dẫn, số phiên bản lời hướng dẫn, bộ định nghĩa tool, số phiên bản bộ định nghĩa, bộ câu eval, cách chấm, và mô hình.

## Assumptions

- Hai số sau đây để Starter duyệt trước bước plan. Trần ngữ cảnh: 20 tin đã lưu trước tin mới. Tuổi tối đa: 24 giờ, tính từ lúc kênh lưu tin tới lúc nhận tin mới; tin đúng 24 giờ vẫn được đưa vào, tin cũ hơn thì không. Test điều khiển đồng hồ tuổi tin và đồng hồ ngân sách lượt, không ngủ 24 giờ thật và không ngủ 20 giây thật.
- Cách biết "không còn lượt nào đang chạy" thuộc bước plan. Test phải dựng được trạng thái đã bắt đầu mà chưa có kết quả mà không ngủ thật. Nếu plan dùng một khoảng thời gian để coi lượt đã chết, khoảng đó phải dài hơn ngân sách 20 giây của lượt, số cụ thể đưa Starter duyệt ở bước plan, và test đẩy đồng hồ giả thay vì ngủ. Spec này không chốt số giây đó.
- Lịch và số lần Telegram gửi lại chưa đo. Nếu Telegram bỏ cuộc trước khi khoảng lượt đã chết trôi qua thì chủ bot không nhận câu nào cho update đó. Rủi ro này đo ở vòng chạy thật.
- Trần một tin là 4096 đơn vị UTF-16. Mỗi phần từ 1 đến 4096 đơn vị, không cắt giữa một code point. Câu đúng 4096 đơn vị là một tin. Câu gồm 2049 emoji ngoài mặt phẳng cơ bản (4098 đơn vị) là hai tin. Đếm UTF-16 không bao giờ vượt trần dù Telegram đếm theo cách nào. Đếm code point có thể vượt nếu Telegram đếm UTF-16; khi đó lần gửi bị từ chối và update kẹt ở trạng thái 3.
- Năm câu do lát này chọn, vì yêu cầu gốc giao nghĩa và giao một số nguyên văn. Starter duyệt chữ:
  - Không có câu trả lời: `Mình chưa có câu trả lời cho tin này.`
  - Bị cắt vì quá dài: `Câu trả lời bị cắt vì quá dài.`
  - Bị từ chối: `Mình không trả lời được tin này.`
  - Update đã bắt đầu, không còn lượt đang chạy, chưa có kết quả: `Chưa chắc tin này đã được xử lý.` Cùng câu này khi lượt ném ngoại lệ không phải thiếu khóa: lưu và gửi ngay, không chờ khoảng lượt đã chết, không chạy lại. Câu không chứa tên loại lỗi hay thông điệp lỗi.
  - Tin không phải chữ: `Mình chỉ đọc được tin chữ.`
- Câu update đứt giữa chừng cố ý khác câu `Chưa chắc thay đổi đã được lưu.` của D-021. Câu D-021 chỉ nói về một lần ghi. Câu mới không khẳng định đã lưu và không khẳng định chưa lưu. Khi lượt đã xong bằng câu D-021 hoặc bằng bản ghép, lần gửi lại gửi đúng câu đó.
- Danh tính chủ bot là mã số người gửi trên Telegram, không phải tên người dùng. Tên người dùng đổi được và có thể vắng. So khớp đúng mã số.
- Thiếu token bot thì từ chối, cùng họ với thiếu secret: chưa có gì để gửi thì không chạy lượt. Starter duyệt điểm này. Yêu cầu gốc nói rõ thiếu secret và thiếu danh tính, không nói rõ thiếu token.
- Xác nhận gửi là cho cả câu, không nhớ từng phần đã tới. Gửi lại trước khi xác nhận là gửi lại cả câu. Đứt sau phần đầu có thể làm phần đầu tới lần nữa.
- Gửi là ít nhất một lần. Telegram không có khóa chống gửi trùng cho sendMessage. Hai lần nhận chồng ở giai đoạn gửi, hoặc đứt giữa các phần, có thể làm cùng một câu tới hai lần. Lát này chấp nhận điều đó.
- "Chữ trơn, không parse mode" có nghĩa người nhận thấy đúng ký tự đã lưu. Test đọc yêu cầu gửi mà client giả ghi lại: không bật kiểu diễn giải định dạng.
- Lượt là lượt đã có. Lát này không chỉ định file sẽ sửa để đổi câu rỗng, câu `max_tokens`, và câu `refusal`. Plan chọn chỗ sửa. Bộ câu eval và cách chấm không đổi. Khẳng định test cũ chỉ được đổi khi nó khóa đúng hành vi người dùng Telegram mà FR-010 và FR-011 đổi.
- Hình lưu của bản ghi update và của tin ngữ cảnh thuộc bước plan. Spec chỉ chốt điều quan sát được: sống qua hai lần nhận không chung bộ nhớ kênh, và test dùng kho giả. Bước specify không viết migration.
- Kiểm trên máy bằng kho kế hoạch giả trong bộ nhớ, mô hình giả, client Telegram giả, và kho bền giả. Không gọi Telegram thật. Phần chạy thật, gồm đăng ký webhook, gói Workers Paid, đo bộ nhớ, `pywrangler dev`, migration lên cloud, deploy, và một lần gọi mô hình thật với danh sách mở đầu bằng tin `assistant` để xem API trả gì, là vòng riêng sau tính năng này. Lát này không thêm bộ lọc cho danh sách đó.
- Bước specify không sửa `docs/`. Tính năng này không sửa [docs/PRODUCT.md](../../docs/PRODUCT.md). Bước đồng bộ docs sau này được thêm một quyết định trong [docs/DECISIONS.md](../../docs/DECISIONS.md) cho ba luật F10 và F18 sẽ dùng lại: danh tính chủ bot, chống xử lý trùng một update, và ngữ cảnh hội thoại. Spec không cấm quyết định đó và không gán số. Câu nào trong `docs/ARCHITECTURE.md` hoặc bảng review mà tính năng này làm thành sai thì sửa ở bước đồng bộ đó. Không sửa constitution. Diagram trong `docs/architecture/` không sửa cùng thay đổi code (D-016).
- Ngoài phạm vi, theo mô tả tính năng:
  - Voice và nhận dạng giọng nói, hiểu nội dung ảnh hay file, nhóm chat, nhiều người dùng, lệnh riêng, nút bấm, hiệu ứng đang gõ, và trả lời theo từng mảnh.
  - F02 (`session_id`, hỏi lại có trạng thái), F10, F17, F18. Ba luật ở trên là để các vòng đó dùng lại, không phải làm các vòng đó.
  - Đăng ký webhook với Telegram, Workers Paid, đo bộ nhớ, `pywrangler dev`, migration lên cloud, deploy. Một lần gọi mô hình thật với danh sách mở đầu bằng tin `assistant`.
  - Đổi lời hướng dẫn, số phiên bản lời hướng dẫn, bộ định nghĩa tool, số phiên bản bộ định nghĩa, bộ câu eval, cách chấm, hoặc mô hình.
  - Hai phần còn lại của L1-13: dòng trống trong bản ghép, và câu "Đã lưu" khi việc con không đổi. Việc đổi tham số thời gian còn lại của `execute_tool` thành bắt buộc.
  - Tóm tắt hay nén hội thoại dài.
  - Sửa `docs/PRODUCT.md`.
  - Sửa các file spec cũ trong `specs/`.
