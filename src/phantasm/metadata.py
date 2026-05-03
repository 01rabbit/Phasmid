import io
import os
import re
import zipfile

METADATA_WARNING = (
    "This file may contain metadata that could reveal source, device, "
    "location, or author information."
)
SCRUB_LIMITATION = (
    "Metadata removal is best-effort and may not remove every embedded "
    "identifier from every file format."
)
DETECTION_LIMITATION = "Metadata detection is best-effort."


def metadata_risk_report(filename, data):
    name = os.path.basename(filename or "")
    lower_name = name.lower()
    risks: list[str] = []

    if _looks_like_jpeg(data):
        if b"Exif\x00\x00" in data:
            risks.append("embedded image metadata")
        _scan_ascii_tokens(
            data,
            risks,
            {
                b"GPS": "possible location metadata",
                b"Make": "camera maker metadata",
                b"Model": "camera model metadata",
                b"Serial": "device serial-like metadata",
            },
        )

    if lower_name.endswith(".pdf") or data.startswith(b"%PDF"):
        _scan_ascii_tokens(
            data,
            risks,
            {
                b"/Author": "document author metadata",
                b"/Creator": "creator application metadata",
                b"/Producer": "creator application metadata",
                b"/Title": "document title metadata",
                b"/Subject": "document subject metadata",
            },
        )

    if _looks_like_zip(data):
        risks.extend(_office_zip_risks(data))

    if _looks_like_text(data):
        text = data[:65536].decode("utf-8", errors="ignore")
        if re.search(r"(/Users/|/home/|[A-Za-z]:\\Users\\)", text):
            risks.append("local path leakage")
        if re.search(r"(?i)\b(author|creator|modified by|last saved by)\b", text):
            risks.append("author or modification metadata")
        if name:
            risks.append("original filename may reveal context")

    unique_risks = sorted(set(risks))
    return {
        "risk": _risk_level(unique_risks),
        "warning": METADATA_WARNING if unique_risks else "",
        "findings": unique_risks,
        "scrub_supported": _scrub_supported(lower_name, data),
        "limitation": DETECTION_LIMITATION,
    }


def scrub_metadata(filename, data):
    lower_name = os.path.basename(filename or "").lower()
    if _looks_like_text(data) and lower_name.endswith((".txt", ".md", ".csv", ".log")):
        text = data.decode("utf-8", errors="ignore")
        scrubbed = re.sub(
            r"(/Users/|/home/|[A-Za-z]:\\Users\\)[^\s]+", "[local-path]", text
        )
        scrubbed = re.sub(
            r"(?im)^(author|creator|modified by|last saved by)\s*[:=].*$",
            r"\1: [removed]",
            scrubbed,
        )
        return {
            "success": True,
            "filename": "metadata_reduced_payload.bin",
            "data": scrubbed.encode("utf-8"),
            "message": "Best-effort metadata removal completed.",
            "limitation": SCRUB_LIMITATION,
        }

    return {
        "success": False,
        "filename": "",
        "data": b"",
        "message": "Metadata removal is not supported for this file type.",
        "limitation": SCRUB_LIMITATION,
    }


def _looks_like_jpeg(data):
    return data.startswith(b"\xff\xd8")


def _looks_like_zip(data):
    return data.startswith(b"PK\x03\x04")


def _looks_like_text(data):
    if not data:
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _scan_ascii_tokens(data, risks, token_map):
    sample = data[:262144]
    for token, description in token_map.items():
        if token in sample:
            risks.append(description)


def _office_zip_risks(data):
    risks: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            for info_name in ("docProps/core.xml", "docProps/app.xml"):
                if info_name in names:
                    xml = archive.read(info_name)[:262144]
                    _scan_ascii_tokens(
                        xml,
                        risks,
                        {
                            b"creator": "document author metadata",
                            b"lastModifiedBy": "modification history metadata",
                            b"title": "document title metadata",
                            b"subject": "document subject metadata",
                            b"Application": "creator application metadata",
                        },
                    )
            if any(name.startswith("docProps/thumbnail") for name in names):
                risks.append("embedded thumbnail")
    except zipfile.BadZipFile:
        return risks
    return risks


def _scrub_supported(lower_name, data):
    return _looks_like_text(data) and lower_name.endswith(
        (".txt", ".md", ".csv", ".log")
    )


def _risk_level(risks):
    if not risks:
        return "low"
    if len(risks) >= 3:
        return "high"
    return "medium"
