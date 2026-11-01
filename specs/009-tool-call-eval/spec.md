# Feature Specification: Bộ đánh giá gọi tool của một lượt

**Feature Branch**: `009-tool-call-eval`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Bộ eval cho hành vi gọi tool của lượt LLM (run_turn). Vì sao: lượt LLM đã chạy được với API thật nhưng chưa có cách đo nó gọi tool đúng hay sai. Cần một đường cơ sở cho prompt v1 trước khi đổi sang prompt v2, và chạy lại được mỗi khi đổi prompt, định nghĩa tool hoặc model để so. Hành vi: một bộ câu tiếng Việt cố định, có phiên bản, khoảng 50 câu. Mỗi câu có id, nhóm, câu người dùng, tên bộ dữ liệu dựng sẵn cho kho (có thể rỗng), và kỳ vọng. Các nhóm: nhờ lập kế hoạch, chỉ kể việc, hỏi danh sách, xem chi tiết, cập nhật trạng thái việc con, thêm việc con, ghi chú, chào hỏi, câu mơ hồ, câu ngoài phạm vi. Kỳ vọng theo nhóm: không gọi tool (chỉ kể việc, chào hỏi, mơ hồ, ngoài phạm vi); gọi create_plan đúng một lần (nhờ lập kế hoạch); gọi tool đọc tương ứng (danh sách, chi tiết). Với ca ghi, đạt hay không xét bằng trạng thái kho sau lượt; được phép gọi tool đọc trước để tra id. Luật chấm tự động: đúng tool hoặc đúng là không gọi tool; số lần gọi create_plan; tham số bắt buộc có mặt; tiêu đề việc con không có tiền tố thứ tự (ít nhất Ngày 1:, Tuần 1:, 1., Bước 1); câu trả lời không có Markdown; câu trả lời không tự xưng trợ lý lập kế hoạch. Luật điểm kết thúc đo được không chấm tự động, có chỗ đánh dấu tay từng tiêu đề. Mỗi câu chạy 3 lần độc lập, kho dựng lại, lịch sử rỗng. Báo tỉ lệ đạt theo câu, luật, nhóm, và tổng token đầu vào, đầu ra từ dòng log của lượt. Lỗi hạ tầng ghi riêng, không tính trượt luật, không dừng cả bộ. Mỗi lần chạy lưu một file kết quả gắn prompt_version, definitions_version, model và ngày, gồm câu trả lời, các dòng log, số vòng tool và kết quả từng luật. File được commit làm đường cơ sở. Không file nào chứa khóa API. Tiêu chí: phần đọc, dựng kho, chấm và tổng hợp chạy trong test không gọi mạng, dùng output mô hình ghi sẵn; mỗi luật có ca đạt và ca trượt; lần chạy API thật là lệnh tay, không nằm trong bộ test thường. Ngoài phạm vi: không sửa system prompt, định nghĩa tool, run_turn, adapter hay các tool; prompt v1 đóng băng; mong đợi đường cơ sở trượt ở tiền tố Ngày 1: và Markdown; không dùng LLM để chấm; không hội thoại nhiều lượt; không Telegram, không Worker; không tự sáng tác bộ câu; không sửa docs/PRODUCT.md. Dòng log tám khóa và bảy khóa là hợp đồng D-014, D-015."

## Clarifications

### Session 2026-10-31

- Q: Những dấu nào làm câu trả lời trượt luật Markdown? → A: Giữ ba backtick, một backtick, `**`, `__`, `](`, dòng có ký tự khác khoảng trắng đầu tiên là `#`, và dòng bắt đầu bằng `*` rồi khoảng trắng. Bỏ dòng đánh số và bỏ dòng bắt đầu bằng `-` hoặc `+` rồi khoảng trắng. Câu có dòng `1. Chạy 2km` và dòng `- Nộp báo cáo` đạt.
- Q: Lỗi chạy và lần hết lượt tool nhận ra bằng gì? → A: Theo dòng log cuối và theo exception, không so câu trả lời. Kết thúc bình thường khi dòng cuối là dòng tám khóa, `error_type` là `null`, và `stop_reason` là `end_turn`. Hết lượt tool khi dòng cuối là dòng tám khóa, `stop_reason` là `tool_use`, `error_type` là `null`, và trước đó đúng ba vòng tool. Năm mã lỗi chạy trong file kết quả: `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`.
- Q: Ctrl+C trong lệnh tay xử lý thế nào? → A: Dừng cả bộ, không chạy lần nào tiếp theo, không ghi file kết quả. Hủy không phải lỗi chạy của một lần.
- Q: Lệnh tay gặp khóa rỗng hoặc chỉ khoảng trắng thì sao? → A: Kiểm trước lượt đầu, dừng ngay với một câu báo, không chạy lượt nào, không ghi file. Giấu khóa chỉ áp cho khóa không rỗng. `MissingKeyError` vẫn là lỗi chạy ở phần chấm và bộ test thường.
- Q: Luật đúng tool của ba nhóm ghi gồm những tên nào? → A: Mọi lần gọi chỉ được là `get_plans`, `get_plan_detail`, hoặc đúng tool ghi của nhóm. Ca cập nhật trạng thái có `set_subtask_note` thì trượt.
- Q: Luật tiền tố có phân biệt hoa thường không, và có từ nào thêm? → A: Không phân biệt hoa thường. Thêm `Giai đoạn`. `ngày 1:` và `Giai đoạn 2:` trượt.
- Q: Báo cáo đếm lần hết lượt tool ở đâu? → A: Đếm theo câu và theo nhóm, tách khỏi tỉ lệ đạt.

## User Scenarios & Testing *(mandatory)*

Người dùng của lát này là người giữ lời hướng dẫn và bộ định nghĩa tool. Người đó cần một đường cơ sở đo được: một lượt có gọi đúng tool hay không, trước khi đổi lời hướng dẫn từ phiên bản 1 sang phiên bản 2. Lượt được chấm là lượt đã có ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Sáu tool và dòng log bảy khóa đã có ở [spec điều phối tool](../007-plan-tool-router/spec.md). Lát này không đổi lượt, không đổi tool, không đổi lời hướng dẫn, và không đổi hai dòng log.

