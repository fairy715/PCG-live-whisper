# Phiên dịch cuộc họp PCG: hướng dẫn cài đặt và cập nhật

[中文](安裝說明.md) · [English](INSTALL-GUIDE-en.md) · [Bahasa Indonesia](INSTALL-GUIDE-id.md) · [Tiếng Việt](INSTALL-GUIDE-vi.md)

Phiên bản mới nhất: **https://github.com/fairy715/PCG-live-whisper/releases/latest**

Mỗi trang phát hành đều có hướng dẫn giống như vậy và cho biết có thể dùng gói cập nhật nhỏ hay không.

## 1. Tải về

1. Mở trang phát hành: https://github.com/fairy715/PCG-live-whisper/releases/latest
2. Ở mục "Assets" cuối trang, bấm `PCG-Meeting-Translator-Setup-<phiên bản>.exe` (khoảng 1,8 GB).
   * Nếu trình duyệt cảnh báo tệp này "không thường được tải xuống", chọn "Giữ lại" / "Keep" (Edge: bấm "…" → "Giữ lại").
   * Tệp khá lớn: IT cũng có thể đặt tệp vào thư mục dùng chung hoặc Google Drive cho bạn.

## 2. Cài đặt

1. Bấm đúp vào tệp exe vừa tải.
2. Xuất hiện cửa sổ màu xanh "Windows đã bảo vệ PC của bạn" ("Windows protected your PC"):
   * Bấm "Thông tin thêm" ("More info"), rồi bấm "Vẫn chạy" ("Run anyway").
   * Cửa sổ này luôn xuất hiện lần đầu vì bộ cài không có chứng chỉ ký mã.
3. Nếu xuất hiện cửa sổ chọn ngôn ngữ, chọn ngôn ngữ rồi bấm "OK" (thường đã được chọn tự động theo ngôn ngữ Windows).
4. Vị trí cài đặt: mặc định `D:\PCG-live-whisper` (nếu không có ổ D thì là `C:\PCG-live-whisper`). Giữ nguyên, bấm nút tiếp theo rồi bấm cài đặt.
   * Không cần quyền quản trị viên và không cần mạng internet.
5. Cửa sổ hiển thị "Đang cài đặt môi trường chạy và mô hình", mất khoảng 3–10 phút. Đừng đóng cửa sổ.
6. Hoàn tất: đánh dấu "Mở Phiên dịch cuộc họp PCG ngay" rồi bấm nút hoàn tất. Màn hình desktop sẽ có lối tắt "Phiên dịch cuộc họp PCG".

## 3. Sử dụng lần đầu

1. Bấm đúp vào lối tắt trên desktop. Trình duyệt sẽ mở trang ứng dụng (`http://localhost:19781/simple`).
2. Lần đầu sẽ có phần hướng dẫn ngắn. Hãy xem qua một lần.
3. Có thể đổi ngôn ngữ trang ở góc trên bên phải (中文 / English / Bahasa Indonesia / Tiếng Việt / हिन्दी).
4. Phụ đề trực tiếp: chọn ngôn ngữ người đối diện nói → "Bắt đầu". Bản ghi âm: tải tệp lên → khi xử lý xong, tải biên bản cuộc họp về.
5. Phiên bản được hiển thị ở cuối trang (ví dụ v2026.11.5.r5). Hãy ghi kèm khi báo lỗi (bấm vào để sao chép).

## 4. Cập nhật

**Không cần** gỡ phiên bản cũ. Cài đặt, bản ghi âm và bản chép lời đều được giữ lại.

* **Gói cập nhật nhỏ** (`PCG-Update-….exe`, khoảng 10 MB): đóng Phiên dịch cuộc họp PCG → bấm đúp vào gói cập nhật → nếu cửa sổ màu xanh xuất hiện, "Thông tin thêm" → "Vẫn chạy" → xong trong khoảng 1 phút.
  * Nếu thông báo bản cập nhật này "cần thành phần mới, chỉ có trong bộ cài đầy đủ", hãy dùng bộ cài đầy đủ.
* **Bộ cài đầy đủ**: chỉ cần cài đè lên phiên bản cũ.
* IT triển khai hàng loạt (không hiện cửa sổ): thêm `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` sau tên tệp exe.

## 5. Khi gặp sự cố

* Cài đặt thất bại: gửi tệp `D:\PCG-live-whisper\group_data\install.log` (nếu cập nhật thất bại: `update.log`) cho IT.
* Bị phần mềm diệt virus chặn: nhờ IT thêm thư mục cài đặt vào danh sách ngoại lệ.
* Gỡ cài đặt: Windows "Cài đặt" → "Ứng dụng" → "PCG Meeting Translator" → "Gỡ cài đặt". Bản ghi âm, bản chép lời và cài đặt vẫn nằm trong thư mục; xóa thủ công nếu không cần nữa.

## Dành cho IT

* **Trang Cài đặt IT**: trên máy của nhân viên, bấm "Cài đặt IT" ở cuối trang ứng dụng, hoặc mở `http://localhost:19781/simple/admin`.
  * Lần đầu: đặt mật khẩu IT trên máy đó (ít nhất 6 ký tự). Sau đó mỗi lần vào đều phải nhập. Nhân viên không cần biết mật khẩu này.
  * Có thể thay đổi: chế độ máy cục bộ/máy chủ, mô hình ngôn ngữ lớn (Open WebUI của tập đoàn, máy chủ nội bộ hoặc dịch vụ AI bên ngoài) và khóa API, máy chủ GPU, mô hình nhận dạng giọng nói, mật khẩu nhân viên, cho phép máy khác xem phụ đề.
  * Có hiệu lực ngay khi lưu, không cần cài lại. Chi tiết trong [INSTALL.md](INSTALL.md) (tiếng Trung).
