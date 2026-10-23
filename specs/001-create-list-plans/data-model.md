# Data Model: Tạo và liệt kê kế hoạch

Nguồn luật nghiệp vụ: [spec.md](./spec.md). Cách chọn id, thứ tự, Unicode, và chỗ đặt mã: [research.md](./research.md). Hình JSON của tool: [contracts/create-plan.md](./contracts/create-plan.md) và [contracts/get-plans.md](./contracts/get-plans.md).

Hình việc con từ F07 thêm `id` và `status`. Chi tiết ở [update-subtask.md](../003-update-subtask/contracts/update-subtask.md).

`Plan`, `Subtask`, `normalize_new_plan`, lỗi miền, `Protocol PlanStore`, và hàm lọc theo từ khóa trong goal nằm ở `src/core/plans.py`. File đó chỉ dùng thư viện chuẩn (`dataclasses`, `typing`, `unicodedata`, `uuid`). Không import FastAPI, Pydantic, `src/tools`, hay `src/db`.

## Plan

Một kế hoạch đã lưu. Dataclass. Trong lát cắt này, có mặt trong store nghĩa là đang hoạt động. Không có trường trạng thái.

| Trường | Kiểu | Ai gán | Quy tắc |
|--------|------|--------|---------|
| `id` | `str` | `PlanStore.add` | `str(uuid.uuid4())`, giữ nguyên sau khi trả về. Hai lần thêm là hai `id`. So khớp thực thể theo `id`. |
| `goal` | `str` | người gọi, sau chuẩn hóa | Bắt buộc. Giá trị lưu là dạng NFC, còn nội dung sau NFC rồi `strip`. Khoảng trắng bên trong giữ nguyên. |
| `subtasks` | `tuple[Subtask, ...]` | người gọi, sau chuẩn hóa | Có thứ tự. Mỗi phần tử là một `Subtask`. Tuple rỗng là hợp lệ. |
| `created_order` | `int` | `PlanStore.add` | Số nguyên ≥ 1, tăng một đơn vị mỗi lần thêm thành công trong cùng một store. Không xuất hiện trong JSON của tool. |

Quan hệ: một `Plan` sở hữu danh sách `Subtask` của nó. Việc con không có danh tính riêng và không tồn tại ngoài `Plan`.

Vị trí việc con là chỉ số trong `subtasks`, bắt đầu từ 0. Liệt kê trả về đúng thứ tự đó.

Đầu vào `create_plan` vẫn là danh sách chuỗi. Chuỗi đó trở thành `Subtask.title` sau chuẩn hóa. JSON của cả hai tool xuất `subtasks` thành mảng object `{"title": "..."}`, giữ thứ tự.

### Chuẩn hóa khi tạo

Hàm `normalize_new_plan` trong `src/core/plans.py` nhận `goal: str | None` và `subtasks: list[str] | None`. Với `goal` và từng phần tử `subtasks`, áp dụng `unicodedata.normalize("NFC", ...)` rồi `str.strip()`. Giá trị lưu là dạng NFC. Hàm trả về `(goal, tuple[Subtask, ...])` đã chuẩn hóa, hoặc báo lỗi miền.

- `goal` là `None`, hoặc chỉ còn rỗng sau NFC rồi `strip`: lỗi miền, không có `Plan`.
- `subtasks` là `None`: tuple rỗng.
- Bất kỳ phần tử nào chỉ còn rỗng sau NFC rồi `strip`: lỗi cả yêu cầu. Không có `Plan` mới, kế hoạch đã có không đổi.
- `str.strip()` chỉ bỏ hai đầu. Khoảng trắng đôi ở giữa được giữ.
- Hai cách mã hóa của cùng một chữ có dấu ra cùng giá trị NFC. Dấu vẫn được giữ: `"tieng"` không thành `"tiếng"`.
- Hai chuỗi cùng chữ sau chuẩn hóa vẫn là hai `Subtask`, đúng vị trí.

`create_plan` chỉ gọi `PlanStore.add` sau khi hàm này trả về giá trị. Store không chuẩn hóa lại. Lỗi miền được lớp tool đổi thành `ToolError`.

## Subtask

Dataclass trong `src/core/plans.py`, một trường. Không id, không hạn chót, không mức ưu tiên, không trạng thái hoàn thành.

| Trường | Kiểu | Ai gán | Quy tắc |
|--------|------|--------|---------|
| `title` | `str` | người gọi, sau chuẩn hóa | Bắt buộc khi việc con được gửi. Giá trị lưu là dạng NFC, còn nội dung sau NFC rồi `strip`. |

## PlanStore

`Protocol` trong `src/core/plans.py`. Tool phụ thuộc cổng này. Lát cắt này không có bản cài đặt trong `src/`.

| Thao tác | Việc phải làm |
|----------|----------------|
| `add(goal, subtasks) -> Plan` | `goal` là `str` đã chuẩn hóa. `subtasks` là `tuple[Subtask, ...]`. Gán `id` và `created_order`, giữ nguyên `goal` và thứ tự `subtasks`, trả về `Plan` vừa lưu. |
| `list_newest_first() -> tuple[Plan, ...]` | Mọi kế hoạch trong store, `created_order` lớn hơn đứng trước. Store rỗng trả về tuple rỗng. |

`MemoryPlanStore` trong `tests/fakes/` là bản cài đặt dùng cho kiểm chứng: danh sách trong bộ nhớ của đúng instance đó, `created_order` bắt đầu ở 1. Mỗi test tạo instance mới và truyền vào hàm tool. Không đưa class này vào `src/`.

Lọc từ khóa không thuộc store. Hàm lọc theo từ khóa trong goal, cùng file `src/core/plans.py`, nhận danh sách mới-nhất-trước và từ khóa, rồi giữ những kế hoạch khớp, đúng thứ tự tương đối.

- `keyword` là `None`: không lọc.
- Ngược lại, từ khóa đi qua `unicodedata.normalize("NFC", ...)` rồi `strip`. Chuỗi rỗng sau bước đó: không lọc.
- So khớp: NFC rồi `casefold` ở cả hai phía. Một kế hoạch khớp khi từ khóa đã chuẩn hóa, sau `casefold`, là đoạn con của `goal` sau NFC rồi `casefold`. Việc con không tham gia.
- `"tieng"` không khớp `"tiếng"`.

Hai tình huống kiểm (tạo bằng goal NFD thì liệt kê ra goal NFC; goal lưu từ NFD, lọc bằng từ khóa NFC của cùng chữ thì khớp) ghi ở hai contract.

## Không lưu trong lát cắt này

Trạng thái hoàn thành, hạn chót, mức ưu tiên, session, người dùng, từ khóa đã tìm. Một người dùng duy nhất đã chốt ở [docs/PRODUCT.md](../../docs/PRODUCT.md) §2; store không có khóa người dùng.

## Chuyển trạng thái

Không có. Tạo thành công thì kế hoạch nằm trong store và xuất hiện khi liệt kê không lọc. Lát cắt này không có thao tác hoàn thành, cất, hay xóa.
