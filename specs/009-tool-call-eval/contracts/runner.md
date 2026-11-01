# Contract: Lệnh chạy tay

File duy nhất: `evals/runner.py`.

`main` là hàm duy nhất làm bốn việc này:

- đọc `os.environ`
- dựng `AnthropicModel` bằng `AnthropicModel()`, rồi truyền instance đó vào hàm chạy bộ
- gọi `date.today()`
- truyền `evals/results/` vào hàm chạy bộ

`from clients.anthropic_model import AnthropicModel` nằm trong `main`. Lớp này không có `__init__`. `complete` mở client SDK rồi đóng, nên một instance dùng cho mọi lần là đủ.

Hàm kiểm khóa, hàm chạy cả bộ, và hàm xử lý `KeyboardInterrupt` nhận một `Mapping[str, str]` và một `ModelClient`. Hàm chạy cả bộ còn nhận thư mục ra và ngày. Cả hai là tham số bắt buộc, không có giá trị mặc định. Hàm chạy cả bộ truyền đúng hai giá trị đó vào hàm ghi. Các hàm này không đọc `os.environ`, không dựng `AnthropicModel`, và không gọi `date.today()`. Test gọi các hàm này với mapping giả, client giả, `tmp_path`, và một ngày cố định. File test là `tests/test_eval_runner.py`.

Việc file này không làm: tự viết luật chấm, tự parse JSON bộ câu, tự dựng `Subtask`. Nó gọi module thuần và truyền `ModelClient`. Không sửa `sys.path`.

Thứ tự trong hàm nhận mapping và client:

1. Đọc `JARVIS_EVAL_ANTHROPIC_KEY` từ mapping. Không có khóa, khóa `""`, hoặc khóa mà `strip()` ra chuỗi rỗng: in đúng một dòng `Thiếu JARVIS_EVAL_ANTHROPIC_KEY.` ra stderr, mã thoát `2`, không gọi client, không chạy lượt, không ghi file. Khóa hợp lệ được strip() rồi mới dùng cho lượt và cho việc giấu khóa (bổ sung 2026-11-01).
2. Đọc bộ câu. Sai định dạng: in lỗi, mã thoát `2`, không ghi file kết quả.
3. Mỗi câu ba lần. Mỗi lần một `MemoryPlanStore` mới và lịch sử rỗng. Client là client được truyền vào. Đủ ba lần của một câu thì in một dòng ra stderr: [<số câu xong>/<tổng>] <id> <mã lần 1> <mã lần 2> <mã lần 3>; dòng này không chứa câu trả lời hay dòng log (bổ sung 2026-11-01).
4. Hết bộ: giấu khóa, ghi đúng một file mới, in báo cáo ra stdout, mã thoát `0`. Tỉ lệ thấp vẫn là mã `0`.
5. `KeyboardInterrupt` hoặc `asyncio.CancelledError` giữa bộ: không chạy lần tiếp, không ghi file, mã thoát `130`.

`main` đọc `os.environ`, dựng một `AnthropicModel()`, gọi `date.today()`, truyền `evals/results/` cùng ngày đó vào hàm chạy cả bộ, và thoát bằng mã hàm đó trả về.

Lệnh, từ gốc repo, ghi trong AGENTS.md kèm chữ "chưa chạy thử" cho tới khi có một lần chạy thật:

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi giá trị vào repo>"
uv run python -m evals.runner
```

Đã thử bằng module tạm `evals._probe_import`, chỉ import `turns.llm_turn`, `tests.fakes.memory_plan_store`, và `evals`, rồi in `OK`. Lệnh là hai dòng đầu, với `-m evals._probe_import` thay cho `-m evals.runner`. Output là `OK`, exit 0. File tạm và thư mục `evals/` đã xóa. `python -m` từ gốc repo đưa gốc vào `sys.path`, nên `evals` và `tests` import được. `PYTHONPATH=src` đưa `turns` import được. Không sửa `sys.path` trong code.

Ba ca trong `tests/test_eval_runner.py`:

| Ca | Kỳ vọng |
|---|---|
| Khóa thiếu, khóa `""`, và khóa chỉ khoảng trắng | Dừng trước lượt đầu, không gọi client, không ghi file |
| `KeyboardInterrupt` giữa bộ | Dừng, không ghi file |
| `asyncio.CancelledError` giữa bộ | Dừng, không ghi file, mã `130` |
| Chạy đủ một bộ nhỏ với client giả | Ghi đúng một file trong `tmp_path` |
| Danh sách file của `evals/results/` trước và sau các ca | Hai danh sách trùng nhau |
| Khóa có khoảng trắng hai đầu | Lượt nhận khóa đã strip, ghi đúng một file |
| Bộ một câu | stderr có đúng một dòng tiến độ |
