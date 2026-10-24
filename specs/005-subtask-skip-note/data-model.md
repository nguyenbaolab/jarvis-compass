# Data Model: Bỏ qua việc con và ghi chú

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách chọn hàm: [research.md](./research.md). Hình JSON và câu từ chối: [contracts/skip-and-note.md](./contracts/skip-and-note.md).

`Plan` giữ trường và kiểu đã chốt ở [data-model của cập nhật việc con](../003-update-subtask/data-model.md). Nghĩa “có mặt trong store là đang hoạt động” không đổi.

## Subtask

`Subtask` vẫn `frozen`. Thứ tự trường:

| Trường | Kiểu | Quy tắc |
|--------|------|---------|
| `id` | `str` | Giữ nguyên khi đổi trạng thái hoặc đặt ghi chú. |
| `title` | `str` | Giữ nguyên khi đổi trạng thái hoặc đặt ghi chú. |
| `status` | `SubtaskStatus` | `PENDING = "pending"`, `DONE = "done"`, `SKIPPED = "skipped"`. |
| `note` | `str \| None` | Không có giá trị mặc định. `None` nghĩa là không có ghi chú. |

`new_subtask` là lời gọi `Subtask(...)` duy nhất. Lời gọi đó truyền `note=None` và `status=SubtaskStatus.PENDING`.

Đổi một việc đang có không gọi `Subtask(...)`. Hàm đổi trả `dataclasses.replace` với đúng một trường được ghi đè: `status` hoặc `note`.

## Trạng thái

Mọi cặp trong `pending`, `done`, và `skipped` đều đi được cả hai chiều, gồm đặt lại đúng mã đang có. Đặt lại đúng mã đang có trả đúng object `Plan` đã nhận.

Đổi trạng thái không đổi `note`. Kế hoạch không có trạng thái mới. Mọi việc `done`, mọi việc `skipped`, hoặc lẫn hai mã: kế hoạch vẫn nằm trong store.

## Ghi chú

| Việc | Ai làm | Quy tắc |
|------|--------|---------|
| Chuẩn hóa | `normalize_subtask_note` | `None` trả `None` trước `_nfc_strip`. Chuỗi khác đi qua `_nfc_strip`. Kết quả rỗng trả `None`. |
| Gán | `replace_subtask_note` | Nhận ghi chú đã chuẩn hóa. Khác ghi chú đang có thì `replace(item, note=note)`. Bằng thì trả đúng object `Plan` cũ. |
| Xóa | cùng hai hàm trên | Đầu vào `None`, `""`, hoặc chỉ khoảng trắng thành `None`. |

Không có hạn số. Không cắt. Không lịch sử.

## Hàm miền

Nằm ở `src/core/plans.py`. Không gọi store. Không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

| Hàm | Việc phải làm |
|-----|----------------|
| Hàm nội bộ tìm một việc | Một vòng theo `id`. Không thấy thì `PlanDomainError` với hằng câu `Kế hoạch này không có việc con với danh tính này.` Hàm đổi trả cùng object việc thì trả cùng object `Plan`. |
| `replace_subtask_status` | Gọi hàm nội bộ. Trạng thái đã đúng thì không `replace`. Khác thì `replace(item, status=status)`. |
| `normalize_subtask_note` | Như bảng ghi chú. Không ném lỗi cho ghi chú trống. |
| `replace_subtask_note` | Cùng khuôn `replace_subtask_status`, ghi đè `note`. |
| `normalize_subtask_status` | `strip` rồi `SubtaskStatus(...)`. Ngoài ba mã thì một hằng câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` |

`normalize_plan_id` và `normalize_subtask_id` giữ nguyên.

## PlanStore

`Protocol` không thêm thao tác. Lát này gọi `get` rồi `replace` đã có. `replace` chỉ được gọi khi hàm miền trả object `Plan` khác object đã đọc.

`MemoryPlanStore` không sửa. `add` không đọc `note`. `replace` không đọc `note`.

## Không lưu trong lát cắt này

Trạng thái cấp kế hoạch, lịch sử ghi chú, hạn chót, mức ưu tiên, session, người dùng. Một người dùng duy nhất đã chốt ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §2.
