# WARNING: do not forget to update all branches before running.
# You may use the "pull-branches.py" script.

import subprocess
import re
import xlsxwriter
import argparse
from datetime import date
from types import SimpleNamespace
import logging
import unittest
import sys

logging.basicConfig(level=logging.DEBUG)

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

class TestParsing(unittest.TestCase):
    def runTest(self):
        # single entry with lots of details
        log ="""Hash:1fba683b56e Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change fixes a crash.
This is because we have a signature mismatch.

Bug: ID-1234

Platforms: All
Test:
1. Build
2. Run
Change-Id: I4b3d81d5a3fc8b5145022e6d219499b7f70a60d3
Reviewed-on: https://example.com
Reviewed-by: Dr Who <drwho@example.com>
Tested-by: Build Verifier <build@example.com>
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])

        # several entries
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix 1 Body:The change
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix 2 Body:The change
Change-Id: i002
<end-of-commit-message>
Hash:456 Email:drwho@example.com Name:Dr Who  Subj:Fix 3 Body:The change
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(2, 'John Doe', 'john.doe@example.com'), SummaryEntry(1, 'Dr Who', 'drwho@example.com')])

        # no change-id
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])

        # same change-id
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])

        # same subjects, diff change-id
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i002
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])

        # same change-id, diff subject
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Test Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

        # multiple change-id
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
Change-Id: i004
<end-of-commit-message>
"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

        # invlid input
        log ="""hello"""
        with self.assertRaises(RuntimeError):
            parse_log(log)


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

def parse_log(data, filter_author=None):
    if filter_author:
        filter_author = filter_author.lower()
    strdata = data if type(data) is str else data.stdout.decode()
    lines1 = strdata.split('<end-of-commit-message>\n')

    lines2 = []
    data_by_id = {}
    data_by_author = {}

    entry = None
    # Example: Hash:41bceac95b7 Email:john.doe@example.com Name:John Doe Subj:test Body:x
    # Subj: could be either on the same line or as a new line
    for i, line in enumerate(lines1):
        m = re.search(r'^Hash:(\S+)\s+Email:(\S+)\s+Name:(.+)\s+Subj:(.+)\s+Body:', line)
        if m:
            entry = SimpleNamespace(hash = m.group(1), mail = m.group(2).lower(), name=m.group(3).strip(), subj = m.group(4).strip())

            if filter_author and filter_author == entry.mail:
                entry = None
                continue

            # extract change-id trailer
            m = re.search(r'\nChange-Id:\s*(\S+)', line)
            if m:
                entry.change_id = m.group(1)
                if 'Change-Id' in line[m.end():]:
                    raise RuntimeError('Multiple Change-Id is unexpected')
            else:
                entry.change_id = entry.hash  # use a fallback
                logging.warning(f'No change id at line {i}: {line}')

            lines2.append(entry)

            # check that change-id correct
            existing = data_by_id.get(entry.change_id)
            if existing:
                if existing.mail != entry.mail or existing.subj != entry.subj:
                    raise RuntimeError('Commits with the same ID differ:', existing, '!=', entry)
            else:
                data_by_id[entry.change_id] = entry

            # check that subject is correct
            data_by_subj = data_by_author.get(entry.mail)
            if data_by_subj:
                existing = data_by_subj.get(entry.subj)
                if existing:
                    if existing.change_id != entry.change_id:
                        logging.warning(f'Commits with the same subject differ:\n  {existing}\n  {entry}')
                else:
                    data_by_subj[entry.subj] = entry
            else:
                data_by_author[entry.mail] = {entry.subj: entry}

            # reset for next iteration
            entry = None
        else:
            if line.strip():
                raise RuntimeError(f'Could not parse at line {i}: {line}')
            entry = None
            continue

    for x in lines2:
        logging.debug(x)

    # generate summary with number of commits
    summaries = []
    for mail in data_by_author:
        data_by_subj = data_by_author[mail]
        if data_by_subj:
            name = next(iter(data_by_subj.values())).name # pick any entry
            summaries.append(SummaryEntry(len(data_by_subj), name, mail))

    return summaries

def generate_output(parsed:list[SummaryEntry], args, email_pattern, since, until, output_name):
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
        return unittest.main(argv=[sys.argv[0]])

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
