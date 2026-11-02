# Contract: Conversation

Feature 001 still defines what the customer may hear. This contract records only what feature 002 changes about how a turn is produced.

## Turn

1. The customer sends one text message in the current conversation.
2. Before the model answers, the policy collection is searched for that message. The passages are policy context, not operational facts.
3. The assistant replies in Portuguese. It uses an operational tool only for a product, order, promotion, or store-profile fact. It uses the retrieved passages only for a policy fact.
4. A follow-up in the same process and the same conversation may rely on the topic already established. A new conversation does not.

## Conduct the assistant applies

The reply itself, not a phrase list in front of the model, does all of the following:

- Answers in Portuguese. A message in another language receives a Portuguese refusal and no answer to that request. A Portuguese sentence that only quotes a recorded product name is still answered.
- Refuses a subject outside this store, such as a recipe or another store's price, and offers help with this store's information, products, orders, promotions, and policies.
- Refuses to place, change, cancel, or pay an order, and does not claim that a record changed.
- Refuses to reveal hidden instructions, to ignore the rules, or to list the whole catalog or every order.
- Still answers a return procedure from the policy document, a payment rule from the policy document, and a recorded status such as cancelled from the order table after the ownership check.

## Conduct the application applies

These hold even if the message tells the assistant to ignore them:

- No order field is returned before this conversation has a grant for that order.
- After the grant, only the requested allow-listed fields are returned.
- Email, full address, payment data, and documents are never returned.
- No tool changes a supplied table.

## Reply kinds

From the reply alone the customer can tell an answer, a request for one missing detail, and a cannot-help reply. An out-of-scope refusal, a sale-action refusal, and a disclosure refusal are distinguishable from one another.
