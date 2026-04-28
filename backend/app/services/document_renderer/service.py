"""Document rendering helpers for submission artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(slots=True)
class RenderedArtifact:
    artifact_path: str


class PdfRenderer:
    """Render minimal PDF artifacts without external runtime dependencies."""

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def render_resume(self, *, file_stem: str, title: str, body: str) -> RenderedArtifact:
        safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", file_stem).strip("-") or "resume"
        target = self.output_root / f"{safe_stem}.pdf"
        target.write_bytes(_build_pdf(title=title, body=body))
        return RenderedArtifact(artifact_path=str(target.resolve()))


def _build_pdf(*, title: str, body: str) -> bytes:
    text_lines = [title, "", *body.splitlines()]
    escaped_lines = [_escape_pdf_text(line[:110]) for line in text_lines[:35]]
    content_lines = ["BT", "/F1 12 Tf", "50 760 Td"]
    for index, line in enumerate(escaped_lines):
        if index == 0:
            content_lines.append(f"({line}) Tj")
        else:
            content_lines.append("0 -18 Td")
            content_lines.append(f"({line}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("utf-8")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("utf-8") + stream + b"\nendstream endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(
        (
            f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("utf-8")
    )
    return bytes(pdf)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
