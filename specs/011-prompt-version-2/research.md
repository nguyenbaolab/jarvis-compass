# Research: Lời hướng dẫn hệ thống phiên bản 2

Quyết định cho lát cắt prompt bản 2. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Nguyên văn chuỗi nằm ở [plan.md](./plan.md) mục Nguyên văn SYSTEM_PROMPT. Ràng buộc cách làm do người dùng chốt khi gọi `/speckit-plan`.

## 1. Sửa hằng đã có, không thêm tên

**Decision**: `src/core/system_prompt.py` giữ docstring hiện tại, giữ hai tên `PROMPT_VERSION` và `SYSTEM_PROMPT`, không thêm import, không thêm hằng, không thêm hàm. `PROMPT_VERSION` là số nguyên `2`. `SYSTEM_PROMPT` là một literal chuỗi ba dấu nháy. Không đọc file lúc chạy. Không tạo file mã nguồn mới.

**Rationale**: FR-001. Người dùng cấm file mới và cấm nạp lúc chạy. Hai tên đã đủ cho lượt và cho test.

**Alternatives considered**: Tách sáu luật thành sáu hằng rồi nối — thêm tên, người dùng cấm nếu không cần. Đọc file `.txt` lúc chạy — lệch FR-001 và lệch contract bản 1.

## 2. Không sửa lượt, catalog, eval, model

**Decision**: Không sửa `src/turns/llm_turn.py`, `src/tools/tool_definitions.py`, `evals/`, adapter Anthropic, cổng `src/core/llm.py`, model trong `src/core/plans.py`, hay migration. `DEFINITIONS_VERSION` giữ `2`. Không sửa `docs/` ở bước specify và plan.

`src/turns/llm_turn.py:65` đã ghi `"prompt_version": PROMPT_VERSION`. `src/turns/llm_turn.py:145` đã gửi `system=SYSTEM_PROMPT`. Đổi hằng là đủ để mọi lần gọi mô hình gửi bản 2 và mọi dòng nhật ký đã kết thúc ghi `prompt_version` `2`. Tập tám khóa không đổi. `definitions_version` trên dòng đó vẫn là hằng catalog `2`.

**Rationale**: FR-008 và FR-009. Sửa lượt không đổi hành vi người dùng thấy. Sửa mô tả status hoặc note của tool làm lần đo sau khác hai biến.

**Alternatives considered**: Gán số `2` ngay tại dòng log — sửa file bị cấm, và tách log khỏi hằng. Nêu `get_plan_detail` để bot tự tìm mã — người dùng cấm. Chuỗi được duyệt nêu `get_plans`. `get_plans` không chứa `get_plan_detail`.

## 3. Cách viết sáu luật

**Decision**: Chuỗi tiếng Việt ở [plan.md](./plan.md). Mỗi luật một đoạn. Câu ngắn. Không có ví dụ thứ hai ngoài câu kể việc của bản 1.

- FR-002 giữ nguyên câu `Bạn là JARVIS. Không dùng tên nhân vật nào khác.`, câu `Trả lời bằng tiếng Việt.`, câu ví dụ `Tuần này mình phải nộp báo cáo thứ Sáu và học xong chương 3`, và câu `Không tự xưng "trợ lý lập kế hoạch".` Câu ví dụ bản 1 vốn kết thúc bằng `không gọi tool`, nên cụm đó còn trong ví dụ. Đoạn luật kể việc thêm chữ `sắp làm`, rồi câu `Luật này không áp khi người dùng báo một việc đã xong hoặc bỏ; trường hợp đó theo đoạn cuối.`
- FR-003 nói `Không in đậm bằng **` vì dạng gặp trong eval là dấu `**`, không phải từ "Markdown" suông. Cùng đoạn cho phép `"1."`, gạch `"- "`, và một dòng chữ trơn như `"Ngày 1"`. Câu cuối của đoạn nói dòng đó không phải tiêu đề việc con.
- FR-004 mở bằng `Tiêu đề việc con do bạn tự đặt không có tiền tố thứ tự` và nêu đúng bốn ví dụ `"Ngày 1:"`, `"Tuần 1:"`, `"Bước 1"`, `"1."` trong cùng câu. `"1."` ở đoạn chữ trơn là số thứ tự của câu trả lời. `"1."` ở đoạn tiêu đề là tiền tố bị cấm. Hai chỗ vì hai luật.
- FR-005: `Tiêu đề việc con do bạn tự đặt phải có điểm kết thúc đo được.` Không tự đặt việc thói quen suốt một khoảng thời gian. `Tiêu đề do người dùng tự đưa được giữ nguyên từng chữ.` Không viết lại tiêu đề đó.
- FR-006: không hiện mã, không hỏi mã. `Cần mã thì tự tìm bằng get_plans với tên việc.` Câu trả lời dùng `chưa làm`, `xong`, `bỏ qua`, và cấm `pending`, `done`, `skipped` trong câu trả lời. Câu sau nói giá trị gửi vào tool là mã trong mô tả tool, không phải ba chữ tiếng Việt. Ba chữ tiếng Việt được nhắc lại ở câu đó vì cụm "ba chữ trên" có thể trỏ nhầm vào `pending`, `done`, `skipped` và cấm đúng mã tool đang dùng. Không nêu `get_plan_detail`.
- FR-007: `gọi get_plans với tên việc họ nói`. Đúng một việc thì cập nhật ngay, không hỏi xác nhận. Không khớp hoặc khớp nhiều việc thì hỏi lại. Không đòi bằng chứng. "Không hỏi mã" chỉ đứng ở đoạn FR-006.

