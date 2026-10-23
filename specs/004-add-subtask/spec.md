# Feature Specification: Thêm một việc con vào kế hoạch đang có

**Feature Branch**: `004-add-subtask`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "F08 add_subtask: thêm một việc con vào một kế hoạch đang có. Tool được LLM của planning service gọi khi người dùng muốn bổ sung bước vào kế hoạch đã tạo. Đầu vào là danh tính kế hoạch và tiêu đề của một việc con mới. Mỗi lần gọi thêm đúng một việc con, luôn vào cuối danh sách, giữ nguyên thứ tự và nội dung các việc con có sẵn. Việc con mới có danh tính riêng, sinh theo cùng cách với việc con tạo bởi create_plan, và luôn bắt đầu ở trạng thái pending. Không cho chọn trạng thái lúc thêm. Tiêu đề theo đúng luật đang áp dụng cho tiêu đề việc con trong create_plan (chuẩn hóa, từ chối tiêu đề rỗng hay chỉ có khoảng trắng, và mọi luật khác create_plan đang có). Không đặt luật mới riêng cho tính năng này. Thành công thì trả về toàn bộ kế hoạch sau khi thêm, cùng hình với kết quả mở một kế hoạch. Kế hoạch có N việc con thì sau khi thêm có N+1, việc con mới ở cuối, N việc con cũ không đổi. Danh tính kế hoạch thiếu, rỗng hoặc không tồn tại thì báo lỗi theo cùng cách và cùng câu như update_subtask. Tiêu đề không hợp lệ thì báo lỗi theo cùng cách create_plan đang báo, và không ghi gì. Kiểm hết đầu vào trước khi tra dữ liệu đã lưu, giống update_subtask. Liệt kê và mở kế hoạch thấy việc con mới ngay sau khi thêm. Ngoài phạm vi: chèn vào vị trí bất kỳ, sắp xếp lại, xóa hay sửa tiêu đề (F09 hoặc lát sau); thêm nhiều việc con trong một lần; đổi trạng thái (F07). Không sửa docs/PRODUCT.md. DB thật chưa có (F03)."

## User Scenarios & Testing *(mandatory)*

Người dùng cần bổ sung một bước vào kế hoạch đã có, rồi thấy bước đó đứng cuối danh sách việc con. Đây là F08 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Cách tạo, liệt kê, mở một kế hoạch, và cách mỗi việc con mang danh tính cùng trạng thái đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec xem chi tiết](../002-get-plan-detail/spec.md), và [spec cập nhật việc con](../003-update-subtask/spec.md). Tính năng này chỉ thêm đúng một việc con vào cuối một kế hoạch đang có.

### User Story 1 - Thêm một việc con vào cuối và thấy lại (Priority: P1)

Khi một kế hoạch đã lưu, người dùng đưa danh tính kế hoạch đó và tiêu đề một việc mới. Việc mới đứng sau mọi việc con đang có. Các việc cũ giữ nguyên danh tính, tiêu đề, trạng thái, và thứ tự. Người dùng nhận lại cả kế hoạch, rồi thấy đúng việc mới khi mở kế hoạch và khi liệt kê kế hoạch đang hoạt động.

**Why this priority**: Không có bước này thì muốn thêm một việc phải làm lại cả kế hoạch. Thêm vào cuối, giữ nguyên phần đã có, là lát nhỏ nhất vẫn mang lại giá trị.

**Independent Test**: Lưu một kế hoạch có hai việc con, một việc `pending` và một việc `done`. Thêm một tiêu đề hợp lệ. Đối chiếu kết quả trả về, lần mở kế hoạch, và lần liệt kê: ba việc con, việc mới ở cuối, hai việc cũ không đổi.

**Acceptance Scenarios**:

