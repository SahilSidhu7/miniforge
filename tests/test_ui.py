"""Tests for UI helpers."""

import unittest
from unittest.mock import Mock, patch

from miniforge.ui_module.ui import check_ollama, get_ollama_runtime_status


class CheckOllamaTests(unittest.TestCase):
    @patch("miniforge.ui_module.ui.requests.get")
    def test_uses_configured_ollama_base_url_for_tags(self, get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"models": [{"name": "qwen2.5-coder:7b"}]}
        get_mock.return_value = response

        ok = check_ollama("qwen2.5-coder:7b", "http://example.com:11434/api/generate")

        self.assertTrue(ok)
        get_mock.assert_called_once_with("http://example.com:11434/api/tags", timeout=5)


class OllamaRuntimeStatusTests(unittest.TestCase):
    @patch("miniforge.ui_module.ui.requests.get")
    def test_reports_cpu_when_no_vram_is_allocated(self, get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "models": [
                {
                    "name": "qwen2.5-coder:7b",
                    "size": 4840321024,
                    "size_vram": 0,
                    "context_length": 8192,
                }
            ]
        }
        get_mock.return_value = response

        status = get_ollama_runtime_status("qwen2.5-coder:7b", "http://example.com:11434/api/generate")

        self.assertIsNotNone(status)
        self.assertEqual(status["processor"], "100% CPU")
        get_mock.assert_called_once_with("http://example.com:11434/api/ps", timeout=5)

    @patch("miniforge.ui_module.ui.requests.get")
    def test_reports_gpu_percentage_when_partially_offloaded(self, get_mock):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "models": [
                {
                    "name": "qwen2.5-coder:7b",
                    "size": 400,
                    "size_vram": 200,
                    "context_length": 4096,
                }
            ]
        }
        get_mock.return_value = response

        status = get_ollama_runtime_status("qwen2.5-coder:7b", "http://example.com:11434/api/generate")

        self.assertIsNotNone(status)
        self.assertEqual(status["processor"], "50% GPU")


if __name__ == "__main__":
    unittest.main()
