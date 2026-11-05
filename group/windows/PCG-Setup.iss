; PCG 集團版：Windows 安裝程式（Inno Setup 6）
; 產生：GitHub Actions（.github/workflows/windows-installer.yml）；本機：ISCC.exe /DAppVersion=1.0.0 group\windows\PCG-Setup.iss
; 安裝時需要旁邊有離線資源包 PCG-offline（group/windows/build_bundle.py 產生），全程不連網、不需要系統管理員
; 三種產出：
;   /DEmbedBundle=資源包路徑 → 單一完整安裝檔（約 1.8 GB）
;   /DPatchOnly /DReqSha=… /DBundleSha=… → 小更新包（約 10 MB，只換程式；執行環境與模型沿用已安裝的）
;   都不帶 → Setup.exe（旁邊要放 PCG-offline 資料夾）
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef ReqSha
  #define ReqSha ""
#endif
#ifndef BundleSha
  #define BundleSha ""
#endif
#define LangDir "lang"

[Setup]
AppId=PCG-live-whisper
AppName=PCG Meeting Translator
AppVersion={#AppVersion}
AppVerName=PCG Meeting Translator {#AppVersion}
AppPublisher=PCG
DefaultDirName={code:GetDefaultDir}
DisableProgramGroupPage=yes
#ifdef PatchOnly
; 小更新包：裝到原本的位置，不讓使用者改
DisableDirPage=yes
UsePreviousAppDir=no
#endif
PrivilegesRequired=lowest
UsedUserAreasWarning=no
DirExistsWarning=no
OutputDir=..\..\dist
#ifdef PatchOnly
OutputBaseFilename=PCG-Update-{#AppVersion}
#elif defined(EmbedBundle)
; 單一安裝檔：離線資源包包在裡面（/DEmbedBundle=資源包路徑），同仁只要這一個檔案
OutputBaseFilename=PCG-Meeting-Translator-Setup-{#AppVersion}
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
#else
OutputBaseFilename=PCG-Setup-{#AppVersion}
#endif
SetupIconFile=..\..\icons\jt-live-whisper.ico
UninstallDisplayIcon={app}\icons\jt-live-whisper.ico
UninstallDisplayName=PCG Meeting Translator
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
#ifexist LangDir + "\ChineseTraditional.isl"
Name: "zh"; MessagesFile: "{#LangDir}\ChineseTraditional.isl"
#endif
Name: "en"; MessagesFile: "compiler:Default.isl"
#ifexist LangDir + "\Indonesian.isl"
Name: "id"; MessagesFile: "{#LangDir}\Indonesian.isl"
#endif
#ifexist LangDir + "\Vietnamese.isl"
Name: "vi"; MessagesFile: "{#LangDir}\Vietnamese.isl"
#endif
#ifexist LangDir + "\Hindi.isl"
Name: "hi"; MessagesFile: "{#LangDir}\Hindi.isl"
#endif

[CustomMessages]
en.ShortcutName=PCG Meeting Translator
en.Installing=Installing the runtime and models (about 3-10 minutes). Please wait...
en.InstallFailed=Setting up the runtime failed. Please send this file to IT:%n%1
en.BundleMissing=The offline package was not found:%n%1%n%nPut the PCG-offline folder next to this Setup file and run it again.
en.LaunchNow=Open PCG Meeting Translator now
en.NotInstalled=PCG Meeting Translator is not installed on this computer.%n%nThis small update only works on a computer that already has it. Use the full installer (PCG-Meeting-Translator-Setup-….exe).
en.NeedFull=This update needs new components that are only in the full installer.%n%nPlease use PCG-Meeting-Translator-Setup-{#AppVersion}.exe instead. Your settings and recordings are kept.
en.Updating=Updating and checking the program. Please wait...
en.UpdateFailed=The update was installed but the self-check failed. Please send this file to IT:%n%1
#ifexist LangDir + "\ChineseTraditional.isl"
zh.ShortcutName=PCG 會議翻譯
zh.Installing=正在安裝執行環境與模型（約 3～10 分鐘），請稍候…
zh.InstallFailed=執行環境安裝失敗。請把這個檔案交給 IT：%n%1
zh.BundleMissing=找不到離線資源包：%n%1%n%n請把 PCG-offline 資料夾放在這個安裝程式旁邊，再執行一次。
zh.LaunchNow=立即開啟 PCG 會議翻譯
zh.NotInstalled=這台電腦還沒有安裝 PCG 會議翻譯。%n%n小更新包只能更新已經裝好的電腦，請改用完整安裝檔（PCG-Meeting-Translator-Setup-….exe）。
zh.NeedFull=這次更新包含新的套件或模型，只有完整安裝檔才有。%n%n請改用 PCG-Meeting-Translator-Setup-{#AppVersion}.exe，設定與錄音都會保留。
zh.Updating=正在更新並檢查程式，請稍候…
zh.UpdateFailed=已更新，但自我檢查沒有通過。請把這個檔案交給 IT：%n%1
#endif
#ifexist LangDir + "\Indonesian.isl"
id.ShortcutName=Penerjemah Rapat PCG
id.Installing=Memasang runtime dan model (sekitar 3-10 menit). Mohon tunggu...
id.InstallFailed=Pemasangan runtime gagal. Kirim file ini ke IT:%n%1
id.BundleMissing=Paket offline tidak ditemukan:%n%1%n%nLetakkan folder PCG-offline di samping file Setup ini, lalu jalankan lagi.
id.LaunchNow=Buka Penerjemah Rapat PCG sekarang
id.NotInstalled=Penerjemah Rapat PCG belum terpasang di komputer ini.%n%nPembaruan kecil ini hanya untuk komputer yang sudah memasangnya. Gunakan penginstal lengkap (PCG-Meeting-Translator-Setup-….exe).
id.NeedFull=Pembaruan ini memerlukan komponen baru yang hanya ada di penginstal lengkap.%n%nGunakan PCG-Meeting-Translator-Setup-{#AppVersion}.exe. Pengaturan dan rekaman tetap disimpan.
id.Updating=Memperbarui dan memeriksa program. Mohon tunggu...
id.UpdateFailed=Pembaruan terpasang, tetapi pemeriksaan mandiri gagal. Kirim file ini ke IT:%n%1
#endif
#ifexist LangDir + "\Vietnamese.isl"
vi.ShortcutName=Phiên dịch cuộc họp PCG
vi.Installing=Đang cài đặt môi trường chạy và mô hình (khoảng 3-10 phút). Vui lòng chờ...
vi.InstallFailed=Cài đặt môi trường chạy thất bại. Hãy gửi tệp này cho IT:%n%1
vi.BundleMissing=Không tìm thấy gói cài đặt ngoại tuyến:%n%1%n%nHãy đặt thư mục PCG-offline cạnh tệp Setup này rồi chạy lại.
vi.LaunchNow=Mở Phiên dịch cuộc họp PCG ngay
vi.NotInstalled=Máy tính này chưa cài Phiên dịch cuộc họp PCG.%n%nGói cập nhật nhỏ chỉ dùng cho máy đã cài. Hãy dùng bộ cài đầy đủ (PCG-Meeting-Translator-Setup-….exe).
vi.NeedFull=Bản cập nhật này cần thành phần mới, chỉ có trong bộ cài đầy đủ.%n%nHãy dùng PCG-Meeting-Translator-Setup-{#AppVersion}.exe. Cài đặt và bản ghi âm vẫn được giữ.
vi.Updating=Đang cập nhật và kiểm tra chương trình. Vui lòng chờ...
vi.UpdateFailed=Đã cập nhật nhưng tự kiểm tra không đạt. Hãy gửi tệp này cho IT:%n%1
#endif
#ifexist LangDir + "\Hindi.isl"
hi.ShortcutName=PCG मीटिंग अनुवादक
hi.Installing=रनटाइम और मॉडल इंस्टॉल हो रहे हैं (लगभग 3-10 मिनट)। कृपया प्रतीक्षा करें...
hi.InstallFailed=रनटाइम इंस्टॉल नहीं हो सका। यह फ़ाइल IT को भेजें:%n%1
hi.BundleMissing=ऑफ़लाइन पैकेज नहीं मिला:%n%1%n%nPCG-offline फ़ोल्डर को इस Setup फ़ाइल के पास रखें और फिर से चलाएँ।
hi.LaunchNow=PCG मीटिंग अनुवादक अभी खोलें
hi.NotInstalled=इस कंप्यूटर पर PCG मीटिंग अनुवादक इंस्टॉल नहीं है।%n%nयह छोटा अपडेट केवल पहले से इंस्टॉल कंप्यूटर के लिए है। पूरा इंस्टॉलर (PCG-Meeting-Translator-Setup-….exe) उपयोग करें।
hi.NeedFull=इस अपडेट के लिए नए घटक चाहिए जो केवल पूरे इंस्टॉलर में हैं।%n%nकृपया PCG-Meeting-Translator-Setup-{#AppVersion}.exe उपयोग करें। सेटिंग्स और रिकॉर्डिंग सुरक्षित रहेंगी।
hi.Updating=प्रोग्राम अपडेट और जाँच हो रही है। कृपया प्रतीक्षा करें...
hi.UpdateFailed=अपडेट इंस्टॉल हो गया, लेकिन स्व-जाँच विफल रही। यह फ़ाइल IT को भेजें:%n%1
#endif

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "\.git\*,\.github\*,\dist\*,\group\tests\*,\group\windows\lang\*,\docs\*,\images\*,\logs\*,\recordings\*,\venv\*,\python\*,\hf_cache\*,\models\*,\tools\*,\group_data\*,\PCG-offline\*,\config.json,*.pyc,__pycache__"

#if defined(EmbedBundle) && !defined(PatchOnly)
Source: "{#EmbedBundle}\*"; DestDir: "{tmp}\PCG-offline"; Flags: recursesubdirs createallsubdirs ignoreversion deleteafterinstall
#endif

[Icons]
Name: "{autodesktop}\{cm:ShortcutName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\group\windows\launch.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\icons\jt-live-whisper.ico"
Name: "{autoprograms}\{cm:ShortcutName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\group\windows\launch.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\icons\jt-live-whisper.ico"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\group\windows\launch.vbs"""; Description: "{cm:LaunchNow}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Get-Process python -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '{app}\python\*' } | Stop-Process -Force"""; Flags: runhidden; RunOnceId: "StopPCG"

[UninstallDelete]
; 執行環境與模型一起移除；同仁的錄音（recordings）、逐字稿（logs）、設定（config.json）保留
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\hf_cache"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\group\__pycache__"
Type: filesandordirs; Name: "{app}\jtlw_api\__pycache__"
Type: filesandordirs; Name: "{app}\jtdt_meeting\__pycache__"
Type: filesandordirs; Name: "{app}\jtlw_tts\__pycache__"

[Code]
var
  BundleDir: String;
  PrevDir: String;

function WantRelaunch(): Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

{ 已安裝的位置：PrivilegesRequired=lowest 寫在 HKCU；以系統管理員執行過的會在 HKLM }
function FindPrevDir(): String;
var
  Key: String;
begin
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PCG-live-whisper_is1';
  Result := '';
  if not RegQueryStringValue(HKCU, Key, 'Inno Setup: App Path', Result) then
    if not RegQueryStringValue(HKLM64, Key, 'Inno Setup: App Path', Result) then
      RegQueryStringValue(HKLM32, Key, 'Inno Setup: App Path', Result);
end;

{ 檔案的 SHA-256（小寫）；不存在回空字串（GetSHA256OfFile 遇到不存在的檔案會丟例外） }
function FileSha(Path: String): String;
begin
  Result := '';
  if FileExists(Path) then
    Result := Lowercase(GetSHA256OfFile(Path));
end;

function GetDefaultDir(Param: String): String;
begin
#ifdef PatchOnly
  Result := PrevDir;
  exit;
#endif
  { 有 D 槽就裝 D 槽，沒有就裝系統磁碟（不放使用者資料夾：中文使用者名稱會讓部分套件出錯） }
  if DirExists('D:\') then
    Result := 'D:\PCG-live-whisper'
  else
    Result := ExpandConstant('{sd}') + '\PCG-live-whisper';
end;

function InitializeSetup(): Boolean;
begin
#ifdef PatchOnly
  { 小更新包：只有在「已安裝、而且執行環境跟這一版要的一樣」時才裝。
    比對已安裝的套件清單與資源包腳本（完整安裝時跟著程式一起放進去的）；不一樣就是這次有新套件或模型，要用完整安裝檔 }
  PrevDir := FindPrevDir();
  if (PrevDir = '') or (not FileExists(AddBackslash(PrevDir) + 'python\python.exe')) then
  begin
    SuppressibleMsgBox(CustomMessage('NotInstalled'), mbCriticalError, MB_OK, IDOK);
    Result := False;
    exit;
  end;
  if (FileSha(AddBackslash(PrevDir) + 'group\windows\requirements-cpu.txt') <> Lowercase('{#ReqSha}')) or
     (FileSha(AddBackslash(PrevDir) + 'group\windows\build_bundle.py') <> Lowercase('{#BundleSha}')) then
  begin
    SuppressibleMsgBox(CustomMessage('NeedFull'), mbCriticalError, MB_OK, IDOK);
    Result := False;
    exit;
  end;
  Result := True;
  exit;
#endif
  BundleDir := ExpandConstant('{param:BUNDLE|}');
#ifdef EmbedBundle
  { 單一安裝檔：資源包在安裝檔裡面，安裝時解到暫存資料夾（CurStepChanged 再決定路徑） }
  Result := True;
  exit;
#endif
  if BundleDir = '' then
    BundleDir := ExpandConstant('{src}\PCG-offline');
  Result := FileExists(AddBackslash(BundleDir) + 'manifest.json');
  if not Result then
    SuppressibleMsgBox(FmtMessage(CustomMessage('BundleMissing'), [BundleDir]), mbCriticalError, MB_OK, IDOK);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  RC: Integer;
begin
  { 更新時先關掉還在跑的程式，否則檔案被佔用 }
  Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like ''' +
       ExpandConstant('{app}') + '\python\*'' } | Stop-Process -Force"', '', SW_HIDE, ewWaitUntilTerminated, RC);
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  RC: Integer;
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
#ifdef PatchOnly
    WizardForm.StatusLabel.Caption := CustomMessage('Updating');
    WizardForm.ProgressGauge.Style := npbstMarquee;
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\group\windows\pcg-update.ps1') +
              '" -AppDir "' + ExpandConstant('{app}') + '"';
    if (not Exec('powershell.exe', Params, '', SW_HIDE, ewWaitUntilTerminated, RC)) or (RC <> 0) then
      SuppressibleMsgBox(FmtMessage(CustomMessage('UpdateFailed'), [ExpandConstant('{app}\group_data\update.log')]),
                         mbCriticalError, MB_OK, IDOK);
    WizardForm.ProgressGauge.Style := npbstNormal;
    { 一鍵更新（/RELAUNCH=1）：自我檢查做完才在背景重新開啟程式，不開新的瀏覽器分頁（原本那一頁會自己重新整理）。
      不放在 [Run]：[Run] 會在這一步之前執行，程式會在自我檢查還沒做完時就開起來 }
    if WantRelaunch() then
      Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' +
           ExpandConstant('{app}\group\windows\launch.ps1') + '" -NoBrowser', '', SW_HIDE, ewNoWait, RC);
    exit;
#endif
    if BundleDir = '' then
      BundleDir := ExpandConstant('{tmp}\PCG-offline');
    WizardForm.StatusLabel.Caption := CustomMessage('Installing');
    WizardForm.ProgressGauge.Style := npbstMarquee;
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\group\windows\pcg-install.ps1') +
              '" -AppDir "' + ExpandConstant('{app}') + '" -Bundle "' + BundleDir + '"';
    if (not Exec('powershell.exe', Params, '', SW_HIDE, ewWaitUntilTerminated, RC)) or (RC <> 0) then
      SuppressibleMsgBox(FmtMessage(CustomMessage('InstallFailed'), [ExpandConstant('{app}\group_data\install.log')]),
                         mbCriticalError, MB_OK, IDOK);
    WizardForm.ProgressGauge.Style := npbstNormal;
  end;
end;
