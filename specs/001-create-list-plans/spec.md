# Feature Specification: Tạo và liệt kê kế hoạch

**Feature Branch**: `001-create-list-plans`

**Created**: 2026-10-18

**Status**: Draft

**Bị thay một phần**: [spec 010](../010-get-plans-subtask-keyword/spec.md) cho từ khóa khớp cả tiêu đề việc con. Tình huống từ khóa "giáo trình" chỉ nằm trong việc con và mọi câu nói chỉ xét mục tiêu không còn hiệu lực.

**Input**: User description: "Tính năng tạo và liệt kê kế hoạch (F04 create_plan, F05 get_plans trong docs/PRODUCT.md), chỉ phần logic của tool. create_plan nhận một goal bắt buộc và danh sách subtask, lưu lại và trả về plan vừa tạo. get_plans liệt kê các plan đang hoạt động, tùy chọn lọc theo keyword trong goal. Tạo xong rồi gọi get_plans phải thấy đúng plan đó cùng subtask của nó. Ngoài phạm vi: LLM gọi tool, route HTTP, Telegram, sửa hoặc xóa plan và subtask (F07 đến F09), kết nối database thật. Database dự kiến chưa được tạo; kiểm chứng phải chạy được khi chưa có database thật."

## User Scenarios & Testing *(mandatory)*

Người dùng cần một kế hoạch đã chốt (một mục tiêu và các việc con) được giữ lại và tìm lại được. Tính năng này chỉ gồm hai hành động trong [docs/PRODUCT.md](../../docs/PRODUCT.md): tạo kế hoạch (F04) và liệt kê kế hoạch đang hoạt động (F05). Ai quyết định gọi hai hành động đó, và qua kênh nào, nằm ngoài phạm vi.

### User Story 1 - Lưu một kế hoạch vừa chốt (Priority: P1)

Khi một mục tiêu và các việc con đã được chốt, người dùng cần chúng được lưu thành một kế hoạch và nhận lại đúng kế hoạch đó, để biết việc lưu đã thành công.

**Why this priority**: Không có bước lưu thì không có gì để nhắc, xem lại hay điều chỉnh sau này. Đây là lát cắt nhỏ nhất vẫn mang lại giá trị.

**Independent Test**: Gửi một mục tiêu cùng hai việc con, rồi kiểm tra kết quả trả về. Không cần bước liệt kê.

**Acceptance Scenarios**:

1. **Given** chưa có kế hoạch nào, **When** tạo kế hoạch với mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày" theo thứ tự đó, **Then** kết quả là một kế hoạch mới gồm danh tính riêng, đúng mục tiêu đó, và đúng hai việc con theo thứ tự đã đưa.
2. **Given** chưa có kế hoạch nào, **When** tạo kế hoạch chỉ với mục tiêu "Viết báo cáo" và không có việc con, **Then** kết quả là một kế hoạch mới với đúng mục tiêu đó và danh sách việc con rỗng.
3. **Given** đã có một kế hoạch cùng mục tiêu "Học tiếng Nhật", **When** tạo thêm một kế hoạch nữa với cùng mục tiêu và cùng các việc con, **Then** kết quả là một kế hoạch mới, có danh tính khác kế hoạch đã có.
4. **Given** chưa có kế hoạch nào, **When** tạo với mục tiêu "  Học tiếng Nhật  " và một việc con "  Học hiragana  ", **Then** mục tiêu và việc con được lưu thành "Học tiếng Nhật" và "Học hiragana".
5. **Given** đang có hai kế hoạch, **When** tạo với mục tiêu bỏ trống hoặc chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối và hai kế hoạch cũ vẫn nguyên.
6. **Given** chưa có kế hoạch nào, **When** tạo với mục tiêu hợp lệ nhưng một việc con chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối và không có kế hoạch nào được lưu.

---

### User Story 2 - Xem lại các kế hoạch đang hoạt động (Priority: P1)

