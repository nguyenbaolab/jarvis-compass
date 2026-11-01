# Feature Specification: Đánh dấu việc con xong hoặc chưa xong

**Feature Branch**: `003-update-subtask`

**Created**: 2026-10-23

**Status**: Draft

**Bị thay một phần**: [spec 005](../005-subtask-skip-note/spec.md) thêm trạng thái `skipped`. Tập hai trạng thái và câu lỗi "chỉ nhận pending hoặc done" trong spec này và contracts/update-subtask.md không còn hiệu lực.

**Input**: User description: "F07 update_subtask: đánh dấu một việc con trong kế hoạch là xong hoặc chưa xong. Kế hoạch đã có mục tiêu và danh sách việc con (F04 tạo, F05 liệt kê, F06 xem chi tiết). Hiện việc con chỉ có tiêu đề, chưa có danh tính riêng và chưa có trạng thái. Người dùng (qua LLM) đưa danh tính kế hoạch, danh tính việc con và trạng thái mới để đánh dấu xong hoặc đánh dấu lại chưa xong. Sau khi cập nhật, xem lại bằng get_plan_detail và get_plans thì thấy trạng thái mới. Mỗi việc con có danh tính riêng, không đổi khi các việc con khác hay kế hoạch thay đổi, và được chỉ ra bằng danh tính này, không bằng vị trí. Việc con mới tạo mặc định chưa xong. Kết quả get_plans và get_plan_detail thêm danh tính và trạng thái cho mỗi việc con; trường title giữ nguyên tên và ý nghĩa. Cập nhật thành công trả về kế hoạch sau khi cập nhật, cùng dạng với kết quả get_plan_detail. Đặt trạng thái giống trạng thái hiện có là thành công. Chỉ việc con được chỉ định đổi trạng thái. Mục tiêu, các việc con khác, thứ tự việc con và trạng thái hoạt động của kế hoạch giữ nguyên. Lỗi tiếng Việt, không lộ lỗi nội bộ: thiếu danh tính kế hoạch như F06; không có kế hoạch như F06; thiếu danh tính việc con: 'Danh tính việc con chưa được đưa.'; kế hoạch có thật nhưng không có việc con đó, kể cả danh tính thuộc kế hoạch khác: 'Kế hoạch này không có việc con với danh tính này.' Ngoài phạm vi: sửa tiêu đề, thêm, xóa hay sắp xếp lại việc con, tự đổi trạng thái kế hoạch khi mọi việc con đã xong, chỉ việc con bằng vị trí."

## User Scenarios & Testing *(mandatory)*

Người dùng cần đánh dấu một việc trong kế hoạch là đã làm xong, hoặc đánh dấu lại là chưa xong, rồi xem lại đúng trạng thái đó. Đây là F07 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Cách tạo, liệt kê và mở một kế hoạch đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md) và [spec xem chi tiết](../002-get-plan-detail/spec.md). Tính năng này thêm danh tính và trạng thái cho từng việc con, rồi cho phép đổi trạng thái của đúng một việc con.

### User Story 1 - Đánh dấu một việc con và xem lại trạng thái (Priority: P1)

Khi một kế hoạch đã có việc con, người dùng chỉ đúng một việc bằng danh tính của việc đó, đặt trạng thái `done` (xong) hoặc `pending` (chưa xong), rồi thấy đúng mã đó khi mở kế hoạch và khi liệt kê kế hoạch đang hoạt động.

**Why this priority**: Không có bước này thì danh sách việc con chỉ là tiêu đề. Người dùng không ghi nhận được việc nào đã làm.

**Independent Test**: Lưu một kế hoạch có hai việc con. Xác nhận cả hai đang `pending` và mỗi việc có danh tính riêng. Đặt một việc thành `done`, rồi mở kế hoạch và liệt kê. Đối chiếu trạng thái, tiêu đề, thứ tự, mục tiêu, và việc còn lại vẫn `pending`.

**Acceptance Scenarios**:

