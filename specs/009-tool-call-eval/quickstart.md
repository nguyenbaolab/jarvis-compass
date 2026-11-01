# Quickstart: Bộ đánh giá gọi tool

Viết trước khi implement. Code eval đã merge ở 057e8a9 và lệnh tay đã chạy 2026-11-01 (AGENTS.md). Các câu "chưa có", "chưa chạy thử" bên dưới là biên bản lúc lập plan.

## Test thường

Từ gốc repo:

```text
uv run pytest tests/test_eval_load.py tests/test_eval_store.py tests/test_eval_score.py tests/test_eval_run.py tests/test_eval_result.py tests/test_eval_runner.py
```

Kỳ vọng: không mở mạng, không đọc `JARVIS_EVAL_ANTHROPIC_KEY`, không gọi `AnthropicModel`. Ca không mở mạng nằm ở `tests/test_eval_run.py`: bịt `socket.socket` để ném `AssertionError` nếu bị gọi, rồi chạy một lần với client giả.

`src/` và `tests/fakes/memory_plan_store.py` không đổi. Sau implement:

```text
git diff --exit-code -- src tests/fakes
git diff --exit-code -- (git ls-files "tests/*.py")
```

Cả hai mã `0`. File test mới là file chưa theo dõi, không nằm trong `git ls-files`. Lúc lập plan, lệnh đầu đã trả mã `0`.

## Bằng chứng trước code và mutation

Với mỗi luật trong bảng dưới, làm đúng một vòng, xong rồi mới sang luật khác.

1. Viết test đạt và test trượt, chưa viết điều kiện chấm, hoặc làm điều kiện luôn đạt. Chạy đúng test đó. Dán output fail vào ghi chú implement.
2. Viết điều kiện cho đến khi test đó xanh.
3. Làm hỏng đúng một chỗ của luật đó. Chạy lại đúng test chuyên trách. Dán output đỏ. Ca của luật khác không được là ca duy nhất đổi. Hoàn nguyên chỗ vừa hỏng.

| Luật | Test chuyên trách |
|---|---|
| Đúng tool, nhóm ghi gọi nhầm `set_subtask_note` | `test_update_group_rejects_set_note` |
| Số lần `create_plan` | `test_create_plan_count_fail_on_two` |
| Tham số bắt buộc | `test_required_param_missing_goal` |
| Tiền tố, gồm `ngày 1:` và `Giai đoạn 2:` | `test_prefix_fails_on_ordinal_words` |
| Tiền tố, NFC chuỗi dựng sẵn và chuỗi tổ hợp | `test_prefix_nfc_composed_and_combining` |
| Markdown, dòng số và gạch ngang được phép | `test_markdown_allows_numbered_and_dash` |
| Markdown, dấu `*` hoặc `**` trượt | `test_markdown_rejects_star` |
| Tự xưng | `test_self_name_rejects_phrase` |
| Kho, cập nhật trạng thái | `test_store_update_requires_new_status` |
| Lỗi chạy `missing_key` | `test_run_error_missing_key` |
| Lỗi chạy `no_model_log` | `test_run_error_no_model_log` |
| Lỗi chạy `ended_on_tool_log` | `test_run_error_ended_on_tool_log` |
| Lỗi chạy `model_error` | `test_run_error_model_error` |
| Lỗi chạy `bad_stop_reason`, `max_tokens` | `test_run_error_bad_stop_reason_max_tokens` |
| Lỗi chạy `bad_stop_reason`, `tool_use` không có `tool_requests` khi chưa đủ ba vòng | `test_run_error_bad_stop_reason_tool_use_without_requests` |
| Hết lượt tool không phải lỗi chạy, có trong số đếm | `test_cap_counted_outside_rate` |
| Giấu khóa không rỗng | `test_redact_replaces_nonempty_key` |
| Runner, khóa thiếu, rỗng, hoặc chỉ khoảng trắng | `test_runner_rejects_missing_empty_and_whitespace_key` |
| Runner, `KeyboardInterrupt` giữa bộ | `test_runner_keyboard_interrupt_writes_no_file` |
| Runner, `CancelledError` giữa bộ | `test_runner_cancelled_error_writes_no_file` |
| Runner, chạy đủ ghi đúng một file | `test_runner_full_run_writes_one_file` |
| Runner, `evals/results/` không có file mới | `test_runner_leaves_evals_results_unchanged` |

## Lệnh tay

Chưa chạy thử.

```text
$env:PYTHONPATH = "src"
$env:JARVIS_EVAL_ANTHROPIC_KEY = "<không ghi vào repo>"
uv run python -m evals.runner
```

Khóa rỗng hoặc chỉ khoảng trắng: một dòng `Thiếu JARVIS_EVAL_ANTHROPIC_KEY.` trên stderr, không file trong `evals/results/`. Ctrl+C: không file kết quả.

Bộ câu v1 chưa có trong repo cho đến khi người giữ đưa nguyên văn cho task riêng. Không bịa 50 câu để chạy lệnh này.

## Cổng constitution

Ngoại lệ constitution version `1.2.0` và D-017 đã duyệt, đúng chữ trong [plan.md](./plan.md). Hai file `.specify/memory/constitution.md` và `docs/DECISIONS.md` sửa ở implement, không sửa ở bước plan.
