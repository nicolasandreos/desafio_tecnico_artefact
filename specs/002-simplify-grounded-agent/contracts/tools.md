# Contract: Operational Tools

The agent may call the functions below. Policy is not one of them. Policy retrieval is [knowledge.md](knowledge.md).

Each function checks its arguments and returns a structured result. The Portuguese reply is composed from that result. No function writes a CSV or changes an order.

The `session_id` used by order tools comes from the agent run context. A model argument named `session_id` is ignored.

Shared error codes:

| Code | Meaning |
|------|---------|
| `invalid_input` | The argument is empty, the wrong type, or too long |
| `not_found` | The loaded table has no matching row, including zero rows |
| `too_broad` | More than five products matched |
| `unavailable` | A required CSV could not be read |
| `not_owner` | This conversation has no grant for that order |
| `code_rejected` | The code is wrong, expired, or no longer the latest |
| `code_not_sent` | The code could not be delivered |
| `ambiguous_order` | More than one order has that identifier |
| `email_missing` | The single matching order has no email |

## search_products

**Input**: `query` string, required, trimmed, at most 200 characters.

**Success**: `matches`, a list of 1 to 5 objects. Each object has `name`, `category_name`, `price_brl`, `stock_quantity`, and `status`. `price_brl`, `stock_quantity`, and `category_name` are null when unrecorded. The key is still present. Null is not replaced with zero. Search compares the product name only.

**Errors**: `invalid_input`, `not_found`, `too_broad`, `unavailable`.

`too_broad` includes the match count and no product rows.

## search_promotions

**Input**: optional `query` string, trimmed, at most 200 characters. An empty query asks for every current promotion.

**Success**: `promotions`, each with `product_name`, `category_name`, `discount_percent`, and `description`. Only rows with `is_active` 1 are eligible. `is_active` is not a date. A non-empty query keeps a current promotion only when the query text appears, case-insensitively, in that product's name or in its category name.

**Errors**: `invalid_input`, `not_found`, `unavailable`.

The result does not include a computed sale price, an inactive promotion, or an invented start or end date.

## get_store_context

**Input**: none.

**Success**: `facts`, the text of the supplied store profile.

**Errors**: `unavailable` when no profile was supplied.

This tool does not search the policy collection and does not answer a product or order question.

## request_order_code

**Input**: `order_id` string, required. Compared after trim, case-insensitively.

**Success**: `code_sent` true. The result has no email, no code, and no order field.

**Errors**: `invalid_input`, `not_found`, `ambiguous_order`, `email_missing`, `code_not_sent`, `unavailable`.

Sending a new code replaces the previous one for that order. The order row is not modified.

## confirm_order_code

**Input**: `order_id` string and `code` string. `code` must be exactly six digits.

**Success**: `verified` true for this conversation and this order. No order fields are included.

**Errors**: `invalid_input`, `not_found`, `ambiguous_order`, `code_rejected`, `unavailable`.

A rejected confirmation does not create a grant.

## get_order_details

**Input**: `order_id` string, and `fields`, a non-empty list. Each entry is one of `status`, `order_date`, `items`, or `total_brl`. Any other name is `invalid_input`.

**Success**, only when a grant exists for this conversation and this order: the result contains only the requested keys.

| Field | Source |
|-------|--------|
| `status` | `orders.status` |
| `order_date` | `orders.order_date` |
| `items` | product `name` and `quantity` |
| `total_brl` | `orders.total_brl` |

A requested value that is not stored is null. Keys the customer did not ask for are omitted.

**Errors**: `invalid_input`, `not_found`, `ambiguous_order`, `not_owner`, `unavailable`.

The result never includes email, phone, customer name, city, `payment_method`, `tracking_code`, `estimated_delivery`, `notes`, or another order.

## Absent on purpose

There is no `search_policies` tool. There is no tool that creates, updates, cancels, or pays an order.
