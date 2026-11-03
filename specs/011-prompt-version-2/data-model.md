# Data Model: Lời hướng dẫn hệ thống phiên bản 2

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Nguyên văn chuỗi: [plan.md](./plan.md) mục Nguyên văn SYSTEM_PROMPT. Chữ ký hằng và khẳng định test: [contracts/system-prompt.md](./contracts/system-prompt.md).

Lát này không thêm thực thể lưu, không thêm trường, và không đổi kiểu.

## Lời hướng dẫn

Không nằm trong kho. Hai tên đã có trong `src/core/system_prompt.py`:

| Tên | Kiểu | Giá trị |
|-----|------|---------|
| `PROMPT_VERSION` | `int` | `2` |
| `SYSTEM_PROMPT` | `str` | Nguyên văn ở [plan.md](./plan.md) |

Không có tên thứ ba. Chuỗi không được lắp từ file lúc chạy.

## Dòng nhật ký lần gọi mô hình

Đúng tám khóa đã chốt ở [spec lượt mô hình](../008-llm-tool-turn/spec.md). Lát này không thêm khóa và không đổi thứ tự.

| Khóa | Việc của lát này |
|------|------------------|
| `prompt_version` | Vẫn là số nguyên lấy từ `PROMPT_VERSION`. Giá trị thành `2` vì hằng thành `2`. |
| `definitions_version` | Vẫn là số nguyên `2` từ catalog. Catalog không sửa. |

Các khóa còn lại giữ nghĩa cũ.

## Việc con và kế hoạch

`Plan`, `Subtask`, và `SubtaskStatus` trong `src/core/plans.py` giữ trường và kiểu. Không thêm trường ngày. Ba mã trong kho vẫn là `pending`, `done`, `skipped`.

Ba chữ `chưa làm`, `xong`, `bỏ qua` chỉ là lời trong `SYSTEM_PROMPT` cho câu trả lời. Chúng không phải giá trị mới của `SubtaskStatus`, và không phải giá trị chuỗi bảo tool gửi đi.
