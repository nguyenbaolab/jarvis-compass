# Feature Specification: Điều phối tool kế hoạch

**Feature Branch**: `007-plan-tool-router`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Lớp trung gian tool_router giữa LLM và sáu tool kế hoạch, cộng chỗ dựng kho từ cấu hình. Sáu tool và kho thật đã có nhưng chưa nối với nhau, và đầu vào từ mô hình chưa được kiểm. Đầu vào sai kiểu đang thoát thành lỗi thô của nền tảng (ví dụ tạo kế hoạch với một việc con rỗng trong danh sách, mở kế hoạch với danh tính là số), và lỗi miền từ kho không được đổi thành lỗi tool. Vòng sau sẽ nối mô hình vào lớp này; bộ đánh giá tool calling cần một dòng nhật ký mỗi lần gọi. Lớp nhận tên tool và đầu vào dạng object như mô hình gửi, chạy đúng tool với kho được truyền vào, trả nội dung để gửi lại mô hình và cờ lỗi. Tên không có, đầu vào thiếu trường, thừa trường, hoặc sai kiểu đều trả lỗi, không có lỗi nào thoát ra ngoài. Lỗi miền giữ nguyên câu. Lỗi không lường trước trả một câu chung, chi tiết chỉ trong nhật ký, không lộ secret. Mỗi lần gọi ghi đúng một dòng nhật ký. Định nghĩa sáu tool nằm một chỗ, có số phiên bản, và chính schema đó được dùng để kiểm đầu vào. Dựng kho thật từ nguồn cấu hình người gọi truyền vào; thiếu cấu hình thì báo lỗi trước mọi lời gọi mạng. Module kho thật được nạp cùng ứng dụng. Ngoài phạm vi: gọi mô hình, system prompt, khóa mô hình, route HTTP hay webhook, Telegram, lịch sử hội thoại, thử lại khi lỗi mạng, đổi hành vi sáu tool, đổi lược đồ kho."

## User Scenarios & Testing *(mandatory)*

Người gọi ở lát này là vòng sau sẽ nối mô hình, và bộ đánh giá mỗi lần gọi tool. Người dùng cuối không thấy tên lớp này. Sáu tool đã chốt ở [spec tạo và liệt kê](../001-create-list-plans/spec.md), [spec xem chi tiết](../002-get-plan-detail/spec.md), [spec cập nhật việc con](../003-update-subtask/spec.md), [spec thêm việc con](../004-add-subtask/spec.md), và [spec bỏ qua và ghi chú](../005-subtask-skip-note/spec.md). Kho thật đã chốt ở [spec lưu kế hoạch](../006-supabase-plan-store/spec.md). Lát này nối đầu vào của mô hình với sáu tool đó, và nối cấu hình với kho thật, không đổi kết quả thành công của tool.

### User Story 1 - Gọi đúng tool trên kho được đưa (Priority: P1)

Vòng gọi đưa tên một trong sáu tool, một object đầu vào hợp lệ, và một kho. Lớp chạy đúng tool đó trên đúng kho đó, rồi trả nội dung thành công mà tool đó đang trả hôm nay, cùng cờ báo đây không phải lỗi.

**Why this priority**: Không có đường gọi chung thì sáu tool và kho thật vẫn đứng riêng. Vòng mô hình sau này chỉ cần một chỗ để gọi.

**Independent Test**: Với kho trong bộ nhớ, gọi lần lượt sáu tên tool bằng đầu vào hợp lệ. So nội dung trả về với nội dung tool đó trả hôm nay trên cùng kho. Không cần mô hình, không cần kho thật.

**Acceptance Scenarios**:

1. **Given** kho trong bộ nhớ đang trống, **When** gọi `create_plan` với mục tiêu "Học tiếng Nhật" và hai việc con "Học hiragana", "Luyện 10 phút mỗi ngày", **Then** cờ lỗi tắt và nội dung là đúng nội dung thành công mà `create_plan` trả hôm nay. Kho nhận đúng kế hoạch đó.
2. **Given** kho đang có kế hoạch vừa tạo, **When** gọi `get_plans` với object rỗng, rồi gọi `get_plans` với từ khóa "tiếng", **Then** cả hai lần đều tắt cờ lỗi. Lần không từ khóa liệt kê mọi kế hoạch, mới hơn đứng trước. Lần có từ khóa chỉ giữ kế hoạch có mục tiêu khớp, đúng luật đã chốt.
3. **Given** một kế hoạch đã có danh tính, **When** gọi `get_plan_detail` với đúng danh tính dạng chuỗi, **Then** cờ lỗi tắt và nội dung là đúng kế hoạch đó, cùng nội dung `get_plan_detail` trả hôm nay.
4. **Given** kế hoạch đó có một việc con, **When** gọi `update_subtask` với trạng thái `done`, gọi `add_subtask` với tiêu đề "Mua giáo trình", và gọi `set_subtask_note` với ghi chú "Đợi giáo trình", **Then** mỗi lần tắt cờ lỗi và nội dung khớp kết quả thành công của đúng tool đó trên cùng kho.
5. **Given** người gọi đưa một kho, **When** một lần gọi thành công, **Then** chỉ kho đó bị đọc hoặc ghi. Lớp không dựng kho khác và không đọc khóa của mô hình.

