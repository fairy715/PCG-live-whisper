# Phiên dịch cuộc họp PCG: các tình huống sử dụng

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Phụ đề trực tiếp phân biệt ngôn ngữ **theo nguồn âm thanh**:

- **Âm thanh máy tính phát ra** (người bên kia trên Teams/Zoom, video) = ngôn ngữ của bên kia
- **Micro** (khi đánh dấu "Tôi cũng sẽ nói") = tiếng Trung của bạn

Vì vậy chỉ **máy tính chủ trì cuộc họp hoặc lớp học** cần cài ứng dụng. Bên kia không cần cài gì.

## 1. Họp hoặc học trực tuyến: tiếng Trung ⇄ ngôn ngữ khác

> Ví dụ: giảng viên nói tiếng Trung, học viên Việt Nam trả lời bằng tiếng Việt, mọi người trên Teams.

**Ai cần cài**: chỉ máy của giảng viên. Học viên vào Teams/Zoom như bình thường.

1. Trên máy giảng viên: "Phiên dịch cuộc họp PCG" → "Phụ đề trực tiếp".
2. Chọn "**Tiếng Việt**" (ngôn ngữ bên kia), đánh dấu "**Tôi cũng sẽ nói (hai chiều)**", bấm Bắt đầu.
3. **Đeo tai nghe**, để giọng học viên từ loa không lọt vào micro và bị coi là tiếng Trung.

Phụ đề: tiếng Trung của giảng viên → tiếng Trung + bản dịch tiếng Việt; tiếng Việt của học viên → tiếng Việt + bản dịch tiếng Trung.

**Để học viên xem phụ đề** (chọn một):
- **Chia sẻ màn hình** (ở đâu cũng được): đánh dấu "Phụ đề luôn ở trên cùng" và chia sẻ màn hình trên Teams.
- **Điện thoại** (học viên trong mạng công ty): bấm "Chia sẻ", học viên quét mã QR, nhập mật khẩu nhân viên và chọn ngôn ngữ. IT cần bật "Cho phép máy tính và điện thoại khác xem phụ đề".

**Học viên muốn xem phụ đề trên máy của mình** (từ v2026.11.5.r9): cài ứng dụng trên máy học viên, mở "Phụ đề trực tiếp", chọn "**Tiếng Trung → Tiếng Việt**" (cũng có Indonesia, Hindi, Anh), bấm Bắt đầu. Học viên chỉ nghe nên không cần hai chiều và không cần tai nghe. Ứng dụng lấy giọng giảng viên từ Teams và hiển thị bằng tiếng Việt; máy giảng viên vẫn bật hai chiều. Không cần chia sẻ màn hình; mỗi người đọc ngôn ngữ của mình.

## 2. Chỉ cần hiểu bên kia nói gì

Chọn ngôn ngữ của bên kia, **không** đánh dấu "Tôi cũng sẽ nói", bấm Bắt đầu. Không cần tai nghe.

## 3. Cùng một phòng họp hoặc lớp học, một micro (chế độ lớp học)

> Ví dụ: giảng viên và học viên Việt Nam nói chuyện trong cùng lớp học. (từ v2026.11.5.r9)

1. Kết nối một micro thu được âm thanh cả phòng (micro hội nghị hoặc micro để bàn).
2. "Phụ đề trực tiếp" → chọn "**Tiếng Việt**" → đánh dấu "**Chế độ lớp học**" → Bắt đầu. (Indonesia, Hindi và tiếng Anh cũng được.)
3. Chiếu phụ đề lên máy chiếu, hoặc học viên quét mã QR từ "Chia sẻ".

Mỗi câu được tự nhận biết là tiếng Trung hay tiếng Việt: tiếng Trung → tiếng Trung + bản dịch tiếng Việt; tiếng Việt → tiếng Việt + bản dịch tiếng Trung.

**Giới hạn**
- Tốt nhất **từng người nói một**; nói chồng lên nhau hoặc câu trộn hai ngôn ngữ sẽ nhận dạng kém.
- **Câu quá ngắn** ("ok", "vâng") có thể bị nhận sai ngôn ngữ.
- Phụ đề **chậm hơn một chút** vì phải nhận biết ngôn ngữ của từng câu trước.
- Chế độ lớp học dùng nhận dạng trên máy này (không dùng máy chủ GPU) với mô hình cục bộ do IT cài đặt.
- "Chế độ lớp học" và "Tôi cũng sẽ nói" chỉ chọn một: học trực tuyến → "Tôi cũng sẽ nói" + tai nghe; cùng phòng → chế độ lớp học.

## 4. Nhiều người muốn xem phụ đề trên điện thoại

1. IT bật "Cho phép máy tính và điện thoại khác xem phụ đề" và đặt mật khẩu nhân viên (sau đó mở lại ứng dụng).
2. Bắt đầu phụ đề trực tiếp, bấm "Chia sẻ", chiếu mã QR.
3. Mọi người quét mã, nhập mật khẩu nhân viên và chọn ngôn ngữ (chỉ xem). Điện thoại phải kết nối được tới máy đó, thường là trong mạng công ty.

## 5. Biên bản sau cuộc họp

1. "Bản ghi âm → Biên bản" → tải lên bản ghi âm hoặc video Teams/Zoom (mp3, m4a, wav, mp4).
2. Chọn ngôn ngữ **được nói nhiều nhất**; có thể điền chủ đề và số người nói.
3. Có thể đóng trang; quay lại sau để tải biên bản, bản chép lời và tệp phụ đề (khoảng 10–30 phút cho cuộc họp 1 giờ).
4. Biên bản AI (quyết định, việc cần làm, rủi ro) cần chế độ máy chủ; chế độ máy cục bộ tạo bản chép lời và bản dịch.

## Mẹo

- Nói rõ ràng, từng người một, micro gần người nói. Điền chủ đề cuộc họp nếu có nhiều thuật ngữ.
- Phía trên trang cho biết âm thanh và văn bản được xử lý ở đâu. Hãy kiểm tra trước cuộc họp bảo mật.
- Phiên bản ở cuối trang; bấm để sao chép khi báo lỗi.
