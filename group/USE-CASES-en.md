# PCG Meeting Translator: use cases

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Live subtitles tell languages apart **by where the sound comes from**:

- **Sound played by the computer** (the other people in Teams/Zoom, a video) = the other language
- **Microphone** (when you choose "I will speak too") = your own language

So only **the computer running the meeting or class** needs the app. The other side does not install anything.

## Choosing the right option (from version r11)

"Live subtitles" asks three things in order, and only the options that fit you stay on screen:

1. **What language do you speak?** Taiwanese staff choose "中文"; Indonesian, Vietnamese and Indian staff choose their own language.
2. **What kind of meeting?**
   - Only read subtitles
   - I will speak too
   - Same classroom
   - Room subtitle computer (from r19; the QR code is shown right after Start and everyone chooses their own language)
3. **What language do the others speak?** If you chose another language, you see "Chinese → your language" and the other foreign languages (from r17; e.g. Vietnamese staff see "Indonesian, to Vietnamese").

Your last choice is remembered. If the option you want is not shown, click "Show all options".

**"Indonesian" vs "Chinese → Indonesian": what is the difference?**

| Option | You hear | Subtitles in | Whose computer | Can add |
|---|---|---|---|---|
| Indonesian (the others speak Indonesian) | Indonesian | Chinese | Taiwanese staff who do not understand Indonesian | I will speak too (two-way), classroom mode |
| Chinese → Indonesian | Chinese | Indonesian | Indonesian staff who do not understand the Chinese-speaking trainer or manager | Classroom mode |
| Indonesian, to Vietnamese (r17) | Indonesian | Vietnamese | Vietnamese staff in a meeting with Indonesian staff | I will speak too (two-way), classroom mode |

Example: trainer Lin teaches Budi in Indonesia over Teams.
- Lin's computer: I speak "中文" → "I will speak too" → "Indonesian".
- Budi's computer: I speak "Bahasa Indonesia" → "Chinese → Indonesian" is selected automatically.

Rule of thumb: the option names the language **the others** speak; subtitles come out in **your** language. Vietnamese, Hindi and English work the same way.

## 1. Online meeting or class: Chinese ⇄ another language

> Example: the trainer speaks Chinese, Indonesian students answer in Indonesian, everyone is in Teams.

**Who installs it**: only the trainer's computer. Students join Teams/Zoom as usual.

1. On the trainer's computer: "PCG Meeting Translator" → "Live subtitles".
2. I speak "**中文**" → setting "**I will speak too**" → "**Indonesian**", click Start.
3. **Wear headphones**, otherwise the students' voices come out of the speakers into the microphone and are treated as Chinese.

Subtitles: the trainer's Chinese → Chinese + Indonesian translation; the students' Indonesian → Indonesian + Chinese translation.

**Let students see the subtitles** (either):
- **Share the screen** (works anywhere): tick "Subtitles always on top" and share your screen in Teams.
- **Phones** (students on the company network): click "Share" under the subtitles; students scan the QR code, enter the staff password and choose their language. IT must first turn on "Allow other computers and phones to view subtitles".

**Students want subtitles on their own computer** (from v2026.11.5.r9): install it on the student's computer too, open "Live subtitles" and choose I speak "**Bahasa Indonesia**": "**Chinese → Indonesian**" is selected automatically (Vietnamese, Hindi and English work the same way). Click Start. Students only listen, so no headphones needed. It picks up the trainer's voice from Teams and shows it in Indonesian; the trainer keeps two-way on. No screen sharing needed; everyone reads their own language.

## 2. Only understand what the other side says

> Example: a presentation from the Indonesian factory, a Vietnamese training video.

I speak "中文" → setting "**Only read subtitles**" → the others' language, click Start. No headphones needed.

## 3. Same meeting room or classroom, one microphone (classroom mode)

> Example: the trainer and Indonesian students talk in the same classroom. (from v2026.11.5.r9)

1. Connect a microphone that picks up the whole room (conference or desk microphone).
2. "Live subtitles" → I speak "中文" → setting "**Same classroom**" → "**Indonesian**" → Start. (Vietnamese, Hindi and English also work.)
3. Project the subtitles, or let students scan the "Share" QR code.

Each sentence is detected as Chinese or Indonesian automatically: Chinese → Chinese + Indonesian; Indonesian → Indonesian + Chinese.

**Limitations**
- Works best **one speaker at a time**; overlapping speech or mixed-language sentences are recognized poorly.
- **Very short replies** ("ok", "ya") may be detected as the wrong language.
- Subtitles are **a little slower** because each sentence's language is detected first.
- Classroom mode uses this computer's recognition (not the GPU server) with the local model IT set.
- "Classroom mode" and "I will speak too" are either/or: online class → "I will speak too" + headphones; same room → classroom mode.