---

### User Story 2 - Đầu vào của mô hình không làm vỡ lượt gọi (Priority: P1)

Mô hình có thể gửi tên lạ, thiếu trường, thừa trường, hoặc sai kiểu. Lượt gọi vẫn trả về một kết quả: cờ lỗi bật, nội dung là câu do dự án viết và có tên trường khi lỗi nằm ở trường. Không có lỗi nào thoát ra ngoài lớp này. Kho không bị gọi.

**Why this priority**: Hôm nay các đầu vào đó thoát thành lỗi thô. Vòng sau không có cách nào đưa câu đó lại cho mô hình.

**Independent Test**: Với từng tool, gửi một đầu vào sai kiểu và một đầu vào thiếu trường bắt buộc. Với `get_plans`, gửi từ khóa sai kiểu và một trường thừa. Thêm một tên tool không có, và một đầu vào không phải object. Mỗi lần chỉ được một kết quả lỗi.

**Acceptance Scenarios**:

1. **Given** bất kỳ kho nào, **When** gọi tên `revise_plan` hoặc một tên không có trong sáu tool, kể cả chuỗi rỗng, **Then** cờ lỗi bật, nội dung đúng là `Không có tool với tên này.`, và kho không bị gọi.
2. **Given** tên `create_plan`, **When** object thiếu `goal`, **Then** cờ lỗi bật, nội dung đúng là `Đầu vào thiếu trường goal.`, và kho không bị gọi.
3. **Given** tên `create_plan`, **When** `subtasks` là danh sách `["Học hiragana", null]`, **Then** cờ lỗi bật, nội dung đúng là `Một phần tử của trường subtasks sai kiểu.`, và kho không bị gọi.
4. **Given** tên `get_plan_detail`, **When** `plan_id` là số, **Then** cờ lỗi bật, nội dung đúng là `Trường plan_id sai kiểu.`, và kho không bị gọi.
5. **Given** tên `get_plans`, **When** object có thêm trường `limit`, **Then** cờ lỗi bật, nội dung đúng là `Đầu vào thừa trường limit.`, và kho không bị gọi.
6. **Given** tên `create_plan` viết đúng, **When** đầu vào là một danh sách, một chuỗi, một số, đúng/sai, hoặc null, **Then** cờ lỗi bật, nội dung đúng là `Đầu vào phải là một object.`, và kho không bị gọi.
7. **Given** tên `update_subtask` và object vừa thiếu `status` vừa có thêm trường `limit`, **When** gọi, **Then** chỉ một lỗi được trả. Nội dung đúng là `Đầu vào thừa trường limit.`, vì trường thừa được xét trước trường thiếu. Kho không bị gọi.
8. **Given** kho bất kỳ, **When** mỗi tool nhận đúng một ca tối thiểu sau, **Then** mỗi ca trả cờ lỗi bật, đúng câu của ca đó, không gọi kho, và không có lỗi nào thoát ra ngoài lớp này:
   - `create_plan` thiếu `goal` ra `Đầu vào thiếu trường goal.`; `subtasks` là `["Học hiragana", null]` ra `Một phần tử của trường subtasks sai kiểu.`
   - `get_plans` thêm trường `limit` ra `Đầu vào thừa trường limit.`; `keyword` là số ra `Trường keyword sai kiểu.`
   - `get_plan_detail` thiếu `plan_id` ra `Đầu vào thiếu trường plan_id.`; `plan_id` là số ra `Trường plan_id sai kiểu.`
   - `update_subtask` thiếu `status` ra `Đầu vào thiếu trường status.`; `status` là số ra `Trường status sai kiểu.`
   - `add_subtask` thiếu `title` ra `Đầu vào thiếu trường title.`; `title` là số ra `Trường title sai kiểu.`
   - `set_subtask_note` thiếu `note` ra `Đầu vào thiếu trường note.`; `note` là số ra `Trường note sai kiểu.`

---

### User Story 3 - Lỗi miền giữ câu, lỗi bất ngờ không lộ bí mật (Priority: P1)

Đầu vào đúng kiểu nhưng miền từ chối, hoặc kho báo lỗi miền, thì câu trả về là đúng câu miền đã có. Mất kết nối, cấu hình thiếu lúc đang gọi, hoặc lỗi lập trình thì người nhận chỉ thấy một câu chung. Chi tiết kỹ thuật và mọi secret chỉ được nằm trong nhật ký, và secret thì không nằm cả trong nhật ký.

