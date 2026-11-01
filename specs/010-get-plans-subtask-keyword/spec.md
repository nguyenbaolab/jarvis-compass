# Feature Specification: Từ khóa liệt kê khớp tiêu đề việc con

**Feature Branch**: `010-get-plans-subtask-keyword`

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "get_plans: từ khóa khớp cả tiêu đề việc con, không chỉ mục tiêu kế hoạch. Lần chạy eval đầu (bộ câu v1, 150 lượt) cho thấy mô hình thường tìm kế hoạch theo tên việc con (ví dụ hiragana, chương 2, katakana). Từ khóa hiện chỉ so với mục tiêu, kho trả danh sách rỗng, mô hình bỏ cuộc và hỏi lại. Đây là nguyên nhân chính của 21 trên 45 lần trượt luật kiểm trạng thái kho. Khi từ khóa còn nội dung sau NFC và bỏ khoảng trắng hai đầu, giữ kế hoạch nếu mục tiêu hoặc ít nhất một tiêu đề việc con chứa từ khóa. Luật so khớp của mục tiêu giữ nguyên và áp y hệt cho tiêu đề: NFC, casefold, chuỗi con, không bỏ dấu, khoảng trắng bên trong giữ nguyên. Kế hoạch khớp trả nguyên vẹn, tối đa một lần, thứ tự mới hơn đứng trước. Mọi trạng thái việc con đều được xét. Từ khóa không có, rỗng, hoặc chỉ khoảng trắng giữ hành vi cũ. Mô tả tool phải nói rõ từ khóa khớp cả mục tiêu lẫn tiêu đề. DEFINITIONS_VERSION tăng từ 1 lên 2. Có test cho từng ý. Hai test cũ đang khẳng định tiêu đề không khớp phải đổi kỳ vọng. Test khẳng định phiên bản bằng 1 đổi thành 2. Mọi test cũ khác giữ assertion. Ngoài phạm vi: ghi chú, system prompt, PROMPT_VERSION, bộ câu eval, cách chấm, cổng lưu trữ, store, truy vấn, migration, khóa dòng log, hình JSON, xếp hạng, tìm gần đúng, bỏ dấu, docs/PRODUCT.md, và spec cũ trong specs/."

## User Scenarios & Testing *(mandatory)*

Người dùng nhờ tìm một kế hoạch bằng một từ nằm trong tên việc con, không nằm trong mục tiêu. Hôm nay danh sách trả về rỗng, nên người trả lời bỏ cuộc và hỏi lại. Lần đánh giá đầu, bộ câu v1 với 150 lượt, cho thấy đây là cách mô hình thường tìm (ví dụ "hiragana", "chương 2", "katakana") và là nguyên nhân chính của 21 trên 45 lần trượt luật kiểm trạng thái kho.

Liệt kê và luật từ khóa trên mục tiêu đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Lát này chỉ mở thêm chỗ so khớp: tiêu đề việc con được xét cùng mục tiêu. Các file trong `specs/001-create-list-plans/` giữ nguyên làm biên bản. Đúng sai của lát này quan sát được trên danh sách kế hoạch đã có, không cần kho đang chạy.

### User Story 1 - Tìm được kế hoạch khi từ khóa nằm ở tên việc con (Priority: P1)

Khi đã có nhiều kế hoạch, người dùng đưa một từ khóa còn nội dung. Kế hoạch được giữ nếu mục tiêu chứa từ khóa, hoặc ít nhất một tiêu đề việc con chứa từ khóa. Kế hoạch chỉ khớp ở tên việc con không còn bị bỏ khỏi danh sách.

**Why this priority**: Đây là lỗ hổng làm danh sách rỗng và làm người trả lời hỏi lại, dù việc con đang nằm trong kho. Không có bước này thì các luật trả nguyên và phiên bản định nghĩa không có gì để bảo vệ.

**Independent Test**: Lưu một kế hoạch mục tiêu "Học tiếng Nhật" với việc con "Mua giáo trình Nhật", và một kế hoạch mục tiêu "Học guitar". Liệt kê với từ khóa "giáo trình". Chỉ kế hoạch tiếng Nhật được trả về, một lần, kèm đủ việc con.

