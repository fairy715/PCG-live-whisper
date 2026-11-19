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
- **What's-new window** (updates after r19): when staff open the page, a "New version" window lists what this version adds, with "Update now" or "Later"; "Later" keeps the update notice at the top of the page as before and the window does not pop up again until the page is opened next time. In the shared folder you can also put `PCG-Update-<version>.whats-new.json` (the release page has `whats-new.json`; just rename it); without it only the version number is shown

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
  - **Back to normal automatically when subtitles fall behind** (r20): if a piece of audio waits more than 6 seconds for recognition (for example a Teams video call using the whole CPU), the priority goes back to normal for a while; subtitles are a bit slower but keep coming. After 30 seconds in a row of keeping up, it goes back down. Before, on a 2-core laptop with Teams open, subtitles stopped completely and only came out all at once after Teams was closed
  - **2-core, 4-thread power-saving laptops** (for example i3-10110U): recognition uses 2 threads (was 1)
- **Cutting speech at pauses** (r21, default for local live subtitles): before, the latest 5 seconds of audio were recognized again every 3 seconds (each piece of audio 1.7 times); now a piece is cut when the speaker pauses and recognized once, and translation waits for the end of the sentence. In a test with the same 38 seconds of English (Whisper base, 2 threads) recognition CPU went from 20.9 to 13.3 seconds (37% less), and subtitles come as whole sentences instead of repeated half sentences. When Whisper gets stuck repeating the same sentence, it is recognized once more with a different temperature and leftover repeats are kept only once. To go back to the old way: Windows system environment variable `PCG_LIVE_SEGMENT=window` (restart the program afterwards)
- **Local live subtitle model "Automatic"** (default from r21): 2-core computers use the **Whisper base** pack if installed (otherwise the built-in small, and the IT settings page suggests installing it); computers with the GPU pack that passed its check use the large-v3-turbo or medium pack if installed; others use the built-in small. The IT settings page shows which one this computer uses. Computers where small was saved before keep small; choose "Automatic (recommended)" and save to switch
- Old computers still struggling, subtitles lagging: install the **Whisper base (multilingual)** pack under "Models" first, then choose it as the "Local live subtitle model" (faster, more mistakes). **The app never downloads models by itself** (offline installs do not download), so the settings page only lists models that are on this computer
- Adjust (Windows system environment variables, restart the app afterwards):
  - `PCG_CPU_THREADS=8`: total number of threads (e.g. a powerful desktop that should run at full speed)
  - `PCG_NORMAL_PRIORITY=1`: back to normal priority

### Speech recognition API (r24, optional)

"**Speech recognition API**" on the IT settings page sends speech recognition to an OpenAI-compatible API (`/audio/transcriptions`). It is usually more accurate than the small model on staff computers, and the laptop no longer runs recognition.

