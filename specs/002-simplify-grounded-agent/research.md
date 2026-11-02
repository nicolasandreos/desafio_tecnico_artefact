# Research: Simplify Grounded Answers

Decisions for feature 002. Feature 001 stays the customer-facing baseline. Application code is not changed by this document.

## Decision: Operational facts are Pandas DataFrames

**Decision**: Catalog, promotion, and order tools load the supplied CSVs with `pandas.read_csv` through `src/emporio_agent/data/csv_tables.py` and filter those DataFrames in the service. SQLite is not the operational database and not a copy of the CSV rows. ChromaDB's own files are the policy vector index, not that database.

**Rationale**: The review requires this path. Catalog and promotion services already do it. The same files and the same filters return the same rows, which is the deterministic access the constitution requires. A database between the file and the answer is the layer this feature removes.

**Alternatives considered**:

- Keep SQLite as the query store and use Pandas only to load it. Rejected. That is the current order-code path and the review forbids it.
- Use SQLAlchemy on the CSVs. Rejected. The review forbids SQLAlchemy, and the files are small enough to filter in memory.
- Add a repository interface around the DataFrames. Rejected. Nothing is shared that the existing `read_table` helper does not already share.

## Decision: Ownership state stays in the process, not in a database

**Decision**: The 6-digit code is stored only as a SHA-256 hash. A newer code marks the previous one replaced. The code expires 15 minutes after it is sent. A grant is the pair of AgentOS `session_id` and `order_id`. All of that lives in process memory inside `otp_repository.py`. The raw code, the email, and the order fields are not stored there.

**Rationale**: Those records are not in the CSVs. They are the security boundary the review says must not depend on the model. Putting them in SQLite would keep a database after the operational database is removed. The spec says the grant lasts for the current conversation, not across a new process.

**Alternatives considered**:

- Keep the `ownership_codes` and `order_grants` SQLite tables. Rejected. The review forbids SQLite for this prototype's data path, and those tables exist only to support the check.
- Write the grant into a new file under `data/`. Rejected. `data/` is the supplied material and must not be modified by a conversation.

## Decision: Conversation memory uses Agno InMemoryDb

**Decision**: `Agent.db` and AgentOS use `agno.db.in_memory.InMemoryDb`. Remove `sqlite_path`, `session_db_path`, and the `sqlite` extra. Application code does not use SQLite or SQLAlchemy for operational rows, CSV queries, sessions, codes, or grants. SQLAlchemy may stay installed because the Agno `os` extra depends on it. That transitive install is not use of the library.

**Rationale**: Agno 3.1.12 `InMemoryDb` subclasses `BaseDb`, which is the type `AgentOS` accepts. Follow-ups work for the life of the process. A restart is a new conversation, which matches the spec. Removing the `sqlite` extra remains valid because sessions do not need it. It does not uninstall SQLAlchemy while the `os` extra is present.

**Alternatives considered**:

- Keep `SqliteDb` for sessions only. Rejected. Sessions must not be stored in SQLite. The `os` extra, not only the `sqlite` extra, is why SQLAlchemy can remain installed.
- Use `JsonDb`. Rejected. It persists sessions the spec does not ask to keep, and it is a second store with no customer-facing gain.

## Decision: Policy retrieval is `add_knowledge_to_context=True` only

**Decision**: One `Knowledge` object in `policy_knowledge.py`, attached to the agent:

- `PDFReader(split_on_pages=False, chunking_strategy=SemanticChunking(embedder=OpenAIEmbedder(id="text-embedding-3-small")))`
- `ChromaDb(..., search_type=SearchType.vector, persistent_client=True, collection="store_policies")`
- `Knowledge(max_results=4)`
- `add_knowledge_to_context=True`
- `search_knowledge=False`
- `add_search_knowledge_instructions=False`
- `update_knowledge=False`

