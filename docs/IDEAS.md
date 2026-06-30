# ytkit - Ideas

Priority order: P0 = blocking/next dev session | P1 = high value | P2 = future

---


## P1 - FFmpeg troubleshooting via ffkit

When a download fails or produces wrong output, use ffkit's FFmpeg to diagnose:
- Run `ffprobe` on the downloaded file to inspect format/codec
- Compare against expected output (MP3, correct bitrate)
- ffkit's `dependencies/ffmpeg/ffprobe.exe` is the tool

---

## P1 - Download history log

Persist a JSON log of every download (`data/history.json`):
- Fields: URL, title, format, output path, timestamp
- Enables "have I already downloaded this?" check before re-downloading
- Claude reads history before any download task

---

## P1 - Playlist / batch download

- Accept a YouTube playlist URL, download all tracks as MP3
- Optional filters: date range, title pattern
- Log each track to download history

---

## P2 - Lightweight download UI

Build a GUI on top of yt-dlp to replace the old Java YTD.

Options explored:
- **Python webapp (Flask/FastAPI + browser UI)** - paste URL, pick format, click download, progress in browser. Accessible from any LAN device. No install. Top candidate.
- **Python + tkinter** - zero extra deps, desktop feel, simpler
- **Python + PyQt/PySide** - more polished, heavier

Notes:
- Check existing yt-dlp web UIs first (MeTube, yt-dlp-web) before building from scratch
- Must use ffkit for FFmpeg (same binary, no duplication)
- ytkit name allows this evolution without a rename

---

## Reference links

- yt-dlp repo: https://github.com/yt-dlp/yt-dlp
- yt-dlp docs (full options): https://github.com/yt-dlp/yt-dlp#readme
- yt-dlp releases: https://github.com/yt-dlp/yt-dlp/releases
- ffkit repo: https://github.com/DavoDC/ffkit
