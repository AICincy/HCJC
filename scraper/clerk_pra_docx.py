"""OOXML letter writer used by scraper.clerk_pra. Stdlib only."""
from __future__ import annotations

import html
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

CONTENT_TYPES = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>
</Types>
"""

RELS = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>
</Relationships>
"""

DOC_RELS = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>
"""


def _paragraph(text: str) -> str:
    if text == "":
        return "<w:p/>"
    return (
        '<w:p><w:r><w:t xml:space=\"preserve\">'
        + html.escape(text)
        + "</w:t></w:r></w:p>"
    )


def write_letter_docx(path: Path, letter: str) -> None:
    """Write a plain-text letter body to a minimal .docx at path."""
    body = "".join(_paragraph(line) for line in letter.splitlines())
    document = (
        '<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>'
        '<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/document.xml", document)
