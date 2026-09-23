"""Router: orchestration layer that decides, per query, whether to consult
the canonical OKF knowledge base or the unstructured RAG index.

Canonical-fact queries (schemas, SLAs, policies, definitions) are routed to
OKFEngine for deterministic, verified answers. Unstructured / historical
queries (incidents, logs, "what happened") are routed to RAGEngine for
semantic similarity search.
"""

from __future__ import annotations

import re

# Keywords that indicate a canonical-fact lookup (OKF).
OKF_KEYWORDS = [
    "schema",
    "sla",
    "policy",
    "policies",
    "definition",
    "canonical",
    "table",
    "column",
    "uptime",
    "service level agreement",
    "spec",
    "specification",
]

# Keywords that indicate an unstructured / historical lookup (RAG).
RAG_KEYWORDS = [
    "incident",
    "history",
    "historical",
    "log",
    "logs",
    "happened",
    "outage",
    "past",
    "postmortem",
    "post-mortem",
    "root cause",
    "timeline",
    "when did",
]


class Router:
    """Evaluates a query string and routes it to the appropriate engine."""

    def __init__(self, okf_engine, rag_engine):
        self.okf_engine = okf_engine
        self.rag_engine = rag_engine

    def classify(self, query_text: str) -> str:
        """Return 'okf' or 'rag' depending on which engine should answer
        the query. Ties/no-matches default to 'rag' since unstructured
        search is the safer fallback for open-ended questions."""
        query_lower = query_text.lower()

        okf_score = sum(1 for kw in OKF_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", query_lower))
        rag_score = sum(1 for kw in RAG_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", query_lower))

        if okf_score > rag_score:
            return "okf"
        if rag_score > okf_score:
            return "rag"
        return "rag"

    def route(self, query_text: str) -> dict:
        """Classify and answer the query, returning both the chosen route
        and the synthesized retrieved context."""
        route = self.classify(query_text)

        if route == "okf":
            context = self.okf_engine.query(query_text)
        else:
            context = self.rag_engine.query(query_text)

        return {
            "query": query_text,
            "route": route,
            "context": context,
        }