## 4. Many people want to read subtitles on their phones

1. IT turns on "Allow other computers and phones to view subtitles" and sets a staff password (then press "Restart the program now" on the page, about 10 seconds; if it is forgotten, pressing Start restarts it first).
2. Start live subtitles, click "Share" and project the QR code.
3. People scan it, enter the staff password and choose their language under "I read" at the top right: Chinese, Indonesian, Vietnamese, Hindi or English. When a sentence is not in that language, the meeting computer translates one more copy (multi-language subtitles, from r19), and the top of the page says so. Phones can only view. They must reach that computer, usually on the company network.

## 5. Minutes after the meeting

1. "Recording → Minutes" → upload the recording or Teams/Zoom video (mp3, m4a, wav, mp4).
2. Choose the language **spoken most**; optionally the topic and number of speakers.
3. You can close the page; come back to download the minutes page, transcript and subtitle files (about 10–30 minutes for a 1-hour meeting).
4. AI minutes (decisions, action items, risks) need server mode; local mode produces the transcript and translation.

## 6. Everyone speaks Chinese

Choose "**Everyone speaks Chinese**": a Chinese transcript only, no translation.

## 7. Foreign-language staff with each other (e.g. Vietnamese and Indonesian staff, from r17)

Translated directly, not through Chinese. Any two of Indonesian, Vietnamese, Hindi and English.

**Online meeting (each on their own computer)**
- Vietnamese staff: I speak "Tiếng Việt" → kind of meeting → "Bahasa Indonesia" (subtitles in Vietnamese).
- Indonesian staff: I speak "Bahasa Indonesia" → kind of meeting → "Tiếng Việt" (subtitles in Indonesian).
- Choose "Only read subtitles", or "I will speak too (headset)" to also show the translation of what you say.

**Same meeting room, one microphone**: on one computer choose your language → "Same classroom" → the other language. Each sentence is detected and translated into the other language; use "Share" so others can follow on their phones in the language they choose.

**Quality**
- By default only the basic models are used: Whisper small for recognition and M2M100 on the computer for translation. Indonesian and Vietnamese recognition makes mistakes, and the translation follows them.
- For better results, IT can install language model packs (they help for "Only read subtitles") or switch to server mode on the IT settings page to translate with a large language model.
- Minutes from recordings are still written in Chinese.

---

## 8. Multinational meeting, Taiwanese staff speak Chinese

For example, a Taiwanese manager chairs the meeting in Chinese, with Indonesian, Vietnamese and Indian staff attending, and everyone wants subtitles in their own language.

**Online meeting (Teams): everyone opens subtitles on their own computer (works now)**
- **Foreign staff**: on your own computer choose I speak "your language" → "Only read subtitles" → "Chinese". The Chinese in Teams is translated into your language; everyone reads their own language independently.
- **Taiwanese staff following what foreign staff say**: choose "Indonesian" and so on. Only one foreign language at a time; when someone speaks another language, choose that language and click Start (the previous session is replaced).

**Same meeting room**
- Use the room's "subtitle computer" (one computer with a graphics card; setup in the IT guide): choose "**Room subtitle computer**" and the language most of the others speak (e.g. Indonesian), click Start; the QR code is shown right away, project it.
- Everyone scans the QR code and chooses their own language at the top right (multi-language subtitles, from r19): Chinese and Indonesian viewers read the normal subtitles; for Vietnamese, Hindi or English viewers the subtitle computer translates one more copy.
- The microphone only tells apart Chinese and the one foreign language you chose. Staff speaking other languages should use English or have someone relay.
- If only Taiwanese staff speak in the room, choose "**Everyone speaks Chinese**": from r28 this scene uses the microphone, and foreign staff read their own language through multi-language subtitles. (Up to r26 this option only listened to what the computer plays; update first.)

---

## 9. Teaching in Chinese from Taiwan, overseas staff read subtitles in their own language (r26)

For example, a teacher in Taiwan teaches Indonesian, Vietnamese and Indian plants over Teams, speaking Chinese throughout. Overseas staff want subtitles in their own language, and **the audio must not leave the company**.

**Recommended: one "subtitle computer" with a graphics card joins the class, and Chinese is recognized once**

The subtitle computer has an NVIDIA graphics card (IT installs the GPU pack and the Chinese model Breeze ASR 25 first; see the IT guide). It joins the Teams class like a student, listens to the teacher, recognizes the Chinese and translates it; overseas staff only need a browser.