1. **Given** một kế hoạch đã lưu với mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana" đang `pending`, "Luyện 10 phút mỗi ngày" đang `done`, theo thứ tự đó, **When** thêm tiêu đề "Mua giáo trình" bằng danh tính kế hoạch đó, **Then** yêu cầu thành công và trả về chính kế hoạch đó sau khi thêm, cùng các phần thông tin với kết quả mở kế hoạch: cùng danh tính kế hoạch, cùng mục tiêu, đúng ba việc con theo thứ tự cũ rồi đến việc mới. Hai việc cũ giữ nguyên danh tính, tiêu đề, và trạng thái. Việc mới có danh tính riêng, khác danh tính kế hoạch và khác danh tính hai việc cũ, tiêu đề "Mua giáo trình", trạng thái `pending`.
2. **Given** một kế hoạch chỉ có mục tiêu "Viết báo cáo" và không có việc con, **When** thêm tiêu đề "Soạn dàn ý", **Then** kết quả có đúng một việc con, việc đó ở vị trí duy nhất, tiêu đề "Soạn dàn ý", trạng thái `pending`, và có danh tính riêng.
3. **Given** kế hoạch ở tình huống 1 vừa thêm thành công, **When** mở kế hoạch bằng danh tính của nó và liệt kê kế hoạch đang hoạt động, **Then** cả hai lần đều thấy việc "Mua giáo trình" với cùng danh tính đã trả về, cùng tiêu đề, trạng thái `pending`, đứng cuối. Mục tiêu, danh tính kế hoạch, và hai việc cũ không đổi. Vị trí của kế hoạch này trong danh sách không lọc không đổi.
4. **Given** một kế hoạch có một việc con "Ôn bài", **When** thêm một việc con nữa cũng tiêu đề "Ôn bài", **Then** kế hoạch có hai việc con cùng tiêu đề, hai danh tính khác nhau, việc mới đứng sau, việc cũ giữ nguyên danh tính và trạng thái.
5. **Given** một kế hoạch đang có, **When** thêm tiêu đề "  Mua giáo trình  ", **Then** tiêu đề được lưu và trả về là "Mua giáo trình".
6. **Given** một kế hoạch có một việc con, **When** thêm "Mua sách" rồi thêm "Đọc chương 1", **Then** sau lần thứ hai kế hoạch có ba việc con theo thứ tự việc cũ, "Mua sách", "Đọc chương 1". Danh tính và trạng thái của hai việc thêm trước giữ nguyên.
7. **Given** ba kế hoạch đã lưu lần lượt là A, rồi B, rồi C, và việc con của B đang `done`, **When** thêm một việc vào B, **Then** B vẫn đang hoạt động, vẫn đứng đúng chỗ cũ khi liệt kê không lọc, việc cũ của B vẫn `done`, và việc mới của B là `pending`.
8. **Given** danh tính kế hoạch đã lưu, có khoảng trắng ở đầu và cuối, và một tiêu đề hợp lệ, **When** thêm việc con, **Then** yêu cầu thành công trên đúng kế hoạch đó.

---

### User Story 2 - Từ chối rõ khi không thêm được (Priority: P1)

Khi danh tính kế hoạch hoặc tiêu đề không dùng được, người dùng nhận một câu từ chối tiếng Việt đúng tình huống. Không có việc con nào được thêm. Lần thêm sau bằng dữ liệu đúng vẫn làm được.

**Why this priority**: Tưởng đã thêm khi kế hoạch không tồn tại, hoặc ghi một tiêu đề trống, làm sai danh sách việc. Câu từ chối phải trùng câu người gọi đã gặp ở các thao tác trước, để biết phải hỏi lại phần nào.

**Independent Test**: Lưu một kế hoạch có một việc con. Gọi thêm với danh tính kế hoạch bỏ trống, với danh tính không tồn tại nhưng tiêu đề hợp lệ, với tiêu đề chỉ gồm khoảng trắng trên kế hoạch có thật, và với tiêu đề trống kèm danh tính không tồn tại. Mỗi lần bị từ chối bằng đúng câu của tình huống đó, và việc con cũ vẫn còn một mình. Sau đó thêm một tiêu đề hợp lệ và mở lại thấy đúng hai việc.

