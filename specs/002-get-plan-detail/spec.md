# Feature Specification: Xem chi tiết một kế hoạch

**Feature Branch**: `002-get-plan-detail`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "F06 get_plan_detail: xem chi tiết một plan theo id. Vì sao: sau khi liệt kê plan bằng get_plans, người dùng (qua LLM) cần mở đúng một plan để xem đầy đủ mục tiêu và các subtask, làm nền cho các tính năng cập nhật tiến độ sau này. Hành vi: nhận id của một plan, đúng loại id mà create_plan trả về. Id tồn tại: trả về đúng plan đó, cùng dạng với một phần tử trong kết quả của get_plans, để phía gọi dùng chung một cách đọc. Id không tồn tại: trả về lỗi rõ ràng mà người gọi đọc hiểu được, không làm sập tiến trình. Id rỗng hoặc chỉ có khoảng trắng: trả về lỗi rõ ràng như trên. Tiêu chí đúng: plan vừa tạo bằng create_plan lấy lại được bằng id của nó, đủ mục tiêu và subtask, đúng thứ tự subtask. Khi có nhiều plan, trả đúng plan được hỏi, không lẫn plan khác. Hành vi của create_plan và get_plans không đổi. Ngoài phạm vi: sửa, xóa plan; cập nhật subtask; trạng thái hay deadline của subtask; endpoint HTTP và nối với LLM; DB thật. Bối cảnh: kho dữ liệu chưa có; đúng sai phải quan sát được trước khi kho đó tồn tại."

## User Scenarios & Testing *(mandatory)*

Sau khi đã biết một kế hoạch đang hoạt động, người dùng cần mở đúng kế hoạch đó để xem đủ mục tiêu và các việc con. Đây là bước nền trước khi cập nhật tiến độ. Tính năng này là F06 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Cách tạo và cách liệt kê đã được chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md); tính năng này chỉ thêm thao tác mở một kế hoạch theo danh tính.

### User Story 1 - Mở đúng kế hoạch theo danh tính (Priority: P1)

Khi một kế hoạch vừa được lưu, người dùng cần mở lại đúng kế hoạch đó bằng danh tính đã nhận lúc lưu, và thấy đủ mục tiêu cùng các việc con theo thứ tự đã lưu.

**Why this priority**: Liệt kê cho biết có những kế hoạch nào. Mở một kế hoạch mới cho thấy đủ nội dung của đúng kế hoạch đó. Không có bước này thì chưa có chỗ đứng để cập nhật tiến độ sau này.

**Independent Test**: Lưu một kế hoạch có mục tiêu và hai việc con, lấy danh tính trong kết quả lưu, rồi mở bằng danh tính đó. Đối chiếu mục tiêu, từng việc con, và thứ tự.

**Acceptance Scenarios**:

1. **Given** một kế hoạch vừa được lưu với mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày" theo thứ tự đó, **When** mở bằng danh tính đã nhận lúc lưu, **Then** kết quả là đúng kế hoạch đó, cùng danh tính, cùng mục tiêu, và đúng hai việc con theo thứ tự đã lưu.
2. **Given** một kế hoạch vừa được lưu chỉ với mục tiêu "Viết báo cáo" và không có việc con, **When** mở bằng danh tính của nó, **Then** kết quả có đúng mục tiêu đó và danh sách việc con rỗng.
3. **Given** ba kế hoạch đã lưu lần lượt là A, rồi B, rồi C, mỗi kế hoạch có mục tiêu và việc con riêng, **When** mở bằng danh tính của B, **Then** kết quả là kế hoạch B, kèm mục tiêu và các việc con của B.
4. **Given** một kế hoạch đang có trong danh sách kế hoạch đang hoạt động, **When** mở bằng danh tính của kế hoạch đó, **Then** danh tính, mục tiêu, và các việc con trùng với chính kế hoạch đó khi nó xuất hiện trong danh sách.

---

### User Story 2 - Từ chối rõ khi không mở được (Priority: P1)

Khi danh tính không dùng được, người dùng cần một lời từ chối nêu lý do, để biết kế hoạch không được mở, và mọi kế hoạch đã lưu vẫn giữ nguyên.

