# WARNING: do not forget to update all branches before running.
# You may use the "pull-branches.py" script.

import subprocess
import re
import xlsxwriter
import argparse
from datetime import date
import logging
import unittest
import sys

logging.basicConfig(level=logging.INFO)

MAX_LOG_LEN = 190

class SummaryEntry:
    def __init__(self, commit_sum: int, author_name: str, author_email: str):
        self.commit_sum = commit_sum
        self.author_name = author_name
        self.author_email = author_email
    def __eq__(self, other):
        return repr(self) == repr(other)
    def __repr__(self):
        return f'{self.commit_sum} {self.author_name} {self.author_email}'


def parse_args():
    parser = argparse.ArgumentParser(description='Git metrics')
    parser.add_argument('--output', default='result.xlsx',
                        help='output XLSX file name (default: %(default)s)')
    parser.add_argument('--since',
                        help='git argument: starting date (example: "2 weeks")')
    parser.add_argument('--until',
                        help='git argument: ending date (example: "Mar 27 2023 00:00:00")')
    parser.add_argument('--author',
                        help='git argument: limit the commits output to ones with specified email')
    parser.add_argument('--glob', nargs='*', action='extend',
                        help='git argument: pattern to match refs; filters branches (example: "*Features*")')
    parser.add_argument('--group_pattern',
                        help='email regex pattern that defines a group to calculate a separate sum')
    parser.add_argument('--exclude_author',
                        help='skip commits from a specified author email')
    parser.add_argument('--test', action='store_true',
                        help='run unit tests')

    return parser.parse_args()

# https://git-scm.com/docs/git-shortlog
def run_shortlog(since, until, author, globs):
    #-n,--numbered  Sort output according to the number of commits per author instead of author alphabetic order.
    # -s,--summary  Suppress commit description and provide a commit count summary only.
    # -e,--email  Show the email address of each author.
    cmd = ['git', 'shortlog', '-esn', '--no-merges']
    if since:
        cmd += [f'--since="{since}"']
    if until:
        cmd += [f'--until="{until}"']
    if author:
        cmd += [f'--author={author}']
    for g in globs:
        cmd += [f'--glob={g}']
    return subprocess.run(cmd, capture_output=True)

def parse_shortlog(data):
    strdata = data.stdout.decode()
    lines1 = strdata.split('\n')
    lines2 = []
    for l in lines1:
        # Example:
        # 99 John Doe <john.doe@example.com>
        m = re.search(r'^\s*(\d+)\s+(.+)\s+<(\S+)>$', l)
        if m:
            lines2.append(SummaryEntry(int(m.group(1)), m.group(2), m.group(3)))
    return lines2

# https://git-scm.com/docs/git-log
# https://git-scm.com/docs/pretty-formats
def run_log(since, until, author, globs):
    # %h - abbreviated commit hash
    # %ae - author email
    # %an - author name
    # %s - subject
    # %(trailers[:<options>]) - display the trailers of the body
    # we could have used "%(trailers:key=Change-Id)" here but if it is not separated by a newline from the message, then it won't be parsed :(
    cmd = ['git', 'log',  '--no-merges', '--format=Hash:%h Email:%ae Name:%an Subj:%s Body:%b<end-of-commit-message>']
    if since:
        cmd += [f'--since="{since}"']
    if until:
        cmd += [f'--until="{until}"']
    if author:
        cmd += [f'--author={author}']
    if globs:
        for g in globs:
            cmd += [f'--glob={g}']
    return subprocess.run(cmd, capture_output=True)

class LogEntry:
    def __init__(self, hash, change_id, mail, name, subj):
        self.hash = hash
        self.change_id = change_id
        self.mail = mail
        self.name = name
        self.subj = subj
    def __str__(self):
        items = ", ".join(f"{k}={repr(self.__dict__[k])}" for k in sorted(self.__dict__))
        return f"{type(self).__name__}({items})"

def parse_entry(line: str, line_num: int, filter_author: str = None) -> LogEntry:
    if not line.strip():
        return None

    m = re.search(r'^Hash:(\S+)\s+Email:(\S+)\s+Name:(.+)\s+Subj:(.+)\s+Body:', line)
    if not m:
        raise RuntimeError(f'Could not parse at line {line_num}: {line}')
    entry = LogEntry(hash = m.group(1), change_id = '', mail = m.group(2).lower(), name=m.group(3).strip(), subj = m.group(4).strip())

    if entry.mail == filter_author:
        return None

    if re.search(r'cherry.pick', line, re.I):
        entry.cherry_pick = True

    # extract change-id trailer
    m = re.search(r'Change-Id:\s*(\S+)', line)
    if m:
        entry.change_id = m.group(1)
        if 'Change-Id' in line[m.end():]:
            raise RuntimeError('Multiple Change-Id is unexpected')
    else:
        entry.change_id = entry.hash  # use a fallback
        logging.warning(f'No change id at line {line_num}: {line}')

    return entry