**Acceptance Scenarios**:

1. **Given** đang có một kế hoạch, **When** thêm với danh tính kế hoạch thiếu, rỗng, hoặc chỉ gồm khoảng trắng, kể cả khi tiêu đề cũng trống, **Then** yêu cầu bị từ chối bằng đúng câu `Danh tính kế hoạch chưa được đưa.` và không việc con nào được thêm.
2. **Given** đang có một kế hoạch, **When** thêm bằng một danh tính kế hoạch có nội dung nhưng không trùng kế hoạch nào đã lưu, với tiêu đề "Mua giáo trình", **Then** yêu cầu bị từ chối bằng đúng câu `Không có kế hoạch với danh tính này.`
3. **Given** một kế hoạch có thật và một việc con của nó, **When** tiêu đề thiếu, rỗng, hoặc chỉ gồm khoảng trắng, **Then** yêu cầu bị từ chối bằng đúng câu `Việc con không được để trống.` Việc con cũ giữ nguyên, và không có việc con mới.
4. **Given** không có kế hoạch nào trùng danh tính được đưa, và tiêu đề rỗng hoặc chỉ gồm khoảng trắng, **When** thêm việc con, **Then** yêu cầu bị từ chối bằng đúng câu `Việc con không được để trống.` Không có kế hoạch nào được thêm hay sửa.
5. **Given** một kế hoạch có mục tiêu "Học tiếng Nhật", **When** đưa chính mục tiêu đó, hoặc cùng danh tính đã lưu nhưng khác hoa thường, làm danh tính kế hoạch, cùng với tiêu đề hợp lệ, **Then** yêu cầu bị từ chối bằng đúng câu `Không có kế hoạch với danh tính này.`
6. **Given** một lần thêm vừa bị từ chối, **When** liệt kê kế hoạch đang hoạt động, rồi thêm một tiêu đề hợp lệ vào đúng kế hoạch, **Then** danh sách trước lần thêm hợp lệ giống như trước lời từ chối, và lần thêm hợp lệ trả về việc mới ở cuối.

---

### Edge Cases

