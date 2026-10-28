import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import ytkit


SAMPLE_CONFIG = {
    "ytdlp_exe": "tools/yt-dlp/yt-dlp.exe",
    "ffmpeg_dir": "tools/ffmpeg",
    "audio_output_dir": "out/NewMusic",
    "video_output_dir": "out/Downloads",
}

SYNTH_ID = "AAAAAAAAAAA"
SYNTH_REEL = f"https://www.instagram.com/reel/{SYNTH_ID}"


def _value(cmd, flag):
    return cmd[cmd.index(flag) + 1]


class TestNormalizeUrl(unittest.TestCase):
    ID = SYNTH_ID
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


class TestLogLine(unittest.TestCase):
    def test_instagram_line_has_all_details(self):
        line = ytkit.log_line("https://www.instagram.com/reel/AbC/?x=1", "https://www.instagram.com/reel/AbC",
                              "", "video", os.path.join("out", "Downloads"), 0, 0.0)
        for want in ("EVENT=run", "source=instagram", "format=video", "requested=(blank)", "exit=0",
                     f"out_dir={os.path.join('out', 'Downloads')}", "url=https://www.instagram.com/reel/AbC",
                     "input_url=https://www.instagram.com/reel/AbC/?x=1"):
            self.assertIn(want, line)

    def test_youtube_source_and_error(self):
        line = ytkit.log_line("https://www.youtube.com/watch?v=a", "https://www.youtube.com/watch?v=a",
                              "t", "transcript", "", 1, 0.0, "RuntimeError: boom")
        self.assertIn("source=youtube.com", line)
        self.assertNotIn("input_url=", line)
        self.assertIn("error=RuntimeError: boom", line)


class TestResolveFormat(unittest.TestCase):
    YT = "https://youtu.be/abc"
    IG = f"{SYNTH_REEL}/?x=1"

    def test_defaults_and_aliases(self):
        self.assertEqual(ytkit.resolve_format("", self.YT), "audio")
        self.assertEqual(ytkit.resolve_format("junk", self.YT), "audio")
        self.assertEqual(ytkit.resolve_format("V", self.YT), "video")
        self.assertEqual(ytkit.resolve_format("3", self.YT), "transcript")
        self.assertEqual(ytkit.resolve_format("frames", self.YT), "frames")

    def test_instagram_defaults_to_video(self):
        self.assertEqual(ytkit.resolve_format("", self.IG), "video")
        self.assertEqual(ytkit.resolve_format("audio", self.IG), "video")
        self.assertEqual(ytkit.resolve_format("t", self.IG), "video")
        self.assertEqual(ytkit.resolve_format("info", self.IG), "info")


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
        self.assertIn("Downloads", out_arg)
        self.assertNotIn("NewMusic", out_arg)

    def test_both_modes_include_ffmpeg_location(self):
        for mode in ("audio", "video"):
            cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode=mode)
            self.assertIn("--ffmpeg-location", cmd)
            self.assertIn(SAMPLE_CONFIG["ffmpeg_dir"], cmd)

    def test_audio_and_video_skip_playlists(self):
        for mode in ("audio", "video"):
            cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/test", mode=mode)
            self.assertIn("--no-playlist", cmd, mode)

    def test_url_is_last_arg(self):
        url = "https://youtu.be/test123"
        cmd = ytkit.build_command(SAMPLE_CONFIG, url, mode="audio")
        self.assertEqual(cmd[-1], url)


