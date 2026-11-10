# Feature Specification: Quét tải

**Feature Branch**: `016-load-check`

**Created**: 2026-11-10

**Status**: Draft

**Input**: User description: "F20 quét tải (D-024 mục 4, 5, 7, 8; D-026 mục 6; D-027 mục 8): khi một lần ghi đặt việc lên một ngày, code cộng giờ của các việc chưa làm mang ngày đó và báo khi tổng vượt quỹ giờ. Cảnh báo mềm, không chặn, không bao giờ tự dời việc. Trong phạm vi: tải của một ngày là tổng giờ của mọi việc chưa làm mang đúng ngày đó, ở mọi kế hoạch; giờ lấy từ sức S, M, L qua EFFORT_HOURS (1, 3, 6); việc chưa có sức tính như M và lời cảnh báo ghi rõ "tính tạm"; việc đã xong và việc bỏ qua không tính. Quỹ giờ do một hàm trong core nhận ngày và hiện luôn trả 8. Kiểm ở tạo kế hoạch có ngày, thêm việc có ngày, và dời ngày. Khi vượt, lần gọi đầu không ghi mà trả cảnh báo (ngày, tổng giờ, quỹ, có tính tạm hay không) kèm danh sách việc sẽ bị dời; mô hình chỉ nói lại; chỉ ghi khi chủ bot xác nhận ở lượt sau, dùng lại cờ xác nhận và cờ đã báo của kiểm trùng hạn. Code chọn việc dời: ưu tiên kế hoạch thấp nhất trước, bằng nhau thì việc có ngày muộn hơn trước; chủ bot sửa được danh sách. Việc dời đi qua đường ghi có sẵn nên có dòng lịch sử. Bộ câu eval phiên bản 3, chạy lại bộ 1 và 2 một lần. Tám câu ở mục cuối không được chọn ở bước specify."

## Clarifications

### Session 2026-11-10

- Q: Khi mọi việc có thể bị dời đang nằm cùng một ngày vượt quỹ, khóa thứ hai để xếp việc nào được dời trước là gì? → A: Hạn của kế hoạch, hạn muộn hơn được dời trước. Hạn bằng nhau thì kế hoạch được tạo trước được dời trước. Hạn là ngày muộn nhất trong các việc chưa làm có ngày. Việc đã xong và việc bỏ qua không tính.
- Q: Việc vừa được đặt lên một ngày vượt quỹ có nằm trong danh sách việc sẽ bị dời không, khi kế hoạch của việc đó có ưu tiên thấp nhất? → A: Không. Chỉ việc đã có trên ngày đó từ trước là ứng viên. Việc vừa đặt ở lại ngày đó. Việc vừa đặt vẫn tính vào tổng giờ.
- Q: Khi chọn việc để dời khỏi một ngày vượt quỹ, kế hoạch chưa có ưu tiên đứng ở đâu so với ưu tiên cao, vừa và thấp? → A: Trống bằng vừa. Khi xếp việc dời, ưu tiên trống ngang với vừa. Giá trị ưu tiên đã lưu vẫn trống, không bị ghi thành vừa.
- Q: Việc bị dời khỏi ngày vượt quỹ được đề xuất sang ngày nào, và nếu ngày đó cũng vượt thì việc đó đi tiếp đến đâu? → A: Ngày gần nhất còn đủ quỹ, tìm trong 7 ngày lịch ngay sau ngày vượt. Hết 7 ngày mà không có ngày đủ quỹ thì việc ở lại ngày gốc.
- Q: Khi một việc được dời nằm ở kế hoạch khác và một lần ghi thành công còn lần sau bị lỗi, phần đã ghi được xử lý thế nào? → A: Giữ phần đã ghi, không hoàn tác. Thứ tự ghi là lần chủ bot đang xin trước, rồi các lần dời theo thứ tự danh sách. Lỗi thì dừng, không tự thử lại, và báo việc nào đã dời cùng việc nào chưa. Lỗi gồm xung đột phiên bản của một kế hoạch khác. Chủ bot muốn dời tiếp thì xin lại. Trạng thái xấu nhất đã được chấp nhận: việc mới nằm trên ngày vượt và ngày đó vẫn vượt.
- Q: Hai việc cùng một kế hoạch, cùng nằm trên ngày vượt quỹ, thì việc nào được dời trước? → A: Việc đứng sau trong thứ tự đã lưu được dời trước. Không xét số giờ.
- Q: Việc chưa làm mang một ngày đã qua, và việc chưa làm mang hôm nay, có được tính vào tải của đúng ngày đó không? → A: Hôm nay có tính. Ngày đã qua không tính. Việc của ngày đã qua không cộng vào hôm nay.
- Q: Khi một việc được dời làm đổi hạn của kế hoạch, và hạn mới trùng hạn một kế hoạch khác, kiểm trùng hạn xử lý thế nào? → A: Lần dời vì quá tải không kiểm trùng hạn. Lần dời đó vẫn ghi khi hạn mới trùng hạn một kế hoạch khác.
- Q: Khi một lần ghi làm nhiều ngày vượt quỹ, và khi lần đó cũng trùng hạn, chủ bot nhận các cảnh báo thế nào trong lần gọi đầu? → A: Cùng lần gọi đầu trả mọi ngày vượt, mỗi ngày một cảnh báo, rồi mới tới trùng hạn. Không ghi. Một cờ xác nhận ở lượt sau bao cả hai. Kiểm trùng hạn không bật ở tạo kế hoạch và thêm việc trong vòng này. Phần trùng hạn chỉ áp cho tool dời ngày. Hạn chế đã biết, bật khi thấy thiếu.
- Q: Một cờ xác nhận ở lượt sau có đủ để ghi không, và eval kiểm sự đồng ý của chủ bot bằng cách nào? → A: Giữ cơ chế đang có. Eval chấm theo kho. Bộ phiên bản 3 có ca hai lượt: lượt một báo vượt, lượt hai chủ bot từ chối. Kho không đổi sau lượt hai. Mô hình đặt cờ sau lời từ chối thì kho đổi và ca trượt.
- Q: Mức cảnh báo khi việc chưa có sức tính 3 giờ có chấp nhận được không, và mô hình nói cảnh báo cùng danh sách dời thế nào? → A: Mức đó được chấp nhận. Mô hình nói: "Lần này chưa ghi. Ngày 12/11 sẽ có 11 giờ trên quỹ 8 giờ (tính tạm: 2 việc chưa có sức, mỗi việc tính 3 giờ). Nếu vẫn ghi thì dời: 1. Học module 3 (kế hoạch Azure) sang 13/11. 2. Luyện nói (kế hoạch Phần Lan) sang 14/11." Số, tên và ngày là phần code đã trả. Rồi hỏi chủ bot. Chỉ gọi lại với confirm ở lượt sau.

## User Scenarios & Testing *(mandatory)*

Chủ bot đặt thêm việc vào một ngày đã có việc. Bot cần nói ngày đó có quá giờ hay không, trước khi ghi. Cộng giờ và chọn việc dời là việc của code. Mô hình không làm số học. Mô hình chỉ nói lại. Chủ bot quyết định có ghi hay không. Bot không tự dời việc.

Vòng này là mục 5 trong thứ tự [docs/PRODUCT.md](../../docs/PRODUCT.md) §7: quét tải, và là một phần mốc v1 ở [D-028](../../docs/DECISIONS.md). Luật lấy từ [D-024](../../docs/DECISIONS.md) mục 4, 5, 7 và 8, từ [D-026](../../docs/DECISIONS.md) mục 6, và từ [D-027](../../docs/DECISIONS.md) mục 8. [D-027](../../docs/DECISIONS.md) đã chuyển việc hằng ngày và sự kiện đột xuất ra ngoài compass, nên vòng này không cộng hai loại đó vào tải.

Câu 9, câu 10, câu 3, câu 1, câu 4, câu 11, câu 2, câu 7, câu 5, câu 6 và câu 8 đã chốt ở Clarifications. Không còn câu mở.

