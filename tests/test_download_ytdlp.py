import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import download_ytdlp as dl


class FakeResponse:
    def __init__(self, body: bytes, headers: dict):
        self._buf = io.BytesIO(body)
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self._buf.read(n)


def fake_opener(body: bytes, headers: dict):
    return MagicMock(return_value=FakeResponse(body, headers))


class TestFindAssetUrl(unittest.TestCase):
    def test_finds_ytdlp_exe_asset(self):
        data = {"assets": [
            {"name": "yt-dlp", "browser_download_url": "https://example.com/yt-dlp"},
            {"name": "yt-dlp.exe", "browser_download_url": "https://example.com/yt-dlp.exe"},
        ]}
        self.assertEqual(dl.find_asset_url(data), "https://example.com/yt-dlp.exe")

    def test_returns_none_when_asset_missing(self):
        data = {"assets": [{"name": "yt-dlp_linux", "browser_download_url": "https://x.com/linux"}]}
        self.assertIsNone(dl.find_asset_url(data))

    def test_returns_none_on_empty_assets(self):
        self.assertIsNone(dl.find_asset_url({"assets": []}))


class TestBinaryExists(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_true_for_nonempty_file(self):
        exe = self.dir / "yt-dlp.exe"
        exe.write_bytes(b"x")
        self.assertTrue(dl.binary_exists({"ytdlp_exe": str(exe)}))

    def test_false_for_zero_byte_file(self):
        exe = self.dir / "yt-dlp.exe"
        exe.write_bytes(b"")
        self.assertFalse(dl.binary_exists({"ytdlp_exe": str(exe)}))

    def test_false_when_binary_missing(self):
        self.assertFalse(dl.binary_exists({"ytdlp_exe": str(self.dir / "missing.exe")}))

    def test_false_when_config_key_absent(self):
        self.assertFalse(dl.binary_exists({}))

    def test_false_when_ytdlp_exe_empty_string(self):
        self.assertFalse(dl.binary_exists({"ytdlp_exe": ""}))


class TestDownloadBinary(unittest.TestCase):
    URL = "https://example.invalid/yt-dlp.exe"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dest = Path(tmp.name) / "yt-dlp.exe"
        self.staging = self.dest.with_name(self.dest.name + ".new")

    def test_success_replaces_dest_and_leaves_no_staging_file(self):
        content = b"fake-binary-data"
        opener = fake_opener(content, {"Content-Length": str(len(content))})
        result = dl.download_binary(url=self.URL, dest=self.dest, opener=opener)
        self.assertEqual(result, self.dest)
        self.assertEqual(self.dest.read_bytes(), content)
        self.assertFalse(self.staging.exists())
        opener.assert_called_once_with(self.URL, timeout=60)

    def test_size_mismatch_keeps_old_binary(self):
        self.dest.write_bytes(b"old")
        opener = fake_opener(b"partial", {"Content-Length": "100"})
        with self.assertRaises(RuntimeError):
            dl.download_binary(url=self.URL, dest=self.dest, opener=opener)
        self.assertEqual(self.dest.read_bytes(), b"old")
        self.assertFalse(self.staging.exists())

    def test_empty_download_is_rejected(self):
        opener = fake_opener(b"", {})
        with self.assertRaises(RuntimeError):
            dl.download_binary(url=self.URL, dest=self.dest, opener=opener)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.staging.exists())

    def test_missing_content_length_is_still_accepted(self):
        dl.download_binary(url=self.URL, dest=self.dest, opener=fake_opener(b"abc", {}))
        self.assertEqual(self.dest.read_bytes(), b"abc")


class TestUpdateConfig(unittest.TestCase):
    def test_config_updated_with_new_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config = {"ytdlp_exe": "", "ffmpeg_dir": "C:\\ffmpeg"}
            config_path.write_text(json.dumps(config))
            from unittest.mock import patch
            with patch.object(dl, "CONFIG_PATH", config_path):
                dl.update_config(config, Path("C:\\ytkit\\dependencies\\yt-dlp\\yt-dlp.exe"))
            result = json.loads(config_path.read_text())
            self.assertIn("yt-dlp.exe", result["ytdlp_exe"])
            self.assertEqual(result["ffmpeg_dir"], "C:\\ffmpeg")


if __name__ == "__main__":
    unittest.main()
