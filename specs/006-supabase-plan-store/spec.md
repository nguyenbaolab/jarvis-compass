# Feature Specification: Lưu kế hoạch vào kho riêng

**Feature Branch**: `006-supabase-plan-store`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "F03: lưu kế hoạch vào Supabase thật. Một bản cài đặt cổng lưu kế hoạch giữ đúng hợp đồng hiện tại như bản trong bộ nhớ của test: thêm thì gán danh tính kế hoạch và thứ tự tạo, giữ nguyên mục tiêu cùng danh tính, tiêu đề, trạng thái, ghi chú và thứ tự của việc con; liệt kê thì kế hoạch mới hơn đứng trước; mở thì trả đúng kế hoạch hoặc không có; thay thì thay kế hoạch cùng danh tính, gồm toàn bộ việc con. Lược đồ nằm trong repo, dựng lại được từ đầu trên một kho trống. Địa chỉ và khóa đọc từ cấu hình, do nơi gọi truyền vào, đúng cả khi môi trường của tiến trình trống lẫn khi kiểm thử. Mỗi việc con lưu thêm thời điểm tạo và thời điểm đổi trạng thái gần nhất. Hai mốc chỉ nằm trong kho, không vào mô hình miền và không ra kết quả tool. Mọi hành vi của cổng được kiểm trên kho thật. Ghi chú trống là không có ghi chú, không bao giờ là chuỗi rỗng. Chữ tiếng Việt đã chuẩn hóa đọc ra giữ nguyên từng ký tự. Danh tính kế hoạch là UUID; chuỗi 1 hay 2 không trỏ tới một kế hoạch. Thứ tự việc con đọc ra đúng thứ tự đã lưu. Thay một danh tính không có thì báo lỗi, không im lặng và không tạo mới. Kho chứa trạng thái lạ thì đọc báo lỗi rõ, không trả việc con mang trạng thái sai. Thời điểm đổi trạng thái chỉ thay khi trạng thái thật sự đổi. 129 kiểm tra hiện có vẫn chạy khi kho không bật. Kiểm tra với kho thật tách riêng; khi kho local không chạy thì bị bỏ qua và lý do bỏ qua được in rõ. Ngoài phạm vi: nối vào HTTP, Telegram, LLM; đưa lược đồ lên kho cloud; ghi đồng thời; giới hạn độ dài; xóa kế hoạch; nhiều người; xác thực; lưu phiên hay hội thoại; đổi mô hình miền hay hình kết quả tool."

## Clarifications

### Session 2026-10-25

- Q: Thay một danh tính không có áp cho bản cài đặt nào, và hai bản được giữ cho khớp bằng cách nào? → A: FR-006 áp cho mọi bản cài đặt của cổng, gồm bản trong bộ nhớ dùng cho kiểm tra. Một bộ kiểm tra hợp đồng chạy trên bản trong bộ nhớ (luôn chạy, không cần kho) và trên bản kho thật (bỏ qua khi kho local không chạy, theo FR-016). Kỳ vọng của 129 kiểm tra hiện có không đổi. Không có kiểm tra hiện có nào phụ thuộc im lặng; nếu khi làm phát hiện một kiểm tra như vậy thì dừng và hỏi.
- Q: Dựng kho khi thiếu địa chỉ hoặc khóa thì thế nào? → A: Thất bại ngay bằng một lỗi nói thiếu giá trị nào, trước mọi lời gọi mạng. Lời lỗi không chứa giá trị của khóa.

## User Scenarios & Testing *(mandatory)*

