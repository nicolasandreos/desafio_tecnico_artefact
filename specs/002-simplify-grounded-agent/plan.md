# Implementation Plan: Simplify Grounded Answers

**Branch**: `002-simplify-grounded-agent` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-simplify-grounded-agent/spec.md`

## Summary

Feature 001 remains the customer-facing contract. This change corrects three paths and deletes what they make unused.

Operational facts are read with Pandas from the supplied CSV files. SQLite is not the operational database and not a copy of those files. Python tools filter the DataFrames directly. ChromaDB's own files are only the policy vector index.

Policy answers come from Agno 3.1.12 Knowledge: the policy PDF is ingested, split with semantic chunking, embedded, stored in Chroma, and retrieved by vector similarity before the model answers. The single switch for that is `add_knowledge_to_context=True`. `search_knowledge=False`, so Agno does not add a second search tool. A policy answer does not come from model memory or from a catalog, order, or promotion tool.

Portuguese, out-of-scope, sale-action, and disclosure limits move into the assistant instructions. Phrase-matching scripts are deleted. Order ownership, the sensitive-field allow-list, and the absence of any tool that changes an order stay in Python. Instructions are not the only protection for those boundaries.

Catalog search, promotion search, mail, and the store profile already do their jobs. They are not rewritten.

## Technical Context

**Language/Version**: Python 3.13 or newer, as declared in `pyproject.toml`

**Primary Dependencies**: Agno 3.1.12 (`knowledge`, `pdf`, `chromadb`, `openai`, `os` extras, without the `sqlite` extra), OpenAI embeddings `text-embedding-3-small`, ChromaDB, Pandas, Resend, Pytest. `SemanticChunking` imports `chonkie.SemanticChunker` and raises `ImportError` naming `chonkie[semantic]` when that extra is missing. Agno 3.1.12's `knowledge` extra already depends on `chonkie` with the `semantic` extra (confirmed in `uv.lock` and by importing `SemanticChunker` from the project environment, chonkie 1.7.0). Do not add a second direct `chonkie` dependency.

**Storage**: Pandas DataFrames loaded from the CSV files in `data/` on each operational read. ChromaDB collection `store_policies` for policy chunks only. Agno `InMemoryDb` for the current process conversation. Ownership codes and grants live in process memory, not in a database and not in a CSV. `DATA_DIR` overrides `data/` when set. Chroma files stay under `var/chroma`. Nothing operational is written back into `data/`.

**Testing**: Pytest. Catalog, promotion, order, ownership, and policy-retrieval tests call functions with fixtures and fakes. They do not call a live model. A live policy question stays manual and follows [quickstart.md](quickstart.md).

**Target Platform**: One local Python process. AgentOS serves the conversation on the local machine.

**Project Type**: Single Python application with a messaging interface.

**Performance Goals**: A policy question the document can answer is answered in one reply, in under one minute (SC-002). A named product returns its recorded price and availability in one reply. No throughput target.

**Constraints**: Feature 001 behavior stays except where this spec names the source of a fact or moves language and scope into the assistant. Application code does not use SQLite or SQLAlchemy for operational storage, CSV queries, sessions, ownership codes, or grants. SQLAlchemy may remain installed because the Agno `os` extra depends on it. That is not permission to use it. The `sqlite` extra stays removed. ChromaDB's on-disk index is not an operational database. Policy is not an operational tool. The prototype does not gain a new abstraction layer.

**Scale/Scope**: The supplied files: about 64 products, 10 categories, 50 customers, 20 orders, the matching item rows, and 25 promotions. One policy PDF. One conversation at a time in one process.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Pre-research result: **PASS**. Post-design result: **PASS**.

| Rule | How this design keeps it |
|------|--------------------------|
| Simplicity | Delete the operational database, the policy tool and service, and the phrase guards. Keep one agent. Do not rewrite catalog, promotion, mail, or the store profile. |
| Separation of concerns | `agent` wires the model and the knowledge base. Operational tools validate and call a service. Services filter DataFrames. `knowledge` ingests and searches the PDF. The agent module does not contain query logic or a phrase list. |
| Deterministic operational data | The same question against unchanged CSVs filters the same rows. The model does not recall a price, stock quantity, order field, or discount. |
| Security and privacy | Ownership, the field allow-list, and read-only tools stay in Python. The code is stored as a hash. Logs and tool results still omit email, phone, the code, and payment data. |
| Grounded answers | A policy sentence comes from a retrieved passage. An operational fact comes from a DataFrame row. A missing value stays missing. |
| Testability | The changed lookups and the ownership rules run under Pytest without a live model. |
| Recorded decisions | Choices and rejected alternatives are in [research.md](research.md). |
| Python, PEP, English source | Application code and tests stay Python. Names, docstrings, errors, and logs stay English. Customer replies stay Portuguese. |
| Current documentation | The knowledge settings below were read from the installed Agno 3.1.12 package and from the current Agno knowledge docs on 2026-10-31. |
| Prototype scope | No second agent, no database server, and no customer account beyond the in-process grant. |

No constitution gate failed. The complexity table is omitted.

## Technical Decisions

These two decisions are mandatory for implementation. The research note records why the alternatives were rejected.

### 1. Pandas for operational data

Python tools query Pandas DataFrames loaded from the supplied CSV files.

- Load with the existing `read_table` helper in `src/emporio_agent/data/csv_tables.py` (`pandas.read_csv`).
- Filter and join those DataFrames in the catalog, promotion, and order services.
- Do not insert the CSVs into SQLite or any other database. This ban is the operational path only. ChromaDB may keep its own files for the policy vectors.
- Do not import SQLAlchemy or `sqlite3` in `src/emporio_agent` for store facts, sessions, codes, or grants. The Agno `os` extra may still install SQLAlchemy. Leaving that package installed is not the same as using it.
- Do not add a repository, a query builder, or a unit-of-work around Pandas.

Catalog and promotion services already follow this. Leave their match rules in place. The order service already reads order rows from Pandas and still takes a SQLite connection for the ownership code. Replace that connection with the in-process store. Do not reimplement the allow-list or the 15-minute code.

### 2. Mandatory semantic RAG for policy

Use Agno 3.1.12 native Knowledge. Verified on the installed package (`.venv`, `agno` 3.1.12) and the current Agno docs:

| Setting | Installed 3.1.12 behavior | Value in this prototype |
|---------|---------------------------|-------------------------|
| `Agent.knowledge` | Knowledge base. Without it, knowledge search does nothing. | The policy `Knowledge` instance |
| `add_knowledge_to_context` | Default `False`. When `True`, `agent/_messages.py` calls `get_relevant_docs_from_knowledge` while building the user message, before the model is asked to answer. This does not depend on `search_knowledge`. | `True` |
| `search_knowledge` | Default `True`. `agent/_tools.py` adds the tool `search_knowledge_base` only when this is true and `knowledge` is set. The model may skip that tool. It does not search before the reply. | `False` |
| `add_search_knowledge_instructions` | Default `True`, but `_messages.py` adds those instructions only when `search_knowledge` is also true. | `False` |
| `update_knowledge` | Default `False`. A `True` value would let the model write the knowledge base. | `False` |
| `ChromaDb.search_type` | Default `SearchType.vector`, pure similarity search. | `SearchType.vector` |
| `Knowledge.max_results` | Default `10`. | `4` |

Pipeline, all inside `src/emporio_agent/knowledge/policy_knowledge.py`:

1. **PDF ingestion.** Read `data/políticas_da_loja.pdf` (or `DATA_DIR`) through Agno `PDFReader`. A missing file raises `FileNotFoundError` with the file name.
2. **Semantic chunking.** `PDFReader(split_on_pages=False, chunking_strategy=SemanticChunking(embedder=embedder))`. `split_on_pages=False` is the Agno setting that combines pages before semantic chunking. Do not switch to fixed-size or agentic chunking.
3. **Embedding generation.** `OpenAIEmbedder(id="text-embedding-3-small")` for both chunking and the vector store.
4. **Vector database storage.** `ChromaDb(collection="store_policies", path=<settings.chroma_path>, persistent_client=True, embedder=embedder, search_type=SearchType.vector)`. Products, orders, customers, and promotions are not embedded. The files Chroma writes under `var/chroma` are this index, not a SQLite copy of the CSVs.
5. **Similarity retrieval.** Chroma vector search through `Knowledge`. No keyword index and no hybrid fusion.
6. **Mandatory retrieval.** `knowledge=<that object>`, `add_knowledge_to_context=True`, and `search_knowledge=False`. Every user message is searched while the user message is built, before the model answers. Instructions say those passages are policy text and are used only for a policy question. There is no `search_policies` tool and no `search_knowledge_base` tool.

A policy question is not answered from memory and not from `search_products`, `search_promotions`, `get_order_details`, or `get_store_context`.

`search_knowledge=True` does not guarantee retrieval in this version. It only registers a tool the model can skip. Keeping it beside `add_knowledge_to_context=True` would be a second search path with no extra guarantee. It stays off.

`add_knowledge_to_context=True` searches every user message before the reply, including messages that are not about policy. This prototype accepts that. Do not replace it with a conditional search, a pre-hook, or an optional tool.

### When the PDF is indexed

`ensure_policy_index` lives in `src/emporio_agent/knowledge/policy_knowledge.py` and runs once when the agent is built. A customer message does not index. There is no second indexer.

Verified on the installed packages, not assumed: Agno 3.1.12 `ChromaDb` exposes `exists`, `drop`, `get_count`, and `client`. ChromaDB 1.5.9 `Collection.modify(metadata=...)` and `Collection.metadata` exist. No transaction API covers insert plus a completion mark, so the mark is a separate step after insert returns.

A chunk that carries `pdf_sha256` is not proof that indexing finished. A partial write can store that hash on the chunks it managed to save.

The collection is valid only when its collection metadata has `index_complete` equal to the SHA-256 of the current PDF bytes. That key is written with `Collection.modify` only after `Knowledge.insert` returns and `get_count()` is greater than zero. It is not written on chunk metadata.

1. The PDF is missing: raise `FileNotFoundError` with the file name. Do not create a collection.
2. The collection is missing, or `index_complete` is absent or different: `drop()` if the collection exists, then index. On success, set `index_complete` to the file hash.
3. `index_complete` equals the current file hash: stop. Do not call the embedder.
4. Insert or the completion mark fails: `drop()` again and raise. Do not leave the partial collection in place. Policy retrieval stays unavailable until a later run finishes. There is no second collection, no swap, and no rollback. Old or partial chunks are not served as the current policy.

An unchanged file is not re-embedded. A changed file is dropped and indexed again. A crash after some chunks exist, and before `index_complete` is set, is incomplete and is rebuilt on the next start.

## Architecture

```text
Customer
   |
   v
