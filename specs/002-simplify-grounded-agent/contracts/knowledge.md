# Contract: Policy Knowledge

Policy questions are answered from the Agno knowledge base. They are not answered by an operational tool.

## Index

| Step | Contract |
|------|----------|
| Source | `políticas_da_loja.pdf` in the data folder. A missing file fails with that file name |
| Read | Agno `PDFReader` with `split_on_pages=False` |
| Chunks | `SemanticChunking` using the same embedder as the store |
| Embeddings | `text-embedding-3-small` |
| Store | Chroma collection `store_policies`, persistent, vector similarity only |
| Rebuild | Only when the collection is missing or its `index_complete` mark is absent or differs from the current PDF. A chunk hash alone is not complete. A failed rebuild leaves retrieval unavailable |
| Excluded | Products, orders, customers, promotions, and the store profile are not embedded |

## Retrieval

The agent is constructed with the policy `Knowledge` object, `add_knowledge_to_context=True`, and `search_knowledge=False`.

On every user message the knowledge base is searched while the user message is built, before the model answers, and at most 4 passages are attached. There is no `search_knowledge_base` tool. `update_knowledge` is false, so the model cannot write the collection.

## What a passage may support

A policy reply may state only a rule that a retrieved passage supports. If no passage supports the question, the reply says the store policies do not provide that answer. If the collection cannot be searched, the reply says policy information is unavailable.

A passage is not a price, a stock quantity, an order status, or a discount. Those facts stay on the operational tools in [tools.md](tools.md).

## What is not this contract

- A Python function named `search_policies`
- A phrase list that decides whether the message is about policy
- An answer from model memory when retrieval did not run