### User Story 1 - Tải một ngày là tổng giờ việc chưa làm (Priority: P1)

Tải của một ngày là tổng giờ của mọi việc chưa làm mang đúng ngày đó, ở mọi kế hoạch. Giờ lấy từ sức. S là 1 giờ, M là 3 giờ, L là 6 giờ. Ba số này nằm ở một chỗ cấu hình, EFFORT_HOURS. Việc chưa có sức được cộng 3 giờ, như M. Việc đã xong và việc bỏ qua không được cộng. Việc không mang ngày đó không được cộng, kể cả khi việc nằm ở kế hoạch khác.

Hôm nay tính như một ngày sau hôm nay: việc chưa làm mang đúng hôm nay cộng vào tải của hôm nay. Hôm nay là ngày lịch Helsinki của mốc đầu lượt. Ngày đã qua không tính: việc chưa làm mang một ngày trước hôm nay cộng 0 vào tải của ngày đó và cộng 0 vào tải của hôm nay.

Mức cảnh báo được chấp nhận. Việc chưa có sức vẫn cộng 3 giờ. Ba việc như vậy là 9 giờ và vượt quỹ 8 giờ.

**Why this priority**: Không có tổng giờ thì không có quét tải. [D-024](../../docs/DECISIONS.md) mục 5 và mục 7 giao phép cộng cho code.

**Independent Test**: Dựng vài việc chưa làm trên một ngày sau hôm nay, ở hai kế hoạch, với S, M, L, một việc không sức, một việc đã xong và một việc bỏ qua. Đọc tổng giờ dùng để so với quỹ. Không cần ghi danh sách dời.

**Acceptance Scenarios**:

1. **Given** một ngày sau hôm nay và các việc chưa làm mang đúng ngày đó ở hai kế hoạch, **When** code tính tải của ngày đó, **Then** tổng bằng số giờ của các việc chưa làm đó. S cộng 1, M cộng 3, L cộng 6. Việc đã xong, việc bỏ qua, và việc mang ngày khác cộng 0.
2. **Given** một việc chưa làm trên ngày đó không có sức, **When** code tính tải, **Then** việc đó cộng 3 giờ.
3. **Given** mọi việc chưa làm trên ngày đó đều có sức, **When** có cảnh báo vượt cho ngày đó, **Then** cảnh báo không nói việc đang được tính tạm.
4. **Given** tổng của ngày đó có ít nhất một việc chưa làm không có sức, **When** có cảnh báo vượt cho ngày đó, **Then** cảnh báo ghi rõ "tính tạm".
5. **Given** vài việc chưa làm mang đúng hôm nay, **When** code tính tải của hôm nay, **Then** các việc đó được cộng giờ như một ngày sau hôm nay.
6. **Given** vài việc chưa làm mang một ngày trước hôm nay, **When** code tính tải của ngày đó và tải của hôm nay, **Then** các việc đó cộng 0 vào cả hai tổng.

---

### User Story 2 - Quỹ giờ nhận một ngày và hiện là 8 (Priority: P1)

Quỹ giờ của một ngày do một hàm trong phần lõi trả về. Hàm nhận ngày làm tham số. Hiện hàm trả 8 với mọi ngày. Nơi gọi hàm này không phải đổi khi sau này routine cấp một số khác cho một ngày. Hàm không hỏi routine. Compass không gọi routine.

Vượt khi tổng lớn hơn quỹ của ngày đó. Tổng bằng quỹ thì chưa vượt. Ngày nghỉ, lệnh sửa quỹ từng ngày, và chỗ lưu quỹ riêng từng ngày không thuộc vòng này.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 4 chốt quỹ 8 giờ. [D-027](../../docs/DECISIONS.md) mục 8 đòi quỹ là hàm của ngày, mặc định 8, để routine cấp số thật sau.

**Independent Test**: Gọi hàm quỹ với một ngày sau hôm nay, một ngày là hôm nay, và một ngày đã qua. Đọc số trả về. So một tổng bằng 8 và một tổng bằng 9 với quỹ 8.

**Acceptance Scenarios**:

1. **Given** bất kỳ ngày lịch nào, **When** hàm quỹ được gọi với ngày đó, **Then** kết quả là 8 giờ.
2. **Given** tổng giờ của một ngày là 8 và quỹ của ngày đó là 8, **When** so với quỹ, **Then** ngày đó chưa vượt.
3. **Given** tổng giờ của một ngày là 9 và quỹ của ngày đó là 8, **When** so với quỹ, **Then** ngày đó vượt.
4. **Given** hàm quỹ, **When** đọc nơi nó lấy số, **Then** nó không hỏi routine.

---

### User Story 3 - Vượt quỹ thì lần gọi đầu chưa ghi (Priority: P1)

Kiểm chạy ở mọi lần ghi đặt một việc chưa làm lên hôm nay hoặc lên một ngày sau hôm nay: tạo kế hoạch có việc mang ngày, thêm việc có ngày, và dời việc sang một ngày. Lần ghi không đặt việc nào lên một ngày thì không chạy kiểm này. Lần ghi chỉ đặt việc lên một ngày đã qua không cảnh báo vượt vì tải.

Tổng đem so là tổng sau lần ghi nếu lần ghi được lưu và chưa dời bớt việc nào. Tổng gồm việc vừa được đặt lên ngày đó và mọi việc chưa làm khác đang mang đúng ngày đó. Việc lần ghi này chuyển khỏi ngày đó không còn nằm trong tổng của ngày đó.

Khi ít nhất một ngày vượt, lần gọi đầu không ghi. Kho không đổi. Kết quả trả về một cảnh báo cho ngày vượt: ngày, tổng giờ, quỹ, và có tính tạm hay không, kèm danh sách việc sẽ bị dời nếu chủ bot vẫn muốn ghi. Đây là cảnh báo mềm. Nó không chặn chủ bot ghi ở lượt sau. Nó không phải một lỗi làm hỏng lần ghi.

Khi lần gọi đầu chưa ghi vì vượt, câu mô hình nói theo FR-006.

Chỉ ghi khi chủ bot xác nhận ở lượt sau. Vòng này dùng lại cơ chế cờ xác nhận và cờ đã báo của kiểm trùng hạn ở [D-026](../../docs/DECISIONS.md) mục 6. Lần gọi đầu không có cờ xác nhận. Cờ xác nhận trong cùng lượt, sau khi vừa báo vượt, không được ghi. Cờ không phải bằng chứng chủ bot đã đồng ý. Lần ghi đã xác nhận thì được lưu, kể cả khi ngày vừa báo vẫn còn vượt vì chủ bot đã rút bớt danh sách dời. Lần ghi đó không mở một cảnh báo vượt mới cho chính ngày vừa báo.

Một lần ghi làm nhiều ngày vượt thì lần gọi đầu trả mọi ngày đó, mỗi ngày một cảnh báo. Cảnh báo tải đứng trước. Nếu lần đang xin là tool dời ngày và cũng trùng hạn, thông tin trùng đứng sau các cảnh báo tải, trong cùng kết quả. Không ghi. Một cờ xác nhận ở lượt sau bao cả tải và trùng hạn, vì chủ bot đã thấy cả hai trong cùng một tin. Tạo kế hoạch và thêm việc không kiểm trùng hạn trong vòng này. Đó là hạn chế đã biết. Bật khi thấy thiếu.

Cơ chế cờ dùng lại nguyên là đủ. Không cần bảo đảm mạnh hơn. Eval chấm theo kho. Bộ phiên bản 3 có ca hai lượt: lượt một báo vượt, lượt hai chủ bot nói thôi không thêm nữa. Kho không đổi sau lượt hai. Nếu mô hình đặt cờ sau lời từ chối thì kho đổi và ca trượt. Ca này chạy bằng seed hai lượt, theo cách spec 015 đã làm.

