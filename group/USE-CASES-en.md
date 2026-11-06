# PCG Meeting Translator: use cases

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Live subtitles tell languages apart **by where the sound comes from**:

- **Sound played by the computer** (the other people in Teams/Zoom, a video) = the other language
- **Microphone** (when you choose "I will speak too") = your own Chinese

So only **the computer running the meeting or class** needs the app. The other side does not install anything.

## Choosing the right option (from version r11)

"Live subtitles" asks three things in order, and only the options that fit you stay on screen:

1. **What language do you speak?** Taiwanese staff choose "中文"; Indonesian, Vietnamese and Indian staff choose their own language.
2. **What kind of meeting?** (asked only if you chose "中文")
   - Online meeting or class, I only read subtitles
   - Online meeting or class, I will speak too (headset)
   - Same classroom, one microphone
3. **What language do the others speak?** If you chose another language, "Chinese → your language" is selected for you.

Your last choice is remembered. If the option you want is not shown, click "Show all options".

**"Indonesian" vs "Chinese → Indonesian": what is the difference?**

| Option | You hear | Subtitles in | Whose computer | Can add |
|---|---|---|---|---|
| Indonesian (the others speak Indonesian) | Indonesian | Chinese | Taiwanese staff who do not understand Indonesian | I will speak too (two-way), classroom mode |
| Chinese → Indonesian | Chinese | Indonesian | Indonesian staff who do not understand the Chinese-speaking trainer or manager | One-way only |

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

1. IT turns on "Allow other computers and phones to view subtitles" and sets a staff password (restart the app afterwards).
2. Start live subtitles, click "Share" and project the QR code.
3. People scan it, enter the staff password and choose their language (view only). Phones must reach that computer, usually on the company network.

## 5. Minutes after the meeting

1. "Recording → Minutes" → upload the recording or Teams/Zoom video (mp3, m4a, wav, mp4).
2. Choose the language **spoken most**; optionally the topic and number of speakers.
3. You can close the page; come back to download the minutes page, transcript and subtitle files (about 10–30 minutes for a 1-hour meeting).
4. AI minutes (decisions, action items, risks) need server mode; local mode produces the transcript and translation.

## 6. Everyone speaks Chinese

Choose "**Everyone speaks Chinese**": a Chinese transcript only, no translation.

## Tips

- Speak clearly, one person at a time, microphone close to the speaker. Fill in the meeting topic for meetings with many technical terms.
- The top of the page shows where audio and text are processed. Check it before confidential meetings.
- **Problems**: click “Report a problem” at the bottom of the page, describe what happened and press “Create report”. A zip file is downloaded; send it to IT (if IT has set it up, the page shows where to send it and an “Email IT” button). It has the version, computer specs and program logs, not recordings, transcripts or minutes.
