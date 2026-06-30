"""Unit tests for merge.py XLSX ingestion."""

import os
import tempfile
import unittest

import xlsxwriter

import merge


def _write_metrics_xlsx(path, rows=None):
    """Write a minimal git-metrics style XLSX file."""
    if rows is None:
        rows = [('Alice', 'alice@example.com', 3)]
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet()
    worksheet.write_row(0, 0, ['Author', 'Email', 'Commits since 01.01.2024'])
    for i, row in enumerate(rows, start=1):
        worksheet.write_row(i, 0, row)
    workbook.close()


class TestParseXlsx(unittest.TestCase):
    """parse() reads valid metrics spreadsheets in read-only mode."""

    def test_parse_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'metrics_01.01.2024.xlsx')
            _write_metrics_xlsx(path, [
                ('Alice', 'alice@example.com', 3),
                ('Bob', 'bob@example.com', 5),
            ])

            rows = merge.parse(path, max_file_size=0)

            self.assertEqual(rows, [
                ['Alice', 'alice@example.com', 3],
                ['Bob', 'bob@example.com', 5],
            ])

    def test_parse_stops_at_empty_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'metrics_01.01.2024.xlsx')
            workbook = xlsxwriter.Workbook(path)
            worksheet = workbook.add_worksheet()
            worksheet.write_row(0, 0, ['Author', 'Email', 'Commits since'])
            worksheet.write_row(1, 0, ['Alice', 'alice@example.com', 1])
            worksheet.write_row(3, 0, ['Bob', 'bob@example.com', 99])
            workbook.close()

            rows = merge.parse(path, max_file_size=0)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], 'Alice')


class TestFileSizeLimit(unittest.TestCase):
    """Oversized input files are rejected when a limit is set."""

    def test_rejects_oversized_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'metrics_01.01.2024.xlsx')
            _write_metrics_xlsx(path)

            with self.assertRaisesRegex(RuntimeError, 'File too large'):
                merge.parse(path, max_file_size=1)

    def test_no_limit_when_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'metrics_01.01.2024.xlsx')
            _write_metrics_xlsx(path)

            rows = merge.parse(path, max_file_size=0)

            self.assertEqual(len(rows), 1)


if __name__ == '__main__':
    unittest.main()
