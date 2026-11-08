# PCG group edition: architecture and installation (for IT)

[中文](INSTALL.md) · [English](IT-GUIDE-en.md) · [Bahasa Indonesia](IT-GUIDE-id.md) · [Tiếng Việt](IT-GUIDE-vi.md)

<!-- When you change this guide, update all four languages (INSTALL.md, IT-GUIDE-en.md, IT-GUIDE-id.md, IT-GUIDE-vi.md). -->

## Architecture

```
                         ┌──────────────── Company network ─────────────┐
                         │                                              │
  Staff computers (browser) │  ① Application server (Linux, no GPU)      │
  ───────────────────    │   ─────────────────────────────              │
  http://app-server:19781/simple ─→  WebUI (incl. simple page /simple)  │
  upload recording → download minutes │ job queue: one at a time, rest wait │
                         │   storage: recordings/, outputs logs/        │
                         │        │ speech recognition  │ translation/summary │
                         │        ▼                     ▼              │
                         │   ② GPU host (Ubuntu + NVIDIA)               │
                         │   ─────────────────────────────              │
                         │   GPU speech recognition service (port 8978) │
                         │   Ollama LLM (port 11434)                    │
                         │     translation gemma4:26b, summary qwen3.8:27b │
                         │        ▲                     ▲              │
  ③ Staff computers that need live subtitles ──┘─────────┘              │
  (each installs on Windows/Mac)                                        │
  captures the sound played on that PC → http://localhost:19781/simple  │
                         └──────────────────────────────────────────────┘
```

| Role | What it does | Recommended hardware |
|---|---|---|
| ① Application server | Web pages, job queue, stores recordings and minutes | Linux (Ubuntu 22.04 / Debian 12 or newer), 2 vCPU, 4 GB RAM, disk according to recording volume (one hour of m4a is about 30–60 MB) |
| ② GPU host | Speech recognition, translation, summaries (the heavy part) | NVIDIA DGX Spark, or RTX 4090/5090 (24 GB VRAM or more) + 64 GB RAM; runs recognition and the LLM at the same time |
| ③ Staff computers | Only people who need **live subtitles** install it | Windows 10/11 or Mac; recognition and translation go to ②, so an ordinary office PC is enough |

- **Local mode and internal servers: audio and text never leave the company network.** With the group's Open WebUI, text goes to the models behind it (confirm luna/deepseek are inside the group); with "External AI service" it leaves the company (see "Server mode: three ways to connect an LLM" below)
- ① and ② can be the same machine, but the original author recommends separating them: while the GPU host runs the LLM, the web pages and file handling are more stable on another machine
- Live subtitles must run on ③ itself: they capture **the sound played on that computer** (Teams, Zoom), which a server cannot get

## Before you install

1. **Do not use the original author's one-line install commands** (`curl … jasoncheng7115 … | bash`, `irm … | iex`): they install the original version, without the new languages and the simple page
2. **Do not update with `./install.sh --upgrade`**: it downloads the original version and overwrites the group edition (the group edition blocks this and tells you to use git pull)
3. The repository may be private: downloading needs GitHub access (an account, or ask the administrator for a read-only deploy key)

## ② GPU host

1. Install the NVIDIA driver and CUDA (`nvidia-smi` shows the card)
2. Install Ollama and download the models:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma4:26b       # translation
   ollama pull qwen3.8:27b      # summaries, transcript correction
   ```
   Make it reachable on the LAN: add `OLLAMA_HOST=0.0.0.0` to Ollama's systemd settings, and open the firewall only to ① and the staff computers' subnets
3. The GPU speech recognition service **does not need a manual install**: at the end of installing ①, you are asked about a GPU server; enter the host address and it is installed automatically over SSH

## ① Application server

```bash
# 1. Download the group edition (as a normal user, not root)
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper

# 2. Install as a server (the WebUI runs as the systemd service jt-live-whisper-webui)
bash install.sh --server
```

During installation:
- `sudo apt` adds system packages such as ffmpeg
- **The "admin password" and "read-only password" are printed once: write them down right away**
- At the end you are asked for a GPU server: enter ②'s address and the GPU speech recognition service is installed over SSH
- LLM server: set ②'s Ollama address in the WebUI (`http://app-server:19781`, with the admin password), or write it as `llm_host` in `config.json`

