# ytkit

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
   - `ytdlp_exe` - path to your yt-dlp executable
   - `ffmpeg_dir` - path to a folder containing `ffmpeg.exe` (or use [ffkit](https://github.com/DavoDC/ffkit))
   - `audio_output_dir` - where downloaded audio goes
   - `video_output_dir` - where downloaded video goes

## Usage

See `CLAUDE.md` for the full download command. Basic audio download:

```bash
yt-dlp.exe --ffmpeg-location "path/to/ffmpeg" \
  -f "bestaudio" --extract-audio --audio-format mp3 --audio-quality 0 \
  -o "path/to/output/%(title)s.%(ext)s" \
  "https://youtu.be/..."
```

## Structure

```
ytkit/
  config/          - config.example.json (template) + config.json (gitignored)
  scripts/         - download helpers and launchers (future)
  data/logs/       - runtime logs
  docs/            - IDEAS.md, HISTORY.md
```

## Related

- [ffkit](https://github.com/DavoDC/ffkit) - FFmpeg toolkit; ytkit uses it as the shared FFmpeg source

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/G2G31WKOCN)
