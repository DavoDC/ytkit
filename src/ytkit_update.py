"""
Non-blocking background updater for the yt-dlp binary (stale-while-revalidate).

resolve() returns the current binary at once and never touches the network. When the last check is more than 24
hours old it starts a detached updater process. The updater downloads to yt-dlp.new.exe, runs a --version smoke
test, keeps the old binary as yt-dlp.previous.exe, then swaps with os.replace. A failed download or smoke test
never touches the live binary. If the exe is locked (Windows, in use) the staged file is kept and the swap is
retried later.

Usage:
  python src/ytkit_update.py --resolve   print the binary path and trigger a background update if stale
  python src/ytkit_update.py --status    show last check, staleness and pending state (no side effects)
  python src/ytkit_update.py --check     start the background updater if stale (does not wait)
  python src/ytkit_update.py --run       run the updater in the foreground (add --force to skip the 24h rule)
"""

import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.json"
DEFAULT_EXE = REPO_ROOT / "dependencies" / "yt-dlp" / "yt-dlp.exe"
STATE_DIR = REPO_ROOT / "data" / "state"
LOG_DIR = REPO_ROOT / "data" / "logs"

CHECK_INTERVAL_SECONDS = 24 * 3600
RETRY_INTERVAL_SECONDS = 15 * 60
LOCK_STALE_SECONDS = 3600

RELEASE_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
USER_AGENT = "ytkit-updater"


@dataclass
class Paths:
    exe: Path
    new: Path
    previous: Path
    state: Path
    lock: Path
    log: Path

    @classmethod
    def for_exe(cls, exe, state_dir=STATE_DIR, log_dir=LOG_DIR):
        exe = Path(exe)
        return cls(
            exe=exe,
            new=exe.with_name(f"{exe.stem}.new{exe.suffix}"),
            previous=exe.with_name(f"{exe.stem}.previous{exe.suffix}"),
            state=Path(state_dir) / "ytkit_update_check.json",
            lock=Path(state_dir) / "ytkit_update.lock",
            log=Path(log_dir) / "ytkit_update.log",
        )


@dataclass
class Deps:
    """Every network and process boundary. Tests inject fakes; nothing else touches the outside world."""
    latest_version: Callable[[], Optional[str]]
    download: Callable[[str, Path], None]
    smoke: Callable[[Path], tuple]
    installed_version: Callable[[Path], Optional[str]]
    replace: Callable[[Path, Path], None]
    now: Callable[[], float]
    spawn: Callable[[list], None]


# ---------------------------------------------------------------- real boundaries

def parse_tag(release):
    tag = (release or {}).get("tag_name", "")
    return tag.lstrip("v") or None


