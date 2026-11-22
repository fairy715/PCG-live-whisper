# Phiên bản tập đoàn PCG: kiến trúc và cài đặt (dành cho IT)

[中文](INSTALL.md) · [English](IT-GUIDE-en.md) · [Bahasa Indonesia](IT-GUIDE-id.md) · [Tiếng Việt](IT-GUIDE-vi.md)

<!-- Khi sửa hướng dẫn này, cập nhật cả bốn ngôn ngữ (INSTALL.md, IT-GUIDE-en.md, IT-GUIDE-id.md, IT-GUIDE-vi.md). -->

Trang cài đặt IT hiện có tiếng Trung, tiếng Anh và tiếng Indonesia: hãy chọn **English** ở góc trên bên phải. Tên nút trong hướng dẫn này ghi theo giao diện tiếng Anh.

## Kiến trúc

```
                         ┌──────────────── Mạng nội bộ công ty ─────────┐
                         │                                              │
  Máy nhân viên (trình duyệt) │ ① Máy chủ ứng dụng (Linux, không cần GPU) │
  ───────────────────    │   ─────────────────────────────              │
  http://may-chu-ung-dung:19781/simple ─→ WebUI (gồm trang đơn giản /simple) │
  tải bản ghi âm lên → tải biên bản về │ hàng đợi: xử lý từng việc, còn lại chờ │
                         │   lưu trữ: recordings/, kết quả logs/        │
                         │        │ nhận dạng giọng nói │ dịch/tóm tắt  │
                         │        ▼                     ▼              │
                         │   ② Máy GPU (Ubuntu + NVIDIA)                │
                         │   ─────────────────────────────              │
                         │   Dịch vụ nhận dạng giọng nói GPU (cổng 8978) │
                         │   LLM Ollama (cổng 11434)                    │
                         │     dịch gemma4:26b, tóm tắt qwen3.8:27b     │
                         │        ▲                     ▲              │
  ③ Máy nhân viên cần phụ đề trực tiếp ─┘───────────────┘              │
  (cài trên từng máy Windows/Mac)                                       │
  thu âm thanh phát trên máy đó → http://localhost:19781/simple         │
                         └──────────────────────────────────────────────┘
```

| Vai trò | Chức năng | Phần cứng đề xuất |
|---|---|---|
| ① Máy chủ ứng dụng | Trang web, hàng đợi công việc, lưu bản ghi âm và biên bản | Linux (Ubuntu 22.04 / Debian 12 trở lên), 2 vCPU, RAM 4 GB, ổ đĩa tùy lượng ghi âm (một giờ m4a khoảng 30–60 MB) |
| ② Máy GPU | Nhận dạng giọng nói, dịch, tóm tắt (phần nặng nhất) | NVIDIA DGX Spark, hoặc RTX 4090/5090 (VRAM từ 24 GB) + RAM 64 GB; chạy nhận dạng và LLM cùng lúc |
| ③ Máy nhân viên | Chỉ người cần **phụ đề trực tiếp** mới cài | Windows 10/11 hoặc Mac; nhận dạng và dịch do ② đảm nhận nên máy văn phòng thông thường là đủ |

- **Chế độ cục bộ và máy chủ nội bộ: âm thanh và văn bản không ra khỏi mạng công ty.** Với Open WebUI của tập đoàn, văn bản được gửi đến các mô hình phía sau nó (hãy xác nhận luna/deepseek nằm trong tập đoàn); với "Dịch vụ AI bên ngoài", dữ liệu ra khỏi công ty (xem "Chế độ máy chủ: ba cách kết nối LLM" bên dưới)
- ① và ② có thể là một máy, nhưng tác giả gốc khuyên nên tách riêng: khi máy GPU chạy LLM, trang web và xử lý tệp ổn định hơn trên máy khác
- Phụ đề trực tiếp phải chạy trên chính ③: nó thu **âm thanh phát ra trên máy đó** (Teams, Zoom), máy chủ không lấy được

## Trước khi cài đặt

1. **Không dùng lệnh cài đặt một dòng của tác giả gốc** (`curl … jasoncheng7115 … | bash`, `irm … | iex`): lệnh này cài phiên bản gốc, không có các ngôn ngữ mới và trang đơn giản
2. **Không cập nhật bằng `./install.sh --upgrade`**: lệnh này tải phiên bản gốc và ghi đè phiên bản tập đoàn (phiên bản tập đoàn đã chặn và nhắc dùng git pull)
3. Kho mã có thể là riêng tư: tải về cần quyền GitHub (tài khoản, hoặc nhờ quản trị viên tạo deploy key chỉ đọc)

## ② Máy GPU

1. Cài driver NVIDIA và CUDA (`nvidia-smi` hiện được card đồ họa)
2. Cài Ollama và tải mô hình:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma4:26b       # dịch
   ollama pull qwen3.8:27b      # tóm tắt, sửa bản chép lời
   ```
   Cho phép truy cập trong mạng LAN: thêm `OLLAMA_HOST=0.0.0.0` vào cấu hình systemd của Ollama, và chỉ mở tường lửa cho ① và dải mạng của máy nhân viên
3. Dịch vụ nhận dạng giọng nói GPU **không cần cài thủ công**: cuối quá trình cài ① sẽ hỏi về máy chủ GPU; nhập địa chỉ máy và dịch vụ được cài tự động qua SSH

## ① Máy chủ ứng dụng

```bash
# 1. Tải phiên bản tập đoàn (dùng tài khoản thường, không dùng root)
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper

# 2. Cài dạng máy chủ (WebUI chạy thường trực bằng dịch vụ systemd jt-live-whisper-webui)
bash install.sh --server
```

Trong quá trình cài:
- `sudo apt` bổ sung các gói hệ thống như ffmpeg
- **"Mật khẩu quản trị" và "mật khẩu chỉ đọc" chỉ in ra một lần: ghi lại ngay**
- Cuối cùng sẽ hỏi máy chủ GPU: nhập địa chỉ ②, dịch vụ nhận dạng giọng nói GPU được cài qua SSH
- Máy chủ LLM: đặt địa chỉ Ollama của ② trong WebUI (`http://may-chu-ung-dung:19781`, bằng mật khẩu quản trị), hoặc ghi vào `llm_host` trong `config.json`

### Trang cài đặt IT (không cần sửa tệp cấu hình)

Mở trang cài đặt IT **trên chính máy cần cài đặt** ("IT settings" ở cuối trang đơn giản):

- Máy nhân viên (cài bằng bộ cài ngoại tuyến): `http://localhost:19781/simple/admin`
- Máy chủ ứng dụng: `http://may-chu-ung-dung:19781/simple/admin`

1. **Lần đầu**: mở trên máy đó và đặt mật khẩu IT (ít nhất 6 ký tự). Sau đó lần nào cũng phải nhập, kể cả trên máy
2. **Chế độ** (Mode): chế độ cục bộ (CPU, dịch bằng M2M100, không có biên bản AI) / chế độ máy chủ (máy chủ LLM dịch và tạo biên bản AI; máy chủ GPU tùy chọn)
3. **Địa chỉ máy chủ**: nhập URL máy chủ LLM (bắt buộc) và máy chủ GPU (tùy chọn) → bấm "Test connection" → danh sách mô hình trên máy chủ hiện ra để chọn.
   Không có máy chủ GPU thì nhận dạng giọng nói ở lại máy này (dùng "mô hình nhận dạng cục bộ"); chỉ dịch và biên bản được gửi đến LLM
4. **Mật khẩu nhân viên**: cần nhập khi kết nối từ máy khác (trên máy thì không cần)
5. Bấm "Save": có hiệu lực khi phụ đề hoặc bản ghi âm tiếp theo bắt đầu; không cần khởi động lại

Cài đặt lưu trong cùng `config.json` (mật khẩu ở dạng băm), cùng định dạng với chương trình gốc.

### Cập nhật một lần bấm

Phần "Updates" trên trang cài đặt IT:

- **Kiểm tra phiên bản mới** (bật sẵn): khi có gói cập nhật nhỏ mới, nhân viên thấy "Có phiên bản mới" và "Cập nhật ngay" phía trên trang
- **Ai được cập nhật**: nhân viên tự bấm (mặc định) / chỉ IT (cần mật khẩu IT)
- **Nguồn cập nhật**:
  1. **Thư mục dùng chung của công ty** (tùy chọn, ví dụ `\\fileserver\PCG\update`): đặt `PCG-Update-<phiên bản>.exe` và tệp `.sha256` cùng tên từ trang phát hành vào đó. Máy không có internet nhưng vào được mạng công ty cũng cập nhật một lần bấm được
  2. **Trang phát hành GitHub**: máy có internet tự động dùng (không dùng được khi kho mã chuyển sang riêng tư; khi đó dùng thư mục dùng chung)
