# Research: Bỏ qua việc con và ghi chú

Quyết định cho phần còn lại của F07. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Ràng buộc cách làm do người dùng chốt khi gọi `/speckit-plan`. Nơi đặt model và chiều phụ thuộc đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011. Cách kiểm danh tính và cách ghi đè một kế hoạch đã chốt ở [research của cập nhật việc con](../003-update-subtask/research.md). Tài liệu này chỉ ghi cách lát cắt này tuân các nơi đó.

## 1. Thêm mã và trường, không giá trị mặc định

**Decision**: Trong `src/core/plans.py`, `SubtaskStatus` thêm `SKIPPED = "skipped"` sau `DONE`. `Subtask` thêm `note: str | None` đứng sau `status`. Trường này không có giá trị mặc định. `Plan` không thêm trường và không đổi kiểu. `new_subtask` vẫn là chỗ duy nhất dựng việc con mới, và lời gọi `Subtask(...)` ở đó truyền `note=None` cùng `id`, `title`, và `SubtaskStatus.PENDING`. Không còn lời gọi `Subtask(...)` nào khác.

**Rationale**: Người dùng bắt mọi chỗ dựng `Subtask` phải truyền `note`, để đổi trạng thái không quên ghi chú. Không đặt mặc định thì trình biên dịch kiểu và mỗi lời gọi đều thấy trường này. Việc con mới chưa có ghi chú, nên giá trị truyền vào là `None`. `Plan` không mang ghi chú và không có trạng thái riêng. Trạng thái cấp kế hoạch thuộc F10.

**Alternatives considered**: `note: str | None = None` — người dùng cấm giá trị mặc định. Để `replace_subtask_status` dựng `Subtask(id=..., title=..., status=..., note=item.note)` — vẫn là dựng bằng tay, đúng kiểu người dùng cấm vì một trường mới sau này lại có thể bị quên. Đặt ghi chú trên `Plan` — spec gắn ghi chú vào việc con.

## 2. Bản đã đổi đi qua dataclasses.replace, tìm việc con một lần

**Decision**: `src/core/plans.py` import `replace` từ `dataclasses`. Một hàm nội bộ nhận `plan`, `subtask_id`, và một hàm đổi một `Subtask`. Vòng `for` tìm `item.id == subtask_id` chỉ nằm trong hàm đó. Không thấy thì ném `PlanDomainError` với hằng `_MISSING_SUBTASK_MESSAGE = "Kế hoạch này không có việc con với danh tính này."` Hằng này là định nghĩa duy nhất của câu đó. Hàm đổi trả lại đúng object `item` thì hàm nội bộ trả đúng object `plan` đã nhận. Ngược lại hàm nội bộ dựng `Plan` mới qua `_plan_with_subtasks`. `replace_subtask_status` gọi hàm nội bộ. Khi `item.status` đã là trạng thái yêu cầu, hàm đổi trả `item`. Khi khác, hàm đổi trả `replace(item, status=status)`. `replace_subtask_note` cùng khuôn. Khi `item.note` đã là ghi chú đã chuẩn hóa, hàm đổi trả `item`. Khi khác, hàm đổi trả `replace(item, note=note)`.

**Rationale**: `Subtask` là `frozen`. `replace` sao chép mọi trường rồi ghi đè trường được nêu, nên đổi `status` giữ `note`, và đổi `note` giữ `status`, `id`, và `title`. Một vòng tìm và một hằng câu chữ ngăn hai bản lệch nhau. Trả đúng object cũ là tín hiệu để lớp tool khỏi gọi `store.replace`, cùng cách `update_subtask` đang làm với `updated is not plan`.

**Alternatives considered**: Hai vòng `for` giống nhau trong hai hàm, mỗi vòng một chuỗi câu lỗi — người dùng cấm chép logic tìm và cấm hai định nghĩa của câu đó. So sánh rồi vẫn `replace` khi giá trị không đổi — tạo object mới, tool sẽ `replace` dù dữ liệu không đổi, trái spec. Sửa `Subtask` tại chỗ — dataclass đang `frozen`.

## 3. Chuẩn hóa ghi chú bằng _nfc_strip

**Decision**: `normalize_subtask_note(note: str | None) -> str | None` trong `src/core/plans.py`. `note` là `None` thì trả `None`, trước khi gọi `_nfc_strip`. Ngược lại gọi `_nfc_strip`. Chuỗi còn rỗng thì trả `None`. Còn nội dung thì trả chuỗi đó. Không có nhánh độ dài và không cắt. `normalize_subtask_status` đổi câu lỗi thành `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` Cả nhánh `None` và nhánh `ValueError` dùng một hằng cho câu đó. `SubtaskStatus("skipped")` hợp lệ vì thành viên mới. Không NFC và không `casefold` cho trạng thái.

**Rationale**: `_nfc_strip` đã là NFC rồi bỏ khoảng trắng hai đầu. Dùng lại nó giữ một luật với tiêu đề. `None` phải được xử lý trước `_nfc_strip` vì `unicodedata.normalize` không nhận `None`. Tiêu đề việc con không có hạn độ dài, theo [spec tạo và liệt kê](../001-create-list-plans/spec.md). Spec của lát này bắt ghi chú theo cùng hạn đó, nên không thêm số và không thêm câu lỗi độ dài. Xóa ghi chú là `None`, không phải chuỗi rỗng, để JSON xuất `null`.

**Alternatives considered**: Hàm chuẩn hóa riêng không gọi `_nfc_strip` — chép luật NFC. Cắt ghi chú ở 200 hay 500 ký tự — spec cấm tự cắt và cấm hạn số riêng. Coi chuỗi rỗng là ghi chú hợp lệ — spec coi rỗng là xóa, và JSON phải là `null` chứ không phải `""`.

