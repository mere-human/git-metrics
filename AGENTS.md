# git-metrics — Agent Guide

CLI tool that parses `git log`, deduplicates commits by Change-Id, and generates XLSX spreadsheets with per-author commit counts.

## Architecture

Flat Python project — no packages, no build step. Each script is self-contained with its own `main()` and `argparse` setup.

| File | Role |
|------|------|
| `run.py` | Main entry: git log execution, parsing, XLSX generation, config workflow |
| `merge.py` | Merges multiple period XLSX reports into one spreadsheet |
| `pull-branches.py` | Pulls/checkout multiple remote branches before analysis |
| `setup.py` | Creates `.venv` and installs dependencies |
| `run-env.py` | Runs any script inside `.venv` without manual activation |
| `test_run.py` | Unit tests for `run.py` parsing and config logic |

## Commands

Prefer the isolated environment when `.venv` exists:

```bash
python3 setup.py                                          # one-time setup
python3 run-env.py run.py --since "2 weeks"             # run in venv
python3 run-env.py merge.py --dir ./reports
python3 -m unittest test_run -v                          # run tests
python3 run.py --test                                     # alternative test entry
```

Without venv: `python3 run.py --since "2 weeks"` (requires `pip3 install -r requirements.txt`).

## Testing

- Framework: `unittest` (stdlib)
- Tests import directly from `run.py` (`from run import *`)
- Run after any change to parsing, config, or XLSX logic
- Test data uses realistic git log fixtures with Change-Id trailers

## Conventions

- Python 3, stdlib-first; dependencies limited to XlsxWriter and openpyxl
- Optional type hints on function signatures; no enforced mypy
- `logging` for warnings (missing Change-Id, duplicate subjects)
- Config files (`git-metrics.json`) are runtime-generated and gitignored
- Do not add packaging (pyproject.toml) — scripts run directly by design

## Agent workflow

1. Read this file and `.cursor/rules/` before making changes
2. Use `run-env.py` for running scripts when `.venv` is present
3. Run `python3 -m unittest test_run -v` after editing Python source
4. Keep changes minimal and match existing flat-script style
5. Do not run destructive git commands (`push --force`, `reset --hard`, etc.)