Mẫu câu tool đã chốt ở [contracts/load-warning.md](./contracts/load-warning.md). Mô hình nói theo FR-006. Số, tên và ngày trong một lượt thật là phần code đã trả ở lượt đó.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 7: cảnh báo mềm, không tự dời, chủ bot xác nhận rồi mới ghi. Kiểm lúc tạo và lúc thêm việc là phần [D-026](../../docs/DECISIONS.md) mục 6 để lại cho vòng này, về phía quét tải.

**Independent Test**: Với một ngày sau hôm nay còn trống, ghi một việc 3 giờ và thấy kho đổi. Dựng tổng 9 giờ rồi gọi lần đầu một lần ghi đặt thêm việc lên ngày đó. Đọc kho và đọc kết quả. Chưa cần danh sách dời đúng thứ tự.

**Acceptance Scenarios**:

1. **Given** một ngày sau hôm nay có tổng sau lần ghi không lớn hơn quỹ, **When** tạo kế hoạch có việc mang ngày đó, hoặc thêm việc mang ngày đó, hoặc dời một việc sang ngày đó, **Then** lần ghi được lưu. Không có cảnh báo vượt.
2. **Given** một ngày sau hôm nay có tổng sau lần ghi lớn hơn quỹ, **When** một trong ba lần ghi đó được gọi lần đầu, **Then** kho không đổi. Kết quả có ngày đó, tổng giờ đã so, quỹ của ngày đó, và có tính tạm hay không.
3. **Given** lần gọi đầu đã trả cảnh báo vượt, **When** cùng lượt gọi lại với cờ xác nhận, **Then** kho vẫn không đổi.
4. **Given** chủ bot đã xác nhận ở lượt sau và lần ghi được gọi lại theo cơ chế cờ của kiểm trùng hạn, **When** lần ghi chạy, **Then** việc đặt lên ngày được lưu. Ngày vừa báo không bị cảnh báo vượt thêm một lần chỉ vì tổng vẫn lớn hơn quỹ.
5. **Given** code đã trả một tổng giờ, **When** mô hình nói với chủ bot, **Then** mô hình nói lại tổng đó. Mô hình không đưa một tổng khác.
6. **Given** code trả ngày 12/11, tổng 11 giờ, quỹ 8 giờ, hai việc chưa sức, và danh sách dời Học module 3 của kế hoạch Azure sang 13/11 rồi Luyện nói của kế hoạch Phần Lan sang 14/11, **When** mô hình nói với chủ bot, **Then** lời nói đúng FR-006 cho ngày, tổng, quỹ, số việc tính tạm và danh sách dời đó. Mô hình hỏi chủ bot và không gọi lại với confirm trong cùng lượt.
7. **Given** một ngày trước hôm nay đã có nhiều việc chưa làm, **When** một lần ghi đặt thêm một việc lên đúng ngày đó, **Then** lần ghi được lưu. Không có cảnh báo vượt vì tải.
8. **Given** một lần ghi làm hai ngày sau hôm nay đều vượt quỹ, **When** lần gọi đầu trả kết quả, **Then** kết quả có cảnh báo của cả hai ngày, mỗi ngày có ngày, tổng giờ, quỹ và có tính tạm hay không. Kho không đổi.
9. **Given** tool dời ngày vừa làm một ngày vượt vừa làm hạn trùng một kế hoạch khác, **When** lần gọi đầu trả kết quả, **Then** cảnh báo tải đứng trước thông tin trùng hạn. Kho không đổi. **When** chủ bot xác nhận ở lượt sau bằng một cờ, **Then** lần ghi được lưu.

---

### User Story 4 - Code chọn việc dời, chủ bot sửa được danh sách (Priority: P1)

Khi một ngày vượt, code lập danh sách việc sẽ bị dời nếu chủ bot vẫn muốn ghi. Ứng viên chỉ là việc chưa làm đã có trên ngày đó từ trước lần ghi. Việc vừa được đặt lên ngày đó ở lại ngày đó và không nằm trong danh sách. Việc vừa đặt vẫn tính vào tổng giờ. Khi xếp việc dời, ưu tiên trống bằng vừa. Giá trị ưu tiên đã lưu vẫn trống. Thứ tự dời là thấp trước, rồi đến trống và vừa, rồi đến cao. Trống và vừa là cùng một mức. Cùng mức thì xếp kế hoạch có hạn muộn hơn trước. Hạn là ngày muộn nhất trong các việc chưa làm có ngày. Việc đã xong và việc bỏ qua không tính. Cùng mức và cùng hạn thì kế hoạch được tạo trước đứng trước. Hai việc cùng một kế hoạch, cùng nằm trên ngày vượt, thì việc đứng sau trong thứ tự đã lưu được dời trước. Không xét số giờ. Code lấy đoạn đầu của thứ tự đó, ngắn nhất, sao cho nếu cả đoạn rời ngày thì tổng còn lại không còn lớn hơn quỹ. Không tách một việc thành vài giờ. Không thêm việc đứng sau đoạn đó.

Chủ bot sửa được danh sách trước khi ghi. Lần ghi đã xác nhận dời đúng các việc trong danh sách chủ bot đã chốt, kể cả khi danh sách đó khác danh sách code đề xuất. Code không tự thêm việc vào danh sách đã chốt. Code không tự dời việc khi chưa có xác nhận.

Mỗi việc trong danh sách có một ngày đích. Code tìm trong bảy ngày lịch ngay sau ngày vượt, ngày gần trước. Ngày đủ quỹ khi cộng giờ việc này, cộng việc chưa làm đã có trên ngày đó, cộng việc đề xuất trước đó đã nhận ngày đó, thì tổng không lớn hơn quỹ. Không có ngày đủ quỹ trong bảy ngày thì việc ở lại ngày gốc và không nằm trong danh sách. Không tìm quá bảy ngày. Thứ Bảy và Chủ nhật vẫn tính, vì ngày nghỉ không thuộc vòng này.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 8 giao việc chọn cho code và để chủ bot sửa. Chọn sai việc thì cảnh báo không dùng được.

**Independent Test**: Dựng ba kế hoạch ưu tiên thấp, vừa và cao, mỗi kế hoạch một việc chưa làm trên cùng một ngày sau hôm nay, đủ giờ để ngày vượt. Đọc thứ tự danh sách code trả ở lần gọi đầu. Chưa ghi.

**Acceptance Scenarios**:

1. **Given** một ngày sau hôm nay vượt quỹ và mọi ứng viên thuộc kế hoạch có ưu tiên cao, vừa hoặc thấp, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch ưu tiên thấp đứng trước việc của kế hoạch ưu tiên vừa, và việc của kế hoạch ưu tiên vừa đứng trước việc của kế hoạch ưu tiên cao.
2. **Given** hai việc ứng viên cùng nằm trên ngày vượt, hai kế hoạch cùng ưu tiên, hạn của kế hoạch này muộn hơn hạn của kế hoạch kia, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch có hạn muộn hơn đứng trước.
3. **Given** hai việc ứng viên, hai kế hoạch cùng ưu tiên và cùng hạn, một kế hoạch được tạo trước kế hoạch kia, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch được tạo trước đứng trước.
4. **Given** đoạn đầu ngắn nhất đã đủ để tổng còn lại không còn lớn hơn quỹ, **When** đọc danh sách code đề xuất, **Then** danh sách không chứa việc đứng sau đoạn đó.
5. **Given** chủ bot đã bỏ bớt một việc khỏi danh sách và đã xác nhận ở lượt sau, **When** lần ghi chạy, **Then** việc đã bỏ không bị dời. Các việc còn trong danh sách đã chốt được đưa vào đường ghi. Không có việc nào bị dời khi chưa có xác nhận.
6. **Given** một ngày sau hôm nay sẽ vượt vì một việc vừa được đặt lên ngày đó, và kế hoạch của việc vừa đặt có ưu tiên thấp nhất, **When** lần gọi đầu trả danh sách, **Then** việc vừa đặt không có trong danh sách. Chỉ việc đã có trên ngày đó từ trước có thể có trong danh sách. Việc vừa đặt vẫn nằm trong tổng giờ.
7. **Given** hai việc đã có trên ngày vượt, một kế hoạch ưu tiên thấp và một kế hoạch ưu tiên trống, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch thấp đứng trước. Ưu tiên đã lưu của kế hoạch trống vẫn trống.
8. **Given** hai việc đã có trên ngày vượt, một kế hoạch ưu tiên trống và một kế hoạch ưu tiên cao, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch trống đứng trước.
9. **Given** hai việc đã có trên ngày vượt, một kế hoạch ưu tiên trống và một kế hoạch ưu tiên vừa, hạn của kế hoạch trống muộn hơn, **When** lần gọi đầu trả danh sách, **Then** việc của kế hoạch trống đứng trước.
10. **Given** một việc ứng viên 3 giờ, ngày ngay sau còn đủ chỗ cho 3 giờ, **When** lần gọi đầu trả danh sách, **Then** ngày đích của việc đó là ngày ngay sau.
11. **Given** một việc ứng viên, cả bảy ngày lịch ngay sau ngày vượt đều không còn đủ quỹ cho việc đó, **When** lần gọi đầu trả danh sách, **Then** việc đó không nằm trong danh sách và vẫn mang ngày gốc.
12. **Given** hai việc đã có trên ngày vượt, cùng một kế hoạch, việc đứng sau trong thứ tự đã lưu có ít giờ hơn việc đứng trước, **When** lần gọi đầu trả danh sách, **Then** việc đứng sau được dời trước. Số giờ không đổi thứ tự đó.