- Danh tính kế hoạch thiếu, rỗng, hoặc chỉ khoảng trắng: từ chối vì danh tính kế hoạch chưa được đưa. Không kế hoạch nào bị thêm, sửa, hay mất.
- Danh tính kế hoạch có nội dung nhưng không trùng kế hoạch nào: từ chối vì không có kế hoạch đó. Câu này khác câu danh tính kế hoạch chưa được đưa, và là đúng câu đã dùng khi cập nhật việc con.
- Danh tính kế hoạch được so theo cách đã chốt khi cập nhật việc con ở [spec cập nhật việc con](../003-update-subtask/spec.md): bỏ khoảng trắng đầu và cuối, phần còn lại trùng từng ký tự, có phân biệt hoa thường.
- Tiêu đề thiếu, rỗng, hoặc chỉ khoảng trắng sau khi chuẩn hóa: từ chối vì việc con không được để trống. Đây là cùng lời tạo kế hoạch đang dùng khi một việc con rỗng hoặc chỉ gồm khoảng trắng. Không ghi gì.
- Tiêu đề được chuẩn hóa theo luật tiêu đề việc con đã chốt khi tạo kế hoạch ở [spec tạo và liệt kê](../001-create-list-plans/spec.md): bỏ khoảng trắng đầu và cuối, giữ nguyên chữ bên trong kể cả khoảng trắng đôi, và hai cách mã hóa của cùng một chữ có dấu được lưu thành cùng một dạng. Không thêm hạn độ dài, không cấm trùng tiêu đề, không cấm tiêu đề trùng mục tiêu.
- Khi nhiều phần cùng không dùng được, chỉ trả câu đầu tiên gặp. Thứ tự: (1) danh tính kế hoạch, (2) tiêu đề, (3) kế hoạch có thật. Đầu vào được kiểm hết trước khi tra kế hoạch. Tiêu đề không hợp lệ thì câu tiêu đề, kể cả khi danh tính kế hoạch không trùng kế hoạch nào.
- Thêm thành công không đổi mục tiêu, không đổi danh tính kế hoạch, không đổi danh tính, tiêu đề, hay trạng thái của việc con đã có, không đổi thứ tự việc con đã có, và không đưa kế hoạch ra khỏi danh sách đang hoạt động. Vị trí kế hoạch khi liệt kê không lọc giữ nguyên.
- Kế hoạch chưa có việc con vẫn thêm được. Việc mới là việc con duy nhất.
- Hai lần thêm liên tiếp: mỗi lần thêm một việc vào cuối. Việc thêm ở lần trước không bị cấp lại danh tính và không đổi trạng thái.
- Tiêu đề trùng một việc đã có: giữ cả hai. Việc mới có danh tính riêng và đứng cuối.
- Việc con đã có đều `done`: kế hoạch vẫn đang hoạt động. Việc mới vẫn `pending`. Các việc cũ vẫn `done`.
- Một tiêu đề là một việc con. Dấu phẩy hay xuống dòng trong tiêu đề không tách thành nhiều việc, và không bị từ chối chỉ vì có các ký tự đó.
- Từ khóa khi liệt kê vẫn chỉ xét mục tiêu, theo [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tiêu đề việc vừa thêm không làm kế hoạch khớp một từ khóa chỉ nằm trong tiêu đề đó.
- Một lời từ chối không chặn lần liệt kê sau, lần mở sau, hay lần thêm sau bằng dữ liệu đúng.
- Lời từ chối là đúng một câu đã chốt cho tình huống đó. Người gọi không thấy chi tiết kỹ thuật bên trong.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Khi nhận danh tính của một kế hoạch đã lưu và một tiêu đề hợp lệ, hệ thống MUST thêm đúng một việc con vào cuối danh sách việc con của kế hoạch đó. Việc con đã có MUST giữ nguyên danh tính, tiêu đề, trạng thái, và thứ tự. Danh tính kế hoạch, mục tiêu, và trạng thái đang hoạt động của kế hoạch MUST giữ nguyên.
- **FR-002**: Việc con mới MUST có một danh tính riêng, được cấp theo cùng cách danh tính được cấp cho việc con lúc tạo kế hoạch, như [spec cập nhật việc con](../003-update-subtask/spec.md). Danh tính đó MUST khác danh tính kế hoạch và khác danh tính mọi việc con khác. Người gọi MUST không được chọn danh tính này. Danh tính MUST giữ nguyên ở lần mở sau và lần liệt kê sau.
- **FR-003**: Việc con mới MUST có trạng thái `pending`. Thao tác thêm MUST không nhận trạng thái. MUST không có cách chọn trạng thái khác `pending` lúc thêm.
- **FR-004**: Tiêu đề MUST được chuẩn hóa và được chấp nhận hay từ chối theo đúng luật tiêu đề việc con đã chốt khi tạo kế hoạch ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Hệ thống MUST không đặt thêm luật tiêu đề nào cho thao tác này. Tiêu đề lưu và tiêu đề trả về MUST là dạng đã chuẩn hóa.
- **FR-005**: Thêm thành công MUST trả về kế hoạch sau khi thêm, cùng các phần thông tin với kết quả mở một kế hoạch. Việc con mới MUST đứng cuối, với danh tính vừa cấp, tiêu đề đã chuẩn hóa, và trạng thái `pending`.
- **FR-006**: Ngay sau một lần thêm thành công, mở kế hoạch đó và liệt kê kế hoạch đang hoạt động MUST thấy việc con mới với cùng danh tính, cùng tiêu đề, trạng thái `pending`, đứng cuối. Vị trí của kế hoạch trong danh sách không lọc MUST giữ nguyên.
- **FR-007**: Hệ thống MUST từ chối khi danh tính kế hoạch thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau khi bỏ khoảng trắng đầu và cuối, bằng đúng câu `Danh tính kế hoạch chưa được đưa.` Câu này là câu đã dùng khi cập nhật việc con. Kiểm tra này MUST đứng trước khi tra kế hoạch.
- **FR-008**: Hệ thống MUST từ chối khi tiêu đề thiếu, rỗng, hoặc chỉ gồm khoảng trắng sau khi chuẩn hóa theo FR-004, bằng đúng câu `Việc con không được để trống.` Câu này là câu tạo kế hoạch đang dùng cho việc con rỗng hoặc chỉ gồm khoảng trắng. Kiểm tra này MUST đứng sau FR-007 và trước khi tra kế hoạch. MUST không ghi gì.
- **FR-009**: Hệ thống MUST từ chối khi danh tính kế hoạch còn nội dung nhưng không trùng kế hoạch nào đã lưu, bằng đúng câu `Không có kế hoạch với danh tính này.` Cách so danh tính MUST giống cách đã chốt ở [spec cập nhật việc con](../003-update-subtask/spec.md). Kiểm tra này MUST đứng sau FR-007 và FR-008.
- **FR-010**: Khi nhiều điều kiện từ chối cùng xảy ra, hệ thống MUST trả đúng một câu, theo thứ tự FR-007, FR-008, rồi FR-009. Đầu vào MUST được kiểm hết trước khi tra kế hoạch.
- **FR-011**: Mọi lời từ chối MUST là đúng câu của tình huống đó và MUST kết thúc yêu cầu thêm. MUST không kèm chi tiết kỹ thuật bên trong. Dữ liệu đã lưu MUST giữ nguyên. Lần liệt kê, lần mở, và lần thêm sau bằng dữ liệu đúng MUST vẫn làm được.
- **FR-012**: Hành vi tạo kế hoạch, liệt kê kế hoạch, mở một kế hoạch, và cập nhật trạng thái việc con đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec xem chi tiết](../002-get-plan-detail/spec.md), và [spec cập nhật việc con](../003-update-subtask/spec.md) MUST giữ nguyên, trừ việc một lần thêm thành công hiện ra ở lần liệt kê và lần mở ngay sau đó. Ngoại lệ: tạo kế hoạch với một phần tử tiêu đề việc con là None giờ bị từ chối bằng câu `Việc con không được để trống.` thay vì lỗi kỹ thuật, vì tạo kế hoạch và thêm việc con dùng chung một luật dựng việc con.

