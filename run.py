import subprocess
import re
import xlsxwriter
import enum


class ParsedRow(enum.IntEnum):
    COMMITS = 0
    AUTHOR = 1
    EMAIL = 2


def extract_data():
    extra = ['--since="12 months"']  # TODO: pass as args
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


def generate_output(parsed, email_pattern, output_name):
    group_rows = []
    workbook = xlsxwriter.Workbook(output_name)
    worksheet = workbook.add_worksheet()
    for i, x in enumerate(parsed):
        ret = worksheet.write_row(
            row=i, col=0, data=[x[ParsedRow.AUTHOR], x[ParsedRow.EMAIL], x[ParsedRow.COMMITS]])
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if x[ParsedRow.EMAIL].endswith(email_pattern):
            group_rows.append(i)
    # Add sum formula.
    stats_row = len(parsed) + 1
    worksheet.write_string(row=stats_row, col=0, string='Total:')
    worksheet.write_formula(row=stats_row, col=2,
                            formula=f'=SUM(C1:C{len(parsed)})')
    # Add group sum.
    if email_pattern and group_rows:
        stats_row += 1
        worksheet.write_string(row=stats_row, col=0,
                               string=f'Total ({email_pattern}):')
        group_cells = ','.join(['C' + str(x) for x in group_rows])
        worksheet.write_formula(row=stats_row, col=2,
                                formula=f'=SUM({group_cells})')

    workbook.close()


def main():
    # Get the data
    data = extract_data()
    # Process the data.
    parsed = parse_data(data)
    # Generate the output.
    # TODO: pass as args
    generate_output(parsed, email_pattern='gmail.com',
                    output_name='result.xlsx')


if __name__ == '__main__':
    main()
