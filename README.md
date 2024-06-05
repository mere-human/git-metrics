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

## TODO

* Output auto-naming.
