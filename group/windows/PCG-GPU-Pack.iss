; PCG 集團版：NVIDIA GPU 加速包（Inno Setup 6）
; 只有裝了 NVIDIA 顯示卡的電腦需要。把語音辨識要用的 CUDA 12 函式庫（cuBLAS、cuDNN 9、NVRTC）放到
; PCG 會議翻譯安裝資料夾的 gpu\cuda12\bin；主程式重裝、小更新包都不會動到這個資料夾。
; 裝好後自動檢查這台電腦能不能用顯示卡（gpu_check.py），把結果告訴使用者；不能用時程式照常用 CPU。
; 產生：.github/workflows/gpu-pack.yml；本機：ISCC.exe /DPackVersion=1 /DStage=暫存資料夾 group\windows\PCG-GPU-Pack.iss
#ifndef PackVersion
  #define PackVersion "1"
#endif
#ifndef Stage
  #define Stage "..\..\dist\gpu-stage"
#endif
#define LangDir "lang"

[Setup]
AppId=PCG-live-whisper-GPU
AppName=PCG Meeting Translator GPU Pack
AppVersion=cuda12.{#PackVersion}
AppVerName=PCG Meeting Translator NVIDIA GPU Pack (CUDA 12, v{#PackVersion})
AppPublisher=PCG
DefaultDirName={code:GetAppDir}
DisableDirPage=yes
UsePreviousAppDir=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UsedUserAreasWarning=no
DirExistsWarning=no
OutputDir=..\..\dist
OutputBaseFilename=PCG-GPU-Pack-cuda12-v{#PackVersion}
SetupIconFile=..\..\icons\jt-live-whisper.ico
UninstallDisplayName=PCG Meeting Translator NVIDIA GPU Pack
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallFilesDir={app}\gpu\uninstall
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
WizardStyle=modern
ShowLanguageDialog=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
#ifexist LangDir + "\ChineseTraditional.isl"
Name: "zh"; MessagesFile: "{#LangDir}\ChineseTraditional.isl"
#endif
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
en.NotInstalled=PCG Meeting Translator is not installed on this computer.%n%nInstall it first, then run this GPU pack.
en.Checking=Checking whether this computer can use the NVIDIA graphics card. Please wait...
en.CheckFailed=The GPU check did not finish. Details are in:%n%1%n%nPCG Meeting Translator keeps working on the CPU.
en.LaunchNow=Open PCG Meeting Translator now
#ifexist LangDir + "\ChineseTraditional.isl"
zh.NotInstalled=這台電腦還沒有安裝 PCG 會議翻譯。%n%n請先安裝 PCG 會議翻譯，再執行這個 GPU 加速包。
zh.Checking=正在檢查這台電腦能不能用 NVIDIA 顯示卡，請稍候…
zh.CheckFailed=顯示卡檢查沒有完成，詳細內容在：%n%1%n%nPCG 會議翻譯會照常用 CPU。
zh.LaunchNow=立即開啟 PCG 會議翻譯
#endif

[Files]
Source: "{#Stage}\bin\*"; DestDir: "{app}\gpu\cuda12\bin"; Flags: ignoreversion
Source: "{#Stage}\VERSION.json"; DestDir: "{app}\gpu\cuda12"; Flags: ignoreversion
Source: "gpu_check.py"; DestDir: "{app}\gpu"; Flags: ignoreversion

[UninstallDelete]
Type: filesandordirs; Name: "{app}\gpu\cuda12"
Type: files; Name: "{app}\gpu\gpu_check.py"
Type: files; Name: "{app}\group_data\gpu_check.json"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\group\windows\launch.vbs"""; Description: "{cm:LaunchNow}"; Flags: postinstall nowait skipifsilent

[Code]
var
  AppDir: String;

function FindAppDir(): String;
var
  Key: String;
begin
  Result := '';
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PCG-live-whisper_is1';
  if not RegQueryStringValue(HKCU, Key, 'Inno Setup: App Path', Result) then
    if not RegQueryStringValue(HKLM64, Key, 'Inno Setup: App Path', Result) then
      RegQueryStringValue(HKLM32, Key, 'Inno Setup: App Path', Result);
end;

function GetAppDir(Param: String): String;
begin
  Result := AppDir;
end;

function InitializeSetup(): Boolean;
begin
  AppDir := FindAppDir();
  Result := (AppDir <> '') and FileExists(AddBackslash(AppDir) + 'python\python.exe');
  if not Result then
    SuppressibleMsgBox(CustomMessage('NotInstalled'), mbError, MB_OK, IDOK);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  RC: Integer;
begin
  { 程式開著的話先關掉：重新打開才會載入顯示卡的函式庫 }
  Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like ''' +
       AppDir + '\python\*'' } | Stop-Process -Force"', '', SW_HIDE, ewWaitUntilTerminated, RC);
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  RC: Integer;
  Params, Log: String;
begin
  if CurStep <> ssPostInstall then Exit;
  ForceDirectories(AppDir + '\group_data');
  Log := AppDir + '\group_data\gpu_check.log';
  WizardForm.StatusLabel.Caption := CustomMessage('Checking');
  { 檢查結果由 gpu_check.py 自己跳視窗說明（Unicode 訊息，安靜安裝時不跳）；程式整個當掉（結束代碼不是 0/1/2）才由這裡說 }
  Params := '--out "' + AppDir + '\group_data\gpu_check.json" --lang ' + ActiveLanguage;
  if not WizardSilent then Params := Params + ' --msgbox';
  if not Exec('cmd.exe', '/C ""' + AppDir + '\python\python.exe" "' + AppDir + '\gpu\gpu_check.py" ' + Params +
              ' > "' + Log + '" 2>&1"', AppDir, SW_HIDE, ewWaitUntilTerminated, RC) or (RC < 0) or (RC > 2) then
    SuppressibleMsgBox(FmtMessage(CustomMessage('CheckFailed'), [Log]), mbInformation, MB_OK, IDOK);
end;
