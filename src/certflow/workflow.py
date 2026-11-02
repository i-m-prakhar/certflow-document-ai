"""Bounded evidence-grounded Q&A pipeline; opt-in LangGraph execution.

No generative model is required: the default answer consists only of retrieved
passages. This is extractive answering, not a hallucination-proof LLM.
"""
from typing import TypedDict
from .service import DocumentService

class WorkflowState(TypedDict, total=False):
    workspace: str
    question: str
    hits: list[dict]
    answer: str
    citations: list[dict]
    needs_review: bool
    audit_id: str

def evidence_answer(hits: list[dict], question: str):
    if not hits or max(hit["bm25_score"] for hit in hits) <= 0:
        return {"answer": "No matching evidence found in this workspace.",
                "citations": [], "needs_review": True}
    # At most two short source quotations; cites exact stored page IDs.
    selected = [hit for hit in hits if hit["bm25_score"] > 0][:2]
    cited = [{"document_id": h["document_id"], "page": h["page"],
              "score": h["score"]} for h in selected]
    answer = "Relevant source excerpts (not a legal determination): " + " ".join(
        f"[document {h['document_id']}, p.{h['page']}] {h['text'][:240].replace(chr(10), ' ')}"
        for h in selected)
    return {"answer": answer, "citations": cited, "needs_review": False}

def ask(service: DocumentService, workspace: str, question: str, k: int = 3,
        use_langgraph: bool = False):
    def retrieve(state: WorkflowState):
        return {"hits": service.search(state["workspace"], state["question"], k)}
    def ground(state: WorkflowState):
        return evidence_answer(state["hits"], state["question"])
    def audit(state: WorkflowState):
        service.store.audit(state["workspace"], None, "ASK")
        return {"audit_id": "recorded"}

    initial: WorkflowState = {"workspace": workspace, "question": question}
    if use_langgraph:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError("uv sync --extra agents to enable LangGraph") from exc
        graph = StateGraph(WorkflowState)
        graph.add_node("retrieve", retrieve); graph.add_node("ground", ground)
        graph.add_node("audit", audit)
        graph.add_edge(START, "retrieve"); graph.add_edge("retrieve", "ground")
        graph.add_edge("ground", "audit"); graph.add_edge("audit", END)
        output = graph.compile().invoke(initial)
    else:
        output = {**initial, **retrieve(initial)}
        output.update(ground(output)); output.update(audit(output))
    return {"answer": output["answer"], "citations": output["citations"],
            "needs_review": output["needs_review"], "orchestrator": "langgraph" if use_langgraph else "direct"}
