# Feature Specification: Ngày, ưu tiên và sức của kế hoạch

**Feature Branch**: `015-plan-dates-priority`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "F17 mở rộng (D-024 mục 1, 3, 5, 9, 11): kế hoạch và việc con có chỗ lưu ngày, ưu tiên, sức và lịch sử dời việc, và mô hình có đồng hồ. Trong phạm vi: mỗi lượt mô hình biết ngày hôm nay, thứ và múi giờ Europe/Helsinki; ngày dự kiến của việc con là ngày lịch, không giờ, không bắt buộc, và bot đặt ngày vào trường đó thay vì vào tiêu đề; ưu tiên của kế hoạch có ba mức cao, vừa, thấp, độ gấp do code tính từ hạn và không lưu; sức việc con S, M, L tương ứng 1, 3, 6 giờ, không bắt buộc, số giờ ở một chỗ cấu hình, vòng này chỉ lưu sức; lịch sử dời việc chỉ thêm không sửa, mỗi dòng ghi việc nào, từ ngày nào sang ngày nào, lý do, thời điểm, và dòng chỉ sinh khi một việc đổi từ một ngày sang một ngày khác; dữ liệu đang có không mất, mọi trường mới cho phép trống; bộ câu eval phiên bản 2 với hai hành vi Starter (hạn tương đối thành ngày tuyệt đối; xin thêm một ngày trong khi một kế hoạch khác đến hạn ngay hôm sau), cộng tin dài có ngày và giờ để giữ luật goal của lời hướng dẫn phiên bản 3, và các ca Q2-14; lời hướng dẫn hệ thống lên 4, định nghĩa tool lên 3. Ràng buộc: truy cập kho theo constitution III, lời gọi ghi trả giá trị theo D-023, khóa lạc quan theo D-021 giữ nguyên, không có khái niệm người dùng trong kho theo D-022, trạng thái ở kho bền. Ngoài phạm vi: việc hằng ngày, sự kiện đột xuất, quét tải, xếp lại lịch, form và Mini App, /today, nhắc theo giờ, voice. Mười câu ở mục cuối không được chọn ở bước specify."

## Clarifications

### Session 2026-11-09

- Q: Trong vòng này, cột "xong khi" của việc con và tên kế hoạch tách khỏi goal có được lưu cùng ngày, ưu tiên và sức không, hay cả hai để vòng form? → A: Cả "xong khi" và tên tách khỏi goal để vòng form. Vòng này không thêm hai trường đó. Goal tiếp tục là tên duy nhất của kế hoạch.
- Q: Trong vòng này, việc con có ưu tiên riêng không, và nếu có thì mức trống trên việc con nghĩa là gì? → A: Chỉ ưu tiên ở kế hoạch. Việc con không có ưu tiên riêng. Phần việc con sửa riêng ưu tiên (D-024 mục 3) dời sang vòng quét tải, là nơi đầu tiên cần nó. Chưa mở rộng sang F17.
- Q: Hạn của kế hoạch được lưu thành một ngày riêng trên kế hoạch, hay là ngày dự kiến muộn nhất trong các việc con? → A: Không có cột hạn. Hạn của kế hoạch là ngày dự kiến muộn nhất của việc chưa làm có ngày. Không việc chưa làm nào có ngày thì kế hoạch không có hạn. Việc đã xong và việc bỏ qua không tính. Khi chủ bot nêu hạn cho cả kế hoạch, bot đặt hạn đó làm ngày của việc con chưa làm cuối cùng. Bộ eval phiên bản 2 đo việc này.
- Q: Khi chủ bot xin dời một hạn thêm một ngày mà hôm sau đã có việc, vòng này có tìm trùng và chờ xác nhận trước khi ghi không, hay phần đó để vòng quét tải? → A: Tìm trùng trong vòng này, chỉ trên tool dời ngày. Trùng nghĩa là hạn của kế hoạch đang dời, tính theo FR-005 sau lần dời, bằng hạn của một kế hoạch khác. Kế hoạch đang xin dời không tính. Lần dời không đổi hạn của chính kế hoạch đó thì không cần xác nhận vì trùng. Bot báo trùng và chỉ ghi sau khi chủ bot xác nhận. Dời hạn thêm một ngày nghĩa là dời thêm một ngày các việc chưa làm đang mang đúng ngày hạn; việc có ngày sớm hơn giữ nguyên. Lý do của dòng dời được phép trống; bot ghi lý do khi chủ bot đã nói. Vòng này chỉ so ngày với ngày, không cộng giờ. Cộng giờ và quỹ 8 giờ để vòng quét tải.
- Q: Lúc tạo kế hoạch và lúc thêm việc, ngày và sức đi vào tool tạo nào, và sau khi đã tạo thì ưu tiên, sức và đổi ngày đi qua tool nào? → A: `create_plan` nhận ưu tiên của kế hoạch, và với mỗi việc nhận ngày cùng sức, tất cả không bắt buộc. `add_subtask` nhận ngày và sức, không bắt buộc. Hai tool này đặt ngày và không kiểm trùng. Sau khi tạo có ba tool, mỗi tool một việc: đặt ưu tiên của kế hoạch; đặt sức của một việc; dời ngày. Tool dời ngày nhận một kế hoạch, một danh sách các việc kèm ngày mới hoặc trống, lý do tùy chọn và cờ xác nhận. Một lần gọi là một lần ghi. Mỗi việc đổi từ một ngày sang một ngày khác có một dòng lịch sử trong cùng lần ghi. Lần gọi đầu của tool dời ngày thấy trùng thì trả thông tin trùng và không ghi. Chỉ ghi khi gọi lại với cờ xác nhận sau khi chủ bot đồng ý. Cờ không chứng minh sự đồng ý của chủ bot. Bộ eval phiên bản 2 chấm ca trùng theo kho: lần gọi đầu không có cờ, và kho không đổi trước khi chủ bot trả lời.
- Q: Dòng lịch sử dời việc sinh ra khi nào? → A: Chỉ khi một việc đổi từ một ngày sang một ngày khác. Lần đặt ngày đầu, từ trống sang một ngày, và lần bỏ ngày, từ một ngày sang trống, vẫn là một lần ghi qua tool dời ngày và vẫn qua khóa lạc quan, nhưng không sinh dòng lịch sử. Ngày đi và ngày đến của một dòng lịch sử luôn có ngày.
- Q: Trùng được xét trên cái gì? → A: Chỉ khi hạn của kế hoạch đang dời, tính theo FR-005 sau lần dời, bằng hạn của một kế hoạch khác. Lần dời không làm đổi hạn của chính kế hoạch đó không cần xác nhận vì trùng.
- Q: Kiểm trùng áp cho lần ghi nào? → A: Chỉ tool dời ngày. `create_plan` và `add_subtask` đặt ngày không kiểm trùng. Kiểm trùng lúc tạo kế hoạch hoặc thêm việc thuộc vòng quét tải.
- Q: Sau khi ngày nằm ở trường ngày, tin digest và lệnh `/next` có in ngày không, có đổi thứ tự đoạn không, và hợp đồng chữ của spec 014 có được sửa trong vòng này không? → A: In ngày của việc chưa làm đầu tiên, cuối dòng tiêu đề, đúng dạng `(thứ Sáu 06/11)`. Tên thứ tiếng Việt và ngày do code dựng từ trường ngày, không do mô hình. Quy tắc dựng không nhận thời điểm hiện tại. Việc không có ngày thì không có đoạn ngày. Không đánh dấu quá hạn. Thứ tự đoạn giữ nguyên, kế hoạch cũ nhất trước. `/next` dùng chung quy tắc dựng với digest. Vòng này sửa `specs/014-morning-digest/spec.md`, `specs/014-morning-digest/contracts/digest-text.md`, và `tests/test_morning_text.py`.
- Q: "Cuối tuần này", "tuần sau", và tên một thứ khi hôm nay đúng là thứ đó thì thành ngày nào, và bot nói ngày đã chọn hay hỏi lại? → A: Tuần lịch là thứ Hai đến Chủ nhật theo ngày Helsinki. "Cuối tuần này" là Chủ nhật của tuần chứa hôm nay. Hôm nay là Chủ nhật thì ngày đó là hôm nay. Bot lưu ngày đó và nói ngày đã chọn. Tên một thứ trong ngày chính là thứ đó: bot hỏi lại, kho không đổi. "Tuần sau" không kèm thứ: bot hỏi lại, kho không đổi. Tên một thứ vào ngày khác, khi câu không kèm "tuần sau", là lần tới của thứ đó. Bot lưu ngày đó và nói ngày đã chọn. "Thứ X tuần sau" là thứ X của tuần lịch kế tiếp. Tình huống 1 của User Story 8 gồm ba ca: "cuối tuần này" chấm theo ngày tuyệt đối, là Chủ nhật của tuần chứa hôm nay; tên một thứ trong ngày chính là thứ đó chấm theo việc bot hỏi lại và kho không đổi; "tuần sau" không kèm thứ chấm theo việc bot hỏi lại và kho không đổi.
- Q: "Thứ X tuần sau", câu có cả tên thứ lẫn tuần, là ngày nào? → A: Thứ X của tuần lịch kế tiếp. Tuần lịch là thứ Hai đến Chủ nhật theo ngày Helsinki. Bot lưu ngày đó và nói ngày đã chọn.
- Q: Kế hoạch đã có mà ngày đang nằm trong tiêu đề thì để nguyên hay chuyển vào trường ngày? → A: Để nguyên tiêu đề từng chữ. Trường ngày của những việc đó để trống. Không có bước chuyển.
- Q: Bộ câu eval phiên bản 2, bộ chạy, bộ chấm và đồng hồ cố định nằm trong spec 015 hay để vòng riêng? → A: Nằm trong spec 015. Mỗi ca của bộ câu phiên bản 2 mang mốc đồng hồ cố định của ca đó, vì các ca hạn tương đối cần hôm nay là những thứ khác nhau. Chạy cả bộ phiên bản 1 với lời hướng dẫn bản 4 để đo hồi quy và việc chọn tool trong chín tool. Cách chấm ca phiên bản 1 giữ nguyên để so với p3-d2. Bộ chấm lên phiên bản 2: đọc thêm ngày, sức, ưu tiên và dòng lịch sử trong kho, và chấm kho không đổi sau lần gọi đầu của ca trùng hạn. Seed của ca trùng có sẵn một kế hoạch khác với hạn đã biết. Một lần chạy mỗi bộ, ghi file kết quả vào `evals/results/`.
- Q: Ba tình huống Q2-14 đạt khi nào và trượt khi nào? → A: Không chấm cùng một kiểu. Liệt kê tiêu đề trong một câu thì chấm: đạt khi mỗi tiêu đề được lưu đúng từng chữ theo luật giữ nguyên tiêu đề ở PRODUCT §9, viết lại tiêu đề là trượt. Câu "học xong bảng chữ cái" chấm với seed hai việc tách riêng, Hiragana và Katakana: câu khớp nhiều việc hoặc không khớp, đạt khi bot hỏi lại và kho không đổi, đánh dấu xong một hoặc cả hai việc mà không hỏi là trượt. Kho chỉ có một việc gộp "Hiragana và Katakana" thì không chấm đạt hay trượt, chỉ ghi nhận trong báo cáo eval, vì luật hiện có cho phép cập nhật khi khớp đúng một việc. Câu sửa lời sau khi đánh dấu nhầm chỉ ghi nhận hành vi trong báo cáo eval, không chấm đạt hay trượt, vì chưa có hành vi nào được chốt.