| Target | Address | Where audio goes | Cost |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1`, models such as `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `whisper-1` | **Leaves the company** | Billed by audio length at OpenAI's published price; each computer showing subtitles counts separately |
| Groq (r26) | `https://api.groq.com/openai/v1`, model `whisper-large-v3-turbo` (default) or `whisper-large-v3` | **Leaves the company** | Has a free tier with usage limits (see below); get a key at [console.groq.com/keys](https://console.groq.com/keys) |
| A recognition service inside the company (RTX Spark, or an OpenAI-compatible server run by another team) | For example `http://10.x.x.x:8000/v1` | Stays in the company | No extra cost |

- Fill in the address, model and key (an internal service may need no key) and press "**Test connection**": one second of silence is sent to check the address, key and model
- **An external service must use https and a key**; an address with an internal IP or a plain host name counts as internal, and for an internal service with a domain name tick "This is a service inside the company"
- When on: each live sentence (a piece cut at a pause) is sent once; recordings are cut at pauses into pieces of at most 25 seconds. It **takes priority over the GPU server**, and English also goes to the API (Moonshine is not used)
- **If the API cannot be reached, times out, or the key is wrong**: that piece is recognized on this computer instead, so subtitles do not stop; after 3 failures in a row the API is paused for 2 minutes, and for 10 minutes when the key or model is wrong
- Glossary terms are sent as hints (`prompt`), and misheard spellings are still changed back
- When audio leaves the company, an orange notice is shown on the IT settings page and at the top of the staff page. Turn it off for confidential meetings or use an internal service
- The key is stored in this computer's `config.json` (`pcg_simple.asr_api_key`) and is masked in diagnostic files; the Windows system environment variable `PCG_ASR_API=off` turns the API off temporarily
- "I will speak too" (two-way) mode still sends overlapping audio every 3 seconds, about 1.7 times the usage of one-way
- **Groq (r26)**: press "Groq (free tier)" on the settings page to fill in the address and model, paste the key and press "Test connection". Recognition uses Whisper large-v3, more accurate than the built-in small model; the program still sends to the API first and falls back to this computer when the API cannot be used
  - **The free tier has limits, shared by the whole account.** Figures collected by third-party sites (Groq may change them at any time; check the [limits page in the Groq console](https://console.groq.com/settings/limits)): about 20 requests per minute, about 2,000 requests per day, about 7,200 seconds of audio per hour and about 28,800 seconds (8 hours) per day
  - In practice: one computer in "Only read subtitles" (one request per sentence) makes about 8–15 requests per minute, so roughly 2–4 hours per day; several computers sharing one key at the same time, or "I will speak too" (one request every 3 seconds, exactly 20 per minute), reach the limit quickly
  - **When the limit is reached (HTTP 429)**: that piece is recognized on this computer at once, and the API is paused for the time Groq asks for (at least 15 seconds, at most 10 minutes, 60 seconds if not stated), then used again automatically; subtitles do not stop, accuracy just returns to the local model for that time. "Test connection" shows "Connected, but the usage limit is reached"
  - A key cannot be shipped inside the installer (the installer is public), so IT enters it once per computer; for heavy use, pay for the service or use a recognition service inside the company
  - Tested on 2026-11-18 against a simulated server (including 429); not yet tested with a real Groq key
- Tested on 2026-11-18 against a simulated API server; not yet tested with a real OpenAI key, so press "Test connection" when you first set it up

### Glossary (names and terms, r23)

Company names, sites, system names and people are often misheard or mistranslated by general models. After you fill in "**Glossary**" on the IT settings page:

| Stage | What happens | Where it works |
|---|---|---|
| Recognition | Glossary terms are given to Whisper as hints, so similar sounds prefer these terms | Chinese, Indonesian, Vietnamese etc. recognized on the staff computer (Whisper). English subtitles (Moonshine) and GPU-server recognition do not take hints |
| After recognition | Spellings listed as "often misheard" are changed back to the correct term | Everywhere (including English subtitles and the GPU server) |
| Translation | Server mode: the large model is told to use the required translation and to keep terms without one unchanged. Local mode (M2M100): terms are replaced with the required translation before translating | Most reliable in server mode; usually works in local mode, not guaranteed |

Format: one term per line. After "`=`" the required translation (optional), after "`|`" spellings it is often misheard as; pasting from Excel also works (three columns: term, translation, misheard spellings).

```
寶成 | 寶城 | 保成 = Pou Chen
MES
Sukabumi | Suka Bumi
# lines starting with # are comments
```

- Applies from the **next** subtitles or recording after saving; at most 500 terms and 20000 characters. Only the first 60 terms are given to Whisper as hints (more makes it worse), so **put important terms first**
- **Shared by all computers**: put a `glossary.txt` (UTF-8) in the same format in the company shared folder set under "Updates"; each computer reads it when subtitles or a recording start, and uses the last copy if the folder cannot be reached. For the same term, the entry on this computer wins
- English terms of 3 letters or fewer (for example ME) must match upper/lower case exactly, so an ordinary "me" is not treated as a term
- Hints raise the chance, they do not guarantee: for a term that is still misheard, adding the misheard spelling after "`|`" is the surest fix
- The glossary is stored in this computer's `config.json` (`pcg_simple.glossary`) and is included in the "Report a problem" diagnostic file

### Model management (model packs, from r15)

The main installer only contains the basics (Whisper small, M2M100, Moonshine for English); other models come as **model packs**, installed under "Models" on the IT settings page:

| Model pack | Use | Size | Licence |
|---|---|---|---|
| PhoWhisper small / medium | Vietnamese speech recognition | about 240 / 740 MB | BSD-3-Clause |
| Whisper small Indonesian (maleo-ai) | Indonesian speech recognition | about 240 MB | Apache-2.0 |
| Whisper medium Indonesian (cahya) | Indonesian speech recognition | about 740 MB | Apache-2.0 |
| Whisper small / medium Hindi (vasista22) | Hindi speech recognition | about 240 / 740 MB | Apache-2.0 |
| Breeze ASR 25 (MediaTek Research, r25) | Taiwanese Mandarin and mixed Chinese-English speech recognition; large-v2 size, needs an NVIDIA card for live subtitles | about 1.5 GB | Apache-2.0 |
| Whisper base / medium / large-v3-turbo (multilingual, OpenAI) | The "local recognition model" for all languages (including Chinese), also used for two-way and classroom mode | about 80 / 740 / 800 MB | Apache-2.0 (base, medium) / MIT (large-v3-turbo) |
| MADLAD-400 3B | Local translation (slower; added content in test translations, compare before switching) | about 2.8 GB | Apache-2.0 |

**Automatic recommendation when the page opens** (r25): based on this computer and the "other side's language" the staff member chose last time, the program recommends one model pack that is not installed yet, one at a time: GPU acceleration + Chinese → Breeze ASR 25; Vietnamese / Indonesian / Hindi → the pack for that language (medium with GPU acceleration, small without); GPU acceleration and no large multilingual model → large-v3-turbo; 2-core computers → base. Staff can press "Install" (the pack is then assigned to that language automatically), "Later" (reminds about this pack again after 7 days) or "Do not remind me again". When "who can update" is IT only, the window only asks staff to contact IT. Hardware-related recommendations are not shown when IT has chosen a fixed "local live subtitle model". Nothing is recommended when the catalog cannot be read (no internet and no `catalog.json` in the shared folder) or disk space is short.

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

#### Measured: error rate of each model (public datasets, 2026-11-19)

The recommendations above are backed by a measurement: every model was run once on public speech datasets and compared with the reference text. 50 sentences per language; error rate = wrong characters (Chinese) or words (other languages) ÷ characters/words in the reference, **lower is better**.

| Model | Chinese | Indonesian | Vietnamese | Hindi | English | Mixed Chinese-English | Processing time ÷ audio length |
|---|---|---|---|---|---|---|---|
| Whisper base (pack) | 17.2% | 30.6% | 40.1% | 105.7% | 8.9% | 37.6% | 0.1 |
| **Whisper small (built into the installer)** | 10.6% | 16.1% | 20.7% | 55.9% | 6.1% | 28.1% | 0.3 |
| The language's own small pack | — | 9.2% | 13.1% | 14.8% | — | — | 0.3 (Hindi 0.6) |
| Whisper medium (pack) | 6.0% | 9.1% | 14.0% | 36.7% | 4.4% | 26.8% | 0.85 |
| The language's own medium pack | — | 7.1% | 9.7% | 11.2% | — | — | 0.85 (Hindi 1.5) |
| Whisper large-v3-turbo (pack) | 5.9% | 7.6% | 10.2% | 30.5% | 4.8% | 20.9% | 1.0 |
| Breeze ASR 25 (pack) | 5.3% | — | — | — | — | 17.8% | 1.6 |

- "The language's own pack": PhoWhisper for Vietnamese, maleo-ai (small) / cahya (medium) for Indonesian, vasista22 for Hindi.
- The last column was measured on a 4-core machine **without a graphics card**: 0.3 means 10 seconds of audio take 3 seconds; close to or above 1 cannot keep up with live subtitles and needs an NVIDIA card with the GPU pack.

**What the numbers show**

- **The built-in small model is the bottleneck**: except for English, replacing it removes 40% to more than half of the errors; Hindi shows it most (55.9% → 11.2%).
- **Foreign languages improve even without a graphics card**: the small packs for Indonesian, Vietnamese and Hindi run at about the same speed as the built-in model and lower the error rate from 16.1% / 20.7% / 55.9% to 9.2% / 13.1% / 14.8%. On computers that often listen to these languages this is the cheapest step.
- **Chinese has no cheap option**: only medium, large-v3-turbo and Breeze ASR 25 go from 10.6% to below 6%, and all three are at or beyond the live limit on an ordinary computer, so a graphics card is needed.
- **Computers with a graphics card**: Breeze ASR 25 for Chinese and mixed Chinese-English; each language's medium pack for Indonesian, Vietnamese and Hindi; large-v3-turbo if you want one general model, but its Hindi is poor (30.5%).
- **Breeze and large-v3-turbo cannot be told apart on plain Chinese** (5.3% vs 5.9%, a difference of 11 characters); the gap on mixed Chinese-English is clearer (17.8% vs 20.9%).

**Limits (the numbers do not transfer directly to real meetings)**

- The data is clean read speech; real meetings have distant microphones, people talking over each other and accents, so error rates will be higher than in the table. The ranking between models is still a useful guide.
- The Chinese set is Mandarin from mainland China, not a Taiwanese accent; the advantage of Breeze ASR 25 on Taiwanese Mandarin may be understated.
- Only 50 sentences per language: a difference of one or two percentage points does not mean a real difference.
- Hindi with base is above 100%, which means it output many extra wrong words; the cause was not checked sentence by sentence.
- If real meetings are much worse than this table, the cause is usually the audio (microphone too far away, room echo); a different model or a graphics card does not help with that.

**Data and re-running**: Chinese, Indonesian, Vietnamese, Hindi and English use [FLEURS](https://huggingface.co/datasets/google/fleurs) (Google, CC-BY 4.0), mixed Chinese-English uses [ASCEND](https://huggingface.co/datasets/CAiRE/ASCEND) (CAiRE, CC-BY-SA 4.0); no company recordings were used. The script is `group/bench_asr.py`; re-run it on GitHub under Actions → "語音辨識模型比較" → Run workflow (languages, number of sentences and models can be chosen; all models with 50 sentences each take about 3 hours 40 minutes). This result: [run log](https://github.com/fairy715/PCG-live-whisper/actions/runs/44498791993).

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

### Room subtitle computer (one computer with a graphics card, everyone connects to it)

The main installer only has the small model: it runs on ordinary laptops, but Indonesian and Vietnamese have more recognition mistakes. For better subtitles, let **one computer with an NVIDIA graphics card be the "subtitle computer"**: it listens, recognizes and translates, and everyone else reads the subtitles in the browser on their phone or laptop. Staff computers need no changes.

**Recommended**: NVIDIA graphics card with at least 4 GB of video memory (e.g. RTX 3050 or better). A 2 GB card such as the MX330 may be too slow; test it first.

**Automatic suggestion** (r25): when staff open the page, the program asks `nvidia-smi` whether this computer has an NVIDIA graphics card. If it does, has at least 4 GB of video memory, and the pack is not installed yet, a window suggests installing it: "Download the pack" (the installer on the GitHub release page, about 706 MB), "Later" (reminds again after 7 days) or "Do not remind me again". When "who can update" is set to IT only, the window only asks staff to contact IT and shows no download. Discrete AMD and Intel cards cannot use the pack (it supports NVIDIA CUDA only), so there is no reminder; computers without the NVIDIA driver (no `nvidia-smi`) are not detected either. For computers without internet, IT should bring the pack installer to them.

**Setup (IT, once, on the subtitle computer)**

1. Install the full installer, then the NVIDIA GPU pack (it checks the graphics card automatically when installed).
2. IT settings page → "Models (model packs)" → install "Whisper large-v3-turbo (multilingual)".
3. Under "Local recognition models", choose large-v3-turbo for "Live subtitles" and click "Save".
4. (Optional) Language packs (medium) for Indonesian, Vietnamese and Hindi: choose them in "Model for each language" and click "Apply model settings". They are used only for "Only read subtitles".
5. Tick "Allow other computers and phones to view subtitles", set a "Staff password", save, then press "**Restart the program now**" that appears on the page (about 10 seconds, from r20; no need to end python.exe in Task Manager). If staff start the "meeting room subtitle computer" scene before the program has restarted, it restarts by itself first
   - The original author added "Allow other computers to connect" under "Security settings" in the advanced WebUI (`/`) in 2.34.1: when the group edition is opened from the desktop shortcut, **the IT settings page option above decides**; ignore the advanced WebUI checkbox (r22)
6. Allow incoming connections in Windows Firewall (needs an administrator: open PowerShell as administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   This only allows the local subnet. If the company network has several subnets, replace `LocalSubnet` with the real range (e.g. `10.10.0.0/16`).
7. Give the subtitle computer a fixed IP address (or a DHCP reservation) so the QR code address does not change.

**During the meeting**

1. The subtitle computer joins the Teams meeting (online), or uses the room microphone (in the room: choose "**Room subtitle computer**", from r19).
2. Choose the languages and click Start: in the room scene the QR code is shown right away (otherwise click "Share" on the subtitle screen); project the QR code.
3. Everyone scans the QR code (or opens `http://<subtitle computer IP>:19781/simple/live`), enters the staff password and picks the language to show in large text with the language menu at the top right. Phones can only view; they cannot stop the subtitles.

**Limits**

- **Multi-language subtitles (from r19)**: viewers choose their own language at the top right (Chinese, Indonesian, Vietnamese, Hindi, English). When a sentence is not in that language, the subtitle computer translates one more copy; e.g. in a "Chinese ⇄ Indonesian" session, viewers who chose Vietnamese see Vietnamese. Speech recognition does not increase, only translation: on the subtitle computer's CPU in local mode (the graphics card with the GPU pack), or on the LLM server in server mode; languages nobody chose are not translated. On slow computers, untick "Multi-language subtitles" on the IT page. Japanese and Korean speech can only be added in Chinese.
- Only computers and phones on the same company network can connect.
- Security: from r18 only connections by IP address or computer name are accepted; use a long staff password (there is no lockout after wrong attempts yet).

### Teaching in Chinese from Taiwan, overseas sites read subtitles: Breeze for Chinese, audio stays inside the company

The staff steps are in scenario 9 of the use cases. One subtitle computer joins the Teams class and recognizes the teacher's Chinese on its graphics card with **Breeze ASR 25** (MediaTek Research, trained for Taiwanese Mandarin and mixed Chinese-English); overseas staff connect with a browser and choose their own language. Speech is recognized once, and audio is processed only on the subtitle computer.

**IT does this once on the subtitle computer**

1. Follow the "meeting room subtitle computer" steps above: full installer, GPU pack, "Allow other computers and phones to view subtitles", staff password. Breeze is a large-v2 size model: 6 GB of video memory or more is recommended, and a 4 GB card needs testing.
2. Under "Models (model packs)", install "**Breeze ASR 25（台灣華語、中英夾雜）**" (about 1.5 GB).
3. Assign Breeze to Chinese:
   - **From r28**: under "Model for each language", row "Chinese", choose Breeze ASR 25 for "Live subtitles" and press "Apply model settings".
   - **r25 and r26**: the settings page has no "Chinese" row. The only way is the staff page on the subtitle computer: choose "Everyone speaks Chinese", reload, and press "Install" in the "A more accurate speech model is recommended" window (it assigns the model to Chinese when installed). Afterwards **do not press "Apply model settings"**, which clears the Chinese assignment. Updating to r28 is recommended.
4. Firewall: the rule above only opens the same subnet. For overseas sites, replace `-RemoteAddress` with their subnets (for example `10.10.0.0/16,10.20.0.0/16`) and ask the network team to confirm TCP 19781 from each site to the subtitle computer.
5. Put course terms (company, plants, systems, names) into the glossary.
6. Translation quality: local mode uses M2M100, which is average for Indonesian and Vietnamese; for better results switch the subtitle computer to server mode and translate with the group AI platform or an internal large model (recognition still runs on the subtitle computer).

**How the program actually behaves**

- A Chinese model pack is used for one-way subtitles that listen to Chinese: Chinese-speaking staff choosing "Everyone speaks Chinese", and foreign-language staff choosing "Chinese → your language". Classroom mode (one microphone, two languages) and "I will speak too" use the multilingual model, not Breeze.
- What "Everyone speaks Chinese" listens to depends on the scene (**from r28**):
  - "Only read subtitles": **what the computer plays** (a subtitle computer that joined Teams and hears the teacher). Do not mute its speakers or headset.
  - "Same classroom" and "Room subtitle computer": the **microphone** (the teacher speaks into this computer or the room microphone). It uses the microphone chosen under "Sound and microphone", or the Windows default if none was chosen; with no microphone at all the session does not start and the page says no microphone was found.
  - Both use the Chinese model pack (Breeze). One session listens to one source; starting "Everyone speaks Chinese" again in another scene replaces the running session.
  - Up to r26 the scene made no difference: it always listened to what the computer plays (so "Room subtitle computer" with "Everyone speaks Chinese" did not hear the room microphone).
- A language is translated only when a viewer chooses it. Only subtitle text is sent out, so traffic is small.
- With "Speech recognition API" on, audio goes to the API first and Breeze is only the fallback. To keep audio inside the company, do not turn on an external API.

**Not yet tested on real machines**: Breeze's delay in live subtitles (depends on the graphics card), microphone capture for "Everyone speaks Chinese" (the cloud has no audio devices, so only passing the microphone number to the main program was tested), cross-site access, and many viewers at once. On 2026-11-18 only model loading with one Chinese sentence and the behaviour above (automated tests) were confirmed in the cloud. Try it with one class first.

### Changes to the IT settings page (r29)

- **“Where data goes” at the top**: from the values currently on the page, it always shows where “Audio” and “Text” go (this computer only, the company GPU server, an internal service, the group AI platform, or outside the company). If either leaves the company the whole bar turns orange. It follows unsaved changes too, so you can check before saving.
- **The LLM data destination now follows the address**: if the server type is “Internal server” but the address is a domain or public IP outside the company, the staff page shows “AI service outside the company” (up to r28 only the type was used, so an external address still showed as internal). When an internal server uses a domain name (not a 10.x or 192.168.x address and not a host name without a dot), a box “This is a server inside the company” appears under the address; tick it after confirming. **After upgrading, open the settings page once and read the top bar**: an internal server addressed by domain name counts as external until the box is ticked.
- **Rarely changed sections start collapsed**: glossary, updates, problem reports, models. The current value is shown at the right of the title (number of terms, automatic check on or off, contact, number of model packs); click the title to open.
- **The save bar stays at the bottom of the window**: it shows “Unsaved changes” and the save result. “Apply model settings” is still a separate button inside Models.
- **Local mode hides the server settings.**
- **Remote viewing on without a staff password**: an orange warning appears under the checkbox.
- The header used to say changes take effect immediately; in fact they apply from the next subtitles or recording. The text has been corrected.
- **Two test buttons** (r30): “Test the LLM connection” and “Test the GPU server”, each showing its result below itself. After the LLM test succeeds, the page checks whether the names in “Translation model” and “Minutes (summary) model” are in the server’s list and warns if not (a mistyped model name is the most common reason subtitles are not translated).
- **Change IT password** (r30): a window on the page, hidden input, entered twice; at least 6 characters.
- **Computers without internet** (r30): Models shows “This computer cannot reach GitHub right now, so only model packs in the company shared folder are listed”. This is normal, not an error.
- **Warnings that data leaves the company** (r30) have a thick orange bar on the left, to set them apart from ordinary notices.

### Icons used in the interface (r29)

- Scene icons are single-colour SVG drawn in the page, no longer emoji (emoji look different on Windows 10 and 11).
- The states “listening, preparing, processing, reconnecting, testing” use moving icons from [Ultra Lab Motion Icons](https://github.com/ppcvote/ultralab-anim-icons) v0.3.1 (MIT License). Only the 8 icons in use are embedded in the pages; nothing is loaded from the internet. They do not move when Windows has animation effects turned off (Settings → Accessibility → Visual effects → Animation effects).

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
