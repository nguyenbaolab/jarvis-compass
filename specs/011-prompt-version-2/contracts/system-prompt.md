# Contract: Lời hướng dẫn hệ thống phiên bản 2

File: `src/core/system_prompt.py`. Không import. Không đọc file lúc chạy. Không thêm tên.

```text
PROMPT_VERSION: int = 2
SYSTEM_PROMPT: str
```

`SYSTEM_PROMPT` là đúng khối trong [plan.md](../plan.md) mục Nguyên văn SYSTEM_PROMPT, kể cả dòng trống giữa các đoạn và dấu xuống dòng cuối chuỗi. Lượt đã gửi nguyên văn này ở mỗi lần `complete` qua `src/turns/llm_turn.py:145`. Lát này không sửa file lượt.

Cụm `trợ lý lập kế hoạch` đứng một lần, trong câu cấm tự xưng. Chuỗi không chứa `get_plan_detail`. Chuỗi không chứa `Friday`. Chuỗi có `get_plans`. Chuỗi `get_plans` không chứa `get_plan_detail`, nên kiểm tra vắng `get_plan_detail` vẫn đúng khi chuỗi có `get_plans`.

## Kiểm tra

Một hàm trong `tests/test_llm_turn.py`, tên `test_system_prompt_has_six_laws`, tên cũ `test_system_prompt_has_four_laws`. Hàm không gọi client. Ngoài ba kiểm tra phiên bản, vắng mặt, và đếm, mỗi dòng dưới đây là một chuỗi con phải có trong `SYSTEM_PROMPT`. Dấu ngoặc kép trong dòng là ký tự của chuỗi, không phải dấu bao.

- `PROMPT_VERSION == 2`
- không chứa `get_plan_detail`
- không chứa `Friday`
- `trợ lý lập kế hoạch` đếm đúng một lần
- `Bạn là JARVIS. Không dùng tên nhân vật nào khác.`
- `Trả lời bằng tiếng Việt.`
- `Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3`
- `Không tự xưng "trợ lý lập kế hoạch".`
- `Luật này không áp khi người dùng báo một việc đã xong hoặc bỏ`
- `Không in đậm bằng **.`
- `một dòng chữ trơn như "Ngày 1"`
- `Tiêu đề việc con do bạn tự đặt không có tiền tố thứ tự`
- `không có tiền tố thứ tự như "Ngày 1:", "Tuần 1:", "Bước 1", "1."`
- `Tiêu đề việc con do bạn tự đặt phải có điểm kết thúc đo được.`
- `Không tự đặt việc kiểu thói quen suốt một khoảng thời gian.`
- `Tiêu đề do người dùng tự đưa được giữ nguyên từng chữ.`
- `Không hiện mã kế hoạch hay mã việc con.`
- `Cần mã thì tự tìm bằng get_plans với tên việc.`
- `Không dùng pending, done, skipped trong câu trả lời.`
- `không phải chưa làm, xong, hay bỏ qua`
- `gọi get_plans với tên việc họ nói`
- `Khớp đúng một việc thì cập nhật ngay, không hỏi xác nhận.`
- `Không khớp hoặc khớp nhiều việc thì hỏi lại.`
- `Không đòi bằng chứng.`

Ánh xạ luật: năm chuỗi JARVIS, tiếng Việt, câu ví dụ, câu cấm tự xưng, và `Luật này không áp khi người dùng báo một việc đã xong hoặc bỏ` là FR-002. Hai chuỗi `**` và `Ngày 1` là FR-003. Chuỗi `Tiêu đề việc con do bạn tự đặt không có tiền tố thứ tự` và chuỗi bốn ví dụ tiền tố là FR-004. Ba chuỗi điểm kết thúc, thói quen, và `Tiêu đề do người dùng tự đưa được giữ nguyên từng chữ.` là FR-005. Bốn chuỗi mã, `Cần mã thì tự tìm bằng get_plans với tên việc.`, `pending`, và `không phải chưa làm` là FR-006. Bốn chuỗi `gọi get_plans với tên việc họ nói`, khớp một việc, hỏi lại, và bằng chứng là FR-007.

Mọi assertion khác trong `tests/test_llm_turn.py` giữ nguyên chữ, gồm `logged["prompt_version"] == PROMPT_VERSION` và `request.system == SYSTEM_PROMPT`. `tests/test_eval_result.py` và `tests/test_eval_score.py` không sửa.