**Why this priority**: Mở nhầm, hoặc tưởng đã mở khi không có kế hoạch, sẽ làm hỏng các bước cập nhật tiến độ sau này. Từ chối phải xong trong yêu cầu này; các yêu cầu sau vẫn làm được.

**Independent Test**: Lưu hai kế hoạch. Mở một lần bằng danh tính không trùng kế hoạch nào, và một lần bằng danh tính bỏ trống. Mỗi lần đều bị từ chối với lý do tương ứng, và hai kế hoạch vẫn còn nguyên khi liệt kê lại.

**Acceptance Scenarios**:

1. **Given** đang có hai kế hoạch, **When** mở bằng một danh tính có nội dung nhưng không trùng danh tính nào đã lưu, **Then** yêu cầu bị từ chối, lời từ chối nói rõ không có kế hoạch với danh tính đó, và hai kế hoạch vẫn nguyên.
2. **Given** đang có hai kế hoạch, **When** mở với danh tính thiếu, rỗng, hoặc chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối, lời từ chối nói rõ danh tính chưa được đưa, và hai kế hoạch vẫn nguyên.
3. **Given** lời từ chối ở tình huống 1 và tình huống 2, **When** so hai lời từ chối, **Then** hai lời khác nhau, mỗi lời đủ để biết thuộc tình huống nào.
4. **Given** một lần mở vừa bị từ chối, **When** liệt kê kế hoạch đang hoạt động, rồi mở một kế hoạch bằng đúng danh tính đã lưu của nó, **Then** danh sách giữ nguyên như trước lần từ chối, và lần mở sau trả về đúng kế hoạch đó.

---

### Edge Cases

- Danh tính thiếu, rỗng, hoặc chỉ gồm khoảng trắng: từ chối vì danh tính chưa được đưa. Không có kế hoạch nào bị thêm, sửa, hay mất.
- Danh tính có nội dung nhưng không trùng kế hoạch nào: từ chối vì không có kế hoạch đó. Lời từ chối khác với trường hợp danh tính chưa được đưa.
- Khoảng trắng ở đầu và cuối danh tính được bỏ qua trước khi so. Phần còn lại phải trùng từng ký tự với danh tính đã lưu, kể cả hoa thường.
- Danh tính là mục tiêu, một đoạn của mục tiêu, hoặc vị trí trong danh sách, mà chuỗi đó không phải danh tính đã cấp lúc lưu: từ chối vì không có kế hoạch với danh tính đó.
- Mở một kế hoạch không đổi mục tiêu, việc con, thứ tự việc con, hay danh tính của bất kỳ kế hoạch nào.
- Kế hoạch không có việc con vẫn mở được; danh sách việc con trong kết quả rỗng.
- Mở cùng một danh tính hai lần: cả hai lần cùng một kế hoạch, cùng mục tiêu, cùng các việc con theo cùng thứ tự.
- Một lần từ chối không chặn lần liệt kê sau, cũng không chặn lần mở sau bằng một danh tính đang có.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST mở một kế hoạch khi nhận đúng danh tính đã cấp lúc kế hoạch đó được lưu. Danh tính này là danh tính mô tả ở [spec tạo và liệt kê](../001-create-list-plans/spec.md).
- **FR-002**: Kế hoạch mở ra MUST gồm cùng danh tính, cùng mục tiêu, và cùng các việc con theo đúng thứ tự đã lưu. Các phần đó MUST trùng với chính kế hoạch ấy khi nó nằm trong kết quả liệt kê kế hoạch đang hoạt động.
- **FR-003**: Khi đang có nhiều kế hoạch, hệ thống MUST trả về kế hoạch có danh tính được hỏi.
- **FR-004**: Mở một kế hoạch MUST để nguyên mọi kế hoạch đã lưu: không thêm, không sửa mục tiêu, không thêm hay đổi việc con, không xóa.
- **FR-005**: Hệ thống MUST từ chối yêu cầu mở khi danh tính thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau khi bỏ khoảng trắng đầu và cuối. Lời từ chối MUST nói rõ danh tính chưa được đưa.
- **FR-006**: Hệ thống MUST từ chối yêu cầu mở khi danh tính còn nội dung sau khi bỏ khoảng trắng đầu và cuối nhưng không trùng danh tính nào đã lưu. Lời từ chối MUST nói rõ không có kế hoạch với danh tính đó, và MUST khác lời từ chối của FR-005.
- **FR-007**: Trước khi so, hệ thống MUST bỏ khoảng trắng đầu và cuối của danh tính. Phần còn lại MUST được so trùng từng ký tự với danh tính đã lưu, có phân biệt hoa thường.
- **FR-008**: Một lời từ chối MUST kết thúc yêu cầu mở đó. Sau lời từ chối, liệt kê kế hoạch đang hoạt động và mở một danh tính đang có MUST vẫn làm được, với dữ liệu như trước lời từ chối.
- **FR-009**: Hành vi tạo kế hoạch và liệt kê kế hoạch đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md) MUST giữ nguyên.

