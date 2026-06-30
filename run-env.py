"""Runner script for git-metrics dependency isolation.

Executes a target script using the .venv Python interpreter,
passing all arguments through and propagating the exit code.
Uses only the Python standard library.
"""

import os
import sys
import subprocess


def detect_platform():
    """Detect the operating system and return the venv interpreter path.

    Returns the path to the Python interpreter inside .venv for the current OS.

    Raises SystemExit with code 1 for unsupported platforms.
    """
    platform = sys.platform

    if platform.startswith("linux") or platform.startswith("darwin"):
        return os.path.join(".venv", "bin", "python")
    elif platform.startswith("win"):
        return os.path.join(".venv", "Scripts", "python.exe")
    else:
        print(
            f"Error: Unsupported operating system: {platform}",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    """Validate arguments, check venv existence, and execute the target script."""
    if len(sys.argv) < 2:
        print(
            "Usage: python3 run-env.py <script> [args...]",
            file=sys.stderr,
        )
        sys.exit(1)

    venv_python = detect_platform()

    if not os.path.isdir(".venv"):
        print(
            "Virtual environment not found. Run: python3 setup.py",
            file=sys.stderr,
        )
        sys.exit(1)

    script = sys.argv[1]
    script_args = sys.argv[2:]

    result = subprocess.run([venv_python, script] + script_args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
