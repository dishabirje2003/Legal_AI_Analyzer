from __future__ import annotations

import io
from dataclasses import dataclass

import fitz

@dataclass(frozen=True)
class ExtractedText:
    text: str
    method: str
    page_count: int = None

class OCRService:
    def extract_text_from_pdf(self, pdf_bytes):
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            n_pages = doc.page_count
            text_parts = []
            for page in doc:
                page_text = page.get_text("text").strip()
                if page_text:
                    text_parts.append(page_text)
            return ExtractedText(text="\n\n".join(text_parts).strip(), method="pymupdf", page_count=n_pages)
        finally:
            doc.close()

    def extract_text(self, filename, content):
        lower = filename.lower()
        if lower.endswith(".pdf"):
            return self.extract_text_from_pdf(content)
        if lower.endswith((".docx", ".doc")):
            try:
                import docx
            except Exception as e:
                raise RuntimeError("python-docx is required for DOCX parsing") from e
            if lower.endswith(".doc"):
                raise ValueError("Legacy .doc files are not supported yet. Please upload .docx or PDF.")
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs).strip()
            return ExtractedText(text=text, method="docx", page_count=None)
        raise ValueError("Unsupported file type for text extraction")

ocr_service = OCRService()