---

### User Story 5 - Việc dời đi qua đường ghi đang có (Priority: P1)

Việc được dời đi qua đường ghi đang có của một lần dời ngày. Vì thế một việc đổi từ một ngày sang một ngày khác có đúng một dòng lịch sử dời việc, như mọi lần dời khác. Dòng ghi việc nào, ngày đi, ngày đến, chỗ cho lý do, và thời điểm. Luật dòng lịch sử đang có không đổi: đặt ngày lần đầu, bỏ ngày, và đặt lại đúng ngày đang có không sinh dòng. Khóa lạc quan của lần ghi đó giữ nguyên.

Lần gọi đầu thấy vượt thì không ghi việc dời nào, nên không sinh dòng lịch sử nào của lần đó.

Khi việc được ghi sang ngày đích đã đề xuất, dòng lịch sử đi từ ngày gốc sang ngày đích đó. Việc không tìm được ngày đủ quỹ trong bảy ngày thì không có dòng, vì ngày của việc không đổi.

Sau khi chủ bot xác nhận, lần ghi chủ bot đang xin chạy trước. Các việc dời chạy sau, đúng thứ tự danh sách. Một lần lỗi thì dừng. Không tự thử lại và không hoàn tác lần đã ghi. Kết quả nói việc nào đã dời và việc nào chưa. Lỗi gồm cả xung đột phiên bản của một kế hoạch khác khi kế hoạch đó đổi giữa lần đọc list_plans và lần replace trong cùng lần gọi. Kế hoạch hoặc việc đổi giữa lượt báo và lượt xác nhận được bắt trước lần ghi đầu: mọi việc trong danh sách đã chốt còn tồn tại và còn chưa làm, nếu không thì lần ghi là lỗi và không ghi gì. Chủ bot muốn dời tiếp thì xin lại. Trạng thái xấu nhất là việc mới đã nằm trên ngày vượt và ngày đó vẫn vượt. Đó là trạng thái cảnh báo mềm đã chấp nhận.

Lần dời trong danh sách vì quá tải không kiểm trùng hạn. Hạn của kế hoạch đổi và trùng hạn một kế hoạch khác thì lần dời đó vẫn ghi. Lần dời do chủ bot xin, không nằm trong danh sách dời vì quá tải, vẫn theo kiểm trùng hạn đang có. Khi chính lần dời do chủ bot xin vừa vượt tải vừa trùng hạn, lần gọi đầu trả cảnh báo tải trước, thông tin trùng hạn sau, và không ghi. Một cờ xác nhận ở lượt sau bao cả hai.

**Why this priority**: [D-024](../../docs/DECISIONS.md) mục 9: lịch sử dời là sự thật của mọi lần đổi từ một ngày sang một ngày khác. Một đường dời riêng sẽ bỏ sót dòng.

**Independent Test**: Xác nhận một lần dời trong cùng một kế hoạch, việc đổi từ một ngày sang một ngày khác, và việc đó không phải việc duy nhất quyết định hạn. Đếm dòng lịch sử. Không cần kế hoạch thứ hai.

**Acceptance Scenarios**:

1. **Given** lần gọi đầu thấy vượt, **When** đọc lịch sử dời, **Then** số dòng không tăng.
2. **Given** chủ bot đã xác nhận và một việc trong cùng kế hoạch đổi từ ngày A sang ngày B khác A, **When** lần ghi thành công, **Then** có đúng một dòng mới cho việc đó, từ A sang B. Các dòng cũ còn nguyên.
3. **Given** lần ghi dời bị từ chối vì bản kế hoạch đã cũ, **When** đọc lại kế hoạch đó, **Then** ngày việc trên kế hoạch đó giữ nguyên và số dòng lịch sử của lần ghi đó không tăng.
4. **Given** lần chủ bot đang xin đã ghi xong và việc dời đứng trước trong danh sách đã dời xong, **When** việc dời đứng sau bị lỗi vì xung đột phiên bản, **Then** hai lần đã ghi còn nguyên. Việc lỗi và mọi việc đứng sau nó không bị dời. Không có lần thử lại. Kết quả nói việc nào đã dời và việc nào chưa.
5. **Given** một việc trong danh sách dời vì quá tải, và lần dời đó làm hạn của kế hoạch trùng hạn một kế hoạch khác, **When** lần dời được ghi sau khi chủ bot xác nhận, **Then** việc được ghi sang ngày đích. Có một dòng lịch sử. Lần dời không bị chặn vì trùng hạn.

---

### User Story 6 - Dữ liệu đang có còn nguyên (Priority: P1)

Mọi kế hoạch và việc con đang có vẫn còn. Goal, tiêu đề, trạng thái, ghi chú, thứ tự, ngày, sức, ưu tiên, thời điểm tạo và thời điểm đổi trạng thái không bị viết lại chỉ vì có quét tải. Vòng này không thêm khái niệm người dùng vào kho. Mọi lời gọi ghi vẫn trả về một giá trị. Đường truy cập kho vẫn là đường duy nhất đang có. Khóa lạc quan giữ nguyên.

Vòng này không bắt buộc đổi schema. Nếu đổi schema thì thay đổi tương thích ngược theo [D-026](../../docs/DECISIONS.md) mục 4: giữa lúc đưa schema mới lên và lúc bản chạy cũ còn sống, bản cũ không làm mất giá trị đã lưu, và bản mới không lỗi khi gặp dữ liệu cũ.

**Why this priority**: Kho đang chạy thật. Quét tải đọc mọi kế hoạch để cộng giờ. Một lần đọc hoặc một lần ghi hỏng không được làm mất kế hoạch đang dùng.

**Independent Test**: Ghi một kế hoạch với việc đã xong, việc bỏ qua, việc chưa làm, ngày, sức và ưu tiên. Chạy một lần quét tải không ghi đè các trường đó. Đọc lại từng trường.

**Acceptance Scenarios**:

1. **Given** một kế hoạch đã có goal, việc con, trạng thái, ghi chú, ngày, sức và ưu tiên, **When** một lần quét tải chạy, **Then** các chữ và các ngày đó còn nguyên.
2. **Given** một lần ghi bị từ chối vì bản kế hoạch đã cũ, **When** đọc lại, **Then** bản cũ vẫn là bản được lưu. Quét tải không tắt khóa đó.
3. **Given** dữ liệu mới của vòng này, **When** đọc kho, **Then** không có danh tính người dùng trên dữ liệu đó.

---

### User Story 7 - Bộ câu eval phiên bản 3, chạy lại bộ 1 và 2 (Priority: P2)

