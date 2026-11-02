"""Document ingestion, extraction and workspace-scoped retrieval service."""
import hashlib
from pathlib import Path
from .config import EMBEDDINGS, STORAGE
from .parsing import extract_fields, optional_ocr_pages, parse_pdf
from .retrieval import Searcher
from .rules import validate
from .storage import Store

class DocumentService:
    def __init__(self, store: Store, upload_root: Path | None = None, mode: str | None = None):
        self.store = store
        self.upload_root = upload_root or STORAGE
        self.embedding_mode = mode or EMBEDDINGS

    def ingest(self, raw: bytes, filename: str, workspace: str = "demo", ocr: bool = False):
        pages = parse_pdf(raw)
        if ocr: pages = optional_ocr_pages(raw, pages)
        fields = extract_fields(pages)
        result = validate(fields)
        sha = hashlib.sha256(raw).hexdigest()
        # content-addressing and workspace isolation prevents directory traversal
        doc_id = sha[:24]
        saved_name = self.upload_root / workspace / f"{doc_id}.pdf"
        saved_name.parent.mkdir(parents=True, exist_ok=True)
        created = self.store.put(workspace, doc_id, Path(filename).name[:128], sha, fields, result, pages)
        if created:
            # File is never user-addressable via filename; parsed before storage.
            saved_name.write_bytes(raw)
        return {"document_id": doc_id, "workspace": workspace, "deduplicated": not created,
                "fields": fields, "validation": result, "pages": len(pages)}

    def search(self, workspace: str, query: str, k: int = 5):
        hits = Searcher(self.store.passages(workspace), self.embedding_mode).search(query, k)
        self.store.audit(workspace, None, "SEARCH")
        return hits