- Sau khi bấm cập nhật: tải về (hoặc sao chép từ thư mục dùng chung) → so dấu vân tay tệp, không khớp thì xóa và không cài → đóng ứng dụng → cài → tự kiểm tra → tự mở lại; trang đang mở tự tải lại
- Không cập nhật được khi đang chạy phụ đề trực tiếp hoặc xử lý bản ghi âm; phiên bản cần bộ cài đầy đủ chỉ hiện "liên hệ IT"
- Nhật ký: `group_data\update.log`; tệp đã tải: `group_data\updates\`
- **Tệp dấu vân tay `.sha256`**: mỗi gói cập nhật nhỏ có một tệp `.sha256` cùng tên, chứa dấu vân tay SHA-256 của tệp exe (một dòng, 64 ký tự)
  - Thư mục dùng chung: đặt `.exe` và `.sha256` cùng nhau; dấu vân tay được so trước khi cài, không khớp thì từ chối; không có `.sha256` vẫn cài, nhưng không kiểm tra
  - GitHub: không cần tệp này; ứng dụng đọc trực tiếp dấu vân tay của tệp đính kèm trên trang phát hành, không có thì không cài
  - Kiểm tra thủ công (PowerShell): `Get-FileHash .\PCG-Update-<phiên bản>.exe -Algorithm SHA256`; tệp nguyên vẹn khi mã băm trùng với nội dung `.sha256` (không phân biệt hoa thường)
- **Cửa sổ tính năng mới** (các bản cập nhật sau r19): khi nhân viên mở trang, cửa sổ "Có phiên bản mới" liệt kê tính năng mới của phiên bản này, có thể chọn "Cập nhật ngay" hoặc "Để sau"; chọn "Để sau" thì thông báo cập nhật vẫn nằm ở đầu trang như trước và cửa sổ không bật lại cho đến lần mở trang sau. Trong thư mục dùng chung có thể đặt thêm `PCG-Update-<phiên bản>.whats-new.json` (trang phát hành có kèm `whats-new.json`, chỉ cần đổi tên); không có tệp này thì chỉ hiện số phiên bản

### Chế độ máy chủ: ba cách kết nối LLM

"Server type" trên trang cài đặt IT:

| Loại | Khi nào dùng | URL | Khóa API |
|---|---|---|---|
| Open WebUI của tập đoàn | Hiện tại (luna, deepseek) | Địa chỉ mở Open WebUI trên trình duyệt | Bắt buộc |
| Máy chủ nội bộ | Khi có RTX Spark / DGX Spark, hoặc Ollama, vLLM tự dựng | `máy:11434` | Thường không cần |
| Dịch vụ AI bên ngoài | OpenAI, DeepSeek, Google Gemini, OpenRouter, v.v. | Bấm nút để điền base URL | Bắt buộc |

Máy chủ GPU (nhận dạng giọng nói) tách riêng với LLM; kết hợp tùy ý, ví dụ LLM dùng Open WebUI của tập đoàn, nhận dạng dùng RTX Spark riêng.
Nếu đã nhập máy chủ GPU nhưng lúc đó không kết nối được, nhận dạng tự chuyển sang mô hình nhỏ trên máy nhân viên, không bị treo.

#### Open WebUI của tập đoàn (luna, deepseek)

1. Tạo khóa API trong Open WebUI: đăng nhập → ảnh đại diện góc trên bên phải → Settings → Account → API keys → Create
   (Không thấy mục này: nhờ quản trị viên AI của tập đoàn bật API Keys trong "Admin settings → User permissions")
2. Trang cài đặt IT: chế độ "Server mode", loại "Group Open WebUI", nhập URL (ví dụ `https://ai.ten-mien-cong-ty`), dán khóa
3. Bấm "Test connection" và chọn trong danh sách: **dịch: luna** (nhanh, phụ đề trực tiếp không trễ), **biên bản: deepseek** (mô hình suy luận, chậm nhưng đầy đủ)
4. Không có máy chủ GPU thì để trống các ô GPU: nhận dạng chạy trên CPU của máy nhân viên (mô hình small)

Lưu ý: khóa là **cá nhân**, lượng dùng tính cho người tạo; nên tạo tài khoản riêng. Máy nhân viên phải truy cập được địa chỉ Open WebUI.

#### Máy chủ nội bộ (RTX Spark, DGX Spark)

Khi có máy, một máy có thể vừa làm "LLM" vừa làm "nhận dạng giọng nói GPU":

- **LLM**: cài Ollama trên Spark, tải mô hình và cho phép truy cập trong LAN (`OLLAMA_HOST=0.0.0.0`). Trên trang cài đặt IT chọn loại "Internal server" và nhập `IP-Spark:11434`
- **Nhận dạng giọng nói GPU**: Spark chạy dịch vụ nhận dạng GPU của tác giả gốc (`remote_whisper_server.py`, hỗ trợ DGX Spark aarch64).
  Nhập `IP-Spark` và cổng `8978` ở "GPU server" trên trang cài đặt IT
  - DGX Spark (DGX OS / Ubuntu): chạy `bash install.sh` từ một máy Linux hoặc Mac; khi được hỏi máy chủ GPU, nhập địa chỉ Spark; dịch vụ được cài qua SSH và tự chạy khi khởi động
  - Laptop RTX Spark (Windows on Arm): dịch vụ nhận dạng chỉ có bản Linux, phải cài trong WSL2; **cần kiểm tra thực tế khi máy về**
- Máy nhân viên kết nối dịch vụ GPU **chỉ qua URL**; không cần và không dùng SSH (dịch vụ chạy bằng systemd trên Spark)
- Chỉ có LLM mà không có nhận dạng GPU cũng được: vẫn dịch và tạo biên bản bình thường

#### Dịch vụ AI bên ngoài (OpenAI, DeepSeek, Gemini…)

- **Nội dung cuộc họp ra khỏi công ty** và tính phí theo lượng dùng: trước hết xác nhận phù hợp quy định dữ liệu của công ty; cuộc họp bảo mật hãy dùng Open WebUI hoặc máy chủ nội bộ
- Đăng ký khóa bằng tài khoản công ty và đặt hạn mức dùng hằng tháng trên trang của dịch vụ
- Chọn loại "External AI service" → bấm OpenAI / DeepSeek / Google Gemini / OpenRouter để điền URL → dán khóa → Test connection → chọn mô hình
- Các dịch vụ tương thích OpenAI khác cũng dùng được: nhập base URL theo tài liệu của họ (thường kết thúc bằng `/v1`). Không hỗ trợ Azure OpenAI (cách xác thực khác); hãy dùng OpenRouter hoặc proxy LiteLLM

Các trường cấu hình (để xử lý sự cố): `llm_url`, `llm_api_key`, `llm_api_style` (`openwebui` / `openai` / không có = nội bộ, tự nhận diện), `remote_whisper.host`.

Nên giới hạn thêm IP nguồn (chỉ dải mạng công ty) trong "Cài đặt bảo mật" của WebUI đầy đủ.

**URL cho nhân viên: `http://may-chu-ung-dung:19781/simple`** (WebUI đầy đủ ở `/`, dành cho IT)

## Cài đặt ngoại tuyến trên máy nhân viên (không cần internet hay máy chủ GPU)

**Xem [windows/README.md](windows/README.md)**: bộ cài đơn, mặc định chế độ cục bộ (CPU);
khi có máy chủ GPU, IT chỉ cần chuyển trên `/simple/admin`. Mục "③" bên dưới là cách cài khác khi có internet.

### Mức dùng CPU (khi máy nhân viên tự nhận dạng)

Khi phụ đề trực tiếp và bản ghi âm chạy trên CPU của máy nhân viên (chế độ cục bộ, hoặc chế độ máy chủ chỉ kết nối máy chủ LLM):

- Nhận dạng giọng nói + dịch cục bộ cộng lại chỉ dùng khoảng **3/4 số nhân**, không bao giờ vượt quá số nhân vật lý (laptop 4 nhân: nhận dạng 2–3, dịch 1), chừa chỗ cho Teams và chương trình khác
- Trên Windows tiến trình chạy ở mức ưu tiên **thấp hơn bình thường**: khi CPU bận, chương trình đang dùng được ưu tiên, Teams và chuột không bị giật
  - **Tự trở lại mức bình thường khi phụ đề bị chậm** (r20): nếu một đoạn âm thanh chờ nhận dạng quá 6 giây (ví dụ video Teams dùng hết CPU), mức ưu tiên tạm trở lại bình thường; phụ đề chậm hơn một chút nhưng vẫn hiện. Sau 30 giây liên tục theo kịp thì hạ lại. Trước đây, trên laptop 2 nhân khi mở Teams phụ đề dừng hẳn, đóng Teams mới hiện ra một lúc
  - **Laptop tiết kiệm điện 2 nhân 4 luồng** (ví dụ i3-10110U): nhận dạng dùng 2 luồng (trước đây 1)
