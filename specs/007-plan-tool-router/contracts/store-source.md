# Contract: Dựng kho từ nguồn cấu hình

Không có factory mới. Lời dựng là `SupabasePlanStore(source)` trong `src/db/plan_store.py`.

`source` là dict hoặc object có attribute, cùng luật `require_supabase` đã chốt ở spec 006. Router không gọi constructor này và không import `db`.

## Đã có, không viết lại và không sửa assertion

`tests/test_supabase_plan_store.py`, hàm `test_store_requires_both_settings_before_network`: thiếu hoặc rỗng `SUPABASE_URL` hay `SUPABASE_KEY` thì `SettingsError` với đúng câu FR-018 của spec 006, câu không chứa giá trị khóa, và `postgrest_client` không được gọi.

`tests/test_plan_store_contract.py`: khi kho local chạy, `SupabasePlanStore(source)` ghi rồi đọc đúng hợp đồng. Lát này không thêm ca skip mới.

## Ca mới

Một test mới, không cần kho chạy và không cần mạng. Test không đọc `_url` hay `_key`.

- Env tiến trình có `SUPABASE_URL`, `SUPABASE_KEY`, `JARVIS_TEST_SUPABASE_URL`, và `JARVIS_TEST_SUPABASE_KEY` là các sentinel, khác giá trị của nguồn.
- Trong module `db.plan_store`, `postgrest_client` được thay bằng hàm ghi đối số `url` và `key`, rồi trả một async context manager. `list_plans` được thay bằng coroutine trả danh sách rỗng, nên không mở mạng.
- Nguồn dict đủ `SUPABASE_URL` và `SUPABASE_KEY`. `SupabasePlanStore(source)` xong thì `postgrest_client` chưa được gọi.
- `await store.list_newest_first()` xong thì `postgrest_client` được gọi đúng một lần. `url` và `key` của lần gọi đó bằng hai giá trị của nguồn, không bằng sentinel.
- Cùng kỳ vọng với một object có hai attribute đó.

Không thêm thuộc tính công khai để đọc địa chỉ hay khóa.

Constructor không ghi dòng log của tool.

## Nạp cùng ứng dụng

`src/app.py` thêm đúng một dòng import, cạnh các dòng `import db` hiện có:

```text
import db.plan_store
```

Không sửa dòng nào khác trong file đó. Không gọi `SupabasePlanStore` lúc nạp. Không đọc cấu hình lúc nạp. Không mở mạng lúc nạp.

Test mới không đọc `sys.modules` của tiến trình pytest. Test spawn tiến trình con bằng `sys.executable`, thư mục làm việc là gốc repo, `PYTHONPATH` của con là `src`, lệnh là:

```text
import app, sys; raise SystemExit(0 if 'db.plan_store' in sys.modules else 1)
```

Mã thoát `0` là đạt. Không sửa `tests/test_health.py`.

Một lần kiểm tay, ghi ở [quickstart.md](../quickstart.md): bỏ dòng `import db.plan_store` thì test này đỏ. Xong thì trả dòng đó lại.