**Why this priority**: Câu miền đã được các spec trước chốt. Đổi chữ làm bộ kiểm tra và mô hình hiểu sai. Lộ khóa trong câu trả về hoặc trong nhật ký là sự cố.

**Independent Test**: Gọi tool với chuỗi hợp lệ nhưng không có kế hoạch. Bảo kho giả ném đúng câu miền của trạng thái đã lưu không hợp lệ. Bảo kho giả ném lỗi mạng có nhét một khóa giả vào lời kỹ thuật. So câu trả về và dòng nhật ký.

**Acceptance Scenarios**:

1. **Given** kho không có kế hoạch nào, **When** `get_plan_detail` nhận `plan_id` là chuỗi `"khong-co"`, **Then** cờ lỗi bật và nội dung đúng là `Không có kế hoạch với danh tính này.`
2. **Given** một kế hoạch không có việc con với danh tính được hỏi, **When** `update_subtask` nhận đủ ba chuỗi và trạng thái `done`, **Then** cờ lỗi bật và nội dung đúng là `Kế hoạch này không có việc con với danh tính này.`
3. **Given** kho báo lỗi miền bằng đúng câu `Trạng thái việc con đã lưu không hợp lệ.`, **When** một tool đọc kế hoạch đó, **Then** cờ lỗi bật và nội dung đúng là câu đó, từng ký tự.
4. **Given** `create_plan` nhận `goal` là chuỗi rỗng, **When** gọi, **Then** đây là lỗi miền, không phải lỗi thiếu trường. Nội dung đúng là `Mục tiêu không được để trống.`
5. **Given** kho ném một lỗi không phải lỗi miền và lời kỹ thuật có chứa khóa giả `secret-key-value`, **When** gọi một tool hợp lệ, **Then** cờ lỗi bật, nội dung đúng là `Không thực hiện được yêu cầu này.`, và nội dung đó không chứa khóa giả, không chứa loại lỗi của nền tảng, và không chứa địa chỉ mạng. Không có lần gọi nào được thử lại.

---

### User Story 4 - Mỗi lần gọi có một dòng nhật ký cho bộ đánh giá (Priority: P1)

Mỗi lần gọi tool, đạt hay lỗi, ghi đúng một dòng nhật ký. Dòng đó đọc lại ra tên tool, đầu vào đã nhận, đạt hay lỗi, loại lỗi, thời gian xử lý bằng mili giây, và phiên bản bộ định nghĩa. Bộ đánh giá không cần mô hình thật để đọc dòng này.

**Why this priority**: Vòng sau chấm tool calling bằng các dòng này. Thiếu một lần, hoặc ghi hai dòng cho một lần, làm bộ đánh giá đếm sai.

**Independent Test**: Gọi một lần thành công, một lần tên lạ, một lần sai kiểu, một lần lỗi miền, và một lần lỗi bất ngờ. Mỗi lần bắt đúng một dòng, parse được, và các trường khớp lần gọi đó.

**Acceptance Scenarios**:

1. **Given** một lần gọi bất kỳ trong năm tình huống trên, **When** lần gọi kết thúc, **Then** có đúng một dòng nhật ký mới, dòng đó là một object đọc được, và không có dòng nhật ký thứ hai cho cùng lần gọi.
2. **Given** lần gọi `create_plan` thành công với mục tiêu "Học tiếng Nhật", **When** đọc dòng, **Then** `tool` là `create_plan`, `input` đọc lại đúng object đã gửi, `ok` là `true`, `error_type` là `null`, `duration_ms` là số nguyên không âm, `definitions_version` là phiên bản bộ định nghĩa đang dùng, và `detail` là `null`.
3. **Given** lần gọi tên lạ, đầu vào sai, hoặc lỗi miền, **When** đọc dòng, **Then** `ok` là `false` và `error_type` lần lượt là `unknown_tool`, `invalid_input`, hoặc `domain`. `detail` là `null`.
4. **Given** lần gọi gặp lỗi bất ngờ có lời kỹ thuật chứa khóa giả, **When** đọc dòng, **Then** `error_type` là `unexpected`, `detail` có mặt để người vận hành đọc, và cả dòng không chứa khóa giả đó.
5. **Given** đầu vào có chữ "Học tiếng Nhật", **When** đọc dòng, **Then** `input` đọc lại đúng từng ký tự đó.

---

### User Story 5 - Một bộ định nghĩa cho cả gửi mô hình và kiểm đầu vào (Priority: P1)

Sáu tool được mô tả một lần: tên, mô tả, và schema đầu vào, kèm một số phiên bản của cả bộ. Phần kiểm đầu vào dùng đúng schema đó. Không có bản schema thứ hai để hai bên lệch nhau.