Có một bộ câu đánh giá phiên bản 3 cho các hành vi mới của vòng này. Có một lần chạy lại bộ phiên bản 1 và một lần chạy lại bộ phiên bản 2, để đo hồi quy, theo cách [spec 015](../015-plan-dates-priority/spec.md) đã làm: mỗi bộ một lần chạy, mỗi lần chạy một file kết quả, cách chấm từng ca của bộ 1 và bộ 2 giữ nguyên.

Bộ phiên bản 3 gồm các ca sau.

1. Đặt việc lên một ngày sau hôm nay, tổng sau lần ghi không lớn hơn quỹ. Lần ghi được lưu. Không có cảnh báo vượt.
2. Cùng loại ngày, tổng sau lần ghi lớn hơn quỹ. Lần gọi đầu không ghi. Kho không đổi. Kết quả có ngày, tổng giờ, quỹ, và có tính tạm hay không. Ca này không lấy bản thân cờ xác nhận làm chuẩn đạt.
3. Việc đã xong và việc bỏ qua trên ngày đó không làm tăng tổng trong kết quả.
4. S, M và L được cộng 1, 3 và 6. Việc không có sức được cộng 3. Mức này được chấp nhận: ba việc không sức là 9 giờ và vượt quỹ 8 giờ. Khi tổng có việc không sức, lời nói có "(tính tạm: {số} việc chưa có sức, mỗi việc tính 3 giờ)".
5. Mô hình được nói bằng chữ của mình, miễn nêu đủ ngày, tổng giờ và quỹ đúng số code đã trả, ghi chú tính tạm khi có, và danh sách dời đúng thứ tự và đúng ngày khi có. Danh sách rỗng thì không bịa việc. Mô hình nói rõ chưa ghi hoặc hỏi chủ bot, và không gọi lại với confirm trong cùng lượt. Ngày/tháng vẫn hai chữ số.
6. Danh sách đề xuất xếp thấp trước, rồi trống cùng vừa, rồi cao. Trống và vừa là cùng một mức: hạn muộn hơn trước, cùng hạn thì kế hoạch được tạo trước đứng trước. Ưu tiên trống đã lưu vẫn trống. Hai việc cùng một kế hoạch thì việc đứng sau trong thứ tự đã lưu đứng trước, không xét số giờ. Ca ngày đích thấy ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau, và thấy việc ở lại ngày gốc khi bảy ngày đều không đủ.
7. Sau một lần xác nhận, lần chủ bot đang xin được ghi trước, rồi các lần dời theo thứ tự danh sách. Lỗi thì dừng, không hoàn tác, không tự thử lại, và báo việc nào đã dời cùng việc nào chưa. Lần dời vì quá tải làm hạn trùng một kế hoạch khác thì vẫn ghi, không bị chặn vì trùng hạn.
8. Hai lượt. Lượt một báo vượt. Lượt hai chủ bot từ chối, nói thôi không thêm nữa. Chấm theo kho: kho không đổi sau lượt hai. Nếu mô hình đặt cờ sau lời từ chối thì kho đổi và ca trượt. Ca chạy bằng seed hai lượt, theo cách spec 015 đã làm.

**Why this priority**: Không có bộ câu thì luật "không cộng giờ bằng mô hình" và luật "lần gọi đầu không ghi" không có chỗ đo trên mô hình thật. Chạy lại bộ 1 và bộ 2 để thấy vòng này không làm hỏng các ca đã chốt.

**Independent Test**: Đọc bộ câu phiên bản 3 và thấy đủ tám ca ở trên. Đọc cách chấm bộ 1 và bộ 2 và thấy không đổi. Chưa cần chạy mô hình thật để coi spec này là đủ mô tả.

**Acceptance Scenarios**:

1. **Given** bộ câu phiên bản 3, **When** đọc danh sách ca, **Then** có đủ tám ca ở trên. Bộ câu phiên bản 1 và bộ câu phiên bản 2 vẫn còn.
2. **Given** ca vượt quỹ, **When** chấm lần gọi đầu, **Then** kho không đổi và kết quả có ngày, tổng giờ, quỹ, và có tính tạm hay không. Chuẩn đạt không phải là bản thân cờ xác nhận.
3. **Given** ca thứ tự dời, **When** chấm danh sách đề xuất, **Then** thấp đứng trước trống và vừa, trống và vừa đứng trước cao. Trống và vừa cùng mức thì hạn muộn hơn đứng trước, cùng hạn thì kế hoạch được tạo trước đứng trước. Hai việc cùng một kế hoạch thì việc đứng sau trong thứ tự đã lưu đứng trước. Ưu tiên trống đã lưu vẫn trống.
4. **Given** một lần chạy bộ phiên bản 1, một lần chạy bộ phiên bản 2, và một lần chạy bộ phiên bản 3, **When** đọc kết quả, **Then** mỗi lần chạy có một file kết quả. Cách chấm từng ca bộ 1 và bộ 2 trùng cách chấm của lần chạy trước vòng này.
5. **Given** ca hai lượt, lượt một báo vượt và lượt hai chủ bot nói thôi không thêm nữa, **When** chấm theo kho, **Then** kho không đổi sau lượt hai. **When** mô hình đặt cờ sau lời từ chối, **Then** kho đổi và ca trượt.

---

### Edge Cases

