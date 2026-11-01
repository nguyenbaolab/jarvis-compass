# Research: Từ khóa liệt kê khớp tiêu đề việc con

Quyết định cho lát cắt lọc `get_plans`. Luật nghiệp vụ nằm ở [spec.md](./spec.md). Ràng buộc cách làm do người dùng chốt khi gọi `/speckit-plan`. Nơi đặt luật miền đã chốt ở [docs/DECISIONS.md](../../docs/DECISIONS.md) D-011. Luật chữ của mục tiêu đã chốt ở [research của F04/F05](../001-create-list-plans/research.md). Tài liệu này chỉ ghi cách lát này tuân các nơi đó.

## 1. Đổi tên hàm lọc, không thêm hàm thứ hai

**Decision**: Trong `src/core/plans.py`, đổi tên `filter_by_goal_keyword` thành `filter_by_keyword`. Một hàm thuần. Không thêm hàm lọc thứ hai. `git grep -n filter_by_goal_keyword` trên repo chỉ ra ba dòng, cả ba trong `src/`:

- `src/core/plans.py:211` — định nghĩa
- `src/tools/plan_tools.py:11` — import
- `src/tools/plan_tools.py:122` — lời gọi trong `get_plans`

Không có dòng nào trong `docs/`, `AGENTS.md`, hay `specs/` đã commit. Ba dòng trên đều sửa tên. `get_plans` chỉ đổi docstring và tên hàm được gọi. Thân còn lại vẫn là `list_newest_first` rồi lọc rồi `_plans_json`.

**Rationale**: Tên cũ nói luật chỉ xét goal. Sau lát này tên đó sai. Gom mọi chỗ gọi bằng `git grep` tránh sót một import. Không có chỗ gọi ngoài hai file này.

**Alternatives considered**: Giữ tên cũ và chỉ sửa thân hàm — tên hàm trở thành câu sai trong code. Thêm `filter_by_title` rồi gộp ở tool — hai luật chữ, và tool không còn là lớp mỏng.

## 2. Một chỗ NFC rồi casefold

**Decision**: Trong `filter_by_keyword`, một hàm lồng làm đúng hai bước `unicodedata.normalize("NFC", value)` rồi `casefold`. Hàm lồng không `strip`. Kim từ khóa, mục tiêu, và từng `title` đều đi qua hàm lồng đó. Từ khóa vẫn NFC rồi `strip` trước; chuỗi rỗng sau `strip` trả nguyên danh sách, không so. `note` không được truyền vào hàm lồng. Một kế hoạch được giữ khi kim nằm trong chuỗi đã gập của `goal` hoặc của ít nhất một `title`. Vòng duyệt append kế hoạch đúng một lần.

**Rationale**: Người dùng cấm viết hai lần bước NFC rồi casefold. Hàm lồng nằm trong hàm lọc, đúng chỗ đã chốt. Không `strip` ở bước gập vì luật mục tiêu hiện tại chỉ `strip` từ khóa, không `strip` lại `goal` lúc so. `_nfc_strip` đã có vừa NFC vừa `strip`, nên không dùng cho mục tiêu và tiêu đề. `casefold` của chuỗi đã NFC là idempotent nếu gọi lại NFC, nên kim sau `strip` đi cùng hàm lồng mà không đổi luật từ khóa.

**Alternatives considered**: Hai khối NFC rồi `casefold` sát nhau, một cho goal và một cho title — đúng kiểu chép bị cấm. Dùng `_nfc_strip` cho tiêu đề — bỏ khoảng trắng hai đầu của tiêu đề lúc so, lệch luật mục tiêu. Đưa hàm gập ra tầm module — vẫn một chỗ, nhưng người dùng nói chỗ đó nằm trong hàm lọc.

## 3. Không đụng cổng, model, schema, log, prompt, eval

**Decision**: Không sửa `Plan`, `Subtask`, `SubtaskStatus`, `PlanStore`, `MemoryPlanStore`, `SupabasePlanStore`, `src/db/`, truy vấn, migration, `src/tools/schemas.py`, khóa dòng log, `SYSTEM_PROMPT`, `PROMPT_VERSION`, hay `evals/`. Không thêm thư viện. `src/core/plans.py` vẫn chỉ dùng thư viện chuẩn đã import, gồm `unicodedata`.

