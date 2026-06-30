import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import download_ytdlp as dl


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
    def test_returns_true_when_binary_exists(self):
        with patch("download_ytdlp.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_cls.return_value = mock_path
            config = {"ytdlp_exe": "C:\\some\\yt-dlp.exe"}
            self.assertTrue(dl.binary_exists(config))

    def test_returns_false_when_binary_missing(self):
        with patch("download_ytdlp.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path
            config = {"ytdlp_exe": "C:\\missing\\yt-dlp.exe"}
            self.assertFalse(dl.binary_exists(config))

    def test_returns_false_when_config_key_absent(self):
        self.assertFalse(dl.binary_exists({}))

    def test_returns_false_when_ytdlp_exe_empty_string(self):
        self.assertFalse(dl.binary_exists({"ytdlp_exe": ""}))


class TestDownloadBinary(unittest.TestCase):
    def _make_mock_response(self, content=b"fake-exe-content", content_length="16"):
        mock_response = MagicMock()
        mock_response.headers.get.return_value = content_length
        mock_response.read.side_effect = [content, b""]
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    def test_download_creates_file_at_dest(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "yt-dlp.exe"
            mock_response = self._make_mock_response()
            with patch("urllib.request.urlopen", return_value=mock_response):
                with patch.object(dl, "DEST_DIR", Path(tmp)):
                    result = dl.download_binary(url="https://fake.url", dest=dest)
            self.assertTrue(dest.exists())
            self.assertEqual(result, dest)

    def test_download_file_has_correct_content(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "yt-dlp.exe"
            content = b"fake-binary-data"
            mock_response = self._make_mock_response(content=content, content_length="0")
            with patch("urllib.request.urlopen", return_value=mock_response):
                with patch.object(dl, "DEST_DIR", Path(tmp)):
                    dl.download_binary(url="https://fake.url", dest=dest)
            self.assertEqual(dest.read_bytes(), content)


class TestUpdateConfig(unittest.TestCase):
    def test_config_updated_with_new_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config = {"ytdlp_exe": "", "ffmpeg_dir": "C:\\ffmpeg"}
            config_path.write_text(json.dumps(config))
            with patch.object(dl, "CONFIG_PATH", config_path):
                dl.update_config(config, Path("C:\\ytkit\\dependencies\\yt-dlp\\yt-dlp.exe"))
            result = json.loads(config_path.read_text())
            self.assertIn("yt-dlp.exe", result["ytdlp_exe"])
            self.assertEqual(result["ffmpeg_dir"], "C:\\ffmpeg")


if __name__ == "__main__":
    unittest.main()
