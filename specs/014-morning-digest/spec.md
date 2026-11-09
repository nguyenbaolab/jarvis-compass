# Feature Specification: Digest sáng và lệnh /next

**Feature Branch**: `014-morning-digest`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "F10, vòng đầu (D-024 mục 2): jarvis-compass tự nhắn chủ bot một tin digest mỗi sáng, và chủ bot gõ /next để xem cùng nội dung bất cứ lúc nào. Đây là lần đầu bot chủ động gửi tin, trước giờ chỉ trả lời. Digest lúc 08:00 giờ Helsinki, kể cả đổi giờ mùa, vào cuộc trò chuyện riêng với chủ bot. Với mỗi kế hoạch đang hoạt động, tin nêu việc chưa làm đầu tiên theo thứ tự trong kế hoạch, giữ nguyên chữ tiêu đề. Không gọi mô hình. Mỗi ngày theo lịch Helsinki tối đa một digest, kể cả khi cron chạy lại hoặc chạy hai lần. /next trả ngay đúng nội dung như digest, không gọi mô hình, chỉ nhận từ chủ bot (D-022). Đây là lệnh cứng đầu tiên; hiện mọi tin chữ đều đi vào mô hình. Digest và nội dung /next do cùng một quy tắc dựng, đầu vào là các kế hoạch. Digest là tin bot gửi, nên theo D-022 phải vào ngữ cảnh hội thoại trước khi gửi. Đồng hồ là giờ Helsinki, kể cả đổi giờ mùa. Đã kiểm trên môi trường dev ở nhánh spike/zoneinfo-pyodide (sáu mốc năm 2026 ra độ lệch 2, 3, 2, 3, 3, 2); chưa kiểm trên Worker đã deploy. Ngoài phạm vi: ngày, ưu tiên, sức (F17 mở rộng); /today; nhắc theo giờ và tin buổi tối; việc hằng ngày; sự kiện; quét tải; form; lịch. Digest chưa có ngày nên chỉ nói được việc chưa làm đầu tiên của mỗi kế hoạch, kể cả việc đã quá hạn mà ngày chỉ nằm trong tiêu đề. Sáu câu dưới đây không được tự quyết ở bước specify; chúng dành cho /speckit-clarify: thứ tự các kế hoạch trong tin; không có kế hoạch đang hoạt động thì gửi tin ngắn hay im lặng; gửi kênh lỗi thì đánh dấu đã gửi khi nào và lần cron sau trong ngày có thử lại không; tin /next và câu trả lời có vào ngữ cảnh không; tin dài hơn giới hạn kênh có dùng luật tách tin của spec 013 không; đưa ngày hôm nay cho mô hình (D-024 mục 11) làm trong F10 hay để F17 mở rộng cùng prompt v3."

## Clarifications

### Session 2026-11-07

- Q: Kế hoạch đang hoạt động nhưng không còn việc `pending` có một đoạn trong tin không? → A: Không. Kế hoạch vẫn đang hoạt động vì chưa có cách đóng; đoạn "Không còn việc chưa làm." cho từng kế hoạch sẽ chất đống. Câu đó chỉ là cả tin khi không có đoạn nào. Cách xếp đoạn đã duyệt: mục tiêu, xuống dòng, tiêu đề việc `pending` đầu tiên; các đoạn cách nhau một dòng trống.
- Q: Thứ tự các kế hoạch trong tin, khi chưa có ưu tiên, là mới nhất trước hay cũ nhất trước? → A: Cũ nhất trước. Thứ tự tạo (`created_order`) tăng dần, để vị trí ổn định qua các ngày. Không dùng thứ tự liệt kê của spec 001.
- Q: Khi không có đoạn nào, digest gửi tin ngắn hay im lặng? → A: Đúng câu `Không còn việc chưa làm.`, cả digest lẫn `/next`. `/next` có người chờ. Digest im lặng thì không phân biệt được bot hỏng với không có việc ([D-018](../../docs/DECISIONS.md)).
- Q: Mốc "đã gửi" ghi khi nào, và lần chạy sau trong ngày có thử lại không? → A: Ghi sau khi kênh xác nhận gửi. Gửi lỗi hoặc không rõ kết quả: ngày đó chưa gửi, lần chạy sau trong ngày thử lại. Ghi ngữ cảnh lỗi: không gửi, không ghi mốc, lần sau thử lại. Thử lại không ghi ngữ cảnh lần hai nếu đã ghi. Chấp nhận digest lặp khi không rõ kết quả, như [spec kênh Telegram](../013-telegram-channel/spec.md): xác nhận là cho cả tin; đứt sau một phần có thể làm phần đó tới lần nữa; đã xác nhận thì không gửi thêm.
- Q: Tin `/next` của chủ bot và câu trả lời có vào ngữ cảnh hội thoại không? → A: Cả hai vào ngữ cảnh trước khi gửi, theo [D-022](../../docs/DECISIONS.md) mục 3. Ghi ngữ cảnh lỗi thì hoãn như spec 013.
- Q: Tin dài hơn một tin của kênh có dùng luật tách của spec 013 không? → A: Có, cho digest và cho câu trả lời `/next`. Trong ngữ cảnh vẫn là một tin bot bằng chuỗi đầy đủ.
- Q: Đưa ngày hôm nay cho mô hình làm trong F10 hay để F17? → A: Để F17 mở rộng. F10 không sửa lượt mô hình và không đổi `PROMPT_VERSION`.
- Q: Chuỗi nào được nhận là lệnh `/next`? → A: Tin chữ mà sau khi cắt khoảng trắng hai đầu, không phân biệt hoa thường, bằng `/next`. `/next@bot`, `/next hôm nay`, `/start` và mọi tin khác vẫn đi vào mô hình. Bàn phím điện thoại hay chèn dấu cách.
- Q: Quy tắc dựng chữ có nhận thời điểm hiện tại không? → A: Không ở vòng này, vì thời điểm không làm đổi chữ. F17 mở rộng thêm tham số khi cần ngày.

