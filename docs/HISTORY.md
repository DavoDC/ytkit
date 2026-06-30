# ytkit - History

## 2026-06-30 - Repo created

Initial setup. Discovered that yt-dlp without `--ffmpeg-location` pointing to ffkit
produces webm output instead of MP3 (ffmpeg not on PATH). CLAUDE.md now encodes
the full working command so future sessions never hit this again.

First successful download: NTFLX & Drill - Hagrid & Harry [EXTENDED] (MP3).

## 2026-06-30 - Made public, config folder pattern

- Moved hardcoded personal paths to `config/config.json` (gitignored) + `config/config.example.json` (template)
- Made repo public on GitHub
- Cross-referenced with ffkit (both CLAUDE.md files updated)

## 2026-06-30 - Auto-download yt-dlp (P0)

`src/download_ytdlp.py` - checks `config.ytdlp_exe`, downloads from GitHub releases
to `dependencies/yt-dlp/yt-dlp.exe` if missing, updates `config.json`. Stdlib only
(urllib), no pip deps. All tests passing. Claude calls it directly before any
download task if the binary is missing - no human step required.

## 2026-06-30 - NOT_MY_REPOS/yt-dlp retired

`C:\Users\David\GitHubRepos\NOT_MY_REPOS\yt-dlp` was a manual clone of yt-dlp with
a downloaded exe in it. Retired in favour of `src/download_ytdlp.py` auto-downloader
(mirrors ffkit's FFmpeg auto-download pattern). yt-dlp source: https://github.com/yt-dlp/yt-dlp
