# Contract: lọc từ khóa của get_plans

Lát này sửa luật lọc của tool F05. Hành vi tạo, mở, thêm, cập nhật, và ghi chú không đổi. Hình JSON không đổi. Spec nghiệp vụ: [spec.md](../spec.md). Model: [data-model.md](../data-model.md).

## Hàm

```text
filter_by_keyword(
    plans: tuple[Plan, ...],
    keyword: str | None,
) -> tuple[Plan, ...]
```

Hàm thuần trong `src/core/plans.py`. Không gọi store. Tên cũ `filter_by_goal_keyword` không còn.

`get_plans` gọi `store.list_newest_first()` rồi `filter_by_keyword`. Tool không tự NFC, `strip`, hay `casefold`.

## Khi nào không lọc

`keyword` là `None`, hoặc `unicodedata.normalize("NFC", keyword).strip()` còn `""`: trả đúng tuple đầu vào, cùng thứ tự.

## Khi có lọc

Kim là chuỗi từ khóa sau NFC rồi `strip`, rồi đi qua đúng một hàm lồng NFC + `casefold`. Hàm lồng không `strip`.

Một kế hoạch được giữ khi kim là đoạn con của một trong các chuỗi sau, mỗi chuỗi cũng đi qua hàm lồng đó:

- `plan.goal`
- `title` của từng việc con

`note` không tham gia. Trạng thái `pending`, `done`, và `skipped` đều được xét.

Kế hoạch khớp xuất hiện một lần dù kim nằm ở mục tiêu và ở nhiều tiêu đề. Thứ tự là thứ tự của tuple đầu vào. Kế hoạch được trả nguyên, gồm mọi việc con không chứa kim.

`"tieng"` không khớp `"tiếng"` ở mục tiêu và không khớp ở tiêu đề. Khoảng trắng bên trong kim được giữ: `"tiếng  Nhật"` không khớp `"tiếng Nhật"`.

Không khớp: tuple rỗng. `get_plans` vẫn là `ToolResult` thành công với `{"plans": []}`.

Tiêu đề đã lưu dạng NFD vẫn khớp kim NFC của cùng các chữ, vì hàm lồng đưa tiêu đề về NFC lúc so. JSON trả về đúng tiêu đề đã lưu, không ghi lại dạng NFC.

## Mô tả và phiên bản

`description` của `get_plans` là đúng câu:

```text
Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.
```

`DEFINITIONS_VERSION` là số nguyên `2`. Schema đầu vào của `get_plans` giữ một trường `keyword` kiểu string, không bắt buộc.

Khóa dòng log tool và dòng log mô hình không đổi. Giá trị `definitions_version` trên hai dòng đó là `2`. `PROMPT_VERSION` không đổi.

## Ngoài hợp đồng

Không đổi `Plan`, `Subtask`, `PlanStore`, `MemoryPlanStore`, `SupabasePlanStore`, `src/db/`, truy vấn, hay migration. Không đổi `src/tools/schemas.py`. Không đổi system prompt. Không đổi `evals/`. Không xếp hạng, không tìm gần đúng, không bỏ dấu. Không sửa `docs/PRODUCT.md` và không sửa spec cũ.