## User Scenarios & Testing *(mandatory)*

Chủ bot nhận một tin buổi sáng do JARVIS tự gửi, và bất cứ lúc nào cũng gõ `/next` để xem lại đúng nội dung đó. Trước lát này bot chỉ trả lời khi có tin tới. Đây là lần đầu bot tự gửi, theo constitution nguyên tắc V và [D-007](../../docs/DECISIONS.md): đồng hồ nằm ở server, tin đi vào cuộc trò chuyện riêng, không phụ thuộc điện thoại có đang mở hay không.

Vòng này là F10 vòng đầu trong [D-024](../../docs/DECISIONS.md) mục 2. Cả hai đường không gọi mô hình. Chữ của digest và chữ của `/next` do cùng một quy tắc dựng. Đầu vào của quy tắc là các kế hoạch đang hoạt động. Quy tắc không nhận thời điểm hiện tại. Việc chưa làm đầu có ngày thì cuối dòng tiêu đề thêm một dấu cách và `(<tên thứ> DD/MM)` dựng từ trường ngày. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không thêm. Tiêu đề đã lưu giữ nguyên từng chữ.

Người dùng là một người, chủ bot, đúng [docs/PRODUCT.md](../../docs/PRODUCT.md) §2 và [D-022](../../docs/DECISIONS.md). Kho kế hoạch không có khái niệm người dùng. Lát này không thêm khái niệm đó.

Tám mục Starter trả ngày 2026-11-07 nằm ở Clarifications. Scenario và yêu cầu bên dưới dùng các đáp án đó.

### User Story 1 - Sáng nào cũng có một tin việc chưa làm (Priority: P1)

Mỗi ngày, lúc 08:00 theo đồng hồ Helsinki, bot gửi một tin vào cuộc trò chuyện riêng với chủ bot. Giờ đó là giờ địa phương: khi Helsinki đổi giờ mùa, mốc gửi vẫn là 08:00 trên đồng hồ đó, không phải một giờ UTC cố định. Ngày của digest là ngày trên lịch Helsinki.

Với mỗi kế hoạch đang hoạt động còn ít nhất một việc `pending`, tin có một đoạn: nguyên văn mục tiêu, xuống dòng, rồi nguyên văn tiêu đề việc `pending` đầu tiên theo thứ tự việc con đã lưu. Kế hoạch không còn việc `pending` không có đoạn. Các đoạn xếp cũ nhất trước, theo thứ tự tạo tăng dần. Việc đã quá hạn mà ngày chỉ nằm trong tiêu đề vẫn được nêu bằng đúng chữ tiêu đề đó. Quy tắc không đọc ngày ra khỏi tiêu đề và không sắp lại theo ngày.

**Why this priority**: Đây là giá trị dùng hằng ngày của F10 vòng đầu. Chưa có tin này thì bot không bao giờ chủ động.

**Independent Test**: Dựng vài kế hoạch với việc `pending`, `done`, và `skipped`. Đặt thời điểm hiện tại là 08:00 một ngày Helsinki, lần lượt ở giờ mùa đông và giờ mùa hè. Chạy lần gửi sáng. Đọc tin chủ bot nhận và đếm lần gọi mô hình. Không cần lệnh `/next`.

**Acceptance Scenarios**:

1. **Given** một kế hoạch đang hoạt động, mục tiêu "Học tiếng Nhật", việc con theo thứ tự "Học hiragana" (`pending`) rồi "Luyện 10 phút mỗi ngày" (`pending`), **When** tới 08:00 giờ Helsinki, **Then** chủ bot nhận đúng chuỗi `Học tiếng Nhật`, xuống dòng, `Học hiragana`. Tin không chứa "Luyện 10 phút mỗi ngày". Mô hình không bị gọi.
2. **Given** cùng kế hoạch nhưng "Học hiragana" là `done` và "Luyện 10 phút mỗi ngày" là `pending`, **When** tới 08:00 giờ Helsinki, **Then** tin là đúng chuỗi `Học tiếng Nhật`, xuống dòng, `Luyện 10 phút mỗi ngày`.
3. **Given** việc đứng trước là `skipped` và việc đứng sau là `pending` với tiêu đề "Luyện 10 phút mỗi ngày", **When** tới 08:00 giờ Helsinki, **Then** tin nêu đúng tiêu đề đó. Việc `skipped` không có đoạn.
4. **Given** tiêu đề việc `pending` đầu tiên là "Nộp báo cáo (thứ Sáu 06/11)", **When** tới 08:00 giờ Helsinki sau ngày ghi trong tiêu đề, **Then** tin giữ nguyên từng ký tự của tiêu đề đó. Quy tắc không bỏ đoạn ngày, không đánh dấu quá hạn, và không đổi thứ tự vì đoạn ngày đó.
5. **Given** kế hoạch "Việc cũ" được tạo trước kế hoạch "Việc mới", cả hai còn một việc `pending` lần lượt là "A1" và "B1", và một kế hoạch thứ ba tạo giữa hai kế hoạch đó nhưng mọi việc đã `done`, **When** tới 08:00 giờ Helsinki, **Then** tin là `Việc cũ`, xuống dòng, `A1`, một dòng trống, `Việc mới`, xuống dòng, `B1`. Kế hoạch không còn việc `pending` không có đoạn. Thứ tự không phải mới nhất trước.
6. **Given** không có kế hoạch nào, hoặc mọi kế hoạch đang hoạt động đều không còn việc `pending`, **When** tới 08:00 giờ Helsinki và kho kế hoạch đọc được, **Then** chủ bot nhận đúng câu `Không còn việc chưa làm.` Mô hình không bị gọi.
7. **Given** Helsinki đang giờ mùa đông, **When** lần gửi sáng chạy, **Then** mốc trên đồng hồ Helsinki là 08:00 của ngày Helsinki đó. **Given** Helsinki đang giờ mùa hè, **When** lần gửi sáng chạy, **Then** mốc vẫn là 08:00 của ngày Helsinki đó, không phải 07:00 hay 09:00 trên đồng hồ Helsinki.
8. **Given** chủ bot không mở cuộc trò chuyện từ hôm trước, **When** tới 08:00 giờ Helsinki, **Then** tin vẫn được gửi vào cuộc trò chuyện riêng. Việc gửi không chờ điện thoại đăng ký lịch.