**Acceptance Scenarios**:

1. **Given** kế hoạch mục tiêu "Học tiếng Nhật" có việc con "Mua giáo trình Nhật", và kế hoạch mục tiêu "Học guitar" có việc con "Hợp âm", **When** liệt kê với từ khóa "giáo trình", **Then** chỉ kế hoạch "Học tiếng Nhật" được trả về. Từ khóa không nằm trong mục tiêu của kế hoạch đó.
2. **Given** một kế hoạch có mục tiêu "Học tiếng Nhật" và có việc con "Học hiragana", **When** liệt kê với từ khóa "hiragana", **Then** kế hoạch đó được trả về.
3. **Given** một kế hoạch có hai việc con cùng chứa từ khóa, và mục tiêu cũng chứa từ khóa đó, **When** liệt kê với từ khóa đó, **Then** kế hoạch xuất hiện đúng một lần.
4. **Given** hai kế hoạch đều khớp, kế hoạch tạo sau đứng trước khi liệt kê không lọc, **When** liệt kê với từ khóa khớp cả hai, **Then** thứ tự giữa hai kế hoạch giống lần liệt kê không lọc.
5. **Given** đang có kế hoạch, **When** liệt kê với từ khóa không nằm trong mục tiêu nào và không nằm trong tiêu đề việc con nào, **Then** kết quả là danh sách rỗng và là kết quả thành công, không phải lỗi.
6. **Given** kế hoạch mục tiêu "Học guitar", việc con "Mua đàn", ghi chú của việc đó là "giáo trình", **When** liệt kê với từ khóa "giáo trình", **Then** kế hoạch đó không được trả về.

---

### User Story 2 - Kế hoạch khớp được trả nguyên, kể cả việc con không chứa từ khóa (Priority: P1)

Người dùng tìm bằng một từ của một việc, rồi cần thấy cả kế hoạch: mọi việc con, trạng thái, ghi chú, và thứ tự việc con. Việc con không chứa từ khóa vẫn nằm trong kế hoạch được trả về. Việc đã xong hoặc đã bỏ qua vẫn làm kế hoạch khớp.

**Why this priority**: Tìm thấy kế hoạch mà mất bớt việc con, hoặc bỏ qua việc đã đánh dấu xong, làm người dùng tưởng việc đó không còn.

**Independent Test**: Lưu một kế hoạch ba việc con, chỉ việc thứ hai chứa từ khóa, việc đó đang `done`, một việc khác đang `skipped` và chứa một từ khóa khác. Mỗi lần liệt kê với đúng một từ khóa, đối chiếu đủ ba việc, đúng trạng thái, đúng ghi chú, đúng thứ tự.

**Acceptance Scenarios**:

