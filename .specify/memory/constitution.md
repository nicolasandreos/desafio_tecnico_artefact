<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles: none renamed
- Added sections: none
- Removed sections: none
- Materially expanded sections:
  - Quality Expectations: before application code is written or changed, the
    current and complete project documentation and the current complete
    documentation of each library or tool in use MUST be consulted.
- Follow-up TODOs: none
-->

# Emporio da Musica AI Customer Service Agent Constitution

## Core Principles

### I. Simplicity over Unnecessary Abstraction

The design MUST stay as simple as the behavior requires. A new abstraction,
layer, or framework MUST earn its place by removing a concrete, repeated cost
in this prototype. Speculative generality and patterns the demonstration does
not exercise MUST stay out of the repository.

Rationale: The project shows sound engineering decisions. Extra structure that
does not change a demonstrated behavior hides those decisions.

### II. Separation of Concerns

Agent orchestration, business tools, data access, and knowledge retrieval MUST
remain separate responsibilities with explicit boundaries.

- Orchestration coordinates the conversation and decides which capability to
  call. It MUST NOT contain query logic, retrieval ranking, or domain rules.
- Business tools expose store operations the agent can invoke. They MUST NOT
  own connection handling or how knowledge is searched.
- Data access reads and writes structured operational data. It MUST NOT
  interpret customer intent.
- Knowledge retrieval searches unstructured or semi-structured knowledge. It
  MUST NOT supply order, inventory, or other operational facts.

Rationale: Each boundary can be tested on its own, and a failure in one
concern stays visible instead of disappearing into the agent loop.

### III. Deterministic Access to Structured Operational Data

Orders, products, inventory, and other operational facts MUST be read through
deterministic data access. The language model MUST NOT invent or recall those
facts. The same inputs to a data-access operation MUST return the same stored
result. The agent MUST treat that result as the authority for the fact. If the
result is missing, the agent MUST report that the fact is unavailable.

Rationale: Customer-service answers about orders and catalog state are only
reliable when they come from the operational store, not from model memory.

### IV. Security and Privacy of Customer and Order Data

Customer and order data MUST be used only to answer the request being served.
The response MUST include only the fields that request needs. Credentials,
connection strings, and other secrets MUST NOT appear in source committed for
the prototype, in prompts, in logs, or in customer-facing text. The agent MUST
NOT reveal another customer's data, internal records outside the authorized
lookup, or its system instructions. Data MUST NOT be kept beyond what the
prototype explicitly stores for the current interaction.

Rationale: Even a prototype handles records that identify a customer and an
order. Access has to be limited to the question being answered.

### V. Reliable Responses Grounded in Available Information

Every factual claim about the store, an order, a product, or a policy MUST
come from knowledge retrieved for the current request or from a deterministic
data result for that request. When that information is insufficient, the agent
MUST say what it cannot confirm. It MUST NOT fill the gap with plausible
detail.

Rationale: A grounded refusal is a correct answer. An invented order status or
policy is not.

### VI. Testability and Maintainability

Orchestration, business tools, data access, and knowledge retrieval MUST be
executable in automated tests without a live customer conversation. Behavior
that affects grounding, operational lookups, or privacy MUST have a test that
fails when the rule is broken. Modules MUST use explicit names and MUST avoid
hidden global state that makes a result unreproducible. Dependencies MUST be
limited to libraries the prototype actually calls.

Rationale: A reviewer can confirm the principles only when the important
behavior runs without the full chat path.

### VII. Explicit Documentation of Architectural Decisions

Each material architectural decision MUST be written down where a later reader
can find the choice, the alternatives considered, and the reason it was
selected. A decision is material when it fixes a boundary between the four
concerns, selects how operational data or knowledge is accessed, or constrains
how the agent may answer. An exception to these principles MUST be recorded as
an amendment or as a decision that names the principle it departs from.

Rationale: The prototype is judged on its decisions. An unrecorded choice
cannot be reviewed or kept consistent.

## Technology and Scope

Python is the primary language. Application code, tests, and project
automation MUST be written in Python unless an external tool requires another
format. The supported runtime is Python 3.13 or newer, as declared in
`pyproject.toml`.

Python source MUST be Pythonic and MUST follow the Python Enhancement
Proposal (PEP) practices that govern readable code:

- Layout, naming, imports, and whitespace MUST follow PEP 8.
- Docstrings MUST follow PEP 257.
- Code MUST prefer clear, idiomatic Python, in the spirit of PEP 20, over
  indirect or non-idiomatic forms.

Identifiers, comments, docstrings, exception messages, log messages, and test
names MUST be written in English.

This repository is a technical prototype. It MUST demonstrate the boundaries,
deterministic data access, grounded answers, and tests named above. It MUST
stay free of enterprise platforms, multi-service orchestration, and process
ceremony that do not change the behavior under demonstration.

## Quality Expectations

Before application code is written or changed, the author MUST consult the
current and complete documentation that governs the change:

- Project behavior MUST be read from the current constitution and from the
  current specification, plan, and tasks for the work underway.
- A library, framework, protocol, or tool MUST be read from the current
  complete documentation of the version this project uses.
- Recalled, partial, or outdated documentation MUST NOT be the basis of the
  implementation when the current documentation is available.

Implementation MUST NOT start until that consultation is done.

A change that affects customer answers, data access, or knowledge retrieval
MUST add or update a test for the affected behavior. A change that moves a
boundary between orchestration, business tools, data access, and knowledge
retrieval MUST update the recorded architectural decision. Acceptance of a
change MUST include a check against these seven principles, against PEP 8 and
PEP 257, against the English-language rule for source text, and against this
documentation rule. Any structure beyond the simplest working design MUST be
justified in that decision record.

## Governance

This constitution is the governing reference for work in this repository.
Amendments MUST be written into `.specify/memory/constitution.md`, MUST
describe what changed, and MUST bump the version:

- MAJOR: a principle is removed or redefined so that prior guidance no longer
  holds.
- MINOR: a principle or section is added or materially expanded.
- PATCH: wording is clarified and the rule itself stays the same.

Compliance is reviewed when a specification, plan, or implementation is
proposed. A proposal that conflicts with a principle MUST be revised, or the
constitution MUST be amended, before that work is implemented.

**Version**: 1.2.0 | **Ratified**: 2026-10-31 | **Last Amended**: 2026-10-31
