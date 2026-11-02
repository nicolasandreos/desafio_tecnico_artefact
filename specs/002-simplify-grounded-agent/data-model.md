# Data Model: Simplify Grounded Answers

Operational rows are the CSV files in `data/`. Pandas loads them on each read. They are not copied into a database. `DATA_DIR` overrides `data/` when set. Feature 001 names the customer-facing fields. This model says where those fields live after the correction.

| File | Frame |
|------|--------|
| `desafio_tecnico_ai_eng - products.csv` | products |
| `desafio_tecnico_ai_eng - categories.csv` | categories |
| `desafio_tecnico_ai_eng - customers.csv` | customers |
| `desafio_tecnico_ai_eng - orders.csv` | orders |
| `desafio_tecnico_ai_eng - order_items.csv` | order items |
| `desafio_tecnico_ai_eng - promotions.csv` | promotions |
| `políticas_da_loja.pdf` | Chroma collection `store_policies` |
| `store_profile.md` | Full text for `get_store_context`. Not a CSV and not embedded |

A missing file means that information is unavailable. A present file with no matching row, including zero rows, means nothing matched. Those meanings stay distinct. They are not required literal names in every return value. A service may keep its existing typed result when the two outcomes remain distinguishable.

## products

| Field | Rule |
|-------|------|
| `product_id` | Row identity. Not required in the reply |
| `name` | Required for a match. Search compares a case-insensitive form of this text only |
| `category_id` | Joined to `categories.category_id`. The reply field is `category_name` |
| `price_brl` | As recorded, or null when missing. Never zero and never recalculated |
| `stock_quantity` | Availability quantity as recorded, or null when missing. Never zero |
| `status` | `active`, `discontinued`, or `coming_soon` when present |
| `description` | Not search text and not returned |
| `specs` | Not search text and not returned |
| `created_at` | Not returned |

Validation: one to five name matches return `name`, `category_name`, `price_brl`, `stock_quantity`, and `status`. A missing `price_brl`, `stock_quantity`, or `category_name` is null and the key stays. More than five matches return `too_broad`, the match count, and no product rows.

## categories

| Field | Rule |
|-------|------|
| `category_id` | Join key |
| `name` | Returned as `category_name`. Also matches a promotion question |
| `description` | Not required for a price answer |

## customers

| Field | Rule |
|-------|------|
| `customer_id` | Join key from `orders.customer_id` |
| `name` | Never returned |
| `phone` | Never returned |
| `email` | Destination of the ownership code only. Never returned |
| `city` | Never returned |

A person's name does not list this frame.

## orders

| Field | Rule |
|-------|------|
| `order_id` | Lookup trims spaces and ignores letter case |
| `customer_id` | Used only to find the email |
| `order_date` | Allowed after a grant, and only if requested |
| `status` | Allowed after a grant, and only if requested. A recorded `cancelled` value is a fact, not a request to cancel |
| `total_brl` | Allowed after a grant, and only if requested |
| `payment_method` | Never returned |
| `tracking_code` | Never returned |
| `estimated_delivery` | Never returned |
| `notes` | Never returned |

More than one row for the same identifier stops the lookup. No code is sent and no field is returned. There is no address column. A request for a full address returns nothing.

`fields` must be a non-empty subset of `status`, `order_date`, `items`, and `total_brl`. Any other name, including `email` or `payment_method`, is `invalid_input` and returns no order field. A missing stored value for a requested key is null.

## order items

| Field | Rule |
|-------|------|
| `order_id` | Join to orders |
| `product_id` | Join to products |
| `quantity` | As recorded |

After a grant, an item is the product `name` plus `quantity`. The line has no price. The service does not multiply catalog price by quantity. The amount is `orders.total_brl`.

## promotions

| Field | Rule |
|-------|------|
| `promotion_id` | Row identity |
| `product_id` | Join to products |
| `discount_percent` | As recorded. Not applied to a price |
| `description` | As recorded |
| `is_active` | `1` is current. `0` is omitted. Not a date |

The file has no start or end date. An empty query returns every current promotion. A query matches when its text appears, case-insensitively, in the product name or the category name. Each result has `product_name`, `category_name`, `discount_percent`, and `description`. A current promotion for a product that does not match is excluded.

## Ownership code

Created by the application. Not a CSV row.

| Field | Rule |
|-------|------|
| `order_id` | The single order the code belongs to |
| `code_hash` | SHA-256 of the 6-digit code. The raw code is not stored |
| `sent_at` | Time the code was sent |
| `expires_at` | `sent_at` plus 15 minutes |
| `replaced` | True after a newer code is sent for that order |

The latest code is the only acceptable one. Acceptance requires the submitted value to hash to `code_hash`, `replaced` false, and the current time before `expires_at`. Feature 001 rejects a wrong, expired, or replaced code and does not reveal the order. It sets no attempt limit, lockout, or CAPTCHA. An invalid attempt does not create a grant. This feature adds no attempt counter and no lockout.

State:

1. **Absent**. No code sent. Order fields stay hidden.
2. **Sent**. Latest code is unexpired. Order fields stay hidden until confirmation.
3. **Expired or replaced**. Confirmation fails. Order fields stay hidden.
4. **Accepted**. A grant exists for that order and that session. Later turns may read any subset of the allow-listed fields, not only the first field that was asked.

## Ownership grant

| Field | Rule |
|-------|------|
| `session_id` | From the agent run context. A model-supplied session id is ignored |
| `order_id` | The verified order |
| `granted_at` | Time of acceptance |

After confirmation, the grant allows any subset of the allow-listed fields for that same order and that same session. It is not limited to the first field consulted. It does not authorize another order, another session, or a field outside the allow-list. It is not a customer account. It dies with the process.

## Policy passage

Chroma collection `store_policies`. Not a tool result schema the model fills in.

| Field | Rule |
|-------|------|
| `text` | One semantic chunk of the policy PDF |
| `source` | `políticas_da_loja.pdf` |
| embedding | `text-embedding-3-small` |
| retrieval | Vector similarity. At most 4 passages |

A passage is not a price, a stock quantity, an order status, or a discount. Passages that do not state the asked rule are not the answer.

## Conversation

Agno `InMemoryDb` for the current process.

| Field | Rule |
|-------|------|
| `session_id` | Identifies the conversation |
| messages | Prior turns used as context |

A new `session_id`, or a new process, does not reuse a product, an order, or a grant.

## Relationships

- One category has many products.
- One customer has many orders.
- One order has many items.
- One product has many items and many promotions.
- One order has at most one active ownership code.
- One grant points at one order in one session.
