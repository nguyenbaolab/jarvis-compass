# Quickstart: Bỏ qua việc con và ghi chú

Kiểm chứng phần còn lại của F07 trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Hình JSON và câu từ chối nằm ở [contracts/skip-and-note.md](./contracts/skip-and-note.md). Cách đọc model nằm ở [data-model.md](./data-model.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và [uv](https://docs.astral.sh/uv/).
- Không tạo file `.env`. Tool không đọc cấu hình.

## Chuẩn bị

```text
uv sync
```

## Chạy

```text
uv run pytest
```

Lệnh này gồm test health, test F04 đến F08, và test lát này. Kỳ vọng: toàn bộ pass, exit code 0.

Chạy riêng lát cắt:

```text
uv run pytest tests/test_subtask_skip_note.py tests/test_update_subtask.py
```

## Việc test cũ được sửa

Đúng ba loại. Không loại sửa nào khác.

- Trong `tests/test_create_plan.py`, `tests/test_get_plans.py`, `tests/test_get_plan_detail.py`, `tests/test_add_subtask.py`, và `tests/test_update_subtask.py`: kỳ vọng khóa việc con từ `id`, `title`, `status` thành `id`, `title`, `status`, `note`.
- Trong `tests/test_update_subtask.py`: câu `Trạng thái việc con chỉ nhận pending hoặc done.` thành `Trạng thái việc con chỉ nhận pending, done hoặc skipped.`
- Trong `tests/test_update_subtask.py`, `test_bad_status_wins_before_lookup`: bỏ `"skipped"` khỏi danh sách trạng thái sai. Các giá trị khác trong danh sách giữ nguyên: `None`, `""`, `"   "`, `"xong"`, `"chưa xong"`, `"Done"`, `"PENDING"`.

Không xóa test. Không đổi assertion tiêu đề, số việc, thứ tự, câu danh tính, hay tập trạng thái mà một test tạo kế hoạch đang khóa.

`tests/fakes/memory_plan_store.py` không đổi. `tests/test_health.py` không đổi.

## Việc file test mới phải chứng minh

Mỗi test tạo store riêng và truyền vào `store=`. Ba ca không ghi dùng lớp cùng khuôn `_ReplaceCounter` của `tests/test_update_subtask.py`, đặt trong file test mới. Lớp đếm `replace` trên đúng instance rồi gọi `replace` của lớp cha. Không dùng phép so object. Ba ca: đặt lại đúng ghi chú đang có, xóa ghi chú khi chưa có, đặt lại đúng `skipped` đang có. Mỗi ca thành công và số lần `replace` không tăng.

- Đặt `skipped`: danh tính kế hoạch, danh tính việc con, tiêu đề, mục tiêu, và thứ tự không đổi. Rồi đặt `done`, rồi `pending`, rồi lại `skipped`. Lần mở và lần liệt kê thấy đúng mã. Việc kia giữ trạng thái. `note` cả hai vẫn `null`.
- Mọi việc `skipped`: liệt kê không lọc và mở đều thấy kế hoạch, cùng danh tính và cùng mục tiêu.
- `" skipped "` thành `skipped`. `Skipped`, `SKIPPED`, và `bỏ qua` bị từ chối bằng câu nêu đủ ba mã, và câu đó thắng trước khi tra kế hoạch.
- JSON của lần đặt `skipped` có `status` là `"skipped"`. `SubtaskStatus` và `Literal` trạng thái trong `src/tools/schemas.py` cùng có mã đó.
- Đặt ghi chú `"Đợi giáo trình"`, rồi đổi trạng thái. Ghi chú vẫn `"Đợi giáo trình"`. Đặt ghi chú không đổi trạng thái.
- Ghi đè ghi chú. Ghi chú cũ không còn.
- `"  Đợi giáo trình  "` được lưu thành `"Đợi giáo trình"`. Một ghi chú NFD được lưu và trả về dạng NFC.
- Ghi chú có dấu phẩy, xuống dòng, và khoảng trắng đôi: các ký tự bên trong giữ nguyên.
- `None`, `""`, hoặc chỉ khoảng trắng khi đang có ghi chú thì xóa thành `null`, và trạng thái không đổi.
- Một ghi chú dài, hơn vài trăm ký tự, được lưu nguyên văn sau chuẩn hóa.
- Tạo kế hoạch: việc con mới có `note` là `null` khi liệt kê và khi mở ngay sau khi tạo. Thêm việc con: việc mới có `note` là `null`. Khóa đúng thứ tự `id`, `title`, `status`, `note`.
- `add_subtask` không làm mất ghi chú của việc con đã có.
- `set_subtask_note` với danh tính kế hoạch trống, danh tính việc con trống, kế hoạch không có, và việc con của kế hoạch khác: đúng câu theo thứ tự trong contract. Ghi chú chỉ khoảng trắng trên danh tính không tồn tại vẫn là câu không có kế hoạch.
- Sau mỗi lần từ chối, danh sách không đổi. Một lần đặt hợp lệ sau đó vẫn thành công.

Parse `ToolResult.output` thành JSON rồi so trường. Không so nguyên văn chuỗi JSON. So câu `ToolError` đúng từng ký tự với bảng trong contract.

## Ngoài kiểm chứng này

Không gọi `pywrangler`, không mở HTTP, không nối Supabase. Các đường đó thuộc lát cắt khác trong [spec.md](./spec.md).
