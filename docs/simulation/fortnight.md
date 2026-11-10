# Mô phỏng 14 ngày

Bắt đầu thứ Hai 2026-11-16. Mỗi sáng 08:00 giờ Helsinki, now cố định.
Bản ghi không in mã kế hoạch hay mã việc. Kết quả JSON của tool bỏ khóa id; mọi câu không phải JSON giữ nguyên chữ của tool.
Tải là day_load sau hành động trong ngày. Mốc hôm nay là ngày của tin sáng, nên ngày trước mốc đó có tải 0.

## Quan sát

(a) Việc quá hạn không bị tự dời và vẫn đứng đầu tin sáng của kế hoạch với ngày đã qua, vì chủ bot không đánh dấu xong.
(b) Việc của ngày đã qua tính 0 giờ vào tải ngày đó và không dồn vào hôm nay.
(c) Lần gọi đầu bị cảnh báo thì không ghi gì, lần xác nhận ghi cả việc xin và các việc dời.
(d) Việc không có sức tính 3 giờ và câu cảnh báo ghi "tính tạm".

## Ngày 1 — 2026-11-16 (thứ Hai)

### Tin 08:00

```text
Không còn việc chưa làm.
```

### Hành động

1. create_plan «Học tiếng Phần Lan», ưu tiên vừa (medium)

- Nghe hội thoại, ngày 2026-11-16, sức S
- Luyện nói, ngày 2026-11-18, sức S
- Ôn từ vựng, ngày 2026-11-20, sức S

Kết quả:

```text
{"goal":"Học tiếng Phần Lan","priority":"medium","subtasks":[{"title":"Nghe hội thoại","status":"pending","note":null,"scheduled_on":"2026-11-16","effort":"S"},{"title":"Luyện nói","status":"pending","note":null,"scheduled_on":"2026-11-18","effort":"S"},{"title":"Ôn từ vựng","status":"pending","note":null,"scheduled_on":"2026-11-20","effort":"S"}]}
```

2. create_plan «Azure», ưu tiên thấp (low)

- Học module 3, ngày 2026-11-17, sức L
- Làm lab, ngày 2026-11-19, sức S
- Ôn chứng chỉ, ngày 2026-11-22, sức S

Kết quả:

```text
{"goal":"Azure","priority":"low","subtasks":[{"title":"Học module 3","status":"pending","note":null,"scheduled_on":"2026-11-17","effort":"L"},{"title":"Làm lab","status":"pending","note":null,"scheduled_on":"2026-11-19","effort":"S"},{"title":"Ôn chứng chỉ","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"}]}
```

### Tải

- 2026-11-16: 1 giờ, tính tạm 0, quỹ 8. Nghe hội thoại (Học tiếng Phần Lan, pending)
- 2026-11-17: 6 giờ, tính tạm 0, quỹ 8. Học module 3 (Azure, pending)
- 2026-11-18: 1 giờ, tính tạm 0, quỹ 8. Luyện nói (Học tiếng Phần Lan, pending)
- 2026-11-19: 1 giờ, tính tạm 0, quỹ 8. Làm lab (Azure, pending)
- 2026-11-20: 1 giờ, tính tạm 0, quỹ 8. Ôn từ vựng (Học tiếng Phần Lan, pending)
- 2026-11-22: 1 giờ, tính tạm 0, quỹ 8. Ôn chứng chỉ (Azure, pending)

