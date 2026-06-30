# ytkit

YouTube download utilities powered by yt-dlp.

## Structure

- `config/` - `config.example.json` (template) and `config.json` (gitignored, your real paths)
- `src/ytkit.py` - CLI wrapper: one command downloads anything, paths handled automatically
- `src/download_ytdlp.py` - auto-downloads yt-dlp binary if missing
- `scripts/` - launchers (future)
- `data/logs/` - runtime logs
- `docs/IDEAS.md` - pending work
- `docs/HISTORY.md` - completed work

## How to download (Claude instructions)

**Audio (default - MP3 highest quality):**
```bash
python src/ytkit.py --url <YouTube URL>
```

**Video:**
```bash
python src/ytkit.py --url <YouTube URL> --format video
```

That's it. ytkit reads `config/config.json` and fills in all paths and flags automatically.
No manual path construction. No reading config first. Just run the command.

The wrapper auto-downloads yt-dlp if the binary is missing, then proceeds.

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
