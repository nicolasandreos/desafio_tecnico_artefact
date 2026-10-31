# Research: Emporio da Musica Customer Service Agent

Decisions below close the technical choices for the prototype. Class and function names that the indexed Agno docs did not return on 2026-10-31 must be copied from the current Agno documentation before that code is written.

## Decision: One Agno agent, exposed by AgentOS

**Decision**: Build one Agno `Agent` and serve it with `AgentOS`. The agent uses an OpenAI chat model, custom Python tools, SQLite session storage, and recent-turn history in context.

**Rationale**: Current AgentOS docs show this shape: an `Agent` with `db=SqliteDb(...)`, `add_history_to_context=True`, then `AgentOS(agents=[...], db=SqliteDb(...))`, `get_app()`, and `serve`. That gives a messaging interface and a persistent session without a second orchestration framework. One agent matches the requested architecture and the constitution's limit on extra structure.

**Alternatives considered**: A hand-rolled chat loop was rejected because the task asks for AgentOS. A team of specialist agents was rejected because the task asks for one agent with tools, and a team would blur the boundary the constitution already draws between orchestration and business tools.

## Decision: Leave unused AgentOS features off

**Decision**: Do not enable AgentOS tracing, the scheduler, or the MCP server for this prototype. Set `OS_SECURITY_KEY` from the environment before the app is reachable beyond the local machine.

**Rationale**: Current docs describe those switches as optional production controls. The prototype does not demonstrate them. The same docs say an unsecured MCP endpoint accepts anonymous local calls, which this project does not need.

**Alternatives considered**: Turning every AgentOS flag on was rejected as ceremony that does not change the customer-facing behavior.

## Decision: OpenAI for chat and for embeddings

**Decision**: The chat provider is OpenAI. The model id comes from `OPENAI_MODEL`. Embeddings for the policy document use `text-embedding-3-small`. The API key comes from `OPENAI_API_KEY`.

**Rationale**: The task names OpenAI as the initial provider and fixes the embedding model. Current Agno examples address chat models as `openai:<model-id>` or `OpenAIResponses`. Keeping the chat model id in the environment avoids locking the prototype to a sample id from the docs (`gpt-5.5` and `gpt-5.2` both appear there).

**Alternatives considered**: A local model was rejected because the task names OpenAI. Hard-coding one chat model id was rejected because the docs already show more than one current id.

## Decision: Agno Knowledge, ChromaDB, and semantic chunking for the policy PDF only

**Decision**: Ingest `data/políticas_da_loja.pdf` with Agno Knowledge, store vectors in a local ChromaDB collection, and chunk that PDF with semantic chunking. No CSV row is embedded.

**Rationale**: The task requires RAG, ChromaDB, and semantic chunking for store policies. The constitution requires operational facts to come from deterministic queries. A docs lookup for the Knowledge plus Chroma plus semantic-chunking constructor did not return a page on 2026-10-31, so the implementation must read the current Agno Knowledge page before writing that module. The architectural choice does not depend on that class name.

**Alternatives considered**: Fixed-size chunking was rejected because the task asks for semantic chunking. Embedding the catalog was rejected because price and stock would then depend on similarity instead of the stored row.

## Decision: SQLite for operational records, loaded by Pandas

**Decision**: A one-shot ingest reads the six CSVs in the repository folder `data/` with Pandas and loads normalized tables into one SQLite file. The policy source in that same folder is `políticas_da_loja.pdf`. `DATA_DIR` may point elsewhere, and it defaults to `data/`. Query functions use parameterized SQL and an explicit column list. Generated databases stay in `var/`.

**Rationale**: The files are small (about 64 products, 20 orders, 25 promotions, 50 customers, 10 categories, and the order-item rows). SQLite gives the same result for the same query, which is the spec rule for repeated lookups. Pandas is only the loader, not the query path.

**Alternatives considered**: Querying CSV files on every question was rejected because joins and the ownership check are clearer in SQL. PostgreSQL was rejected as unused infrastructure for this data size.

## Decision: Promotions are current when `is_active` is 1

**Decision**: The promotion CSV has no start or end date. A promotion is current only when `is_active` is 1. The assistant does not invent a validity period.

