"""RAG Engine: loads unstructured documents from /docs, chunks them,
embeds them locally with a HuggingFace sentence-transformer model, and
builds a FAISS vector index for similarity search.

This engine is the counterpart to okf_engine.py: where OKF handles
canonical, verified facts via deterministic graph traversal, RAG handles
unstructured historical text (logs, incident reports, free-form notes)
via semantic similarity search.
"""

from __future__ import annotations

import os

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class RAGEngine:
    """Loads /docs, builds a local FAISS index, and answers similarity
    search queries over unstructured historical text."""

    def __init__(
        self,
        docs_dir: str,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self.docs_dir = os.path.abspath(docs_dir)
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.vectorstore: FAISS | None = None
        self._build_index()

    def _load_documents(self) -> list:
        loader = DirectoryLoader(
            self.docs_dir,
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        return loader.load()

    def _build_index(self) -> None:
        documents = self._load_documents()
        if not documents:
            self.vectorstore = None
            return

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        chunks = splitter.split_documents(documents)
        self.vectorstore = FAISS.from_documents(chunks, self.embeddings)

    def similarity_search(self, query: str, k: int = 3) -> list:
        """Return the top-k most similar chunks to ``query``."""
        if self.vectorstore is None:
            return []
        return self.vectorstore.similarity_search(query, k=k)

    def query(self, query_text: str, k: int = 3) -> str:
        """Answer an unstructured/historical query by running a similarity
        search and returning the synthesized retrieved context."""
        results = self.similarity_search(query_text, k=k)
        if not results:
            return "No relevant historical documents found."

        sections = []
        for doc in results:
            source = doc.metadata.get("source", "unknown")
            rel_source = os.path.relpath(source, self.docs_dir) if os.path.exists(source) else source
            sections.append(f"### Source: {rel_source}\n\n{doc.page_content.strip()}")

        return "\n\n---\n\n".join(sections)