### Key Entities *(include if feature involves data)*

- **Kế hoạch** và **Việc con**: đúng hai thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này đọc một kế hoạch theo danh tính. Không thêm thuộc tính, không đổi nội dung sau khi lưu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% kế hoạch vừa lưu mở lại được bằng danh tính nhận lúc lưu, với đúng mục tiêu và đúng từng việc con theo thứ tự đã lưu.
- **SC-002**: Khi có từ hai kế hoạch trở lên, 100% lần mở bằng danh tính của một kế hoạch trả về kế hoạch đó; 0 lần trả về kế hoạch khác.
- **SC-003**: 100% yêu cầu mở với danh tính chưa được đưa, hoặc với danh tính không trùng kế hoạch nào, bị từ chối bằng lời nói rõ tình huống tương ứng. Số kế hoạch đang lưu không đổi sau mỗi lời từ chối.
- **SC-004**: Sau khi có thao tác mở, 100% kết quả đã chấp nhận của tạo và liệt kê trong [spec tạo và liệt kê](../001-create-list-plans/spec.md) vẫn đúng.
- **SC-005**: 100% lần mở thành công cho cùng một kết quả đọc với lần kế hoạch đó xuất hiện trong danh sách đang hoạt động: cùng danh tính, cùng mục tiêu, cùng các việc con theo cùng thứ tự.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Mở theo danh tính nằm trong toàn bộ kế hoạch đang hoạt động của người đó; không có chia sẻ hay phân quyền.
- "Đang hoạt động" giữ nghĩa ở [spec tạo và liệt kê](../001-create-list-plans/spec.md): kế hoạch đã lưu thành công và chưa bị đưa ra khỏi danh sách. Tính năng này không có thao tác hoàn thành, cất đi, hay xóa.
- Danh tính dùng để mở là danh tính hệ thống đã trả về lúc lưu. So khớp sau khi bỏ khoảng trắng đầu và cuối, trùng từng ký tự, có phân biệt hoa thường. Mục tiêu không thay cho danh tính.
- Hai lời từ chối (danh tính chưa được đưa, và không có kế hoạch với danh tính đó) khác nhau bằng nội dung chữ, đủ để người gọi biết phải hỏi lại danh tính hay báo là không tìm thấy.
- Lời từ chối là kết quả của yêu cầu mở. Yêu cầu sau vẫn được nhận.
- Kết quả mở dùng cùng các phần thông tin mà một kế hoạch có trong danh sách liệt kê, để người gọi đọc một kiểu. Không thêm trạng thái, hạn chót, hay ghi chú.
- Nơi lưu lâu dài của sản phẩm đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Tính năng này không dựng kho đó và không nối tới kho đang chạy. Đúng sai của việc mở phải quan sát được trước khi kho đó tồn tại.
- Ngoài phạm vi, theo mô tả tính năng và danh sách ở [docs/PRODUCT.md](../../docs/PRODUCT.md):
  - Hội thoại hỏi lại trước khi chốt kế hoạch (F01, F02).
  - Việc quyết định lúc nào gọi mở, tạo, hoặc liệt kê.
  - Đường nhận yêu cầu qua HTTP và qua Telegram (F11, F14).
  - Sửa việc con, thêm việc con, xem lại và điều chỉnh kế hoạch (F07, F08, F09).
  - Trạng thái, hạn chót, mức ưu tiên, hay ghi chú của việc con.
  - Sửa hoặc xóa kế hoạch.
  - Nhắc việc chủ động, đồng bộ ra ngoài, và các tính năng từ F10 trở đi.
  - Dựng hoặc kết nối kho dữ liệu thật.
