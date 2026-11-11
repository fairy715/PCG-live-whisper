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
- Máy cũ vẫn nặng, phụ đề bị chậm: trước hết cài gói **Whisper base (đa ngôn ngữ)** ở "Models", rồi chọn nó làm "Local live subtitle model" (nhanh hơn nhưng sai nhiều hơn). **Ứng dụng không bao giờ tự tải mô hình** (bản cài ngoại tuyến không tải), nên trang cài đặt chỉ liệt kê các mô hình có trên máy này
- Điều chỉnh (biến môi trường hệ thống Windows, sau đó mở lại ứng dụng):
  - `PCG_CPU_THREADS=8`: tổng số luồng (ví dụ máy bàn mạnh muốn chạy hết tốc độ)
  - `PCG_NORMAL_PRIORITY=1`: trở về mức ưu tiên bình thường

### Quản lý mô hình (gói mô hình, từ r15)

Bộ cài chính chỉ có phần cơ bản (Whisper small, M2M100, Moonshine cho tiếng Anh); các mô hình khác là **gói mô hình**, cài ở "Models" trên trang cài đặt IT:

| Gói mô hình | Công dụng | Dung lượng | Giấy phép |
|---|---|---|---|
| PhoWhisper small / medium | Nhận dạng giọng nói tiếng Việt | khoảng 240 / 740 MB | BSD-3-Clause |
| Whisper small tiếng Indonesia (maleo-ai) | Nhận dạng giọng nói tiếng Indonesia | khoảng 240 MB | Apache-2.0 |
| Whisper medium tiếng Indonesia (cahya) | Nhận dạng giọng nói tiếng Indonesia | khoảng 740 MB | Apache-2.0 |
| Whisper small / medium tiếng Hindi (vasista22) | Nhận dạng giọng nói tiếng Hindi | khoảng 240 / 740 MB | Apache-2.0 |
| Whisper base / medium / large-v3-turbo (đa ngôn ngữ, OpenAI) | "Mô hình nhận dạng cục bộ" cho mọi ngôn ngữ (kể cả tiếng Trung), cũng dùng cho hai chiều và chế độ lớp học | khoảng 80 / 740 / 800 MB | Apache-2.0 (base, medium) / MIT (large-v3-turbo) |
| MADLAD-400 3B | Dịch cục bộ (chậm hơn; khi dịch thử có thêm nội dung không có trong câu gốc, hãy so sánh trước khi đổi) | khoảng 2,8 GB | Apache-2.0 |

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
- Hai chiều ("tôi cũng nói"), chế độ lớp học và các ngôn ngữ khác vẫn dùng Whisper (Moonshine chỉ hiểu tiếng Anh)
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

**Cài đặt (IT, một lần, trên máy phụ đề)**

1. Cài bộ cài đầy đủ, rồi cài gói tăng tốc GPU NVIDIA (sau khi cài sẽ tự kiểm tra card đồ họa).
2. Trang cài đặt IT → "**Models (model packs)**" → cài "Whisper large-v3-turbo (multilingual)".
3. Ở "**Local recognition models**", chọn large-v3-turbo cho "**Live subtitles**", rồi bấm "**Save**".
4. (Tùy chọn) Gói ngôn ngữ (medium) cho tiếng Indonesia, Việt, Hindi: chọn ở "**Model for each language**", rồi bấm "**Apply model settings**". Chỉ dùng cho "tôi chỉ đọc phụ đề".
5. Đánh dấu "**Allow other computers and phones to view subtitles**", đặt "**Staff password**", lưu, rồi bấm "**Restart the program now**" xuất hiện trên trang (khoảng 10 giây, từ r20; không cần kết thúc python.exe trong Task Manager). Nếu nhân viên bấm bắt đầu cảnh "máy phụ đề phòng họp" khi chương trình chưa khởi động lại, chương trình sẽ tự khởi động lại trước
6. Cho phép kết nối đến trong Windows Firewall (cần quyền quản trị: mở PowerShell bằng quyền quản trị):
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   Lệnh này chỉ cho phép mạng con nội bộ. Nếu mạng công ty có nhiều mạng con, thay `LocalSubnet` bằng dải thật (ví dụ `10.10.0.0/16`).
7. Đặt IP cố định cho máy phụ đề (hoặc giữ chỗ DHCP) để địa chỉ trong mã QR không đổi.

**Khi họp**

1. Máy phụ đề tham gia cuộc họp Teams (trực tuyến), hoặc dùng micro của phòng họp (họp tại chỗ: chọn "**Máy phụ đề phòng họp, mọi người xem trên điện thoại**", từ r19).
2. Chọn ngôn ngữ rồi bấm Bắt đầu: với lựa chọn phòng họp, mã QR hiện ngay (các lựa chọn khác thì bấm "Chia sẻ" trên màn hình phụ đề); chiếu mã QR lên.
3. Mọi người quét mã QR (hoặc mở `http://<IP máy phụ đề>:19781/simple/live`), nhập mật khẩu nhân viên và chọn ngôn ngữ hiển thị chữ lớn bằng menu ngôn ngữ ở góc trên bên phải. Điện thoại chỉ xem được, không dừng được phụ đề.

**Giới hạn**

- **Phụ đề đa ngôn ngữ (từ r19)**: người xem tự chọn ngôn ngữ ở góc trên bên phải (tiếng Trung, Indonesia, Việt, Hindi, Anh). Khi một câu không có ngôn ngữ đó, máy phụ đề dịch thêm một bản; ví dụ phiên "Tiếng Trung ⇄ Tiếng Indonesia", người chọn tiếng Việt sẽ thấy tiếng Việt. Nhận dạng giọng nói không tăng, chỉ thêm phần dịch: trên CPU của máy phụ đề ở chế độ cục bộ (card đồ họa nếu có gói GPU), hoặc trên máy chủ LLM ở chế độ máy chủ; ngôn ngữ không ai chọn thì không dịch. Máy yếu có thể bỏ chọn "**Multi-language subtitles**" trên trang IT. Lời nói tiếng Nhật, tiếng Hàn chỉ thêm được bản tiếng Trung.
- Chỉ máy tính và điện thoại trong cùng mạng nội bộ công ty mới kết nối được.
- Bảo mật: từ r18 chỉ chấp nhận kết nối bằng địa chỉ IP hoặc tên máy; hãy đặt mật khẩu nhân viên dài (hiện chưa khóa sau nhiều lần nhập sai).

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