1. **Given** một kế hoạch vừa lưu với mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày" theo thứ tự đó, **When** mở kế hoạch và liệt kê kế hoạch đang hoạt động, **Then** mỗi việc con có danh tính riêng, khác danh tính việc kia và khác danh tính kế hoạch, trạng thái `pending`, và phần tiêu đề vẫn tên `title` với đúng nội dung đã lưu.
2. **Given** kế hoạch ở tình huống 1, **When** đặt việc "Học hiragana" thành `done` bằng danh tính kế hoạch và danh tính của việc đó, **Then** yêu cầu thành công và trả về chính kế hoạch đó sau khi cập nhật, cùng các phần thông tin với kết quả mở kế hoạch: mục tiêu cũ, đúng hai việc con theo thứ tự cũ, việc được chỉ định là `done`, việc còn lại `pending`, và danh tính từng việc giữ nguyên.
3. **Given** việc "Học hiragana" đang `done`, **When** đặt lại việc đó thành `pending`, **Then** lần mở kế hoạch và lần liệt kê đều thấy việc đó `pending`, việc kia vẫn `pending`, tiêu đề và thứ tự không đổi.
4. **Given** việc "Học hiragana" đang `done`, **When** đặt lại trạng thái `done`, **Then** yêu cầu thành công, trả về kế hoạch, và việc đó vẫn `done`. Đây không phải lỗi.
5. **Given** hai việc con cùng tiêu đề "Ôn bài" trên cùng một kế hoạch, **When** đặt `done` bằng danh tính của việc đứng trước, **Then** chỉ việc có danh tính đó là `done`. Việc cùng tiêu đề còn lại vẫn `pending`. Hai danh tính vẫn khác nhau.
6. **Given** mọi việc con của một kế hoạch đều `done`, **When** liệt kê kế hoạch đang hoạt động và mở kế hoạch đó, **Then** kế hoạch vẫn đang hoạt động, cùng danh tính kế hoạch, cùng mục tiêu, và từng việc con vẫn `done`.

---

### User Story 2 - Từ chối rõ khi không cập nhật được (Priority: P1)

Khi danh tính hoặc trạng thái không dùng được, người dùng nhận một câu từ chối tiếng Việt đúng tình huống. Không việc nào đổi trạng thái, và lần cập nhật sau bằng dữ liệu đúng vẫn làm được.

**Why this priority**: Cập nhật nhầm việc, hoặc tưởng đã cập nhật khi không tìm thấy việc, làm sai tiến độ. Các câu từ chối phải khác nhau để người gọi biết phải hỏi lại phần nào.

**Independent Test**: Lưu hai kế hoạch, mỗi kế hoạch có một việc con. Gọi cập nhật với danh tính kế hoạch bỏ trống, với danh tính kế hoạch không tồn tại, với danh tính việc con bỏ trống, với danh tính việc con của kế hoạch kia, và với trạng thái không phải `pending` hay `done`. Mỗi lần bị từ chối bằng đúng câu của tình huống đó. Sau đó đặt `done` đúng một việc và mở lại thấy chỉ việc đó `done`.

**Acceptance Scenarios**:

1. **Given** đang có hai kế hoạch, **When** cập nhật với danh tính kế hoạch thiếu, rỗng, hoặc chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối bằng đúng câu `Danh tính kế hoạch chưa được đưa.` và không việc con nào đổi trạng thái.
2. **Given** đang có hai kế hoạch, **When** cập nhật bằng một danh tính kế hoạch có nội dung nhưng không trùng kế hoạch nào đã lưu, với danh tính việc con còn nội dung và trạng thái `pending` hoặc `done`, **Then** yêu cầu bị từ chối bằng đúng câu `Không có kế hoạch với danh tính này.`
3. **Given** một kế hoạch có thật và một việc con của nó, **When** danh tính việc con thiếu, rỗng, hoặc chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối bằng đúng câu `Danh tính việc con chưa được đưa.` và việc con đó vẫn `pending`.
4. **Given** kế hoạch A và kế hoạch B, mỗi kế hoạch có việc con riêng, **When** cập nhật kế hoạch A bằng danh tính việc con của kế hoạch B và trạng thái `done`, **Then** yêu cầu bị từ chối bằng đúng câu `Kế hoạch này không có việc con với danh tính này.` Việc con của A và của B giữ nguyên trạng thái.
5. **Given** một kế hoạch có hai việc con, **When** đưa tiêu đề một việc con, hoặc vị trí trong danh sách, mà chuỗi đó không phải danh tính đã cấp cho việc con, cùng với trạng thái `done`, **Then** yêu cầu bị từ chối bằng đúng câu `Kế hoạch này không có việc con với danh tính này.`
6. **Given** danh tính kế hoạch và danh tính việc con đều đúng, **When** trạng thái mới thiếu, rỗng, chỉ gồm khoảng trắng, hoặc không phải `pending` hay `done`, **Then** yêu cầu bị từ chối bằng đúng câu `Trạng thái việc con chỉ nhận pending hoặc done.` và việc con giữ trạng thái cũ.
7. **Given** một lần cập nhật vừa bị từ chối, **When** liệt kê kế hoạch đang hoạt động, rồi đặt `done` đúng một việc con bằng danh tính của nó, **Then** danh sách trước lần đặt `done` giống như trước lời từ chối, và lần đặt `done` trả về đúng việc đó ở trạng thái `done`.

