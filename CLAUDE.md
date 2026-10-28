# ytkit

YouTube download utilities powered by yt-dlp.

## Structure

- `config/` - `config.example.json` (template) and `config.json` (gitignored, your real paths)
- `src/ytkit.py` - CLI wrapper: one command downloads anything, paths handled automatically
- `src/download_ytdlp.py` - auto-downloads yt-dlp binary if missing (download to `<exe>.new`, verified, then swapped in)
- `src/ytkit_update.py` - non-blocking background updater (stale-while-revalidate); `python src/ytkit_update.py --status|--check|--run|--resolve`
- `data/state/` - updater state and lock (gitignored)
- `scripts/` - `ytkit.bat` is the double-click launcher; it runs `ytkit-menu.ps1` (arrow-key format menu), which hands off to `src/ytkit.py`. `clean_transcripts.py` re-cleans existing `.vtt` files.
- `data/logs/` - runtime logs
- Project planning is kept privately by the maintainer, not in this repo (use GitHub issues for requests)

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

**Also handles Instagram reels and any yt-dlp site (not only YouTube):** `--format video`, `--format info` (caption, stats, top comments) and `--format frames` work on `https://www.instagram.com/reel/<ID>/` (strip the query string); `--format transcript` does not (reels have no subtitles). Details in the Instagram reels and Info and frames sections below. ytkit is not YouTube-only; check this file before saying a site is unsupported.

That's it. ytkit reads `config/config.json` and fills in all paths and flags automatically.
No manual path construction. No reading config first. Just run the command.

The wrapper auto-downloads yt-dlp if the binary is missing, then proceeds. When the binary is present it is used at once; if the last update check is over 24 hours old a detached updater runs after the task (download to `yt-dlp.new.exe`, `--version` smoke test, old kept as `yt-dlp.previous.exe`, `os.replace`). Never blocks a task. Tests inject every network/process boundary: `python -m pytest -q`.

## Configuration

All machine-specific paths live in `config/config.json` (gitignored). To set up:

1. Copy `config/config.example.json` to `config/config.json`
2. Fill in your paths for `ytdlp_exe`, `ffmpeg_dir`, `audio_output_dir`, `video_output_dir`, and optionally `transcript_output_dir` (defaults to `video_output_dir`)
3. Leave `ytdlp_exe` blank to auto-download yt-dlp on first run

## yt-dlp binary and docs

- **Binary location:** `dependencies/yt-dlp/yt-dlp.exe` (auto-downloaded on first use)
- **Auto-download:** `python src/download_ytdlp.py` fetches the latest release and updates config
- **yt-dlp repo:** https://github.com/yt-dlp/yt-dlp
- **yt-dlp full docs:** https://github.com/yt-dlp/yt-dlp#readme
- **Releases:** https://github.com/yt-dlp/yt-dlp/releases

## Instagram reels

- Public reels download with the bundled yt-dlp, no login or cookies: `yt-dlp.exe --ffmpeg-location <ffmpeg_dir> -o "%(id)s.%(ext)s" https://www.instagram.com/reel/<ID>/` (strip the query string). Without `--ffmpeg-location` the video and audio streams are not merged.
- `--format transcript` does not work on reels: Instagram has no subtitle tracks. A transcript needs a local whisper pass over the audio: `python scripts/transcribe_whisper.py <video> <out.txt>` (needs `pip install faster-whisper "av==16.1.0"`; av 19 breaks it with a `metadata_errors` TypeError; the script runs on CPU with int8 and the small.en model). Download the video first with `--format video`.
- The title field is useless ("Video by <handle>"); the post caption is in `description`. Use `--format info` for it instead of calling yt-dlp directly (below). Duration prints NA, use ffprobe.
- `ytkit.py --url <reel URL>` accepts Instagram reels for `--format video`, `info` and `frames`.

## Info and frames modes (any site yt-dlp supports)

```bash
python src/ytkit.py --url <URL> --format info --out-dir <dir>
python src/ytkit.py --url <URL> --format frames --out-dir <dir> --every 3
python src/ytkit.py --url <URL> --format frames --out-dir <dir> --sheet
```

`info` writes `<id>.info.json` and `<id>.info.txt` (uploader, caption, likes, views, comment count, top comments) and prints the text. `frames` downloads the video as `<id>.mp4` into `--out-dir` and samples a JPEG every `--every` seconds into `<out-dir>/frames/<id>/` for reading a reel without watching it. Each video gets its own folder, so runs never overwrite each other. `--sheet` writes one tiled contact sheet `<id>_sheet.jpg` (5 by 4 small frames) into the same folder instead of many JPEGs. Both default to `video_output_dir` when `--out-dir` is omitted; pass a scratch folder outside your Downloads folder so nothing lands there. If a task needs something yt-dlp can give that ytkit cannot, extend ytkit with a tested mode, do not call yt-dlp by hand.

## Cutting clips and playlists

- `--start` and `--end` (video and audio) take seconds (`21`) or `minutes:seconds` (`1:05`); omit either side to run to the start or end. ytkit passes them to yt-dlp as `--download-sections` with `--force-keyframes-at-cuts`.
- Audio and video downloads always pass `--no-playlist`, so a URL that also names a playlist downloads only that one video.

## FFmpeg via ffkit

ytkit depends on [ffkit](https://github.com/DavoDC/ffkit) for FFmpeg.
Set `ffmpeg_dir` in `config/config.json` to ffkit's `dependencies/ffmpeg/` folder.

## Output defaults

| Format | Config key | Output |
|--------|-----------|--------|
| audio | `audio_output_dir` | MP3 VBR 0 (highest quality) |
| video | `video_output_dir` | MP4 (best available) |
| transcript | `transcript_output_dir` (falls back to `video_output_dir`) | `.vtt` plus cleaned `.txt` |