- **Teacher**: teach over Teams as usual. Nothing to install.
- **Whoever runs the subtitle computer** (an assistant or IT):
  1. Join the Teams class on the subtitle computer, microphone off, speakers or headset **not muted** (the program listens to what the computer plays).
  2. Open PCG Meeting Translator → I speak "中文" → "**Only read subtitles**" → "**Everyone speaks Chinese**" → Start.
  3. On the subtitle screen press "**Share**" and paste the address (`http://<subtitle computer IP>:19781/simple/live`) and the staff password into the Teams chat.
- **Overseas staff**: open that address in a browser on a computer or phone, enter the password and choose your language at the top right (Indonesian, Vietnamese, Hindi, English). **Nothing to install.**

**The teacher's own computer has a graphics card: use it as the subtitle computer (from r28)**

The teacher teaches on their own computer (over Teams or in a classroom) and no second computer is needed: I speak "中文" → "**Same classroom**" (or "Room subtitle computer") → "**Everyone speaks Chinese**" → Start. The program then listens to the teacher through the **microphone** and still recognizes with Breeze; press "Share" and give the address to overseas staff. What students say in Teams does not appear in the subtitles (microphone only).

**Why this is more accurate**

- Chinese is recognized on the subtitle computer's graphics card with Breeze ASR 25 (trained for Taiwanese Mandarin and mixed Chinese-English), which is more accurate than the small built-in model on an ordinary laptop.
- Everyone reads the same recognition result; ask IT to put course terms into the glossary first.
- Audio is processed only on the subtitle computer and is not sent outside the company.

**Alternative: each overseas staff member opens subtitles on their own computer**

I speak "your language" → "Only read subtitles" → "Chinese". Recognition runs on that computer: with an NVIDIA graphics card the page suggests installing Breeze ASR 25 and the result matches the subtitle computer; an ordinary laptop can only use the small built-in model, so Chinese accuracy does not improve.

**Limits**

- What "Everyone speaks Chinese" listens to depends on the scene (from r28; the page says which after you choose it): "Only read subtitles" listens to **what the computer plays** (a subtitle computer that joined Teams and hears the teacher); "Same classroom" and "Room subtitle computer" listen to the **microphone** (the teacher speaks into this computer or the room microphone). Up to r26 it always listened to what the computer plays.
- One session listens to one source: with the microphone it does not hear other people in Teams, and with the computer's sound it does not hear this computer's microphone.
- Overseas sites must be able to reach the subtitle computer over the company network (port 19781). Ask IT or the network team first whether cross-site access works.
- Translation quality depends on IT's settings: local mode (M2M100) is average for Indonesian and Vietnamese; server mode (a large model) is much better.
- This setup combines existing features. Breeze's delay in live subtitles, microphone capture, cross-site access and many viewers at once have not been tested on real machines yet, so try it with one class first.

---

## Names and part numbers often misheard? Paste this meeting's information first (r32)

"**+ Add information about this meeting**" under live subtitles (also under "Recording → Minutes"):

1. Paste the **participants' names, product names, part numbers and agenda items** of this meeting, one per line or separated by commas. For example:

   ```
   Participants: Wang Hsiao-ming, Budi Santoso
   Central Java plant equipment acceptance
   PO-12345
   ```
2. Click "Start live subtitles". When recognition hears something similar it prefers these spellings; when an LLM translates, names and terms follow them too.
3. The information is kept on this computer only and is still there next time (no need to paste it again for a regular meeting); for a different meeting, change it or click "Clear".

- You do not need to paste a whole slide deck: short words help most. Long sentences are only background for translation and are not used to help recognition.
- When this computer is in **local mode**, the information only helps recognition (the local translation model cannot use it).
- When the orange notice is shown at the top of the page (audio or text goes to a service outside the company), this information is sent along with it: do not paste confidential content.
- Words the whole company uses (company name, plants, system names) belong in the "Glossary" kept by IT, so nobody has to paste them every time.

## The other side cannot understand me? Type on the subtitle screen (r32)

"**Type a reply**" at the bottom of the subtitle screen: type in your language, click "Translate", and the other side's language appears in large type.

- **Read it aloud**, or turn the screen and **show it**; in an online meeting click "Copy" and paste it into the Teams/Zoom chat.
- The button on the left shows the direction (e.g. "Chinese → Indonesian ⇄"); click it to swap, so the other person can also type in their language on your computer.
- One sentence at a time, up to 300 characters. What you typed stays in the conversation on this page; **people watching subtitles on their phones do not see it**.
- Only available while subtitles are running, on the computer that captures the sound; "Everyone speaks Chinese" has no translation, so it has no typed reply.
- To hide it, click "Type a reply" at the bottom again. In the black subtitle view it is hidden by default.

