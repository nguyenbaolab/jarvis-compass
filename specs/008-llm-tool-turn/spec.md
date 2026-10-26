# Feature Specification: Lượt trả lời có gọi mô hình

**Feature Branch**: `008-llm-tool-turn`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Lớp gọi LLM của jarvis-compass, phần còn lại của F12 sau tool router: nhận tin nhắn tiếng Việt của người dùng, gọi LLM, chạy tool qua execute_tool khi LLM yêu cầu, trả về câu trả lời cuối. Đây là đơn vị bộ eval tool calling sẽ chấm, và là mắt xích còn thiếu giữa tool router (vòng 7) và bot Telegram (vòng sau). Spike đã chạy được với claude-haiku-5-5, nhưng có lỗi hành vi: gọi create_plan khi người dùng chỉ kể việc. Một lượt nhận tin nhắn, lịch sử có thể rỗng và không được lưu, cùng kho cho tool, rồi trả một câu văn bản. Vòng tool chạy execute_tool và gửi kết quả lại, tối đa 3 lượt; hết lượt thì một câu tiếng Việt do dự án viết. Định nghĩa tool lấy từ TOOL_DEFINITIONS. System prompt nằm một chỗ, có phiên bản, với bốn luật: không gọi tool khi người dùng chỉ kể việc; không tự xưng trợ lý lập kế hoạch, tên và vai theo D-002; việc con có điểm kết thúc đo được; tiêu đề không có tiền tố thứ tự. Model mặc định claude-haiku-5-5, không bật thinking. Khóa do người gọi truyền, không đọc môi trường tiến trình; thiếu khóa thì lỗi cấu hình trước mọi lời gọi mạng. Lỗi API và vượt ngân sách thời gian của cả lượt trả một câu tiếng Việt, không lộ nội dung lỗi. CancelledError đi tiếp như router. Mỗi lần gọi mô hình một dòng JSON riêng, tách khỏi bảy khóa log tool của D-014. Hàm log ném lỗi thì nuốt. Ngoài phạm vi: webhook, Telegram, dựng kho thật, chặn theo chat id, lưu lịch sử, bộ eval khoảng 50 câu, streaming. Cổng mô hình trung lập, adapter nhà cung cấp tách khỏi lõi. Test không gọi mạng; smoke gọi API thật nếu có thì chạy tay, không nằm trong bộ test tự động."

## User Scenarios & Testing *(mandatory)*

Người gọi ở lát này là bộ đánh giá tool calling, và vòng sau sẽ là bot Telegram. Người dùng cuối thấy một câu trả lời của JARVIS. Sáu tool và cách gọi chúng đã chốt ở [spec điều phối tool](../007-plan-tool-router/spec.md). Lát này nối một tin nhắn người dùng với mô hình, và khi mô hình đòi tool thì đi qua `execute_tool` của spec đó. Lát này không dựng kho, không lưu hội thoại, và không chấm việc mô hình thật có tuân thủ prompt hay không.

### User Story 1 - Một tin nhắn ra một câu trả lời (Priority: P1)

Người gọi đưa tin nhắn mới của người dùng, danh sách tin nhắn trước đó, và kho cho tool. Danh sách trước đó có thể rỗng. Lượt này không ghi danh sách đó vào đâu cả. Khi mô hình trả lời bằng văn bản và không đòi tool, kết quả của lượt là đúng văn bản đó.

**Why this priority**: Không có lượt này thì tool router không có ai gọi, và bot Telegram chưa có câu để gửi.

**Independent Test**: Client giả trả một văn bản và không đòi tool. Lịch sử rỗng, và một lịch sử hai tin. Không mở mạng. Kho không bị gọi.

**Acceptance Scenarios**:

1. **Given** lịch sử rỗng và client giả trả văn bản "Bạn muốn mình lập kế hoạch cho hai việc đó không?", không đòi tool, **When** người gọi gửi "Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3" cùng một kho, **Then** kết quả là đúng câu đó. Kho không bị gọi.
2. **Given** lịch sử có một tin người dùng và một tin trả lời, theo thứ tự đó, **When** người gọi gửi tin mới, **Then** yêu cầu gửi tới mô hình giữ nguyên thứ tự lịch sử rồi mới tới tin mới. Sau lượt, kho lưu hội thoại không có thêm dòng nào, vì lát này không có kho hội thoại.
3. **Given** client giả trả văn bản rỗng và không đòi tool, **When** chạy một lượt, **Then** kết quả là chuỗi rỗng, không bị thay bằng câu lỗi.

