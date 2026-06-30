"""Unit tests for pull-branches.py branch checkout helper."""

import importlib.util
import os
import unittest
from io import StringIO
from subprocess import CompletedProcess
from unittest.mock import call, patch


def _load_pull_branches():
    """Load pull-branches.py as a module (handles the hyphen in filename)."""
    spec = importlib.util.spec_from_file_location(
        "pull_branches",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "pull-branches.py"),
    )
    pull_branches = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pull_branches)
    return pull_branches


pull_branches = _load_pull_branches()


def _cmd_from_call(call_args):
    return call_args[0][0]


class TestPullBranchesEmptyInput(unittest.TestCase):
    """When stdin has no branch names, only submodule config is toggled."""

    @patch.object(pull_branches.subprocess, "check_call")
    @patch.object(pull_branches.subprocess, "run")
    @patch.object(pull_branches.sys, "stdin", StringIO("\n  \n"))
    @patch("builtins.print")
    def test_empty_input_only_toggles_submodule_config(
        self, mock_print, mock_run, mock_check_call
    ):
        mock_run.return_value = CompletedProcess([], 0)

        pull_branches.main()

        mock_check_call.assert_not_called()
        self.assertEqual(mock_run.call_count, 2)
        run_cmds = [_cmd_from_call(c) for c in mock_run.call_args_list]
        self.assertEqual(
            run_cmds[0],
            ["git", "config", "--local", "submodule.recurse", "false"],
        )
        self.assertEqual(
            run_cmds[1],
            ["git", "config", "--local", "submodule.recurse", "true"],
        )


class TestPullBranchesExistingBranch(unittest.TestCase):
    """When a branch exists locally, checkout, restore, and pull are invoked."""

    @patch.object(pull_branches.subprocess, "check_call")
    @patch.object(pull_branches.subprocess, "run")
    @patch.object(pull_branches.sys, "stdin", StringIO("main\n"))
    @patch("builtins.print")
    def test_existing_branch_checkout_restore_pull(
        self, mock_print, mock_run, mock_check_call
    ):
        def run_side_effect(cmd, *args, **kwargs):
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                return CompletedProcess(cmd, 0)
            return CompletedProcess(cmd, 0)

        mock_run.side_effect = run_side_effect

        pull_branches.main()

        mock_check_call.assert_has_calls(
            [
                call(["git", "checkout", "main"]),
                call(["git", "restore", "."]),
                call(["git", "pull"]),
            ]
        )


class TestPullBranchesMissingBranch(unittest.TestCase):
    """When a branch is missing locally, fetch and create a local tracking branch."""

    @patch.object(pull_branches.subprocess, "check_call")
    @patch.object(pull_branches.subprocess, "run")
    @patch.object(pull_branches.sys, "stdin", StringIO("feature/new\n"))
    @patch("builtins.print")
    def test_missing_branch_fetch_and_checkout(
        self, mock_print, mock_run, mock_check_call
    ):
        def run_side_effect(cmd, *args, **kwargs):
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                return CompletedProcess(cmd, 1)
            return CompletedProcess(cmd, 0)

        mock_run.side_effect = run_side_effect

        pull_branches.main()

        mock_check_call.assert_has_calls(
            [
                call(
                    ["git", "remote", "set-branches", "--add", "origin", "feature/new"]
                ),
                call(["git", "fetch", "origin", "feature/new"]),
                call(
                    ["git", "checkout", "origin/feature/new", "-b", "feature/new"]
                ),
            ]
        )


class TestPullBranchesArgvLists(unittest.TestCase):
    """Branch names with shell metacharacters must be passed as argv elements."""

    @patch.object(pull_branches.subprocess, "check_call")
    @patch.object(pull_branches.subprocess, "run")
    @patch.object(
        pull_branches.sys,
        "stdin",
        StringIO("feature/foo; rm -rf /\n"),
    )
    @patch("builtins.print")
    def test_special_characters_passed_as_single_argument(
        self, mock_print, mock_run, mock_check_call
    ):
        branch = "feature/foo; rm -rf /"

        def run_side_effect(cmd, *args, **kwargs):
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                return CompletedProcess(cmd, 0)
            return CompletedProcess(cmd, 0)

        mock_run.side_effect = run_side_effect

        pull_branches.main()

        rev_parse_cmd = mock_run.call_args_list[1][0][0]
        self.assertEqual(rev_parse_cmd, ["git", "rev-parse", "--verify", "--quiet", branch])

        checkout_cmd = mock_check_call.call_args_list[0][0][0]
        self.assertEqual(checkout_cmd, ["git", "checkout", branch])

        for call in mock_run.call_args_list + mock_check_call.call_args_list:
            cmd = call[0][0]
            self.assertIsInstance(cmd, list)
            kwargs = call[1]
            self.assertNotIn("shell", kwargs)


class TestPullBranchesMultipleBranches(unittest.TestCase):
    """Each non-empty stdin line triggers a separate branch workflow."""

    @patch.object(pull_branches.subprocess, "check_call")
    @patch.object(pull_branches.subprocess, "run")
    @patch.object(pull_branches.sys, "stdin", StringIO("main\n develop \n"))
    @patch("builtins.print")
    def test_multiple_branches(self, mock_print, mock_run, mock_check_call):
        existing = {"main", "develop"}

        def run_side_effect(cmd, *args, **kwargs):
            if cmd[:3] == ["git", "rev-parse", "--verify"]:
                branch = cmd[4]
                code = 0 if branch in existing else 1
                return CompletedProcess(cmd, code)
            return CompletedProcess(cmd, 0)

        mock_run.side_effect = run_side_effect

        pull_branches.main()

        rev_parse_branches = [
            call[0][0][4]
            for call in mock_run.call_args_list
            if call[0][0][:3] == ["git", "rev-parse", "--verify"]
        ]
        self.assertEqual(rev_parse_branches, ["main", "develop"])

        checkout_calls = [
            call[0][0]
            for call in mock_check_call.call_args_list
            if call[0][0][:2] == ["git", "checkout"]
        ]
        self.assertEqual(
            checkout_calls,
            [["git", "checkout", "main"], ["git", "checkout", "develop"]],
        )


if __name__ == "__main__":
    unittest.main()
