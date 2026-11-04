<#
.SYNOPSIS
    PCG 集團版：離線安裝執行環境（由 Setup.exe 呼叫，也可以手動執行修復）
.DESCRIPTION
    從離線資源包（build_bundle.py 產生的 PCG-offline 資料夾）安裝 Python、套件、模型、ffmpeg，
    全程不連網、不需要系統管理員、不寫登錄檔、不影響電腦上其他 Python。
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File pcg-install.ps1 -AppDir D:\PCG-live-whisper -Bundle E:\PCG-offline
#>
param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$Bundle
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$logDir = Join-Path $AppDir "group_data"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "install.log"
function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}
function Fail($msg) { Log "[錯誤] $msg"; exit 1 }
# 任何沒預料到的例外：把原因與行號寫進安裝紀錄（安裝程式是隱藏視窗執行，沒寫下來就什麼都看不到）
trap {
    Log ("[錯誤] {0}（第 {1} 行：{2}）" -f $_.Exception.Message, $_.InvocationInfo.ScriptLineNumber, $_.InvocationInfo.Line.Trim())
    exit 1
}
function Copy-Tree($src, $dst) {
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    & robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP /R:2 /W:2 | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "複製失敗：$src → $dst（robocopy $LASTEXITCODE）" }
    $global:LASTEXITCODE = 0
}

Log "=== PCG 會議翻譯 離線安裝開始 ==="
Log "安裝位置：$AppDir"
Log "資源包：$Bundle"

# 1. 檢查資源包
$manifestPath = Join-Path $Bundle "manifest.json"
if (-not (Test-Path $manifestPath)) { Fail "找不到離線資源包（$manifestPath）。請把 PCG-offline 資料夾放在 Setup.exe 旁邊" }
$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
Log ("資源包：{0}，Python {1}，辨識模型 {2}，共 {3} MB" -f $manifest.created, $manifest.python, ($manifest.whisper_models -join ","), $manifest.total_mb)
$reqHere = Join-Path $AppDir "group\windows\requirements-cpu.txt"
if (Test-Path $reqHere) {
    # 比對前統一換行（Windows 的 git 會把 LF 換成 CRLF，內容一樣卻會被當成不同）
    $text = [System.IO.File]::ReadAllText($reqHere).Replace("`r`n", "`n")
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($text)
    $sha = -join ([System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") })
    if ($sha -ne $manifest.requirements_sha256) {
        Log "[注意] 資源包的套件清單與這一版程式不同（資源包可能太舊）。照資源包安裝，若功能不正常請 IT 重新製作資源包"
    }
}

# 2. Python（NuGet 免安裝版：解壓縮即可，不寫登錄檔）
$pyDir = Join-Path $AppDir "python"
$py = Join-Path $pyDir "python.exe"
$nupkg = Get-ChildItem (Join-Path $Bundle "python") -Filter "python-*.nupkg" | Select-Object -First 1
if (-not $nupkg) { Fail "資源包裡沒有 Python（python\python-*.nupkg）" }
$wantVer = $manifest.python
$haveVer = if (Test-Path $py) { (& $py -c "import platform;print(platform.python_version())" 2>$null) } else { "" }
if ($haveVer -ne $wantVer) {
    Log "安裝 Python $wantVer ..."
    $tmp = Join-Path $env:TEMP ("pcg-py-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp "python.zip"
    Copy-Item $nupkg.FullName $zip
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    if (Test-Path $pyDir) { Remove-Item $pyDir -Recurse -Force }
    Copy-Tree (Join-Path $tmp "tools") $pyDir
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Log "Python $haveVer 已安裝"
}
if (-not (Test-Path $py)) { Fail "Python 安裝失敗（找不到 $py）" }

# 3. 套件（--no-index：只從資源包裝，不連網）
Log "安裝套件（約 2～5 分鐘）..."
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PYTHONUTF8 = "1"
& $py -m ensurepip --default-pip 2>&1 | Out-File -Append -Encoding UTF8 $log
$wheels = Join-Path $Bundle "wheels"
$lock = Join-Path $Bundle "requirements-lock.txt"
& $py -m pip install --no-index --find-links $wheels --upgrade pip 2>&1 | Out-File -Append -Encoding UTF8 $log
& $py -m pip install --no-index --find-links $wheels --no-warn-script-location -r $lock 2>&1 | Out-File -Append -Encoding UTF8 $log
if ($LASTEXITCODE -ne 0) { Fail "套件安裝失敗（詳見 $log）" }
& $py -m pip install --no-index --find-links $wheels --no-deps --no-warn-script-location resemblyzer 2>&1 | Out-File -Append -Encoding UTF8 $log
if ($LASTEXITCODE -ne 0) { Fail "resemblyzer 安裝失敗（詳見 $log）" }

# 4. 模型與 ffmpeg
Log "複製模型與工具..."
Copy-Tree (Join-Path $Bundle "models") (Join-Path $AppDir "models")
Copy-Tree (Join-Path $Bundle "hf_cache") (Join-Path $AppDir "hf_cache")
Copy-Tree (Join-Path $Bundle "tools") (Join-Path $AppDir "tools")

# 5. 設定檔：沒有才建立；已經有的（重新安裝、更新）保留 IT 的設定
$cfgPath = Join-Path $AppDir "config.json"
if (-not (Test-Path $cfgPath)) {
    $cfg = @{ pcg_simple = @{ backend = "local"; local_live_model = "small"; local_file_model = "small"; diarize = $false } }
    [System.IO.File]::WriteAllText($cfgPath, ($cfg | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
    Log "建立設定檔（本機模式）"
} else {
    Log "保留既有設定檔"
}

# 6. 自我檢查：套件載得起來、模型在、翻譯跑得動
Log "自我檢查..."
$env:HF_HUB_CACHE = Join-Path $AppDir "hf_cache"
$env:HF_HUB_OFFLINE = "1"
$env:PATH = (Join-Path $AppDir "tools\ffmpeg\bin") + ";" + $env:PATH
& $py (Join-Path $AppDir "group\windows\selftest.py") --quick 2>&1 | Out-File -Append -Encoding UTF8 $log
if ($LASTEXITCODE -ne 0) { Fail "自我檢查沒有通過（詳見 $log）" }
Log "=== 安裝完成 ==="
exit 0