---

### User Story 2 - Mô hình đòi tool thì chạy rồi hỏi lại (Priority: P1)

Khi mô hình trả một phản hồi có đòi tool, đó là một vòng. Mọi tool trong phản hồi đó chạy bằng `execute_tool` trên đúng kho người gọi đã đưa, theo thứ tự phản hồi đưa. Mọi kết quả được gửi lại trong lần gọi mô hình kế tiếp. Lặp tới khi mô hình trả văn bản và không đòi tool. Tối đa 3 vòng. Nếu phản hồi thứ tư vẫn đòi tool thì không chạy tool nào của phản hồi đó, không gọi mô hình thêm, và kết quả là đúng câu `Chưa trả lời xong yêu cầu này.`

**Why this priority**: Bộ eval chấm đúng vòng này: mô hình đòi tool, tool chạy, kết quả quay lại mô hình, rồi có câu cuối.

**Independent Test**: Client giả trả một chuỗi phản hồi định sẵn: một hoặc nhiều vòng đòi tool, rồi một văn bản. Đếm số vòng và số lần `execute_tool`. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** client giả lần một đòi `get_plans` với object rỗng, lần hai trả văn bản "Bạn đang có một kế hoạch.", **When** chạy một lượt, **Then** `execute_tool` chạy đúng một lần với tên `get_plans`, object đó, và đúng kho người gọi đưa. Nội dung `execute_tool` trả, kể cả khi cờ lỗi bật, được gửi lại nguyên cho mô hình. Kết quả của lượt là câu văn bản lần hai.
2. **Given** client giả trả bốn phản hồi liên tiếp, mỗi phản hồi đòi một tool, **When** chạy một lượt, **Then** ba vòng đầu chạy hết tool của từng phản hồi. Phản hồi thứ tư không chạy tool nào, và không có lời gọi mô hình nào sau phản hồi đó. Kết quả là đúng `Chưa trả lời xong yêu cầu này.`
3. **Given** vòng đầu client giả đòi `get_plans` rồi `get_plan_detail` trong cùng một phản hồi, và lần gọi mô hình sau đó trả văn bản, **When** chạy một lượt, **Then** cả hai tool đều chạy theo thứ tự đó, trên đúng kho. Mô hình được gọi lại đúng một lần, và lần gọi đó nhận cả hai kết quả. Kết quả của lượt là văn bản đó.
4. **Given** `execute_tool` trả cờ lỗi bật và một câu miền, **When** mô hình sau đó trả văn bản, **Then** câu miền đã được gửi lại cho mô hình không đổi chữ, và kết quả của lượt là văn bản đó, không phải câu miền.

---

### User Story 3 - Prompt và danh sách tool chỉ có một chỗ (Priority: P1)

Danh sách tool gửi cho mô hình là đúng bộ `TOOL_DEFINITIONS` đã chốt, không viết lại tên, mô tả, hay schema ở chỗ khác. Lời hướng dẫn hệ thống nằm một chỗ, có số phiên bản `1`, và có bốn luật ở dưới. Lời hướng dẫn đó được gửi trong mỗi lần gọi mô hình của lượt.

**Why this priority**: Spike gọi `create_plan` khi người dùng chỉ kể việc. Luật nằm trong prompt để vòng eval sau chấm. Lát này không chấm mô hình thật có nghe lời hay không.

**Independent Test**: Đọc lời hướng dẫn một lần, không gọi mô hình. Client giả ghi lại yêu cầu đã gửi; danh sách tool trên yêu cầu đó trùng bộ định nghĩa.

**Acceptance Scenarios**:

1. **Given** bộ định nghĩa sáu tool phiên bản `1`, **When** một lượt gọi mô hình, **Then** yêu cầu gửi đi có đúng sáu tool đó, cùng mô tả và schema đầu vào của bộ định nghĩa. Không có tool thứ bảy. `revise_plan` không có trong yêu cầu.
2. **Given** lời hướng dẫn phiên bản `1`, **When** đọc nguyên văn, **Then** lời đó có đủ bốn luật: người dùng chỉ kể việc và không nhờ lập kế hoạch thì không gọi tool, tóm tắt lại rồi hỏi có muốn lập kế hoạch không, kèm đúng ví dụ "Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3"; người nói không tự xưng "trợ lý lập kế hoạch", tên và vai là JARVIS theo D-002, không có tên nhân vật thứ hai; mỗi việc con có điểm kết thúc đo được; tiêu đề việc con không có tiền tố thứ tự như "1." hay "Bước 1".
3. **Given** một lượt có hai lần gọi mô hình, **When** xem từng yêu cầu, **Then** cả hai đều mang cùng lời hướng dẫn phiên bản `1` và cùng bộ tool.

