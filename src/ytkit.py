"""
ytkit CLI - thin wrapper around yt-dlp using config/config.json.
Handles all paths and default flags automatically.

Usage:
  python src/ytkit.py --url <YouTube URL>
  python src/ytkit.py --url <YouTube URL> --format video
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.json"


def load_config():
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found.")
        print("  Copy config/config.example.json to config/config.json and fill in your paths.")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def ensure_ytdlp(config):
    exe = config.get("ytdlp_exe", "")
    if exe and Path(exe).exists():
        return config
    print("yt-dlp binary not found - running auto-downloader...")
    dl_script = REPO_ROOT / "src" / "download_ytdlp.py"
    subprocess.run([sys.executable, str(dl_script)], check=True)
    return json.loads(CONFIG_PATH.read_text())


def build_command(config, url, mode="audio"):
    ytdlp = config["ytdlp_exe"]
    ffmpeg_dir = config["ffmpeg_dir"]

    if mode == "audio":
        out = f"{config['audio_output_dir']}/%(title)s.%(ext)s"
        return [
            ytdlp,
            "--ffmpeg-location", ffmpeg_dir,
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", out,
            url,
        ]

    out = f"{config['video_output_dir']}/%(title)s.%(ext)s"
    return [
        ytdlp,
        "--ffmpeg-location", ffmpeg_dir,
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        "-o", out,
        url,
    ]


def main():
    parser = argparse.ArgumentParser(
        description="ytkit - download audio/video from YouTube"
    )
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument(
        "--format", choices=["audio", "video"], default="audio",
        help="Output format (default: audio as MP3)"
    )
    args = parser.parse_args()

    config = load_config()
    config = ensure_ytdlp(config)
    cmd = build_command(config, args.url, mode=args.format)
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
