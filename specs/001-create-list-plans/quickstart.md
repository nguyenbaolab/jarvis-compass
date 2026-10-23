# Quickstart: Tạo và liệt kê kế hoạch

Kiểm chứng F04 và F05 trên CPython, không cần Supabase, Wrangler, hay WSL. Kịch bản gốc nằm ở [spec.md](./spec.md). Hình JSON nằm ở [contracts/create-plan.md](./contracts/create-plan.md) và [contracts/get-plans.md](./contracts/get-plans.md). Trường lưu nằm ở [data-model.md](./data-model.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và [uv](https://docs.astral.sh/uv/).
- Không tạo file `.env`. Hai tool không đọc cấu hình.

## Chuẩn bị

```text
uv sync
```

## Chạy

```text
uv run pytest
```

Lệnh này gồm test health hiện có và test của lát cắt. Kỳ vọng: toàn bộ pass, exit code 0.

Chạy riêng lát cắt:

```text
uv run pytest tests/test_create_plan.py tests/test_get_plans.py
```

## Việc mỗi test phải chứng minh

Test tạo một `MemoryPlanStore` mới trong từng test và truyền vào `store=`. Không dùng store dùng chung giữa các test.

`tests/test_create_plan.py` phủ User Story 1 trong spec:

- Tạo với mục tiêu và hai việc con trả về đúng mục tiêu, đúng thứ tự việc con, và một `id` đúng dạng ở contract. Mỗi việc con trong JSON là object `{"title": "..."}`, không phải chuỗi.
- Tạo không gửi việc con trả về `subtasks` là mảng rỗng.
- Hai lần tạo cùng nội dung trả về hai `id` khác nhau; cả hai đều còn trong store.
- Khoảng trắng hai đầu của mục tiêu và việc con bị bỏ sau bước NFC; chữ bên trong giữ nguyên.
- Mục tiêu và từng `title` được lưu dạng NFC.
- Mục tiêu thiếu, rỗng, hoặc chỉ khoảng trắng ném `ToolError`. Số kế hoạch trong store không đổi.
- Một việc con chỉ khoảng trắng, kể cả khi đứng giữa việc con hợp lệ, ném `ToolError` và không lưu phần nào.

`tests/test_get_plans.py` phủ User Story 2 và 3:

- Sau một lần tạo thành công, liệt kê không từ khóa trả về đúng `id`, mục tiêu, và việc con. `subtasks` là mảng object `{"title": "..."}` đúng thứ tự đã lưu.
- Ba lần tạo A rồi B rồi C được liệt kê thành C, B, A, mỗi kế hoạch kèm đủ việc con.
- Store rỗng trả về `{"plans": []}` và `success is True`.
- Một lần tạo bị từ chối không làm số kế hoạch tăng.
- Từ khóa khớp đoạn trong mục tiêu: NFC rồi bỏ khoảng trắng hai đầu, rồi `casefold` ở cả hai phía; có phân biệt dấu (`"tieng"` không khớp `"tiếng"`); không xét việc con.
- (a) Tạo với goal dạng NFD, liệt kê không lọc ra goal dạng NFC. Cùng giá trị NFC đó là `goal` trả về lúc tạo.
- (b) Goal lưu từ NFD, lọc bằng từ khóa NFC của cùng chữ thì khớp.
- Từ khóa không khớp trả về mảng rỗng, không ném lỗi.
- Từ khóa rỗng hoặc chỉ khoảng trắng cho cùng kết quả với liệt kê không lọc.

Parse `ToolResult.output` thành JSON rồi so trường. Không so nguyên văn chuỗi JSON. So `subtasks` như mảng object có khóa `title`.

## Ngoài bước kiểm chứng này

Không gọi `uv run pywrangler dev`. Không cần database đang chạy. `src/db/client.py` vẫn là stub.