**Rationale**: Lọc chạy sau khi store trả mọi kế hoạch. Hai store đã trả cùng một `tuple[Plan, ...]`. Sửa truy vấn sẽ tách luật chữ khỏi hàm thuần và cần DB trong test. Schema JSON và khóa log đã khóa ở spec. Eval và prompt nằm ngoài phạm vi spec.

**Alternatives considered**: `ilike` trên PostgREST — lệch luật casefold và NFC, đụng migration, và test phải có DB. Thêm trường `search_text` lên `Plan` — đổi model, người dùng cấm.

## 4. Câu mô tả và số phiên bản

**Decision**: Trong `src/tools/tool_definitions.py`, chỉ hai sửa: `description` của `get_plans` thành đúng câu `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.` và `DEFINITIONS_VERSION` thành `2`. `input_schema` của `get_plans` giữ nguyên: một trường `keyword` kiểu string, `required` rỗng, `additionalProperties` false. Năm tool kia không đổi câu.

**Rationale**: FR-009 và FR-010. Schema không nằm trong lát này. Số `2` để dòng log và file kết quả eval phân biệt đường cơ sở, không phải vì đổi khóa log.

**Alternatives considered**: Giữ số `1` — spec cấm. Đổi schema thêm trường — spec cấm, và test router khóa đúng một trường `keyword`.

## 5. Năm assertion được sửa, và các dòng grep khác

**Decision**: Danh sách assertion được sửa nay là năm chỗ. Người dùng cho sửa cùng lát này hai dòng router đã liệt kê ở vòng plan trước, chỉ đúng hai thay đổi dưới đây. Mọi assertion cũ khác giữ nguyên.

- `test_keyword_in_subtask_only_does_not_match` (đổi tên thành `test_keyword_in_subtask_only_matches`) trong `tests/test_get_plans.py`: từ khóa `"giáo trình"` trên tiêu đề `"Mua giáo trình Nhật"` phải trả về đúng kế hoạch đó, một lần, không còn `[]`.
- `test_keyword_matches_goal_not_new_title` (đổi tên thành `test_keyword_matches_goal_and_new_title`) trong `tests/test_add_subtask.py`: từ khóa `"giáo trình"` phải trả về kế hoạch vừa thêm việc `"Mua giáo trình"`. Assertion từ khóa `"Nhật"` giữ nguyên.
- `assert DEFINITIONS_VERSION == 1` ở `tests/test_tool_router.py:97` thành `== 2`.
- `tests/test_tool_router.py:86`: `assert logged["definitions_version"] == 1` thành `== 2`. Giữ so với số cứng. Không đổi sang so với hằng `DEFINITIONS_VERSION`.
- `tests/test_tool_router.py:109`: câu mô tả cũ của `get_plans` trong `test_catalog_matches_contract` thành đúng câu FR-009 `Liệt kê kế hoạch đang có, mới hơn đứng trước, có thể lọc theo từ khóa trong mục tiêu hoặc tiêu đề việc con.`

Hai hàm test ở mục này được đổi tên theo tasks.md (chỉ đổi tên); mọi assertion cũ khác giữ nguyên. Test mới chỉ thêm trong `tests/test_get_plans.py`, mỗi test một `MemoryPlanStore`. Ca tiêu đề lưu dạng NFD gọi `store.add` với `Subtask` dựng sẵn, không đi qua `create_plan`, vì `new_subtask` đã NFC trước khi lưu. Ca `done` và `skipped` cũng dựng `Subtask` với trạng thái đó rồi `store.add`, để test không phụ thuộc tool cập nhật.

`git grep -n -E "Liệt kê kế hoạch đang có|DEFINITIONS_VERSION|giáo trình" -- tests` còn các dòng sau. Chúng không nằm trong năm chỗ.

