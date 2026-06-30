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
        pass

    def test_audio_command_uses_audio_output_dir(self):
        pass

    def test_video_command_uses_video_output_dir(self):
        pass

    def test_both_modes_include_ffmpeg_location(self):
        pass


class TestEnsureYtdlp(unittest.TestCase):
    def test_skips_download_when_binary_exists(self):
        pass

    def test_triggers_download_when_binary_missing(self):
        pass


class TestLoadConfig(unittest.TestCase):
    def test_returns_config_dict(self):
        pass

    def test_exits_when_config_missing(self):
        pass


if __name__ == "__main__":
    unittest.main()