Sau khi một kế hoạch đã được lưu, người dùng cần thấy lại đúng kế hoạch đó, kèm đủ các việc con, khi xem danh sách kế hoạch đang hoạt động.

**Why this priority**: Điều kiện chấp nhận của tính năng là tạo xong rồi liệt kê phải thấy đúng kế hoạch cùng việc con. Liệt kê là cách người dùng kiểm tra kế hoạch không bị mất.

**Independent Test**: Chuẩn bị sẵn vài kế hoạch đã lưu, rồi liệt kê không kèm từ khóa. Có thể kiểm riêng, không cần vừa tạo trong cùng một bước.

**Acceptance Scenarios**:

1. **Given** vừa tạo thành công một kế hoạch với mục tiêu và các việc con, **When** liệt kê kế hoạch đang hoạt động mà không kèm từ khóa, **Then** danh sách có đúng kế hoạch đó, cùng danh tính đã trả về lúc tạo, cùng mục tiêu, và cùng các việc con theo đúng thứ tự.
2. **Given** đã lưu ba kế hoạch lần lượt là A, rồi B, rồi C, **When** liệt kê không kèm từ khóa, **Then** cả ba đều có mặt, mỗi kế hoạch kèm đủ việc con của nó, và thứ tự là C, B, A.
3. **Given** chưa có kế hoạch nào, **When** liệt kê, **Then** kết quả là một danh sách rỗng, không phải lỗi.
4. **Given** một lần tạo vừa bị từ chối, **When** liệt kê, **Then** số kế hoạch không tăng so với trước lần tạo đó.

---

### User Story 3 - Tìm kế hoạch theo một từ trong mục tiêu (Priority: P2)

Khi đã có nhiều kế hoạch, người dùng cần thu danh sách còn những kế hoạch có một từ hoặc một cụm từ nằm trong mục tiêu.

**Why this priority**: Lọc là phần tùy chọn của việc liệt kê. Tạo và liệt kê đầy đủ vẫn có giá trị khi chưa có lọc.

**Independent Test**: Lưu vài kế hoạch có mục tiêu khác nhau, rồi liệt kê kèm một từ khóa và đối chiếu đúng tập được trả về.

**Acceptance Scenarios**:

1. **Given** một kế hoạch mục tiêu "Học tiếng Nhật" và một kế hoạch mục tiêu "Học guitar", **When** liệt kê với từ khóa "Nhật", **Then** chỉ kế hoạch "Học tiếng Nhật" được trả về, kèm đủ việc con của nó.
2. **Given** kế hoạch mục tiêu "Học tiếng Nhật", **When** liệt kê với từ khóa "tiếng", **Then** kế hoạch đó được trả về.
3. **Given** kế hoạch mục tiêu "Học tiếng Nhật", **When** liệt kê với từ khóa "TIẾNG", **Then** kế hoạch đó vẫn được trả về.
4. **Given** kế hoạch mục tiêu "Học tiếng Nhật", **When** liệt kê với từ khóa "  Nhật  ", **Then** kế hoạch đó được trả về.
5. **Given** kế hoạch mục tiêu "Học tiếng Nhật", **When** liệt kê với từ khóa "tieng", **Then** kế hoạch đó không được trả về.
6. **Given** kế hoạch mục tiêu "Học tiếng Nhật" có một việc con "Mua giáo trình Nhật", **When** liệt kê với từ khóa "giáo trình", **Then** kế hoạch đó không được trả về.
7. **Given** đang có kế hoạch, **When** liệt kê với từ khóa không nằm trong mục tiêu nào, **Then** kết quả là danh sách rỗng, không phải lỗi.
8. **Given** đang có kế hoạch, **When** liệt kê với từ khóa bỏ trống hoặc chỉ gồm khoảng trắng, **Then** kết quả giống liệt kê không lọc.

---

### Edge Cases

