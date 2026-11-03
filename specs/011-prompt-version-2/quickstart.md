# Quickstart: Lời hướng dẫn hệ thống phiên bản 2

Kiểm chứng hằng prompt trên CPython, không cần Supabase, Wrangler, hay WSL. Nguyên văn chuỗi nằm ở [plan.md](./plan.md). Khẳng định nằm ở [contracts/system-prompt.md](./contracts/system-prompt.md). Model nằm ở [data-model.md](./data-model.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và uv.
- Không tạo file `.env`. Test này không đọc cấu hình và không gọi mạng.
- `tasks.md` đã tạo `specs/011-prompt-version-2/allowed-files.txt` với ba dòng ghi trong [plan.md](./plan.md). Bước plan chưa tạo file đó.

## Chuẩn bị

```text
uv sync
```

## Chạy

```text
uv run pytest
```

Kỳ vọng: pass, exit code 0. Không tắt test và không bỏ test. Hàm `test_system_prompt_has_six_laws` pass. Các hàm khác trong `tests/test_llm_turn.py` pass mà không đổi assertion.

```text
.\scripts\check.ps1 -AllowList specs/011-prompt-version-2/allowed-files.txt
```

Kỳ vọng: exit code 0. Mười hàng kiểm sau đây đều `pass`:

- Test
- Changed files
- Core imports
- Workers imports
- Turns imports
- Tools imports
- SDK imports
- Env reads
- Eval tests imports
- Eval env reads

Hàng `Repo review` là hàng thông tin, không tính vào mười hàng đó. Exit code 0 không phụ thuộc hàng đó.

## Việc lát này phải chứng minh

Đọc hằng, không gọi mô hình. `PROMPT_VERSION` là `2`. `SYSTEM_PROMPT` chứa các chuỗi con ở [contracts/system-prompt.md](./contracts/system-prompt.md). Chuỗi không chứa `get_plan_detail` và không chứa `Friday`. Cụm `trợ lý lập kế hoạch` đứng một lần.

`src/tools/tool_definitions.py` không đổi, nên `DEFINITIONS_VERSION` vẫn `2`. Test log đã có so `definitions_version` với hằng đó và so `prompt_version` với `PROMPT_VERSION`. Không sửa hai assertion ấy.