---

### User Story 4 - Khóa, model, và lỗi được gọi tên (Priority: P1)

Model của lát này là `claude-haiku-5-5`. Lượt không bật chế độ suy nghĩ. Khóa do người gọi truyền vào. Không đọc khóa từ môi trường của tiến trình. Không có khóa, hoặc khóa là chuỗi rỗng, thì lỗi cấu hình trước mọi lời gọi mạng, bằng đúng câu `Thiếu ANTHROPIC_API_KEY.` Câu đó không chứa giá trị khóa. Lỗi từ phía mô hình, gồm quá thời gian, bị từ chối vì quá nhiều yêu cầu, lỗi máy chủ, và mất mạng, trả cho người gọi đúng câu `Chưa liên lạc được để trả lời lúc này.` Câu đó không chứa mã trạng thái, địa chỉ, tên loại lỗi, hay giá trị khóa. Không thử gọi lại.

**Why this priority**: Thiếu khóa mà vẫn mở mạng là sai cùng kiểu với kho ở vòng trước. Lỗi thô của nhà cung cấp không được tới người dùng.

**Independent Test**: Không đưa khóa, và đưa khóa rỗng, với client giả sẽ thất bại nếu bị gọi. Rồi đưa khóa và bắt client giả ném lỗi có chữ `secret` và `http` trong thông điệp. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** người gọi không đưa khóa, **When** chạy một lượt, **Then** lỗi là đúng `Thiếu ANTHROPIC_API_KEY.` Client giả không bị gọi. Môi trường tiến trình có khóa cũng không được đọc.
2. **Given** khóa là chuỗi rỗng, **When** chạy một lượt, **Then** cùng câu đó, và client giả không bị gọi.
3. **Given** khóa khác rỗng do người gọi đưa, và môi trường tiến trình có một khóa khác, **When** client giả ghi lại lời gọi `complete`, **Then** `complete` nhận khóa của người gọi. Model `claude-haiku-5-5` và việc không bật chế độ suy nghĩ được kiểm ở test adapter.
4. **Given** client giả ném lỗi với thông điệp chứa `secret-key-value`, `http://example.invalid`, và `429`, **When** chạy một lượt, **Then** kết quả là đúng `Chưa liên lạc được để trả lời lúc này.` Kết quả không chứa ba mảnh đó. Không có lần gọi mô hình thứ hai.

---

### User Story 5 - Cả lượt có ngân sách, hủy tác vụ thì đi tiếp (Priority: P1)

Một lượt có ngân sách 20 giây. Sau khi đã dùng hết 20 giây, lượt không bắt đầu lời gọi mô hình hay lần chạy tool mới và trả câu lỗi phía mô hình. Lời gọi mô hình đang chạy được giới hạn bằng timeout bằng phần ngân sách còn lại; lần execute_tool đã bắt đầu không bị cắt. Phản hồi của lời gọi đã bắt đầu trước mốc vẫn được dùng. Hủy tác vụ đi tiếp, không bị đổi thành câu đó, giống `CancelledError` ở spec điều phối tool.

**Why this priority**: Một lượt có một lần tool đo được mất 5 đến 7 giây. Lượt này cần một ngân sách cho cả các lần gọi mô hình và các lần chạy tool.

**Independent Test**: Client giả không mở mạng. Đồng hồ bịt sẵn để lượt vượt 20 giây. Một ca khác ném hủy tác vụ từ client giả.

**Acceptance Scenarios**:

1. **Given** đồng hồ bịt cho thấy lượt đã dùng hết 20 giây trước khi có văn bản cuối, **When** chạy, **Then** kết quả là đúng câu lỗi phía mô hình. Không bắt đầu lời gọi mô hình hay lần chạy tool mới sau mốc đó. Lời gọi mô hình đang chạy được giới hạn bằng phần ngân sách còn lại; lần execute_tool đã bắt đầu không bị cắt. Phản hồi của lời gọi đã bắt đầu trước mốc vẫn được dùng.
2. **Given** client giả hủy tác vụ, **When** chạy, **Then** việc hủy đi ra khỏi lượt. Kết quả không phải câu lỗi phía mô hình và không phải câu hết lượt tool.