### Key Entities *(include if feature involves data)*

- **Kế hoạch**: Đúng thực thể ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này không thêm thuộc tính cho chính kế hoạch và không đổi nghĩa "đang hoạt động".
- **Việc con**: Đúng thực thể ở [spec cập nhật việc con](../003-update-subtask/spec.md): thuộc về đúng một kế hoạch, có danh tính riêng, phần tiêu đề tên `title`, và trạng thái `pending` hoặc `done`. Việc con thêm bằng tính năng này là cùng loại việc con với việc con tạo cùng kế hoạch. Vị trí cuối danh sách không phải danh tính.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với một kế hoạch đang có N việc con, 100% lần thêm hợp lệ làm kế hoạch đó có N+1 việc con. Việc mới đứng cuối. N việc cũ giữ nguyên danh tính, tiêu đề, và trạng thái.
- **SC-002**: 100% việc con vừa thêm có danh tính riêng và trạng thái `pending` trong kết quả thêm, trong lần mở kế hoạch ngay sau đó, và trong lần liệt kê ngay sau đó.
- **SC-003**: 100% lần thêm hợp lệ trả về cùng một kế hoạch với lần mở ngay sau đó: cùng danh tính kế hoạch, cùng mục tiêu, cùng từng việc con theo cùng thứ tự.
- **SC-004**: 100% lần thêm với danh tính kế hoạch thiếu, rỗng, chỉ khoảng trắng, hoặc không trùng kế hoạch nào bị từ chối bằng đúng câu của tình huống đó trong cập nhật việc con. Số việc con không đổi sau mỗi lời từ chối.
- **SC-005**: 100% lần thêm với tiêu đề không hợp lệ bị từ chối bằng đúng câu tạo kế hoạch đang dùng cho việc con trống. 0 lần tiêu đề không hợp lệ làm tăng số việc con, kể cả khi danh tính kế hoạch không trùng kế hoạch nào.
- **SC-006**: Khi một yêu cầu vừa thiếu danh tính kế hoạch vừa có tiêu đề không hợp lệ, 100% lời từ chối là câu danh tính kế hoạch chưa được đưa. Khi danh tính kế hoạch còn nội dung, tiêu đề không hợp lệ, và không có kế hoạch đó, 100% lời từ chối là câu việc con không được để trống.