1. **Given** một kế hoạch có ba việc con theo thứ tự "Mua vở", "Học hiragana", "Nghe hội thoại", chỉ việc giữa chứa "hiragana", **When** liệt kê với từ khóa "hiragana", **Then** kế hoạch được trả về với đúng ba việc con, đúng thứ tự đó, kể cả hai việc không chứa từ khóa.
2. **Given** việc "Học hiragana" đang `done` và có ghi chú, các việc khác đang `pending`, **When** liệt kê với từ khóa "hiragana", **Then** việc đó vẫn `done`, ghi chú vẫn nguyên, và các việc khác giữ trạng thái cùng ghi chú của chúng.
3. **Given** một việc con đang `skipped` có tiêu đề chứa "katakana", mục tiêu không chứa từ đó, **When** liệt kê với từ khóa "katakana", **Then** kế hoạch được trả về và việc đó vẫn `skipped`.
4. **Given** một việc con đang `pending` có tiêu đề chứa từ khóa, **When** liệt kê với từ khóa đó, **Then** kế hoạch được trả về và việc đó vẫn `pending`.
5. **Given** một kế hoạch khớp, **When** đọc kết quả liệt kê, **Then** hình mỗi kế hoạch và mỗi việc con giống hình đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec cập nhật việc con](../003-update-subtask/spec.md), và [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Không thêm và không bớt phần thông tin.

---

### User Story 3 - Luật so khớp của tiêu đề giống luật của mục tiêu (Priority: P1)

Cách so một từ khóa với mục tiêu không đổi, và cách so với từng tiêu đề việc con dùng đúng luật đó. Hoa thường không chặn. Dấu tiếng Việt vẫn tính. Khoảng trắng bên trong từ khóa không bị nuốt. Từ khóa không có, rỗng, hoặc chỉ khoảng trắng vẫn trả mọi kế hoạch.

**Why this priority**: Nới chỗ so khớp mà đổi luật chữ sẽ làm các lần tìm theo mục tiêu đang đúng trở thành sai, hoặc làm "tieng" khớp nhầm "tiếng".

**Independent Test**: Lưu tiêu đề việc con "Học tiếng Nhật" dưới mục tiêu không chứa các từ khóa bên dưới. Lần lượt liệt kê với "tiếng", "TIẾNG", "  Nhật  ", "tieng", từ khóa NFC của "tiếng" khi tiêu đề đã lưu là dạng NFD của "Học tiếng Nhật", và "tiếng  Nhật". Đối chiếu khớp hoặc không khớp từng lần. Rồi liệt kê với từ khóa bỏ trống, chỉ khoảng trắng, và không gửi từ khóa: cả ba giống liệt kê không lọc.

**Acceptance Scenarios**:

1. **Given** tiêu đề việc con "Học tiếng Nhật" và mục tiêu không chứa "tiếng", **When** liệt kê với "tiếng", với "TIẾNG", và với "  Nhật  ", **Then** cả ba lần đều trả về kế hoạch đó.
2. **Given** cùng tiêu đề "Học tiếng Nhật", **When** liệt kê với "tieng", **Then** kế hoạch đó không được trả về.
3. **Given** tiêu đề việc con đã lưu là dạng NFD của "Học tiếng Nhật", **When** liệt kê với từ khóa là dạng NFC của "tiếng", **Then** kế hoạch đó được trả về.
4. **Given** tiêu đề việc con "Học tiếng Nhật", **When** liệt kê với "tiếng  Nhật", **Then** kế hoạch đó không được trả về. Hai dấu cách giữa hai chữ không bị gộp.
5. **Given** mục tiêu "Học tiếng Nhật" và không việc con nào chứa "Nhật", **When** liệt kê với "Nhật", **Then** kế hoạch đó vẫn được trả về, cùng luật mục tiêu đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md).
6. **Given** đang có vài kế hoạch, **When** liệt kê với từ khóa không được gửi, từ khóa rỗng, hoặc từ khóa chỉ gồm khoảng trắng, **Then** kết quả từng lần giống liệt kê không lọc, gồm cả kế hoạch không chứa các chữ đó.

---

### User Story 4 - Mô tả gửi cho mô hình và số phiên bản phân biệt đường cơ sở (Priority: P2)

Mô hình đọc mô tả của lần liệt kê trước khi chọn từ khóa. Mô tả phải nói từ khóa khớp cả mục tiêu lẫn tiêu đề việc con. Số phiên bản bộ định nghĩa tăng từ 1 lên 2, để dòng nhật ký và file kết quả đánh giá phân biệt hành vi mới với đường cơ sở. Khóa các dòng nhật ký không đổi.

**Why this priority**: Kho khớp tiêu đề mà mô tả vẫn nói chỉ mục tiêu thì mô hình tiếp tục chọn từ khóa như cũ mà không biết chỗ mới được xét. Số phiên bản là dấu hiệu đọc được trên kết quả đánh giá đã có.

**Independent Test**: Đọc mô tả tool liệt kê và số phiên bản bộ định nghĩa. Gọi liệt kê thành công và đọc dòng nhật ký của lần gọi. Mô tả nêu cả mục tiêu và tiêu đề việc con. Phiên bản là 2. Các khóa của dòng nhật ký không thêm và không bớt.