---

### User Story 6 - Một dòng nhật ký cho mỗi lần gọi mô hình (Priority: P1)

Mỗi lần gọi mô hình ghi đúng một dòng nhật ký. Dòng đó tách khỏi dòng bảy khóa của mỗi lần `execute_tool`. Bảy khóa đó không thêm, không bớt, không đổi nghĩa, đúng D-014. Lần gọi mô hình bị lỗi cũng có một dòng; phần mô tả lỗi trên dòng đó chỉ là tên loại lỗi, không có thông điệp. Hàm ghi được truyền vào mà ném lỗi thì lỗi đó bị nuốt, và lượt vẫn trả kết quả.

**Why this priority**: Bộ eval cần đối chiếu lần gọi mô hình với lần gọi tool. Trộn hai dòng, hoặc đưa thông điệp lỗi vào dòng, làm hỏng chỗ chấm và có thể lộ khóa.

**Independent Test**: Client giả trả văn bản, rồi một ca ném lỗi. Hàm ghi nhận từng dòng. Một ca hàm ghi ném lỗi. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** một lượt có một lần gọi mô hình thành công và không có tool, **When** đọc dòng nhật ký của lần gọi mô hình, **Then** có đúng một dòng, đọc được thành object, với các khóa ở FR-012. `error_type` trống. Văn bản tiếng Việt trong yêu cầu không bị đổi thành mã thoát.
2. **Given** một lượt chạy một tool rồi mô hình trả văn bản, **When** đọc nhật ký, **Then** có hai dòng của lần gọi mô hình, và đúng một dòng bảy khóa của tool. Dòng mô hình có đúng tám khóa của Assumptions, dòng tool có đúng bảy khóa D-014; hai loại dòng phân biệt bằng khóa `model` và khóa `tool`.
3. **Given** client giả ném lỗi với thông điệp `secret-key-value`, **When** đọc dòng của lần gọi đó, **Then** dòng có tên loại lỗi và không chứa `secret-key-value`.
4. **Given** hàm ghi ném lỗi ở dòng mô hình, **When** mô hình đã trả văn bản, **Then** lượt vẫn trả đúng văn bản đó, không ném lỗi của hàm ghi.

---

### Edge Cases