AgentOS  ---- InMemoryDb (this process only; not a store of CSV rows)
   |
   v
Agno Agent
   |  instructions: Portuguese, scope, sale action, disclosure, which source to use
   |  add_knowledge_to_context=True  --> Knowledge.search before the model answers
   |  search_knowledge=False         --> no search_knowledge_base tool
   |
   +-- Knowledge
   |     PDFReader + SemanticChunking
   |     OpenAIEmbedder text-embedding-3-small
   |     ChromaDb store_policies (vector similarity)
   |
   +-- read-only tools
         get_store_context     (store profile text)
         search_products       (Pandas)
         search_promotions     (Pandas)
         request_order_code    (Pandas lookup + in-process code)
         confirm_order_code    (in-process hash check)
         get_order_details     (grant required, then Pandas allow-list)
```

## What stays and what goes

| Keep, without a rewrite | Change | Delete |
|-------------------------|--------|--------|
| `services/catalog_service.py`, `tools/catalog_tools.py` | `agent/assistant.py`: attach Knowledge, `add_knowledge_to_context=True`, `search_knowledge=False`, `InMemoryDb`, no pre-hook, no policy tool | `language_guard.py`, `scope_guard.py`, `guard_path.py` |
| `services/promotion_service.py`, `tools/promotion_tools.py` | `agent/instructions.py`: policy from knowledge; language and scope as instructions | `tools/policy_tools.py`, `services/policy_service.py` |
| `services/store_service.py`, `tools/store_tools.py` | `knowledge/policy_knowledge.py`: one Knowledge object the agent and the indexer share | `data/connection.py`, `data/ingest.py`, `data/schema.sql` |
| `mail/`, `logging.py` | `data/otp_repository.py`: same hash, expiry, replacement, and grant rules, in process memory | `tests/unit/test_language_guard.py`, `tests/unit/test_scope_guard.py`, `tests/unit/test_policy_service.py` |
| Order allow-list and code rules in `services/order_service.py` | `tools/order_tools.py`: stop opening SQLite | SQLite helpers in `tests/unit/support.py` |

`config.sqlite_path` is removed. `session_db_path` is removed because the session store is `InMemoryDb()`.

## Security boundaries that stay in Python

These are not instructions and not phrase lists.

- `request_order_code` reads the order and the email from the DataFrames. It sends a 6-digit code and returns no order field and no email. Zero matches, more than one match, or a missing email sends nothing.
- The stored value is the SHA-256 hash. A new code marks the previous one replaced. A code older than 15 minutes is rejected.
- `confirm_order_code` writes a grant only for the `session_id` taken from the Agno run context. A model argument named `session_id` is ignored.
- `get_order_details` returns nothing until that grant exists. The result contains only the requested subset of `status`, `order_date`, `items`, and `total_brl`. Any other field name is `invalid_input`.
- No tool inserts, updates, or deletes a CSV row. No tool places, changes, cancels, or pays an order. `update_knowledge` stays false.
- Refusing a recipe, a sale, or a disclosure in the instructions does not replace the checks above.

## Error handling

| Failure | What the customer hears | What is logged |
|---------|-------------------------|----------------|
| Empty or oversized tool argument | A request for a clearer question | The error code |
| No CSV row, or more than five products | Not found, or a request to narrow the search | The error code and the match count |
| Unknown, duplicate, or emailless order | No order can be confirmed | Order id only |
| Wrong, expired, or replaced code | The code was not accepted | Order id and the reason, never the digits |
| Mail sender failure | The code could not be sent | Sender error name, never the address or the code |
| Missing CSV | That information is unavailable | The file name |
| Missing PDF or missing Chroma collection | Policy information is unavailable | The file or collection name |
| OpenAI or AgentOS failure | The assistant cannot answer right now | The exception type. No API key |

A refusal or a failed lookup does not change a CSV.

## Testing strategy

- Existing catalog and promotion tests stay. They already use CSV fixtures. Do not rewrite them unless a delete breaks an import.
- Order tests keep the current cases and swap the SQLite connection for the in-process store.
- A new test constructs the agent and asserts `add_knowledge_to_context is True`, `search_knowledge is False`, `knowledge` is set, `update_knowledge is False`, `pre_hooks` is empty, and the database is `InMemoryDb`. The application tools are exactly `get_store_context`, `search_products`, `search_promotions`, `request_order_code`, `confirm_order_code`, and `get_order_details`. `search_knowledge_base` and `search_policies` are absent.
- `tests/unit/test_policy_retrieval.py` uses a fake `Knowledge.search` and Agno's user-message preparation. It does not call the chat model. The fake search runs on the customer text and its passages are attached. An empty result attaches no passage. A raised search attaches no invented passage.
- `tests/unit/test_policy_index.py` does not call the chat model. A missing PDF raises `FileNotFoundError` with the file name and creates no collection. A collection whose `index_complete` equals the file hash does not call the embedder. A different hash drops the collection and indexes again. A collection that has chunks but no `index_complete` mark is not valid: it is dropped and rebuilt, and those chunks are not returned as the current policy. If indexing fails after the old collection was dropped, the test asserts the collection is not left searchable as the current policy.
- Phrase-list tests are deleted with the modules they import. Paraphrased refusals are checked by hand in the quickstart, because they are model behavior.
- `pytest` and Ruff remain the gates. No network suite.

## Project Structure

### Documentation (this feature)

```text
specs/002-simplify-grounded-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── conversation.md
│   ├── knowledge.md
│   └── tools.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

Feature `specs/001-customer-service-agent/` is not edited.

### Source Code (repository root)

```text
src/emporio_agent/
├── __main__.py
├── config.py
├── logging.py
├── agent/
│   ├── assistant.py          # Knowledge flags, InMemoryDb, read-only tools
│   └── instructions.py
├── tools/
│   ├── catalog_tools.py
│   ├── promotion_tools.py
│   ├── order_tools.py
│   └── store_tools.py
├── services/
│   ├── catalog_service.py
│   ├── promotion_service.py
│   ├── order_service.py
│   └── store_service.py
├── data/
│   ├── csv_tables.py         # Pandas reads
│   ├── otp_repository.py     # in-process codes and grants
│   └── values.py
├── knowledge/
│   └── policy_knowledge.py   # PDF, semantic chunks, embeddings, Chroma
└── mail/

tests/unit/
├── test_catalog_service.py
├── test_promotion_service.py
├── test_order_service.py
├── test_session_context.py
├── test_agent_boundaries.py
├── test_policy_retrieval.py
├── test_policy_index.py
└── ...                       # phrase-list and policy-tool tests removed
```

**Structure Decision**: Stay in the existing single package `src/emporio_agent`. Do not add a package for guards, databases, or a second policy API.
