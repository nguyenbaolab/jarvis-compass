-- Thu quyền bảng lịch sử dời việc và hàm trigger của nó, cùng mẫu với các bảng cũ. CLI bọc cả file trong một transaction.

revoke all on table public.subtask_date_moves from public, anon, authenticated;
revoke all on function public.subtask_date_moves_block_change() from public, anon, authenticated;
revoke truncate on table public.subtask_date_moves from service_role;
