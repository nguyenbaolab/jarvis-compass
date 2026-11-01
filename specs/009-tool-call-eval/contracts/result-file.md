# Contract: File kết quả

Hàm ghi trong `evals/result.py` nhận thư mục ra và ngày là hai tham số bắt buộc, không có giá trị mặc định. Hàm không gọi `date.today()`. Mỗi lần chạy cả bộ đi tới hết ghi đúng một file mới trong thư mục được truyền. Không ghi đè. Ctrl+C và khóa bị từ chối không ghi file. Test truyền `tmp_path` và một ngày cố định. Chỉ `main` trong `evals/runner.py` gọi `date.today()` và truyền `evals/results/`.

Tên: `p<prompt_version>-d<definitions_version>-<model>-<YYYY-MM-DD>.json`.

Ba nhãn lấy từ dòng tám khóa của lần chạy. Mọi dòng cùng một bộ ba thì dùng bộ ba đó. Lệch thì phần lệch là `lech` và thân file giữ giá trị từng dòng. Không có dòng tám khóa nào thì ba nhãn là `trong`. Ngày trong tên là giá trị tham số, dạng `YYYY-MM-DD`. Model chỉ giữ chữ, số, dấu chấm, dấu gạch ngang; ký tự khác thành `-`. File đã có thì thêm `-2`, `-3`, ... trước `.json`.

Thân file là một object UTF-8, `ensure_ascii=False`:

- `cases_version`, `prompt_version`, `definitions_version`, `model`, `date`
- `input_tokens`, `output_tokens`
- `by_case`: id, group, tỉ lệ hoặc `null`, `run_errors`, `cap_stops`
- `by_rule`: tên luật, số đạt, số được xét
- `by_group`: nhóm, tỉ lệ hoặc `null`, `run_errors`, `cap_stops`
- `runs`: với từng lần, id câu, chỉ số lần `1` đến `3`, `kind` là một trong `scored`, `cap`, `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`, câu trả lời, mảng dòng log nguyên chuỗi, số vòng, kết quả bảy luật (`pass`, `fail`, hoặc `not_applicable` cho luật kho), và `manual_titles` là mảng `{title, mark}` với `mark` ban đầu `unmarked`

`cap_stops` không được dùng làm tử số hay mẫu số của tỉ lệ. Lần `kind` là `cap` vẫn là lần được chấm, nên vẫn nằm trong tỉ lệ và trong `by_rule`. `run_errors` đếm năm mã `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`. `kind` của lần đó là đúng mã ấy, không gộp thành một mã chung.

Trước khi ghi, nếu khóa không rỗng và không chỉ khoảng trắng, mọi chỗ xuất hiện đúng giá trị khóa trong câu trả lời và trong chuỗi dòng log được thay bằng `đã giấu khóa`. Không đổi số khóa JSON của dòng log: giấu bên trong giá trị chuỗi, không thêm trường. Khóa rỗng hoặc chỉ khoảng trắng không đi tới bước ghi.

File không chứa giá trị khóa không rỗng.
