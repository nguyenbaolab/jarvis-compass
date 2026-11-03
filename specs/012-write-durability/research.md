# Research: Độ bền ghi

## 1. Xung đột dùng version, không gộp hai lần ghi

**Decision**: Cột `version` trên `plans`. `replace` gửi đúng version đã đọc. Lệch thì kho từ chối, không đổi hàng và không đổi việc con. Không gộp hai lần ghi.

**Rationale**: Yêu cầu plan đã chốt cơ chế này. Spec cho phép hoặc áp dụng đủ mà vẫn giữ thay đổi kia, hoặc từ chối. Version chọn nhánh từ chối. Ca "A đọc, B đọc, A ghi xong, B ghi" không cần hai lời gọi ghi chồng nhau: B vẫn cầm version cũ và bị từ chối.

**Alternatives considered**: Giữ khóa từ lúc đọc tới lúc ghi. Không làm được, vì đọc và ghi là hai lời gọi HTTP riêng. Gộp hai bản trong kho. Spec không bắt gộp, và gộp cần luật từng trường. Plan không chọn gộp.

## 2. Lỗi xung đột là lớp riêng trong core

**Decision**: `PlanConflictError` trong `src/core/plans.py`, không kế thừa `PlanDomainError`. Kho thật và `MemoryPlanStore` ném đúng lớp đó khi version lệch. Tool bắt lớp này và đổi thành câu từ chối. Không tự gọi `replace` lần nữa.

**Rationale**: `except PlanDomainError` đang đổi mọi lỗi miền thành `str(error)`. Nếu xung đột là lớp con, câu từ chối phải nằm trong core. Spec và yêu cầu plan đặt mọi chuỗi cố định ở một chỗ ngoài core.

**Alternatives considered**: Nhét câu từ chối vào thông điệp của `PlanDomainError`. Chuỗi cố định sẽ nằm trong core.

## 3. Hạn của lượt và trần HTTP

**Decision**: `run_turn` truyền cho `execute_tool` hàm không đối số `lambda: _remaining(started)`. Không truyền số tính sẵn, không truyền mốc tuyệt đối. `execute_tool` mặc định `None` là không giới hạn, chỉ để test cũ. `run_turn` luôn truyền hàm. Tool gọi hàm ngay trước mỗi lời gọi kho và chờ bằng `asyncio.wait_for` với số đó. Đây là chỗ bảo đảm FR-001. Số còn lại nhỏ hơn hoặc bằng 0 trước khi gửi: không gửi, tool trả `Không thực hiện được yêu cầu này.`, không đặt cờ hiệu lực ghi. Lượt tự rơi vào lối hết giờ ở vòng kiểm kế tiếp. Một ca đi qua `run_turn` với kho giả không trả lời, lượt trả trong hạn.

`postgrest_client` tạo `httpx.AsyncClient` với mức trần cố định 20 giây, hằng riêng trong `src/db`, ghi chú là bằng ngân sách của lượt, truyền bằng `http_client`. Không dùng đối số `timeout=` đã deprecated. Trần này không bảo đảm FR-001. Hành vi trên Worker vẫn là chưa kiểm chứng.

**Rationale**: Số tính trước `complete` đã cũ khi tool chạy. Tool đọc rồi ghi thì lời gọi sau phải thấy số đã giảm. `_now` trong `llm_turn` là đồng hồ duy nhất mà test bịt. Cổng `PlanStore` giữ nguyên nên số còn lại không tới được `SupabasePlanStore`. Timeout httpx tính theo từng pha (connect, read, write, pool), không phải tổng. Mức trần chỉ để giải phóng kết nối.

Hằng `DEFAULT_POSTGREST_CLIENT_TIMEOUT` trong gói đang cài là 120. Khi không truyền `timeout`, constructor gán 120 vào `self.timeout` nhưng tạo `httpx.AsyncClient` với `timeout=None`. `httpx` đã là phụ thuộc của `postgrest`, không thêm gói. Không dùng driver TCP.

**Alternatives considered**: Truyền một số tính sẵn. Số đó không giảm sau lúc đọc. Truyền mốc tuyệt đối. Test bịt `_now` sẽ không khống chế được hạn. Gắn phần ngân sách còn lại vào httpx. Cổng kho không có chỗ nhận số đó. Coi timeout httpx là chỗ bảo đảm FR-001. Nó không phải tổng thời gian lời gọi. Để mặc định 120 giây. Một kết nối treo không được giải phóng trong ngân sách của lượt.

## 4. Pyodide chưa kiểm chứng

**Decision**: Hành vi timeout trên Worker ghi là chưa kiểm chứng. Pytest với kho giả không mở mạng không đổi trạng thái đó.

**Rationale**: `AsyncPostgrestClient` đã chạy trên Worker ở spike khâu 2. Chưa có lần nào cắt một lời gọi treo bằng timeout trên Pyodide. Plan không chạy `pywrangler`.