- **Cắt câu theo lúc ngừng nói** (r21, mặc định cho phụ đề trực tiếp cục bộ): trước đây cứ 3 giây lại nhận dạng lại 5 giây âm thanh gần nhất (mỗi đoạn âm thanh bị tính 1,7 lần); nay chỉ cắt khi người nói ngừng và mỗi đoạn nhận dạng một lần, bản dịch cũng chờ hết câu mới gửi. Khi thử cùng 38 giây tiếng Anh (Whisper base, 2 luồng), CPU nhận dạng giảm từ 20,9 xuống 13,3 giây (ít hơn 37%), phụ đề hiện thành câu trọn vẹn thay vì nửa câu lặp lại. Khi Whisper bị kẹt lặp đi lặp lại cùng một câu, đoạn đó được nhận dạng lại một lần với nhiệt độ khác và phần lặp còn lại chỉ giữ một lần. Muốn quay lại cách cũ: biến môi trường hệ thống Windows `PCG_LIVE_SEGMENT=window` (khởi động lại chương trình sau đó)
- **Mô hình phụ đề trực tiếp cục bộ "Automatic"** (mặc định từ r21): máy 2 nhân dùng gói **Whisper base** nếu đã cài (nếu chưa thì dùng small có sẵn, và trang cài đặt IT sẽ gợi ý cài); máy có gói GPU đã qua kiểm tra dùng gói large-v3-turbo hoặc medium nếu đã cài; còn lại dùng small có sẵn. Trang cài đặt IT cho biết máy này dùng mô hình nào. Máy trước đây đã lưu small thì vẫn dùng small; chọn "Automatic (recommended)" rồi lưu để chuyển
- Máy cũ vẫn nặng, phụ đề bị chậm: trước hết cài gói **Whisper base (đa ngôn ngữ)** ở "Models", rồi chọn nó làm "Local live subtitle model" (nhanh hơn nhưng sai nhiều hơn). **Ứng dụng không bao giờ tự tải mô hình** (bản cài ngoại tuyến không tải), nên trang cài đặt chỉ liệt kê các mô hình có trên máy này
- Điều chỉnh (biến môi trường hệ thống Windows, sau đó mở lại ứng dụng):
  - `PCG_CPU_THREADS=8`: tổng số luồng (ví dụ máy bàn mạnh muốn chạy hết tốc độ)
  - `PCG_NORMAL_PRIORITY=1`: trở về mức ưu tiên bình thường

### API nhận dạng giọng nói (r24, tùy chọn)

Mục "**Speech recognition API**" trong trang cài đặt IT chuyển việc nhận dạng giọng nói cho một API tương thích OpenAI (`/audio/transcriptions`). Thường chính xác hơn mô hình nhỏ trên máy nhân viên, và laptop không phải chạy nhận dạng nữa.