- Mục tiêu thiếu, rỗng, hoặc chỉ gồm khoảng trắng: từ chối cả yêu cầu, không lưu kế hoạch.
- Một việc con rỗng hoặc chỉ gồm khoảng trắng, kể cả khi đứng giữa các việc con hợp lệ: từ chối cả yêu cầu, không lưu phần nào.
- Danh sách việc con không được gửi: coi như không có việc con; kế hoạch chỉ gồm mục tiêu vẫn hợp lệ.
- Hai việc con trùng nội dung: giữ cả hai, đúng vị trí đã đưa.
- Hai kế hoạch trùng mục tiêu: cả hai đều đang hoạt động và đều xuất hiện khi liệt kê không lọc; phân biệt bằng danh tính.
- Chưa có kế hoạch, hoặc từ khóa không khớp mục tiêu nào: liệt kê trả về danh sách rỗng.
- Từ khóa chỉ xuất hiện trong việc con, không xuất hiện trong mục tiêu: kế hoạch đó không nằm trong kết quả lọc.
- "tieng" không khớp mục tiêu "tiếng": dấu tiếng Việt được tính là khác ký tự.
- Khoảng trắng ở đầu và cuối mục tiêu, việc con, hoặc từ khóa được bỏ qua; chữ bên trong giữ nguyên, kể cả khoảng trắng đôi.
- Một lần tạo bị từ chối không làm thay đổi danh sách kế hoạch đã có.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST lưu một kế hoạch mới khi nhận một mục tiêu có nội dung và một danh sách việc con (danh sách có thể rỗng), rồi trả về đúng kế hoạch vừa lưu.
- **FR-002**: Kế hoạch trả về MUST gồm một danh tính riêng, mục tiêu đã lưu, và các việc con theo đúng thứ tự đã đưa. Danh tính đó MUST giữ nguyên khi kế hoạch xuất hiện ở lần liệt kê sau.
- **FR-003**: Hệ thống MUST từ chối yêu cầu tạo khi mục tiêu thiếu, rỗng, hoặc chỉ gồm khoảng trắng, và MUST không thêm kế hoạch mới.
- **FR-004**: Hệ thống MUST từ chối cả yêu cầu tạo khi bất kỳ việc con nào rỗng hoặc chỉ gồm khoảng trắng, và MUST không lưu một phần của yêu cầu đó.
- **FR-005**: Khi danh sách việc con không được gửi, hệ thống MUST lưu kế hoạch với danh sách việc con rỗng.
- **FR-006**: Mỗi lần tạo hợp lệ MUST sinh một kế hoạch mới, kể cả khi mục tiêu và các việc con trùng một kế hoạch đã có.
- **FR-007**: Hệ thống MUST liệt kê mọi kế hoạch đang hoạt động. Trong phạm vi tính năng này, mọi kế hoạch tạo thành công đều đang hoạt động.
- **FR-008**: Mỗi kế hoạch trong danh sách MUST kèm mục tiêu và đủ việc con đã lưu, theo đúng thứ tự.
- **FR-009**: Khi không lọc, hệ thống MUST xếp kế hoạch tạo sau trước kế hoạch tạo trước.
- **FR-010**: Hệ thống MUST cho phép lọc danh sách bằng một từ khóa tùy chọn. Một kế hoạch được đưa vào kết quả khi từ khóa là một đoạn liên tục trong mục tiêu. So khớp không phân biệt hoa thường, và phân biệt dấu tiếng Việt.
- **FR-011**: Hệ thống MUST quyết định một kế hoạch có khớp bộ lọc chỉ bằng mục tiêu.
- **FR-012**: Từ khóa bỏ qua, rỗng, hoặc chỉ gồm khoảng trắng MUST có nghĩa là không lọc: kết quả giống liệt kê mọi kế hoạch đang hoạt động.
- **FR-013**: Khi không có kế hoạch khớp, hệ thống MUST trả về một danh sách rỗng. Kết quả rỗng là một danh sách hợp lệ.
- **FR-014**: Trước khi kiểm tra và lưu, hệ thống MUST bỏ khoảng trắng đầu và cuối của mục tiêu, của từng việc con, và của từ khóa. Phần chữ còn lại MUST được giữ nguyên.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Một mục tiêu đã chốt, cần giữ lại để xem lại. Gồm danh tính riêng, mục tiêu (bắt buộc, có nội dung), thứ tự tạo, và các việc con thuộc về nó. Trong phạm vi này, kế hoạch tạo thành công là kế hoạch đang hoạt động.
- **Việc con**: Một việc thuộc về đúng một kế hoạch. Gồm nội dung (bắt buộc khi việc con được gửi) và vị trí trong danh sách. Hai việc con trùng nội dung vẫn là hai việc nếu cùng được gửi. Tính năng này không đổi nội dung việc con sau khi lưu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần tạo hợp lệ trả về một kế hoạch có đúng mục tiêu và đúng từng việc con theo thứ tự đã đưa, kèm một danh tính riêng.
- **SC-002**: 100% kế hoạch vừa tạo xuất hiện ở lần liệt kê kế hoạch đang hoạt động ngay sau đó, cùng danh tính, cùng mục tiêu, và đủ việc con.
- **SC-003**: Khi lọc bằng một từ khóa, danh sách trả về đúng tập kế hoạch đang hoạt động có từ khóa đó trong mục tiêu: không thiếu kế hoạch khớp, không có kế hoạch không khớp.
- **SC-004**: 100% lần tạo không hợp lệ (thiếu mục tiêu hoặc có việc con trống) không làm tăng số kế hoạch đang lưu.
- **SC-005**: Hai kế hoạch tạo riêng với cùng mục tiêu luôn phân biệt được khi liệt kê; cả hai đều có mặt nếu cùng đang hoạt động và cùng khớp bộ lọc.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Danh sách là toàn bộ kế hoạch đang hoạt động của người đó; không có chia sẻ hay phân quyền.
- "Đang hoạt động" nghĩa là kế hoạch đã lưu thành công và chưa bị đưa ra khỏi danh sách. Tính năng này không có thao tác hoàn thành, cất đi, hay xóa, nên mọi kế hoạch tạo thành công đều được liệt kê khi không lọc.
- Việc con là một đoạn nội dung. Không thêm hạn mức độ dài, mức ưu tiên, hạn chót, hay trạng thái hoàn thành trong lát cắt này.
- Từ khóa khớp theo đoạn liên tục trong mục tiêu, không phân biệt hoa thường. Dấu tiếng Việt được giữ: "tieng" không khớp "tiếng". Nhiều chữ trong từ khóa phải đứng liền nhau đúng như đã nhập, sau khi bỏ khoảng trắng đầu và cuối.
- Hai cách mã hóa khác nhau của cùng một chữ có dấu được coi là như nhau khi lưu và khi lọc (Unicode NFC).
- Không phân trang. Một lần liệt kê trả về toàn bộ tập đang khớp.
- Danh tính kế hoạch do hệ thống tạo khi lưu, và không đổi giữa lần trả về lúc tạo và lần liệt kê sau.
- Nơi lưu lâu dài của sản phẩm đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Tính năng này không dựng kho đó và không nối tới kho đang chạy. Đúng sai của tạo và liệt kê phải quan sát được trước khi kho đó tồn tại.
- Ngoài phạm vi, theo mô tả tính năng và danh sách ở [docs/PRODUCT.md](../../docs/PRODUCT.md):
  - Hội thoại hỏi lại trước khi chốt kế hoạch (F01, F02).
  - Việc quyết định lúc nào gọi tạo hoặc liệt kê.
  - Đường nhận yêu cầu qua HTTP và qua Telegram (F11, F14).
  - Xem chi tiết một kế hoạch theo danh tính (F06).
  - Sửa việc con, thêm việc con, xem lại và điều chỉnh kế hoạch (F07, F08, F09).
  - Nhắc việc chủ động, đồng bộ ra ngoài, và các tính năng từ F10 trở đi.
  - Dựng hoặc kết nối kho dữ liệu thật.
