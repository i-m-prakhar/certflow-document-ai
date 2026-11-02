from fastapi.testclient import TestClient
from certflow.api import create_app

def test_ingestion_retrieval_citations_audit_isolation(demo, tmp_path):
    pdfs, store, service=demo
    with TestClient(create_app(store.db_path,service.upload_root)) as client:
        with (pdfs/"demo-002.pdf").open("rb") as f:
            response=client.post("/v1/documents",files={"file":("demo-002.pdf",f,"application/pdf")},headers={"X-Workspace-ID":"companyA"})
        assert response.status_code==200, response.text
        obj=response.json(); did=obj["document_id"]
        assert obj["fields"]["buyer"]["value"]
        assert not obj["deduplicated"]
        with (pdfs/"demo-002.pdf").open("rb") as f:
            again=client.post("/v1/documents",files={"file":("../../demo-002.pdf",f,"application/pdf")},headers={"X-Workspace-ID":"companyA"})
        assert again.json()["deduplicated"]
        assert client.get(f"/v1/documents/{did}",headers={"X-Workspace-ID":"companyA"}).status_code==200
        assert client.get(f"/v1/documents/{did}",headers={"X-Workspace-ID":"companyB"}).status_code==404
        search=client.post("/v1/search",json={"query":"DEMO-CERT-1001"},headers={"X-Workspace-ID":"companyA"})
        assert search.status_code==200
        assert search.json()["results"][0]["document_id"]==did
        ask=client.post("/v1/ask",json={"query":"DEMO-CERT-1001"},headers={"X-Workspace-ID":"companyA"})
        assert ask.json()["citations"][0]["document_id"]==did
        assert ask.json()["orchestrator"]=="direct"
        assert client.post("/v1/ask",json={"query":"zxqxvjjf imaginary nonexistent token"},headers={"X-Workspace-ID":"companyA"}).json()["needs_review"]
        assert client.get("/v1/audit",headers={"X-Workspace-ID":"companyA"}).json()["events"]
        assert client.get("/metrics").status_code==200
        assert client.get("/health/ready").status_code==200

def test_invalid_upload_validation(demo):
    pdfs, store, service=demo
    with TestClient(create_app(store.db_path,service.upload_root)) as client:
        response=client.post("/v1/documents",files={"file":("bad.pdf",b"hello","application/pdf")})
        assert response.status_code==422
        response=client.post("/v1/documents",files={"file":("bad.txt",b"hello","text/plain")})
        assert response.status_code==415
        assert client.get("/v1/documents",headers={"X-Workspace-ID":"../"}).status_code==422