## Ngày 2 — 2026-11-17 (thứ Ba)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Ba 17/11)
```

### Hành động

1. add_subtask «Thi thử» vào kế hoạch «Azure», ngày 2026-11-17, sức L (6 giờ)

Kết quả:

```text
Lần này chưa ghi. Ngày 17/11 sẽ có 12 giờ trên quỹ 8 giờ. Nếu vẫn ghi thì dời: 1. Học module 3 (kế hoạch Azure) sang 18/11.
```

2. add_subtask xác nhận «Thi thử» vào kế hoạch «Azure», ngày 2026-11-17, sức L (6 giờ). Dời: Học module 3 (kế hoạch Azure) sang 2026-11-18

Kết quả:

```text
{"goal":"Azure","priority":"low","subtasks":[{"title":"Học module 3","status":"pending","note":null,"scheduled_on":"2026-11-18","effort":"L"},{"title":"Làm lab","status":"pending","note":null,"scheduled_on":"2026-11-19","effort":"S"},{"title":"Ôn chứng chỉ","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"},{"title":"Thi thử","status":"pending","note":null,"scheduled_on":"2026-11-17","effort":"L"}]}
```

### Tải

- 2026-11-16: 0 giờ, tính tạm 0, quỹ 8. Nghe hội thoại (Học tiếng Phần Lan, pending)
- 2026-11-17: 6 giờ, tính tạm 0, quỹ 8. Thi thử (Azure, pending)
- 2026-11-18: 7 giờ, tính tạm 0, quỹ 8. Luyện nói (Học tiếng Phần Lan, pending); Học module 3 (Azure, pending)
- 2026-11-19: 1 giờ, tính tạm 0, quỹ 8. Làm lab (Azure, pending)
- 2026-11-20: 1 giờ, tính tạm 0, quỹ 8. Ôn từ vựng (Học tiếng Phần Lan, pending)
- 2026-11-22: 1 giờ, tính tạm 0, quỹ 8. Ôn chứng chỉ (Azure, pending)

## Ngày 3 — 2026-11-18 (thứ Tư)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

1. add_subtask «Đọc thêm» vào kế hoạch «Học tiếng Phần Lan», ngày 2026-11-18, sức L (6 giờ)

Kết quả:

```text
Lần này chưa ghi. Ngày 18/11 sẽ có 13 giờ trên quỹ 8 giờ. Nếu vẫn ghi thì dời: 1. Học module 3 (kế hoạch Azure) sang 19/11.
```

2. Chủ bot từ chối. Kho không đổi.

### Tải

- 2026-11-16: 0 giờ, tính tạm 0, quỹ 8. Nghe hội thoại (Học tiếng Phần Lan, pending)
- 2026-11-17: 0 giờ, tính tạm 0, quỹ 8. Thi thử (Azure, pending)
- 2026-11-18: 7 giờ, tính tạm 0, quỹ 8. Luyện nói (Học tiếng Phần Lan, pending); Học module 3 (Azure, pending)
- 2026-11-19: 1 giờ, tính tạm 0, quỹ 8. Làm lab (Azure, pending)
- 2026-11-20: 1 giờ, tính tạm 0, quỹ 8. Ôn từ vựng (Học tiếng Phần Lan, pending)
- 2026-11-22: 1 giờ, tính tạm 0, quỹ 8. Ôn chứng chỉ (Azure, pending)

## Ngày 4 — 2026-11-19 (thứ Năm)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

1. update_subtask «Luyện nói» trong kế hoạch «Học tiếng Phần Lan» thành done

Kết quả:

```text
{"goal":"Học tiếng Phần Lan","priority":"medium","subtasks":[{"title":"Nghe hội thoại","status":"pending","note":null,"scheduled_on":"2026-11-16","effort":"S"},{"title":"Luyện nói","status":"done","note":null,"scheduled_on":"2026-11-18","effort":"S"},{"title":"Ôn từ vựng","status":"pending","note":null,"scheduled_on":"2026-11-20","effort":"S"}]}
```

2. update_subtask «Làm lab» trong kế hoạch «Azure» thành done

Kết quả:

```text
{"goal":"Azure","priority":"low","subtasks":[{"title":"Học module 3","status":"pending","note":null,"scheduled_on":"2026-11-18","effort":"L"},{"title":"Làm lab","status":"done","note":null,"scheduled_on":"2026-11-19","effort":"S"},{"title":"Ôn chứng chỉ","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"},{"title":"Thi thử","status":"pending","note":null,"scheduled_on":"2026-11-17","effort":"L"}]}
```

3. reschedule_subtasks «Ôn từ vựng» trong kế hoạch «Học tiếng Phần Lan» sang 2026-11-22

Kết quả:

```text
Lần này chưa ghi. Kế hoạch Azure cũng đến hạn 2026-11-22. Hỏi chủ bot, rồi chỉ gọi lại với confirm ở lượt sau.
```

4. reschedule_subtasks xác nhận «Ôn từ vựng» trong kế hoạch «Học tiếng Phần Lan» sang 2026-11-22

Kết quả:

```text
{"goal":"Học tiếng Phần Lan","priority":"medium","subtasks":[{"title":"Nghe hội thoại","status":"pending","note":null,"scheduled_on":"2026-11-16","effort":"S"},{"title":"Luyện nói","status":"done","note":null,"scheduled_on":"2026-11-18","effort":"S"},{"title":"Ôn từ vựng","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"}]}
```

### Tải

- 2026-11-16: 0 giờ, tính tạm 0, quỹ 8. Nghe hội thoại (Học tiếng Phần Lan, pending)
- 2026-11-17: 0 giờ, tính tạm 0, quỹ 8. Thi thử (Azure, pending)
- 2026-11-18: 0 giờ, tính tạm 0, quỹ 8. Luyện nói (Học tiếng Phần Lan, done); Học module 3 (Azure, pending)
- 2026-11-19: 0 giờ, tính tạm 0, quỹ 8. Làm lab (Azure, done)
- 2026-11-22: 2 giờ, tính tạm 0, quỹ 8. Ôn từ vựng (Học tiếng Phần Lan, pending); Ôn chứng chỉ (Azure, pending)

## Ngày 5 — 2026-11-20 (thứ Sáu)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

1. add_subtask «Nghe podcast» vào kế hoạch «Học tiếng Phần Lan», ngày 2026-11-21, không sức

Kết quả:

```text
{"goal":"Học tiếng Phần Lan","priority":"medium","subtasks":[{"title":"Nghe hội thoại","status":"pending","note":null,"scheduled_on":"2026-11-16","effort":"S"},{"title":"Luyện nói","status":"done","note":null,"scheduled_on":"2026-11-18","effort":"S"},{"title":"Ôn từ vựng","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"},{"title":"Nghe podcast","status":"pending","note":null,"scheduled_on":"2026-11-21","effort":null}]}
```

2. add_subtask «Đọc tin» vào kế hoạch «Học tiếng Phần Lan», ngày 2026-11-21, không sức

Kết quả:

```text
{"goal":"Học tiếng Phần Lan","priority":"medium","subtasks":[{"title":"Nghe hội thoại","status":"pending","note":null,"scheduled_on":"2026-11-16","effort":"S"},{"title":"Luyện nói","status":"done","note":null,"scheduled_on":"2026-11-18","effort":"S"},{"title":"Ôn từ vựng","status":"pending","note":null,"scheduled_on":"2026-11-22","effort":"S"},{"title":"Nghe podcast","status":"pending","note":null,"scheduled_on":"2026-11-21","effort":null},{"title":"Đọc tin","status":"pending","note":null,"scheduled_on":"2026-11-21","effort":null}]}
```

3. add_subtask «Viết nhật ký» vào kế hoạch «Học tiếng Phần Lan», ngày 2026-11-21, không sức

Kết quả:

```text
Lần này chưa ghi. Ngày 21/11 sẽ có 9 giờ trên quỹ 8 giờ (tính tạm: 3 việc chưa có sức, mỗi việc tính 3 giờ). Nếu vẫn ghi thì dời: 1. Đọc tin (kế hoạch Học tiếng Phần Lan) sang 22/11.
```

4. Chủ bot từ chối lần thứ ba. Kho giữ hai việc không sức.

### Tải

- 2026-11-16: 0 giờ, tính tạm 0, quỹ 8. Nghe hội thoại (Học tiếng Phần Lan, pending)
- 2026-11-17: 0 giờ, tính tạm 0, quỹ 8. Thi thử (Azure, pending)
- 2026-11-18: 0 giờ, tính tạm 0, quỹ 8. Luyện nói (Học tiếng Phần Lan, done); Học module 3 (Azure, pending)
- 2026-11-19: 0 giờ, tính tạm 0, quỹ 8. Làm lab (Azure, done)
- 2026-11-21: 6 giờ, tính tạm 2, quỹ 8. Nghe podcast (Học tiếng Phần Lan, pending); Đọc tin (Học tiếng Phần Lan, pending)
- 2026-11-22: 2 giờ, tính tạm 0, quỹ 8. Ôn từ vựng (Học tiếng Phần Lan, pending); Ôn chứng chỉ (Azure, pending)

## Ngày 6 — 2026-11-21 (thứ Bảy)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 7 — 2026-11-22 (Chủ nhật)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 8 — 2026-11-23 (thứ Hai)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 9 — 2026-11-24 (thứ Ba)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 10 — 2026-11-25 (thứ Tư)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 11 — 2026-11-26 (thứ Năm)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 12 — 2026-11-27 (thứ Sáu)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 13 — 2026-11-28 (thứ Bảy)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.

## Ngày 14 — 2026-11-29 (Chủ nhật)

### Tin 08:00

```text
Học tiếng Phần Lan
Nghe hội thoại (thứ Hai 16/11)

Azure
Học module 3 (thứ Tư 18/11)
```

### Hành động

Không có.
