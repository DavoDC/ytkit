"""
ytkit CLI - thin wrapper around yt-dlp using config/config.json.
Handles all paths and default flags automatically.

Usage:
  python src/ytkit.py --url <YouTube URL>
  python src/ytkit.py --url <YouTube URL> --format video
  python src/ytkit.py --url <YouTube URL> --format transcript
"""

import argparse
import json
import re
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

    if mode == "transcript":
        out_dir = config.get("transcript_output_dir", config["video_output_dir"])
        out = f"{out_dir}/%(title)s [%(id)s].%(ext)s"
        return [
            ytdlp,
            "--skip-download",
            "--write-sub", "--write-auto-sub",
            "--sub-lang", "en.*",
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


def clean_vtt(vtt_path: Path) -> str:
    """Strip VTT timestamps/tags and collapse the duplicate-line rolling-caption
    format auto-subs use into plain, deduplicated transcript text."""
    lines = vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")) or "-->" in line:
            continue
        text = re.sub(r"<[^>]+>", "", line).strip()
        if text and (not out or out[-1] != text):
            out.append(text)
    return " ".join(out)


def download_transcript(config, url):
    """Download auto/manual English subs for url, clean to plain text, write a
    .txt next to the .vtt files. Returns the path to the cleaned .txt, or None."""
    cmd = build_command(config, url, mode="transcript")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return None

    out_dir = Path(config.get("transcript_output_dir", config["video_output_dir"]))
    video_id_match = re.search(r"(?:v=|youtu\.be/)([\w-]+)", url)
    video_id = video_id_match.group(1) if video_id_match else None
    if not video_id:
        return None

    candidates = sorted(out_dir.glob(f"*[{video_id}]*.vtt"))
    # Prefer the non-"-orig" file (yt-dlp's cleaned auto-caption track) if both exist.
    preferred = [c for c in candidates if "-orig" not in c.name]
    vtt_path = (preferred or candidates or [None])[0]
    if not vtt_path:
        print(f"[WARN] No .vtt found for {url}")
        return None

    cleaned = clean_vtt(vtt_path)
    txt_path = vtt_path.with_suffix("").with_suffix(".txt")
    txt_path.write_text(cleaned, encoding="utf-8")
    print(f"Transcript: {txt_path}")
    return txt_path


def main():
    parser = argparse.ArgumentParser(
        description="ytkit - download audio/video/transcript from YouTube"
    )
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument(
        "--format", choices=["audio", "video", "transcript"], default="audio",
        help="Output format (default: audio as MP3)"
    )
    args = parser.parse_args()

    config = load_config()
    config = ensure_ytdlp(config)

    if args.format == "transcript":
        sys.exit(0 if download_transcript(config, args.url) else 1)

    cmd = build_command(config, args.url, mode=args.format)
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
