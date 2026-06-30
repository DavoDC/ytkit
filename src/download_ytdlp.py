"""
Auto-downloads yt-dlp.exe if not present at the path in config/config.json.
Updates config.json with the new path after download.
Usage: python src/download_ytdlp.py
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.json"
DEST_DIR = REPO_ROOT / "dependencies" / "yt-dlp"
DEST_EXE = DEST_DIR / "yt-dlp.exe"
DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


def load_config():
    if not CONFIG_PATH.exists():
        print(f"[ERROR] config.json not found at {CONFIG_PATH}")
        print("  Copy config/config.example.json to config/config.json and fill in your paths.")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def binary_exists(config):
    exe = config.get("ytdlp_exe", "")
    return bool(exe) and Path(exe).exists()


def find_asset_url(release_data):
    for asset in release_data.get("assets", []):
        if asset.get("name") == "yt-dlp.exe":
            return asset.get("browser_download_url")
    return None


def download_binary(url=DOWNLOAD_URL, dest=DEST_EXE):
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading yt-dlp.exe from {url}")
    start = time.time()
    with urllib.request.urlopen(url) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  {pct}% ({downloaded // 1024}KB / {total // 1024}KB)", end="", flush=True)
    elapsed = time.time() - start
    if total:
        print()
    print(f"  Done in {elapsed:.1f}s -> {dest}")
    return Path(dest)


def update_config(config, exe_path):
    config["ytdlp_exe"] = str(exe_path)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"config.json updated: ytdlp_exe = {exe_path}")


def main():
    start = time.time()
    print("=== ytkit: yt-dlp auto-downloader ===")

    config = load_config()

    if binary_exists(config):
        print(f"yt-dlp already present: {config['ytdlp_exe']}")
        return

    print(f"yt-dlp not found at: {config.get('ytdlp_exe') or '(not set)'}")
    exe_path = download_binary()
    update_config(config, exe_path)

    print(f"\n=== Complete in {time.time() - start:.1f}s ===")


if __name__ == "__main__":
    main()
