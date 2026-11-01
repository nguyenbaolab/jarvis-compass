# Research: Bộ đánh giá gọi tool của một lượt

## JSON cho bộ câu, bộ dữ liệu, và file kết quả

- **Decision**: Ba loại file là UTF-8 JSON, `json` của thư viện chuẩn, `ensure_ascii=False`. Thư mục: `evals/cases/v1.json`, `evals/datasets/<tên>.json`, `evals/results/`. Bộ câu v1 không có câu trong plan này.
- **Rationale**: Không thêm dependency. YAML cần thư viện mới. Một file câu giữ `cases_version`. Bộ dữ liệu tách file vì nhiều câu dùng chung một tên, và tên rỗng nghĩa là không có file. File kết quả là JSON để giữ dòng log đã parse và chỗ đánh dấu tay.
- **Alternatives considered**: Nhét bộ dữ liệu vào cùng file câu (một bộ dùng lại phải chép). Pydantic để parse (xem mục dưới).

## Không dùng Pydantic cho định dạng bộ câu

- **Decision**: Dataclass trong `evals/` và kiểm trường bằng code. Không import `pydantic`.
- **Rationale**: Constitution, mục Quy ước mã nguồn, giao Pydantic cho request, response, và schema DB. Bộ câu không phải ba thứ đó. `pyproject.toml` không khai báo `pydantic` trực tiếp. FastAPI kéo nó theo, nhưng thêm import là mở rộng quy ước, không phải việc plan này cần.
- **Alternatives considered**: Pydantic model cho file JSON. Bị bỏ vì lệch chỗ constitution giao Pydantic, trong khi `json` đủ để báo lỗi định dạng trước lượt đầu.

## Import cùng kiểu với test

- **Decision**: Module evals dùng `from core...`, `from turns.llm_turn import run_turn`, `from tools.tool_definitions import TOOL_DEFINITIONS`, và đúng một dòng `from tests.fakes.memory_plan_store import MemoryPlanStore`. Lệnh tay, từ gốc repo, đặt `PYTHONPATH=src` rồi `uv run python -m evals.runner`. Không sửa `sys.path` trong code.
- **Rationale**: `pyproject.toml` chỉ có `pythonpath = ["src"]` cho pytest. `python -m` từ gốc repo đưa gốc vào `sys.path`, nên `evals` và `tests` import được. `PYTHONPATH=src` đưa `turns` import được. Đã thử module tạm chỉ import `turns.llm_turn`, `tests.fakes.memory_plan_store`, và `evals`: output `OK`, exit 0. File tạm đã xóa.
- **Alternatives considered**: Chép `sys.path` như script smoke ngoài repo. Bị bỏ vì ràng buộc yêu cầu cùng kiểu import với test.

## Dựng việc con done, skipped, và ghi chú

- **Decision**: Gọi `normalize_new_plan(goal, None)` để lấy mục tiêu đã chuẩn hóa, `new_subtask(title)` để lấy tiêu đề và id đã chuẩn hóa, `normalize_subtask_note(note)` cho ghi chú, rồi `Subtask(...)` với `SubtaskStatus` khi trạng thái không phải pending hoặc khi có ghi chú. Đưa tuple đó vào `MemoryPlanStore.add`. Không gọi hàm `_`.
- **Rationale**: `new_subtask` luôn đặt `pending` và `note=None`. Không có hàm công khai nào khác dựng sẵn việc con done hoặc skipped. Constructor `Subtask` là công khai. Ba hàm kia là công khai và đã làm NFC. Không sửa model.
- **Alternatives considered**: Tự NFC trong evals rồi bịa id. Bị bỏ vì lệch luật chuẩn hóa sẵn có. Gọi `_nfc_strip`. Bị bỏ vì hàm đó không công khai.

## Nhận lỗi chạy và hết lượt tool