Người dùng cần kế hoạch đã chốt còn đó sau khi lần làm việc kết thúc, rồi sửa việc con và xem lại đúng những gì đã lưu. Đây là F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md): kho riêng là nguồn sự thật cho kế hoạch và việc con. Tạo, liệt kê, mở, đổi trạng thái, thêm việc con, và ghi chú đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec xem chi tiết](../002-get-plan-detail/spec.md), [spec cập nhật việc con](../003-update-subtask/spec.md), [spec thêm việc con](../004-add-subtask/spec.md), và [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Lát này giữ nguyên những hành vi đó và đưa bản đã lưu sang kho còn sau khi tiến trình tắt. Hai mốc thời gian trên mỗi việc con phục vụ việc điều chỉnh tải về sau; người dùng không thấy chúng trong câu trả lời.

### User Story 1 - Kế hoạch còn sau khi lần làm việc kết thúc (Priority: P1)

Khi một kế hoạch vừa được lưu, người dùng tắt phiên rồi mở lại vẫn thấy đúng kế hoạch đó: cùng danh tính, cùng mục tiêu, cùng từng việc con. Kế hoạch lưu sau đứng trước kế hoạch lưu trước. Mở bằng danh tính thì ra đúng kế hoạch. Mở bằng danh tính không có thì không ra kế hoạch nào.

**Why this priority**: Không có bản còn lại thì F04 đến F08 chỉ sống trong bộ nhớ của lần kiểm tra. Constitution, nguyên tắc II và VI, bắt trạng thái nằm ở kho riêng.

**Independent Test**: Trên một kho trống vừa dựng từ repo, lưu hai kế hoạch, kết thúc lần ghi, rồi liệt kê và mở lại. Không cần HTTP, Telegram, hay LLM.

**Acceptance Scenarios**:

1. **Given** một kho trống đã dựng xong từ bản lược đồ trong repo, **When** lưu kế hoạch "Học tiếng Nhật" với hai việc con "Học hiragana" rồi "Luyện 10 phút mỗi ngày", **Then** kết quả có một danh tính kế hoạch mới và đúng mục tiêu, đúng danh tính, tiêu đề, trạng thái `pending`, ghi chú trống, và thứ tự của hai việc con.
2. **Given** kế hoạch ở tình huống 1 đã lưu, và sau đó lưu thêm kế hoạch "Viết báo cáo" không có việc con, **When** liệt kê, **Then** "Viết báo cáo" đứng trước "Học tiếng Nhật". Mỗi kế hoạch giữ danh tính đã cấp lúc lưu.
3. **Given** hai kế hoạch đã lưu, **When** mở bằng đúng danh tính của "Học tiếng Nhật", **Then** ra đúng kế hoạch đó, cùng mục tiêu và cùng hai việc con theo thứ tự đã lưu.
4. **Given** hai kế hoạch đã lưu, **When** mở bằng một danh tính không có trong kho, **Then** không có kế hoạch nào được trả về. Hai kế hoạch đã lưu không đổi.
5. **Given** một kho hoàn toàn trống, **When** dựng lược đồ từ bản trong repo, **Then** kho nhận được kế hoạch như tình huống 1. Không cần chép dữ liệu từ một kho khác.

---

### User Story 2 - Sửa việc con và đọc lại đúng chữ đã lưu (Priority: P1)

Người dùng đổi trạng thái, thêm một việc con, đặt ghi chú, rồi xóa ghi chú. Lần đọc sau thấy đúng các thay đổi đó. Chữ tiếng Việt giữ nguyên từng ký tự. Ghi chú trống không trở thành một chuỗi rỗng. Thứ tự việc con không tự xếp lại.

**Why this priority**: Kho chỉ đáng tin nếu sửa và đọc lại khớp những gì người dùng vừa làm, kể cả tiếng Việt và ghi chú trống.

**Independent Test**: Lưu một kế hoạch có hai việc con. Đổi trạng thái việc thứ nhất, thêm một việc, đặt ghi chú, rồi xóa ghi chú. Mỗi lần đọc lại kế hoạch.

**Acceptance Scenarios**:

1. **Given** kế hoạch "Học tiếng Nhật" với "Học hiragana" đang `pending`, **When** đặt việc đó thành `done`, rồi thành `skipped`, rồi lại thành `pending`, **Then** mỗi lần đọc lại thấy đúng trạng thái vừa đặt. Việc kia, tiêu đề, ghi chú, danh tính, mục tiêu, và thứ tự không đổi.
2. **Given** kế hoạch đang có hai việc con, **When** thêm "Mua giáo trình", **Then** việc mới đứng cuối, trạng thái `pending`, ghi chú trống. Hai việc cũ giữ danh tính, tiêu đề, trạng thái, ghi chú, và thứ tự tương đối.
3. **Given** một việc chưa có ghi chú, **When** đặt ghi chú "Đợi giáo trình", **Then** lần đọc sau ghi chú là "Đợi giáo trình". Trạng thái không đổi.
4. **Given** việc đó đang có ghi chú, **When** đặt ghi chú thiếu, rỗng, hoặc chỉ khoảng trắng, **Then** lần đọc sau việc đó không có ghi chú. Kho không giữ một chuỗi rỗng cho ghi chú đó.
5. **Given** mục tiêu và việc con là chữ tiếng Việt đã chuẩn hóa, gồm "Học tiếng Nhật" và "Học hiragana", **When** lưu rồi đọc lại, **Then** từng ký tự đọc ra trùng từng ký tự đã lưu.
6. **Given** một kế hoạch có ba việc con theo một thứ tự đã lưu, **When** đọc bằng liệt kê và bằng mở, **Then** cả hai cách đều ra đúng thứ tự đó, không xếp theo bảng chữ cái hay theo đồng hồ.

---

### User Story 3 - Dữ liệu không dùng được thì dừng rõ (Priority: P1)

Người dùng, hoặc lần ghi sau, không được tưởng một kế hoạch đã được tạo khi danh tính không có. Chuỗi "1" hay "2" không bao giờ mở được một kế hoạch. Nếu dữ liệu đọc từ kho chứa trạng thái lạ, lần đọc phải dừng với một lỗi rõ, không đưa việc đó ra như một việc hợp lệ.

**Why this priority**: Im lặng khi thay một danh tính không có sẽ tạo kế hoạch thừa hoặc nuốt một lần sửa. Trả một trạng thái lạ làm các bước sau hiểu sai tiến độ.

**Independent Test**: Lưu một kế hoạch trên bản trong bộ nhớ và trên kho thật. Thay bằng một danh tính khác không có. Mở bằng "1" và bằng "2". Với dữ liệu đọc từ kho chứa trạng thái lạ, đọc kế hoạch đó.

**Acceptance Scenarios**:

1. **Given** bản trong bộ nhớ đang có một kế hoạch, và kho thật cũng đang có một kế hoạch, **When** mỗi bản thay một kế hoạch có danh tính không có trong bản đó, **Then** cả hai lần đều thất bại bằng đúng câu `Không có kế hoạch với danh tính này.` Không bản nào thêm kế hoạch mới. Kế hoạch đang có trên bản đó không đổi.
2. **Given** đã lưu một hoặc nhiều kế hoạch, **When** mở bằng chuỗi "1" hoặc "2", **Then** không có kế hoạch nào được trả về.
3. **Given** danh tính kế hoạch vừa lưu, **When** nhìn danh tính đó, **Then** đó là một UUID. Danh tính này không trùng "1" hay "2".
4. **Given** dữ liệu đọc từ kho chứa trạng thái lạ, **When** đọc kế hoạch đó, **Then** lần đọc thất bại bằng đúng câu `Trạng thái việc con đã lưu không hợp lệ.` Không có kết quả thành công nào chứa việc con với trạng thái đó.

---

### User Story 4 - Hai mốc thời gian chỉ để dùng sau (Priority: P2)

Mỗi việc con trong kho có thời điểm được tạo và thời điểm trạng thái đổi gần nhất. Người dùng không thấy hai mốc này trong kế hoạch mà tool trả về. Mốc đổi trạng thái đứng yên khi lần ghi không thực sự đổi trạng thái.

**Why this priority**: Hai mốc là dữ liệu cho việc điều chỉnh tải theo người dùng về sau. Chúng không được làm đổi câu trả lời hiện tại.

**Independent Test**: Lưu một việc con, đọc hai mốc trong kho, đọc kế hoạch qua tool. Ghi lại cùng trạng thái, rồi ghi một trạng thái khác. So hai mốc trước và sau mỗi lần ghi.

**Acceptance Scenarios**:

1. **Given** một việc con vừa được lưu lần đầu, **When** xem bản trong kho, **Then** việc đó có thời điểm tạo và thời điểm trạng thái gần nhất. Cả hai là thời điểm của lần ghi đó.
2. **Given** việc đó vừa lưu, **When** xem kế hoạch qua tạo, liệt kê, mở, đổi trạng thái, thêm việc con, hoặc đặt ghi chú, **Then** kết quả không có hai mốc thời gian này.
3. **Given** một việc đã có hai mốc, **When** ghi lại kế hoạch với cùng trạng thái của việc đó, kể cả khi ghi chú hoặc tiêu đề đổi, **Then** thời điểm tạo và thời điểm trạng thái gần nhất giữ nguyên từng giá trị đã có.
4. **Given** một việc đang `pending`, **When** ghi lại việc đó với trạng thái `done`, **Then** thời điểm tạo giữ nguyên. Thời điểm trạng thái gần nhất trở thành thời điểm của lần ghi vừa đổi trạng thái.
5. **Given** một kế hoạch đã có việc con, **When** thêm một việc con mới, **Then** chỉ việc mới nhận hai mốc của lần thêm. Các việc cũ giữ thời điểm tạo và thời điểm trạng thái của chúng.

---

### Edge Cases

- Mở một danh tính không có là "không có kế hoạch", không phải lỗi. Thay một danh tính không có là lỗi trên mọi bản cài đặt của cổng, gồm bản trong bộ nhớ, không tạo mới và không im lặng. Hai tình huống này không dùng chung một kết quả.
- Dựng bản kho thật khi địa chỉ kho không có hoặc rỗng, khi khóa không có hoặc rỗng, hoặc khi cả hai cùng thiếu: thất bại ngay, lỗi nêu từng giá trị đang thiếu, không gọi mạng, và không chứa giá trị của khóa. Bản trong bộ nhớ không cần địa chỉ hay khóa.
- Danh tính kế hoạch do kho cấp lúc thêm, là UUID. Người gọi không chọn danh tính đó. "1" và "2" không phải danh tính của bất kỳ kế hoạch nào kho cấp.
- Ghi chú trống, gồm thiếu, chuỗi rỗng, hoặc chỉ khoảng trắng sau chuẩn hóa đã chốt ở [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md), được lưu là không có ghi chú. Lần đọc trả ghi chú trống, không trả chuỗi rỗng.
- Chữ đã chuẩn hóa NFC trước khi vào kho. Kho không chuẩn hóa lại và không đổi ký tự khi đọc ra.
- Thứ tự việc con là thứ tự đã lưu trong kế hoạch, không phải thứ tự bảng chữ cái và không phải thứ tự đồng hồ của hai mốc thời gian.
- Thay một kế hoạch làm bản việc con trong kho khớp đúng danh sách được đưa: cùng danh tính việc con, cùng thứ tự, cùng tiêu đề, trạng thái, và ghi chú. Việc con không còn trong danh sách thì không còn được đọc ra. Việc con giữ nguyên danh tính thì giữ thời điểm tạo. Thời điểm trạng thái của việc đó chỉ đổi khi mã trạng thái đổi.
- Trạng thái hợp lệ khi đọc vẫn chỉ là `pending`, `done`, và `skipped`, như [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Dữ liệu đọc từ kho chứa trạng thái lạ làm lần đọc thất bại cả kế hoạch, không bỏ qua riêng việc đó và cũng không sửa giá trị đó thành một mã hợp lệ.
- Đặt lại đúng trạng thái đang có không đổi thời điểm trạng thái. Đặt lại đúng ghi chú đang có vẫn theo luật không ghi lại của [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md) ở tầng tool. Lát này không đổi luật đó.
- Hai lần ghi cùng một kế hoạch diễn ra cùng lúc có thể làm mất một lần. Đây là giới hạn đã chấp nhận, không phải lỗi phải chặn trong lát này.
- Khi kho dùng cho kiểm tra thật không chạy, các kiểm tra cần kho đó bị bỏ qua và lời bỏ qua nói rõ kho không chạy. Các kiểm tra không cần kho đó vẫn chạy và vẫn đạt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST lưu kế hoạch và việc con vào kho còn sau khi tiến trình ghi đã kết thúc. Hành vi thêm, liệt kê mới hơn trước, mở theo danh tính, và thay cả kế hoạch MUST khớp hợp đồng đã chốt ở các spec F04 đến F08, trừ FR-006.
- **FR-002**: Thêm một kế hoạch MUST cấp danh tính kế hoạch mới và thứ tự tạo. Mục tiêu MUST được giữ nguyên. Mỗi việc con MUST giữ nguyên danh tính, tiêu đề, trạng thái, ghi chú, và vị trí trong danh sách đã đưa vào.
- **FR-003**: Liệt kê MUST trả mọi kế hoạch đã lưu, kế hoạch có thứ tự tạo lớn hơn đứng trước. Mở bằng đúng danh tính MUST trả đúng một kế hoạch đó. Mở bằng danh tính không có MUST trả kết quả không có kế hoạch, và MUST NOT tạo kế hoạch.
- **FR-004**: Thay một kế hoạch đang có MUST thay toàn bộ việc con của đúng danh tính đó bằng danh sách được đưa, giữ thứ tự của danh sách đó. Việc con còn danh tính cũ MUST giữ thời điểm tạo. Việc con không còn trong danh sách MUST không còn được đọc ra.
- **FR-005**: Repo MUST chứa bản dựng lược đồ, đủ để một kho trống trở thành nơi lưu kế hoạch và việc con khi chạy bản đó từ đầu. Không cần dữ liệu có sẵn từ một kho khác.
- **FR-006**: Mọi bản cài đặt của cổng lưu kế hoạch, gồm bản trong bộ nhớ dùng cho kiểm tra và bản kho thật, khi thay một kế hoạch có danh tính không có MUST thất bại bằng đúng câu `Không có kế hoạch với danh tính này.` Bản đó MUST NOT thêm kế hoạch mới và MUST NOT đổi các kế hoạch đang có.
- **FR-007**: Danh tính kế hoạch do hệ thống cấp MUST là UUID. Mở bằng "1" hoặc "2" MUST trả kết quả không có kế hoạch.
- **FR-008**: Ghi chú trống MUST được lưu là không có ghi chú, không bao giờ là chuỗi rỗng. Đọc lại MUST trả ghi chú trống, không trả chuỗi rỗng.
- **FR-009**: Chữ tiếng Việt đã chuẩn hóa NFC trước khi lưu MUST được đọc ra trùng từng ký tự đã lưu.
- **FR-010**: Thứ tự việc con đọc bằng liệt kê và bằng mở MUST trùng thứ tự đã lưu, không phụ thuộc đồng hồ của việc con.
- **FR-011**: Nếu dữ liệu đọc từ kho chứa trạng thái lạ, lần đọc kế hoạch đó MUST thất bại bằng đúng câu `Trạng thái việc con đã lưu không hợp lệ.` Lần đọc MUST NOT trả kế hoạch thành công và MUST NOT trả việc con mang trạng thái đó.
- **FR-012**: Mỗi việc con trong kho MUST có thời điểm tạo và thời điểm trạng thái gần nhất. Lần lưu đầu MUST đặt cả hai bằng thời điểm của lần ghi đó. Thời điểm tạo của một việc giữ nguyên danh tính MUST không đổi ở các lần ghi sau.
- **FR-013**: Thời điểm trạng thái gần nhất MUST đổi khi và chỉ khi lần ghi làm mã trạng thái của việc đó khác mã đang lưu. Ghi lại cùng mã trạng thái MUST giữ nguyên thời điểm đó, kể cả khi tiêu đề hoặc ghi chú đổi.
- **FR-014**: Hai mốc thời gian MUST chỉ có trong kho. Chúng MUST NOT xuất hiện trong mô hình miền và MUST NOT xuất hiện trong kết quả của tạo, liệt kê, mở, đổi trạng thái, thêm việc con, hay đặt ghi chú.
- **FR-015**: Địa chỉ kho và khóa MUST được lấy từ cấu hình do nơi gọi truyền vào, không ghi cứng trong mã. Khi tiến trình không có sẵn các giá trị đó, cấu hình của lời gọi vẫn MUST được dùng. Cùng một cách đọc MUST dùng được khi kiểm thử.
- **FR-016**: 129 kiểm tra hiện có MUST vẫn đạt khi kho thật không chạy, và kỳ vọng của chúng MUST không đổi. Kiểm tra cần kho thật MUST nằm riêng. Khi kho đó không chạy, các kiểm tra đó MUST bị bỏ qua và lời bỏ qua MUST nói rõ kho không chạy.
- **FR-017**: Một bộ kiểm tra hợp đồng của cổng MUST chạy trên bản trong bộ nhớ và MUST chạy trên bản kho thật, cùng các tình huống, để hai bản không lệch nhau. Lần chạy trên bản trong bộ nhớ MUST luôn chạy và MUST NOT cần kho. Lần chạy trên bản kho thật MUST bỏ qua khi kho local không chạy, theo FR-016.
- **FR-018**: Khi dựng bản kho thật, nếu địa chỉ kho không có hoặc rỗng, hoặc khóa không có hoặc rỗng, việc dựng MUST thất bại ngay, trước mọi lời gọi mạng. Lỗi MUST nói rõ từng giá trị đang thiếu. Lời lỗi MUST NOT chứa giá trị của khóa.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Đúng thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md): danh tính, mục tiêu, thứ tự tạo, và các việc con. Lát này không thêm thuộc tính nào mà người gọi nhìn thấy. Có mặt trong kho nghĩa là đang hoạt động, cùng nghĩa đã chốt.
- **Việc con**: Đúng thực thể ở [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md): danh tính, tiêu đề, trạng thái `pending`, `done`, hoặc `skipped`, và tối đa một ghi chú. Trong kho, mỗi việc con còn có thời điểm tạo và thời điểm trạng thái gần nhất. Hai mốc đó không thuộc bản người gọi nhìn thấy.
- **Bản dựng lược đồ**: Phần trong repo đủ để tạo cấu trúc kho trên một kho trống. Không phải dữ liệu kế hoạch của người dùng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% kế hoạch lưu thành công còn đủ danh tính, mục tiêu, và từng việc con khi đọc lại sau lúc tiến trình ghi đã kết thúc.
- **SC-002**: 100% lần liệt kê xếp kế hoạch lưu sau trước kế hoạch lưu trước. 100% lần mở bằng đúng danh tính trả về đúng kế hoạch đó.
- **SC-003**: 100% lần mở bằng danh tính không có, gồm chuỗi "1" và "2", không trả về một kế hoạch. 100% danh tính kế hoạch do hệ thống cấp là UUID.
- **SC-004**: 100% lần đổi trạng thái, thêm việc con, đặt ghi chú, và xóa ghi chú đọc lại đúng giá trị vừa lưu, cùng thứ tự việc con đã lưu.
- **SC-005**: 100% ghi chú trống đọc lại là không có ghi chú, không phải chuỗi rỗng. 100% chuỗi tiếng Việt đã chuẩn hóa đọc ra trùng từng ký tự đã lưu.
- **SC-006**: 100% lần thay một danh tính không có, trên bản trong bộ nhớ và trên bản kho thật, bị từ chối bằng cùng một câu. Số kế hoạch trên bản đó không tăng, và kế hoạch đang có không đổi.
- **SC-007**: 100% lần đọc, khi dữ liệu đọc từ kho chứa trạng thái lạ, bị từ chối và không trả việc con mang trạng thái đó.
- **SC-008**: 100% lần ghi không đổi mã trạng thái giữ nguyên thời điểm trạng thái gần nhất. 100% lần ghi đổi mã trạng thái cập nhật thời điểm đó và giữ nguyên thời điểm tạo của cùng việc.
- **SC-009**: 0 kết quả tool nào chứa thời điểm tạo hoặc thời điểm trạng thái của việc con.
- **SC-010**: 100% của 129 kiểm tra hiện có vẫn đạt khi kho thật không chạy, với đúng kỳ vọng đang có. Khi kho thật không chạy, mọi kiểm tra cần kho đó, gồm phần hợp đồng trên bản kho thật, đều bị bỏ qua và mỗi lần bỏ qua đều có lý do đọc được. Phần hợp đồng trên bản trong bộ nhớ vẫn chạy và đạt.
- **SC-011**: 100% lần dựng bản kho thật khi địa chỉ kho hoặc khóa không có hoặc rỗng thất bại trước mọi lời gọi mạng. Lỗi nêu đúng từng giá trị đang thiếu. 0 lời lỗi chứa giá trị của khóa.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Không có chia sẻ, phân quyền, hay xác thực trong lát này.
- Kho riêng đã chốt là Supabase, truy cập theo constitution nguyên tắc III và [docs/DECISIONS.md](../../docs/DECISIONS.md) D-010. Cổng bốn thao tác đã là bất đồng bộ theo D-012. Lát này cài bản lưu thật của cổng đó, không đổi tên thao tác, không đổi mô hình miền, và không đổi hình kết quả tool.
- Địa chỉ và khóa đến từ nơi gọi, đọc qua chỗ cấu hình duy nhất của constitution. Trên Worker, nơi gọi là môi trường của lời gọi chứ không phải biến môi trường của tiến trình, vì biến của tiến trình ở đó trống. Kiểm thử truyền cùng loại cấu hình đó vào.
- "Không có ghi chú" trong kết quả tool vẫn là giá trị trống đã chốt ở [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md), không phải chuỗi rỗng. Bản trong kho của ghi chú trống là không có giá trị, không phải chuỗi rỗng.
- Câu `Không có kế hoạch với danh tính này.` được dùng lại cho lần thay một danh tính không có, cùng câu đã chốt khi mở hoặc sửa một kế hoạch không có. Mở một danh tính không có vẫn là kết quả không có kế hoạch, không phải câu lỗi đó.
- Câu `Trạng thái việc con đã lưu không hợp lệ.` là câu mới, chỉ cho dữ liệu đã nằm trong kho mà không thuộc ba mã. Câu này khác câu từ chối đầu vào `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` Đầu vào sai vẫn dùng câu đầu vào, trước khi ghi.
- Thời điểm là một mốc tuyệt đối theo UTC. Lần lưu đầu đặt cả hai mốc bằng thời điểm lần ghi. So "giữ nguyên" là so đúng giá trị đã lưu, không làm tròn lại.
- Kỳ vọng của 129 kiểm tra hiện có không đổi. Đọc các kiểm tra đó lúc làm rõ spec: không có kiểm tra nào thay một danh tính không có rồi kỳ vọng im lặng. Nếu khi làm phát hiện một kiểm tra hiện có phụ thuộc hành vi im lặng cũ, việc làm MUST dừng và hỏi. Không sửa kỳ vọng của kiểm tra đó, không bỏ kiểm tra đó, và không giữ im lặng để đi tiếp.
- Hai lần ghi cùng lúc có thể làm mất một lần. Chấp nhận vì chỉ có một người dùng. Lát này không khóa, không thử lại, và không ghép hai lần ghi.
- Đưa lược đồ lên project Supabase trên cloud nằm ngoài lát này. Bản dựng trong repo chỉ phải chạy được trên một kho trống ở máy dev.
- Ngoài phạm vi, theo mô tả tính năng:
  - Nối kho vào route HTTP, Telegram, hay LLM (F11, F12).
  - Ghi đồng thời an toàn.
  - Giới hạn độ dài tiêu đề và ghi chú.
  - Xóa kế hoạch.
  - Nhiều người dùng và xác thực.
  - Lưu phiên làm việc hay hội thoại.
  - Đổi mô hình miền trong `src/core` hay hình kết quả của tool.
  - Trạng thái cấp kế hoạch và check-in (F10).
