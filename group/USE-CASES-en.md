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
   - Online meeting or class, I only read subtitles
   - Online meeting or class, I will speak too (headset)
   - Same classroom, one microphone
   - Meeting room subtitle computer, everyone reads on their phones (from r19; the QR code is shown right after Start and everyone chooses their own language)
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
2. I speak "**中文**" → setting "**Online meeting or class, I will speak too (headset)**" → "**Indonesian**", click Start.
3. **Wear headphones**, otherwise the students' voices come out of the speakers into the microphone and are treated as Chinese.

Subtitles: the trainer's Chinese → Chinese + Indonesian translation; the students' Indonesian → Indonesian + Chinese translation.

**Let students see the subtitles** (either):
- **Share the screen** (works anywhere): tick "Subtitles always on top" and share your screen in Teams.
- **Phones** (students on the company network): click "Share" under the subtitles; students scan the QR code, enter the staff password and choose their language. IT must first turn on "Allow other computers and phones to view subtitles".

**Students want subtitles on their own computer** (from v2026.11.5.r9): install it on the student's computer too, open "Live subtitles" and choose I speak "**Bahasa Indonesia**": "**Chinese → Indonesian**" is selected automatically (Vietnamese, Hindi and English work the same way). Click Start. Students only listen, so no headphones needed. It picks up the trainer's voice from Teams and shows it in Indonesian; the trainer keeps two-way on. No screen sharing needed; everyone reads their own language.

## 2. Only understand what the other side says

> Example: a presentation from the Indonesian factory, a Vietnamese training video.

I speak "中文" → setting "**Online meeting or class, I only read subtitles**" → the others' language, click Start. No headphones needed.

## 3. Same meeting room or classroom, one microphone (classroom mode)

> Example: the trainer and Indonesian students talk in the same classroom. (from v2026.11.5.r9)

1. Connect a microphone that picks up the whole room (conference or desk microphone).
2. "Live subtitles" → I speak "中文" → setting "**Same classroom, one microphone**" → "**Indonesian**" → Start. (Vietnamese, Hindi and English also work.)
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
- Choose "I only read subtitles", or "I will speak too (headset)" to also show the translation of what you say.

**Same meeting room, one microphone**: on one computer choose your language → "Same classroom, one microphone" → the other language. Each sentence is detected and translated into the other language; use "Share" so others can follow on their phones in the language they choose.

**Quality**
- By default only the basic models are used: Whisper small for recognition and M2M100 on the computer for translation. Indonesian and Vietnamese recognition makes mistakes, and the translation follows them.
- For better results, IT can install language model packs (they help for "I only read subtitles") or switch to server mode on the IT settings page to translate with a large language model.
- Minutes from recordings are still written in Chinese.

---

## 8. Multinational meeting, Taiwanese staff speak Chinese

For example, a Taiwanese manager chairs the meeting in Chinese, with Indonesian, Vietnamese and Indian staff attending, and everyone wants subtitles in their own language.

**Online meeting (Teams): everyone opens subtitles on their own computer (works now)**
- **Foreign staff**: on your own computer choose I speak "your language" → "I only read subtitles" → "Chinese". The Chinese in Teams is translated into your language; everyone reads their own language independently.
- **Taiwanese staff following what foreign staff say**: choose "Indonesian" and so on. Only one foreign language at a time; when someone speaks another language, choose that language and click Start (the previous session is replaced).

**Same meeting room**
- Use the room's "subtitle computer" (one computer with a graphics card; setup in the IT guide): choose "**Meeting room subtitle computer, everyone reads on their phones**" and the language most of the others speak (e.g. Indonesian), click Start; the QR code is shown right away, project it.
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
  2. Open PCG Meeting Translator → I speak "中文" → "**Online meeting or class, I only read subtitles**" → "**Everyone speaks Chinese**" → Start.
  3. On the subtitle screen press "**Share**" and paste the address (`http://<subtitle computer IP>:19781/simple/live`) and the staff password into the Teams chat.
- **Overseas staff**: open that address in a browser on a computer or phone, enter the password and choose your language at the top right (Indonesian, Vietnamese, Hindi, English). **Nothing to install.**

**The teacher's own computer has a graphics card: use it as the subtitle computer (from r28)**

The teacher teaches on their own computer (over Teams or in a classroom) and no second computer is needed: I speak "中文" → "**Same classroom, one microphone**" (or "Meeting room subtitle computer, everyone reads on their phones") → "**Everyone speaks Chinese**" → Start. The program then listens to the teacher through the **microphone** and still recognizes with Breeze; press "Share" and give the address to overseas staff. What students say in Teams does not appear in the subtitles (microphone only).

**Why this is more accurate**

- Chinese is recognized on the subtitle computer's graphics card with Breeze ASR 25 (trained for Taiwanese Mandarin and mixed Chinese-English), which is more accurate than the small built-in model on an ordinary laptop.
- Everyone reads the same recognition result; ask IT to put course terms into the glossary first.
- Audio is processed only on the subtitle computer and is not sent outside the company.

**Alternative: each overseas staff member opens subtitles on their own computer**

I speak "your language" → "I only read subtitles" → "Chinese". Recognition runs on that computer: with an NVIDIA graphics card the page suggests installing Breeze ASR 25 and the result matches the subtitle computer; an ordinary laptop can only use the small built-in model, so Chinese accuracy does not improve.

**Limits**

- What "Everyone speaks Chinese" listens to depends on the scene (from r28; the page says which after you choose it): "I only read subtitles" listens to **what the computer plays** (a subtitle computer that joined Teams and hears the teacher); "Same classroom" and "Meeting room subtitle computer" listen to the **microphone** (the teacher speaks into this computer or the room microphone). Up to r26 it always listened to what the computer plays.
- One session listens to one source: with the microphone it does not hear other people in Teams, and with the computer's sound it does not hear this computer's microphone.
- Overseas sites must be able to reach the subtitle computer over the company network (port 19781). Ask IT or the network team first whether cross-site access works.
- Translation quality depends on IT's settings: local mode (M2M100) is average for Indonesian and Vietnamese; server mode (a large model) is much better.
- This setup combines existing features. Breeze's delay in live subtitles, microphone capture, cross-site access and many viewers at once have not been tested on real machines yet, so try it with one class first.

---

## No subtitles? Test the sound first (r24)

On the live subtitles page, open "**🔊 Sound and microphone: test and choose devices**":

1. Press "**Start test**": the computer plays a short tone; please also say a few words into the microphone.
2. Watch the two bars:
   - **Sound played by this computer** moves = what the other side says is being captured. If not: the speaker is muted, the volume is 0, or Teams plays through another headset (choose it under "Advanced").
   - **Microphone** moves = what you say is being captured. If not: the microphone is muted, or choose another one in the list below (for example a USB conference microphone).
3. The chosen microphone and speaker are remembered and apply from the next subtitles. "Automatic" is right for most people; it follows the Windows default devices.

The microphone is not used when you only read subtitles; it is used for "I also speak", "same classroom" and "meeting room subtitle computer". You cannot test while subtitles are running; press Stop first.

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
