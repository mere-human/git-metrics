
import argparse
import logging
import re
import openpyxl
import xlsxwriter
import os
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)

def parse_args():
    parser = argparse.ArgumentParser(description='Git metrics')
    parser.add_argument('FILES', nargs='*', help='specify file names to merge')
    parser.add_argument('--output', default='merged.xlsx',
                        help='output XLSX file name (default: %(default)s)')
    parser.add_argument('--dir',
                        help='merge all files in a specified directory')

    return parser.parse_args() 


def validate_header(first_row):
    if len(first_row) != 3:
        raise RuntimeError(f'Expect 3 columns')
    if first_row[0].value.lower() != 'author':
        raise RuntimeError(f'Expect author as 1st column')
    if first_row[1].value.lower() != 'email':
        raise RuntimeError(f'Expect email as 2nd column')
    if not first_row[2].value.lower().startswith('commits'):
        raise RuntimeError(f'Expect commits as 3rd column')


def extract_date(file_path):
    name = os.path.basename(file_path)
    m = re.search(r'(\d{2}\.\d{2}\.\d{4})', name)
    if m:
        return m[1]
    # TODO: next try file creation time and then extract from the content
    raise RuntimeError(f'Could not extract date from {file_path}')


def parse(filename):
    book = openpyxl.load_workbook(filename)

    if len(book.worksheets) != 1:
        logging.warning(f'Expect 1 worksheet in {filename}')
        return

    sheet = book.worksheets[0]

    row_data = []
    for i, row in enumerate(sheet.rows):
        if i == 0:
            validate_header(row)
            continue
        cell_data = []
        for cell in row:
            cell_data.append(cell.value)
        # stop at empty rows for now which separate summary rows
        if all(x is None for x in cell_data):
            break
        row_data.append(cell_data)
    return row_data


def insert_row_data(data_by_authors, row_data, column_name):
    for row in row_data:
        author = row[0]
        # email = row[1]
        commits = row[2]
        if author not in data_by_authors:
            data_by_authors[author] = {}
        data_by_authors[author][column_name] = commits


def write_output(output_name, data, columns):
    workbook = xlsxwriter.Workbook(output_name)
    bold = workbook.add_format({"bold": True})
    worksheet = workbook.add_worksheet()

    # Parse and sort columns (dates).
    columns2 = sorted(columns, key=lambda x: datetime.strptime(x, '%d.%m.%Y'))
    
    # Add header.
    row_curr = 0
    worksheet.write_row(row=row_curr, col=0, data=['Author'] + columns2, cell_format=bold)
    worksheet.set_column(first_col=1, last_col=len(columns2), width=len('31.12.1999'))
    row_curr += 1

    # Write rows. Sort authors.
    first_col_len = 0
    for author in sorted(data.keys()):
        data_by_author = data[author]
        row_data = [author]
        for col in columns2:
            if col in data_by_author:
                row_data.append(data_by_author[col])
            else:
                row_data.append(0)

        ret = worksheet.write_row(row=row_curr, col=0, data=row_data)
        row_curr += 1
        if ret != 0:
            raise RuntimeError(f'Failed to write XLSX row: {ret}')

        if len(author) > first_col_len:
            first_col_len = len(author)

    worksheet.set_column(first_col=0, last_col=0, width=first_col_len+1)

    workbook.close()


def process_files(filenames, output_name):
    column_names = []
    data_by_authors = {}
    for filename in filenames:
        row_data = parse(filename)
        column_names.append(extract_date(filename))
        insert_row_data(data_by_authors, row_data, column_names[-1])
    write_output(output_name, data_by_authors, column_names)


def main():
    args = parse_args()
    logging.debug(f'Args: {args}')
    if args.FILES:
        process_files(args.FILES, args.output)
    elif args.dir:
        files = []
        for entry in os.listdir(args.dir):
            entry_path = os.path.join(args.dir, entry)
            if os.path.isfile(entry_path) and os.path.splitext(entry)[1].lower() == '.xlsx':
                files.append(entry_path)
        process_files(files, args.output)


if __name__ == '__main__':
    main()
