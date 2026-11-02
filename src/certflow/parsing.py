"""Guardrails, PDF page extraction, and regex extraction with per-field provenance."""
import re
import fitz
from .config import MAX_BYTES, MAX_PAGES

FIELDS = {
  "document_type": r"Document Type:\s*([^\n]+)",
  "certificate_number": r"Certificate Number:\s*(DEMO-CERT-\d+)",
  "seller": r"Seller:\s*([^\n]+)",
  "buyer": r"Buyer:\s*([^\n]+)",
  "jurisdiction": r"Jurisdiction:\s*([A-Z]{2})",
  "issue_date": r"Issue Date:\s*(\d{4}-\d{2}-\d{2})",
  "expiry_date": r"Expiry Date:\s*(\d{4}-\d{2}-\d{2})"
}

class InvalidDocument(ValueError): pass

def parse_pdf(raw: bytes) -> list[str]:
    if not raw.startswith(b"%PDF-"):
        raise InvalidDocument("not a PDF signature")
    if len(raw) > MAX_BYTES:
        raise InvalidDocument("PDF exceeds maximum size")
    try:
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if doc.needs_pass: raise InvalidDocument("password-protected PDF not supported")
            if not 1 <= len(doc) <= MAX_PAGES: raise InvalidDocument("page count outside limits")
            pages = [page.get_text(sort=True).strip() for page in doc]
    except (fitz.FileDataError, fitz.EmptyFileError) as err:
        raise InvalidDocument("unreadable PDF") from err
    return pages

def extract_fields(pages: list[str]) -> dict:
    result = {}
    for name, pattern in FIELDS.items():
        result[name] = {"value": None, "page": None, "method": None}
        for index, text in enumerate(pages):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                result[name] = {"value": match.group(1).strip(), "page": index+1,
                                "method": "regex_pdf_text"}
                break
    return result

def optional_ocr_pages(raw: bytes, pages: list[str]) -> list[str]:
    """Opt-in OCR for scanned pages; require pytesseract AND OS tesseract executable."""
    if all(page.strip() for page in pages): return pages
    try:
        import io
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise InvalidDocument("scanned page; install optional ocr extra and Tesseract executable") from exc
    import fitz
    with fitz.open(stream=raw, filetype="pdf") as doc:
        for index, text in enumerate(pages):
            if not text.strip():
                pix = doc[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                try: pages[index] = pytesseract.image_to_string(img).strip()
                except pytesseract.TesseractNotFoundError as exc:
                    raise InvalidDocument("Tesseract executable missing") from exc
    return pages
