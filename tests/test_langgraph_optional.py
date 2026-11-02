"""Executed in CI environments that explicitly install the agents extra."""
import pytest
from certflow.workflow import ask


def test_langgraph_executes_workflow_if_installed(demo):
    pytest.importorskip("langgraph")
    pdfs, _, service = demo
    service.ingest((pdfs / "demo-002.pdf").read_bytes(), "demo-002.pdf")
    result = ask(service, "demo", "DEMO-CERT-1001", use_langgraph=True)
    assert result["orchestrator"] == "langgraph"
    assert result["citations"]
