from certflow.retrieval import BM25, Searcher, hash_vector

def test_bm25_uses_term_frequency_and_exact_terms():
    bm25=BM25(["blue wireless laptop", "apple green banana", "blue laptop laptop"])
    scores=bm25.scores("laptop")
    assert scores[1]==0
    assert scores[2]>scores[0]

def test_hybrid_search_and_empty():
    rows=[{"document_id":"one","page":1,"text":"DEMO-CERT-9999 Seller: Robin"},
          {"document_id":"two","page":1,"text":"DEMO-CERT-8888 Seller: Hart"}]
    assert Searcher(rows).search("DEMO-CERT-9999")[0]["document_id"]=="one"
    assert Searcher([]).search("anything")==[]
    assert len(hash_vector("repeatable"))==384
