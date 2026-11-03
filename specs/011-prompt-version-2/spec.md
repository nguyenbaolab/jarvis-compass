# Feature Specification: Lời hướng dẫn hệ thống phiên bản 2

**Feature Branch**: `011-prompt-version-2`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Lời hướng dẫn hệ thống phiên bản 2 cho JARVIS (PROMPT_VERSION = 2). Eval p1-d2 (prompt v1, definitions v2, bộ câu v1, claude-haiku-5-5) có các lỗi lặp: 46/150 câu trả lời dùng in đậm kiểu **...**, thường để làm tiêu đề nhóm Ngày 1; 8/150 lần tiêu đề việc con có tiền tố Ngày 1: hoặc Tuần 1:; 4 lần bot viết lại tiêu đề người dùng tự đưa để thêm điểm kết thúc; 4 câu trả lời lộ mã UUID; 2 lần bot hỏi người dùng mã kế hoạch thay vì tự tìm; 7 câu trả lời dùng chữ trạng thái tiếng Anh pending, done, skipped; 2 lần người dùng báo bỏ một việc khớp đúng một việc trong kho mà bot vẫn hỏi xác nhận. Telegram gửi tin không parse mode nên Markdown hiện thành ký tự thô. Giữ luật bản 1, thêm năm luật còn lại từ docs/PRODUCT.md §9 và quyết định đã duyệt 2026-11-01: chữ trơn; tiêu đề bot tự đặt không có tiền tố thứ tự; tiêu đề người dùng giữ nguyên từng chữ; không hiện và không hỏi mã, gọi trạng thái bằng tiếng Việt; báo xong hoặc bỏ thì khớp theo tên, đúng một việc thì cập nhật ngay. PROMPT_VERSION là 2 và log ghi prompt_version 2. Lời hướng dẫn vẫn là hằng, không đọc file lúc chạy. Test đang khóa nội dung bản 1 đổi trong cùng thay đổi. Không đổi tool definitions, DEFINITIONS_VERSION giữ 2, không đổi bộ câu eval, bộ chấm, SCORER_VERSION, runner, không thêm trường ngày, không đổi schema, không đẩy bot sang get_plan_detail. Không sửa docs/ ở bước specify. Hiệu quả hành vi đo sau merge bằng eval p2-d2, không phải điều kiện test."

## User Scenarios & Testing *(mandatory)*

Người dùng nhận câu trả lời của JARVIS trên Telegram. Tin gửi đi không có parse mode, nên dấu in đậm, dấu tiêu đề và bảng hiện thành ký tự thô. Eval p1-d2, lời hướng dẫn phiên bản 1, bộ định nghĩa phiên bản 2, bộ câu v1, cho thấy các lỗi lặp ở trên. Các con số đó là lý do làm lát này. Lát này không lấy "các lần đó trở thành đạt" làm điều kiện xong.

Lời hướng dẫn phiên bản 1 và bốn luật của nó đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Hành vi người dùng thấy đã chốt ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §9. Lát này nâng lời hướng dẫn lên phiên bản 2: giữ luật bản 1, thu hẹp luật "chỉ kể việc" vào việc sắp làm, và viết đủ các luật §9 mà bản 1 chưa nói. Bộ test đọc hằng lời hướng dẫn và dòng nhật ký của client giả. Bộ test không gọi mô hình thật và không chấm mô hình thật có nghe lời hay không.

### User Story 1 - Giữ JARVIS, và chỉ im tool khi người dùng kể việc sắp làm (Priority: P1)

Câu trả lời vẫn là JARVIS, bằng tiếng Việt, và không tự xưng trợ lý lập kế hoạch. Người dùng chỉ kể việc sắp làm, chưa nhờ lập kế hoạch, thì không gọi tool: tóm lại những việc vừa nói và hỏi có muốn lập kế hoạch không. Cùng ví dụ bản 1 về báo cáo thứ Sáu và chương 3. Người dùng nói một việc đã xong hoặc bỏ thì không đi vào luật này; việc đó theo luật khớp tên ở User Story 5.

