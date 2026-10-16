import io
import struct
import unittest
import zipfile

import inspect_itrusst_archive as inspector


class ItrusstRemoteArchiveInspectorTests(unittest.TestCase):
    def test_parse_standard_central_directory(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("PH1-BM1-SC1_REFERENCE.mat", b"reference")
            archive.writestr("SKULL-MAPS/brain_mask.mat", b"mask")
        payload = buffer.getvalue()
        eocd_index = payload.rfind(inspector.EOCD_SIGNATURE)
        eocd = struct.unpack_from("<4s4H2LH", payload, eocd_index)
        entry_count = int(eocd[4])
        directory_size = int(eocd[5])
        directory_offset = int(eocd[6])
        entries = inspector.parse_central_directory(
            payload[directory_offset : directory_offset + directory_size],
            entry_count,
        )
        self.assertEqual([entry["name"] for entry in entries], [
            "PH1-BM1-SC1_REFERENCE.mat",
            "SKULL-MAPS/brain_mask.mat",
        ])
        self.assertEqual(entries[0]["uncompressed_size"], len(b"reference"))
        self.assertEqual(entries[0]["compression_method"], zipfile.ZIP_DEFLATED)
        self.assertEqual(entries[0]["flags"] & 0x1, 0)

    def test_rejects_truncated_directory(self):
        with self.assertRaisesRegex(RuntimeError, "Truncated"):
            inspector.parse_central_directory(b"PK\x01\x02")


if __name__ == "__main__":
    unittest.main()