**Why this priority**: Nếu schema gửi cho mô hình và schema dùng để kiểm là hai bản, mô hình sẽ bị từ chối bởi những trường chính bản kia cho là hợp lệ.

**Independent Test**: Đọc bộ định nghĩa một lần. Với mỗi tool, đối chiếu trường bắt buộc và kiểu với các ca ở User Story 2. Đổi không thuộc lát này; lát này chỉ cần một bộ, số phiên bản 1.

**Acceptance Scenarios**:

1. **Given** bộ định nghĩa, **When** liệt kê tool, **Then** đúng sáu tên `create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, `add_subtask`, và `set_subtask_note`. Mỗi tool có một mô tả không rỗng. Không có tool thứ bảy.
2. **Given** bộ định nghĩa, **When** xem phiên bản, **Then** phiên bản là `1`. Mọi dòng nhật ký của lát này ghi phiên bản `1`.
3. **Given** schema của `create_plan`, **When** đối chiếu với ca thiếu `goal` và ca `subtasks` chứa null, **Then** ca thiếu và ca sai kiểu đều do chính schema đó quyết định, không do một danh sách trường viết ở chỗ khác.

---

### User Story 6 - Dựng kho thật từ cấu hình người gọi, và nạp module kho cùng ứng dụng (Priority: P1)

Người gọi đưa một nguồn cấu hình, dạng bảng khóa hoặc môi trường của tiến trình chạy. Chỗ dựng trả về kho thật dùng đúng địa chỉ và khóa trong nguồn đó. Thiếu địa chỉ hoặc khóa thì lỗi cấu hình ngay, trước mọi lời gọi mạng. Khi ứng dụng được nạp, module kho thật được nạp cùng các phần ứng dụng khác, nên lỗi nạp lộ ra lúc nạp chứ không đợi lần gọi tool đầu tiên.

**Why this priority**: Tool đã nhận kho do người gọi truyền. Không có chỗ dựng thì kho thật vẫn không bao giờ được tạo từ cấu hình đang có. Không nạp module cùng ứng dụng thì một lỗi nạp trên môi trường chạy chỉ xuất hiện ở request đầu.

**Independent Test**: Dựng với nguồn thiếu từng giá trị và với nguồn đủ hai giá trị trong khi môi trường tiến trình không có hai giá trị đó. Nguồn thiếu không phát sinh lời gọi mạng. Khi kho local đang chạy, lưu rồi đọc lại qua kho vừa dựng. Nạp ứng dụng và xác nhận phần kho thật đã được nạp, không cần mô hình.

**Acceptance Scenarios**:

1. **Given** nguồn không có địa chỉ kho, hoặc địa chỉ rỗng, **When** dựng kho, **Then** việc dựng thất bại bằng đúng câu đã chốt ở [spec lưu kế hoạch](../006-supabase-plan-store/spec.md) FR-018 cho giá trị đang thiếu. Không có lời gọi mạng. Câu lỗi không chứa giá trị của khóa.
2. **Given** nguồn không có khóa, khóa rỗng, hoặc thiếu cả hai, **When** dựng kho, **Then** cùng luật FR-018 đó: nêu đúng từng giá trị đang thiếu, trước mọi lời gọi mạng, và không chứa giá trị của khóa.
3. **Given** nguồn có cả địa chỉ lẫn khóa khác rỗng, và môi trường của tiến trình không có hai giá trị đó, **When** dựng kho, **Then** việc dựng thành công và trả về kho thật. Kho đó dùng hai giá trị của nguồn người gọi, không lấy từ môi trường tiến trình. Việc dựng không phải một lần gọi tool, nên không ghi dòng nhật ký của tool.
4. **Given** kho local đang chạy và nguồn mang đúng địa chỉ cùng khóa của kho đó, **When** dựng kho rồi lưu một kế hoạch "Học tiếng Nhật" và đọc lại, **Then** đọc lại ra đúng kế hoạch vừa lưu. Khi kho local không chạy, riêng ca này được bỏ qua và lý do bỏ qua nói rõ kho không chạy.
5. **Given** ứng dụng được nạp, **When** việc nạp xong, **Then** phần kho thật đã được nạp cùng các phần ứng dụng khác. Lỗi nạp của phần đó xuất hiện ở lần nạp này. Lần nạp không cần địa chỉ, không cần khóa, và không gọi mạng.

---

### Edge Cases

- Tên tool phải khớp từng ký tự, gồm cả chữ hoa chữ thường. `Create_plan` là tên không có, nội dung `Không có tool với tên này.`
- Một lần gọi chỉ trả một lỗi đầu vào. Thứ tự xét: tên không có; đầu vào không phải object; trường thừa theo thứ tự khóa trong object, lấy khóa thừa đầu tiên; trường bắt buộc thiếu theo thứ tự trong schema; trường sai kiểu theo thứ tự trong schema. Với `subtasks`, giá trị không phải danh sách dùng câu `Trường subtasks sai kiểu.`; danh sách có phần tử không phải chuỗi dùng câu `Một phần tử của trường subtasks sai kiểu.` và chỉ xét phần tử sai đầu tiên.
- `null` là sai kiểu với mọi trường chuỗi và với `subtasks`. Không đưa `null` vào tool để đổi thành câu miền.
- Chuỗi rỗng hoặc chuỗi chỉ khoảng trắng là đúng kiểu. Tool hiện tại xử lý chúng và câu miền đã chốt được giữ nguyên. Ví dụ `goal` rỗng vẫn là `Mục tiêu không được để trống.` Trạng thái `DONE`, `Skipped`, hoặc `bỏ qua` vẫn là câu miền `Trạng thái việc con chỉ nhận pending, done hoặc skipped.`
- `get_plans` không có trường bắt buộc. Object rỗng là liệt kê hết, đúng hành vi đã chốt. Ca "thiếu trường" của tool này được thay bằng ca thừa trường. `keyword` bỏ qua là hợp lệ; `keyword` là số hoặc `null` là sai kiểu; `keyword` là chuỗi rỗng vẫn là không lọc.
- Trường bắt buộc của năm tool còn lại: `create_plan` cần `goal`, `subtasks` được bỏ qua; `get_plan_detail` cần `plan_id`; `update_subtask` cần `plan_id`, `subtask_id`, `status`; `add_subtask` cần `plan_id`, `title`; `set_subtask_note` cần `plan_id`, `subtask_id`, `note`. Bỏ qua `note` là thiếu trường, không phải xóa ghi chú. Chuỗi rỗng cho `note` vẫn đi vào tool và theo luật ghi chú đã chốt.
- Thứ tự trường trong schema: `create_plan` là `goal` rồi `subtasks`; `get_plans` là `keyword`; `get_plan_detail` là `plan_id`; `update_subtask` là `plan_id`, `subtask_id`, `status`; `add_subtask` là `plan_id`, `title`; `set_subtask_note` là `plan_id`, `subtask_id`, `note`.
- Lỗi miền gồm mọi câu đã chốt khi tool hoặc kho từ chối một đầu vào đúng kiểu, hoặc khi kho không có kế hoạch, không có việc con, hay đọc được trạng thái đã lưu không hợp lệ. Lớp này không viết lại các câu đó.
- Lỗi cấu hình lúc dựng kho không đi qua câu chung `Không thực hiện được yêu cầu này.` Dựng kho không phải một lần gọi tool.
- Nếu lỗi cấu hình hoặc lỗi mạng xảy ra giữa một lần gọi tool đã bắt đầu, lần gọi đó dùng câu chung, ghi loại `unexpected`, và không thử lại.
- `KeyboardInterrupt`, `SystemExit`, và `asyncio.CancelledError` là `BaseException`, không phải `Exception`. Chúng đi tiếp, không thành kết quả và không có dòng nhật ký.
- Dòng nhật ký không chứa giá trị khóa kho, khóa mô hình, hay token kênh nhắn. Đầu vào tool được ghi như đã nhận; các đầu vào này là nội dung kế hoạch, không phải những secret đó.
- Một lần gọi tool không thêm lời gọi mạng nào ngoài lời gọi mà chính tool đó đã thực hiện vào kho được truyền vào. Ca đầu vào sai và ca tên lạ không gọi kho.
- `revise_plan` chưa có trong sáu tool. Gọi tên đó là tên không có, không phải một tool mới.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Lớp điều phối MUST nhận tên tool, đầu vào, và kho do người gọi truyền vào, rồi chạy đúng một tool trong sáu tool trên đúng kho đó. Kết quả MUST luôn được trả về, gồm nội dung để gửi lại mô hình và một cờ lỗi. Ở đây "lỗi" là `Exception`. Không `Exception` nào MUST thoát ra ngoài lớp này. `BaseException` không phải `Exception`, gồm `KeyboardInterrupt`, `SystemExit`, và `asyncio.CancelledError`, MUST đi tiếp: không thành kết quả và không có dòng nhật ký.
- **FR-002**: Với đầu vào đúng schema, nội dung khi thành công MUST trùng nội dung thành công mà tool đó trả hôm nay trên cùng kho. Cờ lỗi MUST tắt. Hành vi ghi, lọc, chuẩn hóa, và câu từ chối của sáu tool MUST NOT đổi.
- **FR-003**: Tên không có trong sáu tool MUST trả cờ lỗi bật và đúng nội dung `Không có tool với tên này.` Kho MUST NOT bị gọi.
- **FR-004**: Đầu vào không phải object MUST trả cờ lỗi bật và đúng nội dung `Đầu vào phải là một object.` Kho MUST NOT bị gọi.
- **FR-005**: Object thiếu trường bắt buộc, có trường không có trong schema, hoặc có trường sai kiểu MUST trả cờ lỗi bật và đúng một câu nêu tên trường, theo các câu và thứ tự ở Edge Cases. Kho MUST NOT bị gọi. `null` MUST bị coi là sai kiểu, không được đưa xuống tool.
- **FR-006**: Mỗi tool trong năm tool có trường bắt buộc MUST có ít nhất một ca sai kiểu và một ca thiếu trường, cả hai trả kết quả lỗi theo FR-005 và không để lỗi thoát ra. `get_plans` MUST có một ca sai kiểu và một ca thừa trường thay cho ca thiếu trường, vì object rỗng MUST vẫn liệt kê hết.
- **FR-007**: Khi tool hoặc kho báo một lỗi miền đã chốt, lớp này MUST trả cờ lỗi bật và đúng câu đó, không đổi chữ. Các ca này gồm kế hoạch không có (`Không có kế hoạch với danh tính này.`), việc con không có (`Kế hoạch này không có việc con với danh tính này.`), và ràng buộc FR-011 của [spec lưu kế hoạch](../006-supabase-plan-store/spec.md) (`Trạng thái việc con đã lưu không hợp lệ.`), cùng mọi câu miền khác đã chốt ở spec của sáu tool.
- **FR-008**: Lỗi không lường trước trong một lần gọi, gồm mất kết nối, cấu hình thiếu lúc đang gọi, và lỗi lập trình, MUST trả cờ lỗi bật và đúng nội dung `Không thực hiện được yêu cầu này.` Nội dung đó MUST NOT chứa chi tiết kỹ thuật, loại lỗi của nền tảng, địa chỉ mạng, hay secret. Lớp này MUST NOT thử gọi lại.
- **FR-009**: Mỗi lần gọi tool kết thúc bằng kết quả MUST ghi đúng một dòng nhật ký dạng một object với đúng bảy khóa: `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, và `detail`. `BaseException` (`KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError`) đi tiếp, không thành kết quả và không có dòng nhật ký. `tool` là tên đã nhận. `input` là đầu vào đã nhận. `ok` là `true` khi lần gọi đạt và `false` khi lần gọi lỗi. Ở đây "lỗi" là `Exception`. `error_type` là `null` khi `ok` là `true`, và khi lỗi MUST là một trong `unknown_tool`, `invalid_input`, `domain`, `unexpected`. `duration_ms` là số nguyên mili giây không âm của cả lần gọi, làm tròn xuống. `definitions_version` là phiên bản bộ định nghĩa. `detail` là `null` trừ khi `error_type` là `unexpected`; khi đó `detail` là đúng tên lớp của exception, không có thông điệp. Đầu vào chữ tiếng Việt MUST đọc lại đúng từng ký tự.
- **FR-010**: Tên, mô tả, và schema đầu vào của sáu tool MUST nằm ở một bộ định nghĩa, với số phiên bản `1`. Phần kiểm đầu vào MUST dùng chính schema trong bộ đó. Phiên bản trong mọi dòng nhật ký MUST là phiên bản của bộ đó.
- **FR-011**: Schema MUST đúng biên đã nêu ở Edge Cases: trường bắt buộc, trường tùy chọn, kiểu chuỗi, và `subtasks` là danh sách chuỗi. Giá trị đúng kiểu nhưng miền từ chối MUST đi vào tool, để câu miền giữ nguyên.
- **FR-012**: Chỗ dựng kho MUST nhận nguồn cấu hình do người gọi truyền vào, bảng khóa hoặc môi trường của tiến trình chạy, và trả về kho thật dùng đúng địa chỉ và khóa của nguồn đó. Khi địa chỉ hoặc khóa không có hoặc rỗng, việc dựng MUST thất bại bằng đúng câu của [spec lưu kế hoạch](../006-supabase-plan-store/spec.md) FR-018, trước mọi lời gọi mạng, và câu lỗi MUST NOT chứa giá trị của khóa. Việc dựng MUST NOT ghi dòng nhật ký của tool và MUST NOT đọc khóa mô hình.
- **FR-013**: Khi ứng dụng được nạp, phần kho thật MUST được nạp cùng các phần ứng dụng khác. Lỗi nạp MUST lộ ra ở lần nạp đó. Lần nạp MUST NOT cần địa chỉ kho, MUST NOT cần khóa, và MUST NOT gọi mạng.
- **FR-014**: Lớp điều phối MUST nhận kho đã dựng. Lớp này MUST NOT tự tạo kho thật và MUST NOT làm miền phụ thuộc vào kho thật hay vào lớp tool. Chiều phụ thuộc đã chốt ở D-011 giữ nguyên.
- **FR-015**: Kỳ vọng của mọi kiểm tra hiện có MUST không đổi, gồm không sửa câu khẳng định của chúng. Khi kho local dùng cho kiểm tra đang chạy, toàn bộ kiểm tra MUST chạy với 0 lần bỏ qua. Kiểm tra lớp điều phối và kiểm tra thiếu cấu hình MUST chạy được bằng kho trong bộ nhớ hoặc không cần kho, không cần mô hình. Riêng ca dựng kho rồi đọc lại trên kho local MUST bỏ qua khi kho đó không chạy, với lý do nói rõ kho không chạy, và MUST chạy khi kho đó đang chạy.
- **FR-016**: Một lần gọi qua lớp này, không gồm lời gọi mô hình, MUST nằm trong ngân sách 3 giây của nguyên tắc VII cho phần mã của một lượt. Ca tên lạ và ca đầu vào sai MUST không gọi kho.

