# Quickstart: Độ bền ghi

Plan này không chạy các lệnh dưới đây. Phần Worker ghi chưa kiểm chứng cho tới khi có người chạy và thấy kết quả.

## Pytest, kho giả, không mạng

Từ gốc repo:

```text
uv run pytest
```

Ca mới dùng kho giả trong `tests/fakes`. Một ca để lời gọi kho không trả về và thấy tool bị bỏ trong hạn. Một ca đi qua `run_turn` với kho giả không trả lời, chứng minh lượt trả trong hạn. Một ca hai lần `replace` cùng version: lần sau ném `PlanConflictError` và bản trong bộ nhớ không đổi. Không cần `JARVIS_TEST_SUPABASE_URL`.

## Kho Supabase local

Chỉ sau khi migration được duyệt. Không `db push`. Không sửa file migration cũ.

```text
npx --yes supabase@2.122.0 start
npx --yes supabase@2.122.0 db reset
```

`db reset` chạy lại mọi file trong `supabase/migrations/`, gồm `20261103205500_plans_version.sql`. Hàng có sẵn thành `version` 0. Hàm `replace_plan` còn một chữ ký, có `expected_version`.

Rồi, trong cùng cửa sổ, lấy URL và khóa local. Host phải là `127.0.0.1` hoặc `localhost`.

```text
$s = npx --yes supabase@2.122.0 status -o json | ConvertFrom-Json
$env:JARVIS_TEST_SUPABASE_URL = $s.API_URL
$env:JARVIS_TEST_SUPABASE_KEY = $s.SERVICE_ROLE_KEY
uv run pytest tests/test_supabase_plan_store.py
```

Kỳ vọng khi đã implement: hai `replace` với cùng version đã đọc, lần sau bị từ chối, lần đọc lại vẫn là bản của lần ghi đầu.

Thêm ca hai `replace` chạy cùng lúc bằng `asyncio.gather`, cùng version đã đọc: đúng một lần thành công, một lần `PlanConflictError`, lần đọc lại là bản của lần thành công. Ca tuần tự vẫn qua nếu SQL kiểm version không atomic. Ca cùng lúc mới thấy lỗi đó.

## Worker, chưa kiểm chứng

Chưa chạy trong plan này. Pytest trên CPython không tính là đã kiểm Worker.

Trong WSL Ubuntu, cùng cách dev đã ghi ở `AGENTS.md`:

```text
export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/jarvis-compass
uv run pywrangler dev
```

Cách nhìn, cùng kiểu spike khâu 1 tới 3, không commit route mới: một lời gọi kho qua `postgrest_client` với timeout ngắn, trỏ tới địa chỉ chấp nhận TCP nhưng không trả lời. Timeout ngắn ở đây là cách nhìn, không phải mức trần 20 giây của `postgrest_client`. Thấy lời gọi kết thúc trong hạn thì ghi là đã kiểm chứng, kèm lệnh và kết quả. Không thấy, hoặc chưa chạy, thì vẫn là chưa kiểm chứng. Không ghi là đạt khi chưa chạy.

## Thứ tự lên production

Áp migration rồi deploy Worker ngay. Giữa hai bước, tool ghi vào kế hoạch có sẵn sẽ lỗi vì chữ ký `replace_plan(uuid, text, jsonb)` đã bị bỏ. Đây là việc của bước hoàn tất lát này. Tasks không có bước push hay deploy.
