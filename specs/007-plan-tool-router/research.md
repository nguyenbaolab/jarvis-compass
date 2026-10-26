# Research: Điều phối tool kế hoạch

## 1. Đã thấy

Đọc trong phiên này, không suy đoán:

- `pyproject.toml` phụ thuộc `fastapi`, `anthropic`, `postgrest`. Không có `jsonschema`. Không có `pydantic` khai trực tiếp; Pydantic đến qua FastAPI và đang dùng cho JSON đầu ra ở `src/tools/schemas.py`.
- `src/tools/schemas.py` là `SubtaskJson`, `PlanJson`, `PlansJson`. Đó là hình đầu ra. Không có schema đầu vào.
- `src/tools/tool_router.py` chỉ có một docstring. `src/app.py` import `tools.tool_router` và `db.client`, `db.models`. Không import `db.plan_store`.
- `src/db/__init__.py` không import `plan_store`. `import db` không nạp module kho.
- `SupabasePlanStore.__init__` (`src/db/plan_store.py`) gọi `require_supabase(source)` và gán `_url`, `_key`. `postgrest_client` chỉ được gọi trong `add`, `list_newest_first`, `get`, `replace`. Dựng store không mở mạng.
- `tests/test_supabase_plan_store.py`, `test_store_requires_both_settings_before_network`, gọi `SupabasePlanStore(source)` khi thiếu hoặc rỗng địa chỉ hay khóa. Câu lỗi là câu FR-018 của spec 006. Khóa giả không có trong câu. `postgrest_client` bị bịt và không được gọi.
- `tests/test_plan_store_contract.py`, `_supabase_store`, dựng `SupabasePlanStore(source)` rồi chạy hợp đồng ghi và đọc. Ca đọc lại trên kho local đã có ở đó.
- `tests/test_settings_supabase.py` chứng minh `require_supabase` không đọc `os.getenv`. Chưa có ca constructor thành công khi env tiến trình mang sentinel khác.
- `create_plan` bọc `normalize_new_plan` trong `_domain_as_tool_error`, rồi `await store.add` nằm ngoài khối đó. `get_plan_detail` bọc `normalize_plan_id`, rồi `store.get` nằm ngoài. `PlanDomainError` từ kho ở những chỗ đó thoát khỏi tool.
- `PlanDomainError` và `ToolError` đều kế thừa `Exception`, không kế thừa nhau, không kế thừa `BaseException` trực tiếp ngoài `Exception`.
- `scripts/check.ps1` cấm `src/core` import `fastapi`, `pydantic`, `tools`, `db`. Không có luật máy cho `src/tools` import `db`. Luật đó nằm ở D-011 và ở ràng buộc của bước plan này.

## 2. Chưa đo

Người dùng chốt ở bước plan, phiên này không chạy Worker: `time.monotonic` trên Worker có thể đứng yên trong lúc CPU chạy, nên `duration_ms` của một lần gọi có thể là 0. Test chấp nhận 0. Test không đòi `duration_ms > 0`.

## 3. Quyết định

### Không thêm thư viện kiểm JSON Schema

**Decision**: Viết hàm kiểm trong `src/tools/tool_router.py`. Hàm đọc schema trong `src/tools/tool_definitions.py`. Không thêm dependency. Không dùng Pydantic cho đầu vào.

**Rationale**: Bộ nhớ Worker đã gần 128 MiB. `jsonschema` là dependency mới. Pydantic cho đầu vào tạo một schema thứ hai, lệch với JSON Schema sẽ gửi cho mô hình ở vòng sau.

**Alternatives considered**: Thêm `jsonschema`. Bọc đầu vào bằng `BaseModel`. Cả hai bị loại vì lý do trên.

Phần schema mà hàm kiểm thực sự đọc, và chỉ phần này:

