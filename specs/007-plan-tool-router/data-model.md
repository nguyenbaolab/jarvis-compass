# Data model: Điều phối tool kế hoạch

Lát này không thêm bảng, không thêm cột, không đổi `Plan` hay `Subtask`. Thực thể dưới đây là dữ liệu của một lần gọi và của catalog. Chúng không lưu thành phiên.

## Bộ định nghĩa

Một catalog. `DEFINITIONS_VERSION` là số nguyên `1`.

Mỗi tool trong catalog:

| Mục | Quy tắc |
|-----|---------|
| Tên | Đúng một trong sáu tên ở [contracts/tool-definitions.md](./contracts/tool-definitions.md). Khớp từng ký tự. |
| `description` | Chuỗi không rỗng, đúng câu trong contract đó. |
| `input_schema` | Object JSON Schema rút gọn, đúng contract đó. |

Không có tool thứ bảy. `revise_plan` không có trong catalog.

## Lần gọi

| Mục | Quy tắc |
|-----|---------|
| Tên | Giá trị người gọi đưa. Không có trong catalog thì dừng trước khi xét kho. |
| Đầu vào | Giá trị người gọi đưa. Chỉ `dict` mới được xét trường. |
| Kho | `PlanStore` người gọi đưa. Router không tạo kho. |

Không có trạng thái lưu giữa hai lần gọi.

## Kết quả

Dùng `ToolResult` đã có.

| Mục | Khi đạt | Khi lỗi |
|-----|---------|---------|
| `success` | `True` | `False` |
| `output` | Đúng `output` tool trả | Một câu: tên lạ, đầu vào, miền giữ nguyên, hoặc câu chung |

Một lần trả về không ném `Exception`. `BaseException` không bị biến thành kết quả.

## Phân loại

Thứ tự một lần gọi:

1. Tên không có trong catalog → `unknown_tool`. Kho không gọi.
2. Đầu vào không phải `dict` → `invalid_input`, câu object. Kho không gọi.
3. Trường thừa đầu tiên theo thứ tự khóa của `dict` → `invalid_input`. Kho không gọi. Chỉ khi schema nói `additionalProperties` là `false`.
4. Trường bắt buộc thiếu đầu tiên theo thứ tự `required` → `invalid_input`. Kho không gọi.
5. Trường sai kiểu đầu tiên theo thứ tự `properties` → `invalid_input`. Với mảng, phần tử sai đầu tiên thắng câu phần tử. Kho không gọi.
6. Gọi đúng hàm tool với các khóa đã có và với `store`. `ToolError` hoặc `PlanDomainError` → `domain`, `output` là `str` của lỗi, không đổi chữ.
7. `Exception` khác → `unexpected`, `output` là câu chung, không thử lại.
8. Không có exception → trả nguyên `ToolResult` của tool.

`None` là sai kiểu, không phải “thiếu”. Chuỗi rỗng là đúng kiểu và đi vào tool.

## Dòng nhật ký

Một object, đúng bảy khóa, theo thứ tự này: `tool`, `input`, `ok`, `error_type`, `duration_ms`, `definitions_version`, `detail`.

| Khóa | Quy tắc |
|------|---------|
| `tool` | Tên đã nhận. |
| `input` | Đầu vào đã nhận nếu dumps được. Không dumps được thì `null`. |
| `ok` | `true` khi `success` của kết quả là `True`, ngược lại `false`. |
| `error_type` | `null` khi `ok` là `true`. Khi lỗi: `unknown_tool`, `invalid_input`, `domain`, hoặc `unexpected`. |
| `duration_ms` | Số nguyên không âm. Có thể là 0. |
| `definitions_version` | Số `1`, không phải chuỗi. |
| `detail` | `null`, trừ `unexpected`. Khi đó là tên lớp, không có thông điệp. |

Dòng không phải dữ liệu kế hoạch và không phải hội thoại.

## Nguồn cấu hình kho

Không có thực thể mới. `SupabasePlanStore(source)` nhận dict hoặc object có attribute, qua `require_supabase`. Thiếu hoặc rỗng thì `SettingsError` với câu FR-018 của spec 006, trước `postgrest_client`. Đủ giá trị thì `list_newest_first` gọi `postgrest_client` với đúng địa chỉ và khóa của nguồn đó, không phải sentinel trong env tiến trình. Test không đọc attribute riêng của store.
