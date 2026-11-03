# Feature Specification: Độ bền ghi

**Feature Branch**: `012-write-durability`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Độ bền ghi cho jarvis-compass: việc ghi kế hoạch vào kho không treo, không mất cập nhật và không báo sai. Review repo 2026-11-01 (docs/reviews/2026-11-01-repo-review.md) có ba mục mở cho tính năng này. L1-01: lời gọi kho dùng giới hạn chờ mặc định rất dài, trong khi một lượt có ngân sách 20 giây, nên một lời gọi kho treo làm lượt vượt ngân sách. L1-02: các tool đổi việc con đọc kế hoạch rồi ghi lại cả kế hoạch bằng hai lời gọi riêng, không khóa, không version, nên hai lượt chạy chồng nhau làm lượt ghi sau xóa thay đổi của lượt ghi trước, kể cả việc con vừa thêm. L1-03: khi tool ghi đã thành công mà lượt hết giờ, mô hình lỗi, chạm trần ba vòng hoặc câu trả lời bị cắt hay bị từ chối, người dùng nhận câu lỗi chung dù thay đổi đã lưu, rồi gửi lại và có thể tạo kế hoạch trùng. Hành vi cần có: (1) mỗi lời gọi kho có giới hạn thời gian nằm trong ngân sách 20 giây của lượt; quá giới hạn thì lời gọi bị bỏ và tool trả lỗi thay vì treo. Lời gọi ghi quá giờ không biết đã lưu hay chưa, nên câu trả lời không khẳng định đã lưu hay chưa lưu mà nói là chưa chắc. (2) Hai lượt đổi cùng một kế hoạch không bao giờ làm mất thay đổi của nhau trong im lặng: thay đổi hoặc được áp dụng đầy đủ, hoặc bị từ chối kèm thông báo để người dùng thử lại, không để kế hoạch nửa vời. (3) Khi ít nhất một tool ghi đã thành công trong lượt mà lượt không kết thúc bình thường, câu trả lời nói rõ những gì đã lưu thay vì câu lỗi chung. Câu trả lời vẫn theo docs/PRODUCT.md §9: chữ trơn, không hiện mã, trạng thái gọi là chưa làm, xong, bỏ qua; lượt vẫn trả một chuỗi. Ngoài phạm vi: câu trả lời khi mô hình bị cắt, từ chối hoặc trả rỗng mà chưa ghi gì (phần còn lại của L1-04, để cho F11); chống tạo trùng khi Telegram gửi lại webhook (F11); L1-05 và L1-06; không đổi system prompt, PROMPT_VERSION, tool definitions, DEFINITIONS_VERSION, bộ câu eval, bộ chấm; không thêm trường ngày (F17); không thêm tool mới. Cách làm để cho bước plan. Test đang khóa hành vi cũ chỉ đổi khi chạm đúng ba hành vi trên. Kiểm được trên máy bằng kho giả trong tests/fakes và kho Supabase local. Không sửa docs/ ở bước specify."

## Clarifications

### Session 2026-11-03

- Q: Hai lần ghi trên cùng một kế hoạch được tính là chạy chồng từ thời điểm nào? → A: Khi khoảng thời gian của chúng giao nhau. Mỗi khoảng tính từ lúc tool bắt đầu đọc kế hoạch tới lúc tool trả về, kể cả khi hai lời gọi ghi không chồng nhau.
- Q: Văn bản rỗng hoặc chỉ khoảng trắng sau một lần ghi thành công có phải kết thúc bình thường không? → A: Không, và cũng không khi lượt có lần ghi bị bỏ hoặc lần ghi bị từ chối. Nếu có ít nhất một trong ba thứ đó, chuỗi trả là bản ghép như FR-008 và FR-010. Nếu không có cả ba, văn bản rỗng vẫn là chuỗi rỗng và văn bản chỉ khoảng trắng vẫn là đúng văn bản đó. Văn bản còn chữ khác khoảng trắng vẫn là câu của mô hình.
- Q: Vì sao văn bản rỗng hoặc chỉ khoảng trắng cũng ghép khi chỉ có lần ghi bị bỏ hoặc lần ghi bị từ chối? → A: B9 G16. Ca lần ghi bị bỏ rồi mô hình trả rỗng đang trả chuỗi rỗng, trong khi cùng tình huống mà mô hình bị cắt thì trả câu chưa chắc. Hai lối kết cùng tình huống phải cho cùng một kiểu câu.

## User Scenarios & Testing *(mandatory)*

