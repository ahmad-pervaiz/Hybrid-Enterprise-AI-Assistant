# Walkthrough & Next Steps

This is your checklist for finishing setup and trying out the Hybrid
Enterprise AI Assistant (OKF + RAG). Everything below reflects the state
of the code that is already pushed to `origin/main` on GitHub.

## 1. What's already done

- [x] `okf_knowledge/` — canonical index, SLA policy, database schema (all
      cross-linked via Markdown links and YAML frontmatter).
- [x] `docs/incident_history.txt` — sample unstructured incident log.
- [x] `okf_engine.py` — deterministic OKF parser/graph traversal.
- [x] `rag_engine.py` — FAISS + HuggingFace embeddings over `/docs`.
- [x] `router.py` — classifies each query as `okf`, `rag`, or `hybrid`
      (queries both engines and cross-links RAG incidents to their SLA row
      in OKF).
- [x] `main.py` — CLI entry point.
- [x] `ui_server.py` + `ui/index.html` — local web UI with an animated
      pipeline view of the router's decision.
- [x] All of the above is committed and pushed to
      `https://github.com/ahmad-pervaiz/Hybrid-Enterprise-AI-Assistant`.

## 2. What's NOT done yet (your next steps)

### Step 1 — Finish installing dependencies

A virtual environment already exists at `~/.venvs/hybrid-enterprise-ai-assistant`
(created outside the project folder on purpose — the project lives on an
NTFS-mounted drive, which is very slow for installing thousands of small
package files; the venv lives on your native Linux disk instead).

`okf_engine.py`'s dependencies (`python-frontmatter`, `PyYAML`) are
**already installed** — OKF queries work right now.

The RAG dependencies (`torch`, `faiss-cpu`, `sentence-transformers`) are
large and were still installing over a slow connection. By default, `pip`
pulls the **GPU/CUDA build of torch**, which drags in several extra
gigabytes of NVIDIA CUDA libraries you don't need for this project. Install
the CPU-only build instead — it's a fraction of the size:

```bash
source ~/.venvs/hybrid-enterprise-ai-assistant/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

The second command will see torch is already satisfied and just install
`langchain`, `langchain-community`, `faiss-cpu`, and `sentence-transformers`
around it.

Check whether it's done at any time with:

```bash
~/.venvs/hybrid-enterprise-ai-assistant/bin/python -c "import torch, faiss, sentence_transformers; print('RAG deps OK')"
```

### Step 2 — Run the CLI

```bash
source ~/.venvs/hybrid-enterprise-ai-assistant/bin/activate
python main.py "What is the SLA for P1 incidents?"        # OKF-style
python main.py "What happened during the checkout outage?" # RAG-style
python main.py "Did the database failover incident breach the SLA?" # hybrid
```

Or drop the argument for an interactive REPL (`python main.py`, then type
queries, `exit` to quit).

### Step 3 — Run the web UI

```bash
source ~/.venvs/hybrid-enterprise-ai-assistant/bin/activate
python ui_server.py
```

Open <http://127.0.0.1:8000>. Try the example query chips, or type your
own. Watch the pipeline: `Query -> Router -> OKF/RAG -> Cross-link ->
Context` lights up only the stages your query actually used. The "RAG"
status pill in the header shows `loading` until the FAISS index finishes
building in the background, then `ready`.

### Step 4 — Try queries that exercise each route

| Query | Expected route |
|---|---|
| "Show the database schema for the incidents table" | `okf` |
| "What is the SLA for P1 incidents?" | `okf` |
| "What happened during the checkout outage?" | `rag` |
| "Give me the timeline of the auth service incident" | `rag` |
| "Did the database failover incident breach the SLA?" | `hybrid` (queries both, and cross-links the incident to its SLA row) |

### Step 5 — (Optional) Add more knowledge

- Drop more `.md` files into `okf_knowledge/policies/` or
  `okf_knowledge/schemas/` (with YAML frontmatter) — `okf_engine.py`
  will pick them up automatically via `find_by_tag` / link traversal.
  Link them from `index.md` or from an existing doc's Markdown links so
  the deterministic traversal can reach them.
- Drop more `.txt` files into `docs/` — `rag_engine.py` re-chunks and
  re-indexes the whole directory each time `RAGEngine` is constructed
  (i.e. each time you restart `main.py` / `ui_server.py`).

## 3. Known constraints worth knowing about

- **Network speed**: this environment's connection to PyPI has been slow
  and occasionally drops mid-download. If `pip install` stalls or fails
  with a `NameResolutionError` / `incomplete-download`, just re-run the
  same `pip install` command — it resumes rather than restarting from
  zero.
- **Python 3.14**: this is a very new interpreter; a couple of packages
  only offer source-less prebuilt wheels for it as of very recently, so
  stick to the exact `pip install` commands above rather than pinning
  older versions.
- **NTFS project folder**: don't create another venv inside the project
  folder itself — it will be extremely slow to install into and to import
  from. Keep using `~/.venvs/hybrid-enterprise-ai-assistant`.