---

### User Story 2 - Gõ /next để xem lại đúng việc đó (Priority: P1)

Chủ bot gõ `/next` trong cuộc trò chuyện riêng và nhận ngay nội dung do cùng quy tắc dựng, với cùng các kế hoạch. Lệnh này không gọi mô hình. Đây là lệnh cứng đầu tiên: [spec kênh Telegram](../013-telegram-channel/spec.md) đang cho mọi tin chữ, kể cả `/start`, đi vào lượt mô hình. Lát này chỉ tách đúng một lệnh.

`/next` không tiêu thụ và không tạo mốc "digest đã gửi" của ngày Helsinki. Gõ `/next` lúc nào cũng được, kể cả trước hoặc sau digest sáng, và gõ nhiều lần trong một ngày vẫn được trả lời mỗi lần.

**Why this priority**: Chủ bot cần xem lại việc chưa làm mà không chờ 08:00 hôm sau, và không tốn một lượt mô hình.

**Independent Test**: Cùng một bộ kế hoạch, gọi quy tắc dựng một lần cho digest và một lần cho `/next`. So từng ký tự của cả chuỗi, kể cả thứ tự các đoạn. Đếm lần gọi mô hình. Rồi gửi `/start` và một câu chữ thường, xác nhận hai tin đó vẫn đi vào lượt.

**Acceptance Scenarios**:

1. **Given** chủ bot ở cuộc trò chuyện riêng và các kế hoạch đang như User Story 1 scenario 1, **When** chủ bot gửi đúng `/next`, **Then** chủ bot nhận nội dung do cùng quy tắc dựng với digest. Mô hình không bị gọi. Kho kế hoạch không bị ghi.
2. **Given** cùng tình huống, **When** chủ bot gửi `/next` lần thứ hai trong cùng ngày Helsinki, **Then** chủ bot lại nhận nội dung do quy tắc dựng. Lần gõ không làm digest sáng bị nuốt, và không được tính là digest đã gửi.
3. **Given** cùng cuộc trò chuyện, **When** chủ bot gửi `/Next`, `/next `, hoặc ` /NEXT `, **Then** mỗi tin là lệnh cứng. Chủ bot nhận cùng chữ quy tắc dựng. Mô hình không bị gọi.
4. **Given** cùng cuộc trò chuyện, **When** chủ bot gửi `/start`, `/next@bot`, hoặc `/next hôm nay`, **Then** tin đó đi vào lượt mô hình như một tin chữ, đúng [spec kênh Telegram](../013-telegram-channel/spec.md).
5. **Given** secret đúng và người gửi không phải chủ bot, hoặc tin ở nhóm, **When** tin chữ là `/next`, **Then** tin bị bỏ qua theo spec 013. Không có câu trả lời, không gọi mô hình, không đọc quy tắc dựng cho người đó.
6. **Given** một update `/next` đã gửi xong, **When** cùng mã update tới lại, **Then** không gửi thêm và không gọi mô hình.
7. **Given** update `/next` đã có chữ dựng xong nhưng chưa gửi xong, **When** cùng mã update tới lại, **Then** chủ bot nhận lại đúng chữ đó. Mô hình không bị gọi. Chữ không được dựng lại từ kế hoạch đã đổi sau lần đầu.
8. **Given** chủ bot gửi `/next` và chữ trả lời đã dựng, **When** kênh sắp gửi, **Then** ngữ cảnh đã có tin chữ gốc của chủ bot, rồi câu trả lời bằng chuỗi đầy đủ, trước khi gửi. Ghi một trong hai tin đó lỗi thì không gửi, người gọi bị hoãn, mô hình không bị gọi.
9. **Given** không có đoạn nào, **When** chủ bot gửi `/next`, **Then** chủ bot nhận đúng câu `Không còn việc chưa làm.` Mô hình không bị gọi. Ngày Helsinki không thành đã gửi.

---

### User Story 3 - Hai đường không lệch chữ (Priority: P1)

Digest và `/next` dùng một quy tắc. Không có bản chữ thứ hai viết riêng cho từng đường. Quy tắc nhận các kế hoạch đang hoạt động. Quy tắc không nhận thời điểm hiện tại. Việc chưa làm đầu có ngày thì cuối dòng tiêu đề thêm một dấu cách và `(<tên thứ> DD/MM)` dựng từ trường ngày. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không thêm. Tiêu đề đã lưu giữ nguyên từng chữ.

**Why this priority**: Hai đường lệch nhau thì chủ bot không biết tin sáng và lệnh `/next` cái nào đúng.

**Independent Test**: Gọi quy tắc hai lần với cùng các kế hoạch. So chữ. Không mở kênh và không gọi mô hình.