- Tổng bằng quỹ thì chưa vượt. Chỉ tổng lớn hơn quỹ mới là vượt.
- Việc đã xong và việc bỏ qua không cộng giờ, dù chúng mang đúng ngày đang xét.
- Việc không có ngày không thuộc tải của ngày nào.
- Hôm nay tính vào tải. Ngày trước hôm nay không tính: việc chưa làm của ngày đó cộng 0 vào tải ngày đó và cộng 0 vào tải hôm nay.
- Đặt sức, đặt ưu tiên, sửa ghi chú, hoặc đổi trạng thái mà không đặt việc lên một ngày thì không chạy kiểm tải.
- Dời một việc sang đúng ngày nó đang có không làm đổi tập việc của ngày đó. Lần ghi không bị cảnh báo vượt chỉ vì ngày đó đã vượt từ trước.
- Bỏ ngày của một việc không đặt việc đó lên một ngày đích. Ngày vừa mất việc không bị cảnh báo vượt vì tổng của ngày đó giảm.
- Một việc không tách giờ. Đoạn danh sách dời là cả việc.
- Việc vừa được đặt lên ngày vượt không phải ứng viên dời, kể cả khi kế hoạch của nó ưu tiên thấp nhất. Việc đó ở lại ngày đó và vẫn cộng vào tổng. Không có việc nào đã có từ trước thì danh sách dời trống, và cảnh báo vượt vẫn trả về.
- Ngày đích là ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau ngày vượt. Đủ quỹ nghĩa là tổng sau khi nhận việc không lớn hơn quỹ. Giờ của việc đã được đề xuất nhận ngày đó tính vào tổng. Không có ngày đủ quỹ thì việc ở lại ngày gốc và không nằm trong danh sách. Không tìm ngày thứ tám.
- Sau khi chủ bot xác nhận, lần ghi đang xin chạy trước các lần dời. Dời theo thứ tự danh sách. Lỗi thì dừng, không hoàn tác, không tự thử lại. Kết quả nói việc nào đã dời và việc nào chưa. Xung đột phiên bản của một kế hoạch khác là một lỗi như vậy khi kế hoạch đó đổi giữa lần đọc list_plans và lần replace trong cùng lần gọi. Kế hoạch hoặc việc đổi giữa lượt báo và lượt xác nhận được bắt trước lần ghi đầu: mọi việc trong danh sách đã chốt còn tồn tại và còn chưa làm, nếu không thì không ghi gì.
- Lần dời trong danh sách vì quá tải không kiểm trùng hạn. Hạn mới trùng hạn một kế hoạch khác thì lần dời đó vẫn ghi.
- Khi xếp việc dời, ưu tiên trống bằng vừa. Giá trị đã lưu vẫn trống. Thấp được dời trước trống và vừa. Trống và vừa được dời trước cao. Trống và vừa là cùng một mức: hạn muộn hơn trước, cùng hạn thì kế hoạch được tạo trước trước. Hai việc cùng một kế hoạch, cùng nằm trên ngày vượt, thì việc đứng sau trong thứ tự đã lưu được dời trước. Số giờ không đổi thứ tự đó.
- Lần gọi đầu thấy vượt thì không ghi việc mới, không ghi việc dời, và không thêm dòng lịch sử.
- Chủ bot xác nhận rồi thì lần ghi được lưu kể cả khi ngày vừa báo vẫn vượt. Bot không tự dời thêm cho đủ quỹ.
- Việc hằng ngày, sự kiện đột xuất và ngày nghỉ không có trong compass ở vòng này nên không cộng vào tổng. Quỹ không vì chúng mà về 0 trong vòng này.
- Cảnh báo vượt không ghi danh tính người dùng vào kho.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Với hôm nay và với một ngày sau hôm nay, tải MUST là tổng giờ của mọi việc chưa làm mang đúng ngày đó, ở mọi kế hoạch. Hôm nay MUST là ngày lịch Helsinki của mốc đầu lượt. S MUST cộng 1 giờ, M MUST cộng 3 giờ, L MUST cộng 6 giờ, lấy từ chỗ cấu hình EFFORT_HOURS. Việc chưa làm không có sức MUST cộng 3 giờ. Việc đã xong và việc bỏ qua MUST cộng 0. Việc không mang ngày đó MUST cộng 0. Với một ngày trước hôm nay, việc chưa làm mang ngày đó MUST cộng 0 vào tải của ngày đó và MUST cộng 0 vào tải của hôm nay. Mức này được chấp nhận. Ba việc chưa làm không sức MUST là 9 giờ và MUST vượt quỹ 8 giờ.
- **FR-002**: Một hàm trong phần lõi MUST nhận một ngày lịch và MUST trả quỹ giờ của ngày đó. Hiện hàm MUST trả 8 với mọi ngày. Nơi gọi MUST gọi hàm này khi cần quỹ. Hàm MUST NOT hỏi routine. Compass MUST NOT gọi routine. Sau này routine cấp số khác MUST NOT đòi đổi nơi gọi.
- **FR-003**: Một ngày MUST vượt khi tổng giờ lớn hơn quỹ của ngày đó. Tổng bằng quỹ MUST NOT là vượt.
- **FR-004**: Kiểm tải MUST chạy khi một lần ghi đặt một việc chưa làm lên hôm nay hoặc lên một ngày sau hôm nay. Ba lần ghi đó là tạo kế hoạch có việc mang ngày, thêm việc có ngày, và dời việc sang một ngày. Lần ghi không đặt việc nào lên một ngày MUST NOT chạy kiểm này. Lần ghi chỉ đặt việc lên một ngày trước hôm nay MUST NOT cảnh báo vượt vì tải. Tổng đem so của hôm nay và của ngày sau hôm nay MUST là tổng sau lần ghi nếu lần ghi được lưu và chưa dời bớt việc. Việc vừa đặt lên ngày đó MUST nằm trong tổng. Việc lần ghi chuyển khỏi ngày đó MUST NOT còn trong tổng của ngày đó. Việc mang một ngày trước hôm nay MUST NOT nằm trong tổng của hôm nay.
- **FR-005**: Khi ít nhất một ngày vượt, lần gọi đầu MUST NOT ghi. Kho MUST không đổi. Kết quả MUST trả cảnh báo của ngày vượt, gồm ngày, tổng giờ đã so, quỹ, và có tính tạm hay không. Khi tổng có ít nhất một việc không sức, cảnh báo MUST ghi rõ "tính tạm". Khi mọi việc trong tổng đều có sức, cảnh báo MUST NOT nói tính tạm. Kết quả MUST kèm danh sách việc sẽ bị dời nếu chủ bot vẫn muốn ghi. Cảnh báo MUST là cảnh báo mềm: MUST NOT chặn lần ghi đã được chủ bot xác nhận ở lượt sau, và MUST NOT tự dời việc. Một lần ghi làm nhiều ngày vượt MUST trả cảnh báo của từng ngày trong cùng kết quả lần gọi đầu. Cảnh báo tải MUST đứng trước. Nếu lần đang xin là tool dời ngày và cũng trùng hạn, thông tin trùng hạn MUST đứng sau các cảnh báo tải, trong cùng kết quả. Lần gọi đầu đó MUST NOT ghi. Một cờ xác nhận ở lượt sau MUST bao cả tải và trùng hạn. Tạo kế hoạch và thêm việc MUST NOT kiểm trùng hạn trong vòng này. Đây là hạn chế đã biết. Bật khi thấy thiếu.
- **FR-006**: Khi lần gọi đầu chưa ghi vì vượt, câu của tool là chữ khóa ở [contracts/load-warning.md](./contracts/load-warning.md). Mô hình được nói bằng chữ của mình, miễn nêu đủ ngày, tổng giờ, quỹ, ghi chú tính tạm khi có, danh sách dời đúng thứ tự và đúng ngày khi có, nói rõ chưa ghi hoặc hỏi chủ bot. Mô hình MUST NOT tự cộng giờ và MUST NOT bịa việc. Ngày/tháng MUST vẫn hai chữ số, cùng dạng với digest, như 06/11 và 12/11. Lần gọi lại với confirm MUST chỉ ở lượt sau. FR-006 là luật cho mô hình, đo bằng tỉ lệ eval bộ v3, không phải một assert 100% trong pytest.
- **FR-007**: Chỉ MUST ghi khi chủ bot xác nhận ở lượt sau. Vòng này MUST dùng lại cơ chế cờ xác nhận và cờ đã báo của kiểm trùng hạn ở [D-026](../../docs/DECISIONS.md) mục 6. Lần gọi đầu MUST NOT có cờ xác nhận. Lần gọi có cờ xác nhận trong cùng lượt sau khi vừa báo vượt MUST NOT ghi. Cờ MUST NOT được coi là chứng minh sự đồng ý của chủ bot. Lần ghi đã xác nhận MUST lưu việc đặt lên ngày, kể cả khi ngày vừa báo vẫn vượt. Lần ghi đó MUST NOT mở một cảnh báo vượt mới cho chính ngày vừa báo. Cơ chế cờ dùng lại nguyên là đủ. MUST NOT đòi bảo đảm mạnh hơn. Eval MUST chấm theo kho. Ca hai lượt MUST có lượt một báo vượt và lượt hai chủ bot từ chối. Kho MUST không đổi sau lượt hai. Nếu mô hình đặt cờ sau lời từ chối thì kho đổi và ca MUST trượt. Ca đó MUST chạy bằng seed hai lượt, theo cách spec 015 đã làm.
- **FR-008**: Code MUST lập danh sách việc dời. Khi xếp việc dời, ưu tiên trống MUST bằng vừa. Giá trị ưu tiên đã lưu MUST vẫn trống và MUST NOT bị ghi thành vừa. Thứ tự MUST là thấp trước, rồi trống và vừa, rồi cao. Trống và vừa MUST là cùng một mức. Cùng mức MUST xếp kế hoạch có hạn muộn hơn trước. Hạn MUST là ngày muộn nhất trong các việc chưa làm có ngày. Việc đã xong và việc bỏ qua MUST NOT tính vào hạn. Cùng mức và cùng hạn MUST xếp kế hoạch được tạo trước đứng trước. Hai việc cùng một kế hoạch, cùng nằm trên ngày vượt, MUST xếp việc đứng sau trong thứ tự đã lưu đứng trước. Số giờ MUST NOT đổi thứ tự đó. Ứng viên MUST chỉ là việc chưa làm đã có trên ngày vượt từ trước lần ghi. Việc vừa được đặt lên ngày đó MUST NOT là ứng viên và MUST ở lại ngày đó, kể cả khi kế hoạch của nó ưu tiên thấp nhất. Việc vừa đặt MUST vẫn nằm trong tổng giờ. Danh sách đề xuất MUST là đoạn đầu ngắn nhất của thứ tự đã chọn sao cho tổng còn lại không còn lớn hơn quỹ. MUST NOT tách giờ của một việc. Mỗi việc trong đoạn đầu MUST được gán ngày đích theo thứ tự đó. Ngày đích MUST là ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau ngày vượt. Đủ quỹ MUST nghĩa là tổng giờ chưa làm đã có trên ngày đó, cộng việc đề xuất trước đã nhận ngày đó, cộng việc đang gán, không lớn hơn quỹ của ngày đó. Không có ngày đủ quỹ trong bảy ngày MUST để việc ở lại ngày gốc và MUST NOT đưa việc vào danh sách. MUST NOT tìm ngày thứ tám.
- **FR-009**: Chủ bot MUST sửa được danh sách trước khi ghi. Code MUST NOT tự thêm việc vào danh sách đã chốt. Code MUST NOT dời việc khi chưa có xác nhận của chủ bot. Sau khi chủ bot xác nhận, lần ghi chủ bot đang xin MUST chạy trước. Các việc dời trong danh sách đã chốt MUST chạy sau, đúng thứ tự danh sách. Một lần lỗi MUST dừng các lần còn lại. Lần đã ghi MUST được giữ và MUST NOT bị hoàn tác. MUST NOT tự thử lại. Kết quả MUST nói việc nào đã dời và việc nào chưa. Lỗi MUST gồm xung đột phiên bản của một kế hoạch khác khi kế hoạch đó đổi giữa lần đọc list_plans và lần replace trong cùng lần gọi. Kế hoạch hoặc việc đổi giữa lượt báo và lượt xác nhận MUST được bắt trước lần ghi đầu: mọi việc trong danh sách đã chốt MUST còn tồn tại và còn chưa làm, nếu không thì lần ghi là lỗi và MUST NOT ghi gì. Chủ bot muốn dời tiếp MUST xin lại. Trạng thái việc mới đã nằm trên ngày vượt và ngày đó vẫn vượt MUST được chấp nhận.
- **FR-010**: Việc dời MUST đi qua đường ghi dời ngày đang có. Một việc đổi từ một ngày sang một ngày khác MUST có đúng một dòng lịch sử, như mọi lần dời khác. Đặt ngày lần đầu, bỏ ngày và đặt lại đúng ngày MUST NOT sinh dòng. Lần gọi đầu thấy vượt MUST NOT sinh dòng. Khóa lạc quan của lần ghi đó MUST giữ nguyên. Ngày đến của dòng lịch sử MUST là ngày đích đã đề xuất khi việc đổi từ ngày gốc sang ngày đó. Việc ở lại ngày gốc MUST NOT sinh dòng. Lần dời trong danh sách vì quá tải MUST NOT kiểm trùng hạn. Hạn của kế hoạch đổi và trùng hạn một kế hoạch khác MUST NOT chặn lần dời đó. Lần dời do chủ bot xin và không nằm trong danh sách dời vì quá tải MUST vẫn theo kiểm trùng hạn đang có. Khi chính lần dời do chủ bot xin vừa vượt tải vừa trùng hạn, lần gọi đầu MUST trả cảnh báo tải trước và thông tin trùng hạn sau, và MUST NOT ghi. Một cờ xác nhận ở lượt sau MUST bao cả hai.
- **FR-011**: Mọi kế hoạch và việc con đang có MUST còn. Quét tải MUST NOT viết lại goal, tiêu đề, trạng thái, ghi chú, thứ tự, ngày, sức, ưu tiên, thời điểm tạo hay thời điểm đổi trạng thái khi các trường đó không phải phần chủ bot đang ghi. Dữ liệu mới MUST NOT mang danh tính người dùng, theo [D-022](../../docs/DECISIONS.md). Mọi lời gọi ghi MUST trả về một giá trị, theo [D-023](../../docs/DECISIONS.md). Đường truy cập kho MUST vẫn là đường duy nhất của constitution III. Khóa lạc quan của [D-021](../../docs/DECISIONS.md) MUST giữ nguyên.
- **FR-012**: Vòng này MUST NOT bắt buộc một schema mới. Nếu schema đổi, thay đổi MUST tương thích ngược theo [D-026](../../docs/DECISIONS.md) mục 4.
- **FR-013**: Bộ câu đánh giá phiên bản 3 MUST gồm đủ tám ca của User Story 7. Bộ câu phiên bản 1 và bộ câu phiên bản 2 MUST còn. Vòng này MUST chạy mỗi bộ đúng một lần. Mỗi lần chạy MUST ghi một file kết quả. Cách chấm từng ca bộ 1 và bộ 2 MUST giữ nguyên. Ca vượt quỹ MUST thấy kho không đổi sau lần gọi đầu và MUST NOT lấy bản thân cờ xác nhận làm chuẩn đạt. Ca thứ tám MUST là ca hai lượt: lượt một báo vượt, lượt hai chủ bot từ chối. Kho MUST không đổi sau lượt hai. Nếu mô hình đặt cờ sau lời từ chối thì kho đổi và ca MUST trượt. Ca đó MUST chạy bằng seed hai lượt, theo cách spec 015 đã làm.
- **FR-014**: Vòng này MUST NOT làm việc hằng ngày, sự kiện đột xuất, ngày nghỉ, lệnh hay chỗ lưu quỹ riêng từng ngày, ưu tiên riêng của việc con, lịch lễ tự động, tự dời việc khi chưa có xác nhận, xếp lại lịch bằng mô hình, form nhập kế hoạch, Mini App, lệnh `/today`, nhắc theo giờ, hay voice. Bước specify MUST NOT thêm hàng F20 vào bảng tính năng của [docs/PRODUCT.md](../../docs/PRODUCT.md). Hàng đó được thêm ở lô 3 của implement, sau khi D-029 đã có chữ.