**Why this priority**: Bản 1 đã chặn việc tạo kế hoạch khi người dùng chỉ kể việc. Nếu bản 2 bỏ luật đó, lỗi cũ quay lại. Nếu bản 2 áp luật đó cả khi người dùng báo xong hoặc bỏ, bot sẽ không cập nhật kho.

**Independent Test**: Đọc lời hướng dẫn một lần, không gọi mô hình. Thấy tên JARVIS, thấy lệnh trả lời tiếng Việt, thấy lệnh không tự xưng, thấy đúng câu ví dụ bản 1, và thấy câu phân biệt việc sắp làm với việc đã xong hoặc bỏ.

**Acceptance Scenarios**:

1. **Given** lời hướng dẫn phiên bản 2, **When** đọc nguyên văn, **Then** có câu `Bạn là JARVIS. Không dùng tên nhân vật nào khác.` Không có tên Friday hay tên nhân vật thứ hai. Cụm `trợ lý lập kế hoạch` chỉ đứng trong câu cấm tự xưng.
2. **Given** cùng lời hướng dẫn, **When** đọc nguyên văn, **Then** có câu `Trả lời bằng tiếng Việt.` và có đúng câu ví dụ `Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3` gắn với lệnh không gọi tool.
3. **Given** người dùng chỉ kể việc sắp làm và chưa nhờ lập kế hoạch, **When** đọc luật tương ứng, **Then** luật bảo không gọi tool, tóm lại những việc vừa nói, rồi hỏi có muốn lập kế hoạch không.
4. **Given** người dùng báo một việc đã xong hoặc báo bỏ một việc, **When** đọc lời hướng dẫn, **Then** luật "không gọi tool" không áp cho trường hợp đó. Lời hướng dẫn chỉ trường hợp đó sang luật khớp tên.

---

### User Story 2 - Câu trả lời là chữ trơn (Priority: P1)

Câu người dùng đọc không có in đậm, không có tiêu đề mở đầu bằng `#`, và không có bảng. Được đánh số `1.` và được gạch đầu dòng `- `. Muốn chia nhóm theo ngày trong câu trả lời thì viết một dòng chữ trơn, ví dụ `Ngày 1`, rồi mới tới các mục của nhóm đó. Dòng đó không phải tiêu đề việc con.

**Why this priority**: 46/150 câu trả lời in đậm, thường để làm nhãn nhóm. Trên Telegram các dấu đó hiện thành ký tự thô.

**Independent Test**: Đọc lời hướng dẫn một lần. Thấy lệnh cấm in đậm, cấm tiêu đề `#`, cấm bảng; thấy `1.` và `- ` được phép trong câu trả lời; thấy một dòng chữ trơn như `Ngày 1` được phép để chia nhóm.

**Acceptance Scenarios**:

1. **Given** lời hướng dẫn phiên bản 2, **When** đọc luật câu trả lời, **Then** luật cấm in đậm, cấm dòng tiêu đề mở đầu bằng `#`, và cấm bảng.
2. **Given** cùng luật, **When** đọc phần được phép, **Then** đánh số `1.` và gạch `- ` được phép trong câu trả lời.
3. **Given** câu trả lời cần chia theo ngày, **When** đọc luật, **Then** một dòng chữ trơn như `Ngày 1` đứng trước nhóm là được phép. Dòng đó không bị liệt vào tiền tố tiêu đề việc con.

---

### User Story 3 - Tiêu đề bot tự đặt không mang số thứ tự, tiêu đề người dùng giữ nguyên (Priority: P1)

Thứ tự việc con là vị trí trong danh sách. Tiêu đề do bot tự đặt không mở đầu bằng tiền tố thứ tự, ví dụ `Ngày 1:`, `Tuần 1:`, `Bước 1`, hay `1.` Tiêu đề người dùng tự đưa được giữ nguyên từng chữ, kể cả khi chữ đó không có điểm kết thúc đo được hoặc trông như một thói quen. Luật điểm kết thúc đo được chỉ áp cho tiêu đề bot tự đặt. Bot không tự đặt việc kiểu thói quen suốt một khoảng thời gian, và không viết lại tiêu đề người dùng để thêm điểm kết thúc.

