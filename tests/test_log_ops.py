import tempfile
import unittest
from pathlib import Path

from log_ops import analyze_log


class TestLogAnalysis(unittest.TestCase):
    def test_keyword_line_counts(self):
        log_text = (
            "INFO application started\n"
            "ERROR database connection failed\n"
            "WARNING disk space is low\n"
            "INFO request completed\n"
            "error connection timeout\n"
            "INFO application stopped\n"
            "WARNING ERROR ERROR retry failed\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "sample.log"
            log_path.write_text(log_text, encoding="utf-8")

            result = analyze_log(log_path)

        self.assertEqual(result["error"], "")
        self.assertEqual(result["total_lines"], 7)
        self.assertEqual(result["error_lines"], 3)
        self.assertEqual(result["warning_lines"], 2)

        matched_lines = [
            match["line_number"]
            for match in result["matches"]
        ]
        self.assertEqual(matched_lines, [2, 3, 5, 7])

    def test_match_limit_does_not_stop_counting(self):
        log_text = "ERROR request failed\n" * 25

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "many_errors.log"
            log_path.write_text(log_text, encoding="utf-8")

            result = analyze_log(log_path)

        self.assertEqual(result["error"], "")
        self.assertEqual(result["total_lines"], 25)
        self.assertEqual(result["error_lines"], 25)
        self.assertEqual(len(result["matches"]), 20)
        self.assertEqual(result["matches"][-1]["line_number"], 20)

    def test_missing_log_returns_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "missing.log"

            result = analyze_log(log_path)

        self.assertNotEqual(result["error"], "")