### Key Entities

- **Lần gọi tool**: Tên tool, đầu vào object, và kho được truyền vào. Một lần gọi cho đúng một kết quả và đúng một dòng nhật ký.
- **Kết quả lần gọi**: Nội dung để gửi lại mô hình, và cờ cho biết lần gọi có phải lỗi không. Khi lỗi, nội dung là câu tên lạ, câu đầu vào, câu miền giữ nguyên, hoặc câu chung.
- **Bộ định nghĩa tool**: Đúng sáu tool. Mỗi tool có tên, mô tả, và schema đầu vào. Cả bộ có số phiên bản.
- **Dòng nhật ký**: Một object cho một lần gọi, đúng bảy khóa ở FR-009. Không phải lịch sử hội thoại và không phải dữ liệu kế hoạch.
- **Nguồn cấu hình kho**: Địa chỉ và khóa do người gọi đưa, cùng nghĩa với spec lưu kế hoạch. Chỗ dựng đọc nguồn đó để tạo kho thật.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% lần gọi đúng tên và đúng schema trả nội dung trùng nội dung thành công hiện tại của đúng tool trên đúng kho được truyền vào, với cờ lỗi tắt.
- **SC-002**: 100% lần gọi tên không có trả đúng câu `Không có tool với tên này.` và không gọi kho.
- **SC-003**: 100% ca thiếu trường, thừa trường, và sai kiểu bắt buộc ở FR-006 trả đúng một câu nêu đúng trường, với cờ lỗi bật, không gọi kho, và không có lỗi nào thoát ra ngoài lớp điều phối.
- **SC-004**: 100% lỗi miền đi qua lớp này giữ nguyên từng ký tự của câu miền đã có, gồm ba câu được nêu ở FR-007.
- **SC-005**: 100% lỗi không lường trước trả đúng câu `Không thực hiện được yêu cầu này.` 0 nội dung trả về chứa secret, địa chỉ mạng, hoặc chi tiết kỹ thuật. 0 dòng nhật ký chứa secret.
- **SC-006**: 100% lần gọi trong kiểm tra sinh đúng một dòng nhật ký đọc được, đúng bảy khóa của FR-009, và giá trị các khóa khớp lần gọi đó. Đầu vào tiếng Việt đọc lại trùng từng ký tự.
- **SC-007**: Bộ định nghĩa có đúng sáu tool và phiên bản `1`. 100% lần kiểm đầu vào dùng schema của bộ đó. 100% dòng nhật ký ghi phiên bản `1`.
- **SC-008**: 100% lần dựng kho khi địa chỉ hoặc khóa không có hoặc rỗng thất bại trước mọi lời gọi mạng, bằng đúng câu FR-018 của spec lưu kế hoạch, và 0 câu lỗi chứa giá trị của khóa. Khi môi trường tiến trình không có địa chỉ và khóa, một nguồn người gọi đủ hai giá trị vẫn dựng được kho. Khi kho local đang chạy, lưu rồi đọc lại qua kho vừa dựng ra đúng kế hoạch đã lưu.
- **SC-009**: 100% lần nạp ứng dụng cũng nạp phần kho thật. Lỗi nạp của phần đó lộ ra ở lần nạp, trước lần gọi tool đầu tiên, và lần nạp không gọi mạng.
- **SC-010**: 100% kiểm tra hiện có giữ nguyên kỳ vọng. Khi kho local đang chạy, toàn bộ kiểm tra xong với 0 lần bỏ qua.
- **SC-011**: 100% lần gọi qua lớp này, đo riêng không gồm lời gọi mô hình, xong trong ngân sách 3 giây của nguyên tắc VII. 100% ca tên lạ và ca đầu vào sai không phát sinh lời gọi kho.