**Why this priority**: 8/150 tiêu đề bot có tiền tố ngày hoặc tuần. 4 lần bot sửa tiêu đề người dùng vừa đưa. Hai lỗi đó làm kho lệch với lời người dùng đã nói.

**Independent Test**: Đọc lời hướng dẫn một lần. Với một tiêu đề bot tự đặt, thấy lệnh cấm các tiền tố. Với một tiêu đề người dùng đưa sẵn, thấy lệnh giữ nguyên từng chữ và thấy lệnh không áp điểm kết thúc đo được vào tiêu đề đó.

**Acceptance Scenarios**:

1. **Given** bot tự đặt tiêu đề việc con, **When** đọc luật tiêu đề, **Then** tiêu đề không có tiền tố thứ tự. Các ví dụ bị cấm gồm `Ngày 1:`, `Tuần 1:`, `Bước 1`, và `1.` Thứ tự là vị trí trong danh sách.
2. **Given** người dùng tự đưa tiêu đề `Tập chạy`, **When** bot ghi việc đó, **Then** tiêu đề lưu đúng từng chữ `Tập chạy`. Bot không thêm điểm kết thúc vào tiêu đề này.
3. **Given** người dùng tự đưa tiêu đề đã có tiền tố, ví dụ `Ngày 1: nộp báo cáo`, **When** bot ghi đúng tiêu đề người dùng đã nói, **Then** tiêu đề được giữ nguyên từng chữ. Luật cấm tiền tố không sửa tiêu đề người dùng đã đưa.
4. **Given** bot tự đặt một việc con, **When** đọc luật điểm kết thúc, **Then** việc đó phải có điểm kết thúc đo được, và không phải việc kiểu thói quen suốt một khoảng thời gian. Luật này không bắt người dùng đổi một tiêu đề họ đã đưa.

---

### User Story 4 - Không lộ mã, và nói trạng thái bằng tiếng Việt (Priority: P1)

Câu trả lời không chứa mã kế hoạch hay mã việc con. Bot không hỏi người dùng mã đó. Khi cần mã để gọi tool, bot tự tìm. Trong câu người dùng đọc, trạng thái được gọi là `chưa làm`, `xong`, và `bỏ qua`. Ba chữ tiếng Anh `pending`, `done`, `skipped` không xuất hiện trong câu trả lời.

**Why this priority**: 4 câu trả lời lộ mã. 2 lần bot hỏi người dùng mã kế hoạch. 7 câu trả lời đọc trạng thái bằng tiếng Anh. Người dùng không có mã để đưa, và không cần thấy mã.

**Independent Test**: Đọc lời hướng dẫn một lần. Thấy lệnh không hiện mã, không hỏi mã, và tự tìm khi cần. Thấy ba chữ trạng thái tiếng Việt dành cho câu trả lời, và thấy lệnh không dùng ba chữ tiếng Anh đó trong câu trả lời.

**Acceptance Scenarios**:

1. **Given** bot cần nói về một kế hoạch hoặc một việc con, **When** đọc luật câu trả lời, **Then** câu trả lời không chứa mã kế hoạch và không chứa mã việc con. Bot không hỏi người dùng mã. Bot tự tìm mã khi cần gọi tool.
2. **Given** bot nói trạng thái một việc trong câu trả lời, **When** đọc luật, **Then** ba cách gọi là `chưa làm`, `xong`, và `bỏ qua`. Luật cấm dùng `pending`, `done`, và `skipped` trong câu trả lời.
3. **Given** bot gọi tool để đặt trạng thái, **When** đọc lời hướng dẫn, **Then** lời đó không bảo đưa `chưa làm`, `xong`, hay `bỏ qua` vào giá trị trạng thái của tool. Ba giá trị tool giữ nguyên như bộ định nghĩa phiên bản 2.

---

