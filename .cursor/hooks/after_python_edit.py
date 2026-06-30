#!/usr/bin/env python3
"""Format edited Python files with autopep8 and run unit tests."""

import json
import os
import subprocess
import sys


def find_python():
    if os.path.isdir(".venv/bin"):
        return os.path.join(".venv", "bin", "python")
    if os.path.isdir(".venv/Scripts"):
        return os.path.join(".venv", "Scripts", "python.exe")
    return sys.executable


def main():
    data = json.load(sys.stdin)
    file_path = data.get("file_path") or data.get("path") or ""

    if not file_path.endswith(".py") or not os.path.isfile(file_path):
        return 0

    python = find_python()

    subprocess.run(
        [python, "-m", "autopep8", "--in-place", file_path],
        capture_output=True,
    )

    result = subprocess.run(
        [python, "-m", "unittest", "test_run", "-v"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        output = result.stdout + result.stderr
        msg = f"Unit tests failed after editing {file_path}:\n{output}"
        print(json.dumps({"additional_context": msg[:4000]}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
