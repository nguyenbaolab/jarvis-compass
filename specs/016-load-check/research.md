# Research: Quét tải

Các mục dưới là quyết định của `/speckit-plan`. Spec FR-001 đến FR-014 không bị quyết lại, trừ chỗ mục 4 ghi FR-006 đo bằng eval. Không thêm thư viện. Không thêm trường hay kiểu của `Plan` và `Subtask`.

## 1. Không đổi schema

**Decision:** Không migration. Không RPC mới. Không cột mới. FR-012 được giữ vì plan không chứng minh được schema là cần.

Đã có sẵn: `scheduled_on`, `effort`, `priority`, trạng thái, thứ tự việc, `created_order`, `version`, và dòng `subtask_date_moves` do `replace_plan` chèn khi một ngày đổi sang một ngày khác. Quỹ không lưu. Cờ `confirm` và `turn.clash_reported` sống trong một lần `run_turn`, không ở kho.

**Rationale:** Mọi số của quét tải đọc được từ dòng đang có. Cảnh báo không phải một dòng kho.

**Alternatives considered:** Cột quỹ từng ngày — bỏ, vì quỹ là hàm nhận ngày và hiện luôn trả 8. Bảng cảnh báo — bỏ, vì lần gọi đầu không ghi. RPC gộp nhiều kế hoạch trong một transaction — bỏ, vì spec chấp nhận ghi một phần và D-023 không đòi RPC mới.

## 2. Đọc kho khi lần ghi có ngày

**Decision:** Phép tính tải cần mọi kế hoạch. Một lần `list_newest_first` là một lần `list_plans`: một select PostgREST, một subrequest. Mỗi method kho mở một client httpx riêng, như Q2-05. Plan này không đo subrequest trên Worker.

Lần ghi chỉ đặt việc lên ngày đã qua, hoặc không đặt ngày, không gọi `list_plans` thêm. Đường đọc và ghi hiện tại giữ nguyên.

Lần ghi đặt việc chưa làm lên hôm nay hoặc một ngày sau hôm nay gọi đúng một `list_plans` trong lần gọi tool đó. Không gọi lần thứ hai trong cùng lần gọi. `get` của một kế hoạch bị bỏ khi đã có list, để không cộng thêm một subrequest. Kế hoạch cần ghi được lấy từ list đó.

Kết quả tool không phải JSON của mọi kế hoạch. Mô hình không nhận thân `list_plans`. Q3-04 vẫn đúng với thân phản hồi trên Worker: `list_plans` không phân trang và lớn theo số kế hoạch. Token vào của mô hình không tăng vì thân đó. Phần token tăng là lời hướng dẫn bản 8 và vài khóa mới trên ba tool.

Mỗi lần `replace` của một kế hoạch trong cùng một lần gọi tool MUST dựng từ bản trong bộ nhớ đã áp mọi lần ghi trước của chính kế hoạch đó trong lần gọi này, gồm nội dung các việc và `version`, không chỉ `version`. `version` cộng 1 sau mỗi lần thành công. Không dùng bản gốc của `list_plans` cho lần `replace` thứ hai trở đi của cùng kế hoạch. Lý do: `replace_plan` ghi lại cả danh sách việc. Việc vắng trong payload bị xóa, và `scheduled_on` có trong payload được ghi đè, nên bản cũ làm mất việc vừa thêm, hoặc đưa ngày về chỗ cũ kèm một dòng lịch sử dời ngược. Hai trường hợp có thật: hai việc của cùng một kế hoạch cùng nằm trong `load_moves`; lần chủ bot xin và một việc trong `load_moves` cùng kế hoạch. SQL vẫn làm `version + 1`. Không đọc lại kho giữa hai lần ghi. `PlanStore.replace` vẫn trả `None`.

Số dưới đây là số lời gọi kho. Một lời gọi là một subrequest.