Bộ câu v1 không nằm trong spec này. Spec khóa định dạng và luật. Nguyên văn bộ câu được đưa vào ở bước implement.

### User Story 1 - Chấm một lượt đã ghi sẵn, không mở mạng (Priority: P1)

Người giữ đưa một câu đã đúng định dạng, một kho dựng từ bộ dữ liệu của câu đó, và một phản hồi mô hình đã ghi sẵn gồm câu trả lời cùng các lần đòi tool. Lượt chạy tool trên kho đó. Phần chấm đọc câu trả lời, dòng log của lượt, dòng log của tool, và kho sau lượt, rồi cho biết từng luật đạt hay trượt. Không hỏi một mô hình thứ hai để chấm. Không mở mạng.

**Why this priority**: Không có phần chấm này thì không có đường cơ sở, và không có cách chạy lại khi lời hướng dẫn, bộ định nghĩa, hoặc model đổi.

**Independent Test**: Bộ test dùng phản hồi mô hình ghi sẵn. Mỗi luật tự động có ít nhất một ca đạt và một ca trượt. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** một câu nhóm "chỉ kể việc", kho rỗng, và phản hồi ghi sẵn là một câu văn không đòi tool, **When** chấm, **Then** luật không gọi tool đạt. Luật Markdown và luật không tự xưng đạt khi câu trả lời không dính các dấu bị cấm ở FR-009.
2. **Given** cùng nhóm đó nhưng phản hồi ghi sẵn đòi `create_plan` một lần, **When** chấm, **Then** luật không gọi tool trượt và luật số lần `create_plan` trượt.
3. **Given** một câu nhóm "nhờ lập kế hoạch" và phản hồi đòi đúng một lần `create_plan` với mục tiêu có mặt, không tool khác, **When** chấm, **Then** luật đúng tool đạt và luật số lần `create_plan` đạt.
4. **Given** phản hồi đó đòi `create_plan` hai lần, **When** chấm, **Then** cả hai luật đó trượt.
5. **Given** một câu nhóm "hỏi danh sách" và mọi lần tool đều là `get_plans`, có ít nhất một lần, **When** chấm, **Then** luật đúng tool đạt. **Given** xen một `get_plan_detail`, **Then** luật đó trượt.
6. **Given** một câu nhóm "xem chi tiết", **When** phản hồi gọi `get_plans` rồi `get_plan_detail`, **Then** luật đúng tool đạt. **Given** chỉ có `get_plans`, **Then** luật đó trượt. **Given** có `update_subtask`, **Then** luật đó trượt.
7. **Given** một lần `create_plan` thiếu mục tiêu, **When** chấm, **Then** luật tham số bắt buộc trượt. **Given** mục tiêu có mặt và không có `subtasks`, **Then** luật tham số bắt buộc đạt.
8. **Given** `create_plan` gửi việc con "Ngày 1: nộp báo cáo", "ngày 1: nộp báo cáo", "Tuần 1: ôn tập", "1. học", "Bước 1 viết", và "Giai đoạn 2: ôn", **When** chấm, **Then** luật tiền tố trượt. **Given** việc con "Nộp báo cáo thứ Sáu", **Then** luật tiền tố đạt.
9. **Given** câu trả lời có một dòng bắt đầu bằng `#` hoặc có `**`, **When** chấm, **Then** luật Markdown trượt. **Given** câu trả lời có dòng "1. Chạy 2km" và dòng "- Nộp báo cáo", không có các dấu còn lại của FR-009, **Then** luật Markdown đạt. **Given** câu trả lời có cụm "trợ lý lập kế hoạch", **Then** luật tự xưng trượt.

---

### User Story 2 - Ca ghi được chấm bằng kho sau lượt (Priority: P1)

Với nhóm cập nhật trạng thái, thêm việc con, và ghi chú, đạt hay trượt xét bằng kho sau lượt, không xét bằng việc mô hình có nói đúng tên tool trong câu trả lời. Mô hình được gọi tool đọc trước để tra danh tính. Danh tính trong kho do lần dựng kho cấp, nên câu người dùng không chứa danh tính đó.

**Why this priority**: Ba nhóm này là hành vi ghi. Chấm bằng tên tool mà không nhìn kho thì không biết việc con có đổi thật hay không.

**Independent Test**: Bộ dữ liệu có một kế hoạch và một việc con. Phản hồi ghi sẵn gọi tool đọc rồi tool ghi. So kho sau lượt với kỳ vọng. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** kỳ vọng đưa việc "Học hiragana" từ `pending` sang `done`, và phản hồi gọi `get_plans` rồi `update_subtask` đúng việc đó, **When** chấm, **Then** luật kho đạt. Việc con khác không bị xét.
2. **Given** cùng kỳ vọng nhưng phản hồi chỉ gọi `get_plans`, **When** chấm, **Then** luật kho trượt vì trạng thái vẫn `pending`.
3. **Given** kỳ vọng thêm việc "Làm bài tập cuối chương" vào kế hoạch chưa có việc đó, và phản hồi gọi `add_subtask` với tiêu đề đó, **When** chấm, **Then** luật kho đạt.
4. **Given** kỳ vọng ghi chú của một việc là "Đợi giáo trình", và phản hồi gọi `set_subtask_note` ra đúng ghi chú đó, **When** chấm, **Then** luật kho đạt. **Given** kỳ vọng là không còn ghi chú và phản hồi xóa ghi chú, **Then** luật kho đạt.
5. **Given** một ca ghi mà phản hồi còn gọi `create_plan`, **When** chấm, **Then** luật số lần `create_plan` trượt dù luật kho có thể đạt.
6. **Given** một ca cập nhật trạng thái gọi `get_plans` rồi `update_subtask`, **When** chấm, **Then** luật đúng tool đạt. **Given** ca đó còn gọi `set_subtask_note`, **Then** luật đúng tool trượt.

---

### User Story 3 - Bộ câu và bộ dữ liệu dựng lại được (Priority: P1)

Một bộ câu có số phiên bản. Mỗi câu có id, một nhóm trong mười nhóm, câu người dùng, tên bộ dữ liệu, và kỳ vọng khớp nhóm. Tên bộ dữ liệu rỗng nghĩa là kho không có kế hoạch. Người đọc bộ câu từ chối cả bộ khi sai định dạng, trước mọi lượt. Nội dung tiếng Việt của bộ v1 không do spec này bịa.

**Why this priority**: Luật chấm không có nghĩa nếu câu và kho đầu vào không cố định giữa các lần chạy.

**Independent Test**: Một bộ câu tối thiểu đúng định dạng được đọc và dựng kho. Một bộ thiếu id, sai nhóm, hoặc trỏ tên bộ dữ liệu không có thì bị từ chối trước khi chạy lượt. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** một bộ đúng định dạng, một câu trỏ bộ dữ liệu rỗng và một câu trỏ bộ có một kế hoạch, **When** dựng kho cho từng lần chạy, **Then** kho rỗng không có kế hoạch, kho kia có đúng mục tiêu và việc con của bộ dữ liệu, theo thứ tự trong bộ dữ liệu.
2. **Given** hai lần chạy cùng một câu, lần đầu có thêm một việc con, **When** dựng lần hai, **Then** kho lần hai trùng bộ dữ liệu gốc, không còn việc con mà lần đầu thêm.
3. **Given** một câu có id trùng câu khác, nhóm không thuộc mười nhóm, hoặc kỳ vọng không khớp nhóm, **When** đọc bộ, **Then** bộ bị từ chối và không chạy lượt nào.

---

### User Story 4 - Ba lần độc lập, lỗi hạ tầng không làm dừng bộ (Priority: P2)

Mỗi câu chạy ba lần. Mỗi lần có kho dựng lại và lịch sử rỗng. Lỗi chạy nhận theo FR-012, bằng cấu trúc dòng log hoặc bằng `MissingKeyError`, không bằng câu trả lời. Lỗi chạy không tính là trượt luật hành vi và không nằm ở mẫu số của tỉ lệ đạt. Các lần còn lại và các câu sau vẫn chạy.

**Why this priority**: Đường cơ sở cần một tỉ lệ, không cần một lần mạng hỏng làm mất cả bộ.

**Independent Test**: Ba phản hồi ghi sẵn cho một câu, trong đó một lần có mã lỗi chạy riêng. Bộ vẫn chấm hai lần kia và vẫn chạy câu sau. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** một câu có lần hai mang một trong năm mã lỗi chạy của FR-012, **When** chạy đủ ba lần ở phần chấm, **Then** lần hai là lỗi chạy với đúng mã đó, hai lần kia được chấm luật, và câu sau vẫn chạy. Câu trả lời không được dùng để nhận ra lỗi chạy.
2. **Given** cả ba lần ở phần chấm đều ném `MissingKeyError`, **When** chạy bộ, **Then** không có lần nào vào mẫu số tỉ lệ hành vi, bộ vẫn kết thúc, và số lỗi chạy của câu đó là 3.
3. **Given** một lần có dòng log tám khóa với `stop_reason` là `tool_use` và `error_type` trống, sau đúng ba vòng tool đã chạy, **When** chấm, **Then** lần đó không phải lỗi chạy. Luật hành vi được chấm trên câu trả lời và các tool đã chạy. Lần đó được đếm là hết lượt tool.

---

### User Story 5 - Báo cáo tỉ lệ và một file đường cơ sở (Priority: P2)

Sau một lần chạy cả bộ, người giữ thấy tỉ lệ đạt của từng câu, từng luật, và từng nhóm, cùng tổng token đầu vào và đầu ra lấy từ dòng log của lượt. Cùng lần chạy đó ghi một file kết quả. Tên và nội dung file mang phiên bản lời hướng dẫn, phiên bản bộ định nghĩa, model, và ngày. Trong file có câu trả lời, các dòng log, số vòng tool, và kết quả từng luật của mỗi lần. File không chứa giá trị khóa. File này là thứ được commit làm đường cơ sở. Lệnh chạy không tự commit.

**Why this priority**: So prompt v1 với prompt v2 cần một file cũ còn nguyên và một file mới, không cần nhớ kết quả trong đầu.

**Independent Test**: Chấm một bộ tối thiểu từ phản hồi ghi sẵn, rồi đọc báo cáo và file kết quả. Không mở mạng. Một ca cố ý đưa giá trị khóa vào câu trả lời ghi sẵn và xác nhận file đã ghi không còn giá trị đó.

**Acceptance Scenarios**:

1. **Given** một bộ hai câu, mỗi câu ba lần đều được chấm, **When** đọc báo cáo, **Then** có tỉ lệ từng câu trên số lần được chấm, tỉ lệ từng luật trên số lần luật đó được xét, tỉ lệ từng nhóm, số lần hết lượt tool theo câu và theo nhóm, và hai tổng token là số nguyên. Số lần hết lượt tool không nằm trong tỉ lệ đạt.
2. **Given** một lần lỗi chạy có dòng log mô hình với token, **When** cộng tổng, **Then** token của lần đó vẫn được cộng. Lần đó không làm giảm tỉ lệ hành vi.
3. **Given** một lần chạy xong, **When** tìm file kết quả, **Then** tên file có phiên bản lời hướng dẫn, phiên bản bộ định nghĩa, model, và ngày. Chạy lại cùng ngày không ghi đè file đó.
4. **Given** câu trả lời ghi sẵn chứa đúng giá trị khóa người gọi đã đưa, **When** ghi file, **Then** file không chứa giá trị đó.

---

### User Story 6 - Chỗ đánh dấu tay cho điểm kết thúc đo được (Priority: P3)

Luật "mỗi việc con có điểm kết thúc đo được" không có trong tỉ lệ tự động. File kết quả có một chỗ cho từng tiêu đề việc con mà lượt đã gửi, để người đọc đánh dấu đạt, trượt, hoặc còn để trống. Mặc định là còn để trống.

**Why this priority**: Luật này thuộc lời hướng dẫn phiên bản 1 nhưng không chấm được bằng quy tắc chữ. Đường cơ sở vẫn phải giữ chỗ để người đọc ghi.

**Independent Test**: Một lượt gửi hai tiêu đề. File kết quả có hai chỗ, cả hai để trống. Tỉ lệ tự động không đổi khi người đọc đánh một chỗ thành trượt. Không mở mạng.

**Acceptance Scenarios**:

1. **Given** `create_plan` gửi hai tiêu đề, **When** xem file kết quả, **Then** có đúng hai chỗ đánh dấu, cả hai để trống, và tiêu đề lấy từ đầu vào tool chứ không lấy từ câu trả lời.
2. **Given** lượt không gửi tiêu đề việc con nào, **When** xem file, **Then** không có chỗ đánh dấu nào cho luật này.
3. **Given** người đọc đánh một tiêu đề là trượt, **When** đọc lại tỉ lệ tự động, **Then** các tỉ lệ đó không đổi.

---

### User Story 7 - Lần chạy API thật là lệnh tay (Priority: P3)

Người giữ chạy cả bộ câu v1 bằng một lệnh tay, với khóa do người gọi đưa, qua đúng lượt hiện có. Lệnh đó không nằm trong bộ test thường. Bộ test thường chỉ dùng phản hồi ghi sẵn.

**Why this priority**: Đường cơ sở thật cần API, nhưng mỗi lần test thường không được tốn tiền và không được phụ thuộc mạng.

**Independent Test**: Bộ test thường không có ca nào mở mạng. Lệnh tay được nhận ra là đường riêng: khóa rỗng hoặc chỉ khoảng trắng thì dừng trước lượt đầu, không nằm trong bộ test thường.

**Acceptance Scenarios**:

1. **Given** bộ test thường, **When** chạy test, **Then** không có lời gọi mạng và không có lời gọi mô hình thật.
2. **Given** lệnh tay không được đưa khóa, được đưa khóa rỗng, hoặc được đưa khóa chỉ khoảng trắng, **When** chạy, **Then** lệnh dừng trước lượt đầu với đúng một câu báo, không chạy lượt nào, và không ghi file kết quả.
3. **Given** lệnh tay đang chạy và người giữ bấm Ctrl+C, **When** lệnh nhận việc hủy, **Then** lệnh dừng cả bộ, không chạy lần nào tiếp theo, và không ghi file kết quả.

---

### Edge Cases

- Bộ câu sai định dạng bị từ chối trước lượt đầu. Đó không phải lỗi chạy của một lượt, và không có file đường cơ sở cho lần đó.
- Tên bộ dữ liệu rỗng là kho không có kế hoạch. Tên không rỗng mà không có trong bộ dữ liệu làm cả bộ câu bị từ chối.
- Hai mục tiêu trùng trong một bộ dữ liệu, hoặc hai tiêu đề trùng trong một kế hoạch, làm bộ dữ liệu bị từ chối.
- Ca cập nhật mà trạng thái kỳ vọng đã đúng từ bộ dữ liệu, ca ghi chú mà ghi chú kỳ vọng đã đúng từ bộ dữ liệu, hoặc ca thêm việc mà tiêu đề đã có sẵn, là sai định dạng, không phải lần mô hình trượt.
- Danh tính kế hoạch và việc con do lần dựng kho cấp. Kỳ vọng chỉ việc bằng mục tiêu và tiêu đề, không bằng danh tính, và không bằng cách đọc hiểu câu tiếng Việt.
- Lịch sử mỗi lần chạy là rỗng. Bộ câu không có trường lịch sử.
- Câu trả lời rỗng vẫn được chấm. Luật Markdown và luật tự xưng đạt khi chuỗi rỗng không chứa các dấu bị cấm. Dòng `1. Chạy 2km` và dòng `- Nộp báo cáo` không làm luật Markdown trượt.
- Lỗi chạy nhận theo dòng log cuối và theo exception, đúng FR-012. Không có dòng tám khóa nào là `no_model_log`, trừ khi exception là `MissingKeyError` thì mã là `missing_key`. Dòng log cuối là dòng bảy khóa là `ended_on_tool_log`. Dòng cuối là dòng tám khóa có `error_type` khác `null` là `model_error`. Dòng cuối là dòng tám khóa, `error_type` là `null`, và `stop_reason` ngoài `end_turn` cũng không phải hết lượt tool, là `bad_stop_reason`, kể cả `max_tokens`. Câu trả lời trùng câu lỗi phía mô hình mà dòng cuối là `end_turn` và `error_type` là `null` thì không phải lỗi chạy.
- Hết lượt tool chỉ nhận khi dòng log cuối là dòng tám khóa: `stop_reason` là `tool_use`, `error_type` là `null`, và trước dòng đó đã có đúng ba vòng tool. Không so câu trả lời. Lần đó vẫn được chấm luật và được đếm riêng.
- Kho của một lần lỗi chạy bị bỏ. Lần sau dựng lại từ bộ dữ liệu.
- Ctrl+C ở lệnh tay dừng cả bộ. Không chạy lần nào tiếp theo. Không ghi file kết quả. Hủy không phải lỗi chạy của một lần.
- Không có lần gọi tool thì luật tham số bắt buộc đạt, và luật tiền tố đạt vì không có tiêu đề mới. Với nhóm ghi, không có lần gọi tool thì luật đúng tool vẫn đạt, và luật kho trượt nếu kho không khớp kỳ vọng.
- Tiêu đề đã có trong bộ dữ liệu không bị luật tiền tố xét. Chỉ tiêu đề mà lượt này gửi trong `create_plan` hoặc `add_subtask` mới bị xét.
- `ngày 2:`, `Tuần 3:`, `Bước 4`, và `giai đoạn 2:` cũng trượt luật tiền tố. So khớp không phân biệt hoa thường.
- Ca ghi được gọi `get_plans` và `get_plan_detail` trước đúng tool ghi của nhóm. Tool ghi của nhóm khác, như `set_subtask_note` ở ca cập nhật trạng thái, làm luật đúng tool trượt. `create_plan` trong ca ghi vẫn làm luật số lần `create_plan` trượt.
- Ca xem chi tiết được gọi `get_plans` trước `get_plan_detail` vì danh tính vừa được cấp lúc dựng kho. Chỉ gọi `get_plans` thì chưa đạt.
- Dòng log tool có đầu vào không phải object làm luật tham số bắt buộc của lần đó trượt.
- Token trống trên dòng log được cộng như 0. Token của lần lỗi chạy vẫn vào tổng.
- Không có dòng log mô hình nào thì nhãn phiên bản và model trên tên file là `trong`, và file vẫn được ghi nếu không vướng lỗi định dạng.
- Hai lần chạy cùng phiên bản, cùng model, cùng ngày không ghi đè file đã có.
- Giá trị khóa không rỗng và không chỉ khoảng trắng, nếu xuất hiện trong câu trả lời hoặc trong dòng log, bị thay trước khi ghi file. File đã ghi không chứa giá trị đó. Khóa rỗng hoặc chỉ khoảng trắng không được giấu theo cách đó: lệnh tay đã dừng trước khi ghi.
- Luật điểm kết thúc đo được để trống không làm đổi tỉ lệ tự động.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bộ câu MUST có số phiên bản nguyên. Mỗi câu MUST có id riêng trong bộ, đúng một nhóm trong mười nhóm ở Assumptions, câu người dùng, tên bộ dữ liệu, và kỳ vọng. Tên bộ dữ liệu MAY rỗng.
- **FR-002**: Kỳ vọng MUST khớp nhóm. Bốn nhóm không gọi tool MUST kỳ vọng không có lần gọi tool. Nhóm nhờ lập kế hoạch MUST kỳ vọng đúng một lần `create_plan` và không có tool khác. Nhóm hỏi danh sách MUST kỳ vọng mọi lần gọi tool đều là `get_plans` và có ít nhất một lần. Nhóm xem chi tiết MUST kỳ vọng có ít nhất một `get_plan_detail`, mọi lần gọi khác chỉ được là `get_plans`, và không có tool ghi. Ba nhóm ghi MUST có luật đúng tool: mọi lần gọi tool chỉ được là `get_plans`, `get_plan_detail`, hoặc đúng tool ghi của nhóm. Nhóm cập nhật trạng thái dùng `update_subtask`. Nhóm thêm việc con dùng `add_subtask`. Nhóm ghi chú dùng `set_subtask_note`. Ba nhóm ghi MUST đồng thời kỳ vọng kết quả kho ở FR-005. Bộ câu lệch các quy tắc này MUST bị từ chối trước lượt đầu.
- **FR-003**: Một bộ dữ liệu MUST có tên riêng và danh sách kế hoạch. Mỗi kế hoạch MUST có mục tiêu và danh sách việc con theo thứ tự. Mỗi việc con MUST có tiêu đề, trạng thái `pending`, `done`, hoặc `skipped`, và ghi chú. Mục tiêu MUST riêng trong bộ dữ liệu. Tiêu đề MUST riêng trong một kế hoạch. Tên rỗng MUST nghĩa là không có kế hoạch và MUST NOT cần một bản ghi bộ dữ liệu.
- **FR-004**: Mỗi lần chạy một câu MUST dựng kho mới từ đúng bộ dữ liệu của câu, rồi chạy một lượt với lịch sử rỗng. Lần chạy MUST NOT dùng kho hoặc lịch sử của lần khác. Lượt MUST là lượt hiện có, không một lối chấm khác.
- **FR-005**: Luật kho MUST chỉ áp vào ba nhóm ghi, và MUST so kho sau lượt với kỳ vọng. Ca cập nhật đạt khi việc con chỉ bởi mục tiêu và tiêu đề có đúng trạng thái kỳ vọng. Ca thêm việc đạt khi kế hoạch chỉ bởi mục tiêu có một việc con mang tiêu đề kỳ vọng mà bộ dữ liệu chưa có. Ca ghi chú đạt khi việc con đó có đúng ghi chú kỳ vọng; ghi chú kỳ vọng rỗng hoặc chỉ khoảng trắng MUST nghĩa là việc không còn ghi chú, cùng nghĩa với [spec ghi chú](../005-subtask-skip-note/spec.md). Việc con và kế hoạch không được nêu trong kỳ vọng MUST NOT làm đổi kết quả luật này.
- **FR-006**: Mỗi lần được chấm MUST có sáu luật tự động: đúng tool theo FR-002, số lần `create_plan`, tham số bắt buộc, tiền tố tiêu đề, Markdown, và tự xưng. Với ba nhóm ghi, luật đúng tool MUST đạt khi mọi lần gọi tool chỉ là `get_plans`, `get_plan_detail`, hoặc đúng tool ghi của nhóm ở FR-002, và MUST được xét riêng với luật kho. Một ca cập nhật trạng thái có `set_subtask_note` MUST làm luật đúng tool trượt. Số lần `create_plan` MUST là 1 với nhóm nhờ lập kế hoạch và MUST là 0 với mọi nhóm khác, kể cả nhóm ghi. Luật kho của FR-005 MUST là luật thứ bảy, chỉ được xét trên nhóm ghi. Một lần đạt MUST là lần mọi luật được xét đều đạt.
- **FR-007**: Luật tham số bắt buộc MUST xét từng lần gọi tool trong dòng log tool. Với tool có tên trong bộ định nghĩa, đầu vào MUST là object và MUST có đủ các trường bắt buộc của bộ định nghĩa đó. Thiếu trường, đầu vào không phải object, hoặc tên tool không có trong bộ định nghĩa MUST làm luật này trượt. Không có lần gọi tool MUST làm luật này đạt. Trường không bắt buộc MAY vắng.
- **FR-008**: Luật tiền tố MUST xét từng tiêu đề mà lượt gửi trong `subtasks` của `create_plan` và trong `title` của `add_subtask`. So khớp MUST không phân biệt hoa thường. Tiêu đề MUST trượt khi, sau khi bỏ khoảng trắng đầu, nó bắt đầu bằng `Ngày`, `Tuần`, `Bước`, hoặc `Giai đoạn`, rồi khoảng trắng tùy chọn, rồi một số nguyên, kể cả khi sau số là `:`. Tiêu đề MUST trượt khi nó bắt đầu bằng một số nguyên rồi dấu chấm. Các tiêu đề `Ngày 1:`, `ngày 1:`, `Tuần 1:`, `1.`, `Bước 1`, và `Giai đoạn 2:` MUST trượt. Tiêu đề đã có trong bộ dữ liệu MUST NOT bị xét. Không có tiêu đề mới MUST làm luật này đạt.
- **FR-009**: Luật Markdown MUST chỉ xét câu trả lời của lượt. Câu trả lời MUST trượt khi có ít nhất một trong các dấu: ba dấu backtick, một dấu backtick, `**`, `__`, `](`, một dòng có ký tự khác khoảng trắng đầu tiên là `#`, hoặc một dòng mà sau khoảng trắng đầu thì bắt đầu bằng `*` rồi một khoảng trắng. Dòng đánh số, và dòng mà sau khoảng trắng đầu thì bắt đầu bằng `-` hoặc `+` rồi một khoảng trắng, MUST NOT làm luật này trượt. Câu trả lời có dòng `1. Chạy 2km` và dòng `- Nộp báo cáo`, và không có các dấu bị cấm, MUST đạt. Câu trả lời không có các dấu bị cấm MUST đạt.
- **FR-010**: Luật tự xưng MUST trượt khi câu trả lời chứa đúng cụm `trợ lý lập kế hoạch`. Câu trả lời không chứa cụm đó MUST đạt. Lời hướng dẫn hệ thống MUST NOT bị xét bởi luật này.
- **FR-011**: Luật điểm kết thúc đo được MUST NOT nằm trong tỉ lệ tự động. File kết quả MUST có một chỗ đánh dấu cho từng tiêu đề bị luật tiền tố xét. Mỗi chỗ MUST là đạt, trượt, hoặc để trống, và MUST bắt đầu là để trống. Đổi chỗ đánh dấu MUST NOT đổi tỉ lệ tự động.
- **FR-012**: Mỗi câu trong một lần chạy cả bộ mà không bị dừng sớm MUST được chạy đúng ba lần. MUST NOT nhận loại lần bằng cách so câu trả lời. Lượt kết thúc bình thường khi dòng log cuối là dòng tám khóa có `error_type` là `null` và `stop_reason` thuộc tập kết thúc hợp lệ. Tập đó, lấy từ nhánh `_finish` trả `response.text`, chỉ có `end_turn`. Lượt cũng kết thúc bình thường khi dòng log cuối là hết lượt tool: dòng tám khóa có `stop_reason` là `tool_use`, `error_type` là `null`, và trước dòng đó đã có đúng ba vòng tool. Mọi trường hợp khác MUST là lỗi chạy và MUST có đúng một mã trong file kết quả: `missing_key` khi ném `MissingKeyError`; `no_model_log` khi không có dòng tám khóa và không phải `missing_key`; `ended_on_tool_log` khi dòng log cuối là dòng bảy khóa; `model_error` khi dòng log cuối là dòng tám khóa có `error_type` khác `null`; `bad_stop_reason` khi dòng log cuối là dòng tám khóa, `error_type` là `null`, và `stop_reason` không thuộc tập cũng không phải hết lượt tool. MUST NOT nhận hết lượt tool bằng cách so câu trả lời. Hết lượt tool MUST NOT là lỗi chạy. Lỗi chạy MUST NOT tính là trượt luật và MUST NOT nằm trong mẫu số tỉ lệ hành vi. Một lỗi chạy MUST NOT ngăn lần khác của câu đó hoặc câu sau. Ctrl+C ở lệnh tay MUST dừng cả bộ, MUST NOT chạy lần nào tiếp theo, và MUST NOT ghi file kết quả. Hủy MUST NOT được ghi là lỗi chạy của một lần.
- **FR-013**: Báo cáo của một lần chạy cả bộ MUST có tỉ lệ đạt của từng câu trên số lần được chấm của câu đó, tỉ lệ của từng luật trên số lần luật đó được xét, và tỉ lệ của từng nhóm trên số lần được chấm trong nhóm. Câu mà cả ba lần đều lỗi chạy MUST có tỉ lệ để trống và MUST có số lỗi chạy là 3. Báo cáo MUST đếm số lần hết lượt tool theo từng câu và theo từng nhóm. Số đếm đó MUST đứng riêng, MUST NOT thay cho tỉ lệ đạt, và lần hết lượt tool đã được chấm MUST vẫn nằm trong tỉ lệ. Báo cáo MUST có tổng token đầu vào và tổng token đầu ra.
- **FR-014**: Hai tổng token MUST là tổng các số `input_tokens` và `output_tokens` trên mọi dòng log mô hình của lần chạy cả bộ, kể cả lần lỗi chạy. Giá trị trống MUST được cộng như 0. Nguồn số MUST là dòng log tám khóa của lượt, không phải một bộ đếm khác.
- **FR-015**: Mỗi lần chạy cả bộ đi tới hết MUST ghi đúng một file kết quả mới. Tên file MUST chứa phiên bản lời hướng dẫn, phiên bản bộ định nghĩa, model, và ngày dạng `YYYY-MM-DD`. File đã có MUST NOT bị ghi đè. Nội dung MUST gồm số phiên bản bộ câu, số lần hết lượt tool theo FR-013, và với từng lần: câu trả lời, các dòng log, số vòng tool, và kết quả từng luật. Số vòng tool MUST là số đợt tool mà lượt đã chạy, cùng nghĩa vòng ở spec lượt. Lệnh chạy MUST NOT tự commit. Ctrl+C và lần dừng vì khóa ở FR-017 MUST NOT ghi file.
- **FR-016**: Phiên bản lời hướng dẫn, phiên bản bộ định nghĩa, và model trên file MUST lấy từ dòng log mô hình của lần chạy. Khi mọi dòng đó cùng một bộ ba giá trị, tên file MUST dùng bộ ba đó. Khi chúng khác nhau, tên file MUST dùng `lech` cho phần lệch và nội dung MUST giữ giá trị từng dòng. Khi không có dòng log mô hình nào, tên file MUST dùng `trong` cho ba nhãn đó.
- **FR-017**: Không file nào của lát này MUST chứa giá trị khóa không rỗng. Lệnh tay MUST kiểm khóa trước lượt đầu. Khóa không được đưa, khóa rỗng, hoặc khóa chỉ gồm khoảng trắng MUST làm lệnh dừng ngay với đúng một câu báo, MUST NOT chạy lượt nào, và MUST NOT ghi file. Việc giấu khóa MUST chỉ áp cho khóa không rỗng và không chỉ khoảng trắng: trước khi ghi, giá trị khóa đó MUST được thay bằng đúng cụm `đã giấu khóa` ở câu trả lời và ở dòng log. Dòng log tám khóa và bảy khóa MUST NOT bị thêm hoặc bớt khóa. Lệnh tay MUST nhận khóa từ người gọi và MUST NOT đọc khóa từ một file trong repo. `MissingKeyError` ở phần chấm và ở bộ test thường MUST vẫn là lỗi chạy của lần đó theo FR-012.
- **FR-018**: Phần đọc bộ câu, dựng kho, chấm, và tổng hợp MUST chạy được trong bộ test thường bằng phản hồi mô hình ghi sẵn và MUST NOT mở mạng. Mỗi luật ở FR-006 và FR-008 đến FR-010 MUST có ít nhất một ca đạt và một ca trượt trong bộ test đó. Lần chạy cả bộ câu v1 với mô hình thật MUST là một lệnh tay và MUST NOT nằm trong bộ test thường.
- **FR-019**: Lát này MUST NOT sửa lời hướng dẫn, bộ định nghĩa tool, lượt, adapter, các tool, hay `docs/PRODUCT.md`. Lát này MUST NOT dùng một mô hình để chấm. Lát này MUST NOT chạy hội thoại nhiều lượt, Telegram, hay Worker.