**Acceptance Scenarios**:

1. **Given** bộ định nghĩa tool, **When** đọc mô tả của `get_plans`, **Then** mô tả là đúng câu `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.`
2. **Given** bộ định nghĩa tool, **When** đọc số phiên bản, **Then** số đó là `2`.
3. **Given** một lần liệt kê thành công, **When** đọc dòng nhật ký của lần gọi tool, **Then** khóa `definitions_version` là `2`, và tập khóa của dòng đó vẫn là bảy khóa đã chốt ở [spec router tool](../007-plan-tool-router/spec.md).
4. **Given** một lượt có gọi mô hình, **When** đọc dòng nhật ký của lần gọi mô hình, **Then** khóa `definitions_version` là `2`, và tập khóa của dòng đó vẫn là tám khóa đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Lời hướng dẫn hệ thống và số phiên bản lời hướng dẫn không đổi.

---

### Edge Cases

- So với [spec tạo và liệt kê](../001-create-list-plans/spec.md), hai chỗ sau không còn hiệu lực: tình huống từ khóa "giáo trình" chỉ nằm trong việc con "Mua giáo trình Nhật" thì không trả kế hoạch, và câu cạnh "từ khóa chỉ xuất hiện trong việc con thì kế hoạch không nằm trong kết quả". Lát này trả kế hoạch đó. Các file spec 001 không sửa.
- Từ khóa còn nội dung sau chuẩn hóa là một đoạn liên tục. Khớp khi đoạn đó nằm trong mục tiêu hoặc nằm trong ít nhất một tiêu đề. Không cần khớp cả tiêu đề, không xếp hạng, không tìm gần đúng.
- Chuẩn hóa từ khóa: Unicode NFC, rồi bỏ khoảng trắng hai đầu. Rỗng sau bước đó nghĩa là không lọc. Khoảng trắng bên trong giữ nguyên.
- Khi so, mục tiêu và từng tiêu đề được đưa về Unicode NFC rồi so không phân biệt hoa thường theo cùng cách casefold đã dùng cho mục tiêu. Không bỏ dấu. "tieng" không khớp "tiếng" ở mục tiêu và cũng không khớp ở tiêu đề.
- Tiêu đề đã lưu ở dạng NFD vẫn khớp từ khóa NFC của cùng các chữ, vì bước so đưa tiêu đề về NFC. Kết quả liệt kê vẫn trả tiêu đề đúng giá trị đã lưu.
- Việc con `pending`, `done`, và `skipped` đều được xét. Ghi chú không được xét, dù ghi chú chứa đúng từ khóa và không chỗ nào khác chứa.
- Kế hoạch không có việc con chỉ khớp qua mục tiêu.
- Nhiều việc con cùng khớp, hoặc vừa mục tiêu vừa nhiều việc con cùng khớp: một kế hoạch, một lần.
- Kế hoạch khớp trả đủ việc con đã lưu, kể cả việc không chứa từ khóa, đúng thứ tự, đúng trạng thái, đúng ghi chú.
- Thứ tự các kế hoạch trong kết quả lọc là thứ tự của lần liệt kê không lọc, chỉ bỏ những kế hoạch không khớp. Mới hơn vẫn đứng trước.
- Danh sách rỗng khi không kế hoạch nào khớp là thành công.
- Một kế hoạch khớp vì mục tiêu, đúng các ca chữ của spec 001 (hoa thường, khoảng trắng hai đầu, "tieng", khoảng trắng đôi bên trong), vẫn khớp sau lát này.
- Mô tả năm tool còn lại, schema đầu vào của `get_plans`, và hình JSON kết quả không đổi. Trường từ khóa vẫn là chuỗi, vẫn không bắt buộc.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Khi từ khóa còn nội dung sau Unicode NFC và sau khi bỏ khoảng trắng hai đầu, hệ thống MUST giữ một kế hoạch nếu mục tiêu chứa từ khóa hoặc ít nhất một tiêu đề việc con chứa từ khóa.
- **FR-002**: Luật so khớp MUST là luật đang áp cho mục tiêu ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), và MUST áp y hệt cho từng tiêu đề việc con: đoạn liên tục sau NFC và casefold, không bỏ dấu, khoảng trắng bên trong từ khóa được giữ. "tieng" MUST không khớp "tiếng".
- **FR-003**: Mỗi kế hoạch khớp MUST xuất hiện tối đa một lần, kể cả khi vừa mục tiêu vừa nhiều tiêu đề cùng chứa từ khóa.
- **FR-004**: Thứ tự giữa các kế hoạch trong kết quả lọc MUST là thứ tự của lần liệt kê không lọc. Kế hoạch tạo sau MUST đứng trước kế hoạch tạo trước khi cả hai cùng khớp.
- **FR-005**: Mỗi kế hoạch khớp MUST được trả nguyên vẹn: mọi việc con đã lưu, kể cả việc con không chứa từ khóa, đúng thứ tự việc con, đúng trạng thái, đúng ghi chú. Hình JSON của kết quả liệt kê MUST không đổi so với hình đã chốt ở spec 001, spec 003, và spec 005.
- **FR-006**: Tiêu đề việc con đang `pending`, `done`, hoặc `skipped` MUST đều được xét. Ghi chú MUST không tham gia so khớp.
- **FR-007**: Từ khóa không được gửi, từ khóa rỗng, hoặc từ khóa chỉ gồm khoảng trắng sau NFC rồi bỏ khoảng trắng hai đầu MUST có nghĩa là không lọc. Kết quả MUST giống liệt kê mọi kế hoạch đang hoạt động, theo [spec tạo và liệt kê](../001-create-list-plans/spec.md).
- **FR-008**: Khi không kế hoạch nào khớp, hệ thống MUST trả một danh sách rỗng và MUST coi đó là kết quả thành công.
- **FR-009**: Mô tả `get_plans` trong bộ định nghĩa gửi cho mô hình MUST là đúng câu `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.`
- **FR-010**: Số phiên bản bộ định nghĩa MUST là số nguyên `2`. Khóa `definitions_version` trên dòng nhật ký lần gọi tool và trên dòng nhật ký lần gọi mô hình MUST là `2`. Tập khóa của hai dòng đó MUST giữ nguyên như [spec router tool](../007-plan-tool-router/spec.md) và [spec lượt mô hình](../008-llm-tool-turn/spec.md).
- **FR-011**: Mọi hành vi liệt kê theo mục tiêu đã đạt ở spec 001 MUST vẫn đạt, trừ hai chỗ spec 001 nói từ khóa chỉ trong việc con thì không trả kế hoạch. Hai chỗ đó được lát này thay bằng FR-001.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Đúng thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Lát này không thêm thuộc tính. "Đang hoạt động" giữ nghĩa ở spec đó: có mặt trong danh sách đã lưu.
- **Việc con**: Đúng thực thể ở [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md), gồm tiêu đề, trạng thái `pending`, `done`, hoặc `skipped`, và tối đa một ghi chú. Tiêu đề là chỗ so khớp mới. Ghi chú không phải chỗ so khớp. Vị trí trong danh sách không đổi khi kế hoạch được trả về.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% kế hoạch có từ khóa chỉ nằm trong một tiêu đề việc con xuất hiện trong kết quả liệt kê với từ khóa đó.
- **SC-002**: 100% kết quả lọc chứa mỗi kế hoạch khớp đúng một lần, kể cả khi mục tiêu và nhiều tiêu đề cùng chứa từ khóa.
- **SC-003**: 100% kế hoạch khớp mang đủ việc con đã lưu, đúng thứ tự, đúng trạng thái, đúng ghi chú, gồm cả việc con không chứa từ khóa.
- **SC-004**: 100% tiêu đề đang `done` hoặc `skipped` có chứa từ khóa làm kế hoạch của việc đó được trả về. 0 lần ghi chú là chỗ duy nhất chứa từ khóa mà kế hoạch vẫn được trả về.
- **SC-005**: 100% lần từ khóa không gửi, rỗng, hoặc chỉ khoảng trắng cho kết quả giống lần liệt kê không lọc.
- **SC-006**: 0 lần từ khóa "tieng" khớp mục tiêu hoặc tiêu đề "tiếng". 100% tiêu đề đã lưu dạng NFD khớp từ khóa NFC của cùng các chữ.
- **SC-007**: Mô tả `get_plans` gửi cho mô hình là đúng câu ở FR-009. 100% dòng nhật ký tool và dòng nhật ký mô hình ghi phiên bản bộ định nghĩa `2`, với đúng các khóa đã có.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Lát này không sửa file đó.
- 21 trên 45 là lý do làm lát này. Lát này không chạy lại bộ câu đánh giá và không đổi cách chấm. Không lấy "21 lần đó trở thành đạt" làm điều kiện xong, vì lời mô hình trả còn phụ thuộc bộ câu và cách chấm, cả hai đều nằm ngoài phạm vi.
- Luật chữ của mục tiêu trỏ sang spec 001, không chép lại toàn bộ spec đó. Chỗ spec 001 nói việc con không được xét là chỗ duy nhất lát này thay. Các file trong `specs/` của các tính năng trước giữ nguyên.
- Số phiên bản `1` đã chốt ở [spec router tool](../007-plan-tool-router/spec.md). Lát này nâng số đó lên `2` để đường cơ sở và hành vi mới phân biệt được trên dòng nhật ký. Không thêm quyết định mới cho các khóa nhật ký, vì tập khóa không đổi.
- Lời hướng dẫn hệ thống và số phiên bản lời hướng dẫn giữ nguyên như [spec lượt mô hình](../008-llm-tool-turn/spec.md).
- Nơi lưu lâu dài đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Lát này không đổi cổng lưu, không đổi bản lưu trong bộ nhớ dùng cho kiểm tra, không đổi bản lưu Supabase, không đổi truy vấn, và không đổi migration. Đúng sai của lọc quan sát được từ danh sách kế hoạch đã trả về, trước khi cần kho đang chạy.
- Mỗi ý trong User Story 1 đến User Story 4 có một kiểm tra riêng. Tối thiểu phải có kiểm tra cho: khớp chỉ ở tiêu đề; khớp cả mục tiêu và việc con nhưng một lần; khớp việc đang `done`; tiêu đề lưu dạng NFD khớp từ khóa NFC; khác hoa thường vẫn khớp; không dấu không khớp; không khớp mục tiêu hay tiêu đề nào thì danh sách rỗng thành công; kế hoạch khớp trả đủ việc con kể cả việc không chứa từ khóa.
- Đây là đổi hành vi đã duyệt, không phải nới kiểm tra cho qua. Hai kiểm tra đang khẳng định tiêu đề việc con không khớp phải đổi kỳ vọng cho đúng FR-001: `test_keyword_in_subtask_only_does_not_match` (đổi tên thành `test_keyword_in_subtask_only_matches`) trong `tests/test_get_plans.py` và `test_keyword_matches_goal_not_new_title` (đổi tên thành `test_keyword_matches_goal_and_new_title`) trong `tests/test_add_subtask.py`. Kiểm tra đang khẳng định số phiên bản bộ định nghĩa bằng `1` phải khẳng định bằng `2`. Mọi kiểm tra cũ khác giữ nguyên assertion.
- Ngoài phạm vi, theo mô tả tính năng:
  - Ghi chú của việc con tham gia so khớp.
  - Đổi lời hướng dẫn hệ thống hoặc số phiên bản lời hướng dẫn.
  - Đổi bộ câu đánh giá hoặc cách chấm.
  - Đổi cổng lưu trữ, bản lưu Supabase, bản lưu trong bộ nhớ, truy vấn, hoặc migration.
  - Đổi khóa dòng nhật ký, hoặc đổi hình JSON của tool.
  - Xếp hạng kết quả, tìm gần đúng, hoặc bỏ dấu.
  - Sửa [docs/PRODUCT.md](../../docs/PRODUCT.md) hoặc sửa spec cũ trong `specs/`.
