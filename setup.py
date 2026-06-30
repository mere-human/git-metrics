"""Setup script for git-metrics dependency isolation.

Creates a .venv virtual environment and installs dependencies from requirements.txt.
Uses only the Python standard library.
"""

import os
import sys
import shutil
import subprocess
import venv


def detect_platform():
    """Detect the operating system and return platform-specific configuration.

    Returns a dict with:
        - python_cmd: the Python executable name for this platform
        - venv_python: the path to the Python interpreter inside .venv

    Raises SystemExit with code 1 for unsupported platforms.
    """
    platform = sys.platform

    if platform.startswith("linux") or platform.startswith("darwin"):
        return {
            "python_cmd": "python3",
            "venv_python": os.path.join(".venv", "bin", "python"),
        }
    elif platform.startswith("win"):
        return {
            "python_cmd": "python",
            "venv_python": os.path.join(".venv", "Scripts", "python.exe"),
        }
    else:
        print(
            f"Error: Unsupported operating system: {platform}",
            file=sys.stderr,
        )
        sys.exit(1)


def check_python(python_cmd):
    """Verify that the expected Python 3 executable is available on the system.

    Args:
        python_cmd: The expected Python executable name (python3 or python).

    Raises SystemExit with code 1 if the executable is not found.
    """
    path = shutil.which(python_cmd)
    if path is None:
        print(
            f"Error: {python_cmd} not found. Please install Python 3.", file=sys.stderr)
        sys.exit(1)


def create_venv(venv_dir):
    """Create a virtual environment at the specified directory.

    If the directory already exists, skip creation.

    Args:
        venv_dir: Path to the virtual environment directory.
    """
    if os.path.isdir(venv_dir):
        print(
            f"Virtual environment already exists at {venv_dir}, skipping creation.")
        return

    print(f"Creating virtual environment at {venv_dir}...")
    venv.create(venv_dir, with_pip=True)
    print("Virtual environment created.")


def parse_pip_output(output):
    """Parse pip install output to count installed and already-satisfied packages.

    Args:
        output: The stdout string from pip install.

    Returns:
        A tuple (installed_count, already_satisfied_count).
    """
    installed_count = 0
    already_satisfied_count = 0

    for line in output.splitlines():
        if "Successfully installed" in line:
            # "Successfully installed pkg1-1.0 pkg2-2.0" — count space-separated packages
            parts = line.split("Successfully installed", 1)[1].strip().split()
            installed_count += len(parts)
        elif "Requirement already satisfied" in line:
            already_satisfied_count += 1

    return installed_count, already_satisfied_count


def install_dependencies(venv_python, requirements_file):
    """Install dependencies from requirements_file using pip in the venv.

    Args:
        venv_python: Path to the Python interpreter inside the venv.
        requirements_file: Path to the requirements.txt file.

    Raises SystemExit with code 1 if requirements_file is missing or pip fails.
    """
    if not os.path.isfile(requirements_file):
        print(
            f"Error: {requirements_file} not found.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Installing dependencies from {requirements_file}...")

    result = subprocess.run(
        [venv_python, "-m", "pip", "install", "-r", requirements_file],
        capture_output=True,
        text=True)

    if result.returncode != 0:
        # Try to identify the failed package from pip's stderr
        stderr_output = result.stderr
        failed_package = None
        for line in stderr_output.splitlines():
            if "No matching distribution found for" in line:
                failed_package = line.split(
                    "No matching distribution found for")[-1].strip()
                break
            elif "Could not find a version that satisfies" in line:
                failed_package = line.split(
                    "Could not find a version that satisfies the requirement")[-1].strip()
                break
            elif "ERROR:" in line:
                failed_package = line.split("ERROR:")[-1].strip()
                break

        if failed_package:
            print(
                f"Error: Failed to install package: {failed_package}", file=sys.stderr)
        else:
            print("Error: Package installation failed.", file=sys.stderr)
        sys.exit(result.returncode)

    installed, already_satisfied = parse_pip_output(result.stdout)
    print(
        f"Setup complete: {installed} package(s) installed, {already_satisfied} package(s) already satisfied.")


def main():
    """Orchestrate the setup flow: detect platform, check python, create venv, install deps."""
    platform_config = detect_platform()
    python_cmd = platform_config["python_cmd"]
    venv_python = platform_config["venv_python"]

    check_python(python_cmd)

    venv_dir = ".venv"
    create_venv(venv_dir)

    install_dependencies(venv_python, "requirements.txt")


if __name__ == "__main__":
    main()