### IT settings page (no config file editing)

Open the IT settings page **on the computer you want to configure** ("IT settings" at the bottom of the simple page; switch between 繁體中文, English and Bahasa Indonesia at the top right):

- Staff computers (installed with the offline installer): `http://localhost:19781/simple/admin`
- Application server: `http://app-server:19781/simple/admin`

1. **First use**: open it on that computer and set an IT password (at least 6 characters). It is required every time after that, also locally
2. **Mode**: local mode (CPU, M2M100 translation, no AI minutes) / server mode (an LLM server translates and writes AI minutes; GPU server optional)
3. **Server addresses**: enter the LLM server URL (required) and the GPU server (optional) → click "Test connection" → the models on the server are listed for you to choose.
   Without a GPU server, speech recognition stays on this computer (using the "local recognition model"); only translation and minutes go to the LLM
4. **Staff password**: required when connecting from another computer (not locally)
5. Click "Save": it takes effect the next time subtitles or a recording start; no restart needed

Settings are stored in the same `config.json` (passwords are hashed), in the same format as the original program.

### One-click update

"Updates" on the IT settings page:

- **Check for new versions** (on by default): when a new small update exists, staff see "New version" and "Update now" at the top of their page
- **Who can update**: staff themselves (default) / IT only (IT password required)
- **Update sources**:
  1. **Company shared folder** (optional, e.g. `\\fileserver\PCG\update`): put `PCG-Update-<version>.exe` and the `.sha256` file with the same name from the release page there. Computers without internet that can reach the company network can also update with one click
  2. **GitHub release page**: used automatically by computers with internet (not usable once the repository is private; use the shared folder then)
- After clicking update: download (or copy from the shared folder) → check the file fingerprint, delete and do not install if it does not match → close the app → install → self-check → reopen automatically; the open page reloads by itself
- No update while live subtitles or a recording are running; versions that need the full installer only show "ask IT"
- Log: `group_data\update.log`; downloaded files: `group_data\updates\`
- **`.sha256` fingerprint file**: every small update has a `.sha256` file with the same name, containing the exe's SHA-256 fingerprint (one line, 64 characters)
  - Shared folder: put the `.exe` and `.sha256` together; the fingerprint is checked before installing and the update is refused if it does not match; without a `.sha256` it still installs, but unchecked
  - GitHub: this file is not needed; the app reads the fingerprint of the release asset directly, and does not install when there is none
  - Manual check (PowerShell): `Get-FileHash .\PCG-Update-<version>.exe -Algorithm SHA256`; the file is intact when the hash equals the content of the `.sha256` (case does not matter)

### Server mode: three ways to connect an LLM

"Server type" on the IT settings page:

| Type | When to use | URL | API key |
|---|---|---|---|
| Group Open WebUI | Now (luna, deepseek) | The Open WebUI address you open in a browser | Required |
| Internal server | Once an RTX Spark / DGX Spark arrives, or your own Ollama, vLLM | `host:11434` | Usually not needed |
| External AI service | OpenAI, DeepSeek, Google Gemini, OpenRouter, etc. | Click a button to fill in the base URL | Required |

The GPU server (speech recognition) is separate from the LLM; any combination works, e.g. the LLM on the group's Open WebUI and recognition on your own RTX Spark.
If a GPU server is set but unreachable at the moment, recognition falls back to a small model on the staff computer, so nothing hangs.

#### Group Open WebUI (luna, deepseek)

1. Create an API key in Open WebUI: log in → avatar at top right → Settings → Account → API keys → Create
   (No such option: ask the group's AI administrator to allow API Keys under "Admin settings → User permissions")
2. IT settings page: mode "Server mode", type "Group Open WebUI", enter the URL (e.g. `https://ai.company-domain`), paste the key
3. Click "Test connection" and choose from the list: **translation: luna** (fast, no delay for live subtitles), **minutes: deepseek** (reasoning model, slow but thorough)
4. Without a GPU server, leave the GPU fields empty: recognition runs on the staff computer's CPU (small model)

Note: keys are **personal** and usage is billed to the owner; a dedicated account is recommended. Staff computers must be able to reach the Open WebUI address.