**Acceptance Scenarios**:

1. **Given** một bộ kế hoạch cố định, **When** gọi quy tắc ở hai thời điểm khác nhau, **Then** hai kết quả cùng chữ. Việc chưa làm đầu có ngày thì cuối dòng tiêu đề có đoạn `(<tên thứ> DD/MM)` dựng từ trường ngày. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì không có đoạn đó. Tiêu đề đã lưu giữ nguyên từng chữ.
2. **Given** cùng bộ kế hoạch, **When** lấy chữ bằng đường digest và bằng đường `/next`, **Then** hai chữ là cùng một chuỗi, kể cả thứ tự các đoạn. Khác đường không được thêm lời chào, lời kết, hay một việc khác.

---

### User Story 4 - Trả lời "xong việc đầu" ngay sau digest (Priority: P1)

Digest là tin bot gửi. Trước khi gửi, cả tin được ghi vào ngữ cảnh hội thoại của cuộc trò chuyện riêng, là một tin của bot. Ghi ngữ cảnh lỗi thì không gửi và không ghi mốc ngày, theo [D-022](../../docs/DECISIONS.md). Nhờ đó tin chữ ngay sau của chủ bot đi vào lượt và lượt nhìn thấy digest.

Tin `/next` của chủ bot và câu trả lời cũng vào ngữ cảnh trước khi gửi, tin của chủ bot rồi câu trả lời. Ghi một trong hai tin đó lỗi thì không gửi và hoãn người gọi, như spec 013. Bản ghi update vẫn giữ luật một update một lần.

Digest không được ghép với một tin giả của chủ bot. Trong ngữ cảnh, cả digest và cả câu trả lời `/next` đều là một tin của bot dù kênh có tách lúc gửi. Trần 20 tin và tuổi 24 giờ của spec 013 áp cho các tin này sau khi đã ghi.

**Why this priority**: Không có bước này thì câu "xong việc đầu" ngay sau tin sáng không còn trỏ vào việc vừa nêu.

**Independent Test**: Ghi ngữ cảnh giả. Chạy lần gửi sáng thành công. Đọc ngữ cảnh trước khi tin được phát đi. Rồi đưa một tin chữ của chủ bot và đọc đầu vào lượt mô hình. Một ca riêng: lần ghi ngữ cảnh thất bại. Đếm tin đã phát.

**Acceptance Scenarios**:

1. **Given** digest đã dựng xong và chưa gửi, **When** lần gửi sáng chạy, **Then** ngữ cảnh có đúng một tin của bot bằng nguyên văn digest đó trước khi chủ bot nhận tin. Không có tin giả của chủ bot đi kèm.
2. **Given** digest đã nằm trong ngữ cảnh và chưa quá 24 giờ, còn trong 20 tin, **When** chủ bot gửi "xong việc đầu", **Then** tin "xong việc đầu" đi vào lượt mô hình, và lượt nhận digest như một tin của bot đứng trước. Lượt này là đường tin chữ của spec 013, không phải đường `/next`.
3. **Given** việc ghi ngữ cảnh của digest thất bại, **When** lần gửi sáng chạy, **Then** chủ bot không nhận digest. Mô hình không bị gọi. Ngày Helsinki đó không thành đã gửi.
4. **Given** digest hoặc câu trả lời `/next` dài hơn một tin của kênh, **When** gửi, **Then** các phần theo luật tách của spec 013, ghép lại đúng chuỗi gốc. **When** đọc ngữ cảnh sau khi ghi thành công, **Then** chuỗi đó là một tin của bot, không phải từng phần.

---

### User Story 5 - Chạy lại trong ngày không gửi digest thứ hai (Priority: P1)

Mốc "đã gửi" của một ngày Helsinki được ghi sau khi kênh xác nhận đã gửi cả tin. Mốc nằm ở kho bền, không nằm trong bộ nhớ giữa hai lần chạy (constitution nguyên tắc II). Khi kênh đã xác nhận, lần chạy sau trong ngày đó không gửi thêm.

Gửi lỗi hoặc kết quả không rõ thì ngày đó chưa gửi, và lần chạy sau trong cùng ngày thử lại. Ghi ngữ cảnh lỗi thì không gửi, không ghi mốc, lần sau thử lại. Lần thử lại không ghi ngữ cảnh lần hai nếu digest đó đã được ghi; lần đó gửi đúng chữ đã ghi. Khi kết quả gửi không rõ, digest có thể tới hơn một lần, kể cả một phần đã tới rồi xuất hiện lần nữa, cùng cách spec 013 đã chấp nhận.

`/next` không đọc và không ghi mốc này.

**Why this priority**: Cron chạy lại sau một lần đã xác nhận không được biến một buổi sáng thành hai tin. Lần gửi chưa rõ kết quả vẫn phải thử lại, vì im lặng không cho biết bot hỏng hay chưa gửi.

**Independent Test**: Xác nhận gửi xong một ngày Helsinki, rồi chạy lần nữa. Rồi một lần gửi lỗi, một lần kết quả không rõ, và một lần ghi ngữ cảnh lỗi. Với ca đã ghi ngữ cảnh mà chưa xác nhận, chạy lần sau và đếm tin ngữ cảnh. Hai lần chạy không chung bộ nhớ tiến trình.

**Acceptance Scenarios**:

1. **Given** kênh đã xác nhận digest của ngày Helsinki D, **When** lần chạy khác trong ngày D diễn ra, **Then** không có digest thứ hai và không có tin ngữ cảnh thứ hai cho digest đó. Mô hình không bị gọi.
2. **Given** lần gửi của ngày D lỗi hoặc kết quả không rõ, và ngữ cảnh đã có chữ digest đó, **When** lần chạy sau trong ngày D diễn ra, **Then** ngày D vẫn chưa được đánh dấu đã gửi. Lần sau gửi đúng chữ đã ghi và không ghi thêm tin ngữ cảnh. Chủ bot có thể nhận digest đó hơn một lần, kể cả một phần đã tới rồi xuất hiện lần nữa.
3. **Given** ghi ngữ cảnh của digest ngày D lỗi và chưa có chữ đó trong ngữ cảnh, **When** lần chạy sau trong ngày D đọc được các kế hoạch, **Then** lần sau ghi đúng một tin ngữ cảnh rồi gửi. Mốc chưa được ghi ở lần lỗi.
4. **Given** kênh đã xác nhận digest của ngày D, **When** sang 08:00 ngày Helsinki D+1, **Then** chủ bot nhận được digest của ngày D+1. Mốc của ngày D không chặn ngày sau.
5. **Given** chủ bot đã gõ `/next` nhiều lần trong ngày D và chưa có digest sáng được xác nhận, **When** tới 08:00 ngày D, **Then** digest sáng vẫn được gửi. Các lần `/next` không làm ngày D thành đã gửi.

---

### Edge Cases