## Assumptions

- Người dùng của sản phẩm là một người, như [docs/PRODUCT.md](../../docs/PRODUCT.md) §2. Thêm việc con nằm trong toàn bộ kế hoạch đang hoạt động của người đó; không có chia sẻ hay phân quyền.
- "Đang hoạt động" giữ nghĩa ở [spec tạo và liệt kê](../001-create-list-plans/spec.md). Tính năng này không có thao tác hoàn thành, cất đi, hay xóa kế hoạch. Thêm một việc `pending` không đổi chỗ của kế hoạch trong danh sách không lọc, vì đây không phải tạo kế hoạch mới.
- Danh tính việc con mới do hệ thống cấp lúc thêm, cùng cách với lúc tạo kế hoạch, không do người gọi chọn, và không suy ra từ vị trí hay từ tiêu đề.
- Tiêu đề thiếu được từ chối bằng cùng câu với tiêu đề rỗng. Tạo kế hoạch cũng dùng một câu cho mục tiêu thiếu và mục tiêu rỗng. Đây không phải luật nội dung mới.
- Câu từ chối khi danh tính kế hoạch không dùng được là đúng hai câu đã dùng khi cập nhật việc con: `Danh tính kế hoạch chưa được đưa.` và `Không có kế hoạch với danh tính này.`
- Câu từ chối khi tiêu đề không hợp lệ là đúng câu tạo kế hoạch đang dùng cho việc con rỗng hoặc chỉ gồm khoảng trắng: `Việc con không được để trống.` Không có câu riêng cho tính năng này.
- Kết quả thêm dùng cùng các phần thông tin với kết quả mở một kế hoạch, vì người gọi đọc một kế hoạch theo một kiểu.
- Việc con vừa thêm là việc con bình thường. Đổi trạng thái của nó sau đó thuộc [spec cập nhật việc con](../003-update-subtask/spec.md), không thuộc tính năng này.
- Nơi lưu lâu dài của sản phẩm đã chốt ở constitution (nguyên tắc VI) và F03 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). Tính năng này không dựng kho đó và không nối tới kho đang chạy. Đúng sai của việc thêm phải quan sát được trước khi kho đó tồn tại.
- Dòng F08 trong [docs/PRODUCT.md](../../docs/PRODUCT.md) giữ nguyên. Tính năng này không sửa file đó.
- Ngoài phạm vi, theo mô tả tính năng:
  - Chèn việc con vào một vị trí bất kỳ, sắp xếp lại, xóa, hay sửa tiêu đề việc con (F09 hoặc lát sau).
  - Thêm nhiều việc con trong một lần gọi.
  - Chọn hoặc đổi trạng thái việc con lúc thêm (F07).
  - Hội thoại hỏi lại trước khi chốt kế hoạch (F01, F02).
  - Việc quyết định lúc nào gọi thêm, tạo, liệt kê, mở, hoặc cập nhật.
  - Xem lại và điều chỉnh cả kế hoạch (F09).
  - Đường nhận yêu cầu qua HTTP và qua Telegram (F11, F14).
  - Nhắc việc chủ động, đồng bộ ra ngoài, và các tính năng từ F10 trở đi.
  - Dựng hoặc kết nối kho dữ liệu thật.
