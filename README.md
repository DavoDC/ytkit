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

### No terminal needed

Double-click `scripts/ytkit.bat`, paste a YouTube URL, pick audio/video/transcript. That's it - no Python commands, no Claude required.

### Command line

```bash
# Download audio as MP3 (highest quality)
python src/ytkit.py --url "https://youtu.be/..."

# Download video
python src/ytkit.py --url "https://youtu.be/..." --format video
```

Paths, flags, and format defaults are handled automatically from `config/config.json`.
No manual yt-dlp commands needed.

## Background updates

yt-dlp goes stale quickly, so ytkit keeps its binary fresh without ever making a download wait. Each run uses the binary you already have straight away. If the last check was more than 24 hours ago, a detached background process checks for a newer release after your task finishes, downloads it beside the old one, runs `--version` on it as a smoke test, keeps the old binary as `yt-dlp.previous.exe`, and swaps the new one in with a single `os.replace`. The next run picks it up.

A failed download or a failed smoke test never touches the working binary. If `yt-dlp.exe` is in use (Windows locks running programs) the new file stays staged and the swap is retried a little later. A lock file keeps it to one updater at a time, and the time of the last check is recorded before the network call so a crash cannot cause a retry storm. It only checks GitHub for release info and downloads from the official yt-dlp releases, and it logs to `data/logs/ytkit_update.log`.

```bash
python src/ytkit_update.py --status   # last check, stale or fresh, pending swap (no side effects)
python src/ytkit_update.py --check    # start the background updater if a check is due
python src/ytkit_update.py --run --force   # update now, in the foreground
```

## Structure

```
ytkit/
  config/               - config.example.json (template) + config.json (gitignored)
  src/ytkit.py          - CLI wrapper: one command, all paths auto-filled
  src/download_ytdlp.py - auto-downloads yt-dlp binary if missing
  src/ytkit_update.py   - non-blocking background updater for the yt-dlp binary
  scripts/ytkit.bat     - double-click launcher, no terminal/Claude needed
  data/logs/            - runtime logs
  docs/                 - IDEAS.md, HISTORY.md (stubs)
```

## Related

- [ffkit](https://github.com/DavoDC/ffkit) - FFmpeg toolkit; ytkit uses it as the shared FFmpeg source
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - the underlying download engine
