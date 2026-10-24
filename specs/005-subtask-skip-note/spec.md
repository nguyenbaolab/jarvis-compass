# Feature Specification: Bỏ qua việc con và ghi chú

**Feature Branch**: `005-subtask-skip-note`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Hoàn thiện F07: thêm trạng thái bỏ qua và ghi chú cho việc con. Trạng thái có thêm skipped bên cạnh pending và done. update_subtask nhận skipped. Chuyển tự do giữa ba trạng thái. Câu lỗi trạng thái không hợp lệ nêu đủ ba giá trị. Mỗi việc con có tối đa một ghi chú. set_subtask_note(plan_id, subtask_id, note) đặt ghi chú và ghi đè ghi chú cũ. Ghi chú được chuẩn hóa NFC rồi bỏ khoảng trắng hai đầu. None, rỗng hoặc chỉ khoảng trắng là xóa ghi chú. Quá giới hạn độ dài thì báo lỗi, không tự cắt; giới hạn theo cùng cách tiêu đề việc con đang được giới hạn. Đặt lại đúng ghi chú đang có sau chuẩn hóa thì không ghi. Thứ tự kiểm và câu lỗi cho danh tính kế hoạch, danh tính việc con, kế hoạch không có, việc con không thuộc kế hoạch giống update_subtask. Thành công trả về kế hoạch như update_subtask. Mọi tool trả mỗi việc con với trường note là chuỗi hoặc null. Việc con mới có note null. Đổi trạng thái không đụng ghi chú. Đặt ghi chú không đụng trạng thái. Mọi hành vi có test. Test hiện có vẫn đạt. Ngoài phạm vi: trạng thái cấp kế hoạch (F10), lịch sử nhiều ghi chú, xóa việc con, database thật. Không sửa docs/PRODUCT.md."

## User Scenarios & Testing *(mandatory)*

Người dùng cần đánh dấu một việc là bỏ qua, và gắn một ghi chú vào đúng việc đó, rồi xem lại đúng hai phần này. Đây là phần còn lại của F07 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Đặt `pending` và `done` đã chốt ở [spec cập nhật việc con](../003-update-subtask/spec.md). Tạo, liệt kê, mở, và thêm việc con đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec xem chi tiết](../002-get-plan-detail/spec.md), và [spec thêm việc con](../004-add-subtask/spec.md). Lát này thêm mã `skipped` và một ghi chú cho mỗi việc con.

### User Story 1 - Đánh dấu bỏ qua và chuyển giữa ba trạng thái (Priority: P1)

Khi một kế hoạch đã có việc con, người dùng đặt việc đó thành `skipped`, rồi chuyển sang `done` hoặc `pending`, rồi đặt lại `skipped`. Mỗi lần chỉ việc đó đổi trạng thái. Ghi chú của việc đó không đổi. Kế hoạch vẫn đang hoạt động.

**Why this priority**: Không có `skipped` thì người dùng chỉ đánh dấu xong hoặc chưa xong. Bỏ qua một bước là phần F07 chưa làm.

**Independent Test**: Lưu một kế hoạch có hai việc con. Đặt việc thứ nhất thành `skipped`, rồi `done`, rồi `pending`, rồi lại `skipped`. Mỗi lần mở kế hoạch và liệt kê. Việc kia giữ trạng thái cũ. Ghi chú cả hai vẫn trống.

**Acceptance Scenarios**:

1. **Given** một kế hoạch vừa lưu với hai việc con "Học hiragana" và "Luyện 10 phút mỗi ngày", **When** mở kế hoạch, liệt kê, và xem kết quả tạo, **Then** mỗi việc có trạng thái `pending` và ghi chú trống.
2. **Given** kế hoạch ở tình huống 1, **When** đặt việc "Học hiragana" thành `skipped`, **Then** yêu cầu thành công và trả về chính kế hoạch đó. Việc đó là `skipped`. Việc kia vẫn `pending`. Ghi chú cả hai vẫn trống. Danh tính, tiêu đề, mục tiêu, và thứ tự không đổi.
3. **Given** việc "Học hiragana" đang `skipped`, **When** đặt việc đó thành `done`, rồi thành `pending`, rồi lại thành `skipped`, **Then** mỗi lần thành công, lần mở và lần liệt kê ngay sau đó thấy đúng trạng thái vừa đặt, và việc kia vẫn `pending`.
4. **Given** việc "Học hiragana" đang `skipped`, **When** đặt lại `skipped`, **Then** yêu cầu thành công và việc đó vẫn `skipped`.
5. **Given** mọi việc con đều `skipped`, **When** liệt kê không lọc và mở kế hoạch, **Then** kế hoạch vẫn đang hoạt động, cùng danh tính và cùng mục tiêu.
6. **Given** một việc đang `pending`, **When** đặt trạng thái `" skipped "`, **Then** việc đó thành `skipped`.

---

### User Story 2 - Gắn một ghi chú và xem lại (Priority: P1)

Người dùng gắn một ghi chú vào đúng một việc con, ghi đè nếu đã có, hoặc xóa ghi chú. Trạng thái việc đó không đổi. Mọi cách đọc kế hoạch đều thấy ghi chú đó.

**Why this priority**: F07 gồm cả ghi chú. Không có bước này thì người dùng không lưu được lý do bỏ qua hay một lời nhắc trên việc.

**Independent Test**: Lưu một kế hoạch có hai việc con. Đặt việc thứ nhất thành `skipped`. Gắn ghi chú "Đợi giáo trình", ghi đè bằng ghi chú khác, rồi xóa. Mỗi lần mở và liệt kê. Trạng thái vẫn `skipped`. Việc kia không có ghi chú.

**Acceptance Scenarios**:

1. **Given** việc "Học hiragana" đang `skipped` và chưa có ghi chú, **When** đặt ghi chú "Đợi giáo trình", **Then** yêu cầu thành công và trả về kế hoạch. Việc đó vẫn `skipped`, ghi chú là "Đợi giáo trình". Việc kia vẫn `pending` và ghi chú trống.
2. **Given** việc đó đang có ghi chú "Đợi giáo trình", **When** đặt ghi chú "Học sau", **Then** ghi chú còn lại là "Học sau". Không giữ ghi chú cũ.
3. **Given** một việc chưa có ghi chú, **When** đặt ghi chú "  Đợi giáo trình  ", **Then** ghi chú được lưu và trả về là "Đợi giáo trình".
4. **Given** một việc đang có ghi chú "Đợi giáo trình", **When** đặt ghi chú thiếu, rỗng, hoặc chỉ gồm khoảng trắng, **Then** yêu cầu thành công và ghi chú của việc đó trở thành trống. Trạng thái không đổi.
5. **Given** một việc đang có ghi chú "Đợi giáo trình", **When** đặt lại đúng "Đợi giáo trình", hoặc "  Đợi giáo trình  ", **Then** yêu cầu thành công, ghi chú vẫn là "Đợi giáo trình", và dữ liệu đã lưu không bị ghi lại.
6. **Given** một việc chưa có ghi chú, **When** đặt ghi chú thiếu, rỗng, hoặc chỉ khoảng trắng, **Then** yêu cầu thành công, ghi chú vẫn trống, và dữ liệu đã lưu không bị ghi lại.
7. **Given** một việc có ghi chú "Đợi giáo trình" và trạng thái `skipped`, **When** đặt trạng thái thành `done`, **Then** trạng thái là `done` và ghi chú vẫn "Đợi giáo trình".
8. **Given** một việc có ghi chú dài, dài hơn những hạn thường gặp như vài trăm ký tự, **When** đặt ghi chú đó, **Then** ghi chú được lưu và trả về nguyên văn sau chuẩn hóa, không bị cắt.

