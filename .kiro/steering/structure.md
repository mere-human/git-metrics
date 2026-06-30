# Project Structure

```
git-metrics/
├── run.py              # Main entry point — parses git log, generates XLSX report
├── merge.py            # Merges multiple period XLSX reports into one spreadsheet
├── pull-branches.py    # Helper to pull/checkout multiple branches from remote
├── test_run.py         # Unit tests for run.py (parsing and config logic)
├── requirements.txt    # Python dependencies
├── settings.json       # VS Code unittest configuration
├── README.md           # Usage documentation
└── .gitignore          # Standard Python gitignore
```

## Architecture Notes

- Flat structure with no packages or subdirectories for source code
- Each script is self-contained with its own `main()` and `argparse` setup
- `run.py` contains all core logic: argument parsing, git log execution, log parsing, XLSX generation, and config management
- `merge.py` is an independent utility that reads XLSX files produced by `run.py`
- `pull-branches.py` is a standalone helper with no shared code
- Tests live alongside source in `test_run.py` and import directly from `run.py`
- Config files (`git-metrics.json`) are generated at runtime and gitignored