### Key Entities

- **Tải một ngày**: Tổng giờ tính ra khi cần, không phải một trường lưu trên kế hoạch. Gồm mọi việc chưa làm mang đúng ngày đó ở mọi kế hoạch. Không gồm việc đã xong và việc bỏ qua.
- **Quỹ giờ một ngày**: Số giờ hàm trong phần lõi trả về cho một ngày. Hiện là 8 với mọi ngày. Không có chỗ lưu quỹ riêng từng ngày trong vòng này.
- **Cảnh báo vượt**: Giá trị lần gọi ghi trả về khi tổng lớn hơn quỹ. Có ngày, tổng giờ, quỹ, có tính tạm hay không, và danh sách việc code đề xuất dời. Không lưu thành một dòng kho, và không mang danh tính người dùng.
- **Danh sách việc dời**: Các việc chưa làm code đề xuất đưa ra khỏi ngày vượt, theo FR-008, trước khi chủ bot sửa. Lần ghi đã xác nhận dùng danh sách chủ bot đã chốt.
- **Lần dời việc**: Dòng lịch sử đang có. Vòng này không tạo loại dòng mới. Dòng chỉ sinh khi một việc đổi từ một ngày sang một ngày khác qua đường ghi đang có.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Với hôm nay và với một ngày sau hôm nay, 100% lần tính tải bằng tổng giờ các việc chưa làm mang đúng ngày đó ở mọi kế hoạch. 100% việc chưa làm của một ngày trước hôm nay cộng 0 vào tải ngày đó và cộng 0 vào tải hôm nay. 100% việc đã xong và việc bỏ qua cộng 0. 100% việc S, M, L cộng 1, 3, 6 giờ. 100% việc chưa làm không có sức cộng 3 giờ. 0 lần mô hình là nơi ra tổng đó.
- **SC-002**: 100% lần gọi hàm quỹ, với mọi ngày lịch, trả về 8. 100% lần tổng bằng 8 được coi là chưa vượt. 100% lần tổng lớn hơn quỹ được coi là vượt. 0 lần hàm quỹ hỏi routine.
- **SC-003**: 100% lần gọi đầu đặt việc lên hôm nay hoặc lên một ngày sau hôm nay mà tổng sau lần ghi lớn hơn quỹ để kho không đổi. 100% lần gọi đầu đó trả ngày, tổng giờ, quỹ, và có tính tạm hay không. 100% câu tool trả khi lần gọi đầu chưa ghi vì vượt đúng [contracts/load-warning.md](./contracts/load-warning.md). 100% lần ghi chỉ đặt việc lên một ngày trước hôm nay được lưu và không có cảnh báo vượt vì tải. 0 việc bị dời trước khi chủ bot xác nhận ở lượt sau. Câu mô hình nói lại là tỉ lệ của bộ v3: đạt khi nêu đủ ngày, tổng giờ, quỹ, ghi chú tính tạm khi có, danh sách dời đúng thứ tự và đúng ngày khi có, nói rõ chưa ghi hoặc hỏi chủ bot, không tự cộng giờ và không bịa việc. Ngày/tháng vẫn hai chữ số. Tỉ lệ đó không phải điều kiện của pytest.
- **SC-004**: 100% lần chủ bot xác nhận ở lượt sau thì việc đặt lên ngày được lưu. 100% lần cờ xác nhận trong cùng lượt vừa báo vượt để kho không đổi. 0 lần chấm lấy bản thân cờ làm bằng chứng chủ bot đã đồng ý. 100% ca hai lượt, lượt một báo vượt và lượt hai chủ bot từ chối, để kho không đổi sau lượt hai. 100% lần mô hình đặt cờ sau lời từ chối làm kho đổi và làm ca trượt.
- **SC-005**: 100% danh sách đề xuất xếp thấp trước trống và vừa, rồi trống và vừa trước cao. 100% lần so trống với vừa coi hai mức là một. Cùng mức thì 100% lần hạn kế hoạch muộn hơn đứng trước. Cùng mức và cùng hạn thì 100% lần kế hoạch được tạo trước đứng trước. 100% cặp việc cùng một kế hoạch và cùng ngày vượt xếp việc đứng sau trong thứ tự đã lưu trước. 0 lần số giờ đổi thứ tự của cặp đó. 100% kế hoạch ưu tiên trống vẫn đọc lại là trống sau lần xếp. 100% danh sách đề xuất dừng ở đoạn đầu ngắn nhất còn đủ để tổng không còn lớn hơn quỹ. 100% lần chủ bot bỏ một việc khỏi danh sách thì việc đó không bị dời. 100% việc vừa được đặt lên ngày vượt vắng mặt trong danh sách đề xuất và vẫn cộng vào tổng giờ. 100% việc được đề xuất dời có ngày đích là ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau ngày vượt. 100% việc không có ngày đủ quỹ trong bảy ngày đó ở lại ngày gốc và vắng mặt trong danh sách. 0 việc được đề xuất dời sang ngày thứ tám hoặc xa hơn.
- **SC-006**: 100% việc đổi từ một ngày sang một ngày khác trong một lần ghi đã xác nhận, cùng một kế hoạch, có đúng một dòng lịch sử mới. 100% lần gọi đầu thấy vượt thêm 0 dòng. 100% lần ghi bị từ chối vì bản cũ giữ nguyên ngày của chính kế hoạch đó và thêm 0 dòng của lần ghi đó. 100% lần lỗi sau một lần đã ghi thì phần đã ghi còn nguyên, phần chưa ghi không bị dời, và không có lần thử lại. 100% kết quả của lần lỗi nói được việc nào đã dời và việc nào chưa. 100% lần dời vì quá tải làm hạn trùng một kế hoạch khác vẫn được ghi và có một dòng lịch sử. 0 lần dời vì quá tải bị chặn chỉ vì trùng hạn. 100% xung đột phiên bản giữa lần đọc list_plans và lần replace trong cùng lần gọi dừng các lần còn lại và giữ phần đã ghi. 100% danh sách đã chốt có việc không còn hoặc đã không còn chưa làm thì lần ghi đầu không chạy và không ghi gì.
- **SC-007**: 100% kế hoạch và việc con đang có trước một lần quét tải vẫn đọc lại được với cùng goal, tiêu đề, trạng thái, ghi chú, thứ tự, ngày, sức, ưu tiên và hai mốc thời gian khi lần quét không ghi các trường đó. 0 dữ liệu mới của vòng này mang danh tính người dùng.
- **SC-008**: Bộ câu phiên bản 3 chứa đủ 8 ca của User Story 7, gồm ca hai lượt khi chủ bot từ chối. Một lần chạy bộ 1, một lần chạy bộ 2 và một lần chạy bộ 3, mỗi lần có một file kết quả. Cách chấm từng ca bộ 1 và bộ 2 trùng lần chạy trước vòng này.

