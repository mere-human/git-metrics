import subprocess
import sys
import os
import re
import xlsxwriter


def main():
    # Get the data
    extra = ['--since="12 months"']  # TODO: pass as args
    cmd = ['git', 'shortlog', '-esn'] + extra
    result = subprocess.run(cmd, capture_output=True)
    # Process the data.
    slog = result.stdout.decode()
    lines1 = slog.split('\n')
    lines2 = []
    LINE_DATA_COMMITS = 0
    LINE_DATA_AUTHOR = 1
    LINE_DATA_EMAIL = 2
    for l in lines1:
        # Format:
        # number of commits | author | <email>
        m = re.search(r'^\s*(\d+)\s+(.+)\s+<(\S+)>$', l)
        if m:
            lines2.append([int(m.group(1)), m.group(2), m.group(3)])
    # print(lines2)
    # Generate the output.
    email_pattern = 'gmail.com'  # TODO: pass as an arg
    group_rows = []
    output_name = 'result.xlsx'  # TODO: pass as an arg
    workbook = xlsxwriter.Workbook(output_name)
    worksheet = workbook.add_worksheet()
    for i, x in enumerate(lines2):
        ret = worksheet.write_row(
            row=i, col=0, data=[x[LINE_DATA_AUTHOR], x[LINE_DATA_EMAIL], x[LINE_DATA_COMMITS]])
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
        if x[LINE_DATA_EMAIL].endswith(email_pattern):
            group_rows.append(i)
    # Add sum formula.
    stats_row = len(lines2) + 1
    worksheet.write_string(row=stats_row, col=0, string='Total:')
    worksheet.write_formula(row=stats_row, col=2,
                            formula=f'=SUM(C1:C{len(lines2)})')
    # Add group sum.
    if email_pattern and group_rows:
        stats_row += 1
        worksheet.write_string(row=stats_row, col=0,
                               string=f'Total ({email_pattern}):')
        group_cells = ','.join(['C' + str(x) for x in group_rows])
        worksheet.write_formula(row=stats_row, col=2,
                                formula=f'=SUM({group_cells})')

    workbook.close()


if __name__ == '__main__':
    main()
