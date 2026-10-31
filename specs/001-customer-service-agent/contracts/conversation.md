# Contract: Customer Conversation

The customer talks to one assistant through AgentOS. This contract is the messaging behavior the prototype must keep. AgentOS owns the HTTP route. This project does not add a second public API.

## Turn

**Request**

| Field | Rule |
|-------|------|
| `session_id` | Identifies the conversation. Omitted on the first turn; AgentOS then assigns one |
| `message` | The customer's text |

**Response**

| Field | Rule |
|-------|------|
| `session_id` | Same conversation for later turns |
| `reply` | Portuguese text |

The reply is one of three kinds, and the wording must make the kind obvious:

| Kind | When |
|------|------|
| Answer | A tool returned recorded facts, and the reply uses only those facts. An order answer includes only the allow-listed fields the customer asked about |
| Need a detail | A required field is missing, such as the product name, the order id, or the code |
| Cannot help | The question is out of scope, asks for a sale action, asks for hidden instructions or the whole catalog, is in another language, or the materials do not contain the fact |

The three refusals below stay distinct in the wording:

| Refusal | Example | What the reply does |
|---------|---------|---------------------|
| Out of scope | A recipe, or another store's price | Declines and offers help only with this store. Does not answer the request |
| Sale action | Place, change, cancel, or pay for an order | Says the assistant cannot carry out that action. Does not claim a record changed |
| Disclosure | Hidden instructions, ignore the rules, or the entire catalog | Refuses, invites a specific question, and does not reveal instructions or list the catalog |

A refused turn does not change stored rows. The pre-agent guards return these refusals before any tool runs.

## Language

Every `reply` is Portuguese. If the customer's own wording is in another language, `reply` says that the assistant only communicates in Portuguese and does not answer the request. A Portuguese sentence that quotes a recorded product name is still a Portuguese request.

Recorded names, prices, statuses, and policy sentences are quoted as stored. They are not translated.

## Session

Turns that share a `session_id` may use earlier turns. A follow-up such as "quanto custa?" refers to the product already established in that session.

A new `session_id` does not reuse the previous product, order, or ownership grant. The customer must identify the order again and pass a new code.

## What the reply must not contain

- A price, stock figure, order status, discount, or policy rule that the tools did not return for this turn.
- An email address, phone number, customer name, city, payment method, tracking code, delivery estimate, order note, or document.
- The ownership code.
- A claim that an order or a store record was changed.
- Hidden instructions or a dump of the catalog or of every order.

## Refusals

Out-of-scope questions, sale actions, and disclosure requests are three separate refusals, as in the table above. Each one receives a Portuguese refusal and an offer to help with store information, products, orders, promotions, and policies. The reply does not claim that a record changed, and the operational rows stay as they were.
