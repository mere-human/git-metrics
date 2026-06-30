"""Unit tests for setup.py and run-env.py dependency isolation scripts."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO


class TestSetupSkipsCreation(unittest.TestCase):
    """Tests for Requirement 1.2: skip venv creation when .venv exists."""

    @patch("setup.os.path.isdir", return_value=True)
    @patch("setup.venv.create")
    def test_setup_skips_creation_when_venv_exists(self, mock_create, mock_isdir):
        """When .venv already exists, venv.create() should not be called."""
        import setup

        setup.create_venv(".venv")

        mock_create.assert_not_called()


class TestSetupErrorsPythonMissing(unittest.TestCase):
    """Tests for Requirement 1.5: error when Python 3 not found."""

    @patch("setup.shutil.which", return_value=None)
    def test_setup_errors_when_python_missing(self, mock_which):
        """When python3 is not found, display error and exit non-zero."""
        import setup

        with self.assertRaises(SystemExit) as ctx:
            captured_stderr = StringIO()
            with patch("sys.stderr", captured_stderr):
                setup.check_python("python3")

        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("python3", captured_stderr.getvalue())
        self.assertIn("not found", captured_stderr.getvalue())


class TestSetupErrorsRequirementsMissing(unittest.TestCase):
    """Tests for Requirement 2.4: error when requirements.txt missing."""

    @patch("setup.os.path.isfile", return_value=False)
    def test_setup_errors_when_requirements_missing(self, mock_isfile):
        """When requirements.txt is missing, display error and exit non-zero."""
        import setup

        with self.assertRaises(SystemExit) as ctx:
            captured_stderr = StringIO()
            with patch("sys.stderr", captured_stderr):
                setup.install_dependencies(
                    ".venv/bin/python", "requirements.txt")

        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("requirements.txt", captured_stderr.getvalue())
        self.assertIn("not found", captured_stderr.getvalue())


class TestSetupErrorsUnsupportedPlatform(unittest.TestCase):
    """Tests for Requirement 6.4: error on unsupported platform."""

    @patch("setup.sys.platform", "freebsd13")
    def test_setup_errors_on_unsupported_platform(self):
        """When OS is unrecognized, display error and exit non-zero."""
        import setup

        with self.assertRaises(SystemExit) as ctx:
            captured_stderr = StringIO()
            with patch("sys.stderr", captured_stderr):
                setup.detect_platform()

        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("Unsupported", captured_stderr.getvalue())


def _load_run_env():
    """Load run-env.py as a module (handles the hyphen in filename)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_env", os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "run-env.py")
    )
    run_env = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_env)
    return run_env


# Load run-env module once for all runner tests
run_env = _load_run_env()


class TestRunnerErrorsVenvMissing(unittest.TestCase):
    """Tests for Requirement 3.2: error when .venv missing."""

    def test_runner_errors_when_venv_missing(self):
        """When .venv does not exist, display error instructing to run setup.py."""
        with patch("sys.argv", ["run-env.py", "run.py"]):
            with patch.object(run_env.os.path, "isdir", return_value=False):
                captured_stderr = StringIO()
                with patch("sys.stderr", captured_stderr):
                    with self.assertRaises(SystemExit) as ctx:
                        run_env.main()

                self.assertNotEqual(ctx.exception.code, 0)
                self.assertIn("setup.py", captured_stderr.getvalue())


class TestRunnerErrorsWithoutScriptName(unittest.TestCase):
    """Tests for Requirement 3.4: usage message when no script name provided."""

    def test_runner_errors_without_script_name(self):
        """When no script name is given, display usage message and exit non-zero."""
        with patch("sys.argv", ["run-env.py"]):
            captured_stderr = StringIO()
            with patch("sys.stderr", captured_stderr):
                with self.assertRaises(SystemExit) as ctx:
                    run_env.main()

            self.assertNotEqual(ctx.exception.code, 0)
            self.assertIn("Usage:", captured_stderr.getvalue())


class TestRunnerErrorsExecutableNotFound(unittest.TestCase):
    """Tests for Requirement 3.1: error propagation when executable not found."""

    def test_runner_errors_when_executable_not_found(self):
        """When subprocess raises FileNotFoundError, it should propagate."""
        with patch("sys.argv", ["run-env.py", "nonexistent_script.py"]):
            with patch.object(run_env.os.path, "isdir", return_value=True):
                with patch.object(run_env.subprocess, "run", side_effect=FileNotFoundError(
                    "[Errno 2] No such file or directory: '.venv/bin/python'"
                )):
                    with self.assertRaises(FileNotFoundError):
                        run_env.main()


if __name__ == "__main__":
    unittest.main()
