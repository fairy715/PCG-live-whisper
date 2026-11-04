<#
    PCG 集團版：桌面捷徑「PCG 會議翻譯」執行的啟動腳本（由 launch.vbs 以隱藏視窗呼叫）。
    程式沒在跑就在背景啟動 WebUI，然後用瀏覽器打開簡易頁面；已經在跑就直接打開。
#>
param([switch]$NoBrowser, [int]$Port = 19781)
$App = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$py = Join-Path $App "python\python.exe"
$logDir = Join-Path $App "group_data"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port([int]$p) {
    try { $c = New-Object System.Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $p); $c.Close(); return $true }
    catch { return $false }
}

if (-not (Test-Port $Port)) {
    # 執行環境：ffmpeg、離線的模型快取、UTF-8
    $env:PATH = (Join-Path $App "tools\ffmpeg\bin") + ";" + (Join-Path $App "python") + ";" + (Join-Path $App "python\Scripts") + ";" + $env:PATH
    $env:HF_HUB_CACHE = Join-Path $App "hf_cache"
    $env:HF_HUB_OFFLINE = "1"
    $env:HF_HUB_DISABLE_TELEMETRY = "1"
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    # 只給本機用，除非 IT 在設定頁打開「允許其他電腦觀看字幕」
    $env:PCG_WEBUI_HOST = "127.0.0.1"
    try {
        $cfg = Get-Content (Join-Path $App "config.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.pcg_simple.allow_remote_view) { $env:PCG_WEBUI_HOST = "0.0.0.0" }
    } catch { }
    Start-Process -FilePath $py -ArgumentList @("`"$(Join-Path $App 'webui.py')`"", "--no-browser", "--port", $Port) `
        -WorkingDirectory $App -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "webui.log") -RedirectStandardError (Join-Path $logDir "webui-error.log")
    for ($i = 0; $i -lt 120 -and -not (Test-Port $Port); $i++) { Start-Sleep -Milliseconds 500 }
}
if (-not $NoBrowser) { Start-Process "http://localhost:$Port/simple" }