- `type` của object là `object`.
- `properties`: mỗi trường `type` là `string`, hoặc `type` là `array` với `items.type` là `string`.
- `required`: danh sách tên. Thiếu khóa này thì coi như không có trường bắt buộc. Sáu schema trong lát này đều ghi `required`, kể cả khi rỗng.
- `additionalProperties`: `false` thì trường lạ là lỗi. Sáu schema đều ghi `false`.

Không đọc `enum`, `format`, `minLength`, `oneOf`, `$ref`. `status` là chuỗi trong schema. Chuỗi `DONE` vẫn vào tool và nhận câu miền đã có. Đúng spec: đúng kiểu thì câu miền giữ nguyên.

Kiểu Python tương ứng:

- `string`: `str`. `bool` không phải `str`. `None` không phải `str`.
- `array`: `list`. `tuple` không phải `list`. Phần tử phải là `str`. `None` trong danh sách là sai kiểu phần tử.
- object đầu vào: `dict`. `list` không phải object.

### Không thêm factory kho

**Decision**: FR-012 dùng `SupabasePlanStore(source)` đang có. Không thêm hàm bọc. Không thêm getter.

**Rationale**: Constructor đã gọi `require_supabase` trước mọi `postgrest_client`. Thiếu cấu hình đã có test trên chính constructor. Thêm factory là một đường thứ hai cho cùng một lời gọi.

**Alternatives considered**: `build_plan_store(source)` trong `src/tools` hoặc `src/db`. Loại vì tools không được import `db`, và constructor đã đủ.

Việc còn thiếu so với spec là một ca constructor thành công. Test không đọc `_url` hay `_key`. Env tiến trình mang sentinel. Bản thay của `postgrest_client` trong `db.plan_store` ghi đối số `url` và `key`, rồi trả một async context manager. Bản thay của `list_plans` trong cùng module trả danh sách rỗng, để `list_newest_first` kết thúc mà không mở mạng. Sau `SupabasePlanStore(source)`, `postgrest_client` chưa được gọi. Sau `await store.list_newest_first()`, nó được gọi đúng một lần. `url` và `key` của lần đó là giá trị của nguồn, không phải sentinel. Ca thiếu cấu hình và ca ghi rồi đọc trên kho local không viết lại.

### Một catalog, router tra tên sang hàm

**Decision**: `src/tools/tool_definitions.py` giữ `DEFINITIONS_VERSION: int = 1` và `TOOL_DEFINITIONS`. Mỗi mục có `description` và `input_schema`. Router giữ bảng tên sang hàm của `plan_tools`. Hai tập tên phải bằng nhau. Test so hai tập với sáu tên đã chốt.

**Rationale**: User cấm trộn vào `schemas.py`. Hàm tool không nằm trong catalog vì catalog là thứ vòng sau gửi cho mô hình. Bảng tra nằm cạnh chỗ gọi để `tool_definitions` không import `plan_tools`.

**Alternatives considered**: Nhét hàm vào catalog. Catalog sẽ import `plan_tools`, và thứ gửi cho mô hình lẫn với callable. Loại.

### Phân loại lỗi

**Decision**: Trong `execute_tool`, bắt `(ToolError, PlanDomainError)` trước, giữ `str(error)` làm `output`, `error_type` là `domain`. Sau đó bắt `Exception`: `output` là câu chung, `error_type` là `unexpected`, `detail` là `type(error).__name__`. Không đọc `str(error)` ở nhánh này. Không bắt `BaseException`.

**Rationale**: Hai lớp kia là lỗi miền đã chốt. Mọi `Exception` khác, gồm `SettingsError`, `RuntimeError`, lỗi mạng, là unexpected. Router không biết chuỗi nào trong thông điệp là secret, nên không ghi thông điệp và không cố che. `KeyboardInterrupt` và `SystemExit` đi tiếp. Lần đó không trả `ToolResult` và không bắt buộc một dòng log, vì dòng log gắn với kết quả trả về.

