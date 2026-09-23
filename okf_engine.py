"""OKF Engine: deterministic parsing and traversal of the Open Knowledge
Format (OKF) knowledge base.

The OKF knowledge base is a directory of Markdown files. Each file may
carry YAML frontmatter (type, verified, tags, ...) and may link to other
OKF files via standard Markdown links, e.g. ``[label](relative/path.md)``.

This engine treats the knowledge base as a directed graph: frontmatter
gives each node its metadata, and Markdown links give the edges. Traversal
is deterministic (depth-first, sorted by link order as it appears in the
document) so that the same query always returns the same context.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import frontmatter

# Matches standard Markdown links: [label](target)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


@dataclass
class OKFNode:
    """A single parsed OKF document."""

    path: str
    metadata: dict = field(default_factory=dict)
    content: str = ""
    links: list = field(default_factory=list)  # list of (label, resolved_path)


class OKFEngine:
    """Parses and traverses a directory of OKF Markdown documents."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self._cache: dict = {}

    def _resolve_link(self, source_path: str, target: str) -> str | None:
        """Resolve a relative Markdown link target to an absolute path
        rooted at ``root_dir``. Returns None for external/non-.md links."""
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return None
        if not target.endswith(".md"):
            return None
        source_dir = os.path.dirname(source_path)
        resolved = os.path.normpath(os.path.join(source_dir, target))
        if not resolved.startswith(self.root_dir):
            return None
        return resolved

    def parse_file(self, path: str) -> OKFNode:
        """Parse a single Markdown file: YAML frontmatter + Markdown links."""
        abs_path = os.path.abspath(path)
        if abs_path in self._cache:
            return self._cache[abs_path]

        with open(abs_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        links = []
        for label, target in _MD_LINK_RE.findall(post.content):
            resolved = self._resolve_link(abs_path, target)
            if resolved is not None:
                links.append((label, resolved))

        node = OKFNode(
            path=abs_path,
            metadata=dict(post.metadata),
            content=post.content,
            links=links,
        )
        self._cache[abs_path] = node
        return node

    def traverse(self, start_path: str, max_depth: int = 3) -> list:
        """Deterministically walk the OKF graph depth-first from
        ``start_path``, returning the list of visited OKFNode objects in
        traversal order. Cycles are not revisited."""
        visited: dict = {}
        order: list = []

        def _walk(path: str, depth: int) -> None:
            abs_path = os.path.abspath(path)
            if abs_path in visited or depth > max_depth:
                return
            node = self.parse_file(abs_path)
            visited[abs_path] = node
            order.append(node)
            for _, linked_path in node.links:
                _walk(linked_path, depth + 1)

        _walk(start_path, 0)
        return order

    def find_by_tag(self, tag: str) -> list:
        """Scan the whole knowledge base for documents carrying ``tag``."""
        matches = []
        for dirpath, _dirs, filenames in os.walk(self.root_dir):
            for filename in sorted(filenames):
                if not filename.endswith(".md"):
                    continue
                node = self.parse_file(os.path.join(dirpath, filename))
                if tag in (node.metadata.get("tags") or []):
                    matches.append(node)
        return matches

    def query(self, query_text: str, start_path: str | None = None) -> str:
        """Answer a canonical-facts query by traversing from the index
        (or a given start file) and returning the concatenated, verified
        content most relevant to the query.

        This is a deterministic lookup, not a semantic search: it matches
        keywords in the query against document tags/paths, then returns
        the full canonical content of matching documents plus anything
        they link to.
        """
        if start_path is None:
            start_path = os.path.join(self.root_dir, "index.md")

        query_lower = query_text.lower()
        candidates = self.traverse(start_path)

        keyword_matches = [
            node
            for node in candidates
            if node is not candidates[0]
            and (
                any(tag in query_lower for tag in (node.metadata.get("tags") or []))
                or os.path.splitext(os.path.basename(node.path))[0].lower() in query_lower
            )
        ]

        selected = keyword_matches if keyword_matches else candidates

        sections = []
        for node in selected:
            rel_path = os.path.relpath(node.path, self.root_dir)
            meta_line = ", ".join(f"{k}={v}" for k, v in node.metadata.items())
            sections.append(f"### Source: {rel_path} ({meta_line})\n\n{node.content.strip()}")

        return "\n\n---\n\n".join(sections)
