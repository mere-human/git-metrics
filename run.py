# WARNING: do not forget to update all branches before running.
# You may use the "pull-branches.py" script.

from datetime import date
from datetime import datetime
from datetime import timedelta
import argparse
import json
import logging
import os
import os.path
import re
import subprocess
import sys
import unittest
import xlsxwriter

logging.basicConfig(level=logging.INFO)

MAX_LOG_LEN = 190

STRICT_CHECKS = False
_CONFIG_FILE_NAME = "git-metrics.json"
_CONFIG_DATE_FORMAT = '%b %d %Y'


class SummaryEntry:
    def __init__(self, commit_sum: int, author_name: str, author_email: str):
        self.commit_sum = commit_sum
        self.author_name = author_name
        self.author_email = author_email

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return f'{self.commit_sum} {self.author_name} {self.author_email}'


def parse_args(args=None):
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
    parser.add_argument('--config_write', action='store_true',
                        help=f'writes a "{_CONFIG_FILE_NAME}" config file based on input arguments')
    parser.add_argument('--config_use', action='store_true',
                        help=f'reads the "{_CONFIG_FILE_NAME}" config file to use as arguments')
    parser.add_argument('--config',
                        help=f'specifies path to the config file')

    return parser.parse_args(args)

# https://git-scm.com/docs/git-log
# https://git-scm.com/docs/pretty-formats


def run_log(since, until, author, globs):
    # %h - abbreviated commit hash
    # %ae - author email
    # %an - author name
    # %s - subject
    # %(trailers[:<options>]) - display the trailers of the body
    # we could have used "%(trailers:key=Change-Id)" here but if it is not separated by a newline from the message, then it won't be parsed :(
    cmd = ['git', 'log',  '--no-merges',
           '--format=Hash:%h Email:%ae Name:%an Subj:%s Body:%b<end-of-commit-message>']
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
        items = ", ".join(
            f"{k}={repr(self.__dict__[k])}" for k in sorted(self.__dict__))
        return f"{type(self).__name__}({items})"


def parse_entry(line: str, line_num: int, filter_author: str = None) -> LogEntry:
    if not line.strip():
        return None

    logging.debug(f'parse_entry:{line}'[:MAX_LOG_LEN])
    m = re.search(
        r'^Hash:(\S+)\s+Email:(\S+)\s+Name:(.+)\s+Subj:(.+)\s+Body:', line)
    if not m:
        raise RuntimeError(f'Could not parse at line {line_num}: {line}')
    entry = LogEntry(hash=m.group(1), change_id='', mail=m.group(
        2).lower(), name=m.group(3).strip(), subj=m.group(4).strip())

    if entry.mail == filter_author:
        return None

    if re.search(r'cherry.pick', line, re.I):
        entry.cherry_pick = True

    # extract change-id trailer
    results = re.findall(r'Change-Id:\s*(\S+)', line)
    if results:
        if len(results) > 1:
            logging.warning(
                f'Multiple Change-Id in {entry.hash} is unexpected. Using the last occurence.')
        entry.change_id = results[-1]
    else:
        entry.change_id = entry.hash  # use a fallback
        logging.warning(
            f'No change ID in {entry.hash} at line {line_num} ({line[:MAX_LOG_LEN]}), using hash.')

    return entry


def parse_log(data, filter_author=None, merge_by_email=True):
    if filter_author:
        filter_author = filter_author.lower()
    strdata = data if type(data) is str else data.stdout.decode()
    lines = strdata.split('<end-of-commit-message>\n')

    entries = []
    data_by_id = {}
    data_by_author = {}
    author_emails = {}

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
                if (existing.subj in entry.subj or entry.subj in existing.subj) or not STRICT_CHECKS:
                    # if one subject is a subset of another, it's not critical (e.g. cherry-pick)
                    logging.warning(
                        f'Commits with the same ID differ (keeping 1st)')
                    logging.warning(f'1. {existing}'[:MAX_LOG_LEN])
                    logging.warning(f'2. {entry}'[:MAX_LOG_LEN])
                else:
                    raise RuntimeError(
                        f'Commits with the same ID differ: {existing} != {entry}')
        else:
            data_by_id[entry.change_id] = entry

        # check author
        author = entry.mail if merge_by_email else entry.name
        if not merge_by_email:
            emails = author_emails.get(author)
            if emails:
                if len(emails) > 1:
                    logging.warning(
                        f'Same author has different emails: {author}, {emails}')
                emails.add(entry.mail)
            else:
                author_emails[author] = {entry.mail}

        # check that subject is correct
        data_by_subj = data_by_author.get(author)
        if data_by_subj:
            existing = data_by_subj.get(entry.subj)
            if existing:
                if existing.change_id != entry.change_id:
                    logging.warning(
                        f'Commits with the same subject differ (keeping 1st)')
                    logging.warning(f'1. {existing}'[:MAX_LOG_LEN])
                    logging.warning(f'2. {entry}'[:MAX_LOG_LEN])
            else:
                data_by_subj[entry.subj] = entry
        else:
            data_by_author[author] = {entry.subj: entry}

    logging.info(f'Total commits: {len(entries)}')
    logging.info(f'Commits by change-ID: {len(data_by_id)}')
    logging.info(f'Authors: {len(data_by_author)}')
    for x in entries:
        logging.debug(x)

    # generate summary with number of commits
    summaries = []
    for author in data_by_author:
        data_by_subj = data_by_author[author]
        if data_by_subj:
            data = next(iter(data_by_subj.values()))  # pick any entry
            if merge_by_email:
                mail_data = author
            else:
                mail_data = ';'.join(sorted(author_emails[author]))
            summaries.append(
                SummaryEntry(
                    commit_sum=len(data_by_subj),
                    author_email=mail_data,
                    author_name=data.name if merge_by_email else author,
                )
            )

    # TODO: move this to generate_output and add corresponding tests
    summaries.sort(key=lambda x: x.author_name)

    return summaries


