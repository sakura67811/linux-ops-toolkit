import subprocess
import unittest
from unittest.mock import patch

from inspection_ops import get_service_status


class TestServiceTimeouts(unittest.TestCase):
    def assert_timeout_does_not_stop_next_service(self, first_results):
        responses = first_results + [
            subprocess.CompletedProcess([], 0, "loaded\n", ""),
            subprocess.CompletedProcess([], 0, "active\n", ""),
        ]
        with patch("inspection_ops.subprocess.run", side_effect=responses):
            result = get_service_status(["slow-service", "healthy-service"])

        self.assertEqual(result["slow-service"], "check-timeout")
        self.assertEqual(result["healthy-service"], "active")

    def test_load_state_timeout_does_not_stop_next_service(self):
        self.assert_timeout_does_not_stop_next_service([
            subprocess.TimeoutExpired("systemctl", 5),
        ])

    def test_active_state_timeout_does_not_stop_next_service(self):
        self.assert_timeout_does_not_stop_next_service([
            subprocess.CompletedProcess([], 0, "loaded\n", ""),
            subprocess.TimeoutExpired("systemctl", 5),
        ])
