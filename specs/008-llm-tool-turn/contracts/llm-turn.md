# Contract: Một lượt

File: `src/turns/llm_turn.py`. Hàm công khai:

```text
async def run_turn(
    user_message: str,
    history: Sequence[TextMessage],
    *,
    store: PlanStore,
    api_key: str | None,
    client: ModelClient,
    log: Callable[[str], None] | None = None,
) -> str
```

`client` là đối tượng có `model: str` và `complete` như [model-port.md](./model-port.md). Lượt không import adapter.

## Khóa

`api_key is None` hoặc `api_key == ""`: ném exception có `str` đúng `Thiếu ANTHROPIC_API_KEY.` Không gọi `complete`. Không đọc `os.environ`. Không strip. Chuỗi khác rỗng, kể cả chỉ khoảng trắng, đi tiếp và được truyền vào `complete`.

## Thứ tự một lần gọi mô hình

1. Nếu `_now() - mốc > 20`: trả `Chưa liên lạc được để trả lời lúc này.` Không gọi `complete`.
2. `await client.complete(...)`. `timeout` là `20 - (_now() - mốc)`. `system` là `SYSTEM_PROMPT`. `tools` là chính `TOOL_DEFINITIONS`.
3. Ghi một dòng log tám khóa của lần gọi vừa kết thúc.
4. Xử lý `stop_reason` như dưới.

`CancelledError` từ `complete` đi ra khỏi `run_turn`. Lần đó không bắt buộc có dòng log. Các lần đã ghi thì giữ dòng.

`Exception` khác: dòng log lấy `model` từ `client.model`. `error_type` là `ModelError.class_name` nếu đó là `ModelError`, còn lại là `type(error).__name__`. Kết quả là câu lỗi phía mô hình. Thông điệp exception không vào kết quả và không vào dòng log. Không gọi `complete` lần nữa.

## stop_reason

- `end_turn`: trả `text`. Không gọi `execute_tool`.
- `tool_use` khi lượt đã có 3 vòng: không gọi `execute_tool`, không gọi `complete`, trả `Chưa trả lời xong yêu cầu này.`
- `tool_use` khi chưa đủ 3 vòng và có ít nhất một yêu cầu: tăng số vòng, chạy mọi yêu cầu bằng `execute_tool` theo thứ tự, rồi quay lại bước 1 với mọi kết quả.
- Mọi giá trị khác, gồm `max_tokens` và giá trị trống: không gọi `execute_tool`, không gọi `complete`, trả câu lỗi phía mô hình.

## execute_tool

Mỗi yêu cầu gọi:

```text
await execute_tool(name, tool_input, store=store, log=cùng_hàm_log)
```

Trước mỗi lần gọi, đo ngân sách. Hết giờ thì không gọi lần đó và không gọi phần còn lại. Sau khi một lần đã bắt đầu, lượt chờ đến khi nó trả về. Không hủy nó.

`output` gửi lại nguyên. `is_error` là ngược của `success`. Kết quả không thay câu miền bằng câu lỗi phía mô hình. Lượt trả câu miền cho người gọi chỉ khi mô hình sau đó không đòi tool và trả đúng câu đó như văn bản của nó. Câu miền không phải kết quả của lượt nếu mô hình còn trả một văn bản khác.

Hàm log truyền vào `execute_tool` là cùng object lượt dùng cho dòng mô hình. Khi `log` của `run_turn` là `None`, lượt tạo một hàm in một dòng và truyền đúng hàm đó.

## Log

Một dòng cho một lần `complete` đã kết thúc. `json.dumps(..., ensure_ascii=False)`. Khóa đúng thứ tự ở [data-model.md](../data-model.md).

Lần `complete` trả về `ModelResponse`: khóa `model` của dòng log lấy từ `ModelResponse.model`, kể cả khi lượt sau đó từ chối `stop_reason`. `prompt_version` là `PROMPT_VERSION`. `definitions_version` là `DEFINITIONS_VERSION`. `duration_ms` lấy từ hai lần `_now` quanh `complete`: số nguyên mili giây, bằng 0 khi hiệu bằng 0 hoặc âm.

Ghi log nằm trong `try/except Exception` riêng quanh hàm log. Nuốt lỗi đó. Không nuốt `CancelledError`. Kết quả của lượt vẫn trả.

## Đồng hồ

```text
def _now() -> float
```

Thân là `return time.monotonic()`. Test bịt `turns.llm_turn._now`.