def parse_log(data, filter_author=None):
    if filter_author:
        filter_author = filter_author.lower()
    strdata = data if type(data) is str else data.stdout.decode()
    lines = strdata.split('<end-of-commit-message>\n')

    entries = []
    data_by_id = {}
    data_by_author = {}

    # Example: Hash:41bceac95b7 Email:john.doe@example.com Name:John Doe Subj:test Body:x
    # Subj: could be either on the same line or as a new line
    for i, line in enumerate(lines):
        entry = parse_entry(line, i, filter_author)
        if not entry:
            continue
        entries.append(entry)

        # check that change-id is correct
        existing = data_by_id.get(entry.change_id)
        if existing:
            if existing.mail != entry.mail or existing.subj != entry.subj:
                if existing.subj in entry.subj or entry.subj in existing.subj:
                    # if one subject is a subset of another, it's not critical (e.g. cherry-pick)
                    logging.warning(f'Commits with the same ID differ (keeping 1st)')
                    logging.warning(f'1. {existing}'[:MAX_LOG_LEN])
                    logging.warning(f'2. {entry}'[:MAX_LOG_LEN])
                else:
                    raise RuntimeError('Commits with the same ID differ:', existing, '!=', entry)
        else:
            data_by_id[entry.change_id] = entry

        # check that subject is correct
        data_by_subj = data_by_author.get(entry.mail)
        if data_by_subj:
            existing = data_by_subj.get(entry.subj)
            if existing:
                if existing.change_id != entry.change_id:
                    logging.warning(f'Commits with the same subject differ (keeping 1st)')
                    logging.warning(f'1. {existing}'[:MAX_LOG_LEN])
                    logging.warning(f'2. {entry}'[:MAX_LOG_LEN])
            else:
                data_by_subj[entry.subj] = entry
        else:
            data_by_author[entry.mail] = {entry.subj: entry}
    

    logging.info(f'Total entries: {len(entries)}')
    logging.info(f'Unique entries: {len(data_by_id)}')
    logging.info(f'Authors: {len(data_by_author)}')
    for x in entries:
        logging.debug(x)

    # generate summary with number of commits
    summaries = []
    for mail in data_by_author:
        data_by_subj = data_by_author[mail]
        if data_by_subj:
            name = next(iter(data_by_subj.values())).name # pick any entry
            summaries.append(SummaryEntry(len(data_by_subj), name, mail))

    return summaries

def generate_output(parsed:'list[SummaryEntry]', args, email_pattern, since, until, output_name):
    group_rows = []
    workbook = xlsxwriter.Workbook(output_name)
    bold = workbook.add_format({"bold": True})
    worksheet = workbook.add_worksheet()
    # Set Author and Email columns width for readability.
    worksheet.set_column(0, 0, 20)
    worksheet.set_column(1, 1, 25)
    row_curr = 0
    # Add header.
    date_part = ''
    if since:
        date_part += f'since {since} '
    if until:
        date_part += f'until {until}'
    worksheet.write_row(row=row_curr, col=0, data=[
                        'Author', 'Email', f'Commits {date_part}'], cell_format=bold)
    row_curr += 1
    row_data = row_curr
    # Write data.
    for x in parsed:
        ret = worksheet.write_row(
            row=row_curr, col=0, data=[x.author_name, x.author_email, x.commit_sum])
        row_curr += 1
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if email_pattern and re.match(email_pattern, x.author_email):
            group_rows.append(row_curr)
    # Add sum formula.
    row_curr += 1
    worksheet.write_string(row=row_curr, col=0,
                           string='Sum all:', cell_format=bold)
    worksheet.write_formula(row=row_curr, col=2,
                            formula=f'=SUM(C{row_data+1}:C{row_data+len(parsed)})')
    # Add group sum.
    if email_pattern and group_rows:
        row_curr += 1
        worksheet.write_string(row=row_curr, col=0,
                               string=f'Sum group ({len(group_rows)}):', cell_format=bold)
        worksheet.write_string(row=row_curr, col=1, string=f'{email_pattern}')
        group_cells = ','.join(['C' + str(x) for x in group_rows])
        worksheet.write_formula(row=row_curr, col=2,
                                formula=f'=SUM({group_cells})')

    # Footer info.
    row_curr += 2
    detail_info = f'Generated on {date.today().strftime("%B %d, %Y")}'
    if args.author:
        detail_info += f' for author {args.author}'
    if args.glob:
        detail_info += f' with globs {",".join(args.glob)}'
    ret = worksheet.write_string(row=row_curr, col=0, string=detail_info)
    if ret != 0:
        raise RuntimeError(f'Failed to write XLSX row: {ret}')

    workbook.close()

def main():
    args = parse_args()
    logging.debug(f'Args: {args}')
    if args.test:
        return unittest.main(argv=[sys.argv[0]], module='test_run')

    if 0: # legacy
        data = run_shortlog(args.since, args.until, args.author, args.glob)
        parsed = parse_shortlog(data)
    else:
        data = run_log(args.since, args.until, args.author, args.glob)
        parsed = parse_log(data, args.exclude_author)
    generate_output(parsed, args, email_pattern=args.group_pattern,
                    output_name=args.output, since=args.since, until=args.until)


if __name__ == '__main__':
    main()