#### Internal server (RTX Spark, DGX Spark)

Once it arrives, one machine can serve as both "LLM" and "GPU speech recognition":

- **LLM**: install Ollama on the Spark, download the models and make it reachable on the LAN (`OLLAMA_HOST=0.0.0.0`). On the IT settings page choose type "Internal server" and enter `Spark-IP:11434`
- **GPU speech recognition**: the Spark runs the original author's GPU recognition service (`remote_whisper_server.py`, supports the aarch64 DGX Spark).
  Enter `Spark-IP` and port `8978` under "GPU server" on the IT settings page
  - DGX Spark (DGX OS / Ubuntu): run `bash install.sh` from a Linux machine or Mac; when asked for a GPU server, enter the Spark's address; it is installed over SSH and set to start at boot
  - RTX Spark laptop (Windows on Arm): the recognition service only exists for Linux and has to be installed in WSL2; **test it when it arrives**
- Staff computers reach the GPU service **by URL only**; they neither need nor use SSH (the service runs under systemd on the Spark)
- An LLM without GPU recognition also works: translation and minutes still work

#### External AI services (OpenAI, DeepSeek, Gemini…)

- **Meeting content leaves the company** and is billed by usage: first confirm this meets the company's data rules; use Open WebUI or an internal server for confidential meetings
- Apply for the key with a company account and set a monthly usage limit on the service's website
- Choose type "External AI service" → click OpenAI / DeepSeek / Google Gemini / OpenRouter to fill in the URL → paste the key → Test connection → choose models
- Other OpenAI-compatible services work too: enter the base URL from their documentation (usually ending in `/v1`). Azure OpenAI is not supported (different authentication); use OpenRouter or a LiteLLM proxy instead

Config fields (for troubleshooting): `llm_url`, `llm_api_key`, `llm_api_style` (`openwebui` / `openai` / missing = internal, auto-detected), `remote_whisper.host`.

We also recommend limiting source IPs (company subnets only) under "Security settings" in the full WebUI.

**Staff URL: `http://app-server:19781/simple`** (the full WebUI is at `/`, for IT)

## Offline installation on staff computers (works without internet or a GPU server)

**See [windows/README.md](windows/README.md)**: the single installer, local mode (CPU) by default;
when a GPU server becomes available, IT switches it on `/simple/admin`. "③" below is the alternative installation with internet.

### CPU usage (when staff computers recognize locally)

When live subtitles and recordings run on the staff computer's CPU (local mode, or server mode with only an LLM server):

- Speech recognition + local translation use about **3/4 of the cores** together, never more than the physical cores (4-core laptop: recognition 2–3, translation 1), leaving room for Teams and other programs
- On Windows the worker runs at **below-normal** priority: when the CPU is busy, foreground programs come first, so Teams and the mouse do not stutter
- Old computers still struggling, subtitles lagging: install the **Whisper base (multilingual)** pack under "Models" first, then choose it as the "Local live subtitle model" (faster, more mistakes). **The app never downloads models by itself** (offline installs do not download), so the settings page only lists models that are on this computer
- Adjust (Windows system environment variables, restart the app afterwards):
  - `PCG_CPU_THREADS=8`: total number of threads (e.g. a powerful desktop that should run at full speed)
  - `PCG_NORMAL_PRIORITY=1`: back to normal priority

### Model management (model packs, from r15)

The main installer only contains the basics (Whisper small, M2M100, Moonshine for English); other models come as **model packs**, installed under "Models" on the IT settings page:

| Model pack | Use | Size | Licence |
|---|---|---|---|
| PhoWhisper small / medium | Vietnamese speech recognition | about 240 / 740 MB | BSD-3-Clause |
| Whisper small Indonesian (maleo-ai) | Indonesian speech recognition | about 240 MB | Apache-2.0 |
| Whisper medium Indonesian (cahya) | Indonesian speech recognition | about 740 MB | Apache-2.0 |
| Whisper small / medium Hindi (vasista22) | Hindi speech recognition | about 240 / 740 MB | Apache-2.0 |
| Whisper base / medium / large-v3-turbo (multilingual, OpenAI) | The "local recognition model" for all languages (including Chinese), also used for two-way and classroom mode | about 80 / 740 / 800 MB | Apache-2.0 (base, medium) / MIT (large-v3-turbo) |
| MADLAD-400 3B | Local translation (slower; added content in test translations, compare before switching) | about 2.8 GB | Apache-2.0 |

