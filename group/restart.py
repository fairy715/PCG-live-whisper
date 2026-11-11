"""PCG 集團版 r20：程式自己重新啟動（同仁不用去工作管理員關 python.exe）。

「允許其他電腦或手機連進來看字幕」要在程式啟動時決定（launch.ps1 依設定給 PCG_WEBUI_HOST），
所以 IT 打開或關掉這個選項之後，要重新啟動一次才會生效。程式在背景跑、沒有視窗，同仁不知道怎麼關，
這裡讓頁面上按一個按鈕就重開：
  1. 先在背景叫起 launch.ps1 -NoBrowser -AfterPid <這個程式>（跟這個程式脫鉤，這邊結束它還在）
  2. 這個程式結束
  3. launch.ps1 等這個程式真的結束、連接埠空出來，再照最新的設定啟動
"""
import os
import subprocess
from pathlib import Path


def script(base_dir):
    return Path(base_dir) / "group" / "windows" / "launch.ps1"


def supported(base_dir):
    return os.name == "nt" and script(base_dir).is_file()


def command(base_dir, pid, port):
    return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
            "-File", str(script(base_dir)), "-NoBrowser", "-AfterPid", str(int(pid)), "-Port", str(int(port))]


def relaunch(base_dir, pid, port, popen=subprocess.Popen):
    """在背景啟動「等我結束再開」的 launch.ps1"""
    args = command(base_dir, pid, port)
    flags = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP（沒有主控台視窗）
    try:
        popen(args, creationflags=flags | 0x01000000, close_fds=True)   # + CREATE_BREAKAWAY_FROM_JOB
    except OSError:
        popen(args, creationflags=flags, close_fds=True)