## User Scenarios & Testing *(mandatory)*

Chủ bot nói hạn bằng lời tương đối ("cuối tuần này", "thứ Sáu") và bot cần ra một ngày lịch đúng theo hôm nay ở Helsinki. Hiện bot nhét ngày vào cuối tiêu đề việc con, nên không có chỗ để lọc, sắp hay cộng theo ngày. Lời hướng dẫn đang là một hằng, và một lượt không nhận ngày hôm nay, thứ hay múi giờ.

Vòng này là mục 3 trong thứ tự [docs/PRODUCT.md](../../docs/PRODUCT.md) §7: F17 mở rộng theo [D-024](../../docs/DECISIONS.md) mục 1, 3, 5, 9 và 11. Luật goal ngắn đã chốt ở §9: goal là tên ngắn, dưới 80 ký tự; hạn chót, ngày bắt đầu và số giờ mỗi ngày không nằm trong goal. Ngày có cấu trúc là việc của vòng này.

Các câu còn ở mục [Câu hỏi dành cho /speckit-clarify](#câu-hỏi-dành-cho-speckit-clarify) chưa có đáp án, trừ câu 1 đã để `/speckit-plan` quyết. Câu 2, 3, 4, 5, 6, 7, 8, 9, 10 và 11 đã chốt ở Clarifications. Scenario và yêu cầu bên dưới không suy ra đáp án cho các câu còn lại. Digest và `/next` in ngày của việc chưa làm đầu tiên theo FR-016.

### User Story 1 - Mỗi lượt mô hình biết hôm nay ở Helsinki (Priority: P1)

Mỗi lần mô hình được gọi trong một lượt, mô hình biết ba việc của cùng một mốc: ngày lịch hôm nay, thứ của ngày đó, và múi giờ Europe/Helsinki. Ba việc này đúng cả khi Helsinki đổi giờ mùa. Nhờ đó một hạn nói tương đối có thể thành một ngày tuyệt đối. Cách đưa ba việc này vào lượt, và mô-đun đồng hồ nào phát chúng, để `/speckit-plan` quyết. Tuần lịch là thứ Hai đến Chủ nhật theo ngày Helsinki của mốc đầu lượt. "Cuối tuần này" là Chủ nhật của tuần chứa hôm nay. Tên một thứ trong đúng ngày đó, và "tuần sau" không kèm thứ, thì bot hỏi lại và kho không đổi. Tên một thứ vào ngày khác, khi câu không kèm "tuần sau", là lần tới của thứ đó. "Thứ X tuần sau" là thứ X của tuần lịch kế tiếp. Bot nói ngày khi đã chọn và lưu.

**Why this priority**: Không có hôm nay thì mọi ngày tương đối đều đoán. [D-024](../../docs/DECISIONS.md) mục 11 đặt đồng hồ Helsinki trước mọi hành vi về ngày. [Spec 014](../014-morning-digest/spec.md) đã để phần đưa ngày cho mô hình sang vòng này và không đổi số phiên bản lời hướng dẫn ở F10.

**Independent Test**: Chọn một mốc đã biết, gồm một ngày giờ mùa đông và một ngày giờ mùa hè. Chạy một lượt có ít nhất hai lần gọi mô hình. Đọc phần mô hình nhận ở mỗi lần gọi. Không cần ghi kế hoạch.

**Acceptance Scenarios**:

1. **Given** một mốc ở giờ mùa đông Helsinki, **When** một lượt gọi mô hình, **Then** lần gọi đó nhận ngày lịch Helsinki của mốc đó, thứ của ngày đó, và múi giờ Europe/Helsinki.
2. **Given** một mốc ở giờ mùa hè Helsinki, **When** một lượt gọi mô hình, **Then** ngày, thứ và múi giờ vẫn là của đồng hồ Helsinki, không phải của UTC.
3. **Given** một lượt có hai lần gọi mô hình, **When** đọc cả hai lần, **Then** cả hai thấy cùng ngày, cùng thứ và cùng múi giờ của mốc đầu lượt.

---

### User Story 2 - Ngày dự kiến nằm ở việc con, không nằm trong tiêu đề (Priority: P1)

Mỗi việc con có một ngày dự kiến. Đó là một ngày lịch, không có giờ. Trường này được phép trống. Khi chủ bot đưa một ngày cho một việc, ngày đó được lưu ở trường này. Tiêu đề việc con không được thêm đoạn ngày. Goal không nhận hạn chót, ngày bắt đầu hay số giờ mỗi ngày, đúng luật đã có ở lời hướng dẫn phiên bản 3.

Lúc tạo, `create_plan` nhận ưu tiên của kế hoạch và, với mỗi việc, ngày cùng sức. `add_subtask` nhận ngày và sức. Cả ngày, sức và ưu tiên đều không bắt buộc. Sau khi tạo, ba tool mỗi tool một việc: đặt ưu tiên của kế hoạch, đặt sức của một việc, và dời ngày. Việc đã có mà tiêu đề đang chứa đoạn ngày thì tiêu đề giữ nguyên từng chữ và trường ngày để trống. Không có bước chuyển đoạn ngày đó vào trường ngày.

**Why this priority**: Đây là phần F17 trong [docs/PRODUCT.md](../../docs/PRODUCT.md) §3. Không có trường này thì ngày tiếp tục là chữ trong tiêu đề.

**Independent Test**: Tạo một việc không đưa ngày, rồi tạo hoặc sửa một việc có một ngày lịch. Đọc tiêu đề, goal và trường ngày. Không cần ưu tiên hay sức.

**Acceptance Scenarios**:

1. **Given** một việc con mới không kèm ngày, **When** việc được lưu, **Then** việc có trong kế hoạch, tiêu đề là tên việc, và ngày dự kiến trống.
2. **Given** chủ bot đưa một ngày lịch cho một việc, **When** việc được lưu, **Then** trường ngày dự kiến là đúng ngày lịch đó và không có giờ. Tiêu đề không chứa đoạn ngày. Goal không chứa hạn chót, ngày bắt đầu hay số giờ mỗi ngày.
3. **Given** một việc đã lưu mà tiêu đề đang có đoạn ngày từ trước, **When** chỉ bổ sung các trường mới, **Then** tiêu đề giữ nguyên từng chữ và ngày dự kiến của việc đó trống.

---

### User Story 3 - Ưu tiên của kế hoạch, độ gấp không được lưu (Priority: P1)

Mỗi kế hoạch có một ưu tiên: cao, vừa, hoặc thấp. Trường này được phép trống. Không có mức thứ tư. Độ gấp không phải một trường lưu. Kế hoạch không có cột hạn. Hạn của kế hoạch là ngày dự kiến muộn nhất trong các việc chưa làm có ngày. Không việc chưa làm nào có ngày thì kế hoạch không có hạn. Việc đã xong và việc bỏ qua không tính. Khi chủ bot nêu hạn cho cả kế hoạch, bot đặt ngày đó làm ngày dự kiến của việc con chưa làm cuối cùng, và bộ eval phiên bản 2 đo việc đặt này. Vòng này không yêu cầu tính hay hiện độ gấp, vì quét tải nằm ngoài phạm vi. Việc con không có ưu tiên riêng. Phần việc con sửa riêng ưu tiên ở D-024 mục 3 dời sang vòng quét tải, là nơi đầu tiên cần nó, và chưa mở rộng sang F17.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 3 đặt ưu tiên ở kế hoạch vì ưu tiên thuộc về mục tiêu, và cấm lưu độ gấp.

**Independent Test**: Lưu ba kế hoạch với ưu tiên cao, vừa và thấp, và một kế hoạch không đưa ưu tiên. Đọc lại. Không cần ngày.

**Acceptance Scenarios**:

1. **Given** một kế hoạch mới, **When** ưu tiên được đặt là cao, vừa, hoặc thấp, **Then** đọc lại thấy đúng mức đó.
2. **Given** một kế hoạch mới không kèm ưu tiên, **When** kế hoạch được lưu, **Then** ưu tiên trống và kế hoạch vẫn hợp lệ.
3. **Given** một kế hoạch đã lưu, **When** đọc các trường đã lưu, **Then** không có trường độ gấp và không có cột hạn.
4. **Given** một kế hoạch đã có ưu tiên và có việc con, **When** đọc việc con, **Then** việc con không có ưu tiên riêng. Mức của kế hoạch không được chép thành một trường trên việc con.
5. **Given** một kế hoạch có vài việc chưa làm, **When** chủ bot nêu một hạn cho cả kế hoạch, **Then** ngày đó nằm ở ngày dự kiến của việc chưa làm đứng cuối trong thứ tự đã lưu. Goal không chứa hạn. Tiêu đề việc không chứa đoạn ngày. Kế hoạch không có cột hạn.

---

### User Story 4 - Sức của việc con được lưu, chưa cộng giờ (Priority: P2)

Mỗi việc con có một sức: S, M, hoặc L. Trường này được phép trống. S tương ứng 1 giờ, M tương ứng 3 giờ, L tương ứng 6 giờ. Ba số giờ nằm ở một chỗ cấu hình. Vòng này chỉ lưu chữ S, M hoặc L. Vòng này không cộng giờ, không cảnh báo vượt quỹ giờ, và không ghi chữ "tính tạm".

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 5 cần dữ liệu sức từ sớm. Phần cộng giờ và câu "tính tạm" thuộc quét tải, ngoài phạm vi vòng này.

**Independent Test**: Lưu một việc với S, một việc với M, một việc với L, và một việc không có sức. Đọc lại chữ sức và đọc chỗ cấu hình ba số giờ. Không chạy phép cộng.

**Acceptance Scenarios**:

1. **Given** một việc con, **When** sức được đặt là S, M, hoặc L, **Then** đọc lại thấy đúng chữ đó.
2. **Given** một việc con không kèm sức, **When** việc được lưu, **Then** sức trống và việc vẫn hợp lệ.
3. **Given** chỗ cấu hình, **When** đọc ba mức, **Then** S là 1 giờ, M là 3 giờ, L là 6 giờ.
4. **Given** vài việc đã có ngày và sức, **When** chúng được lưu trong vòng này, **Then** không có tổng giờ và không có cảnh báo vượt quỹ giờ.

---

### User Story 5 - Đổi ngày và lịch sử dời là một lần ghi (Priority: P1)

Lịch sử dời việc chỉ thêm dòng mới. Dòng đã có không bị sửa và không bị xóa. Dòng chỉ sinh khi một việc đổi từ một ngày sang một ngày khác. Mỗi dòng ghi việc nào, từ ngày nào, sang ngày nào, chỗ cho lý do, và thời điểm của lần dời. Ngày đi và ngày đến đều là một ngày lịch. Thời điểm là mốc giờ của lần ghi, khác với hai ngày lịch.

Một lần gọi tool dời ngày là một lần ghi, gồm cả lần đặt ngày đầu và lần bỏ ngày. Mỗi việc đổi từ một ngày sang một ngày khác trong lần gọi có đúng một dòng lịch sử. Việc đi từ trống sang một ngày, hoặc từ một ngày sang trống, đổi ngày đã lưu và không có dòng. Cả lần gọi cùng được lưu hoặc cùng không được lưu. Khóa lạc quan theo [D-021](../../docs/DECISIONS.md) giữ nguyên: bản cũ hơn không ghi đè; khi bị từ chối, mọi ngày trong lần gọi giữ nguyên và không có dòng lịch sử mới của lần gọi đó.

Lý do được phép trống. Khi chủ bot đã nói lý do, dòng dời ghi lý do đó. Dời hạn thêm một ngày chỉ dời các việc chưa làm đang mang đúng ngày hạn; việc chưa làm có ngày sớm hơn giữ nguyên. Việc đã xong và việc bỏ qua giữ nguyên. Trùng chỉ khi hạn của kế hoạch đang dời, tính theo FR-005 sau lần dời, bằng hạn của một kế hoạch khác. Kế hoạch đang xin dời không tính. Lần dời không đổi hạn của chính kế hoạch đó thì ghi ngay, không hỏi xác nhận vì trùng. Lần gọi đầu thấy trùng thì trả thông tin trùng và không ghi. Lần gọi đó không có cờ xác nhận. Chỉ lần gọi sau, có cờ, mới ghi, sau khi chủ bot đồng ý. Cờ không chứng minh sự đồng ý. Vòng này chỉ so ngày với ngày. Cộng giờ và quỹ 8 giờ để vòng quét tải.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 9 đòi bảng chỉ thêm, ghi trước khi có xếp lịch. Đổi từ ngày này sang ngày khác mà không có dòng, hoặc có dòng khi ngày đi hay ngày đến trống, làm lịch sử không còn là sự thật.

**Independent Test**: Đặt ngày một việc đang trống, rồi đổi sang một ngày khác, rồi bỏ ngày, rồi thử một lần ghi với bản kế hoạch đã cũ. Đếm dòng lịch sử và đọc ngày sau mỗi lần. Không cần quét tải.

**Acceptance Scenarios**:

1. **Given** một việc chưa có ngày dự kiến, **When** lần ghi qua tool dời ngày đặt một ngày lịch thành công, **Then** việc mang ngày đó và số dòng lịch sử không tăng.
2. **Given** một việc đang có ngày A, **When** lần ghi qua tool dời ngày bỏ ngày đó thành công, **Then** ngày dự kiến trống và số dòng lịch sử không tăng.
3. **Given** một việc đang có ngày A, **When** lần ghi đổi sang ngày B khác A và thành công, **Then** việc mang ngày B, dòng lịch sử cũ còn nguyên, và có đúng một dòng mới từ A sang B. Ngày đi và ngày đến của dòng đó đều có ngày.
4. **Given** một lần ghi bị từ chối vì bản kế hoạch đã cũ, **When** đọc lại, **Then** ngày dự kiến vẫn là ngày trước lần ghi đó và số dòng lịch sử không tăng.
5. **Given** đã có vài dòng lịch sử, **When** một lần dời sau thành công, **Then** các dòng cũ giữ nguyên việc, ngày đi, ngày đến, lý do và thời điểm.
6. **Given** một lần đổi từ ngày A sang ngày B khác A và chủ bot không nói lý do, **When** lần ghi thành công, **Then** dòng lịch sử mới có lý do trống. **Given** chủ bot đã nói một lý do, **When** cùng lần ghi thành công, **Then** dòng ghi đúng lý do đó.
7. **Given** hạn của kế hoạch đang là ngày H, hai việc chưa làm mang ngày H và một việc chưa làm mang ngày sớm hơn, **When** chủ bot xin dời hạn thêm một ngày và hạn của kế hoạch sau lần dời không bằng hạn kế hoạch khác, **Then** hai việc đang mang H chuyển sang ngày hôm sau, việc có ngày sớm hơn giữ nguyên, và mỗi việc đổi từ H sang hôm sau có một dòng lịch sử.
8. **Given** hạn của kế hoạch sau lần dời, tính theo FR-005, bằng hạn của một kế hoạch khác, **When** tool dời ngày được gọi lần đầu và lần gọi không có cờ xác nhận, **Then** kết quả trả thông tin trùng và không ghi. Kho không đổi trước khi chủ bot trả lời. **When** chủ bot đã đồng ý và tool được gọi lại với cờ xác nhận, **Then** lần ghi đó lưu ngày mới. Mỗi việc đổi từ một ngày sang một ngày khác có một dòng lịch sử. Cờ không phải bằng chứng sự đồng ý. Bộ eval chấm ca này bằng trạng thái kho.
9. **Given** một lần dời không đổi hạn của chính kế hoạch đó, **When** tool dời ngày được gọi không có cờ xác nhận, **Then** lần ghi thành công. Không có bước trả thông tin trùng.

---

### User Story 6 - Dữ liệu đang có còn nguyên (Priority: P1)

Mọi kế hoạch và việc con đang có vẫn còn sau khi các trường mới xuất hiện. Goal, tiêu đề, trạng thái, ghi chú, thứ tự, thời điểm tạo việc con và thời điểm đổi trạng thái giữ nguyên. Mọi trường mới trên các dòng cũ để trống. Đổi ngày, ưu tiên, sức hoặc ghi chú không đổi thời điểm tạo. Thời điểm đổi trạng thái chỉ đổi khi trạng thái đổi.

**Why this priority**: Kho đang chạy thật. Thêm trường mà làm mất hoặc viết lại dòng cũ thì chủ bot mất kế hoạch đang dùng.

**Independent Test**: Ghi một kế hoạch với vài việc, đủ trạng thái và ghi chú, trước khi có trường mới. Thêm trường mới. Đọc lại từng chữ của goal, tiêu đề, trạng thái, ghi chú, và hai mốc thời gian cũ.

**Acceptance Scenarios**:

1. **Given** một kế hoạch đã có goal, việc con, trạng thái và ghi chú, **When** các trường mới được thêm vào kho, **Then** kế hoạch còn, từng việc còn, và các chữ cũ khớp từng ký tự.
2. **Given** một việc đã có thời điểm tạo và thời điểm đổi trạng thái, **When** ngày, sức hoặc ghi chú của việc đó đổi mà trạng thái không đổi, **Then** thời điểm tạo giữ nguyên và thời điểm đổi trạng thái giữ nguyên.
3. **Given** cùng việc đó, **When** trạng thái đổi, **Then** thời điểm đổi trạng thái đổi theo lần đổi trạng thái, và thời điểm tạo vẫn giữ nguyên.

---

### User Story 7 - Lời hướng dẫn phiên bản 4, định nghĩa tool phiên bản 3 (Priority: P2)

Lời hướng dẫn hệ thống lên số nguyên 4. Bộ định nghĩa tool lên số nguyên 3. Mỗi lần gọi mô hình đã kết thúc ghi hai số đó. Tập khóa của dòng nhật ký giữ nguyên như [spec lượt mô hình](../008-llm-tool-turn/spec.md).

Bản 4 giữ mọi luật đang có của bản 3, gồm các luật [spec 011](../011-prompt-version-2/spec.md) và luật goal ngắn ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §9. Bản 4 thêm một luật: ngày dự kiến đặt vào trường ngày của việc con, không viết vào tiêu đề. Luật này nói việc cần lưu. Chỗ nhận ngày, sức và ưu tiên là các tool đã chốt ở Clarifications.

Kiểm tra đang khóa nguyên văn lời hướng dẫn bản 3 được sửa trong cùng thay đổi, theo tiền lệ spec 011. Bộ test tự động không gọi mô hình thật.

**Why this priority**: Lần đo sau chỉ so được khi số phiên bản đổi cùng lúc với luật mới. Giữ số 3 trong khi chữ đã đổi sẽ trộn với lần đo cũ.

**Independent Test**: Đọc số phiên bản lời hướng dẫn và số phiên bản bộ định nghĩa. Chạy một lượt bằng client giả. Đọc dòng nhật ký của lần gọi đã kết thúc.

**Acceptance Scenarios**:

1. **Given** lời hướng dẫn bản 4, **When** đọc số phiên bản, **Then** số đó là số nguyên 4. Các luật bản 3 còn trong chữ, gồm goal là một dòng dưới 80 ký tự và lệnh không đưa hạn chót, ngày bắt đầu hay số giờ mỗi ngày vào goal.
2. **Given** cùng lời hướng dẫn, **When** đọc luật ngày, **Then** luật bảo đặt ngày vào trường ngày dự kiến của việc con và không viết ngày vào tiêu đề.
3. **Given** bộ định nghĩa tool, **When** đọc số phiên bản, **Then** số đó là số nguyên 3.
4. **Given** một lần gọi mô hình đã kết thúc, **When** đọc dòng nhật ký, **Then** số lời hướng dẫn là 4, số bộ định nghĩa là 3, và tập khóa của dòng không thêm không bớt.

---

### User Story 8 - Bộ câu eval phiên bản 2 nêu hành vi cần đo (Priority: P2)

Có một bộ câu đánh giá phiên bản 2. Bộ này gồm các tình huống sau. Mỗi ca của bộ này mang mốc đồng hồ cố định của chính ca đó. Spec này cũng chạy cả bộ câu phiên bản 1 với lời hướng dẫn bản 4. Cách chấm ca phiên bản 1 giữ nguyên. Tình huống 5 được chấm. Tình huống 6 được chấm với seed hai việc tách. Tình huống 7 chỉ được ghi nhận.

1. Hạn tương đối, gồm ba ca. "Cuối tuần này" chấm theo ngày tuyệt đối: Chủ nhật của tuần chứa hôm nay. Tên một thứ trong ngày chính là thứ đó: bot hỏi lại, kho không đổi. "Tuần sau" không kèm thứ: bot hỏi lại, kho không đổi.
2. Chủ bot xin dời hạn thêm một ngày, và hạn của kế hoạch sau lần dời bằng hạn của một kế hoạch khác. Lần gọi đầu của tool dời ngày không có cờ xác nhận, trả thông tin trùng, và kho không đổi trước khi chủ bot trả lời. Sau khi chủ bot đồng ý, lần gọi có cờ mới ghi. Cờ không được lấy làm bằng chứng sự đồng ý. Sau lần ghi, chỉ các việc chưa làm đang mang đúng ngày hạn dịch một ngày. Việc có ngày sớm hơn giữ nguyên. Không cộng giờ. Lần dời không đổi hạn của chính kế hoạch thì không hỏi xác nhận vì trùng.
3. Chủ bot nêu hạn cho cả kế hoạch. Ngày đó được lưu làm ngày dự kiến của việc con chưa làm cuối cùng. Kế hoạch không có cột hạn. Bộ câu đo đúng việc đặt này.
4. Một tin dài có cả ngày và giờ. Goal lưu ra là tên ngắn, dưới 80 ký tự, không chứa hạn chót, ngày bắt đầu hay số giờ mỗi ngày. Giờ trong câu không trở thành một giờ lưu trên việc. Nếu câu có một ngày cho việc, ngày đó nằm ở trường ngày dự kiến, không nằm trong tiêu đề.
5. Chủ bot liệt kê vài tiêu đề việc trong một câu. Ca này được chấm. Đạt khi mỗi tiêu đề được lưu đúng từng chữ, theo luật giữ nguyên tiêu đề ở PRODUCT §9. Viết lại tiêu đề là trượt.
6. Chủ bot nói "học xong bảng chữ cái". Ca được chấm có seed hai việc tách riêng, Hiragana và Katakana. Câu này khớp nhiều việc hoặc không khớp, nên theo luật khớp tên đang có, đạt khi bot hỏi lại và kho không đổi. Đánh dấu xong một hoặc cả hai việc mà không hỏi là trượt. Ca kho chỉ có một việc gộp "Hiragana và Katakana" không được chấm đạt hay trượt. Kết quả của ca đó được ghi trong báo cáo eval, vì luật hiện có cho phép cập nhật khi khớp đúng một việc.
7. Sau một lần đánh dấu nhầm, chủ bot sửa lời là chỉ xong một việc trong nhóm. Ca này chỉ ghi nhận hành vi trong báo cáo eval. Không chấm đạt hay trượt, vì chưa có hành vi nào được chốt.

**Why this priority**: [Q2-14](../../docs/reviews/2026-11-05-repo-review.md) còn mở và được chỉ vào bộ câu eval phiên bản 2. Hai hành vi hạn tương đối và gia hạn là yêu cầu của Starter cho vòng này. Không có bộ câu thì luật ngày và luật tiêu đề không có chỗ đo trên mô hình thật.

**Independent Test**: Đọc bộ câu phiên bản 2 và thấy đủ bảy tình huống. Tình huống 1 có đủ ba ca và chấm theo luật hạn tương đối đã chốt. Tình huống 2 chấm theo luật trùng. Tình huống 3 chấm chỗ đặt hạn. Tình huống 4 đối chiếu luật goal. Tình huống 5 chấm từng chữ tiêu đề. Tình huống 6 chấm seed Hiragana và Katakana tách riêng. Tình huống 7 và ca một việc gộp chỉ có mặt trong báo cáo, không có đạt hay trượt.

**Acceptance Scenarios**:

1. **Given** bộ câu phiên bản 2, **When** đọc danh sách tình huống, **Then** có đủ bảy tình huống ở trên. Bộ câu phiên bản 1 vẫn còn làm biên bản lần đo cũ.
2. **Given** tình huống chủ bot nêu hạn cho cả kế hoạch và kế hoạch còn ít nhất một việc chưa làm, **When** chấm kết quả lưu, **Then** ngày đó là ngày dự kiến của việc chưa làm đứng cuối. Kế hoạch không có cột hạn. Goal không chứa hạn. Tiêu đề không chứa đoạn ngày.
3. **Given** tình huống tin dài có ngày và giờ, **When** một lần chạy được chấm theo luật goal, **Then** goal là một dòng dưới 80 ký tự và không chứa hạn chót, ngày bắt đầu hay số giờ mỗi ngày. Tiêu đề việc không chứa đoạn ngày. Không có giờ trong ngày được lưu trên việc.
4. **Given** tình huống liệt kê vài tiêu đề trong một câu, **When** chấm, **Then** đạt nếu mỗi tiêu đề khớp từng chữ với lời chủ bot. Viết lại tiêu đề là trượt.
5. **Given** seed có hai việc tách riêng Hiragana và Katakana, **When** chủ bot nói "học xong bảng chữ cái" và ca được chấm, **Then** đạt khi bot hỏi lại và kho không đổi. Đánh dấu xong một hoặc cả hai việc mà không hỏi là trượt.
6. **Given** ba ca của tình huống hạn tương đối, **When** chấm, **Then** "cuối tuần này" lưu Chủ nhật của tuần chứa hôm nay. Tên một thứ trong ngày chính là thứ đó thì bot hỏi lại và kho không đổi. "Tuần sau" không kèm thứ thì bot hỏi lại và kho không đổi.
7. **Given** kho chỉ có một việc gộp "Hiragana và Katakana" và chủ bot nói "học xong bảng chữ cái", **When** đọc báo cáo eval, **Then** kết quả được ghi nhận và ca không có đạt hay trượt.
8. **Given** câu sửa lời sau khi đánh dấu nhầm, **When** đọc báo cáo eval, **Then** hành vi được ghi nhận và ca không có đạt hay trượt.

---

### Edge Cases

- Việc không có ngày, kế hoạch không có ưu tiên, và việc không có sức vẫn lưu được. Trống là giá trị hợp lệ của ba trường đó.
- Đặt lại đúng ngày đang có không sinh dòng lịch sử.
- Lần đầu đặt ngày cho việc đang trống, và lần bỏ ngày đang có, đều là một lần ghi qua tool dời ngày và đều qua khóa lạc quan. Cả hai không sinh dòng lịch sử. Ngày đi và ngày đến của một dòng lịch sử luôn có ngày.
- Một lần ghi đổi ngày của nhiều việc: mỗi việc đổi từ một ngày sang một ngày khác có đúng một dòng lịch sử. Việc đặt ngày lần đầu hoặc bỏ ngày trong cùng lần ghi đổi ngày đã lưu và không có dòng. Lần ghi không thành thì không việc nào trong lần đó đổi ngày và không có dòng mới nào của lần đó.
- Hai mốc cũ của việc con giữ nghĩa hiện tại. Thời điểm tạo không bị viết lại. Thời điểm đổi trạng thái không đổi khi chỉ ngày, sức, ưu tiên hoặc ghi chú đổi.
- Một lượt kéo qua nửa đêm Helsinki vẫn dùng ngày, thứ và múi giờ của mốc đầu lượt cho mọi lần gọi mô hình trong lượt đó.
- Tiêu đề cũ đang chứa đoạn ngày giữ nguyên từng chữ. Trường ngày của việc đó để trống. Không có bước đọc đoạn ngày trong tiêu đề để ghi vào trường ngày, và không có bước xóa đoạn ngày khỏi tiêu đề. Vì trường ngày trống, quy tắc dựng digest không thêm một đoạn ngày thứ hai.
- Tuần lịch là thứ Hai đến Chủ nhật theo ngày Helsinki. "Cuối tuần này" là Chủ nhật của tuần chứa hôm nay. Hôm nay là Chủ nhật thì ngày đó là hôm nay. Bot lưu ngày đó và nói ngày đã chọn. Tên một thứ trong ngày chính là thứ đó thì bot hỏi lại và kho không đổi. "Tuần sau" không kèm thứ thì bot hỏi lại và kho không đổi. Tên một thứ vào ngày khác, khi câu không kèm "tuần sau", là lần tới của thứ đó. Bot lưu ngày đó và nói ngày đã chọn. "Thứ X tuần sau", câu có cả thứ lẫn tuần, là thứ X của tuần lịch kế tiếp. Bot lưu ngày đó và nói ngày đã chọn.
- Kế hoạch không có cột hạn. Hạn của kế hoạch là ngày dự kiến muộn nhất trong các việc chưa làm có ngày. Việc đã xong, việc bỏ qua, và việc chưa làm không có ngày không tính. Không việc chưa làm nào có ngày thì kế hoạch không có hạn. Cùng định nghĩa này dùng cho phép tìm trùng.
- Khi chủ bot nêu hạn cho cả kế hoạch và còn ít nhất một việc chưa làm, ngày đó đặt lên việc chưa làm đứng cuối trong thứ tự đã lưu. Việc đã xong và việc bỏ qua không nhận ngày này. Khi việc đó đã lưu, lần đặt này đi qua tool dời ngày và qua khóa lạc quan. Dòng lịch sử chỉ sinh khi việc đó đổi từ một ngày sang một ngày khác. Ngày đặt trong `create_plan` hoặc `add_subtask` không đi qua tool dời ngày. Nếu một việc chưa làm khác đang có ngày muộn hơn, hạn suy ra vẫn là ngày muộn nhất trong các việc chưa làm có ngày.
- Khi không còn việc chưa làm, hoặc không việc chưa làm nào có ngày, kế hoạch không có hạn và không có cột hạn. Luật đặt hạn cho cả kế hoạch không có việc chưa làm để nhận ngày.
- Dời hạn thêm một ngày chỉ đổi các việc chưa làm đang mang đúng ngày hạn. Việc chưa làm có ngày sớm hơn, việc đã xong và việc bỏ qua giữ nguyên ngày.
- Trùng chỉ khi hạn của kế hoạch đang dời, tính theo FR-005 sau lần dời, bằng hạn của một kế hoạch khác. Hạn để so là ngày muộn nhất trong các việc chưa làm có ngày. Kế hoạch đang xin dời không tính. Lần dời không làm đổi hạn của chính kế hoạch đó không cần xác nhận vì trùng.
- Kiểm trùng chỉ áp cho tool dời ngày. `create_plan` và `add_subtask` đặt ngày không kiểm trùng. Kiểm trùng lúc tạo kế hoạch hoặc thêm việc thuộc vòng quét tải.
- Lần gọi đầu của tool dời ngày thấy trùng thì trả thông tin trùng và không ghi. Lần gọi đó không có cờ xác nhận. Kho không đổi trước khi chủ bot trả lời. Chỉ lần gọi sau, có cờ, mới ghi, và chỉ sau khi chủ bot đồng ý. Cờ không chứng minh sự đồng ý. Mỗi việc đổi từ một ngày sang một ngày khác trong lần ghi đó có một dòng lịch sử. Cả lần gọi là một lần ghi.
- Lý do của dòng dời được phép trống. Bot ghi lý do khi chủ bot đã nói.
- Vòng này so ngày với ngày. Cộng giờ và quỹ 8 giờ thuộc vòng quét tải.
- Digest và `/next` dùng một quy tắc dựng. Cuối dòng tiêu đề của việc chưa làm đầu tiên, nếu việc đó có ngày, code thêm một đoạn ngày dựng từ trường ngày, dạng `(thứ Sáu 06/11)`. Mô hình không viết đoạn đó. Quy tắc không nhận thời điểm hiện tại. Việc không có ngày thì không thêm đoạn ngày. Không có chữ quá hạn. Thứ tự đoạn vẫn là kế hoạch cũ nhất trước. Tiêu đề đã lưu giữ nguyên từng chữ.
- Việc con không có ưu tiên riêng. Phần sửa riêng ưu tiên của việc con (D-024 mục 3) thuộc vòng quét tải, nơi đầu tiên cần nó, và không thuộc F17 của vòng này.
- Vòng này không thêm trường "xong khi" trên việc con và không thêm tên kế hoạch tách khỏi goal. Hai trường đó để vòng form. Goal là tên duy nhất của kế hoạch.
- Mỗi ca của bộ câu phiên bản 2 mang một mốc đồng hồ cố định. Các ca hạn tương đối dùng những thứ khác nhau. Bộ câu phiên bản 1 không thêm mốc vào từng ca. Cách chấm ca phiên bản 1 giữ nguyên so với p3-d2. Một lần chạy mỗi bộ ghi một file kết quả trong `evals/results/`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Mỗi lần gọi mô hình trong một lượt MUST nhận ngày lịch hôm nay, thứ của ngày đó, và múi giờ Europe/Helsinki, cả khi Helsinki đổi giờ mùa. Ba việc MUST cùng mô tả một mốc, là mốc đầu lượt. Cách gắn ba việc này vào lượt để `/speckit-plan` quyết. Spec này không chọn cách đó.
- **FR-002**: Mỗi việc con MUST có một ngày dự kiến. Giá trị MUST là một ngày lịch không có giờ, hoặc trống. Trống MUST là hợp lệ.
- **FR-003**: Khi chủ bot đưa một ngày cho một việc, ngày đó MUST được lưu ở trường ngày dự kiến. Tiêu đề việc MUST NOT nhận thêm đoạn ngày. Goal MUST tiếp tục tuân luật phiên bản 3: một dòng dưới 80 ký tự, không chứa hạn chót, ngày bắt đầu hay số giờ mỗi ngày.
- **FR-004**: Mỗi kế hoạch MUST có một ưu tiên: cao, vừa, thấp, hoặc trống. Chỉ ba mức đó. Trống MUST là hợp lệ. Việc con MUST NOT có ưu tiên riêng trong vòng này. Phần việc con sửa riêng ưu tiên (D-024 mục 3) dời sang vòng quét tải, là nơi đầu tiên cần nó, và MUST NOT được mở rộng vào F17 của vòng này.
- **FR-005**: Độ gấp MUST NOT được lưu thành trường. Spec này MUST NOT yêu cầu tính hay hiện độ gấp. Kế hoạch MUST NOT có cột hạn. Hạn của kế hoạch MUST là ngày dự kiến muộn nhất trong các việc chưa làm có ngày. Việc đã xong và việc bỏ qua MUST NOT tính vào hạn đó. Việc chưa làm không có ngày MUST NOT tính vào hạn đó. Khi không việc chưa làm nào có ngày, kế hoạch MUST NOT có hạn. Phép tìm trùng MUST dùng cùng định nghĩa hạn này. Khi chủ bot nêu hạn cho cả kế hoạch và còn ít nhất một việc chưa làm, bot MUST đặt ngày đó làm ngày dự kiến của việc chưa làm đứng cuối trong thứ tự đã lưu. Việc đã xong và việc bỏ qua MUST NOT nhận ngày này. Goal MUST NOT chứa hạn đó. Tiêu đề MUST NOT nhận đoạn ngày. Nếu việc đó đã lưu và ngày của việc đó đổi, lần đặt này MUST đi qua tool dời ngày và MUST qua khóa lạc quan theo FR-008. Dòng lịch sử MUST chỉ sinh khi việc đó đổi từ một ngày sang một ngày khác. Ngày đặt trong `create_plan` hoặc `add_subtask` không đi qua tool dời ngày.
- **FR-006**: Mỗi việc con MUST có một sức: S, M, L, hoặc trống. Trống MUST là hợp lệ. Một chỗ cấu hình MUST map S = 1 giờ, M = 3 giờ, L = 6 giờ. Vòng này MUST chỉ lưu sức và MUST NOT cộng giờ, MUST NOT cảnh báo vượt quỹ giờ, và MUST NOT ghi rằng một việc đang được tính tạm.
- **FR-007**: Lịch sử dời việc MUST chỉ thêm dòng. Dòng đã có MUST NOT bị sửa và MUST NOT bị xóa. Dòng MUST chỉ sinh khi một việc đổi từ một ngày sang một ngày khác. Mỗi dòng MUST ghi việc nào, ngày đi, ngày đến, chỗ cho lý do, và thời điểm lần ghi. Ngày đi và ngày đến MUST là ngày lịch và MUST NOT trống. Thời điểm MUST là mốc giờ của lần ghi. Lý do MUST được phép trống. Khi chủ bot đã nói lý do, dòng MUST ghi lý do đó.
- **FR-008**: Một lần gọi tool dời ngày MUST là một lần ghi, gồm lần đặt ngày đầu và lần bỏ ngày. Mỗi việc đổi từ một ngày sang một ngày khác trong lần gọi đó MUST có đúng một dòng lịch sử trong cùng lần ghi. Việc đi từ trống sang một ngày, hoặc từ một ngày sang trống, MUST đổi ngày đã lưu trong lần ghi đó và MUST NOT sinh dòng lịch sử. Cả lần ghi MUST cùng được lưu hoặc cùng không được lưu. Khóa lạc quan của [D-021](../../docs/DECISIONS.md) MUST giữ nguyên: bản cũ hơn không ghi đè; lần bị từ chối để nguyên mọi ngày trong lần gọi và không thêm dòng lịch sử nào của lần gọi đó.
- **FR-009**: Mọi kế hoạch và việc con đang có MUST còn sau khi thêm trường mới. Goal, tiêu đề, trạng thái, ghi chú, thứ tự, thời điểm tạo và thời điểm đổi trạng thái MUST giữ nguyên khi chỉ thêm trường. Trường mới trên dòng cũ MUST trống. Tiêu đề đang chứa đoạn ngày MUST giữ nguyên từng chữ. Trường ngày của việc đó MUST để trống. Vòng này MUST NOT chuyển đoạn ngày từ tiêu đề sang trường ngày.
- **FR-010**: Đổi ngày, ưu tiên, sức hoặc ghi chú MUST NOT đổi thời điểm tạo việc con. Thời điểm đổi trạng thái MUST đổi chỉ khi trạng thái đổi.
- **FR-011**: Dữ liệu mới MUST NOT mang danh tính người dùng, theo [D-022](../../docs/DECISIONS.md). Trạng thái mới MUST nằm ở kho bền và MUST còn khi một lần chạy khác không chung bộ nhớ, theo constitution nguyên tắc II. Mọi lời ghi mới MUST trả về một giá trị, theo [D-023](../../docs/DECISIONS.md). Đường truy cập kho MUST vẫn là đường duy nhất của constitution III.
- **FR-012**: Số phiên bản lời hướng dẫn MUST là số nguyên 4. Số phiên bản bộ định nghĩa tool MUST là số nguyên 3. Dòng nhật ký của một lần gọi mô hình đã kết thúc MUST ghi hai số đó và MUST giữ tập khóa đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md).
- **FR-013**: Lời hướng dẫn bản 4 MUST giữ mọi luật đang có của bản 3. Bản 4 MUST thêm luật: ngày dự kiến đặt vào trường ngày của việc con và không viết vào tiêu đề. Lời hướng dẫn MUST nói ngày, sức và ưu tiên đi vào các tool đã chốt, không đi vào tiêu đề.
- **FR-014**: Bộ câu đánh giá phiên bản 2 MUST gồm đủ bảy tình huống của User Story 8. Bộ câu phiên bản 1 MUST còn. Tình huống chủ bot nêu hạn cho cả kế hoạch MUST đo việc đặt ngày đó lên việc chưa làm cuối cùng và MUST thấy kế hoạch không có cột hạn. Kết quả lưu của tình huống tin dài MUST theo luật goal đã chốt. Tình huống hạn tương đối MUST có ba ca theo FR-019: "cuối tuần này" chấm theo Chủ nhật của tuần chứa hôm nay; tên một thứ trong ngày chính là thứ đó chấm theo việc bot hỏi lại và kho không đổi; "tuần sau" không kèm thứ chấm theo việc bot hỏi lại và kho không đổi. Tình huống dời thêm một ngày khi hạn sau lần dời bằng hạn kế hoạch khác MUST theo FR-017. Tình huống liệt kê tiêu đề trong một câu MUST được chấm: đạt khi mỗi tiêu đề được lưu đúng từng chữ, viết lại tiêu đề là trượt. Tình huống "học xong bảng chữ cái" MUST được chấm với seed hai việc tách riêng Hiragana và Katakana: đạt khi bot hỏi lại và kho không đổi, đánh dấu xong một hoặc cả hai việc mà không hỏi là trượt. Ca kho chỉ có một việc gộp "Hiragana và Katakana" MUST NOT được chấm đạt hay trượt và MUST được ghi trong báo cáo eval. Tình huống sửa lời sau khi đánh dấu nhầm MUST chỉ được ghi nhận trong báo cáo eval và MUST NOT được chấm đạt hay trượt.
- **FR-015**: Vòng này MUST NOT làm việc hằng ngày, sự kiện đột xuất, quét tải, xếp lại lịch, form nhập kế hoạch, Mini App, lệnh `/today`, nhắc theo giờ, hay voice. Vòng này MUST NOT thêm trường "xong khi" cho việc con và MUST NOT thêm tên kế hoạch tách khỏi goal. Hai trường đó để vòng form. Goal MUST tiếp tục là tên duy nhất của kế hoạch.
- **FR-016**: Digest và `/next` MUST dùng chung một quy tắc dựng. Quy tắc MUST NOT gọi mô hình và MUST NOT nhận thời điểm hiện tại. Hai lần gọi với cùng các kế hoạch MUST ra cùng một chuỗi. Thứ tự đoạn MUST giữ nguyên spec 014: kế hoạch cũ nhất trước, theo thứ tự tạo tăng dần. Với việc chưa làm đầu tiên của một đoạn, nếu việc đó có ngày, cuối dòng tiêu đề MUST có một dấu cách rồi một đoạn ngày do code dựng từ trường ngày. Dạng MUST là `(thứ Sáu 06/11)` cho ngày 2026-11-06. Tên thứ MUST là thứ Hai, thứ Ba, thứ Tư, thứ Năm, thứ Sáu, thứ Bảy, hoặc Chủ nhật. Số ngày và số tháng MUST có hai chữ số, không có năm, không có múi giờ. Việc không có ngày MUST NOT có đoạn ngày thêm. Quy tắc MUST NOT đánh dấu quá hạn. Tiêu đề đã lưu MUST giữ nguyên từng chữ. Đoạn ngày chỉ nằm trên chữ dựng ra. Vòng này MUST sửa ba file: `specs/014-morning-digest/spec.md`, `specs/014-morning-digest/contracts/digest-text.md`, và `tests/test_morning_text.py`. Trong spec 014, câu cấm quy tắc thêm ngày được thay bằng đoạn ngày này. `tasks.md` của spec 014 là biên bản vòng F10 và MUST NOT bị viết lại.
- **FR-017**: "Dời hạn thêm một ngày" MUST chỉ đổi ngày của các việc chưa làm đang mang đúng ngày hạn của kế hoạch đó, sang ngày lịch hôm sau. Việc chưa làm có ngày sớm hơn MUST giữ nguyên. Việc đã xong và việc bỏ qua MUST giữ nguyên. Trùng MUST chỉ khi hạn của kế hoạch đang dời, tính theo FR-005 trên trạng thái sau lần dời, bằng hạn của một kế hoạch khác. Kế hoạch đang dời MUST NOT tính vào phép so. Lần dời không làm đổi hạn của chính kế hoạch đó MUST NOT đòi xác nhận vì trùng. Kiểm trùng MUST chỉ áp cho tool dời ngày. Tool dời ngày MUST nhận một kế hoạch, một danh sách các việc kèm ngày mới hoặc trống, lý do tùy chọn, và cờ xác nhận. Lần gọi thấy trùng mà không phải lần gọi lại với cờ MUST trả thông tin trùng và MUST NOT ghi. Lần gọi đầu của ca trùng MUST không có cờ. Chỉ lần gọi lại với cờ, sau khi chủ bot đồng ý, MUST ghi. Cờ MUST NOT được coi là chứng minh sự đồng ý của chủ bot. Bộ eval phiên bản 2 MUST chấm ca trùng theo kho: lần gọi đầu không có cờ, và kho không đổi trước khi chủ bot trả lời. Vòng này MUST chỉ so ngày với ngày, MUST NOT cộng giờ, và MUST NOT áp quỹ 8 giờ. Cộng giờ và quỹ 8 giờ để vòng quét tải.
- **FR-018**: `create_plan` MUST nhận ưu tiên của kế hoạch và, với mỗi việc, ngày cùng sức. `add_subtask` MUST nhận ngày và sức. Ưu tiên, ngày và sức MUST không bắt buộc. `create_plan` và `add_subtask` đặt ngày MUST NOT kiểm trùng. Kiểm trùng lúc tạo kế hoạch hoặc thêm việc thuộc vòng quét tải. Sau khi tạo, MUST có đúng ba tool sửa, mỗi tool một việc: đặt ưu tiên của một kế hoạch; đặt sức của một việc; dời ngày theo FR-017. Tool đặt ưu tiên MUST NOT đặt sức hay ngày. Tool đặt sức MUST NOT đặt ưu tiên hay ngày. Tool đổi trạng thái MUST NOT đặt ngày, sức hay ưu tiên.
- **FR-019**: Tuần lịch MUST là thứ Hai đến Chủ nhật theo ngày Helsinki của mốc đầu lượt. "Cuối tuần này" MUST là Chủ nhật của tuần chứa hôm nay. Hôm nay là Chủ nhật thì ngày đó MUST là hôm nay. Bot MUST lưu ngày đó và MUST nói ngày đã chọn. Tên một thứ khi hôm nay chính là thứ đó: bot MUST hỏi lại và MUST NOT ghi. Kho MUST không đổi. "Tuần sau" không kèm thứ: bot MUST hỏi lại và MUST NOT ghi. Kho MUST không đổi. Tên một thứ vào ngày khác, khi câu không kèm "tuần sau", MUST là lần tới của thứ đó. Bot MUST lưu ngày đó và MUST nói ngày đã chọn. "Thứ X tuần sau", câu có cả tên thứ lẫn "tuần sau", MUST là thứ X của tuần lịch kế tiếp. Bot MUST lưu ngày đó và MUST nói ngày đã chọn.
- **FR-020**: Vòng này MUST thêm bộ câu phiên bản 2 và MUST sửa bộ chạy để đọc bộ câu đó. Mỗi ca phiên bản 2 MUST mang mốc đồng hồ cố định của ca đó. Các ca hạn tương đối MUST dùng những thứ khác nhau cho hôm nay. Vòng này MUST chạy cả bộ câu phiên bản 1 với lời hướng dẫn bản 4, để đo hồi quy và việc chọn tool trong chín tool: sáu tool đang có và ba tool mới. Cách chấm từng ca phiên bản 1 MUST giữ nguyên so với lần p3-d2. Bộ chấm MUST là phiên bản 2. Bộ chấm phiên bản 2 MUST đọc được ngày, sức, ưu tiên và dòng lịch sử trong kho, và MUST chấm ca trùng hạn theo việc kho không đổi sau lần gọi đầu. Seed của ca trùng MUST có sẵn một kế hoạch khác với hạn đã biết. Mỗi bộ MUST được chạy một lần. Mỗi lần chạy MUST ghi một file kết quả trong `evals/results/`. Bộ câu phiên bản 1 MUST còn.