Indonesian small uses maleo-ai/whisper-small-id (Apache-2.0); cahya/whisper-small-id is tagged only "cc", so commercial use cannot be confirmed and the build skips it automatically.

#### Which packs to install (recommended)

**Only on the computers that need them**: e.g. a Taiwanese staff computer that often meets Indonesian colleagues gets the Indonesian packs. Foreign staff's own computers (choosing "Chinese → my language") listen to Chinese and **do not need** language packs.

| Language | Live subtitles (ordinary laptop, CPU) | Live subtitles (NVIDIA card + GPU pack) | Recordings |
|---|---|---|---|
| Vietnamese | PhoWhisper small | PhoWhisper medium | PhoWhisper medium |
| Indonesian | Whisper small Indonesian (maleo-ai) | Whisper medium Indonesian (cahya) | Whisper medium Indonesian (cahya) |
| Hindi | Whisper small Hindi | Whisper medium Hindi | Whisper medium Hindi |
| Local translation | Keep the built-in M2M100 | Keep the built-in M2M100 | Keep M2M100 for now; decide on MADLAD-400 after comparing |

- small is about 240 MB, medium about 740 MB; both for one language about 1 GB
- medium is 2–3 times slower than small on the CPU: use small for live subtitles on ordinary laptops and keep medium for recordings
- Test recognition during packaging (synthetic speech): PhoWhisper medium and Indonesian small were fully correct; PhoWhisper small and Indonesian medium had one wrong word each. Test with real recordings
- In server mode with a GPU server, recognition happens on the server and the packs on staff computers are not used

#### By computer (new laptops)

First check for an NVIDIA graphics card (Task Manager → "Performance" → GPU):

| Computer | Local recognition model (Chinese, two-way, classroom) | Foreign-language live subtitles | Recordings |
|---|---|---|---|
| **With an NVIDIA card** (RTX 4050/4060/5050/5060 etc.) | Install the GPU pack, then Whisper medium or large-v3-turbo (multilingual) and choose it | medium for each language | medium for each language; large-v3-turbo for Chinese |
| **New 2025–2026 laptops** (Core Ultra, Ryzen AI; 16 GB RAM, 8+ cores) | Built-in small; try Whisper medium (multilingual) and go back to small if subtitles lag | small for each language (try medium) | medium for each language |
| **Ordinary or older laptops** (8 GB RAM, 4 cores) | Built-in small; if it lags, Whisper base (multilingual) | small for each language | medium for each language (takes longer) |

- The "AI chip (NPU)" advertised on new laptops is not used: speech recognition only uses the CPU or an NVIDIA card
- 16 GB RAM or more is recommended: with Teams, a browser and a medium model open, 8 GB is tight

#### Installation steps (once on each computer that needs them)

1. Update that computer to **r15 or newer** (version at the bottom of the page; if older, click "Check for updates")
2. On that computer open `http://localhost:19781/simple/admin` and enter the IT password (packs can only be installed on the computer itself)
3. Scroll to "**Models (model packs)**" → "Available", click "Install" for the packs you want and wait for the progress bar (a small pack takes about 1–3 minutes, depending on the network)
4. Under "**Model for each language**", choose "Live subtitles" and "Recordings" as in the table above, then click "**Apply model settings**"
5. Start one "the others speak …" live subtitle session to check: if text appears normally, you are done
6. No longer needed: click "Remove" under "Installed on this computer"; languages that used it go back to the built-in model

Many computers: IT first puts `catalog.json` and the `*.zip` files you need from the [release page](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs) in the company shared folder (the folder entered under "Updates"); each computer copies from the company network, which is faster than downloading from GitHub every time.

#### Details

