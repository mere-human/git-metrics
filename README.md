# git-metrics
A tool for gathering metrics from a git repository.
Generates XLSX spreadsheets with commits by authors and a sum of all commits.
Optionally, it can group some users by email domain and generate a sum for those groups. 

# Install
`pip3 install -r requirements.txt`

# Run

Example: `python3 run.py --group_domain 'gmail.com' --since '36 months'`.

For more info, see the help: `python3 run.py --help`.

## Multiple branches

1. Pull branches from remote, if necessary.
For that, you can use a helper script `pull-branches.py`.
You can prepare a text file (say "branches.txt") with a list of branches to pull, each branch on a new line.
Then run `python pull-branches.py < branches.txt`.
It will pull remote branches and create corresponding local branches if necessary.
Warning: If there are a lot of branches, the process will take some time.

2. Specify a pattern for branches.
Add arguments such as `--glob="*Features*" --glob=master`.

## Config file

If you generate reports often with most of the arguments unchanged, you can simplify it by using the config file.

1. Create a config file by adding the `--config_write` file. 

`python run.py --group_pattern ".*gmail.com" --since "Jan 1 2025" --until "Feb 1 2025" --config_write`

* It will create a "git-metrics.json" file in the current directory. The file will contain all relevant reusable arguments. Note that `--until` is used as a last updated date so it should be a date, not a period.

```json
{
  "last_date": "Feb 01 2025",
  "delta_days": 31,
  "group_pattern": ".*gmail.com"
}
```

2. Use the existing config file next time.
`python3 run.py --config_use`

* Most of the args can be omitted. You can still specify the output name. "last_date" is updated each time.


## Merging periods

`run.py` provides info on a single specified period. If you want to create a table consisting of multiple periods, you can use the `merge.py` script.
Just specify a list of XLSX files (or a directory with files) and it will produce a table where columns correspond to data from each file.
For more, see `merge.py --help` or its sources.

## Dependency Isolation

The project supports running in an isolated virtual environment so that its dependencies do not interfere with your system Python packages.

**Prerequisite:** Python 3 must be installed on your system.

### Setup

Run the setup script to create the isolated environment:

`python3 setup.py`

This creates a `.venv` directory at the project root with all dependencies from `requirements.txt` installed.

### Running scripts

Use the runner script to execute any git-metrics command inside the isolated environment without manual activation:

`python3 run-env.py run.py --since "2 weeks"`

### Running tests

`python3 run-env.py run.py --test`

Without the venv wrapper: `python3 -m unittest test_run -v` or `python3 run.py --test`.

If you prefer to activate the environment yourself:

- **Unix (Linux/macOS):** `source .venv/bin/activate`
- **Windows:** `.venv\Scripts\activate`

Once activated, run scripts directly (e.g. `python run.py --since "2 weeks"`). Deactivate with `deactivate`.

## TODO

* Easier to run by default:
  * Detect periods automatically
  * Sane default arguments.