### User Story 5 - Báo xong hoặc bỏ: đúng một việc thì cập nhật ngay (Priority: P1)

Người dùng báo đã xong một việc, hoặc báo bỏ một việc. Bot tìm theo tên việc họ nói. Khớp đúng một việc thì cập nhật ngay và không hỏi xác nhận. Khớp không việc nào, hoặc khớp nhiều việc, thì hỏi lại cho rõ việc nào. Mọi nhánh đều không đòi bằng chứng.

**Why this priority**: 2 lần việc bỏ khớp đúng một việc trong kho mà bot vẫn hỏi xác nhận. Hỏi lại lúc đã khớp một việc làm người dùng phải nhắc cùng một việc lần nữa.

**Independent Test**: Đọc lời hướng dẫn một lần. Thấy đủ ba nhánh: một việc, không việc, nhiều việc. Thấy cả "đã xong" và "bỏ". Thấy lệnh không hỏi xác nhận khi đúng một việc, và thấy lệnh không đòi bằng chứng ở cả ba nhánh.

**Acceptance Scenarios**:

1. **Given** kho có đúng một việc khớp tên người dùng vừa nói, **When** người dùng báo việc đó đã xong, **Then** luật bảo cập nhật ngay và không hỏi xác nhận.
2. **Given** kho có đúng một việc khớp tên người dùng vừa nói, **When** người dùng báo bỏ việc đó, **Then** luật bảo cập nhật ngay và không hỏi xác nhận.
3. **Given** không việc nào khớp tên đó, hoặc nhiều việc cùng khớp, **When** người dùng báo xong hoặc báo bỏ, **Then** luật bảo hỏi lại. Hỏi lại không kèm đòi bằng chứng, và không kèm hỏi mã.
4. **Given** một trong ba nhánh trên, **When** đọc luật, **Then** không có nhánh nào bảo người dùng đưa bằng chứng.

---

### User Story 6 - Phiên bản 2 trên lời hướng dẫn và trên dòng nhật ký (Priority: P2)

Lời hướng dẫn là một hằng, số phiên bản `2`, không đọc từ file lúc chạy. Mỗi lần gọi mô hình trong lượt gửi cùng hằng đó. Dòng nhật ký của lần gọi đã kết thúc ghi `prompt_version` bằng `2`. Số phiên bản bộ định nghĩa tool giữ `2`. Tập khóa của dòng nhật ký không thêm và không bớt.

**Why this priority**: Lần đo sau chỉ được khác một biến, là lời hướng dẫn. Số trên dòng nhật ký là dấu hiệu để tách kết quả đó khỏi eval p1-d2.

**Independent Test**: Đọc số phiên bản lời hướng dẫn. Chạy một lượt bằng client giả, không mở mạng, và đọc dòng nhật ký của lần gọi mô hình. Số lời hướng dẫn là `2`. Khóa `prompt_version` trên dòng đó là `2`. Khóa `definitions_version` trên dòng đó là `2`.

**Acceptance Scenarios**:

1. **Given** hằng lời hướng dẫn, **When** đọc số phiên bản, **Then** số đó là số nguyên `2`. Hằng không được nạp từ file lúc chạy.
2. **Given** một lượt có hai lần gọi mô hình, **When** xem từng yêu cầu, **Then** cả hai gửi cùng lời hướng dẫn phiên bản 2.
3. **Given** một lần gọi mô hình đã kết thúc, **When** đọc dòng nhật ký của lần đó, **Then** `prompt_version` là `2` và `definitions_version` là `2`. Tập khóa của dòng vẫn là tám khóa đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md).
4. **Given** bộ định nghĩa tool phiên bản 2, **When** đọc mô tả và số phiên bản sau lát này, **Then** mô tả và số phiên bản giữ nguyên. Lời hướng dẫn không nêu `get_plan_detail`.

---

### Edge Cases

