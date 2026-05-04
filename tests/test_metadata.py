import io
import os
import struct
import sys
import unittest
import zipfile
import zlib

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.metadata import metadata_risk_report, scrub_metadata


def _make_jpeg_with_exif():
    """Minimal JPEG containing an APP1 (EXIF) segment with GPS data."""
    exif_payload = b"Exif\x00\x00II\x2a\x00GPS location info"
    app1_len = struct.pack(">H", 2 + len(exif_payload))
    app1 = b"\xff\xe1" + app1_len + exif_payload
    sos_payload = b"\x00\x08\x01\x01\x00\x00\x3f\x00"
    sos_len = struct.pack(">H", 2 + len(sos_payload))
    sos = b"\xff\xda" + sos_len + sos_payload + b"\xfe\xdc\xba"
    return b"\xff\xd8" + app1 + sos + b"\xff\xd9"


def _make_png_with_text():
    """Minimal 1x1 RGB PNG with a tEXt metadata chunk."""

    def chunk(ctype, data=b""):
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        return length + ctype + data + crc

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    text = chunk(b"tEXt", b"Author\x00Alice")
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = chunk(b"IEND")
    return b"\x89PNG\r\n\x1a\n" + ihdr + text + idat + iend


def _make_docx_with_author():
    """Minimal DOCX-like ZIP with docProps/core.xml containing author fields."""
    core_xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b"<cp:coreProperties"
        b' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        b' xmlns:dc="http://purl.org/dc/elements/1.1/">'
        b"<dc:creator>Alice Smith</dc:creator>"
        b"<cp:lastModifiedBy>Bob Jones</cp:lastModifiedBy>"
        b"<dc:title>Secret Document</dc:title>"
        b"</cp:coreProperties>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types/>')
    return buf.getvalue()


class MetadataRiskReportTests(unittest.TestCase):
    def test_text_path_and_author_metadata_are_reported(self):
        data = b"author: Alice\nsource path: /Users/alice/interview.txt\n"
        report = metadata_risk_report("interview.txt", data)
        self.assertEqual(report["risk"], "high")
        self.assertIn("local path leakage", report["findings"])
        self.assertIn("author or modification metadata", report["findings"])
        self.assertTrue(report["scrub_supported"])
        self.assertIn("best-effort", report["limitation"])

    def test_jpeg_exif_risk_is_reported(self):
        data = _make_jpeg_with_exif()
        report = metadata_risk_report("photo.jpg", data)
        self.assertIn("embedded image metadata", report["findings"])
        self.assertIn("possible location metadata", report["findings"])
        self.assertTrue(report["scrub_supported"])

    def test_png_text_chunk_risk_is_reported(self):
        data = _make_png_with_text()
        report = metadata_risk_report("image.png", data)
        self.assertIn("embedded text metadata", report["findings"])
        self.assertTrue(report["scrub_supported"])

    def test_office_zip_author_risk_is_reported(self):
        data = _make_docx_with_author()
        report = metadata_risk_report("report.docx", data)
        self.assertIn("document author metadata", report["findings"])
        self.assertTrue(report["scrub_supported"])

    def test_pdf_author_risk_reported_but_scrub_not_supported(self):
        data = b"%PDF-1.4 /Author Alice /Title Classified"
        report = metadata_risk_report("document.pdf", data)
        self.assertIn("document author metadata", report["findings"])
        self.assertFalse(report["scrub_supported"])

    def test_clean_file_without_identifying_content_has_low_risk(self):
        # No filename so "original filename may reveal context" is not added
        data = b"Hello, world.\n"
        report = metadata_risk_report("", data)
        self.assertEqual(report["risk"], "low")
        self.assertEqual(report["findings"], [])