### Key Entities

- **Kế hoạch**: Thực thể đang có, thêm ưu tiên cao, vừa, thấp, hoặc trống. Không thêm độ gấp. Goal là tên duy nhất; không có tên tách khỏi goal. Không có cột hạn. Hạn là ngày dự kiến muộn nhất trong các việc chưa làm có ngày. Việc đã xong và việc bỏ qua không tính.
- **Việc con**: Thực thể đang có, thêm ngày dự kiến (ngày lịch hoặc trống) và sức S, M, L hoặc trống. Giữ tiêu đề, trạng thái, ghi chú, thứ tự, thời điểm tạo và thời điểm đổi trạng thái. Không có ưu tiên riêng. Phần sửa riêng ưu tiên dời sang vòng quét tải và không thuộc F17 của vòng này. Không có trường "xong khi"; trường đó để vòng form.
- **Lần dời việc**: Một dòng chỉ thêm. Chỉ sinh khi một việc đổi từ một ngày sang một ngày khác. Gắn với một việc con. Có ngày đi, ngày đến, lý do được phép trống, và thời điểm. Ngày đi và ngày đến luôn có ngày. Lý do có chữ khi chủ bot đã nói. Không sửa, không xóa. Lần đặt ngày đầu và lần bỏ ngày không phải một dòng của thực thể này.
- **Đồng hồ Helsinki**: Ngày lịch, thứ và múi giờ Europe/Helsinki của mốc đầu một lượt. Cùng đồng hồ địa phương mà digest đang dùng cho mốc 08:00. Cách đưa vào lượt để `/speckit-plan` quyết.
- **Lời hướng dẫn và bộ định nghĩa**: Hai số phiên bản, 4 và 3. Luật chữ của bản 3 cộng luật ngày không nằm trong tiêu đề.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần gọi mô hình trong một lượt nhận đúng ngày lịch, thứ và múi giờ Europe/Helsinki của mốc đầu lượt, cả ở giờ mùa đông và giờ mùa hè. 0 lần gọi buộc mô hình tự đoán hôm nay.
- **SC-002**: 100% việc con lưu được khi ngày dự kiến trống và khi ngày dự kiến là một ngày lịch. 0 ngày dự kiến đã lưu có kèm giờ. 100% ngày chủ bot đưa cho một việc đọc lại được từ trường ngày. 0 ngày mới chỉ tồn tại bên trong tiêu đề.
- **SC-003**: 100% kế hoạch lưu được với ưu tiên trống hoặc với đúng một trong ba mức cao, vừa, thấp. 0 kế hoạch có trường độ gấp. 0 lần ghi của vòng này ra tổng giờ hoặc cảnh báo vượt quỹ giờ. 0 việc con có trường "xong khi". 0 kế hoạch có tên tách khỏi goal. 0 việc con có ưu tiên riêng.
- **SC-004**: 100% việc con lưu được với sức trống hoặc với S, M, L. Chỗ cấu hình đọc ra S = 1 giờ, M = 3 giờ, L = 6 giờ.
- **SC-005**: 100% lần đổi từ một ngày sang một ngày khác thành công có đúng một dòng lịch sử mới cho việc đó, và ngày đọc lại khớp ngày đến. 100% lần đặt ngày đầu và lần bỏ ngày thành công thêm 0 dòng lịch sử. 0 dòng lịch sử có ngày đi trống hoặc ngày đến trống. 100% lần ghi bị từ chối vì bản cũ giữ nguyên ngày và thêm 0 dòng lịch sử. 100% dòng lịch sử đã có còn nguyên sau các lần dời sau.
- **SC-006**: 100% kế hoạch và việc con đang có trước khi thêm trường vẫn đọc lại được với cùng goal, tiêu đề, trạng thái, ghi chú, thứ tự và hai mốc thời gian cũ. 100% trường mới trên các dòng đó trống. 0 tiêu đề cũ bị viết lại.
- **SC-007**: 100% lần đọc lời hướng dẫn thấy số phiên bản 4 và thấy luật ngày không viết vào tiêu đề, cùng các luật bản 3. 100% lần đọc bộ định nghĩa thấy số phiên bản 3. 100% dòng nhật ký của lần gọi mô hình đã kết thúc ghi hai số đó với đúng tập khóa đang có.
- **SC-008**: Bộ câu phiên bản 2 chứa đủ 7 tình huống của User Story 8. 100% lần chấm tình huống hạn cả kế hoạch thấy ngày đó ở việc chưa làm cuối cùng và thấy 0 cột hạn trên kế hoạch. 100% lần chấm tình huống dời thêm một ngày khi hạn của kế hoạch sau lần dời bằng hạn kế hoạch khác thấy lần gọi đầu không có cờ xác nhận và kho không đổi trước khi chủ bot trả lời, rồi sau lần gọi có cờ chỉ các việc chưa làm đang mang đúng ngày hạn dịch một ngày. 0 lần chấm lấy bản thân cờ làm bằng chứng chủ bot đã đồng ý. 100% lần chấm tình huống tin dài dùng luật goal đã chốt. 100% lần chấm "cuối tuần này" thấy ngày là Chủ nhật của tuần chứa hôm nay. 100% lần chấm tên một thứ trong đúng ngày đó, và "tuần sau" không kèm thứ, thấy bot hỏi lại và kho không đổi. Bộ câu phiên bản 1 còn đủ để đọc lại lần đo cũ. 100% ca phiên bản 2 mang mốc đồng hồ của chính ca đó. Một lần chạy bộ phiên bản 1 với lời hướng dẫn bản 4 và một lần chạy bộ phiên bản 2 mỗi lần ghi một file trong `evals/results/`. Cách chấm ca phiên bản 1 trùng cách chấm của p3-d2. 100% lần chấm liệt kê tiêu đề trong một câu đạt chỉ khi mỗi tiêu đề đúng từng chữ, và 100% lần viết lại tiêu đề là trượt. 100% lần chấm "học xong bảng chữ cái" với seed Hiragana và Katakana tách riêng đạt chỉ khi bot hỏi lại và kho không đổi. 0 lần chấm đạt hay trượt cho ca một việc gộp "Hiragana và Katakana", và 0 lần chấm đạt hay trượt cho câu sửa lời. 100% hai ca đó có hành vi được ghi trong báo cáo eval.
- **SC-009**: 100% dòng tiêu đề việc chưa làm đầu tiên có ngày kết thúc bằng đoạn ngày do code dựng từ trường ngày, đúng tên thứ tiếng Việt và dạng `DD/MM` trong ngoặc. 100% việc chưa làm đầu tiên không có ngày thêm 0 đoạn ngày. 0 tin digest hoặc `/next` có chữ quá hạn, có năm, hoặc có chữ múi giờ do quy tắc thêm. 100% cặp lần gọi trên cùng các kế hoạch ra cùng chuỗi mà không nhận thời điểm hiện tại. 100% tin `/next` trùng chữ digest của cùng các kế hoạch. Thứ tự đoạn vẫn là kế hoạch cũ nhất trước.

