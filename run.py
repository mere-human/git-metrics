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
    parser.add_argument('--group_domain',
                        help='email domain that defines a group to calculate a separate sum')
    parser.add_argument('--since', default='12 months',
                        help='"git shortlog" argument (default: %(default)s)')

    return parser.parse_args()


def extract_data(since):
    extra = [f'--since="{since}"']
    cmd = ['git', 'shortlog', '-esn'] + extra
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


def generate_output(parsed, email_pattern, commits_detail, output_name):
    group_rows = []
    workbook = xlsxwriter.Workbook(output_name)
    bold = workbook.add_format({"bold": True})
    worksheet = workbook.add_worksheet()
    row_curr = 0
    # Add header.
    today = date.today()
    today = today.strftime("%B %d, %Y")
    worksheet.write_row(row=row_curr, col=0, data=[
                        'Author', 'Email', f'Commits on {today} ({commits_detail})'], cell_format=bold)
    row_curr += 1
    row_data = row_curr
    # Write data.
    for x in parsed:
        ret = worksheet.write_row(
            row=row_curr, col=0, data=[x[ParsedRow.AUTHOR], x[ParsedRow.EMAIL], x[ParsedRow.COMMITS]])
        row_curr += 1
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if x[ParsedRow.EMAIL].endswith(email_pattern):
            group_rows.append(row_curr)
    # Add sum formula.
    row_curr += 1
    worksheet.write_string(row=row_curr, col=0,
                           string='Total:', cell_format=bold)
    worksheet.write_formula(row=row_curr, col=2,
                            formula=f'=SUM(C{row_data+1}:C{row_data+len(parsed)})')
    # Add group sum.
    if email_pattern and group_rows:
        row_curr += 1
        worksheet.write_string(row=row_curr, col=0,
                               string=f'Total ({email_pattern}):', cell_format=bold)
        group_cells = ','.join(['C' + str(x) for x in group_rows])
        worksheet.write_formula(row=row_curr, col=2,
                                formula=f'=SUM({group_cells})')

    workbook.close()


def main():
    args = parse_args()
    data = extract_data(args.since)
    parsed = parse_data(data)
    generate_output(parsed, email_pattern=args.group_domain,
                    output_name=args.output, commits_detail=args.since)


if __name__ == '__main__':
    main()