### Key Entities

- **Bộ câu**: Một tập câu có số phiên bản. Bộ v1 khoảng 50 câu tiếng Việt, nguyên văn được đưa ở bước implement, không nằm trong spec này.
- **Câu đánh giá**: Id, nhóm, câu người dùng, tên bộ dữ liệu, và kỳ vọng. Không có lịch sử.
- **Bộ dữ liệu kho**: Tên, các kế hoạch, và việc con dùng để dựng kho đầu mỗi lần chạy.
- **Lần chạy**: Một lượt trên một kho mới và lịch sử rỗng. Cho ra câu trả lời, các dòng log, số vòng tool, và kết quả luật, hoặc một lỗi chạy.
- **Báo cáo**: Tỉ lệ theo câu, theo luật, theo nhóm, số lần hết lượt tool theo câu và theo nhóm, số lỗi chạy, và hai tổng token.
- **File kết quả**: Bản ghi của một lần chạy cả bộ, đủ để commit làm đường cơ sở và để so với lần chạy sau. Không chứa giá trị khóa.
- **Chỗ đánh dấu tay**: Một ô trên từng tiêu đề việc con mà lượt đã gửi, ngoài tỉ lệ tự động.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% bộ câu đúng định dạng được đọc thành câu và bộ dữ liệu. 100% bộ sai định dạng bị từ chối trước lượt đầu.
- **SC-002**: 100% lần chạy dựng kho mới từ bộ dữ liệu của câu và dùng lịch sử rỗng. 0 lần chạy dùng lại kho đã bị lần trước sửa.
- **SC-003**: 100% luật tự động có ít nhất một ca đạt và một ca trượt trong bộ test thường. 100% ca đó chạy từ phản hồi ghi sẵn và không mở mạng.
- **SC-004**: 100% ca ghi được xét bằng kho sau lượt. 100% ca cập nhật trạng thái có `set_subtask_note` làm luật đúng tool trượt. 100% ca xem chi tiết chỉ đạt khi có `get_plan_detail`. 100% ca nhờ lập kế hoạch chỉ đạt luật tool khi đúng một `create_plan` và không có tool khác.
- **SC-005**: 100% lần thuộc năm mã của FR-012 được ghi đúng mã đó, không vào mẫu số tỉ lệ, và không dừng các lần còn lại của phần chấm. 0 lần được nhận là lỗi chạy chỉ vì câu trả lời. 100% lần `end_turn` với `error_type` là `null`, và 100% lần hết lượt tool, vẫn được chấm luật. Lần hết lượt tool được đếm riêng. 100% Ctrl+C ở lệnh tay dừng cả bộ và không ghi file.
- **SC-006**: 100% lần chạy cả bộ cho ra đủ tỉ lệ theo câu, theo luật, và theo nhóm, số lần hết lượt tool theo câu và theo nhóm đứng riêng khỏi tỉ lệ, cùng hai tổng token khớp tổng số trên các dòng log mô hình.
- **SC-007**: 100% lần chạy cả bộ đi tới hết tạo một file kết quả mới, không ghi đè file cũ, mang đủ bốn nhãn phiên bản lời hướng dẫn, phiên bản bộ định nghĩa, model, và ngày. 0 file chứa giá trị khóa không rỗng. 0 lần Ctrl+C hoặc khóa rỗng ghi file.
- **SC-008**: 100% tiêu đề mà lượt gửi có một chỗ đánh dấu tay bắt đầu ở trạng thái để trống. 0 lần đổi chỗ đánh dấu làm đổi tỉ lệ tự động.
- **SC-009**: 100% ca của bộ test thường không gọi mô hình thật. Lệnh tay là đường duy nhất chạy bộ câu v1 với mô hình thật.