| Nơi kết nối | Địa chỉ | Âm thanh đi đâu | Chi phí |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1`, mô hình ví dụ `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `whisper-1` | **Ra khỏi công ty** | Tính theo thời lượng âm thanh theo giá OpenAI công bố; mỗi máy đang hiện phụ đề được tính riêng |
| Groq (r26) | `https://api.groq.com/openai/v1`, mô hình `whisper-large-v3-turbo` (mặc định) hoặc `whisper-large-v3` | **Ra khỏi công ty** | Có hạn mức miễn phí kèm giới hạn sử dụng (xem bên dưới); lấy khóa tại [console.groq.com/keys](https://console.groq.com/keys) |
| Dịch vụ nhận dạng trong công ty (RTX Spark, hoặc máy chủ tương thích OpenAI của nhóm khác) | Ví dụ `http://10.x.x.x:8000/v1` | Ở lại trong công ty | Không tốn thêm |

- Điền địa chỉ, mô hình và khóa (dịch vụ nội bộ có thể không cần khóa) rồi bấm "**Test connection**": gửi 1 giây im lặng để kiểm tra địa chỉ, khóa và mô hình
- **Dịch vụ bên ngoài phải dùng https và có khóa**; địa chỉ là IP nội bộ hoặc tên máy đơn giản được coi là nội bộ, còn dịch vụ nội bộ có tên miền thì đánh dấu "This is a service inside the company"
- Khi bật: mỗi câu phụ đề trực tiếp (đoạn cắt ở chỗ ngừng nói) gửi một lần; bản ghi được cắt ở chỗ ngừng thành các đoạn tối đa 25 giây. **Được ưu tiên hơn máy chủ GPU**, và tiếng Anh cũng gửi qua API (không dùng Moonshine)
- **Khi API không kết nối được, quá chậm hoặc sai khóa**: đoạn đó được nhận dạng trên máy này, phụ đề không bị ngắt; sau 3 lần lỗi liên tiếp API tạm dừng 2 phút, và 10 phút nếu sai khóa hoặc sai mô hình
- Các thuật ngữ trong bảng thuật ngữ được gửi làm gợi ý (`prompt`), các cách viết nghe sai vẫn được đổi lại
- Khi âm thanh ra khỏi công ty, thông báo màu cam hiện ở trang cài đặt IT và đầu trang của nhân viên. Hãy tắt khi họp mật hoặc dùng dịch vụ nội bộ
- Khóa được lưu trong `config.json` của máy này (`pcg_simple.asr_api_key`) và được che trong tệp chẩn đoán; biến môi trường hệ thống Windows `PCG_ASR_API=off` tạm tắt API
- Chế độ "Tôi cũng nói" (hai chiều) vẫn gửi âm thanh chồng lấn mỗi 3 giây, lượng dùng khoảng 1,7 lần so với một chiều
- **Groq (r26)**: bấm "Groq (free tier)" trong trang cài đặt để điền sẵn địa chỉ và mô hình, dán khóa rồi bấm "Test connection". Nhận dạng dùng Whisper large-v3, chính xác hơn mô hình small có sẵn; chương trình vẫn gửi cho API trước và quay về máy này khi API không dùng được
  - **Hạn mức miễn phí có giới hạn, dùng chung cho cả tài khoản.** Số liệu do các trang bên thứ ba tổng hợp (Groq có thể thay đổi bất cứ lúc nào; hãy xem [trang giới hạn trong bảng điều khiển Groq](https://console.groq.com/settings/limits)): khoảng 20 yêu cầu mỗi phút, khoảng 2.000 yêu cầu mỗi ngày, khoảng 7.200 giây âm thanh mỗi giờ và khoảng 28.800 giây (8 giờ) mỗi ngày
  - Thực tế: một máy ở chế độ "Chỉ đọc phụ đề" (mỗi câu một yêu cầu) gửi khoảng 8–15 yêu cầu mỗi phút, tức khoảng 2–4 giờ mỗi ngày; nhiều máy dùng chung một khóa cùng lúc, hoặc "Tôi cũng nói" (3 giây một yêu cầu, đúng 20 yêu cầu mỗi phút), sẽ nhanh chạm giới hạn
  - **Khi chạm giới hạn (HTTP 429)**: đoạn đó được nhận dạng ngay trên máy này, và API tạm dừng theo thời gian Groq yêu cầu (ít nhất 15 giây, nhiều nhất 10 phút, 60 giây nếu không nêu), sau đó tự động dùng lại; phụ đề không bị ngắt, chỉ là độ chính xác trở về mô hình cục bộ trong thời gian đó. "Test connection" sẽ báo đã kết nối nhưng chạm giới hạn sử dụng
  - Không thể đặt sẵn khóa trong bộ cài (bộ cài là công khai), nên IT nhập một lần trên mỗi máy; nếu dùng nhiều, hãy trả phí hoặc dùng dịch vụ nhận dạng trong công ty
  - Đã thử ngày 2026-11-18 với máy chủ mô phỏng (gồm cả 429); chưa thử với khóa Groq thật
- Đã thử ngày 2026-11-18 với máy chủ API giả lập; chưa thử với khóa OpenAI thật, nên hãy bấm "Test connection" khi cài lần đầu

### Bảng thuật ngữ (tên riêng và thuật ngữ, r23)

Tên công ty, nhà máy, tên hệ thống và tên người thường bị các mô hình chung nghe sai hoặc dịch sai. Sau khi điền "**Glossary**" trong trang cài đặt IT:

| Giai đoạn | Việc được làm | Có hiệu lực ở đâu |
|---|---|---|
| Nhận dạng | Các thuật ngữ được đưa cho Whisper làm gợi ý, âm gần giống sẽ ưu tiên chọn các từ này | Tiếng Trung, Indonesia, Việt… nhận dạng trên máy nhân viên (Whisper). Phụ đề tiếng Anh (Moonshine) và nhận dạng trên máy chủ GPU không dùng gợi ý |
| Sau nhận dạng | Các cách viết ghi là "hay bị nghe sai" được đổi lại thành từ đúng | Tất cả (kể cả phụ đề tiếng Anh và máy chủ GPU) |
| Dịch | Chế độ máy chủ: yêu cầu mô hình lớn dùng bản dịch đã chỉ định và giữ nguyên các từ không có bản dịch. Chế độ cục bộ (M2M100): thay thuật ngữ bằng bản dịch đã chỉ định trước khi dịch | Đáng tin cậy nhất ở chế độ máy chủ; ở chế độ cục bộ thường có hiệu lực, không bảo đảm |

Định dạng: mỗi dòng một thuật ngữ. Sau "`=`" là bản dịch bắt buộc (tùy chọn), sau "`|`" là các cách viết hay bị nghe sai; dán từ Excel cũng được (ba cột: thuật ngữ, bản dịch, cách viết nghe sai).

```
寶成 | 寶城 | 保成 = Pou Chen
MES
Sukabumi | Suka Bumi
# dòng bắt đầu bằng # là ghi chú
```

- Có hiệu lực từ phụ đề hoặc bản ghi **kế tiếp** sau khi lưu; tối đa 500 thuật ngữ và 20000 ký tự. Chỉ 60 thuật ngữ đầu được đưa cho Whisper làm gợi ý (nhiều hơn sẽ kém đi), nên **đặt thuật ngữ quan trọng lên trước**
- **Dùng chung cho mọi máy**: đặt tệp `glossary.txt` (UTF-8) cùng định dạng vào thư mục dùng chung của công ty đã cài ở phần "Updates"; mỗi máy đọc khi bắt đầu phụ đề hoặc xử lý bản ghi, không kết nối được thì dùng bản đọc lần trước. Cùng một thuật ngữ thì mục điền trên máy này được ưu tiên
- Thuật ngữ tiếng Anh từ 3 chữ cái trở xuống (ví dụ ME) phải khớp đúng chữ hoa/thường, để chữ "me" thông thường không bị coi là thuật ngữ
- Gợi ý chỉ tăng khả năng, không bảo đảm: với từ vẫn bị nghe sai, thêm cách viết sai sau "`|`" là cách chắc chắn nhất
- Bảng thuật ngữ được lưu trong `config.json` của máy này (`pcg_simple.glossary`) và có trong tệp chẩn đoán "Report a problem"

### Quản lý mô hình (gói mô hình, từ r15)

Bộ cài chính chỉ có phần cơ bản (Whisper small, M2M100, Moonshine cho tiếng Anh); các mô hình khác là **gói mô hình**, cài ở "Models" trên trang cài đặt IT:

| Gói mô hình | Công dụng | Dung lượng | Giấy phép |
|---|---|---|---|
| PhoWhisper small / medium | Nhận dạng giọng nói tiếng Việt | khoảng 240 / 740 MB | BSD-3-Clause |
| Whisper small tiếng Indonesia (maleo-ai) | Nhận dạng giọng nói tiếng Indonesia | khoảng 240 MB | Apache-2.0 |
| Whisper medium tiếng Indonesia (cahya) | Nhận dạng giọng nói tiếng Indonesia | khoảng 740 MB | Apache-2.0 |
| Whisper small / medium tiếng Hindi (vasista22) | Nhận dạng giọng nói tiếng Hindi | khoảng 240 / 740 MB | Apache-2.0 |
| Breeze ASR 25 (MediaTek Research, r25) | Nhận dạng tiếng Trung Đài Loan và tiếng Trung pha tiếng Anh; cỡ large-v2, cần card NVIDIA để chạy phụ đề trực tiếp | khoảng 1,5 GB | Apache-2.0 |
| Whisper base / medium / large-v3-turbo (đa ngôn ngữ, OpenAI) | "Mô hình nhận dạng cục bộ" cho mọi ngôn ngữ (kể cả tiếng Trung), cũng dùng cho hai chiều và chế độ lớp học | khoảng 80 / 740 / 800 MB | Apache-2.0 (base, medium) / MIT (large-v3-turbo) |
| MADLAD-400 3B | Dịch cục bộ (chậm hơn; khi dịch thử có thêm nội dung không có trong câu gốc, hãy so sánh trước khi đổi) | khoảng 2,8 GB | Apache-2.0 |

**Tự động gợi ý khi mở trang** (r25): dựa trên máy này và "ngôn ngữ của người kia" mà nhân viên chọn lần trước, chương trình gợi ý một gói mô hình chưa cài, mỗi lần một gói: có tăng tốc GPU + tiếng Trung → Breeze ASR 25; tiếng Việt / Indonesia / Hindi → gói của ngôn ngữ đó (medium nếu có tăng tốc GPU, small nếu không); có tăng tốc GPU và chưa có mô hình đa ngôn ngữ lớn → large-v3-turbo; máy 2 nhân → base. Nhân viên có thể bấm "Cài đặt" (gói được tự gán cho ngôn ngữ đó), "Để sau" (nhắc lại gói này sau 7 ngày) hoặc "Không nhắc lại". Khi mục "ai được cập nhật" là chỉ IT, cửa sổ chỉ đề nghị nhân viên liên hệ IT. Không gợi ý theo phần cứng khi IT đã chọn cố định "mô hình phụ đề trực tiếp cục bộ". Không gợi ý khi không đọc được danh sách (không có internet và thư mục dùng chung không có `catalog.json`) hoặc thiếu dung lượng đĩa.

Tiếng Indonesia small dùng maleo-ai/whisper-small-id (Apache-2.0); cahya/whisper-small-id chỉ ghi "cc" nên không xác nhận được việc dùng thương mại, khi đóng gói tự động bỏ qua.

#### Nên cài gói nào (đề xuất)

**Chỉ cài trên máy cần dùng**: ví dụ máy của nhân viên Đài Loan thường họp với đồng nghiệp Việt Nam thì cài gói tiếng Việt. Máy của nhân viên nước ngoài (chọn "Tiếng Trung → ngôn ngữ của tôi") nghe tiếng Trung nên **không cần** gói ngôn ngữ.

| Ngôn ngữ | Phụ đề trực tiếp (laptop thường, CPU) | Phụ đề trực tiếp (card NVIDIA + gói GPU) | Bản ghi âm |
|---|---|---|---|
| Tiếng Việt | PhoWhisper small | PhoWhisper medium | PhoWhisper medium |
| Tiếng Indonesia | Whisper small tiếng Indonesia (maleo-ai) | Whisper medium tiếng Indonesia (cahya) | Whisper medium tiếng Indonesia (cahya) |
| Tiếng Hindi | Whisper small tiếng Hindi | Whisper medium tiếng Hindi | Whisper medium tiếng Hindi |
| Dịch cục bộ | Giữ M2M100 có sẵn | Giữ M2M100 có sẵn | Tạm giữ M2M100; quyết định MADLAD-400 sau khi so sánh |

- small khoảng 240 MB, medium khoảng 740 MB; cả hai cho một ngôn ngữ khoảng 1 GB
- Trên CPU, medium chậm hơn small 2–3 lần: laptop thường dùng small cho phụ đề trực tiếp, medium để cho bản ghi âm
- Nhận dạng thử khi đóng gói (giọng tổng hợp): PhoWhisper medium và tiếng Indonesia small đúng hoàn toàn; PhoWhisper small và tiếng Indonesia medium mỗi gói sai một từ. Hãy thử với bản ghi âm thật
- Ở chế độ máy chủ có máy chủ GPU, nhận dạng chạy trên máy chủ và các gói trên máy nhân viên không được dùng

#### Kết quả đo: tỷ lệ lỗi của từng mô hình (bộ dữ liệu công khai, 2026-11-19)

Các đề xuất ở trên có số liệu đo: mỗi mô hình được chạy một lần trên các bộ dữ liệu giọng nói công khai rồi so với văn bản chuẩn. Mỗi ngôn ngữ 50 câu; tỷ lệ lỗi = số chữ (tiếng Trung) hoặc số từ (ngôn ngữ khác) bị sai ÷ số chữ/từ trong văn bản chuẩn, **càng thấp càng tốt**.

| Mô hình | Tiếng Trung | Tiếng Indonesia | Tiếng Việt | Tiếng Hindi | Tiếng Anh | Trung-Anh xen kẽ | Thời gian xử lý ÷ độ dài âm thanh |
|---|---|---|---|---|---|---|---|
| Whisper base (gói) | 17,2% | 30,6% | 40,1% | 105,7% | 8,9% | 37,6% | 0,1 |
| **Whisper small (có sẵn trong bộ cài)** | 10,6% | 16,1% | 20,7% | 55,9% | 6,1% | 28,1% | 0,3 |
| Gói small riêng cho ngôn ngữ đó | — | 9,2% | 13,1% | 14,8% | — | — | 0,3 (tiếng Hindi 0,6) |
| Whisper medium (gói) | 6,0% | 9,1% | 14,0% | 36,7% | 4,4% | 26,8% | 0,85 |
| Gói medium riêng cho ngôn ngữ đó | — | 7,1% | 9,7% | 11,2% | — | — | 0,85 (tiếng Hindi 1,5) |
| Whisper large-v3-turbo (gói) | 5,9% | 7,6% | 10,2% | 30,5% | 4,8% | 20,9% | 1,0 |
| Breeze ASR 25 (gói) | 5,3% | — | — | — | — | 17,8% | 1,6 |

- "Riêng cho ngôn ngữ đó": PhoWhisper cho tiếng Việt, maleo-ai (small) / cahya (medium) cho tiếng Indonesia, vasista22 cho tiếng Hindi.
- Cột cuối được đo trên máy 4 nhân **không có card đồ họa**: 0,3 nghĩa là 10 giây âm thanh mất 3 giây xử lý; gần bằng hoặc lớn hơn 1 thì không theo kịp phụ đề trực tiếp, cần card NVIDIA và gói GPU.

**Những điều thấy được từ số liệu**

- **Mô hình small có sẵn là điểm nghẽn**: trừ tiếng Anh, thay nó giúp giảm từ 40% đến hơn một nửa số lỗi; rõ nhất là tiếng Hindi (55,9% → 11,2%).
- **Ngoại ngữ vẫn cải thiện được khi không có card đồ họa**: các gói small cho tiếng Indonesia, tiếng Việt và tiếng Hindi chạy nhanh gần bằng mô hình có sẵn và giảm tỷ lệ lỗi từ 16,1% / 20,7% / 55,9% xuống 9,2% / 13,1% / 14,8%. Với máy thường nghe các ngôn ngữ này, đây là bước ít tốn kém nhất.
- **Tiếng Trung không có lựa chọn ít tốn kém**: chỉ medium, large-v3-turbo và Breeze ASR 25 mới giảm từ 10,6% xuống dưới 6%, và cả ba đều ở mức sát hoặc vượt giới hạn phụ đề trực tiếp trên máy thường, nên cần card đồ họa.
- **Máy có card đồ họa**: Breeze ASR 25 cho tiếng Trung và Trung-Anh xen kẽ; gói medium riêng cho tiếng Indonesia, tiếng Việt và tiếng Hindi; large-v3-turbo nếu chỉ muốn cài một mô hình chung, nhưng tiếng Hindi của nó kém (30,5%).
- **Breeze và large-v3-turbo không phân biệt được trên tiếng Trung thuần** (5,3% so với 5,9%, chênh 11 chữ); khoảng cách ở Trung-Anh xen kẽ rõ hơn (17,8% so với 20,9%).

**Giới hạn (không áp dụng trực tiếp các con số này cho cuộc họp thực tế)**

- Dữ liệu là bản ghi đọc sạch; cuộc họp thực tế có micro đặt xa, nhiều người nói chen nhau và giọng địa phương, nên tỷ lệ lỗi sẽ cao hơn trong bảng. Thứ hạng giữa các mô hình vẫn dùng để tham khảo được.
- Bộ tiếng Trung là tiếng phổ thông của Trung Quốc đại lục, không phải giọng Đài Loan; ưu thế của Breeze ASR 25 với tiếng Trung Đài Loan có thể bị đánh giá thấp.
- Mỗi ngôn ngữ chỉ có 50 câu: chênh một hai điểm phần trăm chưa chắc là khác biệt thật.
- Tiếng Hindi với base vượt 100%, nghĩa là mô hình xuất ra thêm nhiều từ sai; chưa kiểm tra nguyên nhân từng câu.
- Nếu cuộc họp thực tế tệ hơn bảng này nhiều thì nguyên nhân thường là âm thanh (micro quá xa, phòng bị vang); đổi mô hình hay card đồ họa không giúp được phần đó.

**Dữ liệu và chạy lại**: tiếng Trung, tiếng Indonesia, tiếng Việt, tiếng Hindi và tiếng Anh dùng [FLEURS](https://huggingface.co/datasets/google/fleurs) (Google, CC-BY 4.0), Trung-Anh xen kẽ dùng [ASCEND](https://huggingface.co/datasets/CAiRE/ASCEND) (CAiRE, CC-BY-SA 4.0); không dùng bản ghi âm nào của công ty. Mã nguồn là `group/bench_asr.py`; chạy lại trên GitHub tại Actions → "語音辨識模型比較" → Run workflow (chọn được ngôn ngữ, số câu và mô hình; tất cả mô hình với 50 câu mất khoảng 3 giờ 40 phút). Kết quả lần này: [nhật ký chạy](https://github.com/fairy715/PCG-live-whisper/actions/runs/44498791993).

#### Theo cấu hình máy (laptop mới)

Trước hết xem máy có card NVIDIA không (Task Manager → "Performance" → GPU):

| Máy | Mô hình nhận dạng cục bộ (tiếng Trung, hai chiều, lớp học) | Phụ đề trực tiếp tiếng nước ngoài | Bản ghi âm |
|---|---|---|---|
| **Có card NVIDIA** (RTX 4050/4060/5050/5060, v.v.) | Cài gói GPU, rồi cài và chọn Whisper medium hoặc large-v3-turbo (đa ngôn ngữ) | medium cho từng ngôn ngữ | medium cho từng ngôn ngữ; tiếng Trung dùng large-v3-turbo |
| **Laptop mới 2025–2026** (Core Ultra, Ryzen AI; RAM 16 GB, từ 8 nhân) | small có sẵn; thử Whisper medium (đa ngôn ngữ), phụ đề chậm thì quay lại small | small cho từng ngôn ngữ (thử medium) | medium cho từng ngôn ngữ |
| **Laptop thường hoặc cũ** (RAM 8 GB, 4 nhân) | small có sẵn; nếu chậm, dùng Whisper base (đa ngôn ngữ) | small cho từng ngôn ngữ | medium cho từng ngôn ngữ (lâu hơn) |

- "Chip AI (NPU)" quảng cáo trên laptop mới hiện không được dùng: nhận dạng giọng nói chỉ dùng CPU hoặc card NVIDIA
- Nên có RAM từ 16 GB: mở Teams, trình duyệt và mô hình medium cùng lúc thì 8 GB sẽ chật

#### Các bước cài đặt (một lần trên mỗi máy cần dùng)

1. Cập nhật máy đó lên **r15 trở lên** (phiên bản ở cuối trang; nếu cũ hơn, bấm "Kiểm tra cập nhật")
2. Trên máy đó mở `http://localhost:19781/simple/admin`, chọn **English** ở góc trên bên phải và nhập mật khẩu IT (chỉ cài được trên chính máy đó)
3. Kéo xuống "**Models (model packs)**" → "Available", bấm "Install" cho các gói cần dùng và chờ thanh tiến trình chạy xong (một gói small khoảng 1–3 phút, tùy mạng)
4. Ở "**Model for each language**", chọn "Live subtitles" và "Recordings" theo bảng trên, rồi bấm "**Apply model settings**"
5. Mở thử một phiên phụ đề trực tiếp "người kia nói …": chữ hiện bình thường là xong
6. Không cần nữa: bấm "Remove" ở "Installed on this computer"; ngôn ngữ đang dùng gói đó tự trở về mô hình có sẵn

Nhiều máy: IT đặt trước `catalog.json` và các tệp `*.zip` cần dùng từ [trang phát hành](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs) vào thư mục dùng chung của công ty (thư mục đã nhập ở "Updates"); từng máy sao chép qua mạng nội bộ, nhanh hơn tải từ GitHub mỗi lần.

#### Chi tiết

- **Nguồn**: [trang phát hành model-packs](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs) trên GitHub; máy không có internet: IT đặt `catalog.json` và các tệp gói từ trang đó vào thư mục dùng chung đã nhập ở "Updates" (hoặc thư mục con `models` của nó)
- **Cài đặt**: chỉ trên chính máy đó (cần mật khẩu IT); SHA-256 của từng tệp được so, không khớp thì không cài; gói được đặt vào `models\packs\<mã>`
- **Chỉ định**: ở "Model for each language", chọn mô hình cho phụ đề trực tiếp và bản ghi âm, bấm "Apply model settings"; có hiệu lực khi phụ đề hoặc bản ghi âm tiếp theo bắt đầu
  - Chỉ dùng cho phụ đề trực tiếp và bản ghi âm **một chiều** bằng ngôn ngữ đó ("người kia nói …"); hai chiều (phía micro là tiếng Trung) và chế độ lớp học vẫn dùng mô hình đa ngôn ngữ có sẵn
  - Khi chọn MADLAD-400 cho dịch cục bộ, mọi bản dịch ở chế độ cục bộ đều dùng nó (vài giây mỗi câu; phụ đề trực tiếp trên máy cũ sẽ bị chậm, nên thử với bản ghi âm trước)
- **Gỡ bỏ**: ngôn ngữ đang dùng gói đó tự trở về mô hình có sẵn
- Cách đóng gói: `.github/workflows/model-packs.yml` (tải từ Hugging Face, chuyển sang CTranslate2 int8, chỉ nhận giấy phép cho phép dùng thương mại, nhận dạng/dịch thử, cài thử một lần rồi mới phát hành)

### Phụ đề trực tiếp tiếng Anh (Moonshine)

- Khi "người kia nói tiếng Anh" được nhận dạng trên máy nhân viên, dùng **Moonshine medium** (chỉ tiếng Anh, giấy phép MIT, khoảng 250 MB, có sẵn trong bộ cài ngoại tuyến): độ trễ khoảng 0,3 giây, nhẹ CPU hơn Whisper nhiều
- Hai chiều ("Tôi cũng nói"), chế độ lớp học và các ngôn ngữ khác vẫn dùng Whisper (Moonshine chỉ hiểu tiếng Anh)
- Khi có máy chủ GPU (nhận dạng trên máy chủ) thì vẫn dùng Whisper trên máy chủ
- Quay lại Whisper: thêm `"english_asr": "whisper"` dưới `pcg_simple` trong `config.json`
- Các mô hình Moonshine cho ngôn ngữ khác tiếng Anh có giấy phép phi thương mại và phiên bản tập đoàn không dùng

### Gói tăng tốc GPU NVIDIA (máy nhân viên có card NVIDIA)

- Trang phát hành còn có "Gói tăng tốc GPU NVIDIA" (tag `gpu-cuda12-v…`, khoảng 670 MB): CUDA 12 cuBLAS, cuDNN 9, NVRTC
- Chỉ dùng cho card NVIDIA (GeForce, RTX, MX); không hỗ trợ đồ họa Intel và AMD
- Cần PCG Meeting Translator r13 trở lên và driver NVIDIA hỗ trợ CUDA 12 (khoảng năm 2023 trở về sau)
- Cài vào `gpu\cuda12` trong thư mục PCG Meeting Translator; cài lại ứng dụng hay gói cập nhật nhỏ đều không xóa; chỉ cần cài một lần
- Cài xong tự kiểm tra và hiện kết quả (cài im lặng thì không hiện; xem `group_data\gpu_check.log`); nếu không dùng được card, ứng dụng vẫn dùng CPU
- Kiểm tra thủ công: chạy `python\python.exe gpu\gpu_check.py` trong thư mục cài đặt
- Định dạng tính toán chọn tự động: dòng GTX 10 / MX (compute capability 6.x) dùng int8, từ dòng RTX 20 trở lên dùng float16
- Bản dựng trên đám mây không có card đồ họa để thử: hãy thử trên máy có card NVIDIA trước khi triển khai rộng

### Máy phụ đề phòng họp (một máy có card đồ họa, mọi người kết nối vào)

Bộ cài chính chỉ có mô hình small: chạy được trên laptop thường, nhưng tiếng Indonesia và tiếng Việt nhận dạng sai nhiều hơn. Muốn phụ đề chính xác hơn, hãy dùng **một máy có card đồ họa NVIDIA làm "máy phụ đề"**: máy này thu âm, nhận dạng và dịch, mọi người khác xem phụ đề trên trình duyệt của điện thoại hoặc laptop. Máy của nhân viên không cần thay đổi. (Trang cài đặt IT hiển thị bằng tiếng Anh; tên nút được ghi bằng tiếng Anh.)

**Khuyến nghị**: card đồ họa NVIDIA có ít nhất 4 GB bộ nhớ video (ví dụ RTX 3050 trở lên). Card 2 GB như MX330 có thể quá chậm; hãy thử trước.

**Tự động gợi ý** (r25): khi nhân viên mở trang, chương trình hỏi `nvidia-smi` xem máy này có card đồ họa NVIDIA không. Nếu có, bộ nhớ video từ 4 GB trở lên và chưa cài gói, một cửa sổ sẽ gợi ý cài đặt: "Tải gói" (bộ cài trên trang phát hành GitHub, khoảng 706 MB), "Để sau" (nhắc lại sau 7 ngày) hoặc "Không nhắc lại". Khi mục "ai được cập nhật" đặt là chỉ IT, cửa sổ chỉ đề nghị nhân viên liên hệ IT và không hiện nút tải. Card rời của AMD và Intel không dùng được gói này (chỉ hỗ trợ NVIDIA CUDA) nên không nhắc; máy chưa cài driver NVIDIA (không có `nvidia-smi`) cũng không phát hiện được. Với máy không có internet, IT cần mang bộ cài gói đến.

**Cài đặt (IT, một lần, trên máy phụ đề)**

1. Cài bộ cài đầy đủ, rồi cài gói tăng tốc GPU NVIDIA (sau khi cài sẽ tự kiểm tra card đồ họa).
2. Trang cài đặt IT → "**Models (model packs)**" → cài "Whisper large-v3-turbo (multilingual)".
3. Ở "**Local recognition models**", chọn large-v3-turbo cho "**Live subtitles**", rồi bấm "**Save**".
4. (Tùy chọn) Gói ngôn ngữ (medium) cho tiếng Indonesia, Việt, Hindi: chọn ở "**Model for each language**", rồi bấm "**Apply model settings**". Chỉ dùng cho "Chỉ đọc phụ đề".
5. Đánh dấu "**Allow other computers and phones to view subtitles**", đặt "**Staff password**", lưu, rồi bấm "**Restart the program now**" xuất hiện trên trang (khoảng 10 giây, từ r20; không cần kết thúc python.exe trong Task Manager). Nếu nhân viên bấm bắt đầu cảnh "máy phụ đề phòng họp" khi chương trình chưa khởi động lại, chương trình sẽ tự khởi động lại trước
   - Tác giả gốc đã thêm "Allow other computers to connect" trong "Security settings" của WebUI nâng cao (`/`) ở bản 2.34.1: khi mở bản dùng cho tập đoàn từ lối tắt trên màn hình, **tùy chọn ở trang cài đặt IT phía trên là tùy chọn quyết định**; không cần để ý ô đánh dấu trong WebUI nâng cao (r22)
6. Cho phép kết nối đến trong Windows Firewall (cần quyền quản trị: mở PowerShell bằng quyền quản trị):
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   Lệnh này chỉ cho phép mạng con nội bộ. Nếu mạng công ty có nhiều mạng con, thay `LocalSubnet` bằng dải thật (ví dụ `10.10.0.0/16`).
7. Đặt IP cố định cho máy phụ đề (hoặc giữ chỗ DHCP) để địa chỉ trong mã QR không đổi.

**Khi họp**

1. Máy phụ đề tham gia cuộc họp Teams (trực tuyến), hoặc dùng micro của phòng họp (họp tại chỗ: chọn "**Máy phụ đề phòng họp**", từ r19).
2. Chọn ngôn ngữ rồi bấm Bắt đầu: với lựa chọn phòng họp, mã QR hiện ngay (các lựa chọn khác thì bấm "Chia sẻ" trên màn hình phụ đề); chiếu mã QR lên.
3. Mọi người quét mã QR (hoặc mở `http://<IP máy phụ đề>:19781/simple/live`), nhập mật khẩu nhân viên và chọn ngôn ngữ hiển thị chữ lớn bằng menu ngôn ngữ ở góc trên bên phải. Điện thoại chỉ xem được, không dừng được phụ đề.

**Giới hạn**

- **Phụ đề đa ngôn ngữ (từ r19)**: người xem tự chọn ngôn ngữ ở góc trên bên phải (tiếng Trung, Indonesia, Việt, Hindi, Anh). Khi một câu không có ngôn ngữ đó, máy phụ đề dịch thêm một bản; ví dụ phiên "Tiếng Trung ⇄ Tiếng Indonesia", người chọn tiếng Việt sẽ thấy tiếng Việt. Nhận dạng giọng nói không tăng, chỉ thêm phần dịch: trên CPU của máy phụ đề ở chế độ cục bộ (card đồ họa nếu có gói GPU), hoặc trên máy chủ LLM ở chế độ máy chủ; ngôn ngữ không ai chọn thì không dịch. Máy yếu có thể bỏ chọn "**Multi-language subtitles**" trên trang IT. Lời nói tiếng Nhật, tiếng Hàn chỉ thêm được bản tiếng Trung.
- Chỉ máy tính và điện thoại trong cùng mạng nội bộ công ty mới kết nối được.
- Bảo mật: từ r18 chỉ chấp nhận kết nối bằng địa chỉ IP hoặc tên máy; hãy đặt mật khẩu nhân viên dài (hiện chưa khóa sau nhiều lần nhập sai).

### Giảng viên ở Đài Loan dạy bằng tiếng Trung, nhà máy nước ngoài xem phụ đề: Breeze cho tiếng Trung, âm thanh ở lại trong công ty

Các bước cho nhân viên nằm ở tình huống 8 trong tài liệu tình huống sử dụng. Một máy phụ đề tham gia lớp Teams và nhận dạng tiếng Trung của giảng viên bằng card đồ họa với **Breeze ASR 25** (MediaTek Research, huấn luyện cho tiếng Trung Đài Loan và tiếng Trung pha tiếng Anh); nhân viên ở nước ngoài kết nối bằng trình duyệt và tự chọn ngôn ngữ. Giọng nói chỉ nhận dạng một lần và chỉ được xử lý trên máy phụ đề.

**IT làm một lần trên máy phụ đề**

1. Làm theo các bước "máy phụ đề phòng họp" ở trên: bộ cài đầy đủ, gói GPU, "Allow other computers and phones to view subtitles", mật khẩu nhân viên. Breeze có kích thước large-v2: nên có bộ nhớ đồ họa từ 6 GB; card 4 GB cần thử thực tế.
2. Trong "Models (model packs)", cài "**Breeze ASR 25（台灣華語、中英夾雜）**" (khoảng 1,5 GB).
3. Chỉ định Breeze cho tiếng Trung:
   - **Từ r28**: ở mục "Model for each language", dòng "Chinese", chọn Breeze ASR 25 cho "Live subtitles" rồi bấm "Apply model settings".
   - **r25 và r26**: trang cài đặt không có dòng "Chinese". Cách duy nhất là trang nhân viên trên máy phụ đề: chọn "Mọi người đều nói tiếng Trung", tải lại trang, rồi bấm "Cài đặt" trong cửa sổ "Nên cài mô hình giọng nói chính xác hơn" (cài xong mô hình tự được chỉ định cho tiếng Trung). Sau đó **đừng bấm "Apply model settings"**, vì sẽ xóa chỉ định cho tiếng Trung. Nên cập nhật lên r28.
4. Tường lửa: quy tắc ở trên chỉ mở cùng mạng con. Với nhà máy nước ngoài, thay `-RemoteAddress` bằng các mạng con của họ (ví dụ `10.10.0.0/16,10.20.0.0/16`) và nhờ nhóm mạng xác nhận TCP 19781 từ từng nhà máy tới máy phụ đề thông suốt.
5. Nhập thuật ngữ của khóa học (công ty, nhà máy, hệ thống, tên người) vào bảng thuật ngữ.
6. Chất lượng bản dịch: chế độ cục bộ dùng M2M100, ở mức trung bình với tiếng Indonesia và tiếng Việt; muốn tốt hơn, chuyển máy phụ đề sang chế độ máy chủ và dịch bằng nền tảng AI của tập đoàn hoặc mô hình lớn nội bộ (nhận dạng vẫn chạy trên máy phụ đề).

**Chương trình thực tế hoạt động thế nào**

- Gói mô hình tiếng Trung được dùng cho phụ đề một chiều nghe tiếng Trung: nhân viên nói tiếng Trung chọn "Mọi người đều nói tiếng Trung", và nhân viên nói ngoại ngữ chọn "Tiếng Trung → ngôn ngữ của bạn". Chế độ lớp học (một micro, hai ngôn ngữ) và "Tôi cũng nói" dùng mô hình đa ngôn ngữ, không dùng Breeze.
- "Mọi người đều nói tiếng Trung" nghe nguồn nào là tùy loại cuộc họp (**từ r28**):
  - "Chỉ đọc phụ đề": **âm thanh máy tính phát ra** (máy phụ đề tham gia Teams và nghe giảng viên). Đừng tắt tiếng loa hoặc tai nghe.
  - "Cùng một phòng học" và "Máy phụ đề phòng họp": **micro** (giảng viên nói vào máy này hoặc micro của phòng). Dùng micro đã chọn trong "Âm thanh và micro", chưa chọn thì dùng micro mặc định của Windows; nếu hoàn toàn không có micro thì phiên không bắt đầu và trang báo không tìm thấy micro.
  - Cả hai đều dùng gói mô hình tiếng Trung (Breeze). Mỗi phiên chỉ nghe một nguồn; bắt đầu lại "Mọi người đều nói tiếng Trung" ở loại cuộc họp khác sẽ thay phiên đang chạy.
  - Đến r26 loại cuộc họp không ảnh hưởng: luôn nghe âm thanh máy tính phát ra (nên "Máy phụ đề phòng họp" với "Mọi người đều nói tiếng Trung" không nghe được micro của phòng).
- Một ngôn ngữ chỉ được dịch khi có người xem chọn nó. Chỉ có chữ phụ đề được gửi đi nên lưu lượng rất nhỏ.
- Khi bật "Speech recognition API", âm thanh được gửi cho API trước và Breeze chỉ là dự phòng. Muốn âm thanh ở lại trong công ty, đừng bật API bên ngoài.

**Chưa thử trên máy thật**: độ trễ của Breeze với phụ đề trực tiếp (tùy card đồ họa), việc thu micro cho "Mọi người đều nói tiếng Trung" (đám mây không có thiết bị âm thanh nên mới chỉ kiểm tra việc chuyển số hiệu micro cho chương trình chính), truy cập giữa các nhà máy, và nhiều người xem cùng lúc. Ngày 2026-11-18 mới chỉ xác nhận trên đám mây việc tải mô hình với một câu tiếng Trung và cách hoạt động nêu trên (kiểm thử tự động). Hãy thử trước với một buổi học.

### Thay đổi ở trang cài đặt IT (r29)

- **“Where data goes” ở đầu trang**: dựa trên các giá trị đang hiện trên trang, luôn cho biết “Audio” và “Text” được gửi đi đâu (chỉ máy này, máy chủ GPU của công ty, dịch vụ nội bộ, nền tảng AI của tập đoàn, hoặc ra ngoài công ty). Chỉ cần một mục ra khỏi công ty là cả thanh chuyển màu cam. Thanh này cũng theo các thay đổi chưa lưu, nên có thể kiểm tra trước khi lưu.
- **Nơi nhận dữ liệu của LLM nay dựa theo địa chỉ**: nếu loại máy chủ là “Internal server” nhưng địa chỉ là tên miền hoặc IP công cộng bên ngoài công ty, trang nhân viên sẽ hiện “dịch vụ AI bên ngoài công ty” (đến r28 chỉ xét loại máy chủ nên địa chỉ bên ngoài vẫn hiện là nội bộ). Khi máy chủ nội bộ dùng tên miền (không phải địa chỉ 10.x, 192.168.x và không phải tên máy không có dấu chấm), dưới ô địa chỉ sẽ có ô “This is a server inside the company”; hãy đánh dấu sau khi xác nhận. **Sau khi nâng cấp, hãy mở trang cài đặt một lần và xem thanh trên cùng**: máy chủ nội bộ dùng tên miền sẽ bị coi là bên ngoài cho đến khi đánh dấu ô đó.
- **Các mục ít thay đổi được thu gọn sẵn**: bảng thuật ngữ, cập nhật, báo lỗi, mô hình. Giá trị hiện tại hiện ở bên phải tiêu đề (số thuật ngữ, có tự kiểm tra hay không, người nhận, số gói mô hình); bấm tiêu đề để mở.
- **Thanh lưu luôn ở cuối cửa sổ**: hiện “Unsaved changes” và kết quả lưu. “Apply model settings” vẫn là nút riêng trong mục Models.
- **Chế độ cục bộ ẩn phần cài đặt máy chủ.**
- **Bật xem từ xa mà chưa đặt mật khẩu nhân viên**: có cảnh báo màu cam dưới ô đánh dấu.
- Tiêu đề trang trước đây ghi thay đổi có hiệu lực ngay; thực tế là từ lần phụ đề hoặc bản ghi tiếp theo. Câu chữ đã được sửa.
- **Hai nút kiểm tra** (r30): “Test the LLM connection” và “Test the GPU server”, kết quả hiện ngay dưới từng nút. Sau khi kiểm tra LLM thành công, trang sẽ xem tên trong “Translation model” và “Minutes (summary) model” có trong danh sách của máy chủ hay không và cảnh báo nếu không có (gõ sai tên mô hình là nguyên nhân phổ biến nhất khiến phụ đề không được dịch).
- **Đổi mật khẩu IT** (r30): cửa sổ ngay trên trang, không hiện ký tự, nhập hai lần; ít nhất 6 ký tự.
- **Máy không có internet** (r30): mục Models hiện “This computer cannot reach GitHub right now, so only model packs in the company shared folder are listed”. Đây là bình thường, không phải lỗi.
- **Cảnh báo dữ liệu ra khỏi công ty** (r30) có vạch cam dày bên trái để phân biệt với thông báo thường.

### Biểu tượng dùng trong giao diện (r29)

- Biểu tượng loại cuộc họp là SVG một màu vẽ ngay trong trang, không còn dùng emoji (emoji trên Windows 10 và 11 trông khác nhau).
- Các trạng thái “đang nghe, đang chuẩn bị, đang xử lý, đang kết nối lại, đang kiểm tra” dùng biểu tượng động lấy từ [Ultra Lab Motion Icons](https://github.com/ppcvote/ultralab-anim-icons) v0.3.1 (giấy phép MIT). Chỉ 8 biểu tượng đang dùng được nhúng vào trang; không tải gì từ internet. Biểu tượng không chuyển động khi Windows tắt hiệu ứng động (Settings → Accessibility → Visual effects → Animation effects).

### Thông tin cuộc họp, từ nghe sai, gõ để trả lời (r32)

**Thông tin cuộc họp này**: chương trình họp, người tham dự, mã hàng mà nhân viên dán trước khi bắt đầu phụ đề (hoặc trước khi gửi bản ghi âm).

| | Bảng thuật ngữ (r23) | Thông tin cuộc họp này (r32) |
|---|---|---|
| Ai quản lý | IT, cả công ty dùng chung | Nhân viên tự dán, chỉ dùng cho cuộc họp này |
| Nội dung | Tên công ty, nhà máy, tên hệ thống | Người tham dự, sản phẩm, mã hàng, chương trình của cuộc họp này |
| Chỉ định cách dịch, cách viết nghe sai | Được | Không |

- **Lưu trữ**: trình duyệt của nhân viên (mở lại vẫn còn); khi bắt đầu phụ đề được ghi vào `group_data\meeting-notes.txt` (văn bản thuần, bị xóa khi phiên sau không điền). Tối đa 4.000 ký tự. Tệp chẩn đoán không chứa tệp này, danh sách công việc cũng không hiển thị nội dung.
- **Nhận dạng**: các từ ngắn (mỗi từ tối đa 40 ký tự, nhiều nhất 40 từ, tổng 200 ký tự) làm từ gợi ý, đặt trước các từ của bảng thuật ngữ (gợi ý có giới hạn độ dài, khoảng 220 token). Dòng có dấu chấm hoặc dài hơn 80 ký tự được coi là câu và không làm từ gợi ý.
- **Dịch (chế độ máy chủ)**: 1.200 ký tự đầu được đặt ở đầu mỗi prompt dịch, ghi rõ chỉ để tham khảo. Câu nào cũng mang thêm đoạn này: LLM cục bộ (Ollama, vLLM) chậm hơn một chút, dịch vụ AI bên ngoài tính thêm lượng đầu vào. M2M100 ở chế độ cục bộ không dùng được.
- **Dữ liệu đi đâu**: đi theo phần dịch và phần nhận dạng giọng nói. Khi bật API nhận dạng giọng nói, từ gợi ý được gửi tới API đó cùng mỗi đoạn âm thanh; khi LLM ở ngoài công ty, phần bối cảnh được gửi ra ngoài công ty. Trong hai trường hợp này trang nhân viên hiện nhắc nhở màu cam dưới ô nhập.
- Khi không ai nói, Whisper đôi khi chép lại gợi ý: kết quả nằm trọn trong các từ gợi ý và trải qua từ hai từ trở lên sẽ bị bỏ.

**Từ nghe sai** (chế độ máy chủ): văn bản phụ đề đến từ nhận dạng giọng nói nên có từ đồng âm và từ nghe sai. Trước đây prompt dịch yêu cầu LLM "dịch từng chữ ngay cả khi nghĩa không rõ", nên nghe sai thì dịch sai theo. Từ r32 đổi thành: "khi một từ có vẻ bị nghe sai, hãy dịch theo nghĩa hợp lý nhất dựa vào ngữ cảnh; tên riêng không nhận ra thì giữ nguyên như nghe được; không bình luận". Phụ đề gốc không bị sửa, chỉ bản dịch thay đổi. Nếu thấy LLM đoán quá nhiều, đặt biến môi trường hệ thống Windows `PCG_TRANSLATE_GUESS=off` để quay về cách cũ (khởi động lại chương trình sau khi đặt).

**Gõ để trả lời**: ở cuối màn hình phụ đề, nhân viên gõ bằng ngôn ngữ của mình và ngôn ngữ của người kia hiện bằng chữ lớn.

- Chương trình đang chạy phụ đề sẽ dịch: cùng một M2M100 ở chế độ cục bộ (không tốn thêm bộ nhớ), cùng một LLM ở chế độ máy chủ. Dữ liệu đi đến cùng nơi với phần dịch phụ đề.
- Chỉ dùng được trên máy đang thu âm (`/api/simple/say` từ chối máy khác); kết quả chỉ trả về trang đã gõ, không gửi cho người xem bằng điện thoại.
- Mỗi lần một câu, tối đa 300 ký tự; quá 30 giây không có kết quả sẽ báo thất bại. Ở chế độ cục bộ, lần đầu dùng một chiều dịch sẽ chậm hơn vài giây.
- "Mọi người đều nói tiếng Trung" chỉ nhận dạng, không dịch, nên không có chức năng này.

**Đã kiểm chứng đến đâu** (2026-11-22): kiểm thử đơn vị; WebUI thật với bộ máy thay thế được thao tác thực tế trong trình duyệt (giao diện tiếng Trung, tiếng Indonesia và tiếng Việt, kể cả chiều rộng điện thoại); phần tự kiểm tra trên Windows trước mỗi lần phát hành thật sự nhận dạng bằng mô hình small kèm từ gợi ý và thật sự dịch câu đã gõ bằng M2M100, không đạt thì không phát hành. **Chưa kiểm chứng trong cuộc họp thực tế**: từ gợi ý giúp được bao nhiêu với giọng người thật, và quy tắc "từ nghe sai" hoạt động thế nào trên từng LLM. Hãy thử trong cuộc họp của chính bạn.

Cách làm tham khảo phần bối cảnh bài nói, prompt phụ đề và cửa sổ trả lời của [OwnVoice Meet](https://github.com/Zaious/ownvoice-meet) (Apache-2.0); mã được viết lại cho bản tập đoàn, không sao chép mã nguồn.

## ③ Máy nhân viên cần phụ đề trực tiếp

### Windows

1. Tải phiên bản tập đoàn vào `C:\jt-live-whisper`:
   - Có Git: `git clone https://github.com/fairy715/PCG-live-whisper.git C:\jt-live-whisper`
   - Không có Git: trên trang GitHub bấm Code → Download ZIP, giải nén, rồi đặt **các tệp bên trong** vào `C:\jt-live-whisper`
2. Mở PowerShell bằng quyền quản trị:
   ```powershell
   cd C:\jt-live-whisper
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   Khi được hỏi máy chủ GPU ở cuối, nhập địa chỉ ② (nhận dạng do máy GPU đảm nhận, máy cá nhân không cần card đồ họa tốt)
3. Đặt máy chủ LLM: nhập địa chỉ Ollama của ② khi mở WebUI lần đầu (sẽ được ghi nhớ)
4. Lối tắt trên màn hình tạo theo cách này mở WebUI đầy đủ; hãy tạo dấu trang cho nhân viên: **`http://localhost:19781/simple`** (bộ cài ngoại tuyến không gặp vấn đề này: lối tắt "PCG Meeting Translator" mở thẳng trang đơn giản)

### Mac

```bash
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper
bash install.sh
```

Lần đầu sử dụng, cấp quyền "Screen & System Audio Recording" cho Terminal (sẽ có nhắc), sau đó thoát hẳn Terminal rồi mở lại.

## Cập nhật

```bash
cd ~/Apps/jt-live-whisper        # Windows: cd C:\jt-live-whisper
git pull
./install.sh                     # Windows: .\install.ps1 (bổ sung gói mà phiên bản mới cần)
sudo systemctl restart jt-live-whisper-webui    # chỉ trên ①
```

Khi tác giả gốc phát hành phiên bản mới (ứng dụng hiện "có phiên bản mới" khi khởi động), hãy gộp vào phiên bản tập đoàn trước rồi mới cập nhật; không dùng trực tiếp `--upgrade`. GitHub tự kiểm tra cập nhật của dự án gốc mỗi thứ Hai và mở issue khi có nội dung mới.

## Vận hành

| Mục | Vị trí / lệnh |
|---|---|
| Trạng thái dịch vụ, nhật ký lỗi | `systemctl status jt-live-whisper-webui`, `journalctl -u jt-live-whisper-webui` |
| Danh sách công việc của trang đơn giản | `group_data/jobs.json` |
| Nhật ký đầy đủ của một công việc | `group_data/job_<mã công việc>.log` (nhân viên thấy mã công việc trên màn hình) |
| Bản ghi âm nhân viên tải lên | `recordings/simple/` |
| Biên bản và bản chép lời | `logs/` |
| Kiểm tra tình trạng | `./install.sh --doctor` |

**Bản ghi âm và kết quả không bao giờ tự xóa**: bản ghi âm cuộc họp là dữ liệu nhạy cảm; hãy dọn định kỳ theo quy định lưu trữ dữ liệu của công ty (ví dụ giữ 90 ngày).

### Báo lỗi (từ r16)

* **Nhân viên**: “Báo lỗi” ở cuối trang → mô tả chuyện gì đã xảy ra → “Tạo báo cáo”. Trình duyệt tải về `PCG-report-<tên máy>-<ngày giờ>.zip`, nhân viên gửi tệp đó cho IT. Chỉ tạo được trên chính máy đó (nhật ký là của máy đó).
* **IT**: trên trang cài đặt, mục "**Problem reports**" (trang cài đặt IT hiển thị bằng tiếng Anh) cho phép điền nơi nhân viên gửi báo cáo (email hoặc nhóm Teams); thông tin này hiện cho nhân viên. Nếu là email, sẽ có thêm nút “Gửi email cho IT” (đã điền sẵn tiêu đề và mô tả; nhân viên tự đính kèm tệp zip). Nút "**Create a diagnostic file for this computer**" trên cùng thẻ tạo tệp cho IT; khi bật "Allow other computers and phones to view subtitles", IT cũng có thể lấy từ máy của mình bằng mật khẩu IT.
* **Trong tệp zip**: `summary.txt` (phiên bản, cấu hình máy, bộ nhớ, ổ đĩa, gói GPU, gói mô hình, trình duyệt, mô tả của nhân viên), `report.json` (cùng dữ liệu, thêm trạng thái và lỗi của 20 tác vụ ghi âm gần nhất và tham số phụ đề trực tiếp), `config.json` (cài đặt, **khóa, mật khẩu và mã băm được thay bằng `***`**), `logs/` (400 dòng cuối của `webui.log`, `webui-error.log`, `update.log`, `install.log`, `gpu_check.log`, và nhật ký của 3 tác vụ gần nhất, ưu tiên tác vụ lỗi).
* **Không có trong tệp zip**: bản ghi âm, bản ghi lời, biên bản, tên tệp ghi âm và chủ đề cuộc họp. Nhật ký chương trình có thể có một phần nội dung phụ đề; nhân viên có thể bỏ chọn “Kèm nhật ký chương trình gần đây”.
* Mỗi máy chỉ giữ 10 tệp chẩn đoán gần nhất (`group_data\reports\`).
* Tệp chẩn đoán có thể chứa một phần cuộc họp: **không đăng lên issue GitHub công khai**. Mẫu “Báo lỗi” trên GitHub chỉ hỏi phiên bản, hiện tượng và các bước.