- Dòng chữ trơn `Ngày 1` trong câu trả lời là nhãn nhóm, được phép. Tiêu đề việc con `Ngày 1: nộp báo cáo` do bot tự đặt là tiền tố, bị cấm. Cùng các chữ `Ngày 1` nhưng khác chỗ đứng.
- `1.` đứng đầu một mục trong câu trả lời được phép. `1.` đứng đầu tiêu đề việc con do bot tự đặt bị cấm.
- Tiêu đề người dùng đã chứa tiền tố, hoặc không có điểm kết thúc đo được, hoặc là một thói quen, vẫn được giữ nguyên từng chữ. Bot không sửa tiêu đề đó cho khớp luật dành cho tiêu đề bot tự đặt.
- Luật "không gọi tool" chỉ phủ việc sắp làm mà người dùng chưa nhờ lập kế hoạch. Báo đã xong và báo bỏ không bị phủ bởi luật đó.
- Khớp đúng một việc thì không hỏi xác nhận. Hỏi lại chỉ khi không khớp hoặc khớp nhiều hơn một. Hỏi lại vẫn không đòi bằng chứng và không hỏi mã.
- Ba chữ `chưa làm`, `xong`, `bỏ qua` là lời nói với người dùng. Giá trị trạng thái gửi vào tool vẫn là ba mã của bộ định nghĩa phiên bản 2. Lời hướng dẫn không trộn hai thứ này.
- Lời hướng dẫn không nêu `get_plan_detail` và không thêm lý do để mở chi tiết một kế hoạch. "Tự tìm" nghĩa là không hỏi người dùng mã, không phải thêm một lệnh gọi tool chi tiết.
- Việc kiểu thói quen suốt một khoảng thời gian là việc bot không được tự đặt. [docs/PRODUCT.md](../../docs/PRODUCT.md) §9 giữ chỗ kiểu việc đó cho tính năng thích ứng tải. Lát này không làm tính năng đó.
- Bộ test không gọi mô hình thật. Client giả trả phản hồi định sẵn. Một câu trả lời của client giả có in đậm không làm test này trượt, vì test khóa lời hướng dẫn chứ không khóa văn client giả trả.
- Các file spec của phiên bản 1 giữ nguyên làm biên bản. Đúng sai của lát này đọc ở spec này.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Lời hướng dẫn hệ thống MUST là một hằng, MUST NOT được đọc từ file lúc chạy, và MUST được gửi ở mỗi lần gọi mô hình của lượt. Số phiên bản MUST là số nguyên `2`.
- **FR-002**: Hằng MUST giữ các luật bản 1 ở User Story 1: một nhân vật JARVIS, không tên nhân vật khác, trả lời bằng tiếng Việt, không tự xưng `trợ lý lập kế hoạch`, và khi người dùng chỉ kể việc sắp làm mà chưa nhờ lập kế hoạch thì không gọi tool, tóm lại, rồi hỏi có muốn lập kế hoạch không. Hằng MUST còn đúng câu ví dụ `Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3`. Cụm `trợ lý lập kế hoạch` MUST chỉ đứng trong câu cấm tự xưng. Luật không gọi tool MUST NOT áp khi người dùng báo một việc đã xong hoặc báo bỏ một việc; hai trường hợp đó MUST được chỉ sang FR-007.
- **FR-003**: Hằng MUST bắt câu trả lời là chữ trơn: không in đậm, không dòng tiêu đề mở đầu bằng `#`, không bảng. Hằng MUST cho phép đánh số `1.` và gạch `- ` trong câu trả lời. Hằng MUST cho phép một dòng chữ trơn như `Ngày 1` đứng trước một nhóm trong câu trả lời, và MUST NOT coi dòng đó là tiêu đề việc con.
- **FR-004**: Hằng MUST cấm tiêu đề việc con do bot tự đặt có tiền tố thứ tự. Các ví dụ MUST được nêu là bị cấm: `Ngày 1:`, `Tuần 1:`, `Bước 1`, và `1.` Hằng MUST nói thứ tự là vị trí trong danh sách.
- **FR-005**: Hằng MUST bắt tiêu đề người dùng tự đưa được giữ nguyên từng chữ. Luật điểm kết thúc đo được MUST chỉ áp cho tiêu đề bot tự đặt. Hằng MUST cấm bot tự đặt việc kiểu thói quen suốt một khoảng thời gian, và MUST cấm bot viết lại tiêu đề người dùng để thêm điểm kết thúc hoặc để gỡ tiền tố.
- **FR-006**: Hằng MUST cấm hiện mã kế hoạch và mã việc con trong câu trả lời, MUST cấm hỏi người dùng mã, và MUST bảo tự tìm khi cần. Hằng MUST gọi trạng thái trong câu trả lời là `chưa làm`, `xong`, và `bỏ qua`, và MUST cấm ba chữ `pending`, `done`, `skipped` trong câu trả lời. Hằng MUST NOT bảo đưa ba chữ tiếng Việt đó vào giá trị trạng thái của tool.
- **FR-007**: Khi người dùng báo đã xong hoặc báo bỏ một việc, hằng MUST bảo tìm theo tên việc họ nói. Khớp đúng một việc thì MUST cập nhật ngay và MUST NOT hỏi xác nhận. Khớp không việc nào hoặc khớp nhiều việc thì MUST hỏi lại. Mọi nhánh MUST NOT đòi bằng chứng và MUST NOT hỏi mã.
- **FR-008**: Mỗi lần gọi mô hình đã kết thúc MUST ghi `prompt_version` bằng số nguyên `2`. `definitions_version` trên dòng đó MUST vẫn là số nguyên `2`. Tập khóa của dòng MUST giữ nguyên như [spec lượt mô hình](../008-llm-tool-turn/spec.md).
- **FR-009**: Bộ định nghĩa tool, gồm mô tả trạng thái và mô tả ghi chú, MUST không đổi so với bộ phiên bản 2. Hằng MUST NOT nêu `get_plan_detail` và MUST NOT thêm lý do để mở chi tiết một kế hoạch.
- **FR-010**: Kiểm tra đang khóa nguyên văn lời hướng dẫn bản 1 MUST được đổi trong cùng thay đổi. Kiểm tra đó MUST khóa số phiên bản `2` và MUST có ít nhất một khẳng định cho từng luật FR-002, FR-003, FR-004, FR-005, FR-006, và FR-007. Mọi khẳng định của kiểm tra không khóa nội dung lời hướng dẫn MUST giữ nguyên. Bộ test tự động MUST NOT gọi mô hình thật.