| Lần gọi | Hôm nay | Vòng này | Đọc thêm | Subrequest thêm |
|---------|---------|----------|----------|-----------------|
| `create_plan`, có ngày hôm nay hoặc tương lai, chưa vượt | 1 `add` | 1 `list_plans` + 1 `add` | 1 | +1 |
| `create_plan`, vượt, lần đầu | 1 `add` | 1 `list_plans`, không `add` | 1 | 0 (đọc thay cho ghi) |
| `create_plan`, không ngày cần xét | 1 `add` | 1 `add` | 0 | 0 |
| `create_plan`, lượt sau đã xác nhận, không việc dời | 1 `add` | 1 `add` | 0 | 0 |
| `create_plan`, lượt sau đã xác nhận, M việc dời | 1 `add` | 1 `list_plans` + 1 `add` + M `replace` | 1 | +1+M |
| `add_subtask`, có ngày cần xét, chưa vượt | 1 `get` + 1 `replace` | 1 `list_plans` + 1 `replace` | 0 lần, `get` đổi thành `list_plans` | 0 |
| `add_subtask`, vượt, lần đầu | 1 `get` + 1 `replace` | 1 `list_plans`, không `replace` | 0 lần, `get` đổi thành `list_plans` | −1 |
| `add_subtask`, không ngày cần xét | 1 `get` + 1 `replace` | giữ nguyên | 0 | 0 |
| `add_subtask`, lượt sau đã xác nhận, M việc dời | 1 `get` + 1 `replace` | 1 `list_plans` + 1 `replace` của lần thêm + M `replace` | 0 lần so với `get` | +M |
| `reschedule_subtasks`, hạn đổi, chưa vượt | 1 `get` + 1 `list_plans` + 1 `replace` | 1 `list_plans` + 1 `replace` | −1 | −1 |
| `reschedule_subtasks`, hạn không đổi, có ngày cần xét, chưa vượt | 1 `get` + 1 `replace` | 1 `list_plans` + 1 `replace` | 0 lần, `get` đổi thành `list_plans` | 0 |
| `reschedule_subtasks`, vượt hoặc vừa vượt vừa trùng, lần đầu | 2 hoặc 3 | 1 `list_plans`, không `replace` | không đọc quá một list | không tăng |
| `reschedule_subtasks`, chỉ ngày đã qua | đường hiện tại | đường hiện tại | 0 | 0 |
| `reschedule_subtasks`, lượt sau đã xác nhận, M việc dời | 1 `replace` cộng phần đọc hiện tại | 1 `list_plans` + 1 `replace` của lần xin + M `replace` | một list, không `get` riêng | +M so với một lần dời không list |

`set_subtask_effort`, `set_plan_priority` và `update_subtask` không quét tải. Spec chỉ nêu ba lần ghi.

**Rationale:** Một list trả đủ việc, hạn, ưu tiên, thứ tự và version cho mọi kế hoạch. Thêm `get` cạnh list chỉ tốn subrequest. Q3-04 được ghi nhận, không được giải bằng schema hay phân trang trong vòng này.

**Alternatives considered:** Giữ `get` rồi list thêm — bỏ, vì thêm một subrequest mà không thêm dữ liệu. Đọc lại kho trước mỗi lần dời — bỏ, vì M lần đọc toàn bộ kế hoạch. Cache list qua lượt — bỏ, vì version có thể đổi và Worker không giữ trạng thái.

## 3. Hàm thuần và ba tool

**Decision:** `src/core/plans.py` thêm hàm thuần, chỉ thư viện chuẩn. Không thêm trường. Tool tính `today` bằng ngày lịch Helsinki của `turn.instant` rồi truyền vào. Core không đọc đồng hồ và không import `tools` hay `db`.

Hàm:

- `day_budget(day) -> int`: mọi ngày trả 8. Không gọi routine.
- `task_hours(subtask) -> int`: việc chưa làm, S = 1, M = 3, L = 6, không sức = 3. Xong và bỏ qua = 0.
- `day_load(plans, day, today) -> ...`: ngày trước `today` có tổng 0. Hôm nay và ngày sau cộng mọi việc chưa làm mang đúng ngày đó.
- Chọn ứng viên, thứ tự, đoạn đầu ngắn nhất, và ngày đích trong bảy ngày lịch sau ngày vượt. Việc vừa đặt không phải ứng viên. Hết bảy ngày thì việc ở lại và không vào danh sách.
- Kết quả là dữ liệu: ngày, tổng, quỹ, số việc tính tạm, danh sách dời. Không phải câu chữ.

Ba tool gọi các hàm đó rồi tự dựng câu, cùng kiểu `_clash_text`.