- Lịch sử rỗng là hợp lệ. Tin mới vẫn được gửi.
- Văn bản cuối rỗng là một kết quả thành công, không bị thay bằng câu lỗi.
- Một phản hồi đòi nhiều tool là một vòng: mọi tool trong phản hồi đó chạy theo thứ tự phản hồi đưa, và mọi kết quả được gửi lại trong lần gọi mô hình kế tiếp. Phản hồi thứ tư nếu vẫn đòi tool thì không chạy tool nào của phản hồi đó, và không gọi mô hình thêm.
- Nội dung `execute_tool` trả, dù cờ lỗi bật hay tắt, gửi lại mô hình không đổi chữ.
- Khóa không có và khóa chuỗi rỗng là lỗi cấu hình, trước client. Chuỗi chỉ khoảng trắng không bị cắt; nó được coi là đã có khóa. Nếu phía mô hình từ chối khóa đó thì đó là lỗi phía mô hình, không phải câu thiếu khóa.
- Môi trường tiến trình có khóa không được đọc, kể cả khi người gọi không đưa khóa.
- Câu thiếu khóa, câu lỗi phía mô hình, và câu hết lượt tool là ba câu khác nhau.
- Quá thời gian chờ, bị từ chối vì quá nhiều yêu cầu, lỗi máy chủ, mất mạng, và vượt 20 giây của cả lượt dùng chung một câu lỗi phía mô hình. Không thử lại.
- Hủy tác vụ không thành câu lỗi, không thành câu hết lượt, và lần gọi đang dang dở không bắt buộc có dòng nhật ký. Những lần gọi mô hình đã xong trước đó vẫn giữ dòng của chúng.
- Hàm ghi của dòng mô hình ném lỗi thì nuốt. Dòng tool vẫn theo luật nuốt của spec điều phối tool, không đổi.
- Lát này không gọi mạng trong bộ test tự động. Lần thử tay với API thật, nếu có, không thuộc bộ đó.
- Không có luồng trả lời từng mảnh. Kết quả là một chuỗi sau khi lượt xong.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Một lượt MUST nhận tin nhắn mới của người dùng, danh sách tin nhắn trước đó, kho cho tool, và khóa do người gọi truyền. Kết quả thành công MUST là một chuỗi văn bản. Danh sách trước đó MAY rỗng.
- **FR-002**: Lượt MUST gửi tới mô hình đúng thứ tự danh sách trước đó, rồi tin mới. Lượt MUST NOT lưu danh sách đó, MUST NOT lưu tin mới, và MUST NOT lưu câu trả lời.
- **FR-003**: Khi mô hình đòi tool, lượt MUST chạy bằng `execute_tool` trên đúng kho người gọi đưa, rồi MUST gửi lại mô hình đúng nội dung `execute_tool` trả, không đổi chữ. Lặp tới khi mô hình trả văn bản và không đòi tool.
- **FR-004**: Một vòng là một phản hồi của mô hình có đòi tool. Mọi tool trong phản hồi đó MUST được chạy bằng `execute_tool` theo thứ tự phản hồi đưa, và mọi kết quả MUST được gửi lại trong lần gọi mô hình kế tiếp. Một lượt hội thoại MUST NOT có quá 3 vòng. Nếu phản hồi thứ tư vẫn đòi tool, lượt MUST NOT chạy tool nào của phản hồi đó, MUST NOT gọi mô hình thêm, và kết quả MUST là đúng `Chưa trả lời xong yêu cầu này.`
- **FR-005**: Danh sách tool trên yêu cầu gửi mô hình MUST là đúng `TOOL_DEFINITIONS`, gồm tên, mô tả, và schema đầu vào. Lượt MUST NOT chép một bộ định nghĩa thứ hai. Phiên bản trong nhật ký mô hình MUST là phiên bản của bộ đó.
- **FR-006**: Lời hướng dẫn hệ thống MUST nằm một chỗ, số phiên bản `1`, và MUST được gửi ở mỗi lần gọi mô hình của lượt. Nguyên văn MUST có bốn luật ở User Story 3, gồm đúng câu ví dụ về báo cáo thứ Sáu và chương 3. Nguyên văn MUST NOT chứa cụm "trợ lý lập kế hoạch" như cách người nói tự xưng, và MUST NOT đặt tên nhân vật nào khác JARVIS.
- **FR-007**: Model của yêu cầu MUST là `claude-haiku-5-5`. Yêu cầu MUST NOT bật chế độ suy nghĩ. Lát này MUST NOT nhận model khác từ người gọi.
- **FR-008**: Khóa MUST lấy từ đối số người gọi. Lượt MUST NOT đọc khóa từ môi trường tiến trình. Khi khóa không có hoặc là chuỗi rỗng, lượt MUST thất bại bằng đúng `Thiếu ANTHROPIC_API_KEY.` trước mọi lời gọi tới client, và câu đó MUST NOT chứa giá trị khóa.
- **FR-009**: Lỗi phía mô hình, gồm quá thời gian chờ, từ chối vì quá nhiều yêu cầu, lỗi máy chủ, và mất mạng, MUST trả đúng `Chưa liên lạc được để trả lời lúc này.` Chuỗi đó MUST NOT chứa thông điệp lỗi, mã trạng thái, địa chỉ, tên loại lỗi, hay giá trị khóa. Lượt MUST NOT thử gọi lại.
- **FR-010**: Sau khi cả lượt đã dùng hết 20 giây, lượt MUST NOT bắt đầu lời gọi mô hình hay lần chạy tool mới và MUST trả câu lỗi ở FR-009. Lời gọi mô hình đang chạy được giới hạn bằng timeout bằng phần ngân sách còn lại; lần execute_tool đã bắt đầu không bị cắt. Phản hồi của lời gọi đã bắt đầu trước mốc vẫn được dùng.
- **FR-011**: Hủy tác vụ MUST đi tiếp ra ngoài lượt, MUST NOT bị đổi thành câu FR-009 hay câu FR-004. Lần gọi mô hình đang dang dở khi bị hủy MUST NOT bắt buộc có dòng nhật ký.
- **FR-012**: Mỗi lần gọi mô hình đã kết thúc MUST ghi đúng một dòng, là một object với đúng các khóa ở Assumptions, theo thứ tự đó. Lần lỗi cũng MUST có một dòng. Phần lỗi trên dòng MUST chỉ là tên loại lỗi, MUST NOT chứa thông điệp lỗi. Dòng tool MUST có đúng bảy khóa D-014 và MUST NOT đổi so với D-014. Hai loại dòng phân biệt bằng khóa `model` và khóa `tool`.
- **FR-013**: Nếu hàm ghi của dòng mô hình ném lỗi, lượt MUST nuốt lỗi đó và vẫn trả kết quả của lượt. MUST NOT nuốt việc hủy tác vụ.
- **FR-014**: Lượt MUST nhận kho đã có. Lượt MUST NOT tự dựng kho thật. Mọi lời gọi mô hình của lượt MUST đi qua một cổng trung lập với nhà cung cấp. Lõi của lượt MUST NOT phụ thuộc SDK của nhà cung cấp. Adapter của nhà cung cấp MUST nằm ngoài lõi đó.
- **FR-015**: Bộ test tự động của lát này MUST NOT mở mạng và MUST NOT gọi mô hình thật. Client giả MUST trả chuỗi phản hồi định sẵn. Lần thử tay với API thật, nếu có, MUST NOT nằm trong bộ test tự động.

