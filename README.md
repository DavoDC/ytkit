# ytkit

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/G2G31WKOCN)

YouTube download utilities powered by yt-dlp.

Download audio and video from YouTube with sane defaults - highest quality audio as MP3, organised output, and no manual fiddling with format codes.

## What it does

- Downloads audio at highest quality and converts to MP3 (VBR 0)
- Organised output directories for audio and video
- Config-driven: one file to set your paths, everything else just works
- Pairs with [ffkit](https://github.com/DavoDC/ffkit) for FFmpeg (shared binary, no duplication)

## Setup

1. Clone the repo
2. Copy `config/config.example.json` to `config/config.json`
3. Fill in your paths:
   - `ytdlp_exe` - leave blank to auto-download, or point to an existing `yt-dlp.exe`
   - `ffmpeg_dir` - path to a folder containing `ffmpeg.exe` (or use [ffkit](https://github.com/DavoDC/ffkit))
   - `audio_output_dir` - where downloaded audio goes
   - `video_output_dir` - where downloaded video goes
4. Run `python src/download_ytdlp.py` - auto-downloads yt-dlp if missing and updates your config

## Usage

```bash
# Download audio as MP3 (highest quality)
python src/ytkit.py --url "https://youtu.be/..."

# Download video
python src/ytkit.py --url "https://youtu.be/..." --format video
```

Paths, flags, and format defaults are handled automatically from `config/config.json`.
No manual yt-dlp commands needed.

## Structure

```
ytkit/
  config/               - config.example.json (template) + config.json (gitignored)
  src/ytkit.py          - CLI wrapper: one command, all paths auto-filled
  src/download_ytdlp.py - auto-downloads yt-dlp binary if missing
  scripts/              - launchers (future)
  data/logs/            - runtime logs
  docs/                 - IDEAS.md, HISTORY.md
```

## Related

- [ffkit](https://github.com/DavoDC/ffkit) - FFmpeg toolkit; ytkit uses it as the shared FFmpeg source
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - the underlying download engine
