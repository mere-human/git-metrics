from run import *
import tempfile
import unittest

class TestParsing(unittest.TestCase):
    def test_single_entry(self):
        # single entry with lots of details
        log = """Hash:1fba683b56e Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change fixes a crash.
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
        self.assertEqual(
            parse_log(log), [SummaryEntry(1, "John Doe", "john.doe@example.com")]
        )

    def test_several_entries(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix 1 Body:The change
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix 2 Body:The change
Change-Id: i002
<end-of-commit-message>
Hash:456 Email:drwho@example.com Name:Dr Who  Subj:Fix 3 Body:The change
Change-Id: i003
<end-of-commit-message>
Hash:789 Email:wewe@example.com Name:We we  Subj:Fix 4 Body:We change
Change-Id: i004
<end-of-commit-message>
"""
        self.assertEqual(
            parse_log(log),
            [
                SummaryEntry(1, "Dr Who", "drwho@example.com"),
                SummaryEntry(2, "John Doe", "john.doe@example.com"),
                SummaryEntry(1, "We we", "wewe@example.com"),
            ],
        )

    def test_no_change_id(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            self.assertEqual(
                parse_log(log), [SummaryEntry(1, "John Doe", "john.doe@example.com")]
            )
            self.assertEqual(len(l.output), 1)
            self.assertIn("No change id at line", l.output[0])

    def test_same_change_id(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(
            parse_log(log), [SummaryEntry(1, "John Doe", "john.doe@example.com")]
        )

    def test_same_subj_diff_change_id(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i002
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            self.assertEqual(
                parse_log(log), [SummaryEntry(1, "John Doe", "john.doe@example.com")]
            )
            self.assertEqual(len(l.output), 3)
            self.assertIn("Commits with the same subject differ", l.output[0])

            self.assertIn("i001", l.output[1])
            self.assertIn("Fix crash", l.output[1])

            self.assertIn("i002", l.output[2])
            self.assertIn("Fix crash", l.output[2])

    def test_same_change_id_diff_subj(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Test Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            parse_log(log)
            self.assertEqual(len(l.output), 3)
            self.assertIn("Commits with the same ID differ (keeping 1st)", l.output[0])
            self.assertIn("i003", l.output[1])
            self.assertIn("Fix crash", l.output[1])

            self.assertIn("i003", l.output[2])
            self.assertIn("Test", l.output[2])

    def test_same_change_id_similar_subj(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash (cherry-pick) Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            parse_log(log)
            self.assertEqual(len(l.output), 3)
            self.assertIn("Commits with the same ID differ", l.output[0])

            self.assertIn("i003", l.output[1])
            self.assertIn("Fix crash", l.output[1])

            self.assertIn("i003", l.output[2])
            self.assertIn("Fix crash (cherry-pick)", l.output[2])

    def test_same_subj_diff_change_id_cherry_pick_body(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i005
(cherry picked from commit 789)
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            parse_log(log)
            self.assertEqual(len(l.output), 3)
            self.assertIn("Commits with the same subject differ", l.output[0])

            self.assertIn("i003", l.output[1])
            self.assertIn("Fix crash", l.output[1])

            self.assertIn("i005", l.output[2])
            self.assertIn("Fix crash", l.output[2])

    def test_multiple_change_id(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
Change-Id: i004
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            parse_log(log)
            self.assertEqual(len(l.output), 1)
            self.assertIn("Multiple Change-Id", l.output[0])

    def test_invlid_input(self):
        log = """hello"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

    def test_change_id_starts_body(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe Subj:Update and update Body:Change-Id: i1234567890
Reviewed-on: http://example.com
Reviewed-by: Jo <john.doe@example.com>
Tested-by: Build Verifier <build@example.com>
"""
        with self.assertNoLogs(level=logging.WARNING):
            parse_log(log)

    def test_same_author_diff_email(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix 1 Body:The change
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@gmail.com Name:John Doe  Subj:Fix 2 Body:The change
Change-Id: i002
<end-of-commit-message>
Hash:789 Email:drwho@example.com Name:Dr Who  Subj:Fix 3 Body:The change
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(
            parse_log(log),
            [
                SummaryEntry(1, "Dr Who", "drwho@example.com"),
                SummaryEntry(1, "John Doe", "john.doe@example.com"),
                SummaryEntry(1, "John Doe", "john.doe@gmail.com"),
            ],
        )

    def test_same_author_diff_email_merge_name(self):
        log = """Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix 1 Body:The change
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@gmail.com Name:John Doe  Subj:Fix 2 Body:The change
Change-Id: i002
<end-of-commit-message>
Hash:789 Email:drwho@example.com Name:Dr Who  Subj:Fix 3 Body:The change
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(
            parse_log(log, merge_by_email=False),
            [
                SummaryEntry(1, "Dr Who", "drwho@example.com"),
                SummaryEntry(2, "John Doe", "john.doe@example.com;john.doe@gmail.com"),
            ],
        )


class TestCmdArgs:
    def __init__(self):
        self.since = ""
        self.until = ""
        self.group_pattern = ""
        self.output = "result.xlsx"


class TestConfig(unittest.TestCase):
    def test_from_args_empty(self):
        args = parse_args([])
        config_data = config_create(args)
        self.assertEqual(config_data, {})

    def test_from_args_no_end_date(self):
        args = parse_args(["--since", "Jan 1 2025", "--config_write"])
        config_data = config_create(args)
        self.assertEqual(
            config_data,
            {},
        )

    def test_from_args_valid(self):
        args = parse_args(
            ["--since", "Jan 1 2025", "--until", "Feb 1 2025", "--config_write"]
        )
        config_data = config_create(args)
        self.assertEqual(
            config_data,
            {"delta_days": 31, "last_date": date(year=2025, month=2, day=1)},
        )

    def test_read_empty(self):
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write("{}".encode())
            tmp.close()
            data = config_read(tmp.name)
            self.assertEqual(data, {})
        except Exception as e:
            self.fail(e)
        finally:
            os.unlink(tmp.name)

    def test_read_valid(self):
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(
                '{"last_date": "Mar 04 2025", "delta_days": 31, "group_pattern": ".*gmail.com"}'.encode()
            )
            tmp.close()
            data = config_read(tmp.name)
            self.assertEqual(
                data,
                {
                    "last_date": "Mar 04 2025",
                    "delta_days": 31,
                    "group_pattern": ".*gmail.com",
                },
            )
        except Exception as e:
            self.fail(e)
        finally:
            os.unlink(tmp.name)

    def test_update_args(self):
        config_data = {
            "last_date": "Mar 04 2025",
            "delta_days": 31,
            "group_pattern": ".*gmail.com",
        }
        args = TestCmdArgs()
        config_update_args(config_data, args)
        self.assertEqual(args.since, "Mar 04 2025")
        self.assertEqual(args.until, "Apr 04 2025")
        self.assertEqual(args.group_pattern, ".*gmail.com")

    def test_output_pattern(self):
        config_data = {
            "last_date": "Feb 01 2025",
            "delta_days": 31,
            "output_pattern": "foo.%m.%d.tmp",
        }
        args = TestCmdArgs()
        config_update_args(config_data, args)
        self.assertEqual(args.output, "foo.03.04.tmp")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], module="test_run")