class MetadataScrubTests(unittest.TestCase):
    def test_text_scrub_removes_paths_and_authors(self):
        data = b"author: Alice\npath=/home/alice/source.txt\nbody\n"
        result = scrub_metadata("revealing-name.txt", data)
        self.assertTrue(result["success"])
        self.assertEqual(result["filename"], "metadata_reduced_payload.bin")
        self.assertNotEqual(result["data"], data)
        self.assertIn("best-effort", result["limitation"].lower())

    def test_jpeg_exif_segment_is_stripped(self):
        data = _make_jpeg_with_exif()
        self.assertIn(b"Exif\x00\x00", data)
        result = scrub_metadata("photo.jpg", data)
        self.assertTrue(result["success"])
        self.assertNotIn(b"Exif\x00\x00", result["data"])
        self.assertNotIn(b"GPS location", result["data"])
        self.assertTrue(result["data"].startswith(b"\xff\xd8"))
        self.assertEqual(result["filename"], "metadata_reduced_payload.bin")
        self.assertIn("best-effort", result["limitation"].lower())

    def test_jpeg_soi_and_image_data_preserved(self):
        data = _make_jpeg_with_exif()
        result = scrub_metadata("photo.jpg", data)
        self.assertTrue(result["success"])
        self.assertIn(b"\xff\xda", result["data"])  # SOS
        self.assertIn(b"\xff\xd9", result["data"])  # EOI

    def test_malformed_jpeg_scrub_not_supported(self):
        data = b"\xff\xd8Exif\x00\x00GPS"
        result = scrub_metadata("photo.jpg", data)
        self.assertFalse(result["success"])
        self.assertEqual(result["data"], b"")
        self.assertIn("not supported", result["message"])

    def test_png_text_chunk_is_stripped(self):
        data = _make_png_with_text()
        result = scrub_metadata("image.png", data)
        self.assertTrue(result["success"])
        self.assertNotIn(b"tEXt", result["data"])
        self.assertNotIn(b"Author", result["data"])
        self.assertTrue(result["data"].startswith(b"\x89PNG"))
        self.assertEqual(result["filename"], "metadata_reduced_payload.bin")

    def test_png_image_chunks_preserved(self):
        data = _make_png_with_text()
        result = scrub_metadata("image.png", data)
        self.assertTrue(result["success"])
        self.assertIn(b"IHDR", result["data"])
        self.assertIn(b"IDAT", result["data"])
        self.assertIn(b"IEND", result["data"])

    def test_office_zip_author_fields_blanked(self):
        data = _make_docx_with_author()
        result = scrub_metadata("report.docx", data)
        self.assertTrue(result["success"])
        self.assertEqual(result["filename"], "metadata_reduced_payload.bin")
        with zipfile.ZipFile(io.BytesIO(result["data"])) as zf:
            core = zf.read("docProps/core.xml")
        self.assertNotIn(b"Alice Smith", core)
        self.assertNotIn(b"Bob Jones", core)
        self.assertNotIn(b"Secret Document", core)

    def test_office_zip_structure_preserved(self):
        data = _make_docx_with_author()
        result = scrub_metadata("report.docx", data)
        self.assertTrue(result["success"])
        with zipfile.ZipFile(io.BytesIO(result["data"])) as zf:
            names = zf.namelist()
        self.assertIn("docProps/core.xml", names)
        self.assertIn("[Content_Types].xml", names)

    def test_pdf_scrub_not_supported(self):
        data = b"%PDF-1.4 /Author Alice /Title Classified"
        result = scrub_metadata("document.pdf", data)
        self.assertFalse(result["success"])
        self.assertEqual(result["data"], b"")
        self.assertIn("not supported", result["message"])

    def test_unknown_binary_scrub_not_supported(self):
        result = scrub_metadata("binary.bin", bytes(range(256)))
        self.assertFalse(result["success"])
        self.assertEqual(result["data"], b"")

    def test_scrub_result_always_has_limitation_field(self):
        cases = [
            ("photo.jpg", _make_jpeg_with_exif()),
            ("image.png", _make_png_with_text()),
            ("report.docx", _make_docx_with_author()),
            ("notes.txt", b"author: Alice\n"),
            ("doc.pdf", b"%PDF-1.4 /Author Alice"),
        ]
        for filename, data in cases:
            with self.subTest(filename=filename):
                result = scrub_metadata(filename, data)
                self.assertIn("limitation", result)


if __name__ == "__main__":
    unittest.main()
