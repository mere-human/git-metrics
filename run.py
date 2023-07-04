import subprocess
import re
import xlsxwriter
import enum
import argparse
from datetime import date


class ParsedRow(enum.IntEnum):
    COMMITS = 0
    AUTHOR = 1
    EMAIL = 2


def parse_args():
    parser = argparse.ArgumentParser(description='Git metrics')
    parser.add_argument('--output', default='result.xlsx',
                        help='output XLSX file name (default: %(default)s)')
    parser.add_argument('--group_pattern',
                        help='email regex pattern to match that defines a group to calculate a separate sum')
    parser.add_argument('--since',
                        help='"git shortlog" argument (example: "2 weeks")')
    parser.add_argument('--until',
                        help='"git shortlog" argument (example: "Mar 27 2023 00:00:00")')

    return parser.parse_args()


def extract_data(since, until):
    cmd = ['git', 'shortlog', '-esn']
    if since:
        cmd += [f'--since="{since}"']
    if until:
        cmd += [f'--until="{until}"']
    return subprocess.run(cmd, capture_output=True)


def parse_data(data):
    strdata = data.stdout.decode()
    lines1 = strdata.split('\n')
    lines2 = []
    for l in lines1:
        # Format:
        # number of commits | author | <email>
        m = re.search(r'^\s*(\d+)\s+(.+)\s+<(\S+)>$', l)
        if m:
            lines2.append([int(m.group(ParsedRow.COMMITS+1)),
                          m.group(ParsedRow.AUTHOR+1), m.group(ParsedRow.EMAIL+1)])
    return lines2


def generate_output(parsed, email_pattern, commits_date1, commits_date2, output_name):
    group_rows = []
    workbook = xlsxwriter.Workbook(output_name)
    bold = workbook.add_format({"bold": True})
    worksheet = workbook.add_worksheet()
    # Set Author and Email columns width for readability.
    worksheet.set_column(0, 0, 20)
    worksheet.set_column(1, 1, 25)
    row_curr = 0
    # Add header.
    if not commits_date1:
        today = date.today()
        commits_date1 = today.strftime("%B %d, %Y")
    worksheet.write_row(row=row_curr, col=0, data=[
                        'Author', 'Email', f'Commits on {commits_date1} ({commits_date2})'], cell_format=bold)
    row_curr += 1
    row_data = row_curr
    # Write data.
    for x in parsed:
        ret = worksheet.write_row(
            row=row_curr, col=0, data=[x[ParsedRow.AUTHOR], x[ParsedRow.EMAIL], x[ParsedRow.COMMITS]])
        row_curr += 1
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if re.match(email_pattern, x[ParsedRow.EMAIL]):
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

    workbook.close()


def main():
    args = parse_args()
    data = extract_data(args.since, args.until)
    parsed = parse_data(data)
    generate_output(parsed, email_pattern=args.group_pattern,
                    output_name=args.output, commits_date1=args.until, commits_date2=args.since)


if __name__ == '__main__':
    main()
