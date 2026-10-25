# Contract: Cổng PlanStore trên bộ nhớ và trên Supabase

Người gọi của lát này là test. Route HTTP, Telegram, và LLM không gọi store. Hình JSON của tool không đổi và không thêm khóa thời gian; [src/tools/plan_tools.py](../../../src/tools/plan_tools.py) không sửa.

Miền và bảng nằm ở [data-model.md](../data-model.md).

## Dựng bản Supabase

```text
SupabasePlanStore(source)
```

`source` là dict hoặc object có attribute. Tên đọc: `SUPABASE_URL`, `SUPABASE_KEY`.

| source | Kết quả |
|--------|---------|
| Cả hai là `str` khác `""` | Store được tạo. Chưa có request mạng nào trong lúc tạo. |
| URL thiếu, không phải `str`, hoặc `""` | `SettingsError("Thiếu SUPABASE_URL.")` |
| Khóa thiếu, không phải `str`, hoặc `""` | `SettingsError("Thiếu SUPABASE_KEY.")` |
| Cả hai cùng thiếu theo luật trên | `SettingsError("Thiếu SUPABASE_URL và SUPABASE_KEY.")` |

`str` chỉ toàn khoảng trắng vẫn là có giá trị. Spike không `strip`.

`SettingsError` không chứa các giá trị đã đưa vào, kể cả khi một khóa có giá trị và khóa kia thiếu. Dict trống vẫn thất bại khi môi trường tiến trình đang có hai biến này. Bản trong bộ nhớ không nhận `source`.

Header và URL gốc của client lắp như spike `12079c0`: `apikey` luôn có; `Authorization: Bearer` chỉ khi khóa bắt đầu bằng `eyJ`; đường dẫn là URL bỏ slash cuối rồi cộng `/rest/v1`; header mặc định của `postgrest` được giữ.

## Bốn phương thức

Cùng chữ ký với `PlanStore` trong `src/core/plans.py`.

### add

Nhận `goal` và tuple việc con đã chuẩn hóa. Không chuẩn hóa lại.

Trả `Plan` mới. `id` kế hoạch là UUID do kho cấp, chữ thường, khớp regex phiên bản 4 đang có trong `tests/helpers.py`. `created_order` là số nguyên, lần thêm sau lớn hơn lần thêm trước trong cùng một kho. `goal` và từng việc con giữ `id`, `title`, `status`, `note`, và thứ tự tuple.

Trên Supabase, dòng việc con mới có `created_at` và `status_changed_at` bằng nhau, là thời điểm của lần ghi đó. Hai trường này không có trên `Plan`.

### list_newest_first

Trả mọi kế hoạch đang có. `created_order` lớn hơn đứng trước. Kho trống trả tuple rỗng. Việc con của mỗi kế hoạch theo `position` tăng dần.

### get

| Đầu vào | Kết quả |
|---------|---------|
| Đúng chuỗi `id` đã cấp | Đúng `Plan` đó |
| `"1"`, `"2"`, UUID viết hoa, chuỗi không phải UUID canonical | `None`. Trên Supabase, không gửi request lọc bằng chuỗi đó |
| UUID canonical không có trong kho | `None` |

`None` không phải lỗi. Các kế hoạch đang có không đổi.

`get` và `list` cùng gọi một hàm ánh xạ. Dữ liệu đọc từ kho chứa trạng thái lạ làm hàm đó ném `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")`. Không có `Plan` trả về. Test gọi hàm với dòng giả, không ghi mã lạ vào kho, và luôn chạy.

### replace

Thay kế hoạch cùng `id` bằng object được đưa: `goal` và toàn bộ việc con. Không cấp `id` kế hoạch mới. Không cấp lại `id` việc con. Không đổi `created_order` trên Supabase.

| Tình huống | Kết quả |
|------------|---------|
| Không có `id`, gồm `"1"`, `"2"`, và UUID viết hoa | `PlanDomainError("Không có kế hoạch với danh tính này.")`. Số kế hoạch không tăng. Kế hoạch đang có không đổi |
| Việc con còn `id` | Giữ `created_at`. `status_changed_at` giữ nguyên nếu mã trạng thái giữ nguyên, kể cả khi `title` hoặc `note` đổi. Mã đổi thì `status_changed_at` là thời điểm lần ghi này |
| Việc con mới trong danh sách | Hai mốc là thời điểm lần ghi này. Việc cũ không nhận mốc mới |
| Việc con không còn trong danh sách | Lần đọc sau không còn việc đó |
| Ghi chú trống trên miền (`None`) | Cột `note` là `NULL` |

