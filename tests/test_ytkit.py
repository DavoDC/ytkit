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


class TestNormalizeUrl(unittest.TestCase):
    ID = "Dbs7zZTyCSf"
    WANT = f"https://www.instagram.com/reel/{ID}"

    def test_instagram_forms_reduce_to_id(self):
        forms = [
            f"https://www.instagram.com/reel/{self.ID}/?vrfl=cWJ2bHg4aHF3Yzho",
            f"https://www.instagram.com/reel/{self.ID}/?igsh=abc&utm_source=x#frag",
            f"https://www.instagram.com/reel/{self.ID}",
            f"https://instagram.com/reel/{self.ID}/",
            f"http://m.instagram.com/reels/{self.ID}/?x=1",
            f"https://www.instagram.com/someuser/reel/{self.ID}/?hl=en",
            f"https://www.instagram.com/reel/{self.ID}/embed/captioned",
            f"instagram.com/reel/{self.ID}/?x",
            f"  https://www.instagram.com/reel/{self.ID}/?x  ",
        ]
        for form in forms:
            self.assertEqual(ytkit.normalize_url(form), self.WANT, form)

    def test_post_kinds_kept(self):
        self.assertEqual(ytkit.normalize_url("https://www.instagram.com/p/AbC_-1/?x=1"),
                         "https://www.instagram.com/p/AbC_-1")

    def test_other_urls_unchanged(self):
        for url in ("https://youtu.be/abc?t=5", "https://www.youtube.com/watch?v=abc&list=x"):
            self.assertEqual(ytkit.normalize_url(url), url)


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
            with patch("ytkit.subprocess.run") as mock_run, patch("ytkit.ytkit_update.resolve"):
                result = ytkit.ensure_ytdlp(SAMPLE_CONFIG)
                mock_run.assert_not_called()
        self.assertEqual(result, SAMPLE_CONFIG)

    def test_present_binary_hands_off_to_background_updater_after_task(self):
        with patch("ytkit.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            with patch("ytkit.ytkit_update.resolve") as mock_resolve:
                ytkit.ensure_ytdlp(SAMPLE_CONFIG)
        mock_resolve.assert_called_once()
        self.assertTrue(mock_resolve.call_args.kwargs.get("defer_to_exit"))

    def test_updater_failure_never_breaks_a_task(self):
        with patch("ytkit.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            with patch("ytkit.ytkit_update.resolve", side_effect=RuntimeError("boom")):
                result = ytkit.ensure_ytdlp(SAMPLE_CONFIG)
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


SAMPLE_INFO = {
    "id": "DboG_LfRkYd",
    "uploader": "JustSaySteven",
    "description": "Indie Developer Made $360,000 in 24 hours",
    "like_count": 5993,
    "view_count": None,
    "comment_count": 50,
    "upload_date": "20260804",
    "comments": [{"author": "a", "text": "Less is more"}],
}


class TestInfoMode(unittest.TestCase):
    def test_info_command_skips_download_and_dumps_json(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://www.instagram.com/reel/x/", mode="info")
        self.assertIn("--skip-download", cmd)
        self.assertIn("--dump-single-json", cmd)
        self.assertEqual(cmd[-1], "https://www.instagram.com/reel/x/")

    def test_format_info_has_caption_stats_and_comments(self):
        text = ytkit.format_info(SAMPLE_INFO)
        self.assertIn("JustSaySteven", text)
        self.assertIn("Indie Developer Made $360,000 in 24 hours", text)
        self.assertIn("likes: 5993", text)
        self.assertIn("Less is more", text)

    def test_format_info_tolerates_missing_fields(self):
        self.assertIn("views: unknown", ytkit.format_info({"id": "x"}))

    def test_fetch_info_writes_json_and_txt(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=0, stdout=json.dumps(SAMPLE_INFO), stderr="")
            with patch("ytkit.subprocess.run", return_value=fake):
                txt = ytkit.fetch_info(SAMPLE_CONFIG, "https://x/", Path(tmp))
            self.assertTrue((Path(tmp) / "DboG_LfRkYd.info.json").exists())
            self.assertIn("likes: 5993", txt.read_text(encoding="utf-8"))

    def test_fetch_info_returns_none_on_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=1, stdout="", stderr="boom")
            with patch("ytkit.subprocess.run", return_value=fake):
                self.assertIsNone(ytkit.fetch_info(SAMPLE_CONFIG, "https://x/", Path(tmp)))


class TestFramesMode(unittest.TestCase):
    def test_frames_command_samples_every_n_seconds(self):
        cmd = ytkit.build_frames_command(SAMPLE_CONFIG, Path("v.mp4"), Path("out"), every=3)
        self.assertTrue(cmd[0].endswith("ffmpeg.exe") or cmd[0].endswith("ffmpeg"))
        self.assertIn("fps=1/3,scale=540:-1", cmd)
        self.assertTrue(cmd[-1].endswith("f%03d.jpg"))

    def test_video_command_honours_out_dir(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://x/", mode="video", out_dir="D:\\TEMP\\x")
        self.assertIn("D:\\TEMP\\x", cmd[cmd.index("-o") + 1])
        self.assertIn("after_move:filepath", cmd)


if __name__ == "__main__":
    unittest.main()
