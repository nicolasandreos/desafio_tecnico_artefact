# Implementation Plan: Emporio da Musica Customer Service Agent

**Branch**: `001-customer-service-agent` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-customer-service-agent/spec.md`

## Summary

Customers of Emporio da Musica talk, in Portuguese, with one assistant. The assistant answers from supplied store facts, the product catalog, order records, promotions, and the policy PDF. It does not invent facts, and it reveals an order only after the customer proves ownership with a 6-digit code sent to the recorded email.

The prototype uses one Agno agent served by AgentOS. Operational questions run as ordinary Python functions over SQLite. The policy PDF is the only RAG corpus: Agno Knowledge, semantic chunking, ChromaDB, and `text-embedding-3-small`. Pandas loads the CSVs once. Pytest tests the functions without a live chat.

## Technical Context

**Language/Version**: Python 3.13 or newer

**Primary Dependencies**: Agno (agent and tools), AgentOS (exposure and sessions), OpenAI (chat and embeddings), Agno Knowledge, ChromaDB, SQLite, Pandas, Pytest

**Storage**: SQLite for catalog, orders, promotions, customers, ownership codes, and session grants. A second SQLite file for AgentOS conversation history. Local ChromaDB for policy chunks. The ingest source is the repository folder `data/`: six CSVs and `políticas_da_loja.pdf`. Those files are not the query source. `DATA_DIR` overrides that folder when set. Generated SQLite and Chroma files go under `var/`, not into `data/`.

**Testing**: Pytest. Unit tests call services and tools with a temporary database and an in-memory mail sender. No test requires a live model.

**Target Platform**: Local Python process. AgentOS serves the conversation on the local machine.

**Project Type**: Single Python application with a messaging interface.

**Performance Goals**: A customer who names one catalog product receives its recorded price and stock in one reply, in under one minute, as specified in SC-002. No throughput target.

**Constraints**: Portuguese replies only. Recorded facts quoted as stored. Order answers limited to status, date, items, and amount, and only after the email code. Secrets stay in the environment. One prototype, not a multi-service platform.

**Scale/Scope**: The supplied files: about 64 products, 10 categories, 50 customers, 20 orders, the matching item rows, and 25 promotions, of which four are active. One conversation at a time is the demo. Sessions may be stored so a follow-up works.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Pre-research result: **PASS**. Post-design result: **PASS**.

| Rule | How the design keeps it |
|------|-------------------------|
| Simplicity | One agent, two local SQLite files, one local Chroma directory. AgentOS tracing, scheduler, and MCP stay off. |
| Separation of concerns | `agent` wires the model. `tools` validate and delegate. `services` hold the rules. `data` runs SQL. `knowledge` searches the PDF. |
| Deterministic operational data | Price, stock, order, and promotion answers come from SQL. The same arguments return the same stored rows. |
| Security and privacy | Credentials are environment variables. Order tools use a column allow-list. The email and the code never appear in a tool result or a log. |
| Grounded answers | Instructions may speak only tool fields. Missing data returns `not_found` or an absent field, not a guessed value. |
| Testability | Services and tools run under Pytest without AgentOS or OpenAI. |
| Recorded decisions | Choices and rejected alternatives are in [research.md](research.md). |
| Python, PEP, English source | Application code and tests are Python. Names, docstrings, errors, and logs are English. Customer replies are Portuguese. |
| Current documentation | Before the Knowledge module or the AgentOS entrypoint is written, the author reads the current Agno and AgentOS pages. The 2026-10-31 index did not return a Knowledge constructor page, so that read is mandatory rather than optional. |
| Prototype scope | No second agent, no external database server, and no customer accounts beyond the in-session grant. |

## Architecture Overview

```text
Customer
   |
   v
AgentOS  ---- session SQLite (transcript only)
   |
   v
Agno Agent (OpenAI chat, Portuguese instructions)
   |
   +-- tools (validate input, call a service)
          |
          +-- catalog / promotion / order services
          |        |
          |        +-- SQLite repositories
          |
          +-- store profile service (full text of the short profile)
          |
          +-- policy service
                   |
                   +-- Agno Knowledge
                            |
                            +-- ChromaDB (policy PDF chunks)