class TestSections(unittest.TestCase):
    URL = "https://youtu.be/t"

    def build(self, mode, **kwargs):
        return ytkit.build_command(SAMPLE_CONFIG, self.URL, mode=mode, **kwargs)

    def test_no_sections_by_default(self):
        for mode in ("audio", "video"):
            cmd = self.build(mode)
            self.assertNotIn("--download-sections", cmd, mode)
            self.assertNotIn("--force-keyframes-at-cuts", cmd, mode)

    def test_start_and_end_cut_the_range(self):
        cmd = self.build("video", start="1:05", end="2:00")
        self.assertEqual(_value(cmd, "--download-sections"), "*1:05-2:00")
        self.assertIn("--force-keyframes-at-cuts", cmd)

    def test_start_only_runs_to_end_of_video(self):
        self.assertEqual(_value(self.build("video", start="21"), "--download-sections"), "*21-inf")

    def test_end_only_starts_at_zero(self):
        self.assertEqual(_value(self.build("video", end="30"), "--download-sections"), "*0-30")

    def test_audio_gets_the_same_sections(self):
        cmd = self.build("audio", start="21", end="45")
        self.assertEqual(_value(cmd, "--download-sections"), "*21-45")
        self.assertIn("--force-keyframes-at-cuts", cmd)


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
    "id": SYNTH_ID,
    "uploader": "example_user",
    "description": "Example caption text",
    "like_count": 5993,
    "view_count": None,
    "comment_count": 50,
    "upload_date": "20260101",
    "comments": [{"author": "a", "text": "Example comment"}],
}


class TestInfoMode(unittest.TestCase):
    def test_info_command_skips_download_and_dumps_json(self):
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://www.instagram.com/reel/x/", mode="info")
        self.assertIn("--skip-download", cmd)
        self.assertIn("--dump-single-json", cmd)
        self.assertEqual(cmd[-1], "https://www.instagram.com/reel/x/")

    def test_format_info_has_caption_stats_and_comments(self):
        text = ytkit.format_info(SAMPLE_INFO)
        self.assertIn("example_user", text)
        self.assertIn("Example caption text", text)
        self.assertIn("likes: 5993", text)
        self.assertIn("Example comment", text)

    def test_format_info_tolerates_missing_fields(self):
        self.assertIn("views: unknown", ytkit.format_info({"id": "x"}))

    def test_fetch_info_writes_json_and_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=0, stdout=json.dumps(SAMPLE_INFO), stderr="")
            with patch("ytkit.subprocess.run", return_value=fake):
                txt = ytkit.fetch_info(SAMPLE_CONFIG, "https://x/", Path(tmp))
            self.assertTrue((Path(tmp) / f"{SYNTH_ID}.info.json").exists())
            self.assertIn("likes: 5993", txt.read_text(encoding="utf-8"))

    def test_fetch_info_returns_none_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=1, stdout="", stderr="boom")
            with patch("ytkit.subprocess.run", return_value=fake):
                self.assertIsNone(ytkit.fetch_info(SAMPLE_CONFIG, "https://x/", Path(tmp)))


class TestFramesMode(unittest.TestCase):
    def test_frames_command_samples_every_n_seconds(self):
        cmd = ytkit.build_frames_command(SAMPLE_CONFIG, Path("v.mp4"), Path("out"), every=3)
        self.assertTrue(cmd[0].endswith("ffmpeg.exe") or cmd[0].endswith("ffmpeg"))
        self.assertIn("-y", cmd)
        self.assertIn("fps=1/3,scale=540:-1", cmd)
        self.assertTrue(cmd[-1].endswith("f%03d.jpg"))

    def test_sheet_command_tiles_one_small_jpeg(self):
        cmd = ytkit.build_frames_command(SAMPLE_CONFIG, Path("v.mp4"), Path("out"), every=3, sheet=True)
        self.assertIn("-y", cmd)
        self.assertEqual(_value(cmd, "-vf"), "fps=1/3,scale=240:-1,tile=5x4")
        self.assertEqual(_value(cmd, "-q:v"), "8")
        self.assertEqual(_value(cmd, "-frames:v"), "1")
        self.assertEqual(cmd[-1], str(Path("out") / "v_sheet.jpg"))

    def test_video_command_honours_out_dir(self):
        out_dir = os.path.join("scratch", "x")
        cmd = ytkit.build_command(SAMPLE_CONFIG, "https://x/", mode="video", out_dir=out_dir)
        self.assertIn(out_dir, cmd[cmd.index("-o") + 1])
        self.assertIn("after_move:filepath", cmd)

    def test_extract_frames_writes_one_folder_per_video_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / f"{SYNTH_ID}.mp4"
            download = MagicMock(returncode=0, stdout=f"{video}\n", stderr="")
            ffmpeg = MagicMock(returncode=0)
            with patch("ytkit.subprocess.run", side_effect=[download, ffmpeg]) as mock_run:
                frames = ytkit.extract_frames(SAMPLE_CONFIG, "https://x/", Path(tmp), every=3)
        self.assertEqual(frames, Path(tmp) / "frames" / SYNTH_ID)
        ffmpeg_cmd = mock_run.call_args_list[1].args[0]
        self.assertIn("-y", ffmpeg_cmd)
        self.assertEqual(Path(ffmpeg_cmd[-1]).parent, Path(tmp) / "frames" / SYNTH_ID)