---

### Edge Cases

- Danh tính kế hoạch thiếu, rỗng, hoặc chỉ khoảng trắng: từ chối vì danh tính kế hoạch chưa được đưa. Không kế hoạch nào bị thêm, sửa, hay mất.
- Danh tính kế hoạch có nội dung nhưng không trùng kế hoạch nào: từ chối vì không có kế hoạch đó. Câu này khác câu danh tính kế hoạch chưa được đưa.
- Danh tính kế hoạch được so theo cách đã chốt khi mở kế hoạch ở [spec xem chi tiết](../002-get-plan-detail/spec.md): bỏ khoảng trắng đầu và cuối, phần còn lại trùng từng ký tự, có phân biệt hoa thường.
- Danh tính việc con thiếu, rỗng, hoặc chỉ khoảng trắng: từ chối vì danh tính việc con chưa được đưa. Việc này được kiểm tra trên đầu vào, trước khi tra kế hoạch có thật.
- Danh tính việc con có khoảng trắng đầu hoặc cuối: bỏ khoảng trắng đó rồi mới so. Phần còn lại trùng từng ký tự với danh tính đã cấp, có phân biệt hoa thường.
- Danh tính việc con thuộc kế hoạch khác, là tiêu đề, là một đoạn của tiêu đề, hoặc là vị trí trong danh sách, mà chuỗi đó không phải danh tính đã cấp: từ chối vì kế hoạch này không có việc con với danh tính đó. Kế hoạch kia không đổi.
- Kế hoạch không có việc con: mọi danh tính việc con còn nội dung đều bị từ chối vì kế hoạch này không có việc con đó.
- Trạng thái mới, sau khi bỏ khoảng trắng đầu và cuối, chỉ được là `pending` hoặc `done`. Giá trị khác, kể cả `xong` hoặc `chưa xong`, bị từ chối bằng câu `Trạng thái việc con chỉ nhận pending hoặc done.` Việc con giữ trạng thái cũ.
- Khi nhiều phần cùng không dùng được, chỉ trả câu đầu tiên gặp. Thứ tự: (1) danh tính kế hoạch, (2) danh tính việc con, (3) trạng thái, (4) kế hoạch có thật, (5) việc con thuộc kế hoạch. Đầu vào được kiểm hết trước khi tra kế hoạch. Danh tính kế hoạch còn nội dung nhưng danh tính việc con trống thì câu danh tính việc con, kể cả khi kế hoạch đó không tồn tại và trạng thái cũng không hợp lệ. Danh tính kế hoạch và danh tính việc con còn nội dung nhưng trạng thái không hợp lệ thì câu trạng thái, kể cả khi không có kế hoạch đó.
- Đặt cùng trạng thái đang có là thành công và trả về kế hoạch. Không tạo thêm việc con, không đổi tiêu đề, không đổi danh tính.
- Cập nhật một việc con không đổi mục tiêu, không đổi tiêu đề hay trạng thái của việc con khác, không đổi thứ tự, không đổi danh tính kế hoạch, và không đưa kế hoạch ra khỏi danh sách đang hoạt động.
- Mọi việc con đều `done`: kế hoạch vẫn đang hoạt động và vẫn được liệt kê khi không lọc.
- Một lời từ chối không chặn lần liệt kê sau, lần mở sau, hay lần cập nhật sau bằng dữ liệu đúng.
- Lời từ chối là đúng một câu đã chốt cho tình huống đó. Người gọi không thấy chi tiết kỹ thuật bên trong.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mỗi việc con MUST có một danh tính riêng, được cấp lúc việc con được lưu cùng kế hoạch. Danh tính đó MUST khác danh tính của mọi việc con khác và khác danh tính kế hoạch. Danh tính MUST giữ nguyên khi trạng thái của chính việc đó hay của việc con khác đổi.
- **FR-002**: Việc con mới lưu MUST có trạng thái `pending`, cho tới khi một lần cập nhật thành công đặt trạng thái khác.
- **FR-003**: Mỗi việc con trong kết quả tạo kế hoạch, trong kết quả liệt kê, trong kết quả mở một kế hoạch, và trong kết quả cập nhật thành công MUST gồm danh tính việc con, trạng thái, và phần tiêu đề. Phần tiêu đề MUST giữ tên `title` và MUST giữ đúng nội dung đã lưu. Thứ tự việc con MUST là thứ tự đã lưu.
- **FR-004**: Người dùng MUST đặt được trạng thái của một việc con khi đưa đủ danh tính kế hoạch, danh tính việc con, và trạng thái mới là `pending` hoặc `done`.
- **FR-005**: Cập nhật thành công MUST trả về kế hoạch sau khi cập nhật, cùng các phần thông tin với kết quả mở một kế hoạch. Việc con được chỉ định MUST ở trạng thái vừa đặt. Danh tính kế hoạch, mục tiêu, các việc con khác, và thứ tự MUST giữ nguyên.
- **FR-006**: Đặt lại đúng trạng thái việc con đang có MUST thành công và MUST trả về kế hoạch. Trạng thái, tiêu đề, và danh tính của việc đó MUST giữ nguyên.
- **FR-007**: Một lần cập nhật thành công MUST chỉ đổi trạng thái của đúng việc con được chỉ bằng danh tính. MUST không đổi trạng thái hoạt động của kế hoạch, kể cả khi mọi việc con là done.
- **FR-008**: Hệ thống MUST từ chối khi danh tính kế hoạch thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau khi bỏ khoảng trắng đầu và cuối, bằng đúng câu `Danh tính kế hoạch chưa được đưa.`
- **FR-009**: Hệ thống MUST từ chối khi danh tính kế hoạch còn nội dung nhưng không trùng kế hoạch nào đã lưu, bằng đúng câu `Không có kế hoạch với danh tính này.` Cách so danh tính kế hoạch MUST giống cách đã chốt ở [spec xem chi tiết](../002-get-plan-detail/spec.md). Kiểm tra này MUST đứng sau khi đầu vào đã qua FR-008, FR-010, và FR-012.
- **FR-010**: Hệ thống MUST từ chối khi danh tính việc con thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau khi bỏ khoảng trắng đầu và cuối, bằng đúng câu `Danh tính việc con chưa được đưa.` Kiểm tra này MUST đứng sau FR-008 và trước khi tra kế hoạch có thật.
- **FR-011**: Khi kế hoạch đã xác định và danh tính việc con còn nội dung, hệ thống MUST từ chối nếu việc con đó không thuộc kế hoạch này, kể cả khi danh tính thuộc kế hoạch khác, bằng đúng câu `Kế hoạch này không có việc con với danh tính này.` Kế hoạch khác MUST giữ nguyên. Kiểm tra này MUST đứng sau FR-009.
- **FR-012**: Hệ thống MUST từ chối khi trạng thái mới, sau khi bỏ khoảng trắng đầu và cuối, không phải đúng `pending` hoặc đúng `done`, bằng đúng câu `Trạng thái việc con chỉ nhận pending hoặc done.` Kiểm tra này MUST đứng sau FR-008 và FR-010, và trước khi tra kế hoạch có thật.
- **FR-013**: Khi nhiều điều kiện từ chối cùng xảy ra, hệ thống MUST trả đúng một câu, theo thứ tự FR-008, FR-010, FR-012, FR-009, rồi FR-011. Đầu vào MUST được kiểm hết trước khi tra kế hoạch.
- **FR-014**: Mọi lời từ chối MUST là đúng câu của tình huống đó và MUST kết thúc yêu cầu cập nhật. MUST không kèm chi tiết kỹ thuật bên trong. Dữ liệu đã lưu MUST giữ nguyên. Lần liệt kê, lần mở, và lần cập nhật sau bằng dữ liệu đúng MUST vẫn làm được.
- **FR-015**: Hành vi tạo kế hoạch, liệt kê kế hoạch, và mở một kế hoạch đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md) và [spec xem chi tiết](../002-get-plan-detail/spec.md) MUST giữ nguyên, trừ phần việc con được thêm danh tính và trạng thái theo FR-001, FR-002, và FR-003.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Đúng thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này không thêm thuộc tính cho chính kế hoạch và không đổi nghĩa "đang hoạt động".
- **Việc con**: Một việc thuộc về đúng một kế hoạch, như [spec tạo và liệt kê](../001-create-list-plans/spec.md), nay thêm danh tính riêng và trạng thái. Trạng thái là mã `pending` (chưa xong) hoặc `done` (xong). Phần tiêu đề giữ tên `title` và giữ nghĩa là nội dung việc con đã lưu. Vị trí trong danh sách không phải danh tính.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% việc con vừa lưu có danh tính riêng và trạng thái `pending` khi tạo, khi liệt kê, và khi mở kế hoạch.
- **SC-002**: 100% lần đặt `done` hoặc `pending` lên đúng một việc con đang có làm lần mở kế hoạch và lần liệt kê ngay sau đó thấy trạng thái vừa đặt, với cùng danh tính việc con.
- **SC-003**: 100% lần đặt lại đúng trạng thái đang có thành công. 0 lần bị từ chối chỉ vì trạng thái không đổi.
- **SC-004**: Sau mỗi lần cập nhật thành công, 100% việc con không được chỉ định giữ nguyên tiêu đề, danh tính, và trạng thái. 100% kế hoạch giữ nguyên mục tiêu, thứ tự việc con, danh tính kế hoạch, và vẫn đang hoạt động.
- **SC-005**: 100% yêu cầu cập nhật thuộc năm tình huống từ chối bị từ chối bằng đúng câu của tình huống đó. Số kế hoạch và trạng thái việc con không đổi sau mỗi lời từ chối.
- **SC-006**: Khi một kế hoạch có từ hai việc con trở lên, 100% lần cập nhật bằng danh tính của một việc chỉ đổi việc đó. 0 lần cập nhật bằng vị trí trong danh sách làm đổi một việc con, trừ khi chuỗi vị trí tình cờ trùng danh tính đã cấp.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Cập nhật nằm trong toàn bộ kế hoạch đang hoạt động của người đó; không có chia sẻ hay phân quyền.
- "Đang hoạt động" giữ nghĩa ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này không có thao tác hoàn thành, cất đi, hay xóa kế hoạch. Mọi việc con đã xong không làm kế hoạch ra khỏi danh sách.
- Danh tính việc con do hệ thống cấp lúc lưu, không do người gọi chọn, và không suy ra từ vị trí hay từ tiêu đề. Hai việc con trùng tiêu đề vẫn là hai việc, với hai danh tính.
- Danh tính kế hoạch và danh tính việc con được so sau khi bỏ khoảng trắng đầu và cuối, trùng từng ký tự, có phân biệt hoa thường. Quy tắc này cho danh tính kế hoạch là quy tắc đã chốt khi mở kế hoạch.
- Trạng thái việc con là một giá trị trong tập cố định, dùng mã ASCII: `pending` (chưa xong) và `done` (xong). Đầu vào của cập nhật việc con và đầu ra của tạo kế hoạch, liệt kê, mở một kế hoạch, và cập nhật việc con đều dùng hai mã này. Tập giá trị được chọn để sau này thêm `skipped` mà không phá kiểu.
- Câu từ chối khi danh tính kế hoạch không dùng được là đúng hai câu đã dùng khi mở kế hoạch: `Danh tính kế hoạch chưa được đưa.` và `Không có kế hoạch với danh tính này.`
- Kết quả tạo kế hoạch dùng cùng các phần của việc con với kết quả liệt kê và kết quả mở, vì người gọi đọc một kế hoạch theo một kiểu. Đây là chỗ F07 mở rộng hình kế hoạch đã chốt ở F04 và F06: thêm danh tính và trạng thái, không đổi các phần cũ.
- Nơi lưu lâu dài của sản phẩm đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Tính năng này không dựng kho đó và không nối tới kho đang chạy. Đúng sai của việc cập nhật phải quan sát được trước khi kho đó tồn tại.
- Ngoài phạm vi, theo mô tả tính năng:
  - Sửa tiêu đề việc con.
  - Thêm, xóa, hay sắp xếp lại việc con (F08).
  - Tự đổi trạng thái hoạt động của kế hoạch khi mọi việc con đã xong.
  - Chỉ một việc con bằng vị trí trong danh sách.
  - Đánh dấu bỏ qua (skip) và ghi chú (note) cho việc con là lát sau của F07. [docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên dòng F07 gốc.
  - Hội thoại hỏi lại trước khi chốt kế hoạch (F01, F02).
  - Việc quyết định lúc nào gọi cập nhật, tạo, liệt kê, hoặc mở.
  - Xem lại và điều chỉnh kế hoạch (F09).
  - Đường nhận yêu cầu qua HTTP và qua Telegram (F11, F14).
  - Nhắc việc chủ động, đồng bộ ra ngoài, và các tính năng từ F10 trở đi.
  - Dựng hoặc kết nối kho dữ liệu thật.
