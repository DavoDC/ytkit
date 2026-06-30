# ytkit

YouTube download utilities powered by yt-dlp.

## Structure

- `scripts/` - download helpers (future launchers)
- `data/logs/` - runtime logs
- `docs/IDEAS.md` - pending work
- `docs/HISTORY.md` - completed work
- `dependencies/` - notes on external binary locations

## Key binaries

| Binary | Location |
|--------|----------|
| yt-dlp | `C:\Users\David\GitHubRepos\NOT_MY_REPOS\yt-dlp\RELEASE_EXE\yt-dlp.exe` |
| ffmpeg | `C:\Users\David\GitHubRepos\ffkit\dependencies\ffmpeg\ffmpeg.exe` |
| ffprobe | `C:\Users\David\GitHubRepos\ffkit\dependencies\ffmpeg\ffprobe.exe` |

yt-dlp requires ffmpeg for audio format conversion. Always pass `--ffmpeg-location` pointing to ffkit's binary directory. Never assume ffmpeg is on PATH.

## Default audio download command

Always use this pattern - highest quality MP3 is the default:

```
"C:\Users\David\GitHubRepos\NOT_MY_REPOS\yt-dlp\RELEASE_EXE\yt-dlp.exe" ^
  --ffmpeg-location "C:\Users\David\GitHubRepos\ffkit\dependencies\ffmpeg" ^
  -f "bestaudio" ^
  --extract-audio ^
  --audio-format mp3 ^
  --audio-quality 0 ^
  -o "C:\Users\David\Downloads\NewMusic\%(title)s.%(ext)s" ^
  <URL>
```

In Bash (Git Bash / Claude Code):

```bash
YTDLP="/c/Users/David/GitHubRepos/NOT_MY_REPOS/yt-dlp/RELEASE_EXE/yt-dlp.exe"
FFMPEG_DIR="/c/Users/David/GitHubRepos/ffkit/dependencies/ffmpeg"
OUT="/c/Users/David/Downloads/NewMusic/%(title)s.%(ext)s"

"$YTDLP" --ffmpeg-location "$FFMPEG_DIR" \
  -f "bestaudio" --extract-audio --audio-format mp3 --audio-quality 0 \
  -o "$OUT" "<URL>"
```

## Output defaults

| Type | Default location | Default format |
|------|-----------------|----------------|
| Audio | `C:\Users\David\Downloads\NewMusic\` | MP3 (VBR 0, highest quality) |
| Video | `C:\Users\David\Downloads\` | best available |

## Claude instructions

When David says "use this repo" or "download X":
1. Read this CLAUDE.md for the correct binary paths and flags
2. Always use `--ffmpeg-location` pointing to ffkit - never skip this
3. Default to MP3 audio unless David specifies another format
4. Default output to `Downloads\NewMusic\` for audio unless told otherwise
5. Never use `python -c` or inline code - write a script to `TEMP/` if needed
6. Log the download outcome to `data/logs/` if running a script

## Relationship to ffkit

ytkit depends on ffkit for all media processing (format conversion, encoding).
ffkit repo: `C:\Users\David\GitHubRepos\ffkit`
ffkit CLAUDE.md documents the ffmpeg binary location and the hub pattern.
Never mention ffkit in any public-facing README of this repo (internal knowledge only).
