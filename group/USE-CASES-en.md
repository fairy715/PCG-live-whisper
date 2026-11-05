# PCG Meeting Translator: use cases

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Live subtitles tell languages apart **by where the sound comes from**:

- **Sound played by the computer** (the other people in Teams/Zoom, a video) = the other language
- **Microphone** (when "I will speak too" is ticked) = your own Chinese

So only **the computer running the meeting or class** needs the app. The other side does not install anything.

## 1. Online meeting or class: Chinese ⇄ another language

> Example: the trainer speaks Chinese, Indonesian students answer in Indonesian, everyone is in Teams.

**Who installs it**: only the trainer's computer. Students join Teams/Zoom as usual.

1. On the trainer's computer: "PCG Meeting Translator" → "Live subtitles".
2. Choose "**The other side speaks Indonesian**", tick "**I will speak too (two-way)**", click Start.
3. **Wear headphones**, otherwise the students' voices come out of the speakers into the microphone and are treated as Chinese.

Subtitles: the trainer's Chinese → Chinese + Indonesian translation; the students' Indonesian → Indonesian + Chinese translation.

**Let students see the subtitles** (either):
- **Share the screen** (works anywhere): tick "Subtitles always on top" and share your screen in Teams.
- **Phones** (students on the company network): click "Share" under the subtitles; students scan the QR code, enter the staff password and choose their language. IT must first turn on "Allow other computers and phones to view subtitles".

**Students want subtitles on their own computer** (from v2026.11.5.r9): install it on the student's computer too, open "Live subtitles", choose "**Chinese → Indonesian**" (also Vietnamese, Hindi, English) and click Start. Students only listen, so no two-way and no headphones needed. It picks up the trainer's voice from Teams and shows it in Indonesian; the trainer keeps two-way on. No screen sharing needed; everyone reads their own language.

## 2. Only understand what the other side says

> Example: a presentation from the Indonesian factory, a Vietnamese training video.

Choose "**The other side speaks …**", do **not** tick "I will speak too", click Start. No headphones needed.

## 3. Same meeting room or classroom, one microphone for everyone

**Current limitation**: everyone's voice comes through the same microphone and is treated as Chinese, so Indonesian answers are recognized wrongly.

**For now**
- **Translate only the trainer**: the trainer wears a headset microphone; choose "The other side speaks Indonesian" and tick "I will speak too". The trainer's Chinese is translated into Indonesian on the projector. Students' answers get no subtitles.
- **After class**: record the class and use "Recording → Minutes". Choose the language spoken most.

**Planned**: a "classroom mode" that detects whether each sentence is Chinese or Indonesian from one microphone and translates both ways.

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
- The version is at the bottom of the page; click to copy it when reporting a problem.
