import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import ytkit_update as up

HOUR = 3600
NOW = 1_000_000.0


class Fake:
    """Injectable network/process boundary. Records every call, never touches the network."""

    def __init__(self, latest="2026.09.29", installed="2026.01.01", payload=b"NEW-BINARY",
                 download_error=None, smoke=(True, "2026.09.29"), replace_errors=()):
        self.latest = latest
        self.installed = installed
        self.payload = payload
        self.download_error = download_error
        self.smoke_result = smoke
        self.replace_errors = list(replace_errors)
        self.calls = []
        self.spawned = []
        self.clock = NOW

    def deps(self):
        return up.Deps(
            latest_version=self._latest,
            download=self._download,
            smoke=self._smoke,
            installed_version=self._installed,
            replace=self._replace,
            now=lambda: self.clock,
            spawn=self.spawned.append,
        )

    def _latest(self):
        self.calls.append("latest")
        return self.latest

    def _download(self, url, dest):
        self.calls.append("download")
        Path(dest).write_bytes(b"partial")
        if self.download_error:
            raise self.download_error
        Path(dest).write_bytes(self.payload)

    def _smoke(self, path):
        self.calls.append("smoke")
        return self.smoke_result

    def _installed(self, exe):
        self.calls.append("installed")
        return self.installed

    def _replace(self, src, dst):
        self.calls.append("replace")
        if self.replace_errors:
            raise self.replace_errors.pop(0)
        import os
        os.replace(src, dst)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.exe = root / "dependencies" / "yt-dlp" / "yt-dlp.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"OLD-BINARY")
        self.paths = up.Paths.for_exe(self.exe, state_dir=root / "data" / "state", log_dir=root / "data" / "logs")
        self.fake = Fake()

    def write_state(self, **kw):
        self.paths.state.parent.mkdir(parents=True, exist_ok=True)
        self.paths.state.write_text(json.dumps(kw))

    def read_state(self):
        return json.loads(self.paths.state.read_text())


class TestResolve(Base):
    def test_fresh_check_spawns_nothing(self):
        self.write_state(last_check=NOW - HOUR)
        result = up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(result, self.exe)
        self.assertEqual(self.fake.spawned, [])

    def test_stale_check_spawns_background_updater(self):
        self.write_state(last_check=NOW - 25 * HOUR)
        result = up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(result, self.exe)
        self.assertEqual(len(self.fake.spawned), 1)
        argv = self.fake.spawned[0]
        self.assertIn("--run", argv)
        self.assertIn(str(self.exe), argv)

    def test_no_state_file_counts_as_stale(self):
        up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(len(self.fake.spawned), 1)

    def test_corrupt_state_counts_as_stale(self):
        self.paths.state.parent.mkdir(parents=True, exist_ok=True)
        self.paths.state.write_text("{not json")
        up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(len(self.fake.spawned), 1)

    def test_resolve_never_touches_network_or_binary(self):
        self.write_state(last_check=NOW - 100 * HOUR)
        up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(self.fake.calls, [])

    def test_resolve_never_blocks_on_a_hung_network(self):
        hang = threading.Event()
        deps = self.fake.deps()
        deps.latest_version = lambda: hang.wait()
        deps.download = lambda url, dest: hang.wait()
        out = []
        t = threading.Thread(target=lambda: out.append(up.resolve(self.exe, paths=self.paths, deps=deps)), daemon=True)
        t.start()
        t.join(timeout=3)
        hang.set()
        self.assertFalse(t.is_alive(), "resolve blocked")
        self.assertEqual(out, [self.exe])

    def test_resolve_swallows_spawn_failure(self):
        deps = self.fake.deps()

        def boom(argv):
            raise OSError("no process for you")

        deps.spawn = boom
        self.assertEqual(up.resolve(self.exe, paths=self.paths, deps=deps), self.exe)

    def test_resolve_skips_spawn_while_updater_holds_lock(self):
        with up.UpdateLock(self.paths.lock, now=lambda: NOW) as lock:
            self.assertTrue(lock.acquired)
            up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(self.fake.spawned, [])

    def test_pending_swap_retries_after_short_interval_only(self):
        self.write_state(last_check=NOW - 60, pending_swap=True)
        up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(self.fake.spawned, [])
        self.fake.clock = NOW + up.RETRY_INTERVAL_SECONDS + 1
        up.resolve(self.exe, paths=self.paths, deps=self.fake.deps())
        self.assertEqual(len(self.fake.spawned), 1)

    def test_defer_to_exit_registers_atexit_instead_of_spawning(self):
        with patch("ytkit_update.atexit.register") as reg:
            up.resolve(self.exe, paths=self.paths, deps=self.fake.deps(), defer_to_exit=True)
        reg.assert_called_once()
        self.assertEqual(self.fake.spawned, [])


