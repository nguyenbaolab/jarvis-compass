# Quickstart: Điều phối tool kế hoạch

Không cần khóa mô hình, không cần route, không cần Telegram. Không cài thêm thư viện.

## Kiểm tra lớp điều phối và nạp ứng dụng

Từ gốc repo:

```text
uv run pytest tests/test_tool_router.py tests/test_app_loads_plan_store.py tests/test_supabase_plan_store_source.py
```

Kỳ vọng: cả ba file đạt, không skip. Các file này không nối kho local.

Đối chiếu hành vi với [contracts/execute-tool.md](./contracts/execute-tool.md), [contracts/tool-definitions.md](./contracts/tool-definitions.md), và [contracts/store-source.md](./contracts/store-source.md).

## Một lần kiểm đột biến

Khi `src/app.py` đã có dòng `import db.plan_store` và `tests/test_app_loads_plan_store.py` đang xanh: bỏ đúng dòng import đó, chạy

```text
uv run pytest tests/test_app_loads_plan_store.py
```

Kỳ vọng: test đỏ. Tiến trình con không thấy `db.plan_store` trong `sys.modules`. Trả dòng import lại ngay sau lần chạy đó. Không commit bản đã bỏ dòng.

## Cả bộ

```text
uv run pytest
```

Kỳ vọng: mọi assertion cũ giữ nguyên. Ba file mới đạt.

Khi Supabase local đang chạy và hai biến `JARVIS_TEST_SUPABASE_URL`, `JARVIS_TEST_SUPABASE_KEY` trỏ vào kho đó: dòng tổng kết có 0 skipped.

Khi kho local tắt: các test kho đã có vẫn skip với lý do kho không chạy. Ba file mới của lát này vẫn chạy, không thêm một lần skip.

## Trước khi có mã nguồn

Bước implement viết test trước, chạy đúng lệnh pytest của ba file mới, và giữ output lần fail trong phiên trước khi sửa `src/`. Cách làm nằm ở [plan.md](./plan.md), mục Cách làm khi implement. Quickstart này là lệnh kiểm sau khi mã đã có.
