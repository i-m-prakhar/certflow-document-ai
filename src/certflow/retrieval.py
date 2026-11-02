"""Real BM25 + deterministic dense hashed-token cosine search, fused using RRF.

The hash vectors are a lexical *baseline*, NOT semantic transformer embeddings.
Optional `sentence_transformers` replaces them with genuinely semantic embeddings.
"""
import math
import re
from collections import Counter
import numpy as np

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", flags=re.I)

def tokens(text: str): return TOKEN_PATTERN.findall(text.lower())

class BM25:
    def __init__(self, passages: list[str], k1: float = 1.5, b: float = .75):
        self.docs = [Counter(tokens(t)) for t in passages]
        self.n = len(self.docs)
        self.avgdl = sum(sum(c.values()) for c in self.docs) / max(self.n, 1)
        self.df = Counter()
        for doc in self.docs: self.df.update(doc.keys())
        self.k1, self.b = k1, b

    def scores(self, query: str) -> np.ndarray:
        result = np.zeros(self.n)
        if not self.n: return result
        for term in set(tokens(query)):
            df = self.df.get(term, 0)
            if not df: continue
            idf = math.log(1 + (self.n - df + .5) / (df + .5))
            for i, doc in enumerate(self.docs):
                freq = doc.get(term, 0)
                if not freq: continue
                length = sum(doc.values())
                result[i] += idf * freq * (self.k1 + 1) / (freq + self.k1*(1-self.b+self.b*length/max(self.avgdl, 1)))
        return result


def hash_vector(text: str, dims: int = 384) -> np.ndarray:
    # Stable crypto hash: Python hash() is process randomized. Dense hashed lexical baseline.
    from hashlib import blake2b
    vector = np.zeros(dims, dtype=np.float32)
    for term in tokens(text):
        data = blake2b(term.encode(), digest_size=8).digest()
        n = int.from_bytes(data, "big")
        vector[n % dims] += 1 if n & 1 else -1
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector

class Searcher:
    def __init__(self, records: list[dict], embedding_mode: str = "hash"):
        self.records = records
        self.bm25 = BM25([r["text"] for r in records])
        if embedding_mode == "hash": self.embed = hash_vector
        elif embedding_mode == "sentence_transformers":
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.embed = lambda text: np.asarray(encoder.encode(text, normalize_embeddings=True))
        else: raise ValueError("unknown embedding mode")
        self.embeddings = np.asarray([self.embed(r["text"]) for r in records]) if records else np.empty((0,384))

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.records: return []
        lexical = self.bm25.scores(query)
        dense = self.embeddings @ self.embed(query)
        rank_bm25 = np.argsort(-lexical, kind="stable")
        rank_dense = np.argsort(-dense, kind="stable")
        fused = np.zeros(len(self.records))
        for rank, idx in enumerate(rank_bm25): fused[idx] += 1/(60+rank+1)
        for rank, idx in enumerate(rank_dense): fused[idx] += 1/(60+rank+1)
        # Boost exact certificate identifiers: structured IDs must outrank
        # generic shared legal boilerplate when present in the query.
        identifiers = re.findall(r"demo-cert-\d+", query.lower())
        if identifiers:
            for i, record in enumerate(self.records):
                if any(identifier in record["text"].lower() for identifier in identifiers):
                    fused[i] += .05
        return [{**self.records[int(i)], "score": round(float(fused[i]), 8),
                 "bm25_score": round(float(lexical[i]), 5),
                 "dense_cosine": round(float(dense[i]), 5)}
                for i in np.argsort(-fused, kind="stable")[:k]]
