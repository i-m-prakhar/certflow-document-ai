"""Zero-credential local reproducible commands."""
import argparse
import json
from .config import DB, ROOT, STORAGE
from .evaluation import run
from .service import DocumentService
from .storage import Store
from .synthetic import generate
from .workflow import ask


def main():
    p=argparse.ArgumentParser(description="CertFlow AI")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("generate-data"); sub.add_parser("evaluate")
    sub.add_parser("ingest-demo")
    q=sub.add_parser("ask"); q.add_argument("question")
    args=p.parse_args()
    root=ROOT/"data"/"synthetic"
    if args.command=="generate-data": print(json.dumps(generate(root/"pdfs"),indent=2))
    elif args.command=="evaluate": print(json.dumps(run(root,ROOT/"reports"),indent=2))
    elif args.command=="ingest-demo":
        if not list((root/"pdfs").glob("*.pdf")): generate(root/"pdfs")
        service=DocumentService(Store(DB), STORAGE)
        for item in sorted((root/"pdfs").glob("*.pdf")):
            result=service.ingest(item.read_bytes(),item.name,"demo")
            print(item.name,result["document_id"],result["validation"]["status"])
    elif args.command=="ask":
        result=ask(DocumentService(Store(DB),STORAGE),"demo",args.question)
        print(json.dumps(result,indent=2))
if __name__=="__main__": main()
