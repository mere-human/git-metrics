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
    for l in lines1:
        # Format:
        # number of commits | author | <email>
        m = re.search(r'^\s*(\d+)\s+(.+)\s+<(\S+)>$', l)
        if m:
            lines2.append(m.groups())
    # print(lines2)
    # Generate the output.
    workbook = xlsxwriter.Workbook('result.xlsx')
    worksheet = workbook.add_worksheet()
    for i, x in enumerate(lines2):
        ret = worksheet.write_row(i, 0, x)
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')
    workbook.close()


if __name__ == '__main__':
    main()
