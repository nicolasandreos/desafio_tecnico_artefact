# Data Model: Emporio da Musica Customer Service Agent

Operational rows come from the CSVs in the repository folder `data/`. The loader is Pandas. The query store is SQLite. Vector storage holds policy chunks only. `DATA_DIR` overrides `data/` when it is set.

Source files:

| File | Table |
|------|--------|
| `desafio_tecnico_ai_eng - products.csv` | `products` |
| `desafio_tecnico_ai_eng - categories.csv` | `categories` |
| `desafio_tecnico_ai_eng - customers.csv` | `customers` |
| `desafio_tecnico_ai_eng - orders.csv` | `orders` |
| `desafio_tecnico_ai_eng - order_items.csv` | `order_items` |
| `desafio_tecnico_ai_eng - promotions.csv` | `promotions` |
| `políticas_da_loja.pdf` | Chroma collection `store_policies` |
| `store_profile.md` | Read in full by `get_store_context`. Not a CSV and not embedded |

## products

| Field | Rule |
|-------|------|
| `product_id` | Primary key, integer |
| `name` | Required. Search compares a normalized form of this text only |
| `category_id` | Foreign key to `categories`. The reply field is `category_name` from `categories.name` |
| `price_brl` | Decimal as recorded, or null when the source value is missing. Never recalculated and never replaced with zero |
| `stock_quantity` | Integer as recorded, or null when the source value is missing. This is the availability quantity. Never replaced with zero |
| `status` | `active`, `discontinued`, or `coming_soon` |
| `description` | Stored. Not used in search and not returned to the customer |
| `specs` | Stored JSON text. Not used in search and not returned to the customer |
| `created_at` | Not used in customer answers |

Validation: a search matches when the customer's words appear, case-insensitively, in the product name. Description and specs do not match. Zero matches return `not_found`, including when the loaded `products` table has zero rows. One to five matches return each product's `name`, `category_name`, `price_brl`, `stock_quantity`, and `status`. A missing `price_brl`, `stock_quantity`, or `category_name` is JSON null and the key stays present. More than five matches return `too_broad` and no product rows. A missing catalog file or an unreadable database returns `unavailable`.

## categories

| Field | Rule |
|-------|------|
| `category_id` | Primary key |
| `name` | Returned as `category_name` on a product match. Also used to match a promotion question to the products in that category |
| `description` | Not required for the price answer |

## customers

| Field | Rule |
|-------|------|
| `customer_id` | Primary key |
| `name` | Never returned by a tool |
| `phone` | Never returned by a tool |
| `email` | Used only as the destination of the ownership code. Never returned |
| `city` | Never returned by a tool |

A name-only request does not query this table for a customer list.

## orders

| Field | Rule |
|-------|------|
| `order_id` | Primary key in this sample. Lookup trims spaces and compares case-insensitively |
| `customer_id` | Foreign key to `customers`. Used to find the email |
| `order_date` | Allowed after a successful code |
| `status` | Allowed after a successful code. Sample values: `pending`, `confirmed`, `shipped`, `delivered`, `cancelled` |
| `total_brl` | Allowed after a successful code. This is the order amount |
| `payment_method` | Stored and never returned |
| `tracking_code` | Stored and never returned |
| `estimated_delivery` | Stored and never returned |
| `notes` | Stored and never returned |

If the identifier matches more than one row, the lookup stops. No code is sent and no field is returned.

There is no separate address column. A request for a full address is refused because the materials do not provide one to the customer tool.

After a grant, `get_order_details` accepts `fields`, a non-empty subset of `status`, `order_date`, `items`, and `total_brl`. The result contains only those requested keys. A missing stored value is JSON null. A name outside that subset is `invalid_input` and returns no order field.

## order_items

| Field | Rule |
|-------|------|
| `order_id` | Foreign key to `orders` |
| `product_id` | Foreign key to `products` |
| `quantity` | Integer as recorded |

An order can have more than one item (sample orders 15 and 20). After a successful code, an item answer is the product `name` plus `quantity`. The line has no stored price. The service does not multiply catalog price by quantity and present that product as the amount paid. The order amount remains `orders.total_brl`.

## promotions

| Field | Rule |
|-------|------|
| `promotion_id` | Primary key |
| `product_id` | Foreign key to `products` |
| `discount_percent` | Integer as recorded. Not applied to compute a new price |
| `description` | Recorded label, such as `Black Friday` |
| `is_active` | `1` means current. `0` means not current |

The file has no validity dates. `is_active` is the current flag, not a date. Answers include promotions with `is_active` 1 and their recorded description and percent. They do not add a start or end date. Promotions with `is_active` 0 are omitted.

A promotion belongs to a product, and that product belongs to a category through `products.category_id`. An empty query returns every current promotion. A query matches when its text appears, case-insensitively, in the product name or in the category name. The result includes only current promotions for products that match, each with `product_name`, `category_name`, `discount_percent`, and `description`. A current promotion for a product that does not match is excluded. Zero matches return `not_found`. A missing file or an unreadable database returns `unavailable`.

## ownership_codes

Created by the app, not loaded from CSV.

| Field | Rule |
|-------|------|
| `order_id` | The single order the code belongs to |
| `code_hash` | Hash of the 6-digit code. The raw code is not stored |
| `sent_at` | Timestamp |
| `expires_at` | `sent_at` plus 15 minutes |
| `replaced` | True when a newer code is sent for the same order |

The latest code for an order is the only acceptable one. A code is accepted only when the submitted value hashes to `code_hash`, `replaced` is false, and the current time is before `expires_at`.

## order_grants

Created by the app after a code is accepted.

| Field | Rule |
|-------|------|
| `session_id` | AgentOS session id, taken from the run context, not from model input |
| `order_id` | The verified order |
| `granted_at` | Timestamp |

A grant authorizes later turns in that session to read the allow-listed fields of that order. It does not authorize another order, another session, or a hidden column. It is not a customer account.

## Policy chunks

Chroma collection `store_policies`.

| Field | Rule |
|-------|------|
| `text` | One semantic chunk of the policy PDF |
| `source` | `políticas_da_loja.pdf` |
| `embedding` | `text-embedding-3-small` |

Chunks are not a source of price, stock, order status, or promotion percent.

## Conversation

Stored by AgentOS in its own SQLite file, separate from the operational database.

| Field | Rule |
|-------|------|
| `session_id` | Identifies the current conversation |
| `messages` | Prior turns used as context |

A new `session_id` is a new conversation. Product and order references from the old transcript are not assumed, and order grants from the old session are not reused.

## Relationships

- One category has many products.
- One customer has many orders.
- One order has many order items.
- One product has many order items and many promotions.
- One order has at most one active ownership code.
- One session grant points at one order.

## State of an ownership code

1. **Absent**. No code has been sent. Order fields stay hidden.
2. **Sent**. The latest code is unexpired. Order fields stay hidden until confirmation.
3. **Expired or replaced**. Confirmation fails. Order fields stay hidden.
4. **Accepted**. A grant exists for this session and order. Allow-listed fields may be read until the session changes.
