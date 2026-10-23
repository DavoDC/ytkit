"""
ytkit CLI - thin wrapper around yt-dlp using config/config.json.
Handles all paths and default flags automatically.

Usage:
  python src/ytkit.py --url <YouTube URL>
  python src/ytkit.py --url <YouTube URL> --format video
  python src/ytkit.py --url <YouTube URL> --format transcript
  python src/ytkit.py --url <any yt-dlp URL> --format info --out-dir <dir>
  python src/ytkit.py --url <any yt-dlp URL> --format frames --out-dir <dir> [--every 3]
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent))
import ytkit_update  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.json"
LOG_PATH = REPO_ROOT / "data" / "logs" / "ytkit.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def load_config():
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found.")
        print("  Copy config/config.example.json to config/config.json and fill in your paths.")
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def ensure_ytdlp(config):
    exe = config.get("ytdlp_exe", "")
    if exe and Path(exe).exists():
        # Stale-while-revalidate: use the current binary now; a detached updater may start after this task.
        try:
            ytkit_update.resolve(exe, defer_to_exit=True)
        except Exception:
            pass
        return config
    print("yt-dlp binary not found - running auto-downloader...")
    dl_script = REPO_ROOT / "src" / "download_ytdlp.py"
    subprocess.run([sys.executable, str(dl_script)], check=True, creationflags=NO_WINDOW)
    return json.loads(CONFIG_PATH.read_text())


def build_command(config, url, mode="audio", out_dir=None, path_file=None):
    ytdlp = config["ytdlp_exe"]
    ffmpeg_dir = config["ffmpeg_dir"]

    if mode == "info":
        return [ytdlp, "--skip-download", "--dump-single-json", "--no-warnings", url]

    # Final file path goes to path_file so progress still streams to the console.
    to_file = ["--print-to-file", "after_move:filepath", str(path_file)] if path_file else []

    if mode == "audio":
        out = f"{config['audio_output_dir']}/%(title)s.%(ext)s"
        return [
            ytdlp,
            *to_file,
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

    if out_dir:
        # Predictable name (id) and the final path printed, so frames mode can find the file.
        out = f"{out_dir}/%(id)s.%(ext)s"
        extra = ["--print", "after_move:filepath"]
    else:
        out = f"{config['video_output_dir']}/%(title)s.%(ext)s"
        extra = to_file
    return [
        ytdlp,
        "--ffmpeg-location", ffmpeg_dir,
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        *extra,
        "-o", out,
        url,
    ]


def format_info(info: dict) -> str:
    """Plain-text summary of yt-dlp metadata: who posted it, caption, stats, top comments."""
    def stat(key):
        value = info.get(key)
        return "unknown" if value is None else value

    lines = [
        f"id: {info.get('id', 'unknown')}",
        f"uploader: {info.get('uploader') or info.get('channel') or 'unknown'}",
        f"upload_date: {stat('upload_date')}",
        f"likes: {stat('like_count')}",
        f"views: {stat('view_count')}",
        f"comments: {stat('comment_count')}",
        "caption:",
        info.get("description") or "(none)",
    ]
    comments = info.get("comments") or []
    if comments:
        lines.append("top comments:")
        lines += [f"- {c.get('author')}: {c.get('text')}" for c in comments[:20]]
    return "\n".join(lines)


def fetch_info(config, url, out_dir: Path):
    """Write <id>.info.json and <id>.info.txt (caption, stats, comments) for url into out_dir.
    Returns the .txt path, or None on failure. Works for any site yt-dlp supports."""
    result = subprocess.run(build_command(config, url, mode="info"), capture_output=True, text=True,
                            creationflags=NO_WINDOW)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return None
    info = json.loads(result.stdout)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = info.get("id") or "info"
    (out_dir / f"{stem}.info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    txt_path = out_dir / f"{stem}.info.txt"
    txt_path.write_text(format_info(info), encoding="utf-8")
    print(format_info(info))
    print(f"Info: {txt_path}")
    return txt_path


def build_frames_command(config, video_path: Path, out_dir: Path, every=3):
    ffmpeg = Path(config["ffmpeg_dir"]) / "ffmpeg.exe"
    return [str(ffmpeg), "-v", "error", "-i", str(video_path),
            "-vf", f"fps=1/{every},scale=540:-1", str(Path(out_dir) / "f%03d.jpg")]


def extract_frames(config, url, out_dir: Path, every=3):
    """Download the video into out_dir and sample a JPEG every `every` seconds into out_dir/frames.
    Returns the frames folder, or None on failure."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(build_command(config, url, mode="video", out_dir=str(out_dir)),
                            capture_output=True, text=True, creationflags=NO_WINDOW)
    printed = [line for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not printed:
        print(result.stderr, file=sys.stderr)
        return None
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    done = subprocess.run(build_frames_command(config, Path(printed[-1]), frames_dir, every),
                          creationflags=NO_WINDOW)
    if done.returncode != 0:
        return None
    print(f"Frames: {frames_dir}")
    return frames_dir


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
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
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


_IG_POST = re.compile(
    r"^(?:https?://)?(?:[\w-]+\.)?(?:instagram\.com|instagr\.am)/"
    r"(?:[\w.]+/)?(reels?|p|tv)/([\w-]+)",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    """Instagram post URLs -> https://www.instagram.com/<kind>/<ID> only.

    Everything after the ID (query, fragment, trailing path) changes often, so is dropped.
    Other URLs pass through unchanged.
    """
    m = _IG_POST.match(url.strip())
    if not m:
        return url
    kind = "reel" if m.group(1).lower() == "reels" else m.group(1).lower()
    return f"https://www.instagram.com/{kind}/{m.group(2)}"


FORMATS = ("audio", "video", "transcript", "info", "frames")
FORMAT_ALIASES = {"a": "audio", "v": "video", "t": "transcript", "i": "info", "f": "frames",
                  "1": "audio", "2": "video", "3": "transcript", "4": "info", "5": "frames"}


def resolve_format(fmt, url: str) -> str:
    """Alias/menu-digit/blank -> a real format; blank or unknown means audio, or video for Instagram."""
    is_ig = bool(_IG_POST.match(url.strip()))
    fmt = (fmt or "").strip().lower()
    fmt = FORMAT_ALIASES.get(fmt, fmt)
    if fmt not in FORMATS:
        fmt = "audio"
    if is_ig and fmt in ("audio", "transcript"):
        if fmt == "transcript":
            print("Instagram reels have no subtitles - downloading video instead.")
        return "video"
    return fmt


def main():
    parser = argparse.ArgumentParser(
        description="ytkit - download audio/video/transcript from YouTube"
    )
    parser.add_argument("--url", required=True, help="YouTube URL")
    parser.add_argument(
        "--format", default="",
        help="audio|video|transcript|info|frames, letter or 1-5 (default: audio as MP3, video for Instagram); info = caption/stats/comments, "
             "frames = video plus a JPEG every --every seconds"
    )
    parser.add_argument("--out-dir", help="Output folder for info/frames (default: video_output_dir)")
    parser.add_argument("--every", type=int, default=3, help="Seconds between frames (frames mode)")
    args = parser.parse_args()
    requested, input_url = args.format, args.url
    args.format = resolve_format(requested, input_url)
    args.url = normalize_url(input_url)

    started = time.time()
    code, out_dir, error = 1, "", ""
    try:
        config = ensure_ytdlp(load_config())
        out_dir = output_dir_for(config, args)
        code = execute(config, args)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    except Exception as e:  # logged, then re-raised so the traceback still shows
        error = f"{type(e).__name__}: {e}"
        write_log(args, input_url, requested, out_dir, code, started, error)
        raise
    write_log(args, input_url, requested, out_dir, code, started, error)
    sys.exit(code)


def output_dir_for(config, args) -> str:
    if args.format == "audio":
        return config["audio_output_dir"]
    if args.format == "transcript":
        return config.get("transcript_output_dir", config["video_output_dir"])
    return args.out_dir or config["video_output_dir"]


def osc8(uri: str, text: str) -> str:
    """OSC 8 hyperlink: Windows Terminal shows `text` as a link, Ctrl+click opens `uri`."""
    esc, st = "\x1b", "\x1b\\"
    return f"{esc}]8;;{uri}{st}{text}{esc}]8;;{st}"


def print_links(folder: Path, file: Path = None):
    """Short clickable links to the output folder and the file; plain URIs when output is piped."""
    def show(label, path):
        path = Path(path).resolve()
        uri = path.as_uri()
        if sys.stdout.isatty():
            print(f"  {label} {osc8(uri, path.name or str(path))}")
        else:
            print(f"{label} {uri}")
    print()
    show("Open folder:", folder)
    if file:
        show("Open file:  ", file)


def execute(config, args) -> int:
    if args.format in ("info", "frames"):
        out_dir = Path(args.out_dir or config["video_output_dir"])
        if args.format == "info":
            result = fetch_info(config, args.url, out_dir)
            if result:
                print_links(out_dir, result)
            return 0 if result else 1
        result = extract_frames(config, args.url, out_dir, args.every)
        if result:
            print_links(result)
        return 0 if result else 1
    if args.format == "transcript":
        result = download_transcript(config, args.url)
        if result:
            print_links(result.parent, result)
        return 0 if result else 1
    path_file = REPO_ROOT / "data" / "state" / "last-download.txt"
    path_file.parent.mkdir(parents=True, exist_ok=True)
    path_file.unlink(missing_ok=True)
    cmd = build_command(config, args.url, mode=args.format, path_file=path_file)
    code = subprocess.run(cmd, creationflags=NO_WINDOW).returncode
    lines = path_file.read_text(encoding="utf-8").splitlines() if path_file.exists() else []
    if code == 0 and lines:
        print_links(Path(lines[-1]).parent, Path(lines[-1]))
    return code


def log_line(input_url, url, requested, fmt, out_dir, code, started, error="") -> str:
    """One key=value line per run: when, what was asked, what ran, where it went, how it ended."""
    host = (urlparse(url if "//" in url else "//" + url).hostname or "?").removeprefix("www.")
    source = "instagram" if _IG_POST.match(url) else host
    parts = [
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started)),
        f"EVENT=run source={source} format={fmt} requested={requested or '(blank)'}",
        f"exit={code} seconds={time.time() - started:.1f}",
        f"out_dir={out_dir or '-'}",
        f"url={url}",
    ]
    if input_url != url:
        parts.append(f"input_url={input_url}")
    if error:
        parts.append(f"error={error}")
    return " ".join(parts)


def write_log(args, input_url, requested, out_dir, code, started, error=""):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(log_line(input_url, args.url, requested, args.format, out_dir, code, started, error) + "\n")
    except OSError:
        pass  # logging must never fail a download


if __name__ == "__main__":
    main()