Cụm `trợ lý lập kế hoạch` đứng một lần. Chuỗi không chứa `get_plan_detail` và không chứa `Friday`.

**Rationale**: Eval p1-d2 là lý do các câu này có mặt. Mô hình nhỏ cần một câu một ý. Spec cấm đưa ba chữ tiếng Việt vào giá trị trạng thái của tool, và cấm đổi mô tả tool.

**Alternatives considered**: Giữ câu bản 1 `Mỗi việc con phải có điểm kết thúc đo được` — câu đó áp cả tiêu đề người dùng, lệch FR-005. Viết "không Markdown" mà không nêu `**` — người dùng bắt buộc nêu dấu gặp thật. Thêm ví dụ UUID — dài thêm và không cần cho assertion chuỗi con.

## 4. Một hàm test đổi tên

**Decision**: Trong `tests/test_llm_turn.py`, đổi tên `test_system_prompt_has_four_laws` thành `test_system_prompt_has_six_laws`. Thân mới chỉ đọc `PROMPT_VERSION` và `SYSTEM_PROMPT`. Không gọi client. Danh sách khẳng định nằm ở [contracts/system-prompt.md](./contracts/system-prompt.md). Mỗi FR-002 đến FR-007 có ít nhất một chuỗi con. Thêm `PROMPT_VERSION == 2`, `get_plan_detail` không có trong chuỗi, `Friday` không có trong chuỗi, và đếm `trợ lý lập kế hoạch` đúng một lần.

Không sửa assertion nào khác trong file đó. Không sửa `tests/test_eval_result.py` và `tests/test_eval_score.py`. Hai file đó nhúng `prompt_version` `1` như dữ liệu mẫu, kể cả ca cố ý lệch `1` với `2`.

**Rationale**: FR-010 và ràng buộc người dùng. So log với hằng đã chứng minh `prompt_version` đi theo `PROMPT_VERSION`. Sửa các assert đó thành số cứng `2` là sửa test không bị yêu cầu.

**Alternatives considered**: Thêm file test mới — thêm đường dẫn mã, trong khi một hàm hiện có đã là chỗ khóa nội dung. Giữ tên `four_laws` — tên còn nói bốn luật sau khi thân đã khóa sáu luật.

## 5. Docs để B10

**Decision**: Không sửa `docs/` ở bước specify và plan. PRODUCT §9 được đồng bộ ở B10 trên cùng branch `011-prompt-version-2`, trước merge. Ảnh `docs/architecture/` nói `PROMPT_VERSION = 1`; đó là ảnh chụp theo D-016, không sửa khi hình dạng kiến trúc không đổi.

**Rationale**: Người dùng thu hẹp lệnh cấm `docs/` vào specify và plan, và chốt thời điểm đồng bộ §9. Câu này đứng dưới Constitution Check của [plan.md](./plan.md).

**Alternatives considered**: Sửa §9 ngay trong bước plan — lệch lệnh vừa chốt. Để §9 lệch sau merge — lệch câu B10 trước merge.
