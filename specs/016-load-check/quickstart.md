# Quickstart: Quét tải

`tasks.md` đã có. Chưa sửa `src/` và `docs/` trước khi T001 xong.

## Trước khi sửa mã

Dừng để chat viết D-029 theo [research.md](./research.md) mục 6. Chưa có chữ đã duyệt thì không sửa `src/` và không sửa `docs/DECISIONS.md`.

Không `db push`. Không deploy. Không `pywrangler`. Không thêm gói. Không đọc `.env` hay `.dev.vars`.

## Pytest

Không cần Supabase cho hàm thuần và tool trên `MemoryPlanStore`. Không `db reset` cho vòng này vì không có migration.

Từ gốc repo:

```text
uv run pytest
```

Kỳ vọng khi implement xong: ca mới của tải, thứ tự dời, bảy ngày đích, câu trong [contracts/load-warning.md](./contracts/load-warning.md), và ba tool không ghi ở lần gọi đầu khi vượt. Hai việc của cùng một kế hoạch cùng được dời, kết quả có đúng ngày đích của cả hai và đúng hai dòng lịch sử. Lần xin của chủ bot và một việc dời cùng kế hoạch, kết quả vẫn còn việc vừa thêm, đúng ngày, đúng số dòng lịch sử. `PROMPT_VERSION` là 8. `DEFINITIONS_VERSION` là 4. Ca bộ nhớ và ca kho đang có vẫn xanh.

## Eval

Ba lệnh tay, mỗi lệnh một bộ, mỗi lệnh một file trong `evals/results/`. Không gộp.

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi vào repo>"
uv run python -m evals.runner
```

Lần chạy bộ v1 và bộ v2 truyền đường dẫn bộ câu của bộ đó. Cách chấm từng ca hai bộ đó không đổi. Bộ v3 có tám ca của User Story 7, gồm ca hai lượt khi chủ bot từ chối. Chấm ca đó theo kho.

## Đột biến

Mỗi lô một lần, sau khi test của lô xanh. Chép file sang thư mục tạm, ghi SHA256, sửa đúng một chỗ, chạy đúng hàm, thấy đỏ, hoàn tác. SHA256 sau khi hoàn tác bằng bản chép.

- Lô 1: `day_budget` trả 7. Ca quỹ luôn là 8 phải đỏ.
- Lô 2: lần gọi đầu vẫn ghi khi vượt. Ca kho không đổi phải đỏ.
- Lô 2: lần `replace` thứ hai của cùng kế hoạch dựng từ bản gốc của `list_plans`. Ca hai việc cùng kế hoạch phải đỏ.
- Lô 3: ca từ chối coi cờ `confirm` là đạt. Ca đó phải đỏ vì chuẩn đạt là kho không đổi.
