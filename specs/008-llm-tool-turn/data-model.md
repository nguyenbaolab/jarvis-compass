# Data model: Lượt trả lời có gọi mô hình

Không có bảng mới. Không có trạng thái giữa hai request. Các kiểu dưới đây là kiểu trong bộ nhớ của một lần gọi.

Nguồn hành vi: [spec.md](./spec.md). Hình gọi: [contracts/model-port.md](./contracts/model-port.md), [contracts/llm-turn.md](./contracts/llm-turn.md).

## TextMessage

Tin người gọi đưa, hoặc tin văn bản lượt tự thêm cho lần gọi sau trong cùng lượt.

| Trường | Kiểu | Luật |
|--------|------|------|
| role | `user` hoặc `assistant` | Không có vai khác. |
| text | str | Được rỗng. Không phải khối tool. |

Lịch sử người gọi là một dãy `TextMessage`. Lượt không sửa dãy đó.

## ToolRequest

Một yêu cầu tool đã đủ, nằm trong phản hồi mô hình.

| Trường | Kiểu | Luật |
|--------|------|------|
| id | str | Id để gắn kết quả. |
| name | str | Tên đưa vào `execute_tool`. |
| tool_input | dict | Object đầu vào. Không phải chuỗi JSON dở. |

Chỉ xuất hiện khi `stop_reason` là `tool_use` và khối SDK đủ ba trường trên.

## ToolResultMessage

Kết quả một lần `execute_tool`, chỉ để gửi lại trong lần `complete` kế tiếp.

| Trường | Kiểu | Luật |
|--------|------|------|
| tool_use_id | str | Bằng `id` của yêu cầu. |
| output | str | Đúng `ToolResult.output`, không đổi chữ. |
| is_error | bool | Ngược với `ToolResult.success`. Không thay chữ của `output`. |

Không đưa kiểu này ra giá trị trả về của lượt và không gắn vào list lịch sử người gọi.

## ModelRequest

Đối số của một lần `complete`.

| Trường | Kiểu | Luật |
|--------|------|------|
| system | str | Đúng hằng `SYSTEM_PROMPT`. |
| messages | tuple TextMessage | Lịch sử người gọi theo thứ tự, rồi tin mới. |
| tools | chính object `TOOL_DEFINITIONS` | Không chép bộ thứ hai. |
| rounds | tuple các vòng đã chạy trong lượt | Mỗi vòng: các `ToolRequest` theo thứ tự phản hồi, rồi các `ToolResultMessage` cùng thứ tự. Rỗng ở lần gọi đầu. |

## ModelClient

Protocol của cổng.

| Trường | Kiểu | Luật |
|--------|------|------|
| model | str | Adapter đặt bằng `claude-haiku-5-5`. Dòng log của lần `complete` ném lỗi lấy giá trị này. |

## ModelResponse

Phản hồi cổng sau một lần `complete` thành công.

| Trường | Kiểu | Luật |
|--------|------|------|
| text | str | Phần văn bản. Được rỗng. |
| tool_requests | tuple ToolRequest | Rỗng khi không phải một vòng tool. |
| stop_reason | str hoặc trống | Giá trị SDK trả, hoặc trống khi không có. |
| input_tokens | int hoặc trống | Trống khi SDK không trả. |
| output_tokens | int hoặc trống | Trống khi SDK không trả. |
| model | str | Model của phản hồi. Dòng log của lần gọi thành công lấy giá trị này. |

## ModelError

Một exception của cổng. Không phải câu trả về cho người dùng.

| Trường | Kiểu | Luật |
|--------|------|------|
| class_name | str | Tên lớp exception của SDK. Không chứa thông điệp SDK, địa chỉ, mã trạng thái, hay khóa. |

`CancelledError` không đổi thành `ModelError`.

## Lượt

Không lưu. Đầu vào và đầu ra:

| Đầu | Nội dung |
|-----|----------|
| Vào | Tin mới, lịch sử văn bản, kho, khóa, client cổng, hàm log. |
| Ra thành công | Một str. Có thể rỗng. |
| Ra hết vòng | Đúng `Chưa trả lời xong yêu cầu này.` |
| Ra lỗi phía mô hình hoặc hết 20 giây | Đúng `Chưa liên lạc được để trả lời lúc này.` |
| Ra thiếu khóa | Exception, câu đúng `Thiếu ANTHROPIC_API_KEY.`, trước mọi `complete`. |

Ba câu đó khác nhau. Hai câu trả cho người gọi không chứa chữ `tool`. Câu thiếu khóa không chứa giá trị khóa.

## Vòng tool

Một `ModelResponse` có `stop_reason` `tool_use` và có ít nhất một `ToolRequest`. Tối đa ba vòng trong một lượt. Phản hồi thứ tư còn đòi tool không tạo `ToolResultMessage` và không tạo `ModelRequest` mới.

## Dòng log lần gọi mô hình

Một object JSON cho một lần `complete` đã kết thúc. Khóa theo thứ tự:

`model`, `prompt_version`, `definitions_version`, `stop_reason`, `input_tokens`, `output_tokens`, `duration_ms`, `error_type`.

`prompt_version` và `definitions_version` là số. `error_type` trống khi lần gọi thành công. Khi lỗi, `error_type` là `class_name`, không có thông điệp. `duration_ms` là số nguyên không âm, có thể bằng 0. Lần `complete` trả về thì `model` lấy từ `ModelResponse`. Lần `complete` ném lỗi thì `model` lấy từ `client.model`. Dòng tool vẫn đúng bảy khóa D-014. Hai loại dòng phân biệt bằng khóa `model` và khóa `tool`.

## Prompt

Một str và `PROMPT_VERSION: int = 1`. Không đọc từ file. Nguyên văn nằm ở [contracts/system-prompt.md](./contracts/system-prompt.md).
