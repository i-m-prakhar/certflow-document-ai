from fastapi.testclient import TestClient
import certflow.api as api

def test_api_key_gate(monkeypatch, demo):
    pdfs,store,service=demo
    monkeypatch.setattr(api,"API_KEY","secret")
    with TestClient(api.create_app(store.db_path,service.upload_root)) as client:
        assert client.get("/v1/documents").status_code==401
        assert client.get("/v1/documents",headers={"X-API-Key":"wrong"}).status_code==401
        assert client.get("/v1/documents",headers={"X-API-Key":"secret"}).status_code==200
