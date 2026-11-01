# Quickstart: Từ khóa liệt kê khớp tiêu đề việc con

Kiểm chứng lọc `get_plans` trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Luật lọc nằm ở [contracts/keyword-filter.md](./contracts/keyword-filter.md). Model nằm ở [data-model.md](./data-model.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và uv.
- Không tạo file `.env`. Test mới không đọc cấu hình và không gọi mạng.

## Chuẩn bị

```text
uv sync
```

## Chạy

```text
uv run pytest tests/test_get_plans.py tests/test_add_subtask.py tests/test_tool_router.py tests/test_llm_turn.py
```

Kỳ vọng sau năm assertion trong [research.md](./research.md) mục 5: lệnh này pass, exit code 0. Dòng 86 so với số cứng `2`, không so với hằng. Dòng 109 là đúng câu FR-009. `tests/test_llm_turn.py` không sửa; nó so `definitions_version` với hằng.

Toàn bộ `uv run pytest` cũng pass. Không tắt test và không bỏ test.

## Việc test mới phải chứng minh

Mỗi test mới nằm trong `tests/test_get_plans.py`, tự tạo `MemoryPlanStore`, và gọi `get_plans`. Không dùng DB.

Ca tiêu đề NFD, ca `done`, và ca `skipped` dựng `Subtask` rồi `store.add`. Không đi qua `create_plan` cho riêng ca NFD, vì `create_plan` lưu tiêu đề dạng NFC.

Phải có ca cho từng ý:

- Từ khóa chỉ nằm trong tiêu đề việc con thì kế hoạch được trả về.
- Từ khóa nằm ở cả mục tiêu và nhiều tiêu đề thì kế hoạch xuất hiện một lần.
- Tiêu đề đang `done` chứa từ khóa thì kế hoạch được trả về, trạng thái vẫn `done`.
- Tiêu đề đang `skipped` chứa từ khóa thì kế hoạch được trả về.
- Tiêu đề đã lưu dạng NFD khớp từ khóa NFC của cùng các chữ.
- Khác hoa thường vẫn khớp trên tiêu đề.
- `"tieng"` không khớp tiêu đề `"tiếng"`.
- Từ khóa không nằm trong mục tiêu hay tiêu đề nào: `success` đúng, `plans` rỗng.
- Kế hoạch khớp trả đủ việc con, kể cả việc không chứa từ khóa, đúng thứ tự.
- Ghi chú là chỗ duy nhất chứa từ khóa: kế hoạch không được trả về.
- `"tiếng  Nhật"` không khớp tiêu đề `"tiếng Nhật"`.
- Hai kế hoạch chỉ khớp qua tiêu đề giữ thứ tự mới hơn đứng trước.

Năm assertion cũ đổi kỳ vọng. Hai hàm test đầu đổi tên (chỉ đổi tên), ba assertion của tests/test_tool_router.py giữ tên hàm:

- `test_keyword_in_subtask_only_matches`: `"giáo trình"` trả về kế hoạch có việc `"Mua giáo trình Nhật"`.
- `test_keyword_matches_goal_and_new_title`: `"giáo trình"` trả về kế hoạch vừa thêm việc `"Mua giáo trình"`. Assertion `"Nhật"` giữ nguyên.
- `tests/test_tool_router.py`: `assert DEFINITIONS_VERSION == 1` thành `== 2`. Dòng 86 thành `assert logged["definitions_version"] == 2`, vẫn số cứng. Dòng 109 thành đúng câu FR-009.
