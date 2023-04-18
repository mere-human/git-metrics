# git-metrics
A tool for gathering metrics from a git repository.
Generates XLSX spreadsheets with commits by authors and a sum of all commits.
Optionally, can group some users by email domain and generate a sum for them.

**Example:**

`python3 run.py --group_domain 'gmail.com' --since '36 months'`

## Install
`pip3 install -r requirements.txt`

## TODO

* Output auto-naming.
* Unit tests.
