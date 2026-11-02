"""Local-first, API-key gated document ingestion + retrieval + audit service."""
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Response, UploadFile
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from .config import API_KEY, DB, MAX_BYTES, STORAGE
from .parsing import InvalidDocument
from .service import DocumentService
from .storage import Store
from .workflow import ask

REQUESTS = Counter("certflow_requests_total", "Document requests", ["action"])
LATENCY = Histogram("certflow_operation_seconds", "Document operation latency", ["action"])
logger = logging.getLogger(__name__)

class Question(BaseModel):
    query: str = Field(min_length=4, max_length=500)
    k: int = Field(default=3, ge=1, le=10)
    use_langgraph: bool = False
    use_ollama: bool = False


def key_guard(x_api_key: str | None = Header(None)):
    if API_KEY and (x_api_key is None or not hmac.compare_digest(x_api_key, API_KEY)):
        raise HTTPException(401, "API key required")

def workspace_guard(x_workspace_id: str = Header("demo")):
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", x_workspace_id):
        raise HTTPException(422, "invalid workspace ID")
    return x_workspace_id


def create_app(db_path=None, upload_root=None, embedding_mode="hash"):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = Store(Path(db_path or DB))
        app.state.service = DocumentService(app.state.store, Path(upload_root or STORAGE), embedding_mode)
        yield
    app = FastAPI(title="CertFlow AI", version="1.0.0", lifespan=lifespan,
                  description="Synthetic compliance-style document parsing and grounded retrieval; no legal validation")

    @app.get("/health/live")
    def live(): return {"status": "alive"}

    @app.get("/health/ready")
    def ready(): return {"status": "ready", "retrieval_backend": app.state.service.embedding_mode}

    @app.get("/metrics")
    def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/v1/documents", dependencies=[Depends(key_guard)])
    async def upload(file: UploadFile = File(...),
                     ocr: bool = False, workspace: str = Depends(workspace_guard)):
        if file.content_type not in {"application/pdf", "application/octet-stream"}:
            raise HTTPException(415, "PDF only")
        raw = await file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES: raise HTTPException(413, "PDF too large")
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(415, "PDF filename required")
        try:
            with LATENCY.labels(action="ingest").time():
                result = app.state.service.ingest(raw, file.filename, workspace, ocr)
        except InvalidDocument as exc:
            raise HTTPException(422, str(exc)) from exc
        REQUESTS.labels(action="ingest").inc()
        logger.info("ingest workspace=%s document=%s", workspace, result["document_id"])
        return result

    @app.get("/v1/documents", dependencies=[Depends(key_guard)])
    def list_documents(workspace: str = Depends(workspace_guard)):
        return {"document_ids": app.state.store.documents(workspace)}

    @app.get("/v1/documents/{doc_id}", dependencies=[Depends(key_guard)])
    def get_document(doc_id: str, workspace: str = Depends(workspace_guard)):
        obj = app.state.store.get(workspace, doc_id)
        if not obj: raise HTTPException(404, "document not found")
        app.state.store.audit(workspace, doc_id, "READ")
        return obj

    @app.post("/v1/search", dependencies=[Depends(key_guard)])
    def search(req: Question, workspace: str = Depends(workspace_guard)):
        with LATENCY.labels(action="search").time():
            results = app.state.service.search(workspace, req.query, req.k)
        REQUESTS.labels(action="search").inc()
        return {"results": results, "retrieval": f"BM25+{app.state.service.embedding_mode}+RRF"}

    @app.post("/v1/ask", dependencies=[Depends(key_guard)])
    def answer(req: Question, workspace: str = Depends(workspace_guard)):
        try:
            with LATENCY.labels(action="ask").time():
                result = ask(app.state.service, workspace, req.query, req.k, req.use_langgraph)
                if req.use_ollama:
                    from .llm import ask_ollama
                    hits = app.state.service.search(workspace, req.query, req.k)
                    result.update(ask_ollama(req.query, hits))
                    result["mode"] = "experimental_local_ollama_unverified"
        except RuntimeError as exc:
            raise HTTPException(422, str(exc)) from exc
        REQUESTS.labels(action="ask").inc()
        return result

    @app.get("/v1/audit", dependencies=[Depends(key_guard)])
    def audit(workspace: str = Depends(workspace_guard), document_id: str | None = None,
              limit: int = Query(default=50, ge=1, le=200)):
        return {"events": app.state.store.events(workspace, document_id, limit)}
    return app

app = create_app()
