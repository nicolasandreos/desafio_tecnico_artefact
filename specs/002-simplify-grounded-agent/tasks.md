# Tasks: Simplify Grounded Answers

**Input**: Design documents from `/specs/002-simplify-grounded-agent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included. The constitution requires a test when grounding, operational lookup, or privacy changes. Current tests also import modules this feature deletes. These tasks update that suite. They are not a new product behavior.

**Organization**: Tasks are grouped by user story so each story can be implemented and checked on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/emporio_agent/`, `tests/unit/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Drop the database extra the operational path will no longer use

- [X] T001 Remove the `sqlite` extra from the `agno` dependency in `pyproject.toml`, and remove the hatch `force-include` of `src/emporio_agent/data/schema.sql`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove the operational database without dropping the ownership check

**⚠️ CRITICAL**: No user story work begins until this phase is complete

- [X] T002 Replace the SQLite ownership store in `src/emporio_agent/data/otp_repository.py` with process memory. Keep these rules from `data-model.md`: store only the SHA-256 `code_hash` of the 6-digit code, set `expires_at` to `sent_at` plus 15 minutes, set `replaced` when a newer code is sent for that `order_id`, and record a grant as `session_id` plus `order_id`. After confirmation the grant allows any later subset of `status`, `order_date`, `items`, and `total_brl` for that order and session, not only the first field. An invalid code does not create a grant. Do not add an attempt counter or a lockout. Do not store the raw code
- [X] T003 Remove the SQLite `connection` argument from `src/emporio_agent/services/order_service.py` and stop opening a database in `src/emporio_agent/tools/order_tools.py`. Order rows still come from Pandas through `src/emporio_agent/data/csv_tables.py`. `session_id` still comes from the Agno run context, and a model-supplied `session_id` is ignored
- [X] T004 Delete `src/emporio_agent/data/connection.py`, `src/emporio_agent/data/ingest.py`, and `src/emporio_agent/data/schema.sql`. Update the module text in `src/emporio_agent/data/__init__.py` so it no longer describes SQLite
- [X] T005 Remove `sqlite_path` and `session_db_path` from `src/emporio_agent/config.py`

**Checkpoint**: CSV reads and the in-process grant work. Order tests that still open SQLite fail until Phase 4. Catalog tests that only use CSV fixtures still pass.

---

## Phase 3: User Story 1 - Get a policy answer from the policy document (Priority: P1) 🎯 MVP

**Goal**: Every policy question is answered from semantic retrieval of the policy PDF, and from no operational tool

**Independent Test**: The agent flags and tool list match the plan. A fake search runs before any model call, including an empty result and a failed search. An incomplete index is not treated as valid. `search_policies` and `search_knowledge_base` are not tools.

### Tests for User Story 1

- [X] T006 [P] [US1] Add `tests/unit/test_agent_boundaries.py` asserting `add_knowledge_to_context` is true, `search_knowledge` is false, `add_search_knowledge_instructions` is false, `knowledge` is set, `update_knowledge` is false, `pre_hooks` is empty, and the database is Agno `InMemoryDb`. Application tools are exactly `get_store_context`, `search_products`, `search_promotions`, `request_order_code`, `confirm_order_code`, and `get_order_details`. `search_knowledge_base` and `search_policies` are absent
- [X] T007 [P] [US1] Add `tests/unit/test_policy_retrieval.py`. Use a fake `Knowledge.search` and Agno's user-message preparation. Do not call the chat model. The fake search runs on the customer text and its passages are attached. An empty result attaches no passage. A raised search attaches no invented passage
- [X] T008 [P] [US1] Add `tests/unit/test_policy_index.py`. Do not call the chat model. A missing PDF raises `FileNotFoundError` with `políticas_da_loja.pdf` and creates no collection. `index_complete` equal to the file hash does not call the embedder. A different hash drops the collection and indexes again. Chunks without `index_complete` are not valid: they are dropped and rebuilt, and they are not returned as the current policy. A failed rebuild after the old collection was dropped does not leave that collection searchable as the current policy

### Implementation for User Story 1

- [X] T009 [US1] In `src/emporio_agent/knowledge/policy_knowledge.py`, build one Agno 3.1.12 `Knowledge` object: `PDFReader(split_on_pages=False)`, `SemanticChunking` with `OpenAIEmbedder(id="text-embedding-3-small")`, `ChromaDb` collection `store_policies` with `SearchType.vector` and `persistent_client=True`, and `Knowledge(max_results=4)`. `ensure_policy_index` runs only from agent build. The collection is valid only when collection metadata `index_complete` equals the SHA-256 of the PDF, set with ChromaDB 1.5.9 `Collection.modify` after insert returns and `get_count()` is greater than zero. A chunk hash alone is not valid. A missing or different mark is dropped, then indexed. A failed insert or mark calls `drop()` again and raises, so partial chunks are not served. A missing PDF raises `FileNotFoundError` with `políticas_da_loja.pdf`. Do not embed products, orders, customers, or promotions. Do not add a direct `chonkie` dependency
- [X] T010 [US1] In `src/emporio_agent/agent/assistant.py`, call `ensure_policy_index` once, attach that `Knowledge`, set `add_knowledge_to_context=True`, `search_knowledge=False`, and `add_search_knowledge_instructions=False`, keep `update_knowledge=False`, set `db` to `InMemoryDb`, remove `pre_hooks`, and remove `search_policies` from the tool list. If `ensure_policy_index` fails, do not start the agent against a partial collection
- [X] T011 [US1] In `src/emporio_agent/agent/instructions.py`, state that a policy answer uses only the passages already retrieved into the message, and that a passage is not a price, a stock quantity, an order status, or a discount
- [X] T012 [US1] Delete `src/emporio_agent/tools/policy_tools.py`, `src/emporio_agent/services/policy_service.py`, and `tests/unit/test_policy_service.py`

**Checkpoint**: User Story 1 tests pass. A live PDF question is the manual check in `quickstart.md`.

---

## Phase 4: User Story 2 - Get operational facts from the supplied tables (Priority: P1)

**Goal**: Product, order, and promotion facts come from the CSV files, and order fields stay behind the ownership check

**Independent Test**: With the table files present and no database, a known product returns its recorded price, an order status is hidden until the code is accepted, and a current promotion comes from the promotion file.

- [X] T013 [P] [US2] Leave the Pandas match rules in `src/emporio_agent/services/catalog_service.py` and `src/emporio_agent/services/promotion_service.py`. Product search matches `name` only. One to five matches return `name`, `category_name`, `price_brl`, `stock_quantity`, and `status`. A missing `price_brl`, `stock_quantity`, or `category_name` stays null. More than five matches return `too_broad`, the match count, and no product rows. Promotions keep only `is_active` 1, do not invent a start or end date, and a name or category query excludes other products. A missing file means unavailable. A present file with no match, including zero rows, means nothing matched. Those outcomes stay distinct even when the return value does not use those words as keys. Remove a `sqlite3` or SQLAlchemy import if one is present. Do not rewrite the rules
- [X] T014 [P] [US2] Point `tests/unit/test_order_service.py` at the in-process store. Keep these cases: no order field before a correct code; after acceptance only the requested subset of `status`, `order_date`, `items`, and `total_brl`; a later turn may ask a different allow-listed subset without a new code; any other field name, including `email` or `payment_method`, is `invalid_input` and returns no order field; reject `000000`; reject a code older than 15 minutes; reject a replaced code; an invalid code does not create a grant and there is no attempt counter; match `order_id` after trim and without regard to letter case; `code_not_sent` when mail fails; `not_owner` for a different session; a new process does not keep the grant. A missing order file means unavailable. A present file with no row means nothing matched. Those outcomes stay distinct even when the return value does not use those words as keys
- [X] T015 [P] [US2] Remove SQLite setup from `tests/unit/support.py`, `tests/unit/test_session_context.py`, `tests/unit/test_log_redaction.py`, and `tests/unit/test_refusal_is_read_only.py`. The refusal test asserts that calling the read-only tools does not change a CSV file

**Checkpoint**: User Stories 1 and 2 both pass their automated checks.

---

## Phase 5: User Story 3 - Hear the right refusal in ordinary words (Priority: P2)

**Goal**: Language and scope are instructions. Phrase-matching scripts are gone

**Independent Test**: The guard modules are absent, the agent has no pre-hook, and `instructions.py` tells the model how to refuse an out-of-scope request, a sale action, and a disclosure request, including wording that is not a fixed example sentence.

- [X] T016 [US3] Extend `src/emporio_agent/agent/instructions.py` so the assistant replies in Portuguese, refuses a non-Portuguese request without answering it, still answers a Portuguese sentence that only quotes a recorded product name, and keeps the three refusals distinct: out of scope, sale action, and disclosure. A return procedure, a payment rule, and a recorded cancelled status are not those refusals
- [X] T017 [P] [US3] Delete `src/emporio_agent/language_guard.py`, `src/emporio_agent/scope_guard.py`, `src/emporio_agent/guard_path.py`, `tests/unit/test_language_guard.py`, and `tests/unit/test_scope_guard.py`

**Checkpoint**: Phrase lists are gone. Paraphrased refusals are checked by hand with `quickstart.md`, because they are model behavior.

---

## Phase 6: User Story 4 - Keep one source for each kind of fact (Priority: P2)

**Goal**: The prototype contains only the parts a specified behavior uses

**Independent Test**: A price-and-policy reply uses the product CSV and the policy collection. A review of `src/emporio_agent` finds no phrase filter, no operational database, and no policy tool.

- [X] T018 [US4] Remove imports of deleted modules from `src/emporio_agent/tools/__init__.py`, `src/emporio_agent/services/__init__.py`, `src/emporio_agent/knowledge/__init__.py`, and `src/emporio_agent/agent/__init__.py`
- [X] T019 [US4] Search `src/emporio_agent` for `sqlite3`, `sqlalchemy`, `search_policies`, `language_guard`, `scope_guard`, and `guard_path`. Delete any leftover file that exists only for those names
- [X] T020 [US4] Run `pytest` and `ruff check src tests`. Fix only failures caused by this change

**Checkpoint**: All four stories are in place and the automated suite passes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Confirm the validation guide matches the finished suite

- [X] T021 Run the automated section of `specs/002-simplify-grounded-agent/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories
- **User Stories (Phases 3–6)**: Depend on Foundational. US1 and US2 have no dependency on each other after that. With one coding agent, finish US1 before US2. US3 edits `instructions.py` only after US1's edit of that file. US4 runs last
- **Polish (Phase 7)**: Depends on US4

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational. No dependency on US2
- **User Story 2 (P1)**: After Foundational. No dependency on US1. Prefer running it after US1 when only one agent is implementing
- **User Story 3 (P2)**: After T011, because T011 and T016 both edit `src/emporio_agent/agent/instructions.py` and must not run at the same time
- **User Story 4 (P2)**: After US1, US2, and US3, because it deletes what those stories made unused

