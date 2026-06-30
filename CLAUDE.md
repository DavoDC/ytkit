# ytkit

YouTube download utilities powered by yt-dlp.

## Structure

- `config/` - `config.example.json` (template) and `config.json` (gitignored, your real paths)
- `src/` - Python utilities (`download_ytdlp.py` for auto-fetching the binary, future helpers)
- `scripts/` - download helpers (future launchers)
- `data/logs/` - runtime logs
- `docs/IDEAS.md` - pending work
- `docs/HISTORY.md` - completed work

## Configuration

All machine-specific paths live in `config/config.json` (gitignored). To set up:

1. Copy `config/config.example.json` to `config/config.json`
2. Fill in your actual paths for `ytdlp_exe`, `ffmpeg_dir`, `audio_output_dir`, `video_output_dir`

**Read `config/config.json` at the start of every download task** to get the correct paths for this machine.

## yt-dlp binary and docs

- **Binary location:** read from `config/config.json` (`ytdlp_exe` key)
- **Auto-download:** if `ytdlp_exe` path doesn't exist, run `src/download_ytdlp.py` to fetch it automatically
- **yt-dlp repo:** https://github.com/yt-dlp/yt-dlp
- **yt-dlp full docs (all options, formats, extractors):** https://github.com/yt-dlp/yt-dlp#readme
- **Releases (manual download):** https://github.com/yt-dlp/yt-dlp/releases

## FFmpeg via ffkit

ytkit depends on [ffkit](https://github.com/DavoDC/ffkit) for FFmpeg. ffkit stores the FFmpeg binary in its `dependencies/ffmpeg/` folder and acts as a shared FFmpeg hub for sibling repos.

Set `ffmpeg_dir` in `config/config.json` to point at ffkit's `dependencies/ffmpeg/` folder.

yt-dlp requires FFmpeg for audio format conversion. Always pass `--ffmpeg-location` using the value from config - never assume FFmpeg is on PATH.

## Default audio download command

Always use this pattern - highest quality MP3 is the default:

```bash
# Read paths from config/config.json first, then:
YTDLP="<config.ytdlp_exe>"
FFMPEG_DIR="<config.ffmpeg_dir>"
OUT="<config.audio_output_dir>/%(title)s.%(ext)s"

"$YTDLP" --ffmpeg-location "$FFMPEG_DIR" \
  -f "bestaudio" --extract-audio --audio-format mp3 --audio-quality 0 \
  -o "$OUT" "<URL>"
```

## Output defaults

| Type | Config key | Default format |
|------|-----------|----------------|
| Audio | `audio_output_dir` | MP3 (VBR 0, highest quality) |
| Video | `video_output_dir` | best available |

## Claude instructions

When asked to download something using ytkit:
1. Read `config/config.json` for all binary paths and output directories
2. Always pass `--ffmpeg-location` - never skip this step
3. Default to MP3 audio unless another format is requested
4. Use `audio_output_dir` from config for audio, `video_output_dir` for video
5. Never use inline code execution - write a script to TEMP/ if needed
