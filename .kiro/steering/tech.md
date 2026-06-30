# Tech Stack

## Language
- Python 3 (no type annotations enforced, but some type hints used in function signatures)

## Dependencies (requirements.txt)
- `XlsxWriter>=3.1.0` — writing XLSX output files
- `openpyxl>=3.1.5` — reading existing XLSX files (used by merge.py)

## Testing
- Framework: `unittest` (standard library)
- Test file: `test_run.py`
- Run tests: `python3 -m unittest test_run -v`
- Alternative: `python3 run.py --test`

## Common Commands

| Task | Command |
|------|---------|
| Install dependencies | `pip3 install -r requirements.txt` |
| Run the tool | `python3 run.py --since "2 weeks"` |
| Run tests | `python3 -m unittest test_run -v` |
| Merge reports | `python3 merge.py --dir ./reports` |
| Pull branches | `python3 pull-branches.py < branches.txt` |

## Build & Packaging
- No build step; scripts are run directly with the Python interpreter
- No packaging configuration (setup.py, pyproject.toml, etc.)
- Dependencies installed via pip into the active environment
