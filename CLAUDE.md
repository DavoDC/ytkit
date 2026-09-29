# ytkit

YouTube download utilities powered by yt-dlp.

## Structure

- `config/` - `config.example.json` (template) and `config.json` (gitignored, your real paths)
- `src/ytkit.py` - CLI wrapper: one command downloads anything, paths handled automatically
- `src/download_ytdlp.py` - auto-downloads yt-dlp binary if missing
- `src/ytkit_update.py` - non-blocking background updater (stale-while-revalidate); `python src/ytkit_update.py --status|--check|--run|--resolve`
- `data/state/` - updater state and lock (gitignored)
- `scripts/` - launchers (future)
- `data/logs/` - runtime logs
- `docs/IDEAS.md`, `docs/HISTORY.md` - stubs only: the backlog is kept privately by the maintainer, not in this repo (use GitHub issues for requests)

## How to download (Claude instructions)

**Audio (default - MP3 highest quality):**
```bash
python src/ytkit.py --url <YouTube URL>
```

**Video:**
```bash
python src/ytkit.py --url <YouTube URL> --format video
```

**Transcript (subtitles as plain text - for research/market analysis, not just downloads):**
```bash
python src/ytkit.py --url <YouTube URL> --format transcript
```
Downloads English subs (manual or auto-generated) via yt-dlp, no ffmpeg required, then cleans the `.vtt` into a deduplicated plain-text `.txt` next to it (auto-caption `.vtt` repeats lines in a rolling-caption format - the cleaner in `clean_vtt()` collapses that). Output goes to `transcript_output_dir` in `config/config.json`. **Only fetch the specific video URLs given - never pass a channel URL (`@channelname/videos`) to this or you'll bulk-download the whole channel's transcripts.** If you already have `.vtt` files from a manual yt-dlp run, `scripts/clean_transcripts.py <dir-or-files>` re-runs just the cleaning step (imports the same `clean_vtt()` - one canonical implementation, not duplicated).

That's it. ytkit reads `config/config.json` and fills in all paths and flags automatically.
No manual path construction. No reading config first. Just run the command.

The wrapper auto-downloads yt-dlp if the binary is missing, then proceeds. When the binary is present it is used at once; if the last update check is over 24 hours old a detached updater runs after the task (download to `yt-dlp.new.exe`, `--version` smoke test, old kept as `yt-dlp.previous.exe`, `os.replace`). Never blocks a task. Tests inject every network/process boundary: `python -m pytest -q`.

## Configuration

All machine-specific paths live in `config/config.json` (gitignored). To set up:

1. Copy `config/config.example.json` to `config/config.json`
2. Fill in your paths for `ytdlp_exe`, `ffmpeg_dir`, `audio_output_dir`, `video_output_dir`
3. Leave `ytdlp_exe` blank to auto-download yt-dlp on first run

## yt-dlp binary and docs

- **Binary location:** `dependencies/yt-dlp/yt-dlp.exe` (auto-downloaded on first use)
- **Auto-download:** `python src/download_ytdlp.py` fetches the latest release and updates config
- **yt-dlp repo:** https://github.com/yt-dlp/yt-dlp
- **yt-dlp full docs:** https://github.com/yt-dlp/yt-dlp#readme
- **Releases:** https://github.com/yt-dlp/yt-dlp/releases

## FFmpeg via ffkit

ytkit depends on [ffkit](https://github.com/DavoDC/ffkit) for FFmpeg.
Set `ffmpeg_dir` in `config/config.json` to ffkit's `dependencies/ffmpeg/` folder.

## Output defaults

| Format | Config key | Output |
|--------|-----------|--------|
| audio | `audio_output_dir` | MP3 VBR 0 (highest quality) |
| video | `video_output_dir` | MP4 (best available) |