class TestEncoding(unittest.TestCase):
    def test_text_subprocess_calls_use_utf8_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = MagicMock(returncode=0, stdout=json.dumps(SAMPLE_INFO), stderr="")
            with patch("ytkit.subprocess.run", return_value=fake) as mock_run:
                ytkit.fetch_info(SAMPLE_CONFIG, "https://x/", Path(tmp))
        self.assertEqual(mock_run.call_args.kwargs.get("encoding"), "utf-8")
        self.assertEqual(mock_run.call_args.kwargs.get("errors"), "replace")

    def test_emoji_caption_prints_to_cp1252_console(self):
        emoji_info = {**SAMPLE_INFO, "description": "Launch day \U0001F680 caption"}
        console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        with patch.object(sys, "stdout", console), \
                patch.object(sys, "argv", ["ytkit.py", "--url", SYNTH_REEL, "--format", "info"]), \
                patch.object(ytkit, "load_config", return_value=SAMPLE_CONFIG), \
                patch.object(ytkit, "ensure_ytdlp", side_effect=lambda cfg: cfg), \
                patch.object(ytkit, "execute", side_effect=lambda cfg, args: print(ytkit.format_info(emoji_info)) or 0), \
                patch.object(ytkit, "write_log"):
            with self.assertRaises(SystemExit) as exit_info:
                ytkit.main()
        self.assertEqual(exit_info.exception.code, 0)


class TestVttSelection(unittest.TestCase):
    def test_only_the_requested_id_is_picked(self):
        # "BBBBBBBBBBA" shares a letter with the id, so a character-class glob would also match it.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "Other [BBBBBBBBBBA].en.vtt").write_text("x", encoding="utf-8")
            wanted = out / f"Title [{SYNTH_ID}].en.vtt"
            wanted.write_text("x", encoding="utf-8")
            self.assertEqual(ytkit.find_vtt_candidates(out, SYNTH_ID), [wanted])


class TestDownloadLinks(unittest.TestCase):
    def test_path_file_adds_print_to_file_for_audio_and_video(self):
        for mode in ("audio", "video"):
            cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/t", mode=mode, path_file="p.txt")
            self.assertEqual(cmd[cmd.index("--print-to-file") + 1:][:2], ["after_move:filepath", "p.txt"])

    def test_print_links_plain_uris_when_piped(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "My Dir"
            file = folder / "a b.mp3"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ytkit.print_links(folder, file)
        out = buf.getvalue()
        self.assertIn(folder.resolve().as_uri(), out)
        self.assertIn("a%20b.mp3", out)

    def test_osc8_wraps_text_in_hyperlink(self):
        e = chr(27)
        self.assertEqual(ytkit.osc8("file:///example/a", "a"),
                         e + "]8;;file:///example/a" + e + chr(92) + "a" + e + "]8;;" + e + chr(92))


class TestUniqueNames(unittest.TestCase):
    def test_audio_and_video_names_include_id_so_same_title_posts_dont_collide(self):
        for mode in ("audio", "video"):
            cmd = ytkit.build_command(SAMPLE_CONFIG, "https://youtu.be/t", mode=mode)
            self.assertTrue(any("%(title)s [%(id)s].%(ext)s" in a for a in cmd), mode)


if __name__ == "__main__":
    unittest.main()
