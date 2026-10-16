from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from download_nlm_additional_head_case import DownloadError, commit_download, parse_index


class DownloadNLMAdditionalHeadTests(unittest.TestCase):
    def test_parse_index_filters_and_sorts_expected_files(self) -> None:
        html = """
        <a href='J.002.gz'>J.002.gz</a><td class='size'>20</td>
        <a href='ignore.txt'>ignore.txt</a><td class='size'>2</td>
        <a href='J.001.gz'>J.001.gz</a><td class='size'>10</td>
        """
        self.assertEqual(parse_index(html, r"J\.\d+\.gz"), [("J.001.gz", 10), ("J.002.gz", 20)])

    def test_parse_index_rejects_empty_match(self) -> None:
        with self.assertRaisesRegex(DownloadError, "no matching files"):
            parse_index("<html></html>", r"I\.\d+\.gz")

    def test_concurrent_completed_target_discards_temporary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "I.001.gz"
            temporary = root / "I.001.gz.part.unique"
            target.write_bytes(b"complete")
            temporary.write_bytes(b"complete")
            commit_download(temporary, target, len(b"complete"))
            self.assertEqual(target.read_bytes(), b"complete")
            self.assertFalse(temporary.exists())


if __name__ == "__main__":
    unittest.main()
