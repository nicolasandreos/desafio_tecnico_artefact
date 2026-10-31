# Contract: Agent Tools

The agent calls these functions. It does not receive a database handle. Each function validates its inputs and returns a structured result. Customer-facing Portuguese is composed from that result. It is not stored in the database.

The `session_id` used by order tools comes from the agent run context. A model argument named `session_id` is ignored.

Shared error codes:

| Code | Meaning |
|------|---------|
| `invalid_input` | The argument is empty, the wrong type, or too long |
| `not_found` | Nothing in the store matched |
| `too_broad` | More than five products matched |
| `unavailable` | The source file or database could not be read |
| `not_owner` | The order is not verified for this session |
| `code_rejected` | The code is wrong, expired, or no longer the latest |
| `code_not_sent` | The code could not be delivered |

## search_products

**Input**: `query` string, required, trimmed, at most 200 characters.

**Success**: `matches`, a list of 1 to 5 objects. Each object has these keys: `name`, `category_name`, `price_brl`, `stock_quantity`, and `status`. `price_brl`, `stock_quantity`, and `category_name` are JSON null when that value is not recorded. The key is still present. Null is not replaced with zero or an estimate. Search compares the product name only.

**Errors**: `invalid_input`, `not_found` (no name match, including an empty loaded table), `too_broad`, `unavailable` (missing file or unreadable database).

`too_broad` includes the match count and no product rows.

## search_promotions

**Input**: optional `query` string, trimmed, at most 200 characters. An empty query asks for every current promotion.

**Success**: `promotions`, each with `product_name`, `category_name`, `discount_percent`, and `description`. Only rows with `is_active` 1 are eligible. `is_active` is not a date. An empty query returns every current promotion. A non-empty query keeps a current promotion only when the query text appears, case-insensitively, in that product's name or in its category name. Promotions for products that do not match are excluded.

**Errors**: `invalid_input`, `not_found` (no current promotion matches, including an empty loaded table), `unavailable` (missing file or unreadable database).

The result does not include a computed sale price, an inactive promotion, or an invented start or end date.

## get_store_context

**Input**: none.

**Success**: `facts`, the text of the supplied store profile. The profile states only facts present in the supplied materials.

**Errors**: `unavailable` when no profile was supplied.

This tool does not search the policy index and does not answer product or order questions.

## search_policies

**Input**: `question` string, required, trimmed, at most 500 characters.

**Success**: `passages`, the retrieved policy chunks, each with `text` and `source`.

**Errors**: `invalid_input`, `not_found` when no passage is relevant, `unavailable` when the index is missing.

Passages are not a source of price, stock, order status, or discount percent.

## request_order_code

**Input**: `order_id` string, required. Compared after trim, case-insensitively.

**Success**: `code_sent` true. The result has no email, no code, and no order field.

**Errors**:

| Code | When |
|------|------|
| `invalid_input` | Missing or malformed id |
| `not_found` | No order has that id |
| `ambiguous_order` | More than one order has that id |
| `email_missing` | The matching order has no email |
| `code_not_sent` | The sender failed |
| `unavailable` | The database could not be read |

Sending a new code replaces the previous one for that order.

## confirm_order_code

**Input**: `order_id` string and `code` string. `code` must be exactly six digits.

**Success**: `verified` true for this `session_id` and `order_id`. No order fields are included.

**Errors**: `invalid_input`, `not_found`, `ambiguous_order`, `code_rejected`, `unavailable`.

A rejected confirmation does not create a grant.

## get_order_details

**Input**: `order_id` string, and `fields`, a non-empty list. Each entry is one of `status`, `order_date`, `items`, or `total_brl`. Any other name, including email or payment fields, is `invalid_input`.

**Success**, only when a grant exists for this `session_id` and `order_id`: the result contains only the requested keys.

| Field | Source |
|-------|--------|
| `status` | `orders.status` |
| `order_date` | `orders.order_date` |
| `items` | product `name` and `quantity` |
| `total_brl` | `orders.total_brl` |

A requested value that is not stored is JSON null. It is not filled in. Keys the customer did not ask for are omitted, even when they are on this allow-list.

**Errors**: `invalid_input`, `not_found`, `ambiguous_order`, `not_owner`, `unavailable`.

The result never includes email, phone, customer name, city, `payment_method`, `tracking_code`, `estimated_delivery`, `notes`, or another order.
