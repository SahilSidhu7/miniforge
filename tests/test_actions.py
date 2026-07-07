"""Tests for action parsing and execution."""

import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from miniforge.core.actions import execute_action, parse_actions


class ParseActionsTests(unittest.TestCase):
    def test_parses_multiline_fields_and_pattern(self):
        text = """<<<ACTION>>>
TYPE: edit_file
PATH: src/app.py
FIND:
old_line = 1
print(old_line)
REPLACE:
new_line = 2
print(new_line)
<<<END>>>
<<<ACTION>>>
TYPE: find_files
PATH: .
PATTERN: *.py
<<<END>>>"""

        actions = parse_actions(text)

        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]["type"], "edit_file")
        self.assertEqual(actions[0]["path"], "src/app.py")
        self.assertIn("print(old_line)", actions[0]["find"])
        self.assertEqual(actions[1]["pattern"], "*.py")

    def test_parses_bash_detach_flag(self):
        text = """<<<ACTION>>>
TYPE: bash
COMMAND: npm start
DETACH: true
<<<END>>>"""

        actions = parse_actions(text)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "bash")
        self.assertEqual(actions[0]["command"], "npm start")
        self.assertEqual(actions[0]["detach"], "true")


class ExecuteActionTests(unittest.TestCase):
    def setUp(self):
        self._tmpdirs = []

    def tearDown(self):
        for path in self._tmpdirs:
            shutil.rmtree(path, ignore_errors=True)

    def make_workspace(self) -> Path:
        root = Path.cwd() / "tests_tmp"
        root.mkdir(exist_ok=True)
        path = root / f"workspace_{uuid.uuid4().hex}"
        path.mkdir()
        self._tmpdirs.append(path)
        return path

    def test_find_files_respects_pattern(self):
        work_dir = self.make_workspace()
        (work_dir / "a.py").write_text("print('a')", encoding="utf-8")
        (work_dir / "b.txt").write_text("hello", encoding="utf-8")

        success, output, next_dir = execute_action(
            {"type": "find_files", "path": ".", "pattern": "*.py"},
            work_dir,
        )

        self.assertTrue(success)
        self.assertIn("a.py", output)
        self.assertNotIn("b.txt", output)
        self.assertEqual(next_dir, work_dir)

    def test_escape_outside_workdir_is_blocked(self):
        work_dir = self.make_workspace()
        success, output, next_dir = execute_action(
            {"type": "create_file", "path": "../escape.txt", "content": "x"},
            work_dir,
        )

        self.assertFalse(success)
        self.assertIn("escapes working directory", output)
        self.assertEqual(next_dir, work_dir)

    def test_cd_changes_directory_for_subsequent_actions(self):
        work_dir = self.make_workspace()
        app_dir = work_dir / "calculator"
        app_dir.mkdir()

        success, output, next_dir = execute_action(
            {"type": "bash", "command": "cd calculator"},
            work_dir,
            work_dir,
        )

        self.assertTrue(success)
        self.assertIn("Current directory:", output)
        self.assertEqual(next_dir, app_dir)

        success, output, _ = execute_action(
            {"type": "create_file", "path": "src/App.js", "content": "export default null;\n"},
            next_dir,
            work_dir,
        )

        self.assertTrue(success)
        self.assertTrue((app_dir / "src" / "App.js").exists())

    @patch("miniforge.core.actions.subprocess.Popen")
    def test_detached_bash_uses_new_process(self, popen_mock):
        work_dir = self.make_workspace()
        popen_mock.return_value = Mock(pid=4321)

        success, output, next_dir = execute_action(
            {"type": "bash", "command": "npm start", "detach": "true"},
            work_dir,
            work_dir,
        )

        self.assertTrue(success)
        self.assertIn("Started", output)
        self.assertEqual(next_dir, work_dir)
        popen_mock.assert_called_once()

    @patch("miniforge.core.actions.subprocess.run")
    @patch("miniforge.core.actions.subprocess.Popen")
    def test_long_running_bash_auto_detaches(self, popen_mock, run_mock):
        work_dir = self.make_workspace()
        popen_mock.return_value = Mock(pid=9876)

        success, output, next_dir = execute_action(
            {"type": "bash", "command": "npm start"},
            work_dir,
            work_dir,
        )

        self.assertTrue(success)
        self.assertIn("Started", output)
        self.assertEqual(next_dir, work_dir)
        popen_mock.assert_called_once()
        run_mock.assert_not_called()

    @patch("miniforge.core.actions.subprocess.run")
    def test_short_bash_command_stays_synchronous(self, run_mock):
        work_dir = self.make_workspace()
        run_mock.return_value = Mock(returncode=0, stdout="done\n", stderr="")

        success, output, next_dir = execute_action(
            {"type": "bash", "command": "python --version"},
            work_dir,
            work_dir,
        )

        self.assertTrue(success)
        self.assertEqual(output, "done")
        self.assertEqual(next_dir, work_dir)
        run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