- **Decision**: Phân loại theo dòng log cuối và theo exception, đúng bảng trong plan. Kết thúc bình thường là dòng tám khóa cuối có `error_type` là `null` và `stop_reason` là `end_turn`, hoặc là hết lượt tool theo định nghĩa đang có. Năm mã lỗi chạy: `missing_key`, `no_model_log`, `ended_on_tool_log`, `model_error`, `bad_stop_reason`. Không so câu trả lời.
- **Rationale**: `_finish` chỉ trả `response.text` khi `stop_reason` là `end_turn`. Hết ngân sách trước `complete` không có dòng tám khóa. Hết ngân sách giữa các tool để dòng cuối là dòng bảy khóa. `max_tokens` rơi vào nhánh cuối của `_finish` sau khi log đã ghi `error_type` là `null`. Mỗi đường một mã để file kết quả không gộp chúng.
- **Alternatives considered**: Coi câu `Chưa liên lạc được để trả lời lúc này.` là lỗi chạy. Bị bỏ vì FR-012 cấm so chữ. Coi mọi lần không có `error_type` là lần chấm. Bị bỏ vì người duyệt yêu cầu nhận theo cấu trúc log.

## Số vòng tool

- **Decision**: Không có trường số vòng. Một vòng là một dòng tám khóa có `stop_reason` bằng `tool_use` và phía sau, trước dòng tám khóa kế tiếp, có ít nhất một dòng bảy khóa. Dòng `tool_use` không có dòng bảy khóa theo sau không cộng vòng. Nếu trước nó đã có đúng ba vòng thì đó là hết lượt tool.
- **Rationale**: `_model_log` ghi `stop_reason` của phản hồi. `_run_tools` chỉ chạy khi `_finish` trả `None`. Phản hồi thứ tư còn đòi tool không gọi `_run_tools`, nên không có dòng bảy khóa sau dòng tám khóa đó.
- **Alternatives considered**: Đếm mọi dòng `tool_use`. Bị bỏ vì cộng cả phản hồi thứ tư, lệch nghĩa "vòng đã chạy" của spec lượt.

## Mẫu cấm import tests

- **Decision**: `Invoke-GrepCheck` có tham số tùy chọn `-Allow`. Hàng cấm import `tests` dùng mẫu `^\s*(from|import)\s+tests\b` và `-Allow` là `^\s*(from|import)\s+tests\.fakes\.memory_plan_store(\s|$)`. Sau `git grep`, `-notmatch` áp lên phần mã nguồn sau tiền tố `đường-dẫn:số-dòng:`. Sáu hàng hiện có không truyền `-Allow`.
- **Rationale**: Lookahead trên `-E` trả exit 128. ERE dài đã bị bỏ. `-notmatch` trên cả dòng output không bỏ dòng hợp lệ vì dòng đó bắt đầu bằng đường dẫn, còn mẫu neo `^` vào `from` hoặc `import`. Đã thử lại bằng file tạm. Bốn dòng vi phạm còn lại. Hai dòng `tests.fakes.memory_plan_store` bị bỏ. File tạm đã xóa.
- **Alternatives considered**: Đổi hàm sang `-P`. Bị bỏ vì sáu hàng cũ không được đổi engine. Giữ ERE dài. Bị bỏ vì người duyệt yêu cầu `-Allow`.

## Constitution và biến môi trường của runner

- **Decision**: Ngoại lệ constitution version `1.2.0` và D-017 đã duyệt, đúng chữ trong plan. Sửa `.specify/memory/constitution.md` và `docs/DECISIONS.md` ở implement. Chỉ `main` trong `evals/runner.py` đọc `os.environ` và dựng `AnthropicModel`. Hàm kiểm khóa, vòng chạy, và `KeyboardInterrupt` nhận mapping và client.
- **Alternatives considered**: Thêm khóa vào `settings.py`. Bị bỏ vì sửa `src/`. Im và chỉ ghi AGENTS.md. Bị bỏ vì người duyệt đã nói ngoại lệ phải ở constitution.

## Archify

- **Decision**: Không cập nhật diagram trong `docs/architecture/`. Có sửa `docs/ARCHITECTURE.md`.
- **Rationale**: D-016 chỉ cập nhật diagram khi thêm gói hoặc ranh giới trong `src/`, nối hai cụm chưa nối, hoặc thêm composition root. `evals/` nằm ngoài `src/`, gọi lượt theo cách test đã gọi, và không phải composition root. Câu trong ARCHITECTURE.md nói mọi package nằm trong `src/` sẽ sai, nên prose phải sửa. Worker không import `evals/`.
- **Alternatives considered**: Chạy Archify vì có thư mục mới ở gốc. Bị bỏ vì điều kiện D-016 không khớp.