**Rationale**: The supplied file has no start or end date. `is_active` is the recorded current flag, not a validity date. Inactive rows stay out of the answer so the assistant does not present an old offer as current. The active rows in the sample are promotion ids 12, 14, 19, and 24. A query matches the product name or the category name reached through `products.category_id`.

**Alternatives considered**: Treating every row as current was rejected because the file already marks most rows inactive. Guessing calendar seasons from the description text was rejected because that invents a date rule.

## Decision: Availability is the stored stock and product status

**Decision**: A product answer reports `name`, `category_name`, `price_brl`, `stock_quantity`, and `status` (`active`, `discontinued`, or `coming_soon`). Search uses the product name only. A missing price, stock, or category name is null and is described as not recorded. The answer does not invent a restock or delivery date.

**Rationale**: Those are the catalog columns the customer reply needs. The spec defines availability as the recorded value and forbids an implied restock date, a zero substituted for null, and a match on description or specs.

**Alternatives considered**: Collapsing status and stock into a single "available" boolean was rejected because it hides a recorded distinction, such as `coming_soon` with a future-facing status or `active` with zero stock.

## Decision: Order facts use an allow-list after an email code

**Decision**: `request_order_code` loads the email by joining `orders.customer_id` to `customers.email` and sends a 6-digit code. `confirm_order_code` accepts the code only when it matches the latest unexpired code for that order. `get_order_details` then returns only the requested subset of status, `order_date`, item names and quantities, and `total_brl`.

**Rationale**: The spec requires the order id plus a 6-digit code sent to the recorded email, valid for 15 minutes, before any order fact is spoken. The allowed fields are status, date, items, and amounts, and one reply includes only the subset the customer asked about. The order file also contains `payment_method`, `tracking_code`, `estimated_delivery`, and `notes`. Those stay out of the tool result. Customer name, phone, email, and city stay out of the tool result. The email is used only to address the code.

**Alternatives considered**: Treating the order id as proof of ownership was rejected by the clarified spec. Returning the tracking code with the status was rejected because the allowed field list does not include it.

## Decision: OTP delivery is a swappable sender

**Decision**: The order service calls a mail sender interface. Tests use an in-memory sender. If SMTP settings are present, a sender can deliver the message. Otherwise the prototype writes the message to a local outbox that is not shown in the chat. The code stored in SQLite is a hash, not the raw code. A new code replaces the previous hash.

**Rationale**: The sample emails use fictional domains, so a take-home demo cannot depend on a real inbox. The spec still requires a real send step and a check that the code is correct, valid, and unexpired. The chat must not display the code or the email address.

**Alternatives considered**: Printing the code in the assistant reply was rejected because it skips the ownership check. A third-party email vendor was rejected as extra infrastructure.

## Decision: Session persistence is justified and limited

**Decision**: AgentOS `SqliteDb` stores the conversation so a follow-up can resolve "how much is it?" and so an accepted order code remains valid for later turns in that same session. The grant is stored as `session_id` plus `order_id` in the operational database. A new session id requires a new code. The session store is not a source of prices, stock, or order status.

**Rationale**: The spec requires conversational context and says a successful code unlocks that order for the rest of the current conversation only. Follow-up turns need a stored transcript. Keeping the grant beside the session id stops the model from claiming verification it did not pass.

**Alternatives considered**: A stateless agent was rejected because follow-up scenarios would fail. A long-term customer profile was rejected because the spec ends the grant when the conversation ends.

## Decision: Business rules live behind tools

**Decision**: Tools validate inputs and call services. Services apply matching, privacy, and the code check. Repositories run SQL. The agent file only wires the model, the tools, the session database, and the instructions.

**Rationale**: The constitution separates orchestration, business tools, data access, and knowledge retrieval. Tests can call services without a live model.

**Alternatives considered**: SQL inside tool closures defined in the agent module was rejected because the orchestration file would then own query logic.

## Decision: Customer replies are Portuguese; source text is English

**Decision**: Tool payloads use English keys and stable error codes. Agent instructions tell the model to answer only in Portuguese and to speak only fields the tool returned. Source code, docstrings, logs, and tests stay in English.

**Rationale**: The spec limits customer communication to Portuguese. The constitution requires English source text.

**Alternatives considered**: Portuguese identifiers were rejected by the constitution. Letting the model translate recorded names was rejected by the clarification that recorded facts are quoted as written.