`create_plan` và `add_subtask` nhận `confirm: bool = False`, `load_moves` không bắt buộc, và `turn`. `reschedule_subtasks` đã có `confirm`. Nó nhận thêm `load_moves`. `changes` vẫn là lần chủ bot đang xin. `load_moves` là danh sách dời đã chốt, mỗi phần tử có `plan_id`, `subtask_id`, `scheduled_on`. Khóa vắng thì không có danh sách.

Lần gọi không `confirm` bỏ qua `load_moves`, tính lại, và không ghi khi vượt. `confirm` true ở lượt sau ghi lần đang xin trước, rồi đúng các phần tử `load_moves` theo thứ tự mảng. Code không thêm phần tử. Đích là ngày trong phần tử, kể cả khi chủ bot đã sửa. Không mở lại cảnh báo vượt cho ngày vừa báo.

Không có `turn` thì không xét tải và lần ghi đi đường cũ. Router luôn truyền `turn`; trường hợp này chỉ có khi gọi trực tiếp, trong test hoặc eval. `reschedule_subtasks` vẫn lỗi khi không có `turn` như trước. Không ngày cần xét thì `turn` trống vẫn ghi, như các lời gọi test hiện tại.

Cùng lượt: cả cảnh báo tải và trùng hạn đều đặt `turn.clash_reported`. Không thêm cờ. `confirm` trong cùng lượt, sau khi cờ đã đặt, vẫn ném câu `_CONFIRM_SAME_TURN` đang có. Lượt sau có `TurnContext` mới, cờ bắt đầu false. Đó là cơ chế D-026 mục 6 dùng lại.

`create_plan` và `add_subtask` không kiểm trùng hạn. `reschedule_subtasks` vẫn kiểm trùng cho lần đang xin khi lần đó không nằm trong `load_moves`. Việc trong `load_moves` không kiểm trùng. Vừa vượt vừa trùng: một lần `list_plans`, câu tải trước, câu trùng sau, không ghi. Một `confirm` ở lượt sau ghi cả hai.

Lần dời lỗi sau khi đã ghi được một phần: dừng, không thử lại, không hoàn tác. Xung đột version của một kế hoạch khác là lỗi đó. Kết quả nói việc đã dời và việc chưa dời. Lần xin của chủ bot lỗi trước thì chưa có lần dời nào.

**Rationale:** Core giữ phép tính để test không cần kho. Tool giữ câu chữ, đúng chỗ `_clash_text` đang đứng. Một cờ tránh hai cơ chế xác nhận.

**Alternatives considered:** Hàm dựng câu trong core — bỏ, vì `_clash_text` ở tool và contract khóa câu. Cờ `load_reported` riêng — bỏ, vì spec dùng lại cờ đã báo. Gộp `load_moves` vào `changes` — bỏ, vì `changes` là một kế hoạch còn danh sách dời có thể nhiều kế hoạch.

## 4. Câu cảnh báo và lời hướng dẫn

**Decision:** Câu lần gọi đầu do tool dựng. Chữ khóa ở [contracts/load-warning.md](./contracts/load-warning.md). FR-006 là luật cho mô hình: nói lại câu tool, không cộng giờ, hỏi chủ bot, chỉ gọi lại với `confirm` ở lượt sau. Pytest khóa câu của tool. Tỉ lệ mô hình nói lại đúng đo bằng eval bộ v3, không phải một assert 100% trong pytest. SC-003 phần chữ mô hình là đích của tỉ lệ đó.

`PROMPT_VERSION` lên 8. Giữ mọi câu bản 7. Thêm một đoạn: không cộng giờ và không tự chọn việc dời; nói lại câu tool; hỏi chủ bot; `confirm` true chỉ ở lượt sau; một cờ đó bao cả tải và trùng hạn khi cùng một câu tool đã nêu cả hai; gửi lại `load_moves` đúng danh sách chủ bot đã chốt, không thêm việc. Hằng không chứa ngày.

`DEFINITIONS_VERSION` lên 4. Vẫn chín tool. Không tool mới. Schema thêm khóa ở [contracts/tools.md](./contracts/tools.md). Test `test_system_prompt_has_version_seven_laws` đổi tên theo bản 8. Test khóa `DEFINITIONS_VERSION == 3` đổi thành 4.