---

### User Story 3 - Từ chối rõ khi không đổi được (Priority: P1)

Khi danh tính hoặc trạng thái không dùng được, người dùng nhận đúng một câu tiếng Việt của tình huống đó. Không trạng thái và không ghi chú nào đổi. Lần sau bằng dữ liệu đúng vẫn làm được.

**Why this priority**: Đổi nhầm việc, hoặc tưởng đã bỏ qua khi không tìm thấy việc, làm sai tiến độ. Câu trạng thái phải nói đủ ba giá trị để người gọi biết `skipped` là giá trị hợp lệ.

**Independent Test**: Lưu hai kế hoạch, mỗi kế hoạch một việc con. Gọi cập nhật trạng thái và gọi đặt ghi chú với danh tính kế hoạch trống, danh tính việc con trống, danh tính không tồn tại, việc con của kế hoạch kia, và trạng thái không thuộc ba mã. Mỗi lần đúng câu của tình huống đó. Sau đó đặt `skipped` và một ghi chú lên đúng một việc.

**Acceptance Scenarios**:

1. **Given** đang có một kế hoạch, **When** cập nhật trạng thái hoặc đặt ghi chú với danh tính kế hoạch thiếu, rỗng, hoặc chỉ khoảng trắng, kể cả khi phần còn lại cũng không dùng được, **Then** yêu cầu bị từ chối bằng đúng câu `Danh tính kế hoạch chưa được đưa.` Không việc nào đổi.
2. **Given** danh tính kế hoạch còn nội dung, **When** danh tính việc con thiếu, rỗng, hoặc chỉ khoảng trắng, kể cả khi không có kế hoạch đó, **Then** yêu cầu bị từ chối bằng đúng câu `Danh tính việc con chưa được đưa.`
3. **Given** hai danh tính còn nội dung, **When** trạng thái mới thiếu, rỗng, chỉ khoảng trắng, hoặc không phải đúng `pending`, `done`, hay `skipped`, kể cả `bỏ qua`, `Skipped`, hoặc `DONE`, và kể cả khi không có kế hoạch đó, **Then** yêu cầu bị từ chối bằng đúng câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.`
4. **Given** hai danh tính còn nội dung và trạng thái `skipped` hoặc một ghi chú hợp lệ, **When** không có kế hoạch với danh tính đó, **Then** yêu cầu bị từ chối bằng đúng câu `Không có kế hoạch với danh tính này.`
5. **Given** kế hoạch A và kế hoạch B, mỗi kế hoạch một việc con, **When** cập nhật A bằng danh tính việc con của B, với trạng thái `skipped` hoặc với một ghi chú, **Then** yêu cầu bị từ chối bằng đúng câu `Kế hoạch này không có việc con với danh tính này.` Cả hai kế hoạch giữ nguyên.
6. **Given** một lần vừa bị từ chối, **When** liệt kê, rồi đặt `skipped` và một ghi chú lên đúng việc, **Then** danh sách trước lần thành công giống như trước lời từ chối, và lần thành công trả về đúng việc đó.

---

### Edge Cases

- Danh tính kế hoạch và danh tính việc con được so theo cách đã chốt ở [spec cập nhật việc con](../003-update-subtask/spec.md): bỏ khoảng trắng đầu và cuối, phần còn lại trùng từng ký tự, có phân biệt hoa thường.
- Trạng thái, sau khi bỏ khoảng trắng đầu và cuối, chỉ được là đúng `pending`, đúng `done`, hoặc đúng `skipped`. Không NFC, không đổi hoa thường. `" skipped "` là `skipped`. `Skipped` và `bỏ qua` bị từ chối bằng câu nêu đủ ba giá trị.
- Khi cập nhật trạng thái, nhiều phần cùng không dùng được thì chỉ trả câu đầu tiên. Thứ tự giữ như [spec cập nhật việc con](../003-update-subtask/spec.md): danh tính kế hoạch, danh tính việc con, trạng thái, kế hoạch có thật, rồi việc con thuộc kế hoạch. Đầu vào được kiểm hết trước khi tra kế hoạch.
- Khi đặt ghi chú, thứ tự câu là: danh tính kế hoạch, danh tính việc con, kế hoạch có thật, rồi việc con thuộc kế hoạch. Ghi chú trống không phải lỗi. Ghi chú trống trên một danh tính kế hoạch không tồn tại vẫn là câu không có kế hoạch, không phải câu xóa ghi chú.
- Ghi chú được chuẩn hóa như tiêu đề việc con ở [spec tạo và liệt kê](../001-create-list-plans/spec.md): NFC rồi bỏ khoảng trắng đầu và cuối, giữ nguyên chữ bên trong kể cả khoảng trắng đôi. Dấu phẩy hay xuống dòng không tách ghi chú và không bị từ chối chỉ vì các ký tự đó.
- Tiêu đề việc con hiện không có hạn độ dài, như [spec tạo và liệt kê](../001-create-list-plans/spec.md). Ghi chú dùng cùng hạn đó: không có hạn số riêng, không bị cắt, và không có câu lỗi độ dài riêng trong lát này.
- Đặt lại đúng trạng thái đang có là thành công. Đặt lại đúng ghi chú đang có, sau chuẩn hóa, là thành công và không ghi lại dữ liệu đã lưu. Xóa ghi chú khi việc chưa có ghi chú cũng không ghi lại.
- Đổi trạng thái không đổi ghi chú, tiêu đề, danh tính, hay việc con khác. Đặt ghi chú không đổi trạng thái, tiêu đề, danh tính, hay việc con khác. Thứ tự việc con và trạng thái đang hoạt động của kế hoạch không đổi.
- Việc con mới, lúc tạo kế hoạch hoặc lúc thêm việc con, có ghi chú trống và trạng thái `pending`.
- Mọi việc con `done`, mọi việc con `skipped`, hoặc lẫn hai mã đó: kế hoạch vẫn đang hoạt động và vẫn được liệt kê khi không lọc.
- Một lời từ chối không chặn lần liệt kê, lần mở, lần cập nhật, lần thêm việc con, hay lần đặt ghi chú sau bằng dữ liệu đúng.
- Lời từ chối là đúng một câu đã chốt. Người gọi không thấy chi tiết kỹ thuật bên trong.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trạng thái việc con MUST là đúng một trong ba mã `pending`, `done`, hoặc `skipped`. Việc con mới, lúc tạo kế hoạch hoặc lúc thêm việc con, MUST có trạng thái `pending`.
- **FR-002**: Người dùng MUST đặt được trạng thái của một việc con thành `pending`, `done`, hoặc `skipped` khi đưa đủ danh tính kế hoạch, danh tính việc con, và trạng thái mới. Chuyển từ mã nào sang mã nào trong ba mã đều MUST thành công.
- **FR-003**: Hệ thống MUST từ chối khi trạng thái mới, sau khi bỏ khoảng trắng đầu và cuối, không phải đúng một trong ba mã, bằng đúng câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` Kiểm tra này MUST đứng sau kiểm danh tính kế hoạch và danh tính việc con, và trước khi tra kế hoạch có thật, cùng thứ tự đã chốt ở [spec cập nhật việc con](../003-update-subtask/spec.md).
- **FR-004**: Một lần đổi trạng thái thành công MUST chỉ đổi trạng thái của đúng việc được chỉ bằng danh tính. Ghi chú, tiêu đề, danh tính việc con, các việc khác, thứ tự, mục tiêu, danh tính kế hoạch, và trạng thái đang hoạt động của kế hoạch MUST giữ nguyên. Đặt lại đúng trạng thái đang có MUST thành công.
- **FR-005**: Mỗi việc con MUST có tối đa một ghi chú. Đặt ghi chú mới MUST ghi đè ghi chú đang có. Không có lịch sử các ghi chú cũ.
- **FR-006**: Ghi chú MUST được chuẩn hóa theo luật tiêu đề việc con ở [spec tạo và liệt kê](../001-create-list-plans/spec.md): NFC rồi bỏ khoảng trắng đầu và cuối. Phần chữ còn lại MUST được giữ nguyên. Ghi chú thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau chuẩn hóa MUST có nghĩa là xóa ghi chú. Xóa ghi chú MUST thành công.
- **FR-007**: Hạn độ dài của ghi chú MUST là hạn độ dài của tiêu đề việc con. Tiêu đề việc con hiện không có hạn độ dài. Hệ thống MUST không cắt ghi chú và MUST không đặt hạn số riêng cho ghi chú. Ghi chú còn nội dung sau chuẩn hóa MUST được lưu và trả về nguyên văn.
- **FR-008**: Đặt lại đúng ghi chú việc con đang có, sau chuẩn hóa, MUST thành công và MUST không ghi lại dữ liệu đã lưu. Xóa ghi chú khi việc đó chưa có ghi chú MUST thành công và MUST không ghi lại dữ liệu đã lưu.
- **FR-009**: Khi đặt ghi chú, hệ thống MUST từ chối danh tính kế hoạch, danh tính việc con, kế hoạch không có, và việc con không thuộc kế hoạch bằng đúng các câu và đúng thứ tự đã chốt cho các tình huống đó ở [spec cập nhật việc con](../003-update-subtask/spec.md). Đầu vào MUST được kiểm hết trước khi tra kế hoạch. Ghi chú trống MUST không phải một lý do từ chối.
- **FR-010**: Cập nhật trạng thái thành công và đặt ghi chú thành công MUST trả về kế hoạch sau thao tác, cùng các phần thông tin với kết quả cập nhật trạng thái. Việc được chỉ định MUST mang trạng thái và ghi chú vừa có hiệu lực.
- **FR-011**: Mỗi việc con trong kết quả tạo kế hoạch, liệt kê, mở một kế hoạch, cập nhật trạng thái, thêm việc con, và đặt ghi chú MUST có phần ghi chú tên `note`. Giá trị MUST là nội dung ghi chú đã lưu, hoặc trống khi việc không có ghi chú. Việc con mới MUST có ghi chú trống. Thứ tự các phần đã có, `id`, `title`, rồi `status`, MUST giữ nguyên. `note` MUST đứng sau `status`.
- **FR-012**: Đặt ghi chú MUST không đổi trạng thái của việc đó. Đổi trạng thái MUST không đổi ghi chú của việc đó.
- **FR-013**: Hành vi tạo kế hoạch, liệt kê, mở, thêm việc con, và đặt `pending` hoặc `done` đã chốt ở các spec trước MUST giữ nguyên, trừ câu từ chối trạng thái ở FR-003 và phần ghi chú ở FR-011.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Đúng thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này không thêm thuộc tính cho chính kế hoạch và không đổi nghĩa "đang hoạt động".
- **Việc con**: Đúng thực thể ở [spec cập nhật việc con](../003-update-subtask/spec.md), nay có trạng thái thêm mã `skipped` (bỏ qua) và tối đa một ghi chú. Ghi chú trống nghĩa là không có ghi chú. Vị trí trong danh sách không phải danh tính.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần đặt `skipped`, `done`, hoặc `pending` lên đúng một việc làm lần mở và lần liệt kê ngay sau đó thấy đúng mã vừa đặt, cùng danh tính việc con.
- **SC-002**: 100% lần đổi trạng thái giữ nguyên ghi chú của việc đó. 100% lần đặt ghi chú giữ nguyên trạng thái của việc đó.
- **SC-003**: 100% việc con mới có ghi chú trống khi tạo, khi thêm, khi liệt kê, và khi mở.
- **SC-004**: 100% lần đặt ghi chú còn nội dung làm lần mở và lần liệt kê ngay sau đó thấy đúng nội dung đã chuẩn hóa. 100% lần xóa ghi chú làm ghi chú trở thành trống.
- **SC-005**: 100% lần đặt lại đúng ghi chú đang có, sau chuẩn hóa, không ghi lại dữ liệu đã lưu. 0 lần ghi chú bị cắt.
- **SC-006**: 100% yêu cầu trạng thái không thuộc ba mã bị từ chối bằng đúng câu nêu đủ `pending`, `done`, và `skipped`. 100% yêu cầu danh tính không dùng được, ở cả cập nhật trạng thái và đặt ghi chú, bị từ chối bằng đúng câu của tình huống đó trong cập nhật việc con. Số trạng thái và số ghi chú không đổi sau mỗi lời từ chối.
- **SC-007**: 100% tình huống đã đạt của tạo, liệt kê, mở, thêm việc con, và đặt `pending` hoặc `done` vẫn đạt sau lát này, với phần ghi chú thêm như FR-011.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Không có chia sẻ hay phân quyền.
- "Đang hoạt động" giữ nghĩa ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Mọi việc con `done`, mọi việc con `skipped`, hoặc lẫn cả hai không đưa kế hoạch ra khỏi danh sách. Trạng thái cấp kế hoạch thuộc F10 và nằm ngoài lát này.
- `skipped` là mã ASCII thứ ba, cùng kiểu với `pending` và `done`. Câu từ chối trạng thái đang chạy được đổi trong code thành câu nêu đủ ba mã. Các file trong `specs/003-update-subtask/` giữ nguyên làm biên bản. Các câu danh tính giữ nguyên.
- Ghi chú trống trong kết quả là giá trị trống, không phải chuỗi rỗng. Người gọi đọc một kiểu ở mọi tool.
- Hạn độ dài lấy từ luật tiêu đề hiện có, không đặt số mới. Luật đó là không có hạn độ dài. Vì vậy không có tình huống "quá dài" để từ chối trong lát này, và không có câu lỗi độ dài riêng.
- Đặt lại đúng trạng thái đang có giữ cách đã chốt khi cập nhật việc con. Đặt lại đúng ghi chú, sau chuẩn hóa, không ghi lại dữ liệu đã lưu.
- Các kiểm tra cũ được sửa đúng ba loại để bộ kiểm tra vẫn đạt. Không loại sửa nào khác và không bỏ các kiểm tra đó. Loại một: câu từ chối trạng thái cũ thành câu nêu đủ ba mã ở FR-003. Loại hai: thêm `note` vào kỳ vọng JSON của việc con cho khớp FR-011. Loại ba: trong `tests/test_update_subtask.py`, `test_bad_status_wins_before_lookup` bỏ giá trị `skipped` khỏi danh sách trạng thái sai, vì lát này làm `skipped` hợp lệ. Các giá trị khác trong danh sách đó giữ nguyên. Các ca `Skipped`, `SKIPPED`, và `bỏ qua` nằm ở file test mới: đúng câu nêu đủ ba mã, và câu đó thắng trước khi tra kế hoạch.
- Nơi lưu lâu dài đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Lát này không dựng kho đó. Đúng sai phải quan sát được trước khi kho đó tồn tại.
- Dòng F07 trong [docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên. Lát này không sửa file đó.
- Ngoài phạm vi, theo mô tả tính năng:
  - Trạng thái cấp kế hoạch, kể cả coi kế hoạch là xong khi mọi việc con là `done` hoặc `skipped` (cùng F10).
  - Lịch sử nhiều ghi chú.
  - Xóa việc con, sửa tiêu đề, chèn, hay sắp xếp lại.
  - Hội thoại hỏi lại, việc quyết định lúc nào gọi tool, HTTP, và Telegram.
  - Dựng hoặc kết nối kho dữ liệu thật.
