"""Local in-process sequential retrieval benchmark, never a production SLO."""
import json
import statistics
import time
from fastapi.testclient import TestClient
from certflow.api import create_app
from certflow.config import ROOT

with TestClient(create_app()) as client:
    ids=client.get("/v1/documents").json()["document_ids"]
    if not ids:
        raise SystemExit("First run: uv run certflow ingest-demo")
    for _ in range(10): client.post("/v1/search",json={"query":"DEMO-CERT-1001"})
    times=[]
    for _ in range(100):
        start=time.perf_counter()
        resp=client.post("/v1/search",json={"query":"DEMO-CERT-1001"})
        resp.raise_for_status(); times.append((time.perf_counter()-start)*1000)
result={"mode":"single-process sequential in-process TestClient, full search index rebuilt per request",
        "docs":len(ids), "queries":100, "p50_ms":round(statistics.median(times),3),
        "p95_ms":round(sorted(times)[94],3),
        "limitations":"Local synthetic corpus only; no network, concurrency, OCR or semantic model in benchmark."}
(ROOT/"reports"/"api_benchmark.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
