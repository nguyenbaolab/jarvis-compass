# Contract: Chấm từ dòng log và kho

Nguồn dòng tám khóa và dòng bảy khóa là log `run_turn` đã có. Eval không thêm khóa. Phân biệt hai dòng bằng khóa `model` và khóa `tool`, đúng spec lượt.

## Dòng code quyết định FR-012

Thiếu khóa, `src/turns/llm_turn.py:134-135`: `api_key is None or api_key == ""` thì `raise MissingKeyError()` trước vòng lặp. Không gọi `_model_log`. Không có `error_type`. Khóa chỉ khoảng trắng không vào nhánh này.

Hết ngân sách trước lời gọi mô hình, `src/turns/llm_turn.py:141-143`: `remaining <= 0` thì `return _MODEL_ERROR`. Không có dòng tám khóa.

`complete` ném, `src/turns/llm_turn.py:153-163`: `_model_log` với `stop_reason` là `None` và `error_type` là `_error_type(error)`. `_error_type`, dòng 41-46: `ModelError` thì `class_name`, exception khác thì `type(error).__name__`. Adapter, `src/clients/anthropic_model.py:44-45`, bọc mọi exception SDK thành `ModelError(type(error).__name__)`. `ModelError.class_name` là đối số đó, `src/core/llm.py:64-66`. Code không liệt kê tên lớp timeout. Plan không điền một tên lớp SDK.

`complete` trả được, `src/turns/llm_turn.py:164-172`: luôn `_model_log` với `stop_reason` là `response.stop_reason` và `error_type` là `None`, rồi mới `_finish`.

Phản hồi thứ tư còn đòi tool: `done` đã có ba phần tử vì `done.append` ở dòng 184 chỉ chạy sau khi tool chạy xong. `_finish`, dòng 116-117: `stop_reason == "tool_use"` và `done >= 3` thì trả câu hết lượt, không gọi `_run_tools`. Dòng tám khóa của phản hồi đó đã được ghi. `stop_reason` trên dòng đó là `tool_use` khi đi vào nhánh này. `error_type` là `None`.

Hết ngân sách giữa các tool, `src/turns/llm_turn.py:93-94`: trả câu lỗi, không thêm dòng tám khóa.

`_finish` dòng 120: `stop_reason` khác `end_turn` và không phải `tool_use` còn tool để chạy thì trả câu lỗi phía mô hình sau khi dòng log đã ghi `error_type` là `None`. Ví dụ `max_tokens`. Đó là `bad_stop_reason`.

Nguyên văn `_finish` và mọi `return` của `run_turn` nằm ở plan, mục FR-012. Tập `stop_reason` kết thúc hợp lệ chỉ có `end_turn`, vì đó là nhánh duy nhất trả `response.text`.

## Phân loại một lần

Không đọc câu trả lời. Xét đúng thứ tự này.

| Thứ tự | Điều kiện | Mã trong file kết quả | Chấm luật |
|---|---|---|---|
| 1 | Ném `MissingKeyError` | `missing_key` | Không |
| 2 | Không có dòng tám khóa | `no_model_log` | Không |
| 3 | Dòng log cuối là dòng bảy khóa | `ended_on_tool_log` | Không |
| 4 | Dòng cuối là dòng tám khóa và `error_type` khác JSON `null` | `model_error` | Không |
| 5 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `tool_use`, số vòng đã đếm trước dòng đó là 3 | hết lượt tool | Có |
| 6 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` là `end_turn` | kết thúc bình thường | Có |
| 7 | Dòng cuối là dòng tám khóa, `error_type` là `null`, `stop_reason` khác `end_turn` | `bad_stop_reason` | Không |

Năm mã lỗi chạy là `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`. Chuỗi `error_type` rỗng không xuất hiện trên đường ghi của code: trường đó là `null` hoặc một tên lớp. Coi khác `null` là `model_error`.

Hết ngân sách trước `complete` không có dòng tám khóa, nên là `no_model_log`. Hết ngân sách sau khi đã ghi ít nhất một dòng bảy khóa của vòng đang chạy làm dòng cuối thành dòng bảy khóa, nên là `ended_on_tool_log`. `max_tokens` là `bad_stop_reason`.

## Số vòng

Đi lần lượt các dòng.

- Dòng có khóa `model` là dòng tám khóa.
- Dòng có khóa `tool` là dòng bảy khóa.
- Một vòng là một dòng tám khóa có `stop_reason` bằng `tool_use`, và trước dòng tám khóa kế tiếp có ít nhất một dòng bảy khóa.
- Dòng `tool_use` không có dòng bảy khóa theo sau không cộng vòng.

Không có trường nào trên hai dòng log tên là số vòng. Suy ra từ `stop_reason` cộng sự có mặt của dòng bảy khóa phía sau.

## So chữ

Trước khi so tiêu đề, mục tiêu, ghi chú, tiền tố, và cụm tự xưng: NFC. Tiền tố còn `casefold` sau NFC. Tự xưng không `casefold`. Mẫu tiền tố, không phân biệt hoa thường sau bước đó: bắt đầu bằng `ngày`, `tuần`, `bước`, hoặc `giai đoạn`, khoảng trắng tùy chọn, rồi `[0-9]+`, rồi có thể `:`. Hoặc bắt đầu bằng `[0-9]+` rồi dấu chấm. `ngày 1:` và `giai đoạn 2:` trượt. Tiêu đề chỉ lấy từ đầu vào tool của lần này.

Markdown xét câu trả lời sau NFC. Dấu cấm là spec FR-009. Dòng đánh số và dòng `- ` / `+ ` không cấm.