### Key Entities

- **Lượt hội thoại**: Tin nhắn mới, danh sách tin trước, kho, và khóa. Cho ra một chuỗi, hoặc lỗi thiếu khóa. Không lưu lại sau khi trả.
- **Vòng tool**: Một phản hồi của mô hình có đòi tool. Mọi tool trong phản hồi đó được chạy. Tối đa ba vòng trong một lượt hội thoại.
- **Lời hướng dẫn**: Một văn bản, số phiên bản `1`, bốn luật ở User Story 3.
- **Bộ định nghĩa tool**: Bộ đã có của spec điều phối tool. Lượt này chỉ đọc.
- **Dòng nhật ký lần gọi mô hình**: Một object cho một lần gọi mô hình đã kết thúc. Không phải dòng tool, không phải hội thoại đã lưu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lượt mà mô hình trả văn bản và không đòi tool trả đúng văn bản đó, kể cả chuỗi rỗng. 100% lượt như vậy không gọi kho.
- **SC-002**: 100% lượt giữ nguyên thứ tự lịch sử người gọi đưa, rồi tin mới. 0 lượt lưu thêm hội thoại.
- **SC-003**: 100% tool trong một vòng được chạy bằng `execute_tool` trên đúng kho, theo thứ tự phản hồi, và 100% kết quả của vòng được gửi lại ở lần gọi mô hình kế tiếp, cho tới khi đủ 3 vòng. 0 phản hồi thứ tư còn đòi tool được chạy tool. 100% lượt gặp phản hồi thứ tư như vậy trả đúng `Chưa trả lời xong yêu cầu này.`
- **SC-004**: 100% nội dung `execute_tool` trả được gửi lại mô hình không đổi chữ.
- **SC-005**: 100% yêu cầu gửi mô hình dùng đúng `TOOL_DEFINITIONS` và lời hướng dẫn phiên bản `1`. 100% lần đọc lời hướng dẫn thấy đủ bốn luật, đúng câu ví dụ, thấy JARVIS là nhân vật duy nhất, và thấy lệnh không được tự xưng "trợ lý lập kế hoạch".
- **SC-006**: 100% yêu cầu dùng model `claude-haiku-5-5` và không bật chế độ suy nghĩ. 100% lượt thiếu khóa hoặc khóa rỗng thất bại bằng đúng câu thiếu khóa, trước mọi lời gọi client, và không đọc khóa từ môi trường tiến trình.
- **SC-007**: 100% lỗi phía mô hình và 100% lượt đã dùng hết 20 giây trả đúng câu lỗi phía mô hình, và không bắt đầu lời gọi mô hình hay lần chạy tool mới. Lời gọi mô hình đang chạy được giới hạn bằng timeout bằng phần ngân sách còn lại; lần execute_tool đã bắt đầu không bị cắt. Phản hồi của lời gọi đã bắt đầu trước mốc vẫn được dùng. 0 kết quả chứa thông điệp lỗi, địa chỉ, mã trạng thái, hoặc giá trị khóa. 0 lần thử gọi lại.
- **SC-008**: 100% lần hủy tác vụ đi ra khỏi lượt và không thành câu trả lời.
- **SC-009**: 100% lần gọi mô hình đã kết thúc có đúng một dòng nhật ký đúng khóa FR-012. 100% dòng lỗi không chứa thông điệp lỗi. 100% dòng tool trong lượt vẫn đúng bảy khóa D-014. 100% lần hàm ghi ném lỗi vẫn trả được kết quả của lượt.
- **SC-010**: 100% ca trong bộ test tự động chạy bằng client giả và không mở mạng.