class TestRunUpdate(Base):
    def test_up_to_date_stamps_and_stops(self):
        self.fake.installed = self.fake.latest
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "up_to_date")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertNotIn("download", self.fake.calls)
        self.assertEqual(self.read_state()["last_check"], NOW)

    def test_successful_update_swaps_and_keeps_previous(self):
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "updated")
        self.assertEqual(self.exe.read_bytes(), b"NEW-BINARY")
        self.assertEqual(self.paths.previous.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.paths.new.exists())
        self.assertFalse(self.read_state().get("pending_swap"))

    def test_stamp_is_written_before_the_network_call(self):
        seen = {}
        deps = self.fake.deps()
        real_latest = deps.latest_version

        def spy():
            seen["state"] = self.read_state()
            return real_latest()

        deps.latest_version = spy
        up.run_update(self.paths, deps)
        self.assertEqual(seen["state"]["last_check"], NOW)

    def test_crash_mid_update_does_not_cause_retry_storm(self):
        deps = self.fake.deps()

        def crash():
            raise RuntimeError("boom")

        deps.latest_version = crash
        up.run_update(self.paths, deps)
        self.assertFalse(up.is_stale(up.read_state(self.paths), NOW + HOUR))

    def test_version_check_failure_leaves_binary_alone(self):
        self.fake.latest = None
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "check_failed")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertNotIn("download", self.fake.calls)

    def test_download_failure_leaves_live_binary_untouched(self):
        self.fake.download_error = OSError("connection reset")
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "download_failed")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.paths.new.exists(), "half-written .new must be removed")
        self.assertFalse(self.paths.previous.exists())
        self.assertNotIn("replace", self.fake.calls)

    def test_smoke_failure_leaves_live_binary_untouched(self):
        self.fake.smoke_result = (False, "exit 1")
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "smoke_failed")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.paths.new.exists())
        self.assertNotIn("replace", self.fake.calls)

    def test_locked_exe_keeps_new_and_marks_pending(self):
        self.fake.replace_errors = [PermissionError("in use")]
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "swap_locked")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertEqual(self.paths.new.read_bytes(), b"NEW-BINARY")
        self.assertTrue(self.read_state()["pending_swap"])

    def test_locked_exe_retry_completes_without_redownloading(self):
        self.fake.replace_errors = [PermissionError("in use")]
        up.run_update(self.paths, self.fake.deps())
        self.fake.calls.clear()
        self.fake.clock = NOW + up.RETRY_INTERVAL_SECONDS + 1
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "updated")
        self.assertNotIn("download", self.fake.calls)
        self.assertEqual(self.exe.read_bytes(), b"NEW-BINARY")
        self.assertEqual(self.paths.previous.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.read_state()["pending_swap"])

    def test_retry_with_bad_staged_file_discards_it(self):
        self.fake.replace_errors = [PermissionError("in use")]
        up.run_update(self.paths, self.fake.deps())
        self.fake.smoke_result = (False, "corrupt")
        self.fake.calls.clear()
        self.fake.clock = NOW + up.RETRY_INTERVAL_SECONDS + 1
        up.run_update(self.paths, self.fake.deps())
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.paths.new.exists())

    @unittest.skipUnless(sys.platform == "win32", "real file lock semantics are Windows-specific")
    def test_really_locked_file_on_windows(self):
        deps = self.fake.deps()
        deps.replace = up.os.replace
        with open(self.exe, "r+b"):
            status = up.run_update(self.paths, deps)
        self.assertEqual(status, "swap_locked")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")

    def test_other_swap_error_cleans_up_and_keeps_live(self):
        self.fake.replace_errors = [OSError("disk full")]
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "swap_failed")
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")
        self.assertFalse(self.paths.new.exists())

    def test_concurrent_lock_second_updater_backs_off(self):
        with up.UpdateLock(self.paths.lock, now=lambda: NOW) as held:
            self.assertTrue(held.acquired)
            self.assertEqual(up.run_update(self.paths, self.fake.deps()), "busy")
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.exe.read_bytes(), b"OLD-BINARY")

    def test_lock_is_released_after_run(self):
        up.run_update(self.paths, self.fake.deps())
        self.assertFalse(self.paths.lock.exists())

    def test_lock_is_released_even_on_crash(self):
        deps = self.fake.deps()
        deps.latest_version = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        up.run_update(self.paths, deps)
        self.assertFalse(self.paths.lock.exists())

    def test_stale_lock_from_dead_updater_is_reclaimed(self):
        self.paths.lock.parent.mkdir(parents=True, exist_ok=True)
        self.paths.lock.write_text("123")
        self.fake.clock = NOW
        import os
        os.utime(self.paths.lock, (NOW - 3 * HOUR, NOW - 3 * HOUR))
        with up.UpdateLock(self.paths.lock, now=lambda: NOW) as lock:
            self.assertTrue(lock.acquired)

    def test_two_threads_only_one_gets_the_lock(self):
        results = []
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            with up.UpdateLock(self.paths.lock, now=lambda: NOW) as lock:
                results.append(lock.acquired)
                threading.Event().wait(0.2)

        ts = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(results), [False, True])


