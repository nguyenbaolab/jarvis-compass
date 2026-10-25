# Quickstart: Lưu kế hoạch vào kho Supabase

Kiểm chứng F03. Hành vi cổng nằm ở [contracts/plan-store.md](./contracts/plan-store.md). Bảng nằm ở [data-model.md](./data-model.md). Cách chọn RPC, trigger, và skip nằm ở [research.md](./research.md).

## Điều kiện

- Đứng ở gốc repo.
- Python 3.13+ và uv.
- Node đủ để chạy `npx`. Không thêm `package.json`.
- Docker, chỉ khi chạy test kho thật.
- Không tạo `.env`. Không đọc và không ghi `.dev.vars`. Không dán khóa vào file trong repo.

## Chạy khi không có kho

```text
uv sync
uv run pytest
```

Kỳ vọng: 129 test hiện có pass. Test ánh xạ trạng thái lạ pass. Test chặn host xa pass. Test cần kho bị skip khi `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY` không có trong tiến trình. Mỗi dòng skip đọc được và bắt đầu bằng `Kho local không chạy:`. Exit code của pytest vẫn là 0 khi chỉ có skip, không có fail.

Lệnh này không cần `supabase start`. Không đặt hai biến đó thành URL kho cloud: host không phải `127.0.0.1` hoặc `localhost` thì pytest thất bại trước khi gọi mạng, với câu `Test kho chỉ chạy trên kho local.`

## Bật kho local

CLI ghim `2.122.0`. Lần đầu, trong gốc repo:

```text
npx --yes supabase@2.122.0 init
npx --yes supabase@2.122.0 start
npx --yes supabase@2.122.0 db reset
npx --yes supabase@2.122.0 status
```

`init` tạo `supabase/config.toml`. Migration lược đồ nằm ở `supabase/migrations/` và được `db reset` áp lên kho trống. Không tạo bảng trên dashboard.

`status` in URL API local và khóa service role. Export hai giá trị đó vào tiến trình sẽ chạy pytest, dưới tên `JARVIS_TEST_SUPABASE_URL` và `JARVIS_TEST_SUPABASE_KEY`. Không dùng `SUPABASE_URL` hay `SUPABASE_KEY` cho pytest. URL phải có host `127.0.0.1` hoặc `localhost`. Tên nhãn trong output của CLI lấy từ chính lệnh `status` của bản `2.122.0` khi implement ghi lệnh này sang AGENTS.md. Không chép khóa vào `.env.example`, `.env`, hay `.dev.vars`.

`db reset` dựng lại lược đồ và xóa dữ liệu. Test kho còn tự xóa `subtasks` rồi `plans` trước mỗi ca, trong `tests/supabase_plan_db.py`, bằng client lấy từ `src/db/client.py`. Không cần reset tay trước mỗi `uv run pytest`.

## Chạy khi kho đang lên

Cùng một lệnh:

```text
uv run pytest
```

Kỳ vọng thêm: param hợp đồng trên bộ nhớ và trên Supabase cùng pass; test mốc thời gian và `note` là `NULL` pass; test thiếu cấu hình pass mà không cần mạng. Test trạng thái lạ đã pass cả khi không có kho.

Riêng lát này:

```text
uv run pytest tests/test_plan_store_contract.py tests/test_supabase_plan_store.py tests/test_plan_row_mapping.py tests/test_settings_supabase.py
```

## Ca cần thấy khi kho đang lên

1. Kho vừa `db reset`, thêm “Học tiếng Nhật” với “Học hiragana” rồi “Luyện 10 phút mỗi ngày”, rồi thêm “Viết báo cáo”. Liệt kê đặt báo cáo trước. Mở đúng id thì ra đúng việc theo thứ tự đã lưu. Mở `"1"` và `"2"` thì không có kế hoạch.
2. `replace` một id không có, trên bộ nhớ và trên Supabase, cùng câu `Không có kế hoạch với danh tính này.` Số kế hoạch không tăng.
3. Đổi trạng thái, thêm việc, đặt ghi chú “Đợi giáo trình”, rồi xóa ghi chú. Đọc lại khớp. Cột `note` lúc không còn ghi chú là `NULL`.
4. Ghi lại cùng trạng thái thì hai mốc việc đó giữ nguyên. Đổi mã trạng thái thì `created_at` giữ nguyên và mốc trạng thái đổi. Việc mới có mốc riêng; việc cũ không nhận mốc của lần thêm.
5. Hàm ánh xạ nhận dòng giả có mã khác ba mã. Lỗi đúng câu `Trạng thái việc con đã lưu không hợp lệ.` Ca này không cần kho.
6. Dựng store bằng dict thiếu URL hoặc thiếu khóa. Lỗi nêu tên đang thiếu, không chứa giá trị khóa, và không mở socket.
7. URL có host không phải `127.0.0.1` hoặc `localhost` làm test thất bại với câu `Test kho chỉ chạy trên kho local.`, và không mở socket.

## Ngoài lát này

Không thêm route spike. Không `pywrangler deploy`. Không đẩy migration lên project Supabase cloud.