### Within Each User Story

- T006, T007, and T008 are written before T009 and T010
- T009 before T010
- T012 after T010, so nothing still imports the policy tool
- T011 before T016, same file, not in parallel
- T003 after T002. T004 after T003. T005 after T004

### Parallel Opportunities

- T006, T007, and T008 touch different test files and can run together
- T013, T014, and T015 touch different files and can run together after Phase 2
- T017 can run beside T016 because it does not edit `instructions.py`
- Do not run T011 and T016 at the same time

---

## Parallel Example: User Story 1 tests

```text
T006 tests/unit/test_agent_boundaries.py
T007 tests/unit/test_policy_retrieval.py
T008 tests/unit/test_policy_index.py
```

## Parallel Example: User Story 3

```text
T016 src/emporio_agent/agent/instructions.py
T017 src/emporio_agent/language_guard.py and the other guard modules
```

T016 and T017 can run together. T016 must not run while T011 is still editing `instructions.py`.

## Parallel Example: User Story 2

```text
T013 catalog_service.py and promotion_service.py
T014 test_order_service.py
T015 support.py, test_session_context.py, test_log_redaction.py, test_refusal_is_read_only.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2
2. Complete Phase 3, tests before the Knowledge implementation and the agent wiring
3. Stop and run `tests/unit/test_agent_boundaries.py`, `tests/unit/test_policy_retrieval.py`, and `tests/unit/test_policy_index.py`
4. Do not start a live rewrite of catalog or promotion code

### Incremental Delivery

1. Setup and foundational work remove the operational database and keep the ownership check
2. User Story 1 turns policy retrieval on
3. User Story 2 updates the order tests to the in-process store
4. User Story 3 deletes the phrase guards
5. User Story 4 removes whatever those stories left unused

### Parallel Team Strategy

After Phase 2, US1 and US2 may proceed in parallel. With one coding agent, finish US1 before US2. User Story 3 waits until T011 has finished editing `instructions.py`. User Story 4 waits for the other three.

---

## Notes

- [P] tasks use different files and do not depend on an unfinished task
- Do not rewrite `catalog_service.py`, `promotion_service.py`, `store_service.py`, or `mail/` except to drop a broken import
- Feature `specs/001-customer-service-agent/` is not edited
- Application code stays unchanged until these tasks are approved

## Phase 8: Convergence

- [X] T022 State in `src/emporio_agent/agent/instructions.py` that a request in a language other than Portuguese is refused in Portuguese, that the reply says the assistant only communicates in Portuguese, and that the request is not answered, per US3/AC1 and FR-010 (partial)