- Kế hoạch đang hoạt động lấy đúng nghĩa đã chốt: đã lưu và chưa bị đưa ra khỏi danh sách ([spec tạo và liệt kê](../001-create-list-plans/spec.md)); mọi việc `done`, mọi việc `skipped`, hoặc lẫn hai mã, kế hoạch vẫn đang hoạt động ([spec cập nhật việc con](../003-update-subtask/spec.md), [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md)). Có mặt trong kho là đang hoạt động ([spec kho kế hoạch](../006-supabase-plan-store/spec.md)). Lát này không thêm trạng thái "đóng kế hoạch".
- Kế hoạch đang hoạt động mà không có việc `pending` (danh sách việc con rỗng, hoặc chỉ `done` và `skipped`) không có đoạn trong tin. Kế hoạch đó vẫn đang hoạt động.
- Khi không có đoạn nào, cả digest và `/next` là đúng câu `Không còn việc chưa làm.` Câu đó là cả tin. Kho đọc được mới ra câu này. Không đọc được kho thì không dựng câu này và không đánh dấu đã gửi.
- Việc chưa làm là việc `pending` đầu tiên theo thứ tự đã lưu. `done` và `skipped` bị bước qua. Ghi chú không được đưa vào như một phần riêng. Mã kế hoạch và mã việc con không có trong tin.
- Hai kế hoạch trùng mục tiêu đều có đoạn nếu mỗi kế hoạch còn việc `pending`. Chúng không bị gộp. Đoạn của kế hoạch có thứ tự tạo nhỏ hơn đứng trước.
- Lệnh cứng là tin chữ của chủ bot ở cuộc trò chuyện riêng mà sau khi cắt khoảng trắng hai đầu, không phân biệt hoa thường, bằng `/next`. `/Next` và `/next ` là lệnh. `/next@bot`, `/next hôm nay`, `/start`, và mọi tin chữ khác đi vào lượt.
- Tin `/next` của người không phải chủ bot, hoặc không ở cuộc trò chuyện riêng, bị bỏ qua theo spec 013.
- Digest không sửa kế hoạch, không đổi trạng thái việc con, và không gọi tool lập kế hoạch. Hạn chờ của một lượt mô hình trong [D-021](../../docs/DECISIONS.md) không phải ngân sách của hai đường này, vì hai đường không mở lượt. F10 không sửa lượt mô hình và không đổi `PROMPT_VERSION`.
- Không đọc được các kế hoạch thì không dựng tin, không gọi mô hình, và không coi ngày Helsinki đó là đã gửi. `/next` trong trường hợp đó không trả một danh sách bịa; update bị hoãn theo kiểu spec 013 để lần gửi lại còn xử lý, và lần gửi lại vẫn không gọi mô hình.
- Ghi ngữ cảnh digest lỗi thì không gửi và không ghi mốc. Gửi kênh lỗi hoặc kết quả không rõ thì không ghi mốc. Lần chạy sau trong cùng ngày thử lại. Nếu chữ digest đã nằm trong ngữ cảnh, lần thử lại gửi đúng chữ đó và không ghi tin ngữ cảnh lần hai.
- Tin dài hơn một tin của kênh, ở digest và ở câu trả lời `/next`, tách theo spec 013. Ngữ cảnh giữ chuỗi đầy đủ thành một tin bot. Xác nhận gửi là cho cả tin. Đứt sau một phần có thể làm phần đó tới lần nữa. Đã xác nhận thì không gửi thêm trong ngày.
- Tin `/next` của chủ bot và câu trả lời đều vào ngữ cảnh trước khi gửi. Ghi lỗi thì hoãn như spec 013, không gửi. Lần gửi lại của cùng update không ghi đè hai tin đó.
- Cùng một update `/next` chỉ được xử lý một lần theo spec 013. Đã gửi xong thì không gửi thêm. Đã có chữ mà chưa gửi xong thì gửi lại đúng chữ đó, không gọi mô hình và không dựng lại. Chưa dựng được vì không đọc được kế hoạch thì lần sau vẫn không gọi mô hình.
- Hai lần chạy digest không chung bộ nhớ vẫn thấy cùng mốc ngày, vì mốc nằm ở kho bền. Khi chưa có xác nhận, hai lần chạy có thể làm digest tới hơn một lần.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mỗi ngày, lúc 08:00 theo đồng hồ Helsinki, khi ngày đó chưa được xác nhận đã gửi, hệ thống MUST gửi một digest vào cuộc trò chuyện riêng với chủ bot. Mốc MUST là 08:00 giờ địa phương Helsinki cả khi Helsinki đổi giờ mùa. Ngày của digest MUST là ngày trên lịch Helsinki. Việc gửi MUST NOT phụ thuộc điện thoại có đang mở hay có tự đặt lịch.
- **FR-002**: Digest và câu trả lời `/next` MUST được dựng bằng cùng một quy tắc. Đầu vào MUST là các kế hoạch đang hoạt động. Quy tắc MUST NOT gọi mô hình. Quy tắc MUST NOT nhận thời điểm hiện tại. Việc chưa làm đầu có ngày thì cuối dòng tiêu đề MUST thêm một dấu cách và `(<tên thứ> DD/MM)` dựng từ trường ngày. Không năm, không múi giờ, không chữ quá hạn. Không ngày thì MUST NOT thêm đoạn đó. Tiêu đề đã lưu MUST giữ nguyên từng chữ. Hai lần gọi với cùng các kế hoạch MUST ra cùng một chuỗi. Các đoạn MUST xếp theo thứ tự tạo (`created_order`) tăng dần: kế hoạch tạo trước đứng trước.
- **FR-003**: Nghĩa "đang hoạt động" MUST giữ nguyên theo [spec tạo và liệt kê](../001-create-list-plans/spec.md) và [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Kế hoạch không còn việc `pending` MUST vẫn đang hoạt động và MUST NOT có đoạn trong tin. Lát này MUST NOT thêm cách đóng kế hoạch.
- **FR-004**: Với mỗi kế hoạch đang hoạt động còn ít nhất một việc `pending`, đoạn của kế hoạch đó MUST là nguyên văn mục tiêu đã lưu, xuống dòng, rồi nguyên văn tiêu đề của việc `pending` đầu tiên theo thứ tự đã lưu. Tiêu đề việc `done`, tiêu đề việc `skipped`, và tiêu đề các việc `pending` đứng sau MUST NOT được thêm vào. Ngày chỉ nằm trong tiêu đề MUST được giữ nguyên từng ký tự.
- **FR-005**: Khi không có đoạn nào, vì không có kế hoạch đang hoạt động hoặc không kế hoạch nào còn việc `pending`, cả digest và câu trả lời `/next` MUST là đúng câu `Không còn việc chưa làm.` Câu đó MUST là cả tin. Khi đã có ít nhất một đoạn, quy tắc MUST NOT thêm câu đó.
- **FR-006**: Khi có từ hai đoạn, các đoạn MUST cách nhau bằng một dòng trống. Tin MUST NOT có lời chào, lời kết, mã kế hoạch, mã việc con, tên trạng thái, hay ghi chú được thêm riêng. Dấu sao, gạch dưới, và dấu backtick trong mục tiêu hoặc tiêu đề MUST được giữ là ký tự.
- **FR-007**: Chủ bot MUST nhận được nội dung của quy tắc khi gửi một lệnh `/next` trong cuộc trò chuyện riêng. Câu trả lời MUST đi ngay bằng quy tắc đó, MUST NOT gọi mô hình, và MUST NOT ghi kho kế hoạch. `/next` MUST NOT tạo hay xóa mốc digest của ngày Helsinki.
- **FR-008**: Lệnh cứng MUST là tin chữ mà sau khi cắt khoảng trắng hai đầu, không phân biệt hoa thường, bằng `/next`. `/Next` và `/next ` MUST là lệnh đó. `/start`, `/next@bot`, `/next hôm nay`, và mọi tin chữ còn lại MUST đi vào lượt mô hình đúng spec 013. Tin của người không phải chủ bot, hoặc không ở cuộc trò chuyện riêng, MUST bị bỏ qua đúng spec 013 dù chữ có khớp lệnh.
- **FR-009**: Một update là lệnh `/next` MUST chỉ được xử lý một lần theo spec 013 và MUST NOT gọi mô hình. Update đã gửi xong MUST NOT gửi thêm. Update đã có chữ mà chưa gửi xong MUST gửi lại đúng chữ đã dựng, MUST NOT dựng lại từ kế hoạch đã đổi.
- **FR-010**: Trước khi digest được gửi, hệ thống MUST ghi nguyên văn digest vào ngữ cảnh cuộc trò chuyện riêng như một tin của bot. Ghi lỗi thì MUST NOT gửi và MUST NOT ghi mốc ngày. Digest MUST NOT được kèm một tin giả của chủ bot. Sau khi ghi, tin này MUST chịu trần 20 tin và tuổi 24 giờ của spec 013. Trong ngữ cảnh, digest MUST là một tin, bằng chuỗi đầy đủ, kể cả khi kênh tách lúc gửi.
- **FR-011**: Sau khi digest đã nằm trong ngữ cảnh còn hiệu lực, tin chữ tiếp theo của chủ bot MUST đi vào lượt mô hình của spec 013, và lượt đó MUST nhận digest như một tin của bot đứng trước.
- **FR-012**: Mốc "đã gửi" của một ngày Helsinki MUST được ghi chỉ sau khi kênh xác nhận đã gửi cả tin, và MUST còn sau khi hai lần chạy không chung bộ nhớ. Gửi lỗi hoặc kết quả không rõ MUST NOT ghi mốc, và lần chạy sau trong cùng ngày Helsinki MUST thử lại. Ghi ngữ cảnh lỗi MUST NOT gửi và MUST NOT ghi mốc; lần sau MUST thử lại. Lần thử lại MUST NOT ghi ngữ cảnh lần hai nếu chữ digest đó đã được ghi, và MUST gửi đúng chữ đã ghi. Khi kết quả gửi không rõ, digest có thể tới hơn một lần, kể cả một phần đã tới rồi xuất hiện lần nữa, cùng cách spec 013. Khi kênh đã xác nhận, lần chạy sau trong ngày MUST NOT gửi thêm và MUST NOT thêm tin ngữ cảnh thứ hai. Mốc của ngày D MUST NOT chặn digest của ngày Helsinki D+1.
- **FR-013**: Không đọc được các kế hoạch thì hệ thống MUST NOT dựng tin, MUST NOT gọi mô hình, và MUST NOT đánh dấu ngày Helsinki đó là đã gửi. Với `/next`, update đó MUST bị hoãn theo spec 013 và lần sau MUST NOT gọi mô hình.
- **FR-014**: Hai đường MUST NOT sửa kế hoạch hay việc con. Hai đường MUST NOT mở một lượt mô hình. Lát này MUST NOT sửa lượt mô hình và MUST NOT đổi `PROMPT_VERSION`. Nội dung người dùng thấy MUST là lời của JARVIS, đúng constitution nguyên tắc I.
- **FR-015**: Trước khi câu trả lời `/next` được gửi, hệ thống MUST ghi tin chữ gốc của chủ bot, rồi câu trả lời bằng chuỗi đầy đủ, vào ngữ cảnh. Ghi một trong hai tin lỗi thì MUST NOT gửi và MUST hoãn người gọi như spec 013. Lần gửi lại của cùng update MUST NOT ghi đè hai tin đó. Hai tin MUST chịu trần 20 tin và tuổi 24 giờ của spec 013.
- **FR-016**: Digest và câu trả lời `/next` dài hơn một tin của kênh MUST được tách theo luật spec 013: mỗi phần từ 1 đến 4096 đơn vị UTF-16, không cắt giữa một code point, ghép các phần theo thứ tự gửi ra đúng chuỗi gốc. Xác nhận gửi MUST là cho cả chuỗi.

### Key Entities

- **Quy tắc dựng nội dung**: Một cách dựng duy nhất cho digest và `/next`. Nhận các kế hoạch đang hoạt động. Trả một đoạn cho mỗi kế hoạch còn việc `pending`, xếp theo thứ tự tạo tăng dần. Không còn đoạn nào thì trả đúng câu `Không còn việc chưa làm.` Không gọi mô hình.
- **Kế hoạch đang hoạt động**: Đúng thực thể ở spec 001, spec 003, spec 005, và spec 006, gồm thứ tự tạo (`created_order`). Lát này không thêm thuộc tính và không thêm cách đóng.
- **Việc chưa làm**: Việc con `pending` đứng sớm nhất trong thứ tự đã lưu của một kế hoạch. `done` và `skipped` không phải việc chưa làm. Tiêu đề giữ nguyên.
- **Digest của một ngày Helsinki**: Tin bot tự gửi lúc 08:00 giờ Helsinki của ngày đó. Mốc "đã gửi" ghi sau khi kênh xác nhận cả tin, và nằm ở kho bền. Chưa xác nhận thì lần chạy sau trong ngày thử lại.
- **Lệnh `/next`**: Tin chữ của chủ bot ở cuộc trò chuyện riêng, sau khi cắt khoảng trắng hai đầu và không phân biệt hoa thường thì bằng `/next`. Không phải một lượt mô hình. Không phải mốc digest. Tin gốc và câu trả lời đều là tin ngữ cảnh.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần tới 08:00 giờ Helsinki, khi đọc được các kế hoạch và ngày đó chưa được xác nhận đã gửi, chủ bot nhận một digest ở cuộc trò chuyện riêng. 100% các lần đó có 0 lời gọi mô hình. Mốc trên đồng hồ Helsinki là 08:00 cả ngày giờ mùa đông và ngày giờ mùa hè. 100% lần không có đoạn nào, chủ bot nhận đúng câu `Không còn việc chưa làm.`
- **SC-002**: 100% kế hoạch đang hoạt động còn việc `pending` xuất hiện đúng một đoạn, với nguyên văn mục tiêu và nguyên văn tiêu đề việc `pending` đầu tiên, xếp theo thứ tự tạo tăng dần. 0 đoạn cho kế hoạch không còn việc `pending`. 0 tiêu đề của việc không phải việc `pending` đầu tiên bị thêm vào. 100% tin không có đoạn nào là đúng câu `Không còn việc chưa làm.`
- **SC-003**: 100% lần chủ bot gửi lệnh `/next` ở cuộc trò chuyện riêng, kể cả `/Next` và `/next ` sau khi cắt khoảng trắng, nhận cùng chữ mà quy tắc dựng cho digest, với 0 lời gọi mô hình và 0 lần ghi kho kế hoạch. 100% tin `/start`, `/next@bot`, và `/next hôm nay` vẫn đi vào lượt như spec 013.
- **SC-004**: 100% digest đã gửi có mặt trong ngữ cảnh như một tin của bot, nguyên văn, trước lúc gửi. 100% câu trả lời `/next` và tin chữ gốc của chủ bot có mặt trong ngữ cảnh trước lúc gửi. 100% lần ghi ngữ cảnh thất bại có 0 tin gửi. 100% tin chữ của chủ bot ngay sau digest còn hiệu lực được lượt nhìn thấy với digest đứng trước.
- **SC-005**: 100% lần kênh đã xác nhận digest của một ngày Helsinki thì lần chạy sau trong ngày đó gửi 0 digest thêm. 100% lần gửi lỗi, kết quả không rõ, hoặc ghi ngữ cảnh lỗi không ghi mốc, và lần chạy sau trong ngày thử lại. 100% lần thử lại khi chữ đã có trong ngữ cảnh gửi đúng chữ đó và ghi 0 tin ngữ cảnh thêm. Khi kết quả không rõ, digest có thể tới hơn một lần. 100% lần sang ngày Helsinki sau vẫn gửi được digest mới. 100% lần `/next` không làm một ngày thành đã gửi.
- **SC-006**: 100% cặp lần gọi quy tắc trên cùng các kế hoạch ra cùng một chuỗi, kể cả thứ tự tạo tăng dần, ở mọi thời điểm. 100% chuỗi đó không chứa ngày, thứ, hay múi giờ do quy tắc thêm vào.

## Assumptions

- Câu `Không còn việc chưa làm.` đã được Starter duyệt. Câu đó là cả tin khi không có đoạn nào, cho cả digest và `/next`. Câu đó không gắn vào từng kế hoạch.
- Cách xếp đoạn đã được Starter duyệt: nguyên văn mục tiêu, xuống dòng, rồi tiêu đề việc `pending` đầu tiên. Từ hai đoạn trở lên, các đoạn cách nhau bằng một dòng trống. Không lời chào và không lời kết. Hai đường dùng cùng cách xếp này.
- Chữ gửi lại của cùng một update `/next` là chữ đã dựng lần đầu cho update đó. `/next` không tạo kế hoạch, nhưng gửi lại một bản khác khi kế hoạch vừa đổi sẽ làm cùng một update có hai nội dung.
- Không đọc được kế hoạch thì chưa gửi, nên chưa đánh dấu đã gửi. Đây khác với kho đọc được mà không có đoạn nào: trường hợp đó vẫn gửi đúng câu `Không còn việc chưa làm.`
- Thứ tự liệt kê của spec 001 là kế hoạch tạo sau đứng trước. Thứ tự các đoạn trong tin là thứ tự tạo tăng dần, kế hoạch tạo trước đứng trước.
- Đồng hồ giờ Helsinki đã được kiểm trên môi trường dev ở nhánh `spike/zoneinfo-pyodide`: sáu mốc năm 2026 cho độ lệch 2, 3, 2, 3, 3, 2. Chưa kiểm trên Worker đã deploy. Lát này không biến sáu mốc đó thành bài kiểm mới, và không coi khoảng trống trên Worker đã deploy là đã đóng.
- Nếu lát này thêm lời gọi kho cho mốc "đã gửi", lời gọi đó theo [D-023](../../docs/DECISIONS.md): phản hồi có giá trị, không rỗng. Hình lưu của mốc thuộc bước plan. Bước specify không viết migration.
- [D-021](../../docs/DECISIONS.md) bắt mọi nơi gọi tool trong một lượt, kể cả scheduler F10 sau này, truyền phần ngân sách còn lại. Vòng này không gọi tool và không mở lượt, nên không đưa ngân sách đó vào hai đường digest và `/next`.
- Bước specify không sửa `src/`, `tests/`, `supabase/`, và không sửa `docs/`. Không sửa các file spec cũ. Spec 013 vẫn là biên bản của đường tin chữ; lát này chỉ thêm một ngoại lệ cho lệnh `/next`, ghi ở spec này.
- Ngoài phạm vi, theo mô tả tính năng và [D-024](../../docs/DECISIONS.md):
  - Ngày, ưu tiên, và sức trên kế hoạch hoặc việc con (F17 mở rộng).
  - `/today`, nhắc theo giờ, và tin buổi tối.
  - Việc hằng ngày, sự kiện, quét tải, form, và lịch.
  - Đọc ngày trong tiêu đề để lọc, sắp, hoặc báo quá hạn. Tiêu đề chỉ được chép nguyên văn.
  - Sửa lượt mô hình và đổi `PROMPT_VERSION`. Đưa ngày hôm nay, thứ, và múi giờ Helsinki cho mô hình thuộc F17 mở rộng.
  - Kiểm đồng hồ trên Worker đã deploy, đăng ký lịch chạy thật, và deploy.

## Đã chốt

Tám mục Starter trả ngày 2026-11-07 đã ghi ở Clarifications và đã sửa vào User Story, Edge Cases, FR-002 đến FR-016, SC-001 đến SC-006, Key Entities, và Assumptions. Không còn câu chưa chọn trong tám mục đó.

1. Kế hoạch không còn việc `pending` không có đoạn trong tin.
2. Các đoạn xếp cũ nhất trước, thứ tự tạo tăng dần.
3. Không có đoạn nào thì cả digest và `/next` là đúng câu `Không còn việc chưa làm.`
4. Mốc "đã gửi" ghi sau khi kênh xác nhận. Gửi lỗi, kết quả không rõ, hoặc ghi ngữ cảnh lỗi thì chưa gửi và lần sau trong ngày thử lại. Thử lại không ghi ngữ cảnh lần hai nếu đã ghi. Digest có thể lặp khi kết quả không rõ.
5. Tin `/next` của chủ bot và câu trả lời vào ngữ cảnh trước khi gửi. Ghi lỗi thì hoãn như spec 013.
6. Tin dài dùng luật tách của spec 013. Ngữ cảnh vẫn là một tin bot bằng chuỗi đầy đủ.
7. Đưa ngày hôm nay cho mô hình để F17. F10 không sửa lượt mô hình và không đổi `PROMPT_VERSION`.
8. Lệnh cứng là tin chữ, sau khi cắt khoảng trắng hai đầu và không phân biệt hoa thường, bằng `/next`. `/next@bot`, `/next hôm nay`, và `/start` vẫn đi vào mô hình.

Câu `Không còn việc chưa làm.` và cách xếp đoạn đã được duyệt cùng tám mục trên.