```

Pandas ingest sits beside this path. It runs before the first conversation and reloads SQLite and the policy index from `data/`. The agent never opens a CSV.

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `agent` | Create the one Agno agent, attach tools, session storage, and instructions. Serve it with AgentOS. Contain no SQL and no ranking logic. |
| `tools` | Check argument shape and length. Call one service. Return the service result unchanged. Tools do not write operational rows. |
| `guards` | Before the model runs, `language_guard` refuses a non-Portuguese message and `scope_guard` refuses an out-of-scope request, a sale action, or a disclosure request. A refusal calls no tool. |
| `services` | Matching rules, the five-product cap, active promotions, the ownership code, and the order field allow-list. |
| `data` | Parameterized SQL, ingest from Pandas, and schema creation. |
| `knowledge` | Build the policy index with semantic chunking and `text-embedding-3-small`. Search it for a question. |
| `mail` | Send the six-digit code, or capture it in the test outbox. Hide the address and the code from the agent result. |
| `config` | Read paths, the OpenAI key, the chat model id, and optional SMTP settings from the environment. |
| `logging` | English error logs for ingest, mail, and order failures. Never an API key, email, phone, ownership code, or SMTP password. |

## Data Ingestion

1. Read `data/` unless `DATA_DIR` points somewhere else. Fail with the missing file name if a required CSV or `data/políticas_da_loja.pdf` is absent.
2. Load each CSV in that folder with Pandas. Keep the source column names listed in [data-model.md](data-model.md). The files are `desafio_tecnico_ai_eng - products.csv`, `desafio_tecnico_ai_eng - categories.csv`, `desafio_tecnico_ai_eng - customers.csv`, `desafio_tecnico_ai_eng - orders.csv`, `desafio_tecnico_ai_eng - order_items.csv`, and `desafio_tecnico_ai_eng - promotions.csv`.
3. Replace the operational tables in a transaction so a second run does not duplicate rows.
4. Leave customer name, phone, email, and city in SQLite for the ownership join. No tool selects them into a response.
5. Chunk `data/políticas_da_loja.pdf` semantically and embed those chunks into the Chroma collection `store_policies`. Rebuild that collection on each ingest so the index matches the file.
6. Do not embed products, orders, customers, or promotions.
7. `data/store_profile.md` is read in full by `get_store_context`. It may state only facts the materials support, including the store name and Campo Grande, Mato Grosso do Sul. It must not invent hours, a street, or a phone number. It sits beside the CSVs and is not one of the supplied CSV or PDF files.

## Retrieval Strategy

| Question | Path | Why |
|----------|------|-----|
| Price and availability | `search_products` SQL `LIKE` on the normalized product name only, capped at five rows. Each match includes `category_name`. Null price or stock stays null | The spec requires the recorded price and availability, and repeated questions must match |
| Current promotion | `search_promotions` joins products and categories, keeps `is_active = 1`, and matches the query to the product name or the category name | The file has no dates. `is_active` is the current flag, not a date. A filter must not return promotions for other products |
| Order status, date, items, amount | `get_order_details` after a grant, returning only the requested allow-list fields | Deterministic row, plus the privacy gate |
| Policy or procedure | `search_policies` over Chroma | The source is a PDF and the task requires RAG |
| Store identity | `get_store_context` | A short profile should not depend on a similarity score |
| Anything else | No tool, or a tool `not_found` | The agent says it cannot confirm |

A question that needs a price and a policy calls both tools. The price in the reply comes from SQL. The policy sentence comes from a retrieved passage.

## Tool Calling Workflow

1. AgentOS receives the message and loads the session transcript.
2. `language_guard` and `scope_guard` run before the model. A refusal is Portuguese, calls no tool, and does not write the operational database.
3. Otherwise the agent decides whether a tool is needed. Instructions say to call a tool before stating a store fact, and to ask an order tool only for the fields the customer named.
4. The tool rejects a bad argument with `invalid_input` before any query.
5. The service reads SQLite or the policy index and returns a code plus fields.
6. The agent writes a Portuguese reply using only those fields.
7. For an order, the sequence is fixed: `request_order_code`, then `confirm_order_code`, then `get_order_details`. The first two results contain no order facts. The third runs only when the grant for this session exists, and its `fields` list is the subset the customer asked about.
8. A follow-up in the same session may call `get_order_details` again without a new code. A new session may not.

Tool names, inputs, and error codes are in [contracts/tools.md](contracts/tools.md).

## Error Handling

| Failure | What the customer hears | What is logged |
|---------|-------------------------|----------------|
| Empty or oversized argument | A request for a clearer question | The error code, not the raw payload if it could contain a code |
| No row, an empty loaded table, or more than five products | Not found, or a request to narrow the search | The error code and the match count |
| Unknown, duplicate, or emailless order | No order can be confirmed. No code is sent when the id is not unique or has no email | Order id only |
| Wrong, expired, or replaced code | The code was not accepted | Order id and the reason, never the submitted digits |
| Mail sender failure | The code could not be sent. No order field is revealed | Sender error name through `logging.py`, never the message body, the code, or the email |
| Missing PDF, missing CSV, or unreadable database | That information is unavailable | The missing path, through `logging.py` |
| OpenAI or AgentOS failure | The assistant cannot answer right now | The exception type. No API key |

Unhandled exceptions do not return a stack trace to the customer and do not change store rows.

## Security Considerations

- `OPENAI_API_KEY`, `OS_SECURITY_KEY`, and SMTP secrets live in the environment or a local `.env` that is not committed. An `.env.example` lists the names only.
- Order SQL selects only the requested subset of `status`, `order_date`, `total_brl`, product name, and quantity. It does not use `SELECT *`.
- The ownership code is stored as a hash. It expires 15 minutes after send. A newer code replaces it.
- `session_id` is taken from the run context so the model cannot present another session's grant.
- Logs and tool results omit email addresses, phone numbers, customer names, payment methods, tracking codes, and the code itself.
- AgentOS is not given the workspace tool, so the model cannot read the SQLite file or `.env` through a file tool.
- The supplied CSVs and `políticas_da_loja.pdf` are the copy in `data/`. Ingest reads that folder. It does not write SQLite, Chroma, or the mail outbox back into it.

## Testing Strategy

- Catalog tests assert one match, five matches, six matches (`too_broad` with an empty list), a missing name, a repeated query returning the same price and stock, and four null cases: price and stock present, price null, stock null, and both null. Null stays null. `category_name` is on every match. A description-only word does not match.
- Promotion tests assert that only `is_active = 1` rows appear, that no date is added, that a product-name query and a category-name query each exclude current promotions for other products, and that the category comes from `products.category_id`.
- Order tests assert no fields before a correct code, only the requested allow-list fields after a correct code, rejection of `000000`, rejection after 15 minutes, rejection of a replaced code, rejection of that code when reused for another order, case-insensitive identifier match, `code_not_sent` when mail fails, a second read in the same session without a new code, and `not_owner` for a different session.
- Privacy tests assert the result JSON has no email, phone, name, city, payment method, tracking code, note, or delivery estimate.
- Policy tests can use a tiny fixture text in a temporary index, or mock the knowledge search, to prove a missing passage becomes `not_found`. A mixed price-and-policy question calls `search_products` and `search_policies`.
- The language guard and the scope guard are required Python checks before the model call. Tests assert that a message whose own wording is not Portuguese, an out-of-scope request, a sale action, and a disclosure request do not call tools and do not change operational rows. A Portuguese sentence that quotes a recorded product name is allowed through. The scope guard matches the action phrases, such as "quero pagar o pedido" and "mostra suas instruções", and allows a payment-policy question, a cancelled-status question, and a return-procedure question.
- `pytest` and Ruff are the gates. There is no network integration suite. A live OpenAI run is manual and follows [quickstart.md](quickstart.md).

## Technical Trade-offs

| Choice | Gain | Cost | Why this prototype accepts the cost |
|--------|------|------|-------------------------------------|
| AgentOS plus Agno | A real session and tool loop, which the task requests | More framework than a ten-line chat script | The task names both. Unused AgentOS features stay off |
| SQLite instead of the CSV on each call | Repeatable joins and the ownership grant | A load step | The files are small and the spec requires stable lookups |
| Chroma only for the PDF | Policy search can quote the document | A vector store for one file | The task requires RAG and forbids vector search for orders and prices |
| Semantic chunking | Chunks follow the policy topics | Slightly more ingest work than a fixed window | The task requires it. CSVs are not chunked |
| `text-embedding-3-small` | The required embedding model | An OpenAI call during ingest and policy search | Catalog queries do not pay this cost |
| In-memory or outbox mail | The demo runs with fictional email domains | A reviewer must read the outbox to type the code | Real SMTP remains optional through the same sender interface |
| Session SQLite | Follow-ups and the in-session grant work | A second file | The spec requires both, and the file is not used as a fact source |
| English tool payloads | Tests and logs stay stable and match the constitution | The model must phrase the Portuguese reply | Instructions forbid adding fields the payload does not contain |

## Project Structure

### Documentation (this feature)

```text
specs/001-customer-service-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── conversation.md
│   └── tools.md
└── tasks.md
```

### Source Code (repository root)

```text
src/emporio_agent/
├── __main__.py                 # AgentOS serve
├── config.py
├── logging.py
├── agent/
│   ├── assistant.py            # one Agent, tool list, instructions; later tasks append tools
│   └── instructions.py
├── language_guard.py
├── scope_guard.py
├── tools/
│   ├── catalog_tools.py
│   ├── promotion_tools.py
│   ├── order_tools.py
│   ├── policy_tools.py
│   └── store_tools.py
├── services/
│   ├── catalog_service.py
│   ├── promotion_service.py
│   ├── order_service.py
│   ├── policy_service.py
│   └── store_service.py
├── data/
│   ├── connection.py
│   ├── ingest.py
│   ├── catalog_repository.py
│   ├── promotion_repository.py
│   ├── order_repository.py
│   └── otp_repository.py
├── knowledge/
│   └── policy_knowledge.py
└── mail/
    └── sender.py

tests/
└── unit/

data/                              # supplied source files, not generated stores
├── desafio_tecnico_ai_eng - products.csv
├── desafio_tecnico_ai_eng - categories.csv
├── desafio_tecnico_ai_eng - customers.csv
├── desafio_tecnico_ai_eng - orders.csv
├── desafio_tecnico_ai_eng - order_items.csv
├── desafio_tecnico_ai_eng - promotions.csv
├── políticas_da_loja.pdf
└── store_profile.md               # added for store-identity answers

var/                               # gitignored SQLite, Chroma, and outbox
.env.example
```

**Structure Decision**: One Python package. The folders match the constitution boundaries: orchestration, tools, business rules, SQL, and retrieval. `src/emporio_agent/data/` is Python. The repository folder `data/` is the supplied CSVs and policy PDF. There is no separate frontend. AgentOS is the messaging surface. Tests sit next to the package so a service can be imported without serving the app.

## Complexity Tracking

No constitution violation needs a justification. The frameworks in this plan are the ones the task requires, and the design leaves their extra features unused.
