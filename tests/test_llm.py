import pytest
from certflow import llm


def test_no_hosted_llm_without_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(llm, "LLM_URL", "")
    with pytest.raises(RuntimeError, match="CERTFLOW_OLLAMA_URL"):
        llm.ask_ollama("some question", [])

def test_unsafe_remote_ollama_url_rejected(monkeypatch):
    monkeypatch.setattr(llm, "LLM_URL", "https://untrusted.example")
    with pytest.raises(RuntimeError, match="loopback"):
        llm.ask_ollama("some question", [])
