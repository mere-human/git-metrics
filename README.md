# git-metrics
Tool for gathering metrics from a git repostory.
Generates XLSX spreadsheets with commits by authors and a sum of all commits.
Optinally, can group some users by email domain and generate a sum for them.

**Sample:**

`python3 run.py --group_domain 'gmail.com' --since '36 months'`

## Install
`pip3 install -r requirements.txt`

