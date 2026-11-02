from certflow.evaluation import run

def test_reproducible_evaluation(tmp_path):
    report=run(tmp_path/"data",tmp_path/"reports")
    assert report["document_count"]==18
    assert report["field_count"]==126
    assert 0<=report["field_exact_match"]<=1
    assert 0<=report["retrieval_mrr_at_10"]<=1
