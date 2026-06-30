# ytkit

YouTube download utilities powered by yt-dlp.

Download audio and video from YouTube with sane defaults - highest quality audio as MP3, organised output, and no manual fiddling with format codes.

## What it does

- Downloads audio at highest quality and converts to MP3
- Organised output to `Downloads\NewMusic\` by default
- Tracks downloads and learnings in a single place

## Structure

```
ytkit/
  scripts/     - download helpers and launchers
  data/logs/   - runtime logs
  docs/        - IDEAS.md, HISTORY.md
```

## Requirements

- yt-dlp (see `CLAUDE.md` for binary location)
- ffmpeg via ffkit (internal - see `CLAUDE.md`)