| Dòng | Lý do không sửa |
|------|-----------------|
| `tests/test_tool_router.py:98` `isinstance(DEFINITIONS_VERSION, int)` | Không khóa số `1`. Vẫn đúng khi hằng là `2`. |
| `tests/test_llm_turn.py:323` `assert logged["definitions_version"] == DEFINITIONS_VERSION` | So với hằng, không so với số `1`. Hằng thành `2` thì assertion vẫn đúng. Không đổi dòng 86 sang kiểu so này. |
| `tests/test_add_subtask.py` các dòng `"Mua giáo trình"` ngoài hàm `test_keyword_matches_goal_not_new_title` (đổi tên thành `test_keyword_matches_goal_and_new_title`) | Khóa tiêu đề vừa thêm hoặc câu từ chối của `add_subtask`. Không gọi lọc theo cách khẳng định tiêu đề không khớp. |
| `tests/test_plan_store_contract.py`, `tests/test_subtask_skip_note.py`, `tests/test_supabase_plan_store.py` các dòng `"giáo trình"` hoặc `"Đợi giáo trình"` | Chuỗi tiêu đề hoặc ghi chú của ca store, thêm việc, và ghi chú. Không khẳng định `get_plans` bỏ kế hoạch. |

**Rationale**: Vòng plan trước không tự thêm dòng 86 và 109. Người dùng đã cho sửa đúng hai thay đổi đó khi gọi `/speckit-tasks`. Dòng 86 vẫn so với số cứng `2`, để file router tiếp tục khóa giá trị ghi ra log chứ không chỉ khóa hằng. Các dòng grep còn lại không khóa luật cũ.

**Alternatives considered**: Đổi dòng 86 thành `== DEFINITIONS_VERSION` — người dùng cấm. Sửa thêm assertion `"Nhật"` hoặc `isinstance` — không nằm trong năm chỗ.

## 6. Docs và D-014

**Decision**: Không sửa file nào trong `docs/` và không sửa `AGENTS.md`. Không sửa `docs/PRODUCT.md`. Không thêm dòng vào `docs/DECISIONS.md`.

`git grep -n -E "mục tiêu|goal|keyword|từ khóa|filter_by_goal_keyword" -- docs AGENTS.md` ra bốn dòng:

- `docs/ARCHITECTURE.md:3` — "thiết kế mục tiêu" nghĩa là thiết kế đích của các module còn lại, không phải mục tiêu kế hoạch. Câu vẫn đúng.
- `docs/PRODUCT.md:25` — F04 tạo plan với goal và subtasks. Lát này không đổi tạo kế hoạch. Câu vẫn đúng. File này dù sao cũng không sửa.
- `docs/PRODUCT.md:26` — F05 "List active plans / tìm theo keyword". Không nói từ khóa chỉ nằm ở mục tiêu. Tìm theo từ khóa vẫn đúng, chỗ khớp rộng thêm. Câu không thành sai. File không sửa.
- `docs/architecture/architecture.html:62` — chữ "goals" trong giấy phép font OFL. Không nói về lọc kế hoạch.

`AGENTS.md` không có dòng khớp. `filter_by_goal_keyword` không có trong `docs/` hay `AGENTS.md`.

D-014, nguyên văn câu căn cứ trong **Quyết định**:

> Đổi khóa thì tăng `DEFINITIONS_VERSION` hoặc ghi quyết định mới.

Không cần dòng "Cập nhật 2026-11-01". Câu đó là điều kiện khi đổi khóa dòng log: lúc đó hoặc tăng số phiên bản, hoặc ghi quyết định mới. Lát này không đổi khóa. Câu không bắt một dòng cập nhật khi số phiên bản tăng vì mô tả tool và luật khớp đổi. Câu D-014 không trở thành sai. Số `2` được khóa ở spec 010.

**Rationale**: Luật repo sửa docs khi một câu thành sai. Bốn dòng grep không có câu nào thành sai. D-014 không bị kích bởi lát này.

**Alternatives considered**: Thêm cập nhật D-014 để ghi rằng số phiên bản cũng tăng khi mô tả tool đổi — câu căn cứ không đòi việc đó, và sẽ sửa `docs/DECISIONS.md` trong khi câu quyết định vẫn đúng. Sửa F05 trong PRODUCT.md — người dùng cấm, và câu hiện tại không sai.