### Key Entities

- **Lời hướng dẫn**: Một hằng văn bản, số phiên bản `2`, sáu luật ở User Story 1 đến User Story 5. Không nạp từ file lúc chạy. Không phải một thực thể trong kho.
- **Dòng nhật ký lần gọi mô hình**: Đúng dòng tám khóa ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Lát này chỉ đổi giá trị `prompt_version` thành `2`. `definitions_version` giữ `2`.
- **Việc con**: Đúng thực thể đã chốt ở [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Lát này không thêm thuộc tính, không thêm trường ngày, và không đổi ba mã trạng thái trong kho.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần đọc lời hướng dẫn thấy số phiên bản `2`, thấy đủ sáu luật FR-002 đến FR-007, thấy đúng câu ví dụ về báo cáo thứ Sáu và chương 3, và thấy JARVIS là nhân vật duy nhất.
- **SC-002**: 100% lần gọi mô hình trong một lượt gửi cùng hằng đó. 100% dòng nhật ký của lần gọi đã kết thúc ghi `prompt_version` bằng `2` và `definitions_version` bằng `2`, với đúng tập khóa đã có.
- **SC-003**: 0 lần lời hướng dẫn bảo hiện mã, hỏi mã, đòi bằng chứng, dùng `pending`, `done`, hoặc `skipped` trong câu trả lời, hay đưa `chưa làm`, `xong`, `bỏ qua` vào giá trị trạng thái của tool.
- **SC-004**: 0 lần lời hướng dẫn nêu `get_plan_detail`. 100% mô tả tool và số phiên bản bộ định nghĩa giữ nguyên ở phiên bản 2.
- **SC-005**: Đúng một nhóm khẳng định nội dung khóa cả sáu luật, mỗi luật ít nhất một khẳng định, và khóa số phiên bản `2`. 0 khẳng định của kiểm tra không liên quan bị sửa. 100% ca trong bộ test tự động chạy bằng client giả và không gọi mô hình thật.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Bước specify không sửa file trong `docs/`. Các ý sau đây chưa có nguyên văn trong §9, và để B10 đồng bộ: luật "không gọi tool" chỉ cho việc sắp làm; báo bỏ đi cùng báo xong; cấm in đậm, tiêu đề `#` và bảng; dòng chữ trơn `Ngày 1` được phép trong câu trả lời; không hiện mã và không hỏi mã; câu trả lời dùng `chưa làm`, `xong`, `bỏ qua`. §9 đã có chữ trơn, tiền tố `Ngày 1:` và `Tuần 1:`, giữ nguyên tiêu đề người dùng, điểm kết thúc đo được cho tiêu đề bot tự đặt, và khớp một việc thì cập nhật, không khớp hoặc khớp nhiều thì hỏi lại, không đòi bằng chứng.
- 46/150, 8/150, 4, 4, 2, 7, và 2 là lý do làm lát này. Không lấy các lần đó trở thành đạt làm điều kiện xong. Sau merge, hiệu quả hành vi được đo bằng eval p2-d2 trên bộ câu v1, so với `evals/results/p1-d2-claude-haiku-5-5-2026-11-01.json`. Đó là mục tiêu đo, không phải ca trong bộ test tự động. Lát này không chạy eval và không đổi bộ câu, bộ chấm, `SCORER_VERSION`, hay runner.
- Không đặt ngân sách số ký tự. "Ngắn gọn" nghĩa là mỗi luật nói một lần, giữ một ví dụ kể việc của bản 1, không chép lại bộ định nghĩa tool, và không thêm ví dụ kéo mô hình sang `get_plan_detail`.
- Ba mã trạng thái của tool và của kho giữ nguyên `pending`, `done`, `skipped`. Ba chữ tiếng Việt chỉ là lời nói với người dùng. Mô tả status và note mà mục L1-05 để vòng riêng không sửa trong lát này, để lần đo sau chỉ khác lời hướng dẫn.
- Kiểm tra đang khóa nội dung bản 1 là `test_system_prompt_has_four_laws` trong `tests/test_llm_turn.py`: nó khẳng định `PROMPT_VERSION == 1` và các câu của bốn luật. Kiểm tra đó được sửa trong cùng thay đổi. Tên được đổi cho khỏi còn nói bốn luật; tên mới không bị khóa thành một chuỗi cụ thể. Các khẳng định khác trong file đó so với hằng `PROMPT_VERSION` và `SYSTEM_PROMPT` giữ nguyên, gồm `logged["prompt_version"] == PROMPT_VERSION` và `request.system == SYSTEM_PROMPT`.
- `tests/test_eval_result.py` và `tests/test_eval_score.py` nhúng `prompt_version` bằng `1` như dữ liệu mẫu của file kết quả và của bộ chấm, kể cả ca cố ý lệch giữa `1` và `2`. Đó không phải khóa lời hướng dẫn đang chạy. Không sửa các khẳng định đó.
- Các file trong `specs/008-llm-tool-turn/` giữ nguyên làm biên bản phiên bản 1. Lát này không sửa spec cũ.
- Ngoài phạm vi, theo mô tả tính năng:
  - Đổi bộ định nghĩa tool, hoặc đổi `DEFINITIONS_VERSION` khỏi `2`.
  - Đổi bộ câu eval, bộ chấm, `SCORER_VERSION`, hoặc runner.
  - Thêm trường ngày cho việc con, đổi model miền, hoặc đổi schema kho.
  - Thêm câu đẩy bot sang `get_plan_detail`.
  - Sửa file trong `docs/` ở bước specify.
  - Chấm mô hình thật có nghe sáu luật hay không trong bộ test tự động.
