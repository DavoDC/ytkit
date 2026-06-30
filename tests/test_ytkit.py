import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import ytkit


SAMPLE_CONFIG = {
    "ytdlp_exe": "C:\\ytkit\\dependencies\\yt-dlp\\yt-dlp.exe",
    "ffmpeg_dir": "C:\\ffkit\\dependencies\\ffmpeg",
    "audio_output_dir": "C:\\Downloads\\NewMusic",
    "video_output_dir": "C:\\Downloads",
}


class TestBuildCommand(unittest.TestCase):
    def test_audio_command_has_mp3_flags(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode="audio")
        self.assertIn("--audio-format", cmd)
        self.assertIn("mp3", cmd)
        self.assertIn("--extract-audio", cmd)
        self.assertIn("--audio-quality", cmd)
        self.assertIn("0", cmd)

    def test_audio_command_uses_audio_output_dir(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode="audio")
        out_arg = cmd[cmd.index("-o") + 1]
        self.assertIn("NewMusic", out_arg)

    def test_video_command_uses_video_output_dir(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode="video")
        out_arg = cmd[cmd.index("-o") + 1]
        self.assertIn("C:\\Downloads", out_arg)
        self.assertNotIn("NewMusic", out_arg)

    def test_both_modes_include_ffmpeg_location(self):
        for mode in ("audio", "video"):
            cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode=mode)
            self.assertIn("--ffmpeg-location", cmd)
            self.assertIn("C:\\ffkit\\dependencies\\ffmpeg", cmd)

    def test_url_is_last_arg(self):
        url = "https://youtu.be/test123"
        cmd = ytkit.build_command(SAMPLE_CONFIG, url, mode="audio")
        self.assertEqual(cmd[-1], url)


class TestEnsureYtdlp(unittest.TestCase):
    def test_skips_download_when_binary_exists(self):
        with patch("ytkit.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_cls.return_value = mock_path
            with patch("ytkit.subprocess.run") as mock_run:
                result = ytkit.ensure_ytdlp(SAMPLE_CONFIG)
                mock_run.assert_not_called()
        self.assertEqual(result, SAMPLE_CONFIG)

    def test_triggers_download_when_binary_missing(self):
        config_missing = {**SAMPLE_CONFIG, "ytdlp_exe": ""}
        with patch("ytkit.subprocess.run") as mock_run:
            with patch("ytkit.CONFIG_PATH") as mock_cfg:
                mock_cfg.exists.return_value = True
                mock_cfg.read_text.return_value = json.dumps(SAMPLE_CONFIG)
                ytkit.ensure_ytdlp(config_missing)
                mock_run.assert_called_once()


class TestLoadConfig(unittest.TestCase):
    def test_returns_config_dict(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.json"
            cfg_path.write_text(json.dumps(SAMPLE_CONFIG))
            with patch.object(ytkit, "CONFIG_PATH", cfg_path):
                result = ytkit.load_config()
        self.assertEqual(result["ytdlp_exe"], SAMPLE_CONFIG["ytdlp_exe"])

    def test_exits_when_config_missing(self):
        with patch.object(ytkit, "CONFIG_PATH", Path("/nonexistent/config.json")):
            with self.assertRaises(SystemExit):
                ytkit.load_config()


if __name__ == "__main__":
    unittest.main()