def generate_output(parsed: 'list[SummaryEntry]', args, email_pattern, since, until, output_name):
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
    sum_group = 0
    sum_all = 0
    # Write data.
    for x in parsed:
        ret = worksheet.write_row(
            row=row_curr, col=0, data=[x.author_name, x.author_email, x.commit_sum])
        row_curr += 1
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if email_pattern and re.match(email_pattern, x.author_email):
            group_rows.append(row_curr)
            sum_group += x.commit_sum
        sum_all += x.commit_sum
    # Add sum formula.
    row_curr += 1
    worksheet.write_string(row=row_curr, col=0,
                           string='Sum all:', cell_format=bold)
    worksheet.write_formula(row=row_curr, col=2,
                            formula=f'=SUM(C{row_data+1}:C{row_data+len(parsed)})')
    logging.info(f'Sum all: {sum_all}')
    # Add group sum.
    if email_pattern and group_rows:
        row_curr += 1
        worksheet.write_string(row=row_curr, col=0,
                               string=f'Sum group ({len(group_rows)}):', cell_format=bold)
        worksheet.write_string(row=row_curr, col=1, string=f'{email_pattern}')
        group_cells = ','.join(['C' + str(x) for x in group_rows])
        worksheet.write_formula(row=row_curr, col=2,
                                formula=f'=SUM({group_cells})')
        logging.info(f'Sum group: {sum_group}')

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


def config_create(args):
    if not args.since:
        logging.warning("No starting date, needed by config")
        return {}
    start_date = datetime.strptime(args.since, _CONFIG_DATE_FORMAT).date()
    if not args.until:
        logging.warning("No ending date, needed by config")
        return {}
    end_date = datetime.strptime(args.until, _CONFIG_DATE_FORMAT).date()
    config_data = {}
    config_data["last_date"] = end_date
    config_data["delta_days"] = (end_date - start_date).days

    if args.glob:
        config_data["glob"] = args.glob
    if args.group_pattern:
        config_data["group_pattern"] = args.group_pattern
    if args.exclude_author:
        config_data["exclude_author"] = args.exclude_author
    return config_data


def config_write(config_data, file_name=_CONFIG_FILE_NAME):
    if not config_data:
        logging.warning("Failed to generate config file")
        return

    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.strftime(_CONFIG_DATE_FORMAT)
        raise TypeError("Type %s not serializable" % type(obj))

    with open(file_name, "w") as f:
        json.dump(config_data, f, default=json_serial, indent=2)


def config_read(file_name=_CONFIG_FILE_NAME):
    if not os.path.isfile(file_name):
        raise RuntimeError(f"Config file not found {file_name}")
    with open(file_name) as f:
        config_data = json.load(f)
        return config_data
    raise RuntimeError(f"Failed to read config file {file_name}")


def config_update_args(config_data, args):
    key_list = ["glob", "group_pattern", "exclude_author"]
    for k in key_list:
        if k in config_data:
            setattr(args, k, config_data[k])

    args.since = config_data["last_date"]
    delta_days = timedelta(days=config_data["delta_days"])
    end_date = datetime.strptime(
        args.since, _CONFIG_DATE_FORMAT).date() + delta_days
    config_data["last_date"] = end_date
    args.until = end_date.strftime(_CONFIG_DATE_FORMAT)

    if "output_pattern" in config_data:
        args.output = end_date.strftime(config_data["output_pattern"])

    logging.debug(args)


def main():
    args = parse_args()
    logging.debug(f'Args: {args}')
    if args.test:
        return unittest.main(argv=[sys.argv[0]], module='test_run')

    config_data = {}
    config_name = args.config if args.config else _CONFIG_FILE_NAME
    if args.config_write:
        config_data = config_create(args)
    elif args.config_use or args.config:
        config_data = config_read(config_name)
        config_update_args(config_data, args)

    data = run_log(args.since, args.until, args.author, args.glob)
    parsed = parse_log(data, args.exclude_author, merge_by_email=True)
    generate_output(parsed, args, email_pattern=args.group_pattern,
                    output_name=args.output, since=args.since, until=args.until)

    if args.config_write or args.config_use or args.config:
        config_write(config_data, file_name=config_name)


if __name__ == '__main__':
    main()