def fetch_latest_version():
    """Latest release tag from GitHub, or None on any failure."""
    try:
        req = urllib.request.Request(
            RELEASE_API_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return parse_tag(json.loads(resp.read().decode("utf-8")))
    except Exception:
        return None


def download_file(url, dest):
    """Stream url to dest. Raises on network error or a size mismatch (truncated download)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as resp:
        expected = int(resp.headers.get("Content-Length") or 0)
        written = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                written += len(chunk)
    if expected and written != expected:
        raise IOError(f"truncated download: got {written} of {expected} bytes")


def _quiet_flags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def smoke_test(path):
    """(ok, detail): the file runs --version with exit 0 and prints a version."""
    try:
        result = subprocess.run([str(path), "--version"], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=30, creationflags=_quiet_flags())
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    version = (result.stdout or "").strip()
    if result.returncode != 0 or not version:
        return False, f"exit {result.returncode}, output {version[:80]!r}"
    return True, version


def installed_version(exe):
    if not Path(exe).exists():
        return None
    ok, detail = smoke_test(exe)
    return detail if ok else None


def spawn_detached(argv):
    """Start argv as a fully detached process (no console window, not waited on)."""
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)


def real_deps():
    return Deps(latest_version=fetch_latest_version, download=download_file, smoke=smoke_test,
                installed_version=installed_version, replace=os.replace, now=time.time, spawn=spawn_detached)


def _background_python():
    """pythonw.exe (no console) beside the running interpreter when present."""
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return str(pythonw) if sys.platform == "win32" and pythonw.exists() else str(exe)


def updater_argv(exe):
    return [_background_python(), str(Path(__file__).resolve()), "--run", "--exe", str(exe)]


# ---------------------------------------------------------------- state, lock, log

def read_state(paths):
    try:
        data = json.loads(paths.state.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(paths, state):
    """Atomic write: a crash never leaves a half-written state file."""
    paths.state.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.state.with_name(paths.state.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, paths.state)


def log(paths, message, now=time.time):
    try:
        paths.log.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now()))
        with open(paths.log, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {message}\n")
    except Exception:
        pass


def is_stale(state, now):
    last = state.get("last_check")
    if not isinstance(last, (int, float)) or isinstance(last, bool):
        return True
    age = now - last
    if age < 0:
        return True
    if state.get("pending_swap"):
        return age >= RETRY_INTERVAL_SECONDS
    return age >= CHECK_INTERVAL_SECONDS


class UpdateLock:
    """Single-instance lock: exclusive create of a lock file. A lock older than an hour is from a dead updater."""

    def __init__(self, path, now=time.time):
        self.path = Path(path)
        self.now = now
        self.acquired = False

    def _try_create(self):
        fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode())
        finally:
            os.close(fd)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._try_create()
            self.acquired = True
        except FileExistsError:
            try:
                age = self.now() - self.path.stat().st_mtime
            except OSError:
                age = 0
            if age > LOCK_STALE_SECONDS:
                try:
                    self.path.unlink()
                    self._try_create()
                    self.acquired = True
                except OSError:
                    self.acquired = False
        return self

    def __exit__(self, *exc):
        if self.acquired:
            try:
                self.path.unlink()
            except OSError:
                pass
        self.acquired = False
        return False


def lock_held(paths, now):
    try:
        return (now - paths.lock.stat().st_mtime) <= LOCK_STALE_SECONDS
    except OSError:
        return False


# ---------------------------------------------------------------- resolve (the fast path)

def _maybe_spawn(paths, deps):
    try:
        if is_stale(read_state(paths), deps.now()) and not lock_held(paths, deps.now()):
            deps.spawn(updater_argv(paths.exe))
            return True
    except Exception as exc:
        log(paths, f"EVENT=spawn_failed error={exc!r}")
    return False


def resolve(exe=None, paths=None, deps=None, defer_to_exit=False):
    """Return the current yt-dlp path at once. Never checks the network, never blocks.
    If the last check is stale, a detached updater is started (or, with defer_to_exit, at interpreter exit so the
    running task is never slowed)."""
    exe = Path(exe) if exe else configured_exe()
    paths = paths or Paths.for_exe(exe)
    deps = deps or real_deps()
    if defer_to_exit:
        atexit.register(_maybe_spawn, paths, deps)
    else:
        _maybe_spawn(paths, deps)
    return exe


def configured_exe():
    try:
        exe = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("ytdlp_exe", "")
        if exe and Path(exe).exists():
            return Path(exe)
    except (OSError, ValueError):
        pass
    return DEFAULT_EXE


# ---------------------------------------------------------------- the updater (runs detached)

def _remove(path):
    try:
        Path(path).unlink()
    except OSError:
        pass


def _swap_in(paths, deps):
    """Keep the old binary as .previous, then one os.replace. Returns 'updated', 'swap_locked' or 'swap_failed'."""
    try:
        if paths.exe.exists():
            shutil.copy2(paths.exe, paths.previous)
        deps.replace(paths.new, paths.exe)
        return "updated"
    except PermissionError as exc:
        log(paths, f"EVENT=swap_locked error={exc!r} kept={paths.exe.name}", deps.now)
        return "swap_locked"
    except Exception as exc:
        log(paths, f"EVENT=swap_failed error={exc!r} kept={paths.exe.name}", deps.now)
        _remove(paths.new)
        return "swap_failed"


def run_update(paths, deps, force=False):
    """One update attempt. Returns a status string; never raises."""
    with UpdateLock(paths.lock, now=deps.now) as lock:
        if not lock.acquired:
            return "busy"
        try:
            state = read_state(paths)
            now = deps.now()
            if not force and not is_stale(state, now):
                return "fresh"
            pending = bool(state.get("pending_swap")) and paths.new.exists()
            # Stamp BEFORE any network call so a crash cannot cause a retry storm.
            state.update(last_check=now, pending_swap=pending)
            write_state(paths, state)

            if pending:
                status = _finish_staged(paths, deps, state)
            else:
                status = _fetch_and_stage(paths, deps, state)
            state["last_result"] = status
            state["pending_swap"] = status == "swap_locked"
            write_state(paths, state)
            log(paths, f"EVENT=update_result status={status}", deps.now)
            return status
        except Exception as exc:
            log(paths, f"EVENT=update_error error={exc!r}", deps.now)
            return "error"


def _finish_staged(paths, deps, state):
    ok, detail = deps.smoke(paths.new)
    if not ok:
        log(paths, f"EVENT=update_rejected reason={'staged smoke test failed ' + detail!r}", deps.now)
        _remove(paths.new)
        return "smoke_failed"
    return _swap_in(paths, deps)


def _fetch_and_stage(paths, deps, state):
    latest = deps.latest_version()
    if not latest:
        return "check_failed"
    current = deps.installed_version(paths.exe)
    state.update(latest=latest, current=current)
    if current == latest:
        return "up_to_date"
    try:
        deps.download(DOWNLOAD_URL, paths.new)
    except Exception as exc:
        log(paths, f"EVENT=update_rejected reason={'download failed ' + repr(exc)!r} kept={paths.exe.name}", deps.now)
        _remove(paths.new)
        return "download_failed"
    ok, detail = deps.smoke(paths.new)
    if not ok:
        log(paths, f"EVENT=update_rejected reason={'smoke test failed ' + detail!r} kept={paths.exe.name}", deps.now)
        _remove(paths.new)
        return "smoke_failed"
    status = _swap_in(paths, deps)
    if status == "updated":
        state["current"] = latest
        log(paths, f"EVENT=updated from={current} to={latest} previous={paths.previous.name}", deps.now)
    return status


# ---------------------------------------------------------------- CLI

def check(paths, deps):
    """Start the background updater if stale. Returns 'started' or 'fresh'."""
    return "started" if _maybe_spawn(paths, deps) else "fresh"


def format_status(paths, deps):
    state = read_state(paths)
    now = deps.now()
    last = state.get("last_check")
    lines = [f"binary:       {paths.exe} ({'present' if paths.exe.exists() else 'missing'})"]
    if isinstance(last, (int, float)):
        lines.append(f"last check:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last))} "
                     f"({(now - last) / 3600:.1f}h ago)")
    else:
        lines.append("last check:   never")
    lines.append(f"state:        {'stale (an update check is due)' if is_stale(state, now) else 'fresh'}")
    lines.append(f"last result:  {state.get('last_result', 'none')}")
    lines.append(f"pending swap: {'yes (staged file waiting for the exe to be free)' if state.get('pending_swap') else 'no'}")
    lines.append(f"previous:     {'kept' if paths.previous.exists() else 'none'}")
    lines.append(f"updater:      {'running' if lock_held(paths, now) else 'idle'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="ytkit - background yt-dlp updater")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--resolve", action="store_true", help="print the binary path, trigger update if stale")
    mode.add_argument("--status", action="store_true", help="show update state, no side effects")
    mode.add_argument("--check", action="store_true", help="start the background updater if stale")
    mode.add_argument("--run", action="store_true", help="run the updater in the foreground")
    parser.add_argument("--force", action="store_true", help="with --run: ignore the 24 hour rule")
    parser.add_argument("--exe", help="binary to manage (default: config ytdlp_exe or dependencies/yt-dlp)")
    args = parser.parse_args(argv)

    exe = Path(args.exe) if args.exe else configured_exe()
    paths = Paths.for_exe(exe)
    deps = real_deps()

    if args.resolve:
        print(resolve(exe, paths, deps))
    elif args.status:
        print(format_status(paths, deps))
    elif args.check:
        print(check(paths, deps))
    else:
        print(run_update(paths, deps, force=args.force))
    return 0


if __name__ == "__main__":
    sys.exit(main())
