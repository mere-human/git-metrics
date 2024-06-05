
import unittest
from run import *


class TestParsing(unittest.TestCase):
    def test_single_entry(self):
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

    def test_several_entries(self):
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

    def test_no_change_id(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])
            self.assertEqual(len(l.output), 1)
            self.assertIn('No change id at line', l.output[0])

    def test_same_change_id(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])

    def test_same_subj_diff_change_id(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i001
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i002
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            self.assertEqual(parse_log(log), [SummaryEntry(1, 'John Doe', 'john.doe@example.com')])
            self.assertEqual(len(l.output), 3)
            self.assertIn('Commits with the same subject differ', l.output[0])

            self.assertIn('i001', l.output[1])
            self.assertIn('Fix crash', l.output[1])

            self.assertIn('i002', l.output[2])
            self.assertIn('Fix crash', l.output[2])

    def test_same_change_id_diff_subj(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Test Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

    def test_same_change_id_similar_subj(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
<end-of-commit-message>
Hash:456 Email:john.doe@example.com Name:John Doe  Subj:Fix crash (cherry-pick) Body:The change.
Change-Id: i003
<end-of-commit-message>
"""
        with self.assertLogs(level=logging.WARNING) as l:
            parse_log(log)
            self.assertEqual(len(l.output), 3)
            self.assertIn('Commits with the same ID differ', l.output[0])

            self.assertIn('i003', l.output[1])
            self.assertIn('Fix crash', l.output[1])

            self.assertIn('i003', l.output[2])
            self.assertIn('Fix crash (cherry-pick)', l.output[2])

    def test_same_subj_diff_change_id_cherry_pick_body(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
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
            self.assertIn('Commits with the same subject differ', l.output[0])

            self.assertIn('i003', l.output[1])
            self.assertIn('Fix crash', l.output[1])

            self.assertIn('i005', l.output[2])
            self.assertIn('Fix crash', l.output[2])


    def test_multiple_change_id(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe  Subj:Fix crash Body:The change.
Change-Id: i003
Change-Id: i004
<end-of-commit-message>
"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

    def test_invlid_input(self):
        log ="""hello"""
        with self.assertRaises(RuntimeError):
            parse_log(log)

    def test_change_id_starts_body(self):
        log ="""Hash:123 Email:john.doe@example.com Name:John Doe Subj:Update and update Body:Change-Id: i1234567890
Reviewed-on: http://example.com
Reviewed-by: Jo <john.doe@example.com>
Tested-by: Build Verifier <build@example.com>
"""
        with self.assertNoLogs(level=logging.WARNING):
            parse_log(log)

if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], module='test_run')