## Assumptions

- Người gọi của lát này là bộ eval và, sau này, bot Telegram. Người dùng cuối chỉ thấy chuỗi kết quả hoặc, khi thiếu khóa, lỗi cấu hình cho người gọi chứ không phải một câu chat.
- Ba câu do dự án chọn, vì yêu cầu gốc giao dự án viết chữ. Câu hết lượt tool: `Chưa trả lời xong yêu cầu này.` Câu lỗi phía mô hình, gồm vượt ngân sách: `Chưa liên lạc được để trả lời lúc này.` Câu thiếu khóa: `Thiếu ANTHROPIC_API_KEY.` Câu thiếu khóa không chứa giá trị khóa. Hai câu trả cho người dùng không chứa chữ "tool".
- Một vòng là một phản hồi của mô hình có đòi tool, không đếm bằng số lần `execute_tool`. Mọi tool trong vòng chạy theo thứ tự phản hồi đưa, rồi mọi kết quả đi cùng lần gọi mô hình kế tiếp. Phản hồi thứ tư còn đòi tool thì không chạy tool nào của phản hồi đó.
- Văn bản cuối rỗng là thành công. Không suy ra lỗi từ chuỗi rỗng.
- Chuỗi khóa chỉ khoảng trắng không bị cắt và không bị coi là thiếu. Cách này cùng luật với khóa kho: chỉ chuỗi rỗng hoặc không có là thiếu.
- Ngân sách cả lượt là 20 giây, tính mọi lần gọi mô hình và mọi lần chạy tool. Spike đo một lượt có một lần tool mất 5 đến 7 giây. Vượt 20 giây dùng câu lỗi phía mô hình.
- D-002 giữ một nhân vật JARVIS. Prompt cấm tự xưng "trợ lý lập kế hoạch" và cấm tên nhân vật khác. D-004 vẫn ghi Haiku 4.5; lát này khóa model `claude-haiku-5-5` theo yêu cầu gốc. Sửa chữ D-004 không thuộc bước spec này.
- Nguyên tắc IV giữ: lời gọi mô hình đi qua cổng trung lập, không hardcode nhà cung cấp trong lõi. Adapter và chỗ đặt file do plan chốt. SDK nhà cung cấp không đi vào lõi.
- Bảy khóa dòng tool không đổi: `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`.
- Dòng lần gọi mô hình có đúng tám khóa, theo thứ tự: `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`. `prompt_version` và `definitions_version` là số, không phải chuỗi. `error_type` trống khi lần gọi thành công. Khi lỗi, `error_type` là tên loại lỗi, không kèm thông điệp. `stop_reason`, `input_tokens`, và `output_tokens` trống khi lần gọi không trả các giá trị đó. `duration_ms` là số nguyên không âm, có thể bằng 0. Chữ tiếng Việt ghi lại không bị đổi thành mã thoát.
- Hủy tác vụ là `CancelledError`, cùng luật với spec điều phối tool: đi tiếp, không thành kết quả, lần dang dở không bắt buộc có dòng.
- Hàm ghi ném lỗi thuộc loại Exception thì nuốt. Hủy tác vụ không bị nuốt.
- Bộ test tự động dùng client giả. Smoke với API thật, nếu làm, là việc tay và không tính vào bộ đó.
- Ngoài phạm vi, theo mô tả tính năng:
  - Route webhook, Telegram, dựng kho thật, và chặn theo chat id.
  - Lưu lịch sử hội thoại.
  - Bộ eval khoảng 50 câu và việc chấm mô hình thật có tuân thủ bốn luật hay không.
  - Trả lời theo từng mảnh.
  - Thử lại khi lỗi mạng hoặc lỗi phía mô hình.
  - Đổi sáu tool, đổi bảy khóa dòng tool, hoặc đổi lược đồ kho.
