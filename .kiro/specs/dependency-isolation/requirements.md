# Requirements Document

## Introduction

This feature adds dependency isolation to the git-metrics project so that its Python dependencies (XlsxWriter, openpyxl) do not conflict with system-level or other project packages. The solution should use Python virtual environments as the standard, lightweight isolation mechanism, and provide simple setup and usage instructions that integrate with the existing flat project structure and workflow.

## Glossary

- **Setup_Script**: A shell script or Python script that automates the creation and configuration of the isolated environment for git-metrics.
- **Virtual_Environment**: A self-contained Python environment directory (created via `venv`) that holds project-specific dependencies separate from the system Python installation.
- **Dependency_Installer**: The component responsible for installing required packages from `requirements.txt` into the Virtual_Environment.
- **Runner_Script**: A wrapper script that activates the Virtual_Environment and executes a git-metrics command within it.
- **System_Python**: The Python interpreter installed at the operating system level, shared across all projects on the machine.

## Requirements

### Requirement 1: Virtual Environment Creation

**User Story:** As a developer, I want to create an isolated Python environment for git-metrics, so that its dependencies do not interfere with my system Python packages.

#### Acceptance Criteria

1. WHEN the user runs the Setup_Script, THE Setup_Script SHALL create a Virtual_Environment directory within the project root that contains a Python interpreter and a `pyvenv.cfg` file.
2. WHEN the Virtual_Environment directory already exists, THE Setup_Script SHALL skip environment creation and proceed to dependency installation regardless of whether the environment is valid or corrupted.
3. THE Setup_Script SHALL use the Python 3 standard library `venv` module to create the Virtual_Environment.
4. THE Virtual_Environment SHALL be located in a directory named `.venv` at the project root.
5. IF Python 3 is not found on the system, THEN THE Setup_Script SHALL display an error message indicating the failure reason and exit with a non-zero status code, even if the Virtual_Environment directory already exists.

### Requirement 2: Dependency Installation

**User Story:** As a developer, I want project dependencies to be automatically installed into the isolated environment, so that I do not need to manually install them after setup.

#### Acceptance Criteria

1. WHEN the Virtual_Environment is created or already exists, THE Dependency_Installer SHALL install all packages listed in `requirements.txt` into the Virtual_Environment using pip from the Virtual_Environment.
2. WHEN a package listed in `requirements.txt` is already installed at a version satisfying the specified version constraint, THE Dependency_Installer SHALL skip reinstallation of that package.
3. IF a package installation fails, THEN THE Dependency_Installer SHALL display an error message identifying the failed package name and exit with a non-zero status code, leaving any previously installed packages intact.
4. IF the `requirements.txt` file does not exist in the project root, THEN THE Dependency_Installer SHALL display an error message indicating the file is missing and exit with a non-zero status code.
5. WHEN all packages are successfully installed or already satisfied, THE Dependency_Installer SHALL display a summary message indicating the count of packages installed and the count of packages skipped.

### Requirement 3: Script Execution Within Isolated Environment

**User Story:** As a developer, I want a simple way to run git-metrics scripts using the isolated environment, so that I do not need to manually activate the virtual environment each time.

#### Acceptance Criteria

1. WHEN the user invokes the Runner_Script with a script name and optional arguments, THE Runner_Script SHALL first verify the Virtual_Environment exists before attempting execution, then execute that script using the Python interpreter from the Virtual_Environment and exit with the same exit code returned by the executed script.
2. IF the Virtual_Environment does not exist, THEN THE Runner_Script SHALL check for the Virtual_Environment first, display an error message instructing the user to run the Setup_Script, and exit with a non-zero status code without attempting script execution.
3. THE Runner_Script SHALL pass all command-line arguments following the script name through to the target script without modification.
4. IF the user invokes the Runner_Script without specifying a script name, THEN THE Runner_Script SHALL display a usage message indicating the expected invocation format and exit with a non-zero status code.

### Requirement 4: Gitignore Configuration

**User Story:** As a developer, I want the virtual environment directory to be excluded from version control, so that it does not bloat the repository.

#### Acceptance Criteria

1. THE `.gitignore` file SHALL contain a line whose trimmed content equals `.venv` so that the Virtual_Environment directory is excluded from version control.
2. THE `.venv` entry in `.gitignore` SHALL be committed to the repository as a one-time change and SHALL NOT be managed by the Setup_Script at runtime.

### Requirement 5: Documentation

**User Story:** As a developer, I want clear instructions on how to set up and use the isolated environment, so that I can get started without reading implementation details.

#### Acceptance Criteria

1. THE README SHALL include a section describing how to run the Setup_Script to create the isolated environment, containing at minimum the exact command to execute the Setup_Script and a statement of what the script produces (a `.venv` directory with installed dependencies).
2. THE README SHALL include instructions for running git-metrics scripts using the Runner_Script, containing at minimum one usage example showing the Runner_Script invoked with a git-metrics command and its arguments.
3. THE README SHALL include instructions for manually activating the Virtual_Environment as an alternative to the Runner_Script, providing the activation command for both Unix-like systems (`source .venv/bin/activate`) and Windows (`.venv\Scripts\activate`).
4. THE README SHALL state the prerequisite that Python 3 must be installed on the system before running the Setup_Script.

### Requirement 6: Cross-Platform Compatibility

**User Story:** As a developer, I want the isolation setup to work on both Unix-like systems and Windows, so that all contributors can use it regardless of their operating system.

#### Acceptance Criteria

1. THE Setup_Script SHALL detect the operating system and use `python3` as the Python executable name on Unix-like systems (Linux, macOS) and `python` on Windows.
2. THE Runner_Script SHALL use `.venv/bin/python` as the Virtual_Environment interpreter path on Unix-like systems (Linux, macOS) and `.venv/Scripts/python.exe` on Windows.
3. IF the expected Python executable is not found on the detected operating system, THEN THE Setup_Script SHALL display an error message indicating which executable was not found and exit with a non-zero status code.
4. IF the operating system cannot be identified as Unix-like or Windows, THEN THE Setup_Script SHALL display an error message indicating the unsupported operating system and exit with a non-zero status code.