## Assumptions

- Sáu tool là `create_plan`, `get_plans`, `get_plan_detail`, `update_subtask`, `add_subtask`, và `set_subtask_note`, đúng F04 đến F08 trong [docs/PRODUCT.md](../../docs/PRODUCT.md). `revise_plan` (F09) chưa nằm trong lát này. Tên `tool_router` ở PRODUCT §8 là tool phía jarvis-desktop, không phải lớp này. Lớp này là bước điều phối đã được [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) §3 gọi khi mô hình cần một tool.
- Yêu cầu gốc nói câu tên lạ, câu đầu vào, và câu lỗi chung do dự án viết. Bốn câu được chốt trong spec này: `Không có tool với tên này.`, `Đầu vào phải là một object.`, `Đầu vào thiếu trường <tên>.` / `Đầu vào thừa trường <tên>.` / `Trường <tên> sai kiểu.` / `Một phần tử của trường subtasks sai kiểu.`, và `Không thực hiện được yêu cầu này.`
- `get_plans` không được thêm trường bắt buộc, vì bỏ từ khóa đang có nghĩa là liệt kê hết. Ca thiếu trường của tool này đổi thành ca thừa trường để khỏi đổi hành vi tool.
- `note` là trường bắt buộc trong schema. Muốn xóa ghi chú, người gọi vẫn gửi chuỗi rỗng hoặc chuỗi chỉ khoảng trắng và tool xử lý như spec ghi chú đã chốt. Không suy ra "xóa ghi chú" từ việc bỏ trường.
- Lỗi miền là lỗi mà tool hoặc kho đã báo bằng câu miền. Lỗi khác trong lúc gọi là lỗi không lường trước. Phân loại không dựa trên việc câu chữ có tình cờ giống nhau.
- Nhãn loại lỗi `unknown_tool`, `invalid_input`, `domain`, và `unexpected` là nhãn cho bộ đánh giá, không phải câu người dùng thấy. Câu người nhận thấy là nội dung tiếng Việt ở FR-003 đến FR-008. `error_type` và `detail` khi không có giá trị là `null`, không phải chuỗi rỗng.
- Kết quả lần gọi dùng mẫu đã chốt ở constitution: nội dung là phần chữ trả về, cờ lỗi bật khi lần gọi không thành công. Lớp này không thêm một kiểu kết quả khác. Sáu tool vẫn báo lỗi miền theo cách đang có; lớp này đổi lần báo đó thành kết quả có cờ lỗi, và không để lỗi thoát ra.
- Bảy khóa của dòng nhật ký được chốt trong FR-009 vì bộ đánh giá cần một dạng cố định. Tên khóa là `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, và `detail`.
- Thời gian trong `duration_ms` là số nguyên mili giây của cả lần gọi, gồm kiểm đầu vào và phần tool chạy. Làm tròn xuống. Không âm.
- Nhật ký dùng cách ghi một dòng mà nền đã có. Lát này không thêm thư viện ghi log. [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) §6 vẫn để việc chọn thư viện log riêng cho sau, nếu có.
- Secret cần loại khỏi nội dung trả về và khỏi dòng nhật ký là giá trị khóa kho, khóa mô hình, và token kênh nhắn. Nội dung kế hoạch trong đầu vào tool không phải secret và được ghi nguyên.
- Dựng kho dùng lại cách đọc `SUPABASE_URL` và `SUPABASE_KEY` từ nguồn người gọi, đã chốt ở spec lưu kế hoạch và ở cấu hình hiện có. Nguồn là bảng khóa hoặc đối tượng môi trường của tiến trình chạy. Không đọc biến môi trường của tiến trình khi người gọi đã đưa nguồn. Không đọc khóa mô hình.
- Kho thật là bản Supabase đã có. "Phần kho thật" trong FR-013 là module kho đó, được nạp cùng ứng dụng theo cùng cách các phần ứng dụng khác đang được nạp, đúng yêu cầu gốc. Kiểm tra lớp điều phối dùng kho trong bộ nhớ. Kiểm tra hợp đồng kho thật đã có sẵn và không bị đổi kỳ vọng. Ca dựng rồi đọc lại chỉ cần kho local và được bỏ qua khi kho đó tắt. Khi kho local tắt, các kiểm tra cần kho đó vẫn được bỏ qua theo spec lưu kế hoạch; yêu cầu 0 lần bỏ qua chỉ áp khi kho local đang chạy.
- Một lần gọi vẫn bất đồng bộ như tool và cổng kho đã chốt ở D-012. Lát này không thêm thư viện để chạy các lần gọi đó.
- Ngân sách cho phần có lời gọi mô hình không thuộc lát này. Lát này chỉ giữ phần mã của một lần gọi tool trong ngân sách 3 giây đã có.
- Ngoài phạm vi, theo mô tả tính năng:
  - Gọi mô hình, system prompt, và đọc khóa mô hình.
  - Route HTTP, webhook, và Telegram.
  - Lịch sử hội thoại và phiên làm việc.
  - Thử lại khi lỗi mạng.
  - Đổi hành vi của sáu tool, đổi câu miền đã chốt, hoặc đổi lược đồ kho.
  - `revise_plan`, check-in, và tên tool phía jarvis-desktop.
