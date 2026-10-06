"""Check streaming download logs without downloading any vendor installers."""

import io
import json
from pathlib import Path
import selectors
import subprocess
import sys
import unittest


WRAPPER = Path(__file__).resolve().parent.parent / "scripts/curl_progress.py"
sys.path.insert(0, str(WRAPPER.parent))
from curl_progress import Progress


class DownloadProgressTests(unittest.TestCase):
    def test_progress_is_visible_before_download_finishes(self):
        # The child cannot finish until the test observes progress and sends
        # input. This catches buffering until EOF, not just final formatting.
        child = (
            "import sys; "
            "sys.stderr.write('\\r###### 25.0%\\r'); sys.stderr.flush(); "
            "sys.stdin.readline(); "
            "sys.stdout.buffer.write(b'payload\\x00\\r\\n'); "
            "sys.stderr.write('################ 100.0%\\n')"
        )
        with subprocess.Popen(
            [sys.executable, str(WRAPPER), sys.executable, "-c", child],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ) as process:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stderr, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=5), "Progress was buffered until completion")
                progress = process.stderr.read1(4096)
                self.assertEqual(json.loads(progress[5:]), {"action": "setPhase", "phase": "download 25.0%"})
                self.assertIsNone(process.poll())
                output, errors = process.communicate(b"continue\n", timeout=5)
                self.assertEqual(output, b"payload\x00\r\n")
                self.assertEqual(json.loads(errors[5:]), {"action": "setPhase", "phase": "download 100.0%"})
                self.assertEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()

    def test_split_meter_updates_are_throttled_but_completion_is_emitted(self):
        output = io.BytesIO()
        progress = Progress(output, clock=lambda: 0)
        progress.feed(b"\r### 2")
        self.assertEqual(output.getvalue(), b"")
        progress.feed(b"5.0%\r### 26.0%\r### 27.0%\r### 100.0%\r")
        events = [json.loads(line[5:]) for line in output.getvalue().splitlines()]
        self.assertEqual([event["phase"] for event in events], ["download 25.0%", "download 100.0%"])
        self.assertNotIn(b"success", output.getvalue())

    def test_retry_progress_can_restart_and_unknown_sizes_are_explicit(self):
        output = io.BytesIO()
        progress = Progress(output, clock=lambda: 0)
        progress.feed(b"### 50.0%\r### 0.0%\r")
        self.assertIn(b"download 0.0%", output.getvalue())
        output = io.BytesIO()
        progress = Progress(output)
        progress.feed(b" -=O=-    #      #\r")
        self.assertIn(b"downloading (size unknown)", output.getvalue())

    def test_curl_failure_and_unterminated_error_are_preserved(self):
        result = subprocess.run(
            [sys.executable, str(WRAPPER), sys.executable, "-c",
             "import sys; sys.stderr.write('curl: connection failed'); sys.exit(22)"],
            capture_output=True, timeout=5,
        )
        self.assertEqual(result.returncode, 22)
        self.assertEqual(result.stderr, b"curl: connection failed")
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
