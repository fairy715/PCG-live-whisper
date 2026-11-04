; PCG 集團版：Windows 安裝程式（Inno Setup 6）
; 產生：GitHub Actions（.github/workflows/windows-installer.yml）；本機：ISCC.exe /DAppVersion=1.0.0 group\windows\PCG-Setup.iss
; 安裝時需要旁邊有離線資源包 PCG-offline（group/windows/build_bundle.py 產生），全程不連網、不需要系統管理員
#ifndef AppVersion
  #define AppVersion "0.0.0"
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
PrivilegesRequired=lowest
UsedUserAreasWarning=no
DirExistsWarning=no
OutputDir=..\..\dist
OutputBaseFilename=PCG-Setup-{#AppVersion}
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
#ifexist LangDir + "\ChineseTraditional.isl"
zh.ShortcutName=PCG 會議翻譯
zh.Installing=正在安裝執行環境與模型（約 3～10 分鐘），請稍候…
zh.InstallFailed=執行環境安裝失敗。請把這個檔案交給 IT：%n%1
zh.BundleMissing=找不到離線資源包：%n%1%n%n請把 PCG-offline 資料夾放在這個安裝程式旁邊，再執行一次。
zh.LaunchNow=立即開啟 PCG 會議翻譯
#endif
#ifexist LangDir + "\Indonesian.isl"
id.ShortcutName=Penerjemah Rapat PCG
id.Installing=Memasang runtime dan model (sekitar 3-10 menit). Mohon tunggu...
id.InstallFailed=Pemasangan runtime gagal. Kirim file ini ke IT:%n%1
id.BundleMissing=Paket offline tidak ditemukan:%n%1%n%nLetakkan folder PCG-offline di samping file Setup ini, lalu jalankan lagi.
id.LaunchNow=Buka Penerjemah Rapat PCG sekarang
#endif
#ifexist LangDir + "\Vietnamese.isl"
vi.ShortcutName=Phiên dịch cuộc họp PCG
vi.Installing=Đang cài đặt môi trường chạy và mô hình (khoảng 3-10 phút). Vui lòng chờ...
vi.InstallFailed=Cài đặt môi trường chạy thất bại. Hãy gửi tệp này cho IT:%n%1
vi.BundleMissing=Không tìm thấy gói cài đặt ngoại tuyến:%n%1%n%nHãy đặt thư mục PCG-offline cạnh tệp Setup này rồi chạy lại.
vi.LaunchNow=Mở Phiên dịch cuộc họp PCG ngay
#endif
#ifexist LangDir + "\Hindi.isl"
hi.ShortcutName=PCG मीटिंग अनुवादक
hi.Installing=रनटाइम और मॉडल इंस्टॉल हो रहे हैं (लगभग 3-10 मिनट)। कृपया प्रतीक्षा करें...
hi.InstallFailed=रनटाइम इंस्टॉल नहीं हो सका। यह फ़ाइल IT को भेजें:%n%1
hi.BundleMissing=ऑफ़लाइन पैकेज नहीं मिला:%n%1%n%nPCG-offline फ़ोल्डर को इस Setup फ़ाइल के पास रखें और फिर से चलाएँ।
hi.LaunchNow=PCG मीटिंग अनुवादक अभी खोलें
#endif

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "\.git\*,\.github\*,\dist\*,\group\tests\*,\group\windows\lang\*,\docs\*,\images\*,\logs\*,\recordings\*,\venv\*,\python\*,\hf_cache\*,\models\*,\tools\*,\group_data\*,\PCG-offline\*,\config.json,*.pyc,__pycache__"

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

function GetDefaultDir(Param: String): String;
begin
  { 有 D 槽就裝 D 槽，沒有就裝系統磁碟（不放使用者資料夾：中文使用者名稱會讓部分套件出錯） }
  if DirExists('D:\') then
    Result := 'D:\PCG-live-whisper'
  else
    Result := ExpandConstant('{sd}') + '\PCG-live-whisper';
end;

function InitializeSetup(): Boolean;
begin
  BundleDir := ExpandConstant('{param:BUNDLE|}');
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
