# Data model: Bộ đánh giá gọi tool

Không có bảng DB. Mọi kiểu dưới đây là dữ liệu trong bộ nhớ hoặc file UTF-8. Nhóm là `StrEnum` mười giá trị, đúng chữ ở Assumptions của spec. Trạng thái việc con dùng lại `SubtaskStatus` trong `src/core/plans.py`. Không dùng Pydantic. Lý do ở [research.md](./research.md).

## Bộ câu

File `evals/cases/v1.json`. Một object:

| Trường | Kiểu | Luật |
|---|---|---|
| `cases_version` | số nguyên | Bắt buộc. Bộ v1 là `1`. |
| `cases` | mảng câu | Bắt buộc. Id không trùng. |

Nội dung `cases` của bộ v1 không nằm ở plan. Task implement "đưa bộ câu v1 nguyên văn" chờ người giữ đưa chữ. Trước đó test dùng file JSON tạm trong `tests/`, không viết câu vào `evals/cases/`.

## Câu

| Trường | Kiểu | Luật |
|---|---|---|
| `id` | chuỗi | Không rỗng sau NFC và strip. Duy nhất trong bộ. |
| `group` | một trong mười chữ của enum | Đúng nguyên chữ, sau NFC. |
| `user_message` | chuỗi | NFC khi đọc. |
| `dataset` | chuỗi | NFC. Rỗng sau strip nghĩa là không có bộ dữ liệu. |
| `expectation` | object | `kind` phải khớp nhóm. |

`kind` theo nhóm:

| Nhóm | `kind` | Trường thêm |
|---|---|---|
| chỉ kể việc, chào hỏi, câu mơ hồ, câu ngoài phạm vi | `no_tool` | không |
| nhờ lập kế hoạch | `one_create_plan` | không |
| hỏi danh sách | `read_plans` | không |
| xem chi tiết | `read_detail` | không |
| cập nhật trạng thái việc con | `update_status` | `goal`, `title`, `status` |
| thêm việc con | `add_subtask` | `goal`, `title` |
| ghi chú | `set_note` | `goal`, `title`, `note` |

`status` là `pending`, `done`, hoặc `skipped`, đưa vào `SubtaskStatus`. `note` là chuỗi. Chuỗi rỗng hoặc chỉ khoảng trắng sau NFC và strip nghĩa là không còn ghi chú, cùng `normalize_subtask_note`.

Ca `update_status` mà trạng thái kỳ vọng đã bằng bộ dữ liệu, ca `set_note` mà ghi chú kỳ vọng đã bằng bộ dữ liệu, hoặc ca `add_subtask` mà tiêu đề đã có trong kế hoạch đó: sai định dạng.

## Bộ dữ liệu kho

File `evals/datasets/<tên>.json`. `tên` là giá trị `dataset` của câu, sau NFC và strip. Không có đường dẫn, không có `/`.

| Trường | Kiểu | Luật |
|---|---|---|
| `name` | chuỗi | Bằng tên file, không tính `.json`. |
| `plans` | mảng kế hoạch | Thứ tự là thứ tự `add`. |

Kế hoạch: `goal` chuỗi, `subtasks` mảng. Việc con: `title` chuỗi, `status` một trong ba mã, `note` chuỗi hoặc JSON `null`. Mục tiêu không trùng trong một file. Tiêu đề không trùng trong một kế hoạch. Không có trường id. Id việc con do `new_subtask` cấp lúc dựng kho.

## Lần chạy

Một lần là một lời gọi `run_turn` với lịch sử rỗng và một `MemoryPlanStore` mới. Kết quả thuộc đúng một mã, theo thứ tự ở [contracts/scoring.md](./contracts/scoring.md):

| Mã | Vào tỉ lệ |
|---|---|
| `missing_key` | Không |
| `no_model_log` | Không |
| `ended_on_tool_log` | Không |
| `model_error` | Không |
| `cap` | Hết lượt tool. Có, và được đếm riêng |
| `scored` | Kết thúc bình thường, `stop_reason` là `end_turn`. Có |
| `bad_stop_reason` | Không |

Chi tiết trường log ở [contracts/scoring.md](./contracts/scoring.md).

## Báo cáo và file kết quả

Một lần chạy cả bộ tạo một object. Tỉ lệ là số lần đạt trên số lần được chấm. Lần lỗi chạy không vào mẫu số. Câu có cả ba lần lỗi chạy thì tỉ lệ câu đó là `null` và `run_errors` là `3`.

Số hết lượt tool là số lần, theo từng câu và từng nhóm. Số này không thay tỉ lệ.

Hai tổng token cộng mọi số `input_tokens` và `output_tokens` trên dòng tám khóa. Trống cộng `0`. Kể cả lần lỗi chạy.

File kết quả giữ thêm, với từng lần: câu trả lời đã giấu khóa, các dòng log đã giấu khóa, số vòng, kết quả từng luật, và chỗ đánh dấu tay. Chỗ đánh dấu bắt đầu là `unmarked`. Giá trị sau này người đọc ghi là `pass` hoặc `fail`. Đổi chỗ đó không đổi tỉ lệ.

Tên file và luật không ghi đè ở [contracts/result-file.md](./contracts/result-file.md).

## Luật chấm một lần được chấm

Bảy luật. Lần đạt khi mọi luật được xét đều đạt.

| Luật | Áp vào | Đạt khi |
|---|---|---|
| Đúng tool | Mọi lần được chấm | Đúng tập tên ở spec FR-002. Nhóm ghi: chỉ `get_plans`, `get_plan_detail`, và đúng một tool ghi của nhóm. Không gọi tool nào ở nhóm ghi vẫn đạt luật này. |
| Số lần `create_plan` | Mọi lần được chấm | `1` với nhờ lập kế hoạch, `0` với nhóm khác. Đếm dòng bảy khóa có `tool` là `create_plan`. |
| Tham số bắt buộc | Mọi lần được chấm | Mỗi dòng bảy khóa: tên có trong `TOOL_DEFINITIONS`, `input` là object, đủ khóa `required`. Không có dòng tool thì đạt. |
| Tiền tố | Mọi lần được chấm | Không tiêu đề mới nào trượt mẫu. Không có tiêu đề mới thì đạt. Chỉ đọc `subtasks` của `create_plan` và `title` của `add_subtask`. |
| Markdown | Mọi lần được chấm | Câu trả lời không có dấu bị cấm ở spec FR-009. Dòng `1. ` và dòng `- ` / `+ ` không trượt. |
| Tự xưng | Mọi lần được chấm | Câu trả lời sau NFC không chứa cụm `trợ lý lập kế hoạch` sau NFC. |
| Kho | Chỉ ba nhóm ghi | So kho sau lượt với kỳ vọng, sau NFC. Việc không được nêu không làm đổi kết quả. |

Chỗ đánh dấu tay không phải luật thứ tám của tỉ lệ.