## 4. Tool mỏng, JSON luôn có note

**Decision**: `set_subtask_note(plan_id, subtask_id, note, *, store) -> ToolResult` trong `src/tools/plan_tools.py`. Trước `store.get`, theo thứ tự: `normalize_plan_id`, `normalize_subtask_id`, `normalize_subtask_note`. `PlanDomainError` đổi thành `ToolError`. `store.get` trả `None` thì `ToolError(_MISSING_PLAN_MESSAGE)`. Sau đó `replace_subtask_note`. `updated is not plan` thì `store.replace(updated)`. Trả về `_plan_tool_result(updated)`. `SubtaskJson` thêm `note: str | None` sau `status`. `status` là `Literal["pending", "done", "skipped"]`. Không đặt `exclude_none` và không đặt `model_config` mới. `_plan_json` truyền `note=item.note`. Việc con mới có `None`, nên JSON là `null`.

**Rationale**: Khuôn này là khuôn `update_subtask` đang có. Ghi chú trống không ném lỗi, nên bước chuẩn hóa ghi chú không chặn bước “kế hoạch không có”. Dùng lại `_MISSING_PLAN_MESSAGE` và `_plan_tool_result` giữ một câu và một cách dựng JSON. Pydantic 2 mặc định ghi trường có giá trị `None` thành `null`. `exclude_none` sẽ làm mất trường, trái spec.

**Alternatives considered**: Dựng JSON riêng trong `set_subtask_note` — lệch một hàm `_plan_json`. Gọi `store.replace` cả khi object không đổi — trái “không ghi vào store”. Thêm phương thức `PlanStore.set_note` — người dùng cấm thêm phương thức.

## 5. Store giả và test cũ

**Decision**: `tests/fakes/memory_plan_store.py` không sửa. `add` giữ nguyên tuple việc con được giao. `replace` thay `Plan` theo `id` và không đọc `status` hay `note`. Test “không ghi lại dữ liệu đã lưu” đếm lần gọi `replace`. File test mới có lớp cùng khuôn `_ReplaceCounter` trong `tests/test_update_subtask.py`: đếm trên instance đó rồi gọi `replace` của lớp cha. Không dùng phép so object. Ba ca đếm: đặt lại đúng ghi chú đang có, xóa ghi chú khi chưa có, đặt lại đúng `skipped` đang có. Mỗi ca thành công và `replace_calls` không tăng. Test mới còn các ca ở [quickstart.md](./quickstart.md), gồm đặt ghi chú rồi đổi trạng thái rồi ghi chú vẫn còn, và `Skipped`, `SKIPPED`, `bỏ qua` bị từ chối bằng câu nêu đủ ba mã trước khi tra kế hoạch. Test cũ chỉ sửa ba loại: câu trạng thái cũ thành câu nêu đủ ba mã; kỳ vọng khóa việc con thêm `"note"`; `test_bad_status_wins_before_lookup` bỏ `"skipped"` khỏi danh sách trạng thái sai, các giá trị khác trong danh sách giữ nguyên. Không xóa test. Không loại sửa nào khác.

**Rationale**: Store giả không cần biết ghi chú. Sửa nó không mở khóa hành vi nào mà `get` và `replace` chưa làm. Đếm lời gọi chứng minh tool không ghi, cùng cách lát cập nhật việc con đã chứng minh đặt lại đúng trạng thái. So object không nằm trong cách chứng minh đó. `"skipped"` đang nằm trong danh sách trạng thái sai của test cũ. Lát này làm mã đó hợp lệ, nên giá trị đó phải ra khỏi danh sách, nếu không test cũ sẽ đòi từ chối một mã hợp lệ. `Skipped`, `SKIPPED`, và `bỏ qua` vẫn là trạng thái sai và được khóa ở file test mới. Các assertion số việc, tiêu đề, thứ tự, và câu danh tính của test cũ giữ nguyên.

**Alternatives considered**: Thêm `replace_count` vào `MemoryPlanStore` — sửa store giả khi không bắt buộc. So `store.get(...) is` object đã đọc — người dùng cấm phép so object cho ca không ghi. Giữ `"skipped"` trong danh sách trạng thái sai của test cũ — ca đó sẽ fail vì mã đã hợp lệ. Viết test mới đè file test cũ — người dùng yêu cầu file test mới.

## 6. Câu docs bị lệch

**Decision**: Implement cập nhật câu trạng thái đầu [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) để nói F07 gồm `skipped` và ghi chú. Implement cập nhật docstring câu “Đúng ba khóa” trong `src/tools/schemas.py`, và `Literal` trạng thái thành `"pending"`, `"done"`, `"skipped"`, khớp `SubtaskStatus`. Implement cập nhật docstring của `SubtaskStatus` và của `normalize_subtask_status` trong `src/core/plans.py`. Không sửa file nào trong `specs/003-update-subtask/`. [docs/PRODUCT.md](../../docs/PRODUCT.md) không sửa.

**Rationale**: Constitution bắt sửa file docs khi thay đổi làm file đó sai. Câu trạng thái code sẽ sai nếu không nói `skipped` và ghi chú. Ba docstring nói tập trạng thái hoặc số khóa cũ. Spec 003 là biên bản lát đánh dấu done. Luật đang chạy của mã `skipped` và của câu ba mã nằm ở spec này.

**Alternatives considered**: Sửa câu hai mã trong spec 003 — người dùng giữ spec đó làm biên bản và cấm sửa các file đó. Để docstring “Đúng ba khóa” và `Literal` hai mã — JSON và kiểu sẽ lệch `SubtaskStatus` ngay khi thêm `skipped`.