class TestDetachedSpawn(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows creation flags")
    def test_windows_uses_detached_flags_and_no_console(self):
        with patch("ytkit_update.subprocess.Popen") as popen:
            up.spawn_detached(["python", "x.py", "--run"])
        kwargs = popen.call_args.kwargs
        flags = kwargs["creationflags"]
        self.assertTrue(flags & subprocess.DETACHED_PROCESS)
        self.assertTrue(flags & subprocess.CREATE_NEW_PROCESS_GROUP)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)

    def test_spawn_does_not_wait_on_the_child(self):
        with patch("ytkit_update.subprocess.Popen") as popen:
            up.spawn_detached(["python", "x.py", "--run"])
        popen.return_value.wait.assert_not_called()
        popen.return_value.communicate.assert_not_called()


class TestCli(Base):
    def test_status_reports_without_side_effects(self):
        self.write_state(last_check=NOW - 30 * HOUR, last_result="up_to_date")
        text = up.format_status(self.paths, self.fake.deps())
        self.assertIn("stale", text)
        self.assertIn("up_to_date", text)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(self.fake.spawned, [])

    def test_status_fresh(self):
        self.write_state(last_check=NOW - HOUR)
        self.assertIn("fresh", up.format_status(self.paths, self.fake.deps()))

    def test_check_starts_updater_only_when_stale(self):
        self.write_state(last_check=NOW - HOUR)
        self.assertEqual(up.check(self.paths, self.fake.deps()), "fresh")
        self.assertEqual(self.fake.spawned, [])
        self.write_state(last_check=NOW - 30 * HOUR)
        self.assertEqual(up.check(self.paths, self.fake.deps()), "started")
        self.assertEqual(len(self.fake.spawned), 1)

    def test_run_force_ignores_freshness(self):
        self.write_state(last_check=NOW - 60)
        self.assertEqual(up.run_update(self.paths, self.fake.deps(), force=True), "updated")

    def test_run_without_force_skips_when_fresh(self):
        self.write_state(last_check=NOW - 60)
        self.assertEqual(up.run_update(self.paths, self.fake.deps()), "fresh")
        self.assertEqual(self.fake.calls, [])


class TestReleaseHelpers(unittest.TestCase):
    def test_tag_is_stripped_of_v_prefix(self):
        self.assertEqual(up.parse_tag({"tag_name": "v2026.09.29"}), "2026.09.29")

    def test_missing_tag_is_none(self):
        self.assertIsNone(up.parse_tag({}))
        self.assertIsNone(up.parse_tag(None))


if __name__ == "__main__":
    unittest.main()
