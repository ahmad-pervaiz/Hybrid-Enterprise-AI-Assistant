"""Router: orchestration layer that decides, per query, whether to consult
the canonical OKF knowledge base, the unstructured RAG index, or both.

- OKF-only queries (schemas, SLAs, policies) get deterministic, verified answers.
- RAG-only queries (incidents, logs, "what happened") get semantic search.
- Hybrid queries touch both sides (e.g. "Did INC-1078 breach the SLA?").

Whenever RAG returns incidents, the router cross-links each one to the
canonical SLA row for its severity in the OKF knowledge base, so historical
evidence is always presented next to the policy it should be judged against.
"""

from __future__ import annotations

import os
import re
import time

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
    "breach",
    "breached",
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

INCIDENT_ID_RE = re.compile(r"\bINC-\d+\b", re.IGNORECASE)
INCIDENT_SEVERITY_RE = re.compile(r"(INC-\d+)\s*-\s*Severity\s*(P[1-4])")


def _count_sources(context: str) -> int:
    return context.count("### Source:")


class Router:
    """Evaluates a query string and routes it to the appropriate engine(s)."""

    def __init__(self, okf_engine, rag_engine=None):
        self.okf_engine = okf_engine
        self.rag_engine = rag_engine

    def scores(self, query_text: str) -> dict:
        query_lower = query_text.lower()
        okf = sum(1 for kw in OKF_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", query_lower))
        rag = sum(1 for kw in RAG_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", query_lower))
        if INCIDENT_ID_RE.search(query_text):
            rag += 1
        return {"okf": okf, "rag": rag}

    def classify(self, query_text: str) -> str:
        """Return 'okf', 'rag' or 'hybrid'. No keyword hits defaults to 'rag'
        since unstructured search is the safer fallback for open questions."""
        s = self.scores(query_text)
        if s["okf"] and s["rag"]:
            return "hybrid"
        if s["okf"]:
            return "okf"
        return "rag"

    def _severity_row(self, severity: str) -> tuple[str, str] | None:
        """Find the canonical OKF table row for a severity like 'P1'."""
        index_path = os.path.join(self.okf_engine.root_dir, "index.md")
        marker = f"({severity})"
        for node in self.okf_engine.traverse(index_path):
            for line in node.content.splitlines():
                if line.startswith("|") and marker in line:
                    return os.path.relpath(node.path, self.okf_engine.root_dir), line.strip()
        return None

    def _cross_links(self, rag_context: str) -> list[dict]:
        links = []
        seen = set()
        for incident, severity in INCIDENT_SEVERITY_RE.findall(rag_context):
            if (incident, severity) in seen:
                continue
            seen.add((incident, severity))
            row = self._severity_row(severity)
            if row:
                links.append(
                    {
                        "incident": incident,
                        "severity": severity,
                        "okf_path": row[0],
                        "okf_row": row[1],
                    }
                )
        return links

    def route(self, query_text: str) -> dict:
        """Classify and answer the query, returning the route, per-engine
        context, cross-links, a stage trace, and one combined context."""
        trace = []

        def stage(name: str, started: float, detail: str, status: str = "ok") -> None:
            trace.append(
                {
                    "stage": name,
                    "detail": detail,
                    "status": status,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )

        t = time.perf_counter()
        scores = self.scores(query_text)
        route = self.classify(query_text)
        stage("router", t, f"okf score {scores['okf']}, rag score {scores['rag']} -> {route}")

        okf_context = rag_context = None

        if route in ("okf", "hybrid"):
            t = time.perf_counter()
            okf_context = self.okf_engine.query(query_text)
            stage("okf", t, f"{_count_sources(okf_context)} canonical document(s)")

        if route in ("rag", "hybrid"):
            t = time.perf_counter()
            if self.rag_engine is None:
                rag_context = "RAG engine is not available yet."
                stage("rag", t, "engine not ready", status="unavailable")
            else:
                rag_context = self.rag_engine.query(query_text)
                stage("rag", t, f"{_count_sources(rag_context)} retrieved chunk(s)")

        links = []
        if rag_context and self.rag_engine is not None:
            t = time.perf_counter()
            links = self._cross_links(rag_context)
            stage("link", t, f"{len(links)} incident(s) linked to OKF SLA rows")

        sections = []
        if okf_context:
            sections.append(f"## Canonical facts (OKF)\n\n{okf_context}")
        if rag_context:
            sections.append(f"## Historical evidence (RAG)\n\n{rag_context}")
        if links:
            lines = [
                f"- {l['incident']} ({l['severity']}) -> {l['okf_path']}: {l['okf_row']}"
                for l in links
            ]
            sections.append("## Cross-links (RAG -> OKF)\n\n" + "\n".join(lines))

        return {
            "query": query_text,
            "route": route,
            "scores": scores,
            "okf_context": okf_context,
            "rag_context": rag_context,
            "links": links,
            "trace": trace,
            "context": "\n\n".join(sections),
        }