## Assumptions

- Tổng đem so gồm cả việc vừa được đặt lên ngày. Nếu chỉ cộng việc đã có từ trước, tạo kế hoạch mới trên một ngày trống sẽ không bao giờ vượt, trái với việc kiểm lúc tạo.
- "Vượt" là tổng lớn hơn quỹ. Tổng bằng 8 với quỹ 8 là chưa vượt.
- Khóa sau mức ưu tiên là hạn của kế hoạch, không phải ngày của từng việc ứng viên. Hạn bằng nhau thì kế hoạch được tạo trước đứng trước. Khi xếp việc dời, trống bằng vừa, và giá trị đã lưu vẫn trống. Việc vừa đặt lên ngày không phải ứng viên dời. Việc đó vẫn cộng vào tổng giờ. Ngày đích là ngày gần nhất còn đủ quỹ trong bảy ngày lịch ngay sau ngày vượt. Hết bảy ngày thì việc ở lại ngày gốc. Sau khi chủ bot xác nhận, lần đang xin ghi trước các lần dời. Lỗi thì dừng, giữ phần đã ghi, không tự thử lại, và báo việc nào đã dời cùng việc nào chưa.
- Danh sách đề xuất là đoạn đầu ngắn nhất của thứ tự đã chọn. Chủ bot vẫn sửa được đoạn đó trước khi ghi.
- Lần ghi đã xác nhận không hỏi vượt lại cho chính ngày vừa báo. Nếu hỏi lại, chủ bot không bao giờ ghi xong một ngày vẫn còn vượt, trái với cảnh báo mềm không chặn.
- Kiểm trùng hạn không bật ở tạo kế hoạch và thêm việc trong vòng này, dù [D-026](../../docs/DECISIONS.md) mục 6 có để phần đó cho vòng quét tải. Hạn chế đã biết. Bật khi thấy thiếu. Trùng hạn trong lần gọi đầu chỉ áp cho tool dời ngày. Cảnh báo tải đứng trước thông tin trùng. Một cờ xác nhận ở lượt sau bao cả hai.
- Việc hằng ngày, sự kiện đột xuất và ngày nghỉ không cộng vào tải của vòng này, vì [D-027](../../docs/DECISIONS.md) đã đưa chúng ra ngoài compass. Chỗ [D-024](../../docs/DECISIONS.md) mục 7 nói cộng cả việc hằng ngày và sự kiện được hiểu theo cập nhật 2026-11-09 của quyết định đó.
- Người dùng kho là một chủ bot. Dòng cảnh báo và dòng lịch sử không ghi một người.
- Hàng F20 trong bảng tính năng của [docs/PRODUCT.md](../../docs/PRODUCT.md) không thuộc bước specify này.
- Số phiên bản lời hướng dẫn và số phiên bản bộ định nghĩa tool, nếu luật "mô hình không cộng giờ" phải vào lời hướng dẫn, không được chọn ở bước này.

## Câu hỏi dành cho /speckit-clarify

Câu 9, câu 10, câu 3, câu 1, câu 4, câu 11, câu 2, câu 7, câu 5, câu 6 và câu 8 đã chốt ở Clarifications và đã gỡ khỏi mục này. Không còn câu mở.
