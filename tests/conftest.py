import pytest
from certflow.synthetic import generate
from certflow.storage import Store
from certflow.service import DocumentService

@pytest.fixture
def demo(tmp_path):
    pdfs=tmp_path/"data"/"pdfs"
    generate(pdfs, n=6)
    store=Store(tmp_path/"runtime"/"db.sqlite3")
    service=DocumentService(store,tmp_path/"runtime"/"pdfs", "hash")
    return pdfs, store, service