Câu `Trạng thái việc con chỉ nhận pending, done hoặc skipped.` không phải câu của store. Câu đó vẫn là câu từ chối đầu vào ở tool, trước khi `replace`.

`list_newest_first` dùng cùng hàm ánh xạ, nên cùng câu khi dữ liệu đọc từ kho chứa trạng thái lạ. Không trả một phần danh sách.

## Hợp đồng chạy trên cả hai bản

Một coroutine, hai param `memory` và `supabase`:

1. Thêm một kế hoạch có hai việc. `id` kế hoạch là UUID. Mục tiêu, id việc, tiêu đề, `pending`, ghi chú trống, và thứ tự giữ nguyên.
2. Thêm kế hoạch thứ hai. Liệt kê đặt kế hoạch thứ hai trước.
3. `get` đúng id trả đúng kế hoạch. `get` một UUID khác, `"1"`, và `"2"` trả `None`. Hai kế hoạch không đổi.
4. `replace` một id không có ném đúng câu `Không có kế hoạch với danh tính này.` Số kế hoạch không tăng. Kế hoạch đang có không đổi.
5. Đổi trạng thái một việc qua `done`, `skipped`, rồi `pending`. Việc kia giữ nguyên. Thêm một việc thì việc đó đứng cuối, `pending`, ghi chú trống. Đặt ghi chú rồi xóa ghi chú: lần đọc sau là không có ghi chú, không phải chuỗi rỗng.
6. Mục tiêu và tiêu đề tiếng Việt đã NFC đọc lại từng ký tự. Thứ tự việc con khi liệt kê và khi mở trùng thứ tự đã lưu.

Param `memory` luôn chạy. Param `supabase` skip theo mục dưới khi kho local không chạy.

## Chỉ kho thật

- Sau `add`, hai mốc của mỗi việc bằng nhau và có giá trị.
- `replace` cùng mã trạng thái, có đổi tiêu đề hoặc ghi chú, giữ nguyên từng giá trị hai mốc.
- `replace` đổi mã trạng thái giữ nguyên `created_at` và đổi `status_changed_at`.
- Thêm một việc chỉ đặt hai mốc mới trên việc đó.
- Cột `note` đọc thẳng là `NULL` khi miền là không có ghi chú.

Các ca này không chạy trên `MemoryPlanStore`.

## Ánh xạ trạng thái lạ

Một test gọi hàm ánh xạ dòng sang `Subtask` với dòng giả có mã không thuộc `pending`, `done`, `skipped`. Không tạo `SupabasePlanStore`, không đọc biến kho, không mở mạng. Luôn chạy. Kỳ vọng `PlanDomainError("Trạng thái việc con đã lưu không hợp lệ.")`.

## Biến của test kho

Đọc `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` từ môi trường tiến trình test. Không đọc `SUPABASE_URL` hay `SUPABASE_KEY`. Không đọc `.env` và không đọc `.dev.vars`. Hai giá trị đi vào dict cấu hình dưới khóa `SUPABASE_URL` và `SUPABASE_KEY`.

Xóa `subtasks` rồi `plans` nằm trong `tests/supabase_plan_db.py`. Helper dựng client bằng hàm factory của `src/db/client.py`.

## Host không phải local

Trước mọi lời gọi mạng, host của URL phải là `127.0.0.1` hoặc `localhost`. `localhost` không phân biệt hoa thường. Host khác làm test thất bại, không skip, với đúng câu `Test kho chỉ chạy trên kho local.` Factory client không được gọi. Một test luôn chạy với URL host xa để khóa câu này.

## Skip khi kho local không chạy

| Tình huống | Câu `pytest.skip` |
|------------|-------------------|
| Thiếu `JARVIS_TEST_SUPABASE_URL` | `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL.` |
| Thiếu `JARVIS_TEST_SUPABASE_KEY` | `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_KEY.` |
| Thiếu cả hai | `Kho local không chạy: thiếu JARVIS_TEST_SUPABASE_URL và JARVIS_TEST_SUPABASE_KEY.` |
| Host là local mà không kết nối được | `Kho local không chạy: không kết nối được.` |

Câu skip không chứa giá trị khóa và không chứa `str` của exception. Đã nối được mà PostgREST trả lỗi quyền hoặc lỗi thiếu bảng thì test thất bại, không skip. Host không phải local cũng thất bại, không skip.
