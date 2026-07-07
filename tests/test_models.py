"""Tests for prompt enforcement and action-block recovery."""

import unittest
from unittest.mock import Mock, patch

from miniforge.core.models import ask_model, expected_action_types, should_require_actions


def _mock_response(text):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"response": text}
    return response


class ShouldRequireActionsTests(unittest.TestCase):
    def test_actionable_request_requires_actions(self):
        self.assertTrue(should_require_actions("make a calculator using react"))

    def test_explanatory_question_does_not_require_actions(self):
        self.assertFalse(should_require_actions("how do I create a Python virtual environment?"))

    def test_edit_request_expects_edit_related_actions(self):
        self.assertEqual(expected_action_types("edit calculator.py to make it work"), {"edit_file", "read_file"})


class AskModelTests(unittest.TestCase):
    @patch("miniforge.core.models.requests.post")
    def test_retries_when_actionable_response_has_no_action_blocks(self, post_mock):
        post_mock.side_effect = [
            _mock_response("Sure, here are the steps to build it."),
            _mock_response(
                "<<<ACTION>>>\nTYPE: create_file\nPATH: package.json\nCONTENT:\n{}\n<<<END>>>\nDone."
            ),
        ]

        response = ask_model(
            messages=[{"role": "user", "content": "make a calculator using react"}],
            system_prompt="system",
            model="test-model",
            ollama_url="http://localhost:11434/api/generate",
            require_actions=True,
            stream=True,
        )

        self.assertIn("<<<ACTION>>>", response)
        self.assertEqual(post_mock.call_count, 2)

    @patch("miniforge.core.models.requests.post")
    def test_retries_when_edit_request_returns_only_bash(self, post_mock):
        post_mock.side_effect = [
            _mock_response(
                "<<<ACTION>>>\nTYPE: bash\nCOMMAND: python calculator.py\n<<<END>>>\nTrying it now."
            ),
            _mock_response(
                "<<<ACTION>>>\nTYPE: read_file\nPATH: calculator.py\n<<<END>>>\n"
                "<<<ACTION>>>\nTYPE: edit_file\nPATH: calculator.py\nFIND:\npass\nREPLACE:\nprint('ok')\n<<<END>>>"
            ),
        ]

        response = ask_model(
            messages=[{"role": "user", "content": "edit calculator.py to make it work as a calculator"}],
            system_prompt="system",
            model="test-model",
            ollama_url="http://localhost:11434/api/generate",
            require_actions=True,
            stream=True,
        )

        self.assertIn("TYPE: edit_file", response)
        self.assertEqual(post_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