**Alternatives considered**: Ghi `str(error)` rồi xóa khóa nếu tìm thấy. Loại vì router không có danh sách giá trị secret. Bắt `BaseException`. Loại theo ràng buộc bước plan.

### Log là một hàm

**Decision**: Tham số keyword-only `log: Callable[[str], None] | None = None`. `None` thì `print(line, flush=True)`. Chuỗi đưa vào hàm là một object JSON, `json.dumps(..., ensure_ascii=False)`, không chứa ký tự xuống dòng. `print` tự thêm xuống dòng bên ngoài chuỗi đó.

**Rationale**: Test truyền `list.append` và không cần thư viện log. `loguru` vẫn chưa chốt ở ARCHITECTURE §6. Không thêm thư viện.

**Alternatives considered**: `logging` của thư viện chuẩn. Dùng được nhưng test phải cấu hình handler. Hàm truyền vào ngắn hơn và đúng yêu cầu.

Nếu `tool_input` không `json.dumps` được, dòng log vẫn phải là JSON hợp lệ và hàm vẫn trả kết quả. Khi đó khóa `input` của dòng là `null`. Đầu vào JSON bình thường đọc lại đúng từng ký tự. Không dùng `default=str`, vì `str` của một object có thể chứa secret.

### Kết quả

**Decision**: Trả `ToolResult` đã có. `success` sai nghĩa là cờ lỗi bật. `output` là nội dung. Không thêm kiểu kết quả. Tool trả `ToolResult` mà không ném thì router trả nguyên object đó. `ok` trong log là `result.success`. Sáu tool hiện chỉ trả `success=True` hoặc ném.

**Rationale**: Constitution đã chốt mẫu này. Spec mô tả cùng hai phần: nội dung và cờ lỗi.

### Đồng hồ

**Decision**: `started = time.monotonic()` ở đầu `execute_tool`, đọc lại ngay trước khi ghi log. `duration_ms = int(elapsed * 1000)` khi `elapsed > 0`, ngược lại `0`.

**Rationale**: `int` với số dương là làm tròn xuống. Số âm hoặc 0 thành 0, khớp “không âm” và khớp đồng hồ Worker có thể đứng.

### Nạp module kho kiểm ở tiến trình con

**Decision**: `tests/test_app_loads_plan_store.py` spawn một tiến trình con bằng `sys.executable`. Thư mục làm việc là gốc repo. `PYTHONPATH` của con là `src`. Lệnh là `python -c "import app, sys; raise SystemExit(0 if 'db.plan_store' in sys.modules else 1)"`. Test pytest chỉ nhìn mã thoát của con.

**Rationale**: Lúc pytest nạp các file test kho, `db.plan_store` đã nằm trong `sys.modules` của tiến trình pytest. Kiểm `sys.modules` ở đó vẫn xanh dù `app.py` không import module này.

**Alternatives considered**: Đọc cây cú pháp của `app.py`. Loại vì một dòng import sai vẫn có thể được đếm, và không chứng minh lệnh import chạy được. Kiểm `sys.modules` trong tiến trình pytest. Loại vì dương tính giả ở trên.

Quickstart ghi một lần kiểm tay: bỏ dòng `import db.plan_store` trong `src/app.py`, chạy riêng file test này, test đỏ, rồi trả dòng import lại. Không để file nguồn bị bỏ dòng đó.

## 4. Hướng phụ thuộc

`tool_router` import `tools.tool_definitions`, `tools.plan_tools`, `tools.base`, `core.plans` (`PlanStore`, `PlanDomainError`). Không import `db`, `config`, `fastapi`, `pydantic`. `tool_definitions` chỉ dùng thư viện chuẩn. `src/core` không sửa. `src/app.py` thêm đúng một dòng `import db.plan_store` cạnh các import `db` hiện có. Dòng đó không gọi `SupabasePlanStore(...)`. Nạp module không đọc cấu hình và không mở mạng, vì thân module `plan_store` không dựng instance.