Người dùng nhờ JARVIS ghi một kế hoạch hoặc sửa một việc. Việc ghi phải xong trong ngân sách của lượt, không bị một lượt khác xóa mất trong im lặng, và khi lượt không nói được câu bình thường thì người dùng vẫn biết những gì đã nằm trong kho. Ba mục mở L1-01, L1-02, và L1-03 trong [review 2026-11-01](../../docs/reviews/2026-11-01-repo-review.md) là lý do của lát này. Lượt, ngân sách 20 giây, trần ba vòng, và hai câu lỗi do dự án viết đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Sáu tool và câu lỗi tool đã chốt ở [spec điều phối tool](../007-plan-tool-router/spec.md).

Lần ghi là một lần chạy `create_plan`, `add_subtask`, `update_subtask`, hoặc `set_subtask_note`. Lần ghi thành công là lần tool đó trả thành công. Lần đọc là `get_plans` hoặc `get_plan_detail`. Lát này không thêm tool.

### User Story 1 - Lời gọi kho quá giờ thì bỏ, lần ghi không nói chắc (Priority: P1)

Mỗi lời gọi kho có một giới hạn thời gian không dài hơn phần còn lại của ngân sách 20 giây của lượt. Quá giới hạn thì lời gọi đó bị bỏ. Tool trả lỗi và không treo. Lượt không vượt 20 giây vì một lời gọi kho chưa trả về. Lần ghi bị bỏ không biết thay đổi đã vào kho hay chưa, nên câu của tool là đúng `Chưa chắc thay đổi đã được lưu.` Câu đó nói chưa chắc: không kết luận đã lưu, cũng không kết luận chưa lưu.

**Why this priority**: Một lời gọi kho treo làm cả lượt vượt ngân sách. Người dùng chờ mãi rồi gửi lại. Với lần ghi, nói "đã lưu" hoặc "chưa lưu" đều có thể sai.

**Independent Test**: Kho giả không trả về cho một lời gọi. Đo thời gian lượt. Với lần ghi, đọc câu tool trả. Với lần đọc, đọc câu tool trả. Không mở mạng ở ca kho giả.

**Acceptance Scenarios**:

1. **Given** một lượt còn ngân sách và kho không trả về cho lời gọi kho của một lần ghi, **When** quá giới hạn của lời gọi đó, **Then** lời gọi bị bỏ, tool trả lỗi với đúng `Chưa chắc thay đổi đã được lưu.`, và lượt không vượt 20 giây.
2. **Given** một lượt còn ngân sách và kho không trả về cho lời gọi kho của `get_plans` hoặc `get_plan_detail`, **When** quá giới hạn của lời gọi đó, **Then** lời gọi bị bỏ, tool trả lỗi với đúng `Không thực hiện được yêu cầu này.`, và câu đó không phải `Chưa chắc thay đổi đã được lưu.`
3. **Given** một tool định đọc kế hoạch rồi ghi lại, và lời gọi đọc quá giới hạn, **When** tool chạy, **Then** tool trả lỗi của lần đọc và không gửi lời gọi ghi nào sau đó trong cùng tool.
4. **Given** lời gọi đọc của tool đó đã trả về, và lời gọi ghi sau đó quá giới hạn, **When** tool chạy, **Then** tool trả đúng `Chưa chắc thay đổi đã được lưu.`
5. **Given** một lời gọi kho trả về trước giới hạn của nó, **When** tool ghi chạy xong, **Then** kết quả thành công của tool giống hành vi đã chốt ở spec của tool đó. Lát này không đổi câu thành công đó.

---

### User Story 2 - Hai lượt đổi cùng một kế hoạch không xóa nhau trong im lặng (Priority: P1)