**Alternatives considered**: Ghi là đạt vì httpx có tham số timeout. Chưa quan sát trên runtime Worker.

## 5. Chuỗi cố định và bản ghép

**Decision**: Một module mới `src/tools/saved_reply.py` giữ ba câu và sáu mẫu dòng. Hàm ghép cũng ở đó. `src/turns/llm_turn.py` gọi hàm đó. `src/core` không chứa các chuỗi này và không ghép câu.

**Rationale**: Tool phải trả câu từ chối mà không import `src/turns`. Lượt đã import `src/tools`. Đặt module trong `src/turns` thì tool phải import ngược.

**Alternatives considered**: Ghép chuỗi trong core. Yêu cầu plan cấm. Để mỗi file một bản sao câu. Dễ lệch chữ.

## 6. ToolResult thêm trường, JSON gửi mô hình không thêm version

**Decision**: `ToolResult` thêm trường tùy chọn, mặc định trống, để lượt biết lần ghi đã lưu, lần ghi bị bỏ, hoặc lần ghi bị từ chối. `output` gửi lại mô hình giữ nguyên chữ. JSON thành công không có `version`. Khóa bảy của dòng tool và khóa tám của dòng mô hình không thêm, không bớt.

**Rationale**: Bản ghép cần mục tiêu, tiêu đề, trạng thái, ghi chú. JSON thành công có mã. Lượt không parse JSON. Trường mới không đi vào tin nhắn gửi mô hình. Mặc định trống để chỗ dựng `ToolResult` cũ không phải thêm đối số.

**Alternatives considered**: Bắt lượt đọc JSON. Lượt sẽ phụ thuộc hình JSON và dễ in mã. Đổi khóa log để ghi version. Đụng D-014 và D-015.

## 7. Hàng có sẵn và hàm RPC

**Decision**: File migration mới `supabase/migrations/20261103205500_plans_version.sql`. Không sửa `20261025021100_plans_and_subtasks.sql`. Cột `version integer not null default 0`. Hàng có sẵn thành 0. `add_plan` được `create or replace`, giữ chữ ký `(text, jsonb)` và quyền, thân mới để JSON trả về có `version`. Hàng mới cũng là 0 nhờ default, không cần sửa danh sách cột của `insert`. `replace_plan` drop chữ ký cũ `(uuid, text, jsonb)` rồi tạo `(uuid, text, jsonb, integer)`. Kiểm version và tăng version là atomic: một `update ... where id = ... and version = expected_version`, không có hàng thì mới phân biệt `plan_missing` và `plan_version_conflict`; hoặc `select ... for update` rồi so. Không `select` rồi so mà không khóa. So bằng tay thì `is distinct from`. Hàm mới không thừa hưởng quyền hàm cũ. Sau khi tạo: `revoke all on function public.replace_plan(uuid, text, jsonb, integer) from public, anon, authenticated`, rồi `grant execute on function public.replace_plan(uuid, text, jsonb, integer) to service_role`, đúng dạng file migration cũ.

**Rationale**: Sửa file cũ làm `db reset` không còn là lịch sử đã chạy. Default 0 vừa lấp hàng cũ vừa để `insert` hiện tại không liệt kê cột mới. PostgREST không được thấy hai overload của `replace_plan`. So version không khóa thì hai `replace` cùng lúc có thể cùng thấy số cũ. Hàm mới trong Postgres không giữ grant của hàm đã drop.

**Alternatives considered**: Sửa file migration cũ. Cấm. Để overload cũ. PostgREST có thể không chọn được hàm. Bỏ default SQL và bắt `add_plan` ghi số 0 trong danh sách cột. Cũng được, nhưng đụng thân `insert` không cần thiết khi default đã đặt hàng mới ở 0. Chỉ `grant` mà không `revoke`. `public` có thể còn quyền execute.

## 8. Kiểm trên kho giả và kho local

**Decision**: Kho giả trong `tests/fakes` chứng minh timeout không mở mạng, gồm một ca đi qua `run_turn` với kho không trả lời, và chứng minh version lệch thì không đổi bộ nhớ. Kho Supabase local, sau `db reset`, có ca tuần tự và ca hai `replace` cùng lúc bằng `asyncio.gather` cùng version đã đọc. Ca cùng lúc mới chứng minh kiểm version là atomic: đúng một lần thành công, một lần từ chối, lần đọc lại là bản của lần thành công. Plan không chạy các lệnh đó.

**Rationale**: Spec bắt cả hai chỗ kiểm. Lệnh là của quickstart, để người chạy khi implement. Ca tuần tự vẫn qua nếu SQL so version không khóa.

**Alternatives considered**: Chỉ kho giả. Không thấy RPC và cột thật. Chỉ kho local. Ca treo sẽ mở mạng.
