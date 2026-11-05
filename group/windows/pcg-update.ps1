<#
.SYNOPSIS
    PCG 集團版：小更新包裝完後的整理與自我檢查（由 PCG-Update-*.exe 呼叫）
.DESCRIPTION
    小更新包只換程式檔；執行環境（python）、模型（models、hf_cache）、ffmpeg（tools）沿用完整安裝時裝好的。
    這支只清掉舊版的編譯快取，再跑一次自我檢查，結果寫在 group_data\update.log。不連網、不需要系統管理員。
#>
param([Parameter(Mandatory = $true)][string]$AppDir)
$ErrorActionPreference = "Stop"
$logDir = Join-Path $AppDir "group_data"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "update.log"
function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}
trap {
    Log ("[錯誤] {0}（第 {1} 行）" -f $_.Exception.Message, $_.InvocationInfo.ScriptLineNumber)
    exit 1
}

$ver = "?"
$vf = Join-Path $AppDir "group\version.json"
if (Test-Path $vf) { $ver = (Get-Content $vf -Raw -Encoding UTF8 | ConvertFrom-Json).version }
Log "=== 小更新包：更新到 $ver ==="

# 舊版留下的 .pyc：Python 會照時間戳重新編譯，清掉只是保險（不動 python\ 裡的）
Get-ChildItem -Path $AppDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike (Join-Path $AppDir "python\*") } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$py = Join-Path $AppDir "python\python.exe"
if (-not (Test-Path $py)) { Log "[錯誤] 找不到執行環境（$py），請改用完整安裝檔"; exit 1 }
$env:HF_HUB_CACHE = Join-Path $AppDir "hf_cache"
$env:HF_HUB_OFFLINE = "1"
$env:PYTHONUTF8 = "1"
$env:PATH = (Join-Path $AppDir "tools\ffmpeg\bin") + ";" + $env:PATH

Log "自我檢查..."
$old = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $py (Join-Path $AppDir "group\windows\selftest.py") --quick 2>&1 | ForEach-Object { "$_" } | Out-File -Append -Encoding UTF8 $log
$rc = $LASTEXITCODE
$ErrorActionPreference = $old
if ($rc -ne 0) { Log "[錯誤] 自我檢查沒有通過（結束代碼 $rc）"; exit 1 }
Log "=== 更新完成 ==="
exit 0
