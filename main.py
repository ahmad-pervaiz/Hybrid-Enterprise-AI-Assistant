"""CLI entry point for the Hybrid Enterprise AI Assistant.

Combines the Open Knowledge Format (OKF) engine for canonical facts with a
Retrieval-Augmented Generation (RAG) engine for unstructured historical
text, routing each user query to the appropriate engine and printing the
synthesized retrieved context.

Usage:
    python main.py                 # interactive REPL
    python main.py "your query"    # single query, non-interactive
"""

from __future__ import annotations

import sys

from okf_engine import OKFEngine
from rag_engine import RAGEngine
from router import Router

OKF_ROOT = "okf_knowledge"
DOCS_ROOT = "docs"


def build_router() -> Router:
    print("Initializing OKF engine...")
    okf_engine = OKFEngine(OKF_ROOT)

    print("Initializing RAG engine (loading docs, building FAISS index)...")
    rag_engine = RAGEngine(DOCS_ROOT)

    return Router(okf_engine, rag_engine)


def run_query(router: Router, query_text: str) -> None:
    result = router.route(query_text)
    print(f"\nQuery: {result['query']}")
    print(f"Routed to: {result['route'].upper()}")
    for step in result["trace"]:
        print(f"  [{step['stage']}] {step['detail']} ({step['ms']} ms)")
    print("-" * 60)
    print(result["context"])
    print("-" * 60)


def main() -> None:
    router = build_router()

    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        run_query(router, query_text)
        return

    print("\nHybrid Enterprise AI Assistant (OKF + RAG)")
    print("Type a query, or 'exit' to quit.\n")
    while True:
        try:
            query_text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query_text:
            continue
        if query_text.lower() in {"exit", "quit"}:
            break

        run_query(router, query_text)


if __name__ == "__main__":
    main()