## Assumptions

- Người giữ là người đọc báo cáo và commit file đường cơ sở. Lệnh chạy không tự commit, đúng cách làm của repo: người giữ tự commit.
- Mười nhóm, đúng chữ: `nhờ lập kế hoạch`, `chỉ kể việc`, `hỏi danh sách`, `xem chi tiết`, `cập nhật trạng thái việc con`, `thêm việc con`, `ghi chú`, `chào hỏi`, `câu mơ hồ`, `câu ngoài phạm vi`. Bốn nhóm không gọi tool là `chỉ kể việc`, `chào hỏi`, `câu mơ hồ`, và `câu ngoài phạm vi`.
- Bộ câu v1 có khoảng 50 câu, phủ mười nhóm, viết bằng tiếng Việt. Spec không chia số câu mỗi nhóm và không viết sẵn câu. Bước implement nhận nguyên văn.
- Bộ test thường dùng bộ câu tối thiểu đủ để mỗi luật có ca đạt và ca trượt. Bộ tối thiểu đó không phải bộ v1.
- Ca xem chi tiết được phép `get_plans` trước `get_plan_detail` vì mỗi lần dựng kho cấp danh tính mới. Ca ghi được phép hai tool đọc đó, và chỉ được thêm đúng tool ghi của nhóm. Ca hỏi danh sách không được gọi tool khác `get_plans`.
- Kỳ vọng ca ghi chỉ đúng việc bằng mục tiêu cộng tiêu đề. Không chấm các việc không được nêu. Trạng thái kỳ vọng là `pending`, `done`, hoặc `skipped`.
- Ghi chú rỗng sau chuẩn hóa nghĩa là không còn ghi chú, theo spec ghi chú. Kỳ vọng ghi chú so với ghi chú đang lưu sau lượt.
- Số lần `create_plan` đếm trên dòng log tool có tên `create_plan`. Luật này tách khỏi luật đúng tool vì mô tả tính năng nêu cả hai.
- So khớp tiền tố không phân biệt hoa thường. `Ngày`, `Tuần`, `Bước`, và `Giai đoạn` cùng một mẫu. `ngày 1:` và `Giai đoạn 2:` trượt. Tiêu đề `Nộp báo cáo thứ Sáu` không trượt. Tiền tố số rồi dấu chấm vẫn trượt trên tiêu đề việc con, và không còn làm câu trả lời trượt luật Markdown.
- Bộ dấu Markdown ở FR-009 là định nghĩa "có Markdown" của lát này. Dòng đánh số `1.`, `2.` và dòng bắt đầu bằng `-` hoặc `+` rồi khoảng trắng là chữ trơn: câu trả lời được liệt kê việc bằng số, và câu gửi đi không có parse mode nên gạch đầu dòng vẫn là chữ. Dấu nằm trong câu trả lời mới bị xét.
- Lỗi chạy không nhận bằng câu chữ. Năm mã trong file kết quả là `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, và `bad_stop_reason`, đúng FR-012. Hết ngân sách trước lời gọi mô hình là `no_model_log`. Hết ngân sách khi dòng log cuối là dòng bảy khóa là `ended_on_tool_log`. `max_tokens` là `bad_stop_reason`. `end_turn` với `error_type` là `null` được chấm. Hết lượt tool không phải lỗi chạy. Hủy ở lệnh tay dừng cả bộ và không ghi file.
- Dòng log mô hình giữ đúng tám khóa, theo thứ tự: `model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`. Dòng log tool giữ đúng bảy khóa D-014: `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`. Lát này không thêm khóa, không bớt khóa, không đổi nghĩa.
- `prompt_version` và `definitions_version` trên file lấy từ các dòng đó. Lời hướng dẫn phiên bản 1 và bộ định nghĩa phiên bản 1 là đường cơ sở mong đợi của lần chạy tay đầu, không phải giá trị spec bịa thêm khi dòng log thiếu.
- Một vòng tool là một đợt tool của lượt, đúng spec lượt: một phản hồi mô hình có đòi tool và đã được chạy. Phản hồi thứ tư còn đòi tool nhưng không chạy tool thì không tính thêm một vòng.
- Ngày trên tên file là ngày lịch của lần chạy, dạng `YYYY-MM-DD`. Chỗ đặt thư mục file do plan chốt. Tên file phải đủ bốn nhãn để nhận ra đường cơ sở.
- Cụm thay khóa là `đã giấu khóa`. Việc giấu chỉ áp cho khóa không rỗng và không chỉ khoảng trắng. Lệnh tay gặp khóa rỗng hoặc chỉ khoảng trắng thì dừng trước lượt đầu, một câu báo, không file.
- Chi phí một lượt khoảng 0,0002 đến 0,0009 USD và cả bộ 150 lượt dưới 0,15 USD là bối cảnh của lần chạy tay, không phải một ca của bộ test thường.
- Prompt v1 đóng băng trong lát này. Lần chạy tay đầu được mong đợi trượt luật tiền tố kiểu `Ngày 1:` và luật Markdown. Sự mong đợi đó không phải một ca test bắt buộc mô hình thật phải trượt, vì mô hình thật không nằm trong bộ test thường.
- Ngoài phạm vi, theo mô tả tính năng:
  - Sửa lời hướng dẫn, bộ định nghĩa tool, lượt, adapter, các tool, và `docs/PRODUCT.md`.
  - Tự viết nội dung bộ câu v1 trong spec hoặc trong lúc specify.
  - Dùng mô hình để chấm, hội thoại nhiều lượt, Telegram, và Worker.
  - Đổi tám khóa dòng log mô hình hoặc bảy khóa dòng log tool.
  - Tự commit file kết quả.
  - Chấm luật điểm kết thúc đo được bằng quy tắc tự động.