## Assumptions

- Một lượt dùng một mốc đồng hồ, lấy ở đầu lượt, cho mọi lần gọi mô hình của lượt đó, kể cả khi lượt đi qua nửa đêm.
- Ba chữ ưu tiên mà chủ bot nghe là cao, vừa, thấp. Nếu chỗ lưu dùng mã khác, mã đó map một-một với ba chữ này và không thêm mức. Trống không được hiểu thành vừa.
- Sức lưu bằng chữ S, M, L. Số giờ không lưu trên từng việc; số giờ chỉ ở một chỗ cấu hình.
- Phần "việc chưa có ước lượng thì tính tạm như M" và câu cảnh báo "tính tạm" của [D-024](../../docs/DECISIONS.md) mục 5 thuộc quét tải, không thuộc vòng này.
- Phần việc con sửa riêng ưu tiên ở D-024 mục 3 dời sang vòng quét tải, là nơi đầu tiên cần nó. Vòng này chưa mở rộng phần đó sang F17. Ưu tiên lưu trong vòng này chỉ ở kế hoạch.
- Người dùng kho là một chủ bot, như PRODUCT §2. Dòng lịch sử không ghi một người.
- Ngoài phạm vi, theo mô tả tính năng và D-024: việc hằng ngày; sự kiện đột xuất; quét tải (cộng giờ, cảnh báo vượt 8 giờ, danh sách việc sẽ bị dời, kiểm trùng lúc tạo kế hoạch hoặc thêm việc); xếp lại lịch; form nhập kế hoạch và Mini App (F18); trường "xong khi" của việc con; tên kế hoạch tách khỏi goal; ưu tiên riêng của việc con (dời sang vòng quét tải, chưa thuộc F17); `/today`; nhắc theo giờ; voice.
- Quy tắc dựng digest không nhận thời điểm hiện tại. Đoạn ngày trên tin sáng lấy từ trường ngày của việc, không lấy từ đồng hồ lúc dựng.

## Câu hỏi dành cho /speckit-clarify

Câu 2 đến câu 11 đã chốt ở Clarifications và đã gỡ khỏi mục này. Câu 1 để `/speckit-plan` quyết. Câu này không được dùng làm giả định ngầm của yêu cầu phía trên.

1. Mô hình nhận ngày hôm nay bằng cách nào mỗi lượt (lời hướng dẫn hệ thống hay tin nhắn), khi lượt hiện không nhận thời điểm; và đồng hồ chung dùng lại `helsinki_clock` hay tách module. Để `/speckit-plan` quyết.
