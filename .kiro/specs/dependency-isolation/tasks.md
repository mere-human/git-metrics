# Implementation Plan: Dependency Isolation

## Overview

Add dependency isolation to git-metrics via two new Python scripts (`setup.py` and `run-env.py`) that manage a `.venv` virtual environment. The implementation follows the project's flat structure convention, uses only the standard library for the scripts themselves, and includes property-based tests via Hypothesis to verify correctness properties.

## Tasks

- [x] 1. Add .venv to .gitignore (one-time commit)
  - [x] 1.1 Append `.venv` to `.gitignore` and commit
    - Add `.venv` as a new line in the existing `.gitignore` file
    - This is a one-time repository change, not managed by setup.py at runtime
    - _Requirements: 4.1, 4.2_

- [x] 2. Implement setup.py core functions
  - [x] 2.1 Create setup.py with platform detection and venv creation
    - Create `setup.py` at the project root
    - Implement `detect_platform()` that returns python executable name and venv interpreter path based on `sys.platform`
    - Implement `check_python()` that verifies Python 3 is available
    - Implement `create_venv(venv_dir)` using `venv.create()` that skips creation if `.venv` already exists
    - Implement `main()` orchestrating the setup flow with proper error handling and exit codes
    - All error messages go to stderr via `print(..., file=sys.stderr)`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.3, 6.4_

  - [x] 2.2 Implement dependency installation in setup.py
    - Implement `install_dependencies(venv_python, requirements_file)` that runs pip install within the venv
    - Handle missing `requirements.txt` with clear error message and non-zero exit
    - Handle package installation failures with error identifying the failed package
    - Implement pip output summary parsing to report counts of installed vs already-satisfied packages
    - Display summary message on completion: "Setup complete: X package(s) installed, Y package(s) already satisfied."
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Implement run-env.py
  - [x] 3.1 Create run-env.py with argument passthrough and exit code propagation
    - Create `run-env.py` at the project root
    - Implement `detect_platform()` returning the venv interpreter path for the current OS
    - Implement `main()` that validates arguments, checks `.venv` existence, and executes target script
    - Use `subprocess.run()` to execute the target script with the venv Python interpreter
    - Pass all arguments following the script name to the subprocess without modification
    - Propagate the subprocess exit code as the runner's exit code
    - Display error if `.venv` missing: "Virtual environment not found. Run: python3 setup.py"
    - Display usage message if no script name provided: "Usage: python3 run-env.py <script> [args...]"
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.2_

- [x] 4. Checkpoint - Verify core scripts work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create test file with unit tests and property-based tests
  - [x] 5.1 Create test_setup.py with unit tests
    - Create `test_setup.py` at the project root
    - Write unit test: `test_setup_skips_creation_when_venv_exists` — mock venv.create, verify not called
    - Write unit test: `test_setup_errors_when_python_missing` — verify error message and exit code
    - Write unit test: `test_setup_errors_when_requirements_missing` — verify error message and exit code
    - Write unit test: `test_setup_errors_on_unsupported_platform` — verify error message and exit code
    - Write unit test: `test_runner_errors_when_venv_missing` — verify error message and exit code
    - Write unit test: `test_runner_errors_without_script_name` — verify usage message
    - Write unit test: `test_runner_errors_when_executable_not_found` — verify error propagation
    - _Requirements: 1.2, 1.5, 2.3, 2.4, 3.1, 3.2, 3.4, 6.4_

  - [ ]* 5.2 Write property test for platform detection consistency
    - **Property 1: Platform detection returns consistent configuration**
    - Use Hypothesis to generate `sys.platform` string values
    - Verify Unix config for platforms starting with "linux" or "darwin"
    - Verify Windows config for platforms starting with "win"
    - Verify error raised for unrecognized platforms
    - Verify no mixed configurations (Unix executable with Windows path)
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 5.3 Write property test for exit code propagation
    - **Property 2: Exit code propagation**
    - Use Hypothesis to generate integers in range 0–255
    - Mock subprocess to return the generated exit code
    - Verify the runner exits with the same code
    - **Validates: Requirements 3.1**

  - [ ]* 5.4 Write property test for argument passthrough
    - **Property 3: Argument passthrough preserves all arguments**
    - Use Hypothesis to generate lists of arbitrary strings (including spaces, special characters, flags)
    - Mock subprocess and capture the argument list passed to it
    - Verify the subprocess receives exactly the same argument list
    - **Validates: Requirements 3.3**

  - [ ]* 5.5 Write property test for pip output summary parsing
    - **Property 4: Pip output summary parsing produces correct counts**
    - Use Hypothesis to generate pip output with a mix of "Successfully installed" and "Requirement already satisfied" lines
    - Verify parsed counts match the actual number of each line type
    - **Validates: Requirements 2.5**

- [ ] 6. Create requirements-dev.txt
  - [ ] 6.1 Create requirements-dev.txt with test dependencies
    - Create `requirements-dev.txt` at the project root
    - Add `hypothesis>=6.0.0` for property-based testing
    - Add `pytest>=7.0.0` for test runner
    - _Requirements: (testing infrastructure)_

- [x] 7. Update README with setup and usage instructions
  - [x] 7.1 Add dependency isolation section to README.md
    - Add a section describing how to run `python3 setup.py` to create the isolated environment
    - State what the script produces (a `.venv` directory with installed dependencies)
    - Add usage example showing `python3 run-env.py run.py --since "2 weeks"`
    - Add manual activation instructions for Unix (`source .venv/bin/activate`) and Windows (`.venv\Scripts\activate`)
    - State the prerequisite that Python 3 must be installed
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The project uses a flat structure — all new files go in the project root
- `setup.py` and `run-env.py` use only the Python standard library
- Test dependencies (Hypothesis, pytest) go in `requirements-dev.txt`, not the main `requirements.txt`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "6.1"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["5.1", "7.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "5.4", "5.5"] }
  ]
}
```