- **Source**: the GitHub [model-packs release page](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs); computers without internet: IT puts that page's `catalog.json` and the pack files in the shared folder set under "Updates" (or its `models` subfolder)
- **Install**: only on that computer (IT password required); every file's SHA-256 is checked and nothing is installed on a mismatch; packs go to `models\packs\<id>`
- **Assignment**: under "Model for each language", choose the model for live subtitles and for recordings, click "Apply model settings"; it takes effect the next time subtitles or a recording start
  - Used only for **one-way** live subtitles and recordings in that language ("the others speak …"); two-way (the microphone side is Chinese) and classroom mode keep the built-in multilingual model
  - When MADLAD-400 is chosen for local translation, all translation in local mode uses it (a few seconds per sentence; live subtitles on old computers fall behind, so try it on recordings first)
- **Remove**: languages that used it go back to the built-in model automatically
- How packs are built: `.github/workflows/model-packs.yml` (download from Hugging Face, convert to CTranslate2 int8, accept only licences that allow commercial use, test recognition/translation, install once before publishing)

### English live subtitles (Moonshine)

- When "the others speak English" is recognized on the staff computer, **Moonshine medium** is used (English only, MIT licence, about 250 MB, included in the offline installer): about 0.3 s latency and much lighter on the CPU than Whisper
- Two-way ("I will speak too"), classroom mode and other languages keep Whisper (Moonshine only understands English)
- With a GPU server (recognition on the server), the server's Whisper is used as before
- Switch back to Whisper: add `"english_asr": "whisper"` under `pcg_simple` in `config.json`
- Moonshine's non-English models have a non-commercial licence and are not used by the group edition

### NVIDIA GPU pack (staff computers with an NVIDIA card)

- The release page also has the "NVIDIA GPU pack" (tag `gpu-cuda12-v…`, about 670 MB): CUDA 12 cuBLAS, cuDNN 9, NVRTC
- Only for NVIDIA cards (GeForce, RTX, MX); Intel and AMD graphics are not supported
- Needs PCG Meeting Translator r13 or newer and an NVIDIA driver that supports CUDA 12 (roughly 2023 or later)
- Installed into `gpu\cuda12` in the PCG Meeting Translator folder; reinstalling the app or small updates never remove it; install once
- After installing it checks automatically and shows the result (a silent install shows nothing; see `group_data\gpu_check.log`); if the card cannot be used, the app keeps using the CPU
- Manual check: run `python\python.exe gpu\gpu_check.py` in the install folder
- Compute type is chosen automatically: GTX 10 / MX series (compute capability 6.x) use int8, RTX 20 series and newer use float16
- The cloud build has no graphics card to test with: try it on a computer with an NVIDIA card before rolling it out

### Meeting room subtitle computer (one computer with a graphics card, everyone connects to it)

The main installer only has the small model: it runs on ordinary laptops, but Indonesian and Vietnamese have more recognition mistakes. For better subtitles, let **one computer with an NVIDIA graphics card be the "subtitle computer"**: it listens, recognizes and translates, and everyone else reads the subtitles in the browser on their phone or laptop. Staff computers need no changes.

**Recommended**: NVIDIA graphics card with at least 4 GB of video memory (e.g. RTX 3050 or better). A 2 GB card such as the MX330 may be too slow; test it first.

**Setup (IT, once, on the subtitle computer)**

