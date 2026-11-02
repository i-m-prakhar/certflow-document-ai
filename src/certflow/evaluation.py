"""Execute reproducible tests against gold-annotated synthetic PDF corpus."""
import json
import platform
import time
from datetime import date
from pathlib import Path
from .parsing import extract_fields, parse_pdf
from .retrieval import Searcher
from .rules import validate
from .synthetic import generate
from .workflow import evidence_answer


def run(data_root: Path, report_dir: Path) -> dict:
    pdfs = data_root / "pdfs"
    if not (data_root / "annotations" / "gold.json").exists(): generate(pdfs)
    gold = json.loads((data_root / "annotations" / "gold.json").read_text())
    questions = json.loads((data_root / "annotations" / "retrieval_questions.json").read_text())
    records=[]; prediction=[]; errors=[]; durations=[]
    found = correct = review_correct = 0
    for entry in gold:
        start=time.perf_counter()
        pages = parse_pdf((pdfs / entry["file"]).read_bytes())
        fields = extract_fields(pages)
        durations.append((time.perf_counter()-start)*1000)
        for name, expected in entry["fields"].items():
            if name == "document_id": continue
            found += 1
            actual = fields[name]["value"]
            if actual == expected: correct += 1
            else: errors.append({"file":entry["file"],"field":name,
                                 "expected":expected,"actual":actual})
        validity = validate(fields, as_of=date(2026,11,2))
        if (validity["status"] == "NEEDS_REVIEW") == entry["expected_review"]:
            review_correct += 1
        doc_id=entry["file"].removesuffix(".pdf")
        for page_no, content in enumerate(pages,1):
            if content: records.append({"document_id":doc_id,"page":page_no,"text":content})
    searcher = Searcher(records)
    hit1 = hit3 = 0; mrr = 0.0; query_ms=[]
    for item in questions:
        start=time.perf_counter()
        result=searcher.search(item["query"], k=10)
        query_ms.append((time.perf_counter()-start)*1000)
        unique=[]
        for hit in result:
            if hit["document_id"] not in unique: unique.append(hit["document_id"])
        expected=item["expected_document_id"]
        hit1 += expected in unique[:1]; hit3 += expected in unique[:3]
        mrr += 1/(unique.index(expected)+1) if expected in unique else 0
    negative_question = "zxqxvjjf imaginary nonexistent token"
    negative_hits = searcher.search(negative_question, k=3)
    abstains_on_negative = evidence_answer(negative_hits, negative_question)["needs_review"]
    result={"dataset":"18 synthetic exemption-style PDFs, generated, not legally valid",
            "document_count":len(gold), "pages":len(records), "field_count":found,
            "field_exact_match":round(correct/found,5),
            "field_errors":errors, "review_flag_accuracy":round(review_correct/len(gold),5),
            "retrieval_questions":len(questions), "retrieval_recall_at_1":round(hit1/len(questions),5),
            "retrieval_recall_at_3":round(hit3/len(questions),5),
            "retrieval_mrr_at_10":round(mrr/len(questions),5),
            "no_evidence_abstention_on_one_synthetic_negative":abstains_on_negative,
            "mean_pdf_parse_extract_ms":round(sum(durations)/len(durations),4),
            "mean_retrieval_ms":round(sum(query_ms)/len(query_ms),4),
            "retrieval_backend":"actual BM25 + dense hashed lexical vectors + RRF (NOT neural semantic embeddings)",
            "as_of":"2026-11-02", "python_version":platform.python_version(),
            "limitations":"Synthetic native PDFs, deterministic templates; no OCR quality, open-world compliance, or legal validity claims."}
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "evaluation.json").write_text(json.dumps(result,indent=2)+"\n")
    return result