`ensure_policy_index` runs once when the agent is built. A customer message does not index. The collection is valid only when Chroma collection metadata `index_complete` equals the SHA-256 of the current PDF, written with `Collection.modify` after insert returns and the collection is non-empty. Chunks that merely carry the file hash are not that proof. A missing or different mark is dropped and rebuilt. A failed rebuild drops the collection again and leaves policy retrieval unavailable. There is no second collection and no rollback. `add_knowledge_to_context=True` searches every message, including non-policy messages. That is accepted. Do not switch it for a conditional search, a pre-hook, or an optional tool.

Verified on 2026-11-01 from the installed packages: Agno 3.1.12 `ChromaDb.exists`, `drop`, `get_count`, and `client`; ChromaDB 1.5.9 `Collection.modify(metadata=...)` and `Collection.metadata`. No transaction spans insert and the completion mark.

Also verified on Agno 3.1.12:

- `agent/_messages.py` calls `get_relevant_docs_from_knowledge` while building the user message when `add_knowledge_to_context` is true. That call does not depend on `search_knowledge`.
- `agent/_tools.py` adds `search_knowledge_base` only when `search_knowledge` is true and knowledge is set. The model can skip that tool. It does not search before the reply.
- `SemanticChunking` imports `chonkie.SemanticChunker`. Agno's `knowledge` extra already requires `chonkie[semantic]`. Chonkie 1.7.0 with `SemanticChunker` is installed. No direct `chonkie` dependency is added.
- `ChromaDb.search_type` defaults to `SearchType.vector`.

The custom `search_policies` tool is removed. Instructions tell the model that inserted passages are policy text and are not a price, a stock quantity, an order field, or a discount.

**Rationale**: Mandatory retrieval means the search runs before the model answers. In 3.1.12 only `add_knowledge_to_context=True` does that. `search_knowledge=True` is a second, optional tool. It stays off.

**Alternatives considered**:

- `search_knowledge=True` only. Rejected. In 3.1.12 that only registers a tool. A policy answer can still come from memory.
- Both flags. Rejected. The pre-answer search already covers every message. The extra tool does not make retrieval more certain.
- Keep `search_policies` as a wrapper over `Knowledge.search`. Rejected. Policy is not an operational tool.
- Rebuild the collection on every startup. Rejected. Unchanged PDF bytes would pay for embeddings again.
- Rely on Agno `skip_if_exists` alone. Rejected. For a file path, Agno's content hash does not include the file bytes, so a changed PDF with the same path would be skipped.
- A direct `chonkie[semantic]` dependency. Rejected. The `knowledge` extra already requires it.
- Hybrid search. Rejected. The requirement is similarity search. Vector is the installed default.
- A numeric distance cutoff in Python. Rejected. The spec already says a passage that does not state the rule is not the answer. That judgment stays in the instructions.

## Decision: Language and scope move to instructions; order security stays in Python

**Decision**: Delete `language_guard.py`, `scope_guard.py`, and `guard_path.py`, and remove the agent pre-hook. Put Portuguese-only replies, out-of-scope refusal, sale-action refusal, and disclosure refusal in `instructions.py`, including the instruction to judge meaning rather than a fixed sentence. Keep the order code, the grant, the allow-list, and the lack of any write tool in Python.

**Rationale**: The review splits these on purpose. A phrase list misses ordinary wording. An instruction the model can be talked out of is not an acceptable lock on another customer's order.

**Alternatives considered**:

- Move the ownership check into the instructions as well. Rejected. The review says the model must not be the only protection.
- Keep the phrase guards and also add instructions. Rejected. The guards are the redundant scripts the review tells us to remove.

## Decision: Do not rewrite working catalog, promotion, mail, or profile code

**Decision**: Leave `catalog_service.py`, `promotion_service.py`, `store_service.py`, and `mail/` in place except where an import of a deleted module forces a one-line fix.

**Rationale**: Those paths already read CSVs or a text profile and do not use SQLite. Rewriting them would add risk without a behavior change.

**Alternatives considered**: Collapse services into the tool functions. Rejected. The constitution separates tools from data access, and the split already exists and is tested.
