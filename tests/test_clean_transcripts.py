import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "clean_transcripts.py"


class TestCleanTranscripts(unittest.TestCase):
    def test_missing_path_is_skipped_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "nope.vtt")
            result = subprocess.run([sys.executable, str(SCRIPT), missing], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not found", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