Hai lượt cùng sửa một kế hoạch. Hai lần ghi trên cùng một kế hoạch chạy chồng khi khoảng thời gian của chúng giao nhau. Mỗi khoảng tính từ lúc tool bắt đầu đọc kế hoạch tới lúc tool trả về. Hai lời gọi ghi không cần chồng nhau: lần A có thể đọc, lần B đọc, lần A ghi xong và trả về, rồi lần B mới ghi. Mỗi thay đổi hoặc được áp dụng đầy đủ và tool báo thành công, hoặc bị từ chối. Từ chối thì tool trả đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` và lần ghi đó không thêm, không bớt, không sửa gì trên kế hoạch. Kế hoạch không ở trạng thái nửa vời: không vừa nhận một phần của thay đổi này vừa mất một phần của thay đổi kia. Việc con một lượt vừa thêm không biến mất chỉ vì lượt kia ghi lại cả kế hoạch từ bản đã đọc trước đó. Hai lần không chồng nhau khi lần sau bắt đầu đọc lúc lần trước đã trả về, và lần sau giữ hành vi hiện tại.

**Why this priority**: Mất một việc vừa thêm mà không có câu nào nói lại làm người dùng tưởng việc đó chưa từng được lưu.

**Independent Test**: Một kế hoạch có hai việc con. Lần A thêm một việc con. Lần B đánh dấu một việc đang có là xong. Ép đúng thứ tự: lần A đọc, lần B đọc, lần A ghi xong và trả về, lần B ghi. Đọc kho và câu của từng tool. Lặp lại với hai kế hoạch khác nhau. Rồi chạy hai lần không chồng: lần sau bắt đầu đọc khi lần trước đã trả về.

**Acceptance Scenarios**:

1. **Given** kế hoạch "Học tiếng Nhật" có việc "Học hiragana" và "Nghe hội thoại", cả hai đang chưa làm, **When** một lượt thêm việc "Mua vở" và một lượt đặt "Học hiragana" là xong, hai lần ghi chạy chồng, **Then** mỗi lần ghi hoặc thành công và hiệu lực đầy đủ của nó có trong kho, hoặc trả đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` và không đổi kho bằng lần ghi đó. Nếu cả hai thành công, kho có "Mua vở" và "Học hiragana" là xong. Không có kết quả nào mà cả hai tool đều thành công nhưng "Mua vở" vắng, hoặc "Học hiragana" vẫn chưa làm.
2. **Given** cùng kế hoạch, **When** hai lượt cùng đặt trạng thái của "Học hiragana", một lượt đặt xong và một lượt đặt bỏ qua, hai lần ghi chạy chồng, **Then** trạng thái lưu lại là một trong hai trạng thái đó. Lần không còn hiệu lực trong kho đã trả câu từ chối. Không có trạng thái thứ ba, và việc kia không mất.
3. **Given** hai kế hoạch khác nhau, **When** mỗi lượt sửa một kế hoạch và hai lần ghi chạy chồng, **Then** cả hai đều thành công. Mỗi khoản sửa nằm đủ trên đúng kế hoạch của nó.
4. **Given** một lần ghi trên một kế hoạch đã trả về, **When** một lần ghi sau trên cùng kế hoạch bắt đầu đọc, **Then** hai lần không chạy chồng. Lần sau thấy đủ hiệu lực của lần trước và giữ hành vi hiện tại. Lần sau không bị từ chối chỉ vì lần trước đã ghi xong.
5. **Given** một lần ghi bị từ chối, **When** đọc kho, **Then** kế hoạch giống như lần ghi đó chưa từng ghi. Thay đổi của lượt kia, nếu lượt kia đã thành công, vẫn còn đủ.
6. **Given** kế hoạch "Học tiếng Nhật" có việc "Học hiragana" và "Nghe hội thoại", cả hai đang chưa làm, **When** lần A thêm "Mua vở" và lần B đặt "Học hiragana" là xong, đúng thứ tự: lần A đọc, lần B đọc, lần A ghi xong và trả về, lần B ghi, **Then** lần B hoặc áp dụng đủ mà vẫn giữ thay đổi của lần A, hoặc trả đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` và không đổi kho. Nếu lần B áp dụng đủ, kho có "Mua vở" và "Học hiragana" là xong. Nếu lần B bị từ chối, kho vẫn có "Mua vở" và "Học hiragana" vẫn chưa làm.

---

### User Story 3 - Lượt không kết thúc bình thường vẫn nói những gì đã lưu (Priority: P1)

Lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối, rồi không kết thúc bình thường: hết giờ, mô hình lỗi, chạm trần ba vòng, câu trả lời bị cắt, câu trả lời bị từ chối, hoặc văn bản của mô hình rỗng hay chỉ gồm khoảng trắng. Chuỗi lượt trả cho người dùng là bản ghép, thay cho `Chưa liên lạc được để trả lời lúc này.` và thay cho `Chưa trả lời xong yêu cầu này.` Chuỗi đó là một chuỗi, chữ trơn theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §9, không hiện mã kế hoạch hay mã việc con, và gọi trạng thái là chưa làm, xong, hoặc bỏ qua.

**Why this priority**: Câu lỗi chung sau khi đã lưu làm người dùng gửi lại và tạo thêm một kế hoạch nữa. Phần chống tạo trùng khi Telegram gửi lại webhook thuộc F11. Lát này làm cho người dùng thấy việc đã lưu.

**Independent Test**: Mô hình giả gọi một tool ghi, tool đó thành công, rồi lượt hết giờ, hoặc mô hình lỗi, hoặc đòi tool ở vòng thứ tư, hoặc trả lời bị cắt, hoặc bị từ chối, hoặc trả văn bản rỗng hay chỉ khoảng trắng. Đọc chuỗi lượt trả. Một ca lần ghi quá giờ rồi mô hình trả rỗng hoặc khoảng trắng, chuỗi là câu chưa chắc. Một ca lần ghi bị từ chối rồi mô hình trả rỗng hoặc khoảng trắng, chuỗi là câu từ chối. Một ca khác không có lần ghi thành công, lần ghi bị bỏ, hay lần ghi bị từ chối rồi gặp cùng các lối kết đó, và một ca văn bản rỗng khi không có cả ba.

**Acceptance Scenarios**:

1. **Given** `create_plan` đã thành công với mục tiêu "Học tiếng Nhật" và việc "Học hiragana", **When** lượt hết giờ, mô hình lỗi, chạm trần ba vòng, câu trả lời bị cắt, hoặc bị từ chối, **Then** chuỗi lượt trả là `1. Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana.` Chuỗi đó không phải một trong hai câu lỗi chung.
2. **Given** `add_subtask` đã thành công, thêm "Mua vở" vào kế hoạch "Học tiếng Nhật", **When** lượt không kết thúc bình thường, **Then** chuỗi có dòng `1. Đã lưu việc Mua vở vào kế hoạch Học tiếng Nhật.`
3. **Given** `update_subtask` đã thành công, đặt "Học hiragana" trong kế hoạch "Học tiếng Nhật" thành đã xong, **When** lượt không kết thúc bình thường, **Then** chuỗi có dòng `1. Đã lưu việc Học hiragana trong kế hoạch Học tiếng Nhật là xong.` Trạng thái không hiện bằng mã lưu trữ.
4. **Given** `set_subtask_note` đã thành công với ghi chú "Đợi giáo trình" trên việc "Học hiragana" của kế hoạch "Học tiếng Nhật", **When** lượt không kết thúc bình thường, **Then** chuỗi có dòng `1. Đã lưu ghi chú Đợi giáo trình cho việc Học hiragana trong kế hoạch Học tiếng Nhật.`
5. **Given** `set_subtask_note` đã thành công và ghi chú của việc đó trở thành trống, **When** lượt không kết thúc bình thường, **Then** chuỗi có dòng `1. Đã bỏ ghi chú của việc Học hiragana trong kế hoạch Học tiếng Nhật.`
6. **Given** hai lần ghi đã thành công theo thứ tự tạo kế hoạch rồi thêm việc, **When** lượt không kết thúc bình thường, **Then** chuỗi có hai dòng, dòng `1.` là lần ghi xong trước, dòng `2.` là lần ghi xong sau, mỗi dòng đúng mẫu của lần ghi đó.
7. **Given** một lần ghi đã thành công và một lần ghi khác của cùng lượt bị bỏ vì quá giờ, **When** lượt không kết thúc bình thường, **Then** chuỗi có các dòng đã lưu, rồi một dòng đúng `Chưa chắc thay đổi đã được lưu.`
8. **Given** một lần ghi đã thành công và một lần ghi khác của cùng lượt bị từ chối, **When** lượt không kết thúc bình thường, **Then** chuỗi có các dòng đã lưu, rồi một dòng đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`
9. **Given** lượt chưa có lần ghi thành công, chưa có lần ghi bị bỏ, và chưa có lần ghi bị từ chối, **When** lượt hết giờ, mô hình lỗi, chạm trần ba vòng, câu trả lời bị cắt, hoặc bị từ chối, **Then** chuỗi vẫn là câu đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md): `Chưa liên lạc được để trả lời lúc này.` hoặc, khi chạm trần ba vòng, `Chưa trả lời xong yêu cầu này.`
10. **Given** một lần ghi đã thành công và mô hình trả một câu văn còn chữ khác khoảng trắng, **When** lượt trả về, **Then** chuỗi là đúng câu văn đó, không bị thay bằng bản ghép.
11. **Given** một lần ghi bị bỏ vì quá giờ, chưa có lần ghi thành công và chưa có lần ghi bị từ chối, **When** lượt không kết thúc bình thường, **Then** chuỗi là đúng `Chưa chắc thay đổi đã được lưu.`
12. **Given** một lần ghi bị từ chối, chưa có lần ghi thành công và chưa có lần ghi bị bỏ, **When** lượt không kết thúc bình thường, **Then** chuỗi là đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`
13. **Given** `create_plan` đã thành công với mục tiêu "Học tiếng Nhật" và hai việc "Học hiragana" rồi "Mua vở", **When** lượt không kết thúc bình thường, **Then** chuỗi là `1. Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana, Mua vở.`
14. **Given** `create_plan` đã thành công với mục tiêu "Học tiếng Nhật" và việc "Học hiragana", và mô hình trả văn bản rỗng hoặc chỉ gồm khoảng trắng, **When** lượt trả về, **Then** đó là không kết thúc bình thường và chuỗi là `1. Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana.`
15. **Given** một lần ghi quá giờ, chưa có lần ghi thành công và chưa có lần ghi bị từ chối, **When** mô hình trả văn bản rỗng hoặc chỉ gồm khoảng trắng, **Then** chuỗi là `Chưa chắc thay đổi đã được lưu.`
16. **Given** một lần ghi bị từ chối, chưa có lần ghi thành công và chưa có lần ghi bị bỏ, **When** mô hình trả văn bản rỗng hoặc chỉ gồm khoảng trắng, **Then** chuỗi là `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.`

---

### Edge Cases

- Giới hạn của một lời gọi kho không dài hơn phần ngân sách 20 giây còn lại. Số ngắn hơn, và chỗ đặt giới hạn, do bước plan chọn. Lát này không chọn số giây riêng cho từng loại lời gọi.
- Hết ngân sách trước khi một lời gọi kho bắt đầu: không bắt đầu lời gọi đó. Đó là lối kết đã có, không phải một lời gọi bị bỏ giữa chừng.
- Lần đọc bị bỏ dùng câu lỗi tool đã có `Không thực hiện được yêu cầu này.` Lần đọc không phải lần ghi, nên không dùng câu chưa chắc.
- Lần ghi bị bỏ không dùng `Không thực hiện được yêu cầu này.`, vì câu đó nghe như chắc chắn là chưa làm được.
- Trong một tool, lời gọi kho trước bị bỏ thì tool không gửi lời gọi kho sau. Tool trả lỗi của lời gọi bị bỏ.
- Lượt còn thời gian và còn vòng, sau khi tool đã trả lỗi: lỗi đó được gửi lại mô hình không đổi chữ, đúng [spec lượt mô hình](../008-llm-tool-turn/spec.md). Nếu mô hình sau đó trả văn bản còn chữ khác khoảng trắng, người dùng thấy câu đó. Lát này không sửa lời hướng dẫn để bắt mô hình nhắc lại câu đó.
- Lượt không kết thúc bình thường, và trong lượt có lần ghi bị bỏ hoặc bị từ chối dù chưa có lần ghi thành công: chuỗi là các câu cố định tương ứng, mỗi câu một dòng, câu chưa chắc đứng trước câu từ chối nếu cả hai cùng có. Không dùng hai câu lỗi chung.
- Cả ba cùng có (đã lưu, chưa chắc, bị từ chối): các dòng đã lưu theo thứ tự ghi xong, rồi dòng chưa chắc, rồi dòng từ chối.
- Hai lần ghi không chạy chồng khi lần sau bắt đầu đọc lúc lần trước đã trả về. Lần sau giữ hành vi hiện tại và thấy đủ hiệu lực của lần trước.
- Hai lần tạo hai kế hoạch mới không phải hai lần sửa cùng một kế hoạch. Cả hai có thể thành công. Chống tạo trùng khi người dùng hoặc Telegram gửi lại cùng một yêu cầu thuộc F11.
- Một lần ghi quá giờ rồi mô hình gọi ghi lại trong cùng lượt có thể tạo thêm một bản. Lát này không chặn việc đó.
- Lần ghi bị từ chối không xóa hiệu lực của lần ghi khác đã thành công.
- Hủy tác vụ vẫn đi ra khỏi lượt, không bị đổi thành bản tóm đã lưu hay thành câu chưa chắc, đúng spec lượt mô hình.
- Thiếu khóa vẫn là lỗi cấu hình trước mọi lời gọi, đúng spec lượt mô hình.
- Văn bản của mô hình rỗng hoặc chỉ gồm khoảng trắng khi lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối là không kết thúc bình thường, và chuỗi là bản ghép như FR-008 và FR-010. Nếu không có cả ba, văn bản rỗng vẫn là chuỗi rỗng, thuộc F11, và văn bản chỉ gồm khoảng trắng vẫn là đúng văn bản đó. Văn bản còn chữ khác khoảng trắng vẫn là câu của mô hình.
- Câu người dùng thấy không chứa mã kế hoạch, mã việc con, `pending`, `done`, hay `skipped`. Không in đậm, không tiêu đề `#`, không bảng.
- Một dòng đã lưu chứa đúng chữ của mục tiêu, tiêu đề, và ghi chú đã lưu. Chữ đó không bị viết lại.
- Bộ tool vẫn là sáu tool hiện có. Không có trường ngày trên việc con.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mỗi lời gọi kho MUST có giới hạn thời gian không dài hơn phần ngân sách 20 giây còn lại của lượt. Quá giới hạn, lời gọi đó MUST bị bỏ và tool MUST trả lỗi. Lượt MUST NOT vượt 20 giây vì một lời gọi kho chưa trả về.
- **FR-002**: Khi lời gọi đọc bị bỏ, tool MUST trả cờ lỗi bật và đúng `Không thực hiện được yêu cầu này.` Khi lời gọi ghi bị bỏ, tool MUST trả cờ lỗi bật và đúng `Chưa chắc thay đổi đã được lưu.` Câu ghi bị bỏ MUST NOT khẳng định thay đổi đã lưu và MUST NOT khẳng định thay đổi chưa lưu.
- **FR-003**: Nếu một lời gọi kho trong một tool bị bỏ, tool đó MUST NOT gửi thêm lời gọi kho nào trong cùng lần chạy. Tool MUST trả lỗi của lời gọi bị bỏ.
- **FR-004**: Lời gọi kho trả về trước giới hạn MUST giữ kết quả thành công hoặc lỗi miền đã chốt ở spec của tool đó.
- **FR-005**: Hai lần ghi chạy chồng trên cùng một kế hoạch: mỗi lần hoặc MUST áp dụng đủ hiệu lực và báo thành công, hoặc MUST trả cờ lỗi bật với đúng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` và MUST NOT thêm, bớt, hay sửa gì bằng lần ghi đó. Kho MUST NOT vừa nhận một phần của lần ghi này vừa mất một phần của lần ghi kia. Hai lần ghi trên cùng một kế hoạch chạy chồng khi khoảng thời gian của chúng giao nhau. Mỗi khoảng tính từ lúc tool bắt đầu đọc kế hoạch tới lúc tool trả về.
- **FR-006**: Nếu cả hai lần ghi chạy chồng cùng báo thành công, kho MUST chứa đủ hiệu lực của cả hai. Một việc con lần ghi này thêm MUST NOT vắng khi lần ghi kia cũng báo thành công.
- **FR-007**: Hai lần ghi chạy chồng trên hai kế hoạch khác nhau MUST đều được áp dụng đủ. Hai lần ghi trên cùng một kế hoạch MUST NOT chạy chồng khi lần sau bắt đầu đọc lúc lần trước đã trả về. Lần sau MUST thấy đủ hiệu lực của lần trước, MUST giữ hành vi hiện tại, và MUST NOT bị từ chối chỉ vì lần trước đã ghi xong.
- **FR-008**: Khi lượt không kết thúc bình thường và đã có ít nhất một lần ghi thành công, chuỗi lượt trả MUST là bản ghép ở Assumptions: các dòng đã lưu, rồi câu chưa chắc nếu có lần ghi bị bỏ, rồi câu từ chối nếu có lần ghi bị từ chối. Chuỗi đó MUST NOT là `Chưa liên lạc được để trả lời lúc này.` và MUST NOT là `Chưa trả lời xong yêu cầu này.`
- **FR-009**: Chuỗi ở FR-008 và FR-010 MUST là một chuỗi chữ trơn theo [docs/PRODUCT.md](../../docs/PRODUCT.md) §9. Chuỗi MUST NOT chứa mã kế hoạch, mã việc con, `pending`, `done`, hay `skipped`. Trạng thái trong chuỗi MUST là chưa làm, xong, hoặc bỏ qua.
- **FR-010**: Khi lượt không kết thúc bình thường và chưa có lần ghi thành công, nếu có lần ghi bị bỏ hoặc bị từ chối thì chuỗi MUST là các câu cố định tương ứng, câu chưa chắc trước câu từ chối. Nếu không có lần ghi bị bỏ và không có lần ghi bị từ chối, chuỗi MUST vẫn là câu spec lượt mô hình đã chốt cho lối kết đó.
- **FR-011**: Văn bản của mô hình còn chữ khác khoảng trắng MUST được trả đúng văn bản đó, kể cả khi lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối. Nếu có ít nhất một trong ba thứ đó và văn bản của mô hình rỗng hoặc chỉ gồm khoảng trắng, lượt MUST coi đó là không kết thúc bình thường và chuỗi MUST là bản ghép ở FR-008 và FR-010. Nếu không có cả ba, văn bản rỗng MUST vẫn là chuỗi rỗng và văn bản chỉ gồm khoảng trắng MUST được trả đúng văn bản đó. Hủy tác vụ MUST đi tiếp ra ngoài lượt. Thiếu khóa MUST vẫn thất bại trước mọi lời gọi.
- **FR-012**: Khi lượt còn chạy tiếp sau một lỗi tool, nội dung tool trả MUST được gửi lại mô hình không đổi chữ.
- **FR-013**: Lời hướng dẫn hệ thống, `PROMPT_VERSION`, bộ định nghĩa tool, `DEFINITIONS_VERSION`, bộ câu đánh giá, và cách chấm MUST giữ nguyên. Lát này MUST NOT thêm tool và MUST NOT thêm trường ngày cho việc con.

### Key Entities *(include if feature involves data)*

- **Lượt**: Một lần chạy đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Cho ra một chuỗi, trừ khi thiếu khóa hoặc bị hủy. Ngân sách 20 giây và trần ba vòng giữ nguyên.
- **Lần ghi**: Một lần chạy `create_plan`, `add_subtask`, `update_subtask`, hoặc `set_subtask_note`. Thành công thì hiệu lực đầy đủ của lần đó còn trong kho. Bị bỏ hoặc bị từ chối thì lần đó không được kể là thành công.
- **Lần đọc**: `get_plans` hoặc `get_plan_detail`. Không làm thay đổi kho.
- **Lời gọi kho**: Một lần đọc hoặc ghi kho bên trong một tool. Có giới hạn thời gian riêng, nằm trong phần ngân sách còn lại.
- **Kế hoạch và việc con**: Đúng thực thể đã chốt ở spec 001, spec 003, và spec 005. Kế hoạch có thêm một số version để phát hiện hai lần ghi chạy chồng; người dùng và mô hình không thấy số này (plan.md, data-model.md). Việc con không thêm thuộc tính.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lời gọi kho không trả về trước giới hạn của nó bị bỏ. 0 lượt vượt 20 giây vì một lời gọi kho chưa trả về.
- **SC-002**: 100% lần ghi bị bỏ trả đúng `Chưa chắc thay đổi đã được lưu.` 0 câu đó nói chắc đã lưu hoặc chắc chưa lưu. 100% lần đọc bị bỏ trả đúng `Không thực hiện được yêu cầu này.`
- **SC-003**: 100% cặp lần ghi trên cùng một kế hoạch có khoảng thời gian giao nhau, kể cả khi lần A đọc, lần B đọc, lần A ghi xong và trả về, rồi lần B mới ghi, kết thúc với mỗi lần hoặc đủ hiệu lực trong kho, hoặc đúng câu từ chối và không đổi gì bằng lần đó. 0 cặp cùng báo thành công mà việc con vừa thêm bị mất. 100% cặp trên hai kế hoạch khác nhau giữ đủ cả hai hiệu lực.
- **SC-004**: 100% lần ghi không chồng nhau, lần sau bắt đầu đọc khi lần trước đã trả về, thấy đủ hiệu lực của lần trước và giữ hành vi hiện tại.
- **SC-005**: 100% lượt không kết thúc bình thường sau ít nhất một lần ghi thành công trả đúng bản ghép ở FR-008, là một chuỗi, không mã, không hai câu lỗi chung. Trạng thái trong chuỗi chỉ là chưa làm, xong, hoặc bỏ qua.
- **SC-006**: 100% lượt không kết thúc bình thường khi không có lần ghi thành công, lần ghi bị bỏ, và lần ghi bị từ chối vẫn trả đúng câu spec lượt mô hình đã chốt. 100% văn bản của mô hình còn chữ khác khoảng trắng được trả đúng văn bản đó. 100% văn bản rỗng hoặc chỉ khoảng trắng khi lượt có ít nhất một trong ba thứ đó trả đúng bản ghép ở FR-008 và FR-010. 100% văn bản rỗng khi không có cả ba vẫn là chuỗi rỗng. 100% văn bản chỉ khoảng trắng khi không có cả ba được trả đúng văn bản đó.
- **SC-007**: 0 thay đổi ở lời hướng dẫn, số phiên bản lời hướng dẫn, bộ định nghĩa tool, số phiên bản bộ định nghĩa, bộ câu đánh giá, và cách chấm. 0 tool mới. 0 trường ngày mới trên việc con.

## Assumptions

- Ba câu do lát này chọn, vì yêu cầu gốc giao nghĩa và không giao nguyên văn. Câu lần ghi quá giờ: `Chưa chắc thay đổi đã được lưu.` Câu lần ghi bị từ chối: `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` Câu lần đọc quá giờ dùng lại `Không thực hiện được yêu cầu này.` của [spec điều phối tool](../007-plan-tool-router/spec.md).
- Bản tóm đã lưu là các dòng theo thứ tự lần ghi thành công xong. Một dòng không có tiền tố khác ngoài số thứ tự `1.`, `2.`, … đúng [docs/PRODUCT.md](../../docs/PRODUCT.md) §9. Mẫu dòng, với chữ mục tiêu, tiêu đề, và ghi chú đúng giá trị đã lưu:
  - Tạo kế hoạch có việc con: `Đã lưu kế hoạch {mục tiêu} với việc {tiêu đề}.` Nhiều tiêu đề theo thứ tự đã lưu, ngăn bằng dấu phẩy và một dấu cách. Một việc: `Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana.` Hai việc: `Đã lưu kế hoạch Học tiếng Nhật với việc Học hiragana, Mua vở.`
  - Tạo kế hoạch không có việc con: `Đã lưu kế hoạch {mục tiêu}.`
  - Thêm việc con: `Đã lưu việc {tiêu đề} vào kế hoạch {mục tiêu}.`
  - Đặt trạng thái: `Đã lưu việc {tiêu đề} trong kế hoạch {mục tiêu} là {chưa làm|xong|bỏ qua}.`
  - Đặt ghi chú còn chữ: `Đã lưu ghi chú {ghi chú} cho việc {tiêu đề} trong kế hoạch {mục tiêu}.`
  - Xóa ghi chú: `Đã bỏ ghi chú của việc {tiêu đề} trong kế hoạch {mục tiêu}.`
- Khi lượt không kết thúc bình thường, chuỗi ghép theo thứ tự: các dòng đã lưu, rồi dòng `Chưa chắc thay đổi đã được lưu.` nếu có lần ghi bị bỏ, rồi dòng `Thay đổi chưa được áp dụng. Bạn thử lại giúp mình.` nếu có lần ghi bị từ chối. Mỗi phần một dòng. Không thêm dòng trống. Chỉ một loại thì chuỗi là đúng phần đó, dòng đã lưu vẫn mang số thứ tự.
- "Không kết thúc bình thường" gồm hết giờ, mô hình lỗi, trần ba vòng, câu trả lời bị cắt, câu trả lời bị từ chối, và văn bản của mô hình rỗng hoặc chỉ gồm khoảng trắng khi lượt có lần ghi thành công, lần ghi bị bỏ, hoặc lần ghi bị từ chối. Văn bản còn chữ khác khoảng trắng là kết thúc bình thường và được trả đúng văn bản đó. Văn bản rỗng khi không có cả ba vẫn là chuỗi rỗng, thuộc F11. Văn bản chỉ khoảng trắng khi không có cả ba được trả đúng văn bản đó. Hủy tác vụ và thiếu khóa không thuộc nhóm đó.
- Câu chưa chắc và câu từ chối không khẳng định chi tiết của lần ghi hỏng. Chi tiết chỉ xuất hiện ở dòng của lần ghi đã thành công.
- Ngân sách 20 giây và trần ba vòng trỏ sang spec lượt mô hình, không chép lại cả spec đó. Câu trong spec đó nói lần chạy tool đã bắt đầu không bị cắt không còn hiệu lực với lời gọi kho quá giới hạn của chính nó. Các file spec 008 không sửa.
- Cách đặt giới hạn thời gian, cách làm cho định nghĩa chạy chồng ở FR-005 thành hiện thực, và việc có đổi hình dữ liệu trong kho hay không, thuộc bước plan. Lát này chỉ chốt điều quan sát được.
- Người dùng là một người, như PRODUCT §2. Lát này chỉ sửa docs ở bước đồng bộ cuối (T038): PRODUCT §7, bảng review, và câu nào trong docs/ARCHITECTURE.md hoặc AGENTS.md thành sai. docs/DECISIONS.md chỉ được thêm D-021 và một dòng Cập nhật ở D-011, người dùng đã duyệt ở B10 (2026-11-04). Không sửa constitution.
- Kiểm trên máy bằng kho giả trong `tests/fakes` và bằng kho Supabase local. Ca kho giả không mở mạng. Ca kho local chỉ để thấy hai lần ghi chạy chồng không mất cập nhật trong im lặng.
- Kiểm tra đang khóa hành vi cũ chỉ được đổi khi khẳng định đúng một trong ba hành vi này: lời gọi kho quá giờ, hai lần ghi chạy chồng, hoặc chuỗi lượt khi đã ghi mà không kết thúc bình thường. Mọi khẳng định khác giữ nguyên.
- Ngoài phạm vi, theo mô tả tính năng:
  - Câu trả lời khi mô hình bị cắt hoặc bị từ chối mà chưa có lần ghi thành công, chưa có lần ghi bị bỏ, và chưa có lần ghi bị từ chối. Văn bản rỗng khi không có cả ba vẫn là chuỗi rỗng. Phần đó là phần còn lại của L1-04, để cho F11.
  - Chống tạo trùng khi Telegram gửi lại webhook, hoặc khi người dùng gửi lại sau câu chưa chắc. Thuộc F11.
  - L1-05 và L1-06.
  - Đổi lời hướng dẫn, số phiên bản lời hướng dẫn, bộ định nghĩa tool, số phiên bản bộ định nghĩa, bộ câu đánh giá, hoặc cách chấm.
  - Thêm trường ngày cho việc con. Thuộc F17.
  - Thêm tool mới.
  - Sửa spec cũ trong `specs/`.