1. Install the full installer, then the NVIDIA GPU pack (it checks the graphics card automatically when installed).
2. IT settings page → "Models (model packs)" → install "Whisper large-v3-turbo (multilingual)".
3. Under "Local recognition models", choose large-v3-turbo for "Live subtitles" and click "Save".
4. (Optional) Language packs (medium) for Indonesian, Vietnamese and Hindi: choose them in "Model for each language" and click "Apply model settings". They are used only for "I only read subtitles".
5. Tick "Allow other computers and phones to view subtitles", set a "Staff password", save, then **close the app and open it again**.
6. Allow incoming connections in Windows Firewall (needs an administrator: open PowerShell as administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   This only allows the local subnet. If the company network has several subnets, replace `LocalSubnet` with the real range (e.g. `10.10.0.0/16`).
7. Give the subtitle computer a fixed IP address (or a DHCP reservation) so the QR code address does not change.

**During the meeting**

1. The subtitle computer joins the Teams meeting (online), or uses the room microphone (in the room: choose "Same classroom, one microphone").
2. Choose the languages, click Start, then click "Share" on the subtitle screen and project the QR code.
3. Everyone scans the QR code (or opens `http://<subtitle computer IP>:19781/simple/live`), enters the staff password and picks the language to show in large text with the language menu at the top right. Phones can only view; they cannot stop the subtitles.

**Limits**

- **One session has two languages**: each sentence is translated into one language only (e.g. in a "Chinese ⇄ Indonesian" session every sentence has a Chinese and an Indonesian version). Viewers can choose between those two; choosing a third language (e.g. Vietnamese) does not produce Vietnamese. For meetings with three or more languages, see "Multinational meeting" in the use cases.
- Only computers and phones on the same company network can connect.
- Security: from r18 only connections by IP address or computer name are accepted; use a long staff password (there is no lockout after wrong attempts yet).

## ③ Staff computers that need live subtitles

### Windows

1. Download the group edition into `C:\jt-live-whisper`:
   - With Git: `git clone https://github.com/fairy715/PCG-live-whisper.git C:\jt-live-whisper`
   - Without Git: on the GitHub page click Code → Download ZIP, unzip, and put **the files inside** into `C:\jt-live-whisper`
2. Open PowerShell as administrator:
   ```powershell
   cd C:\jt-live-whisper
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   When asked for a GPU server at the end, enter ②'s address (recognition goes to the GPU host, so personal computers do not need a good graphics card)
3. Set the LLM server: enter ②'s Ollama address the first time you open the WebUI (it is remembered)
4. The desktop shortcut created this way opens the full WebUI; create a bookmark for staff: **`http://localhost:19781/simple`** (the offline installer does not have this issue: its "PCG Meeting Translator" shortcut opens the simple page)

### Mac

```bash
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper
bash install.sh
```

On first use, allow "Screen & System Audio Recording" for Terminal (you are prompted), then quit Terminal completely and open it again.

## Updating

```bash
cd ~/Apps/jt-live-whisper        # Windows: cd C:\jt-live-whisper
git pull
./install.sh                     # Windows: .\install.ps1 (adds packages the new version needs)
sudo systemctl restart jt-live-whisper-webui    # only on ①
```

When the original author releases a new version (the app shows "new version" at start), merge it into the group edition first, then update; do not use `--upgrade` directly. A weekly GitHub check opens an issue when the original project has news.

## Operations

| Item | Location / command |
|---|---|
| Service status, error log | `systemctl status jt-live-whisper-webui`, `journalctl -u jt-live-whisper-webui` |
| Job list of the simple page | `group_data/jobs.json` |
| Full log of one job | `group_data/job_<job id>.log` (staff see the job id on screen) |
| Recordings uploaded by staff | `recordings/simple/` |
| Minutes and transcripts | `logs/` |
| Health check | `./install.sh --doctor` |

**Recordings and outputs are never deleted automatically**: meeting recordings are sensitive data; clean them up regularly according to the company's data retention rules (e.g. keep 90 days).

### Problem reports (from r16)

* **Staff**: “Report a problem” at the bottom of the page → describe what happened → “Create report”. The browser downloads `PCG-report-<computer>-<date-time>.zip`, which staff send to IT. It can only be created on that computer (the logs are that computer's).
* **IT**: on the settings page, “Problem reports” lets you enter where staff send reports (email or Teams group); it is shown to staff. An email address also adds an “Email IT” button (subject and description filled in; staff attach the zip themselves). “Create a diagnostic file for this computer” on the same card creates one for IT; with “Allow other computers and phones to view subtitles” on, IT can also fetch it from their own computer with the IT password.
* **In the zip**: `summary.txt` (version, computer specs, memory, disk, GPU pack, model packs, browser, the staff description), `report.json` (the same plus the status and errors of the last 20 recording jobs and the live subtitle parameters), `config.json` (settings, **keys, passwords and hashes replaced with `***`**), `logs/` (last 400 lines of `webui.log`, `webui-error.log`, `update.log`, `install.log`, `gpu_check.log`, and the logs of the last 3 jobs, failed ones first).
* **Not in the zip**: recordings, transcripts, minutes, recording file names and meeting topics. Program logs may contain some subtitle text; staff can untick “Include recent program logs”.
* Each computer keeps only the last 10 diagnostic files (`group_data\reports\`).
* Diagnostic files may contain parts of meetings: **do not post them in a public GitHub issue**. The GitHub “Problem report” template only asks for the version, what happened and the steps.