**Rationale:** Câu tool là hợp đồng code. Câu mô hình nói với chủ bot là hành vi eval, cùng cách spec 015 chấm luật prompt.

**Alternatives considered:** Nhét cả câu mẫu vào hằng prompt và coi đó là bảo đảm — bỏ, vì mô hình vẫn có thể diễn lại khác. Để tool trả JSON số và bắt mô hình dựng câu — bỏ, vì D-024 để code nói số và spec đã chốt câu.

## 5. Eval

**Decision:** `SCORER_VERSION` lên 3. `cases_version` 1 đi đúng hàm bản 1. `cases_version` 2 đi đúng hàm bản 2. Bộ v3 là tám ca của User Story 7. Ca vượt không lấy bản thân cờ làm chuẩn đạt. Ca thứ tám là hai lượt: lượt một báo vượt, lượt hai chủ bot từ chối. Kho không đổi sau lượt hai. Mô hình đặt cờ sau lời từ chối thì kho đổi và ca trượt. Seed hai lượt theo cách spec 015: lượt hai chỉ có hai tin chữ.

Mỗi bộ chạy một lần, một file kết quả trong `evals/results/`. Cách chấm từng ca bộ 1 và bộ 2 không đổi. Không gộp ba bộ vào một lệnh.

**Rationale:** Tách hàm chấm để luật mới không làm trượt ca cũ. Ca từ chối đo việc cờ không phải sự đồng ý.

**Alternatives considered:** Sửa hàm chấm bản 2 cho cả v3 — bỏ, vì một nhánh dùng chung dễ đổi luật cũ. Coi cờ true là đạt — bỏ, vì câu 6 đã chốt chấm theo kho.

## 6. Docs khi implement

**Decision:** Bước plan không sửa `docs/`.

Trước khi sửa `src/`, dừng. Chat viết mục D-029. Cursor không tự viết quyết định. Khi chat đã có chữ, Cursor chỉ chép vào `docs/DECISIONS.md`. Chưa có chữ thì không bắt đầu lô 1.

Điểm đáng vào D-029:

1. Tải hôm nay và ngày sau là tổng giờ việc chưa làm đúng ngày đó, mọi kế hoạch. S/M/L là 1/3/6. Không sức là 3, và mức đó được chấp nhận. Ngày đã qua cộng 0. Quỹ là hàm nhận ngày, luôn trả 8, không gọi routine.
2. Vượt là tổng lớn hơn quỹ. Cảnh báo mềm. Không tự dời. Việc vừa đặt không phải ứng viên. Thứ tự và bảy ngày đích theo spec.
3. Ba tool nhận `confirm` và `load_moves`. Catalog bản 4. Lời hướng dẫn bản 8. Cờ `clash_reported` dùng cho cả tải và trùng hạn. Cùng lượt thì từ chối. Lượt sau một cờ bao cả hai.
4. Không schema mới. Lần dời vì quá tải không kiểm trùng hạn. Tạo kế hoạch và thêm việc không kiểm trùng hạn trong vòng này. Hạn chế đã biết.
5. Câu cảnh báo do tool dựng. FR-006 đo bằng tỉ lệ eval bộ v3, không phải bảo đảm 100% trong code.
6. Mỗi lần xét tải là một `list_plans`. Q3-04 được chấp nhận: thân lớn theo số kế hoạch, không trả thân đó cho mô hình.

Sau khi code xong, cùng thay đổi implement sửa:

- `docs/PRODUCT.md`: thêm hàng F20 ở §3. §7 mục 5 gọi tên F20. §8 không còn để quét tải trong nhóm chưa cấp số.
- `docs/ARCHITECTURE.md` §2: chín tool, `DEFINITIONS_VERSION` 4, `PROMPT_VERSION` 8, hàm tải trong `src/core/plans.py`.

Không sửa diagram `docs/architecture/` (D-016). Không sửa constitution. Không `db push`. Không deploy.

**Rationale:** AGENTS.md bắt dừng khi chạm `docs/DECISIONS.md`. PRODUCT và ARCHITECTURE phải khớp code, nhưng không phải quyết định mới.

**Alternatives considered:** Để Cursor viết D-029 — bỏ, vì luật repo. Sửa diagram trong cùng vòng — bỏ, vì D-016.