---

## Getting a transcript or minutes after the subtitles end (r33)

No separate recording is needed: every live subtitle session is saved as a transcript (only on the computer that captures the sound; the 10 most recent sessions are kept).

- **Subtitle screen**: after you click "Stop", "**Download transcript**" appears at the top; in server mode there is also "**Turn into meeting minutes**", which adds a job to the "Recording → Minutes" list for download a few minutes later.
- **Home page**: next time you open it, "Last subtitle session (date, sentences)" is at the top, with the same two buttons.
- The transcript is a text file: each sentence has its time, the original and the translation; typed replies are marked "（打字）" (typed).
- People watching on their phones cannot get the transcript; ask the colleague who ran the subtitles to download it.
- **The subtitles ended by themselves?** After more than 20 minutes without a new subtitle the program ends the session (the screen says why), so a forgotten session does not keep the computer busy. For a long break, click "Pause" first and it will not be ended; IT can change the time.

---

## Helpers on the screen (r29)

- **Confirmation line before you start**: above the button the page says “You will hear: Indonesian → subtitles in: Chinese”. If that is not what you expect, step 3 is the wrong way round; change it before starting.
- **Same as last time**: after your first session, the page only shows your last choice and “Start”. Press “Change” next to it to pick another language or scene.
- **Foreign-language staff**: once you choose your own language, “Chinese → your language” is already selected; change it only when you need another language.
- **Grey button**: something is not chosen yet; press it and the page tells you which step is missing.
- **Microphone icon at the top left of the subtitle screen**: it moves while the program is listening and nobody is speaking, and stays still while subtitles are appearing. An orange connection icon means the connection dropped and is being restored.
- **Room subtitle computer**: opens in large yellow-on-black subtitle mode; use A−/A+ at the top right to change the size one step at a time.
- **Going back to the home page while subtitles are running** (r30): the subtitle screen has “Back to home” at the bottom. Subtitles keep running; the home page then shows “Subtitles are running” and “Open subtitle screen” at the top to return.
- **Pressing “Stop”** (r30): the page asks “Keep going” or “End subtitles”, so a mistaken press does not stop the session.
- **First time you open the page** only the tour appears; the update and install suggestions wait until next time, and they never appear while subtitles are running.

---

## No subtitles? Test the sound first (r24)

On the live subtitles page, open "**🔊 Sound and microphone: test and choose devices**":

1. Press "**Start test**": the computer plays a short tone; please also say a few words into the microphone.
2. Watch the two bars:
   - **Sound played by this computer** moves = what the other side says is being captured. If not: the speaker is muted, the volume is 0, or Teams plays through another headset (choose it under "Advanced").
   - **Microphone** moves = what you say is being captured. If not: the microphone is muted, or choose another one in the list below (for example a USB conference microphone).
3. The chosen microphone and speaker are remembered and apply from the next subtitles. "Automatic" is right for most people; it follows the Windows default devices.

The microphone is not used when you only read subtitles; it is used for "I will speak too", "same classroom" and "meeting room subtitle computer". You cannot test while subtitles are running; press Stop first.

## Suggestions when the page opens (r25)

When the page opens, the program looks at this computer and the language you chose last time. It shows a suggestion only when one applies, one at a time:

- **“This computer has an NVIDIA graphics card”**: the computer has a graphics card but the GPU pack is not installed. Press “**Download the pack**”, double-click the downloaded file to install it (no administrator needed), then open the program again. Subtitles are faster and the computer is less busy.
- **“A more accurate speech model is recommended”**: for example, if you often choose Vietnamese as the other side's language, the Vietnamese model is recommended; with a graphics card and Chinese, Breeze ASR 25 (Taiwanese Mandarin) is recommended. Press “**Install**” and it downloads by itself; it is used from the next subtitles.
- Not now? Press “**Later**” (reminds you again after 7 days). Never? Press “**Do not remind me again**”.
- If the window says “Please ask IT”, this computer is installed by IT: tell IT what the window says.

## Tips

- Speak clearly, one person at a time, microphone close to the speaker. Fill in the meeting topic for meetings with many technical terms.
- The top of the page shows where audio and text are processed. Check it before confidential meetings.
- **Problems**: click “Report a problem” at the bottom of the page, describe what happened and press “Create report”. A zip file is downloaded; send it to IT (if IT has set it up, the page shows where to send it and an “Email IT” button). It has the version, computer specs and program logs, not recordings, transcripts or minutes.
