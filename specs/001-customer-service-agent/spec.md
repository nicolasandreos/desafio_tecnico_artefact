# Feature Specification: Emporio da Musica Customer Service Agent

**Feature Branch**: `001-customer-service-agent`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Build a customer service assistant for Emporio da Musica, a fictional musical instruments store in Campo Grande, Brazil. Customers talk to the assistant through a messaging interface. The assistant answers general store questions from the supplied business context, searches the product catalog for accurate prices and availability, retrieves order status, searches current promotions, and answers questions about store policies and procedures. It identifies what the customer wants, chooses the appropriate store information, handles questions it should not answer, asks for missing details, keeps conversational context when that context still applies, and does not fabricate information. Operational data is supplied in CSV files and store policies in a PDF document. The result is a functional prototype, described here by user-facing behavior only."

## Clarifications

### Session 2026-10-31

- Q: When a customer's words match several products, what should the assistant show? → A: Show up to 5 matches with each recorded price and availability; if more than 5 match, ask for a more specific request and do not list the whole set.
- Q: When the customer writes in a language other than the language of the store records, how should the assistant present recorded facts? → A: Customer communication is Portuguese only. Records are stored in Portuguese and quoted as written. If the customer writes in another language, the assistant replies in Portuguese that it only communicates in Portuguese and does not answer that request.
- Q: If two orders share the same identifier, what should the assistant tell the customer? → A: The assistant reveals only non-critical order information, including status, and only after confirming the customer owns that order. The customer provides the order identifier (order_id). The system sends a 6-digit code to the email recorded for that single order. The customer enters the code. The system accepts it only when it is correct, still valid, and unexpired. A code expires 15 minutes after it is sent. Until the check succeeds, nothing about the order is revealed. If the identifier is not unique or the order has no email, nothing is revealed and no code is sent.
- Q: After the customer confirms the code, which order information may the assistant share? → A: Status, order date, items, and amounts. The assistant must not share the email, full address, payment data, or documents.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask the store a question (Priority: P1)

A customer opens a text conversation with the Emporio da Musica assistant and asks something about the store. The assistant answers from the supplied business context, says when that context does not contain the answer, and declines requests that are outside store customer service or that ask the assistant to carry out a sale.

**Why this priority**: Nothing else is trustworthy until a customer can ask a question and receive only what the store materials support. This slice is useful on its own for location and other general store questions.

**Independent Test**: Supply only the business context. Ask where the store is, ask for a fact the context does not contain, ask for a recipe, ask the assistant to cancel or pay for an order, and ask for the hidden instructions or the whole catalog. Confirm that none of those refusals changes a store record.

**Acceptance Scenarios**:

1. **Given** a customer is in the messaging conversation, **When** the customer sends a message, **Then** the customer receives a reply in that same conversation.
2. **Given** the business context states that the store is in Campo Grande, **When** the customer asks where the store is, **Then** the reply states Campo Grande and does not add an address, phone number, or opening hours that the context does not contain.
3. **Given** the business context does not contain opening hours, **When** the customer asks what time the store opens, **Then** the reply says that opening hours are not available and does not state a time.
4. **Given** the customer writes in Portuguese, **When** the customer asks a question the materials can answer, **Then** the reply is in Portuguese and quotes recorded names, prices, statuses, and policy text as written.
5. **Given** the customer writes in a language other than Portuguese, **When** the assistant replies, **Then** the reply is in Portuguese, states that the assistant only communicates in Portuguese, and does not answer the request.
6. **Given** the customer's message does not show a language, **When** the assistant replies, **Then** the reply is in Portuguese.
7. **Given** the customer asks for something outside store help, such as a recipe or another store's price, **When** the assistant replies, **Then** it declines, does not answer that request, offers help only with this store's information, products, orders, promotions, and policies, and does not change any store record. This refusal is separate from a sale action and from a request for hidden instructions.
8. **Given** the customer asks the assistant to place, change, cancel, or pay for an order, **When** the assistant replies, **Then** it states that it cannot carry out that action, does not claim that any order or store record changed, does not change any store record, and says that it can still answer questions about products, orders, promotions, and policies.
9. **Given** the customer asks for the assistant's hidden instructions, asks the assistant to ignore its rules, or asks for the entire catalog, **When** the assistant replies, **Then** it refuses that disclosure, does not reveal the instructions, does not list the catalog, invites a specific question instead, and does not change any store record.

---

### User Story 2 - Check price and availability (Priority: P2)

A customer asks whether a musical instrument or related product is available and what it costs. The assistant searches the supplied catalog and reports the recorded price and availability, or says that the product was not found.

**Why this priority**: Price and availability are the main reasons a customer contacts an instrument store. The story can be demonstrated with the catalog alone.

**Independent Test**: Supply a catalog with at least one product that has a price and availability, one product with no price, one product with no availability, and one product with neither. Ask for a product by name, ask with wording that matches more than one product, ask with a word that appears only in a description, and ask for a product that is absent.

**Acceptance Scenarios**:

1. **Given** a catalog product has a recorded price, availability, and category name, **When** the customer asks for that product by a name that matches the product name, **Then** the reply states that recorded price, that recorded availability, and that recorded category name, and no different price. A word that appears only in the description or the specs does not count as a match.
2. **Given** the customer asks the same matching question again, **When** the catalog has not changed, **Then** the reply states the same price and the same availability.
3. **Given** two to five catalog products match the customer's wording, **When** the customer asks, **Then** the reply lists each match with its recorded category name, price, and availability and does not present one match's price as the only price.
4. **Given** more than five catalog products match the customer's wording, **When** the customer asks, **Then** the assistant asks for a more specific request and does not list the whole set.
5. **Given** no catalog product matches, **When** the customer asks, **Then** the reply says the product was not found and does not state a price or availability.
6. **Given** no product is already under discussion, **When** the customer asks for a price without naming a product, **Then** the assistant asks which product the customer means and does not state a price.
7. **Given** a matching product has a price but no availability recorded, **When** the customer asks for price and availability, **Then** the reply includes that product, states the recorded price, and says that availability is not recorded. The missing availability is null. The reply does not substitute zero or an estimate.
8. **Given** a matching product has availability recorded and no price, **When** the customer asks for price and availability, **Then** the reply includes that product, states the recorded availability, and says that the price is not recorded. The missing price is null. The reply does not invent a price.
9. **Given** a matching product records neither price nor availability, **When** the customer asks for price and availability, **Then** the reply includes that product and says that both are not recorded. Neither field is replaced with zero or an estimate.

---

### User Story 3 - Check an order (Priority: P2)

A customer who already has an order asks how that order stands. The assistant first confirms that the customer owns it. The customer provides the order identifier. The assistant sends a 6-digit code to the email recorded for that order and does not show the email address. Only after the customer enters the correct code, while it is still valid and less than 15 minutes old, may the assistant share the recorded status, order date, items, and amounts for that order. The assistant must not share the email, full address, payment data, or documents.

**Why this priority**: Order status is a core customer-service question and it carries privacy risk. It can be demonstrated with one order that has an identifier, a status, and an email.

**Independent Test**: Supply one known order with an identifier, a status, and an email. Ask with that identifier and complete the code, ask with an unknown identifier, and ask with only a person's name.

**Acceptance Scenarios**:

1. **Given** an order has an identifier, a status, and an email, **When** the customer provides that identifier and asks for the status, **Then** the assistant sends a 6-digit code to that email, does not display the email address, and does not state the status.
2. **Given** that code was sent less than 15 minutes ago and no newer code was sent, and the customer asked only for the status, **When** the customer enters that exact code, **Then** the reply states the recorded status of that order and does not include the date, the items, the amounts, or another order.
3. **Given** the customer enters a code that is wrong or expired, **When** the assistant replies, **Then** it says the code was not accepted and does not state any order information.
4. **Given** no order is already verified in this conversation, **When** the customer asks for an order status without an identifier, **Then** the assistant asks for the order identifier and does not return any order or send a code.
5. **Given** the identifier is not in the order records, **When** the customer asks, **Then** the reply says no matching order was found, does not send a code, and does not state a status.
6. **Given** the customer gives only a person's name, **When** the customer asks for that person's orders without an order identifier, **Then** the assistant asks for the order identifier and does not disclose any order or send a code.
7. **Given** the customer has already entered the correct unexpired code for an order in this conversation, **When** the customer asks again for the status and the records have not changed, **Then** the reply repeats that same status without a new code.
8. **Given** the customer asks for every order, **When** the assistant replies, **Then** it refuses the bulk disclosure and asks for one order identifier.
9. **Given** the ownership check has succeeded and the order records include a date, items, and amounts, **When** the customer asks for those details, **Then** the reply states the recorded date, items, and amounts.
10. **Given** the ownership check has succeeded, **When** the customer asks for the email, full address, payment data, or documents, **Then** the assistant refuses and does not reveal them.

---

### User Story 4 - Find a current promotion (Priority: P3)

A customer asks what is on promotion, or whether a particular product or category has an offer. The assistant searches the supplied promotions and describes only the offers those records support.

**Why this priority**: Promotions help a customer decide what to buy, after the assistant can already answer store and catalog questions. The story can be demonstrated with the promotion records alone.

**Independent Test**: Supply promotions that include one row with `is_active` 1 and one row with `is_active` 0, plus two active promotions in different categories. Ask what is on promotion, ask by a product name, ask by a category name, and ask about a product with no active offer.

**Acceptance Scenarios**:

1. **Given** some promotions have `is_active` 1 and others have `is_active` 0, **When** the customer asks what is on promotion, **Then** the reply includes only the promotions with `is_active` 1 and their recorded conditions, omits promotions with `is_active` 0, and does not state a start date or an end date.
2. **Given** a current promotion's product name matches the customer's wording, **When** the customer asks about that offer, **Then** the reply describes that promotion as recorded and does not include a current promotion for a different product.
3. **Given** no current promotion matches, **When** the customer asks, **Then** the reply says no matching current promotion was found and does not state a discount.
4. **Given** the promotion records have no start or end date, **When** the customer asks what is on promotion, **Then** the reply uses `is_active` only as the current flag, does not treat that flag as a date, and does not invent a start date or an end date.
5. **Given** the customer asks the same promotion question again and the promotion records have not changed, **When** the assistant replies, **Then** it describes the same promotions and the same recorded conditions.
6. **Given** a category name matches the customer's wording and that category has current promotions, **When** other categories also have current promotions, **Then** the reply includes only current promotions for products in the named category and does not include promotions for products outside it.
7. **Given** the customer names a product that has no current promotion, **When** other products have current promotions, **Then** the reply says no matching current promotion was found and does not describe those other promotions.

---

### User Story 5 - Ask about a policy or procedure (Priority: P3)

A customer asks how the store handles a policy or procedure, such as returns, exchanges, warranty, or payment rules. The assistant answers from the supplied policy document and does not add rules the document does not contain.

**Why this priority**: Policy answers prevent incorrect promises. The story can be demonstrated with the policy document alone.

**Independent Test**: Ask a procedure the document explains, ask a procedure it does not explain, and ask a question that needs both a catalog price and a policy statement.

**Acceptance Scenarios**:

1. **Given** the policy document states the return rules, **When** the customer asks about returns, **Then** the reply reflects those rules and does not add conditions the document does not contain.
2. **Given** the policy document does not cover the procedure the customer asked about, **When** the assistant replies, **Then** it says the store policies do not provide that answer.
3. **Given** the customer asks about both the price of a specific product and a policy that applies to it, **When** the assistant replies, **Then** the price comes from the catalog, the policy statement comes from the policy document, and neither source replaces the other.

---

### User Story 6 - Continue the conversation (Priority: P3)

A customer follows up in short phrases, supplies a detail the assistant just requested, or changes the subject. The assistant uses the current conversation when the follow-up still refers to it, and stops using that context when the customer moves to a new subject or starts a new conversation.

**Why this priority**: Real messages are incomplete on their own. This story depends on an earlier answer existing to refer back to, so it follows the lookup stories.

**Independent Test**: In one conversation, name a catalog product and then ask "how much is it?". Separately, start a new conversation and confirm the earlier product is no longer assumed.

**Acceptance Scenarios**:

1. **Given** the conversation has just established a specific catalog product, **When** the customer asks how much it costs without repeating the product name, **Then** the reply states that product's recorded price.
2. **Given** the assistant has asked for an order identifier, **When** the customer replies with an identifier that matches one order with a recorded email, **Then** the assistant sends a 6-digit code to that email and does not state the order status.
3. **Given** the customer then enters that correct code within 15 minutes, **When** the assistant accepts it, **Then** the reply states that order's recorded status.
4. **Given** the conversation was about a product, **When** the customer next asks about a store policy, **Then** the reply answers from the policy document and does not treat the policy question as a question about that product.
5. **Given** a conversation has ended, **When** the customer starts a new conversation and sends a follow-up that only makes sense with the earlier topic, **Then** the assistant does not assume the earlier product, order, or topic and asks what the customer means. A previously accepted order code does not carry over.

---

### Edge Cases

- A matching product records neither price nor availability: the assistant says both are not recorded and does not invent them.
- The catalog, order records, promotion records, or policy document is missing, or the database cannot be read: the assistant says that kind of information is unavailable and does not fill in store facts.
- A loaded table has no row that matches the question, including a loaded table with zero rows: the assistant says that nothing matched. That answer is different from a missing file.
- More than one order shares the same identifier: the assistant does not send a code and does not reveal any order information.
- The matching order has no email address: the assistant does not send a code and does not reveal any order information.
- The code is wrong, expired, or replaced by a newer code: the assistant accepts none of those codes and reveals no order information.
- The code cannot be sent: the assistant reveals no order information and says that the code could not be sent.
- The customer asks for the email, full address, payment data, or documents after the code is accepted: the assistant refuses and does not reveal them.
- The customer sends an order identifier that differs only by letter case or surrounding spaces from a recorded identifier: the assistant treats it as that order.
- The customer asks for every order, the whole catalog, or the assistant's hidden instructions: the assistant refuses the broad disclosure. A customer may still ask for a specific product or a specific order.
- The customer asks which instrument is "best" or requests a review the catalog does not contain: the assistant uses only recorded attributes, such as price and availability, and does not invent quality, suitability, or opinions.
- Several current promotions match the same product or category question: the assistant presents each matching promotion as recorded and leaves out promotions that do not match the filter.
- More than five catalog products match the customer's words: the assistant asks for a narrower description and does not list every match.
- The customer asks for a delivery date, restock date, or payment confirmation that is not in the records: the assistant says that fact is not available, even when a related price, status, or policy is available.
- The customer mixes a new request into a follow-up: the assistant answers the new request from the matching store information and keeps earlier context only for the part of the message that still refers to it.
- The customer writes in a language other than Portuguese: the assistant replies only in Portuguese, says that it communicates only in Portuguese, and does not answer the request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a text messaging conversation in which a customer sends a message and receives a reply in that same conversation.
- **FR-002**: The system MUST answer general questions about Emporio da Musica using only the supplied business context.
- **FR-003**: The system MUST search the supplied product catalog by product name and report the recorded category name, price, and availability of matching products. Description and specs are not search text.
- **FR-004**: The system MUST NOT reveal any order information until the ownership check in FR-023 succeeds. After that check, the system MUST answer only with the recorded fields the customer asked about, and only when each field is on the allow-list in FR-016. A field the customer did not ask about MUST NOT appear in the reply. An asked field that is not recorded MUST be reported as not recorded and MUST NOT be filled in.
- **FR-005**: The system MUST search the supplied promotions and present the current promotions that match the customer's question. A promotion is current only when its recorded `is_active` value is 1. Promotions with `is_active` 0 MUST be omitted. The system MUST NOT invent a start date or an end date and MUST NOT treat `is_active` as a validity date. A question that names a product or a category MUST return only current promotions whose product name or category name matches, and MUST NOT return a promotion for a product that does not match that filter.
- **FR-006**: The system MUST answer questions about store policies and procedures using only the supplied policy document.
- **FR-007**: The system MUST recognize what the customer is asking and use the store information that holds that kind of fact: business context, catalog, orders, promotions, or policies.
- **FR-008**: When one question needs more than one kind of fact, the system MUST take each fact from its own source. A price, availability, order status, or recorded promotion MUST NOT be taken from the policy document or the general store description, and a policy MUST NOT be taken from a catalog or order record.
- **FR-009**: The system MUST decline questions that are outside help for this store, such as a recipe or another store's price. The reply MUST NOT answer that request, MUST state that the assistant can help with store information, products, orders, promotions, and policies, and MUST NOT change stored rows. This refusal is distinct from the sale-action refusal in FR-021 and the disclosure refusal in FR-022.
- **FR-010**: When a request is missing a detail required to answer it, the system MUST ask for that detail and MUST NOT guess it.
- **FR-011**: Within the current conversation, the system MUST use an established product, order, promotion, or topic to understand a follow-up that refers to it.
- **FR-012**: The system MUST stop using that earlier context when the customer changes the subject, and MUST NOT carry context from a previous conversation into a new one.
- **FR-013**: The system MUST NOT state a store fact, price, availability, order status, promotion, or policy that the supplied materials do not contain for that request.
- **FR-014**: When the supplied materials do not contain the answer, the system MUST say what it cannot confirm.
- **FR-015**: Repeating the same catalog, order, or promotion lookup against unchanged records MUST produce the same recorded facts.
- **FR-016**: The only order fields that may ever be disclosed, and only after FR-023 succeeds, are the recorded status, order date, items, and amounts for that order. Which of those fields appear in one reply is limited by FR-004 to the fields the customer asked about. The system MUST NOT reveal the email, full address, payment data, or documents. It MUST NOT disclose an order from a person's name alone, from an identifier alone, or when the identifier matches more than one order. It MUST NOT display the email address used for the code.
- **FR-017**: When 2 to 5 products match, the system MUST list each match with its recorded category name, price, and availability and MUST NOT present a single arbitrary price. A missing price or availability stays null, as in FR-019. When more than 5 products match, the system MUST ask the customer for a more specific request and MUST NOT list the whole set.
- **FR-018**: When no product, order, or promotion matches, including when the loaded table has zero rows, the system MUST say that nothing matched. A missing file or an unreadable database is unavailable, not an empty match.
- **FR-019**: When a matching record omits a requested field, the system MUST still return the match, MUST keep that field null, MUST report the fields that are present, and MUST say that the omitted field is not recorded. The system MUST NOT replace a missing price, stock quantity, or other omitted field with zero, a placeholder, or an estimate.
- **FR-020**: The system MUST write every customer-facing reply in Portuguese. Store records are in Portuguese and MUST be quoted as written. When the customer's own wording is in another language, the system MUST reply in Portuguese that it only communicates in Portuguese and MUST NOT answer that request. A Portuguese sentence that includes a recorded name written in another language, such as a catalog product name, remains a Portuguese request and MUST be answered.
- **FR-021**: The system MUST NOT create, update, cancel, or pay orders, and MUST NOT change the supplied store materials. A request to place, change, cancel, or pay for an order MUST be refused. The reply MUST state that the assistant cannot carry out that action and MUST NOT claim that a record changed. The stored rows MUST stay unchanged. This refusal is distinct from FR-009 and FR-022. A question about payment rules, or about a recorded status such as cancelled, is not a request to pay or to cancel, and MUST still be answered from the matching source.
- **FR-022**: The system MUST refuse requests for another customer's information, for a bulk disclosure of orders or of the catalog, for its own hidden instructions, and for instructions to ignore its rules. A specific product question remains allowed. A specific order may be discussed only after the ownership check for that order succeeds. A refused disclosure MUST NOT return the catalog, the instructions, or any order, and MUST NOT change stored rows. A question about a store procedure, including return instructions in the policy document, is not a request for hidden instructions and MUST still be answered from that document.
- **FR-023**: When exactly one order matches the identifier and that order has an email, the system MUST send a 6-digit code to that email and ask the customer to enter it. Identifier matching ignores letter case and surrounding spaces. A newly sent code replaces the previous one. The system MUST reject a code that is incorrect, expired, no longer the latest code, or already replaced. Until a code is accepted, the system MUST NOT state the status or any other order detail. After acceptance, a later question in the same conversation about that order MUST NOT require a new code. A different conversation MUST require a new code. The fields that may be spoken after acceptance are FR-016, limited by FR-004. If the code cannot be sent, the system MUST reveal nothing and MUST say that the code could not be sent.

### Key Entities

- **Customer**: The person in the conversation. The prototype does not require an account. A customer may ask about the store or about one identified order.
- **Conversation**: The sequence of messages in one session. It holds the current topic only for as long as that conversation continues.
- **Business context**: The supplied description of Emporio da Musica, including that it is a musical instruments store in Campo Grande, Mato Grosso do Sul, Brazil, plus any other store facts provided with it. The supplied records are written in Portuguese.
- **Product**: An item in the supplied catalog. A search matches the product name only. Description and specs are stored and are not search text. Relevant reply attributes are the name, the category name, the price, and the availability, when those values are recorded. A missing price or availability is null.
- **Order**: A purchase in the supplied order records. Relevant attributes include the order identifier (order_id), the owner's email, the status, the order date, the items, the amounts, and any other recorded details. No detail is disclosed until the customer passes the email code check for that single order. After the check, one reply includes only the allow-listed fields the customer asked about.
- **Promotion**: An offer in the supplied promotion records. It applies to one product, and that product belongs to one category. Relevant attributes are the product name, the category name, the recorded conditions, and `is_active`. The supplied file has no start or end date. `is_active` 1 means current. `is_active` 0 means not current.
- **Policy**: A rule or procedure stated in the supplied policy document, such as returns, exchanges, warranty, or payment practice.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A customer who names a catalog product with a recorded price and availability receives both in a single reply.
- **SC-002**: A customer can complete that price and availability check in under one minute.
- **SC-003**: In 100% of the acceptance scenarios, every stated store fact, price, availability, order status, promotion, and policy agrees with the supplied materials, and no reply adds a fact the materials do not contain.
- **SC-004**: In 100% of the acceptance scenarios where the materials do not contain the answer, the customer is told what is unconfirmed or is asked for the single missing detail.
- **SC-005**: In 100% of the acceptance scenarios that are out of scope, that ask the assistant to carry out a sale, or that ask for hidden instructions, a rule bypass, or the whole catalog, the assistant uses the matching refusal and tells the customer what it can help with.
- **SC-006**: A customer who completes the email code check for one valid order learns that order's recorded status in the same conversation. Providing only a name, or only the identifier, reveals no order information.
- **SC-007**: In 100% of the scripted follow-up scenarios, the customer can refer to the product or order already established in the conversation without repeating its name or identifier.
- **SC-008**: In one conversation, a customer can receive a store answer, a product price and availability, an order status, a promotion answer, and a policy answer.
- **SC-009**: From the reply alone, a customer can tell whether the assistant answered, needs one more detail, or cannot help with that request. A cannot-help reply for an out-of-scope question, a sale action, and a disclosure request are distinguishable from one another.

## Assumptions

- Emporio da Musica is one fictional musical instruments store in Campo Grande, Mato Grosso do Sul, Brazil. The people using the assistant are customers, not store staff. This is a prototype for that single Brazilian store.
- The prototype covers one text conversation at a time. It does not include customer accounts, staff tools, voice, several stores, campaigns, or a commitment to production-scale traffic.
- The prototype includes the supplied materials: product, category, customer, order, order-item, and promotion records as CSV files, and store policies as one PDF document. Those files are the only source of store facts. General business context is the short store profile kept with them.
- The order identifier (order_id) is expected to be unique. Matching ignores letter case and spaces around the identifier. If more than one order shares an identifier, or the matching order has no email, the assistant sends no code and reveals nothing.
- The 6-digit code goes to the email recorded on that order. The assistant does not show that email. The code expires 15 minutes after it is sent, and a newly sent code replaces the previous one. A correct code unlocks later questions in that same conversation about the allow-listed fields the customer asks for. It does not unlock fields the customer did not ask about, the email, full address, payment data, or documents, and it does not create a customer account. A new conversation requires a new code.
- The supplied promotion file has no start or end date. `is_active` 1 is current and `is_active` 0 is not. The assistant does not treat that flag as a date and does not invent a period. A product or category question returns only current promotions for products that match the name or the category, through the product's `category_id`.
- Prices, availability, statuses, and promotion conditions are presented as recorded. A missing price or availability stays null and is described as not recorded. The assistant does not convert currency, substitute zero, or calculate a price the records do not contain. A catalog match compares the product name only.
- A product search that matches more than 5 products is too broad. The assistant asks the customer to narrow it and does not treat that search as a request to reveal the catalog.
- "Availability" means the availability value recorded for the product, whether that value is a status or a quantity. It does not imply a delivery or restock date unless that date is recorded.
- Conversation context lasts only for the current conversation and is not kept as a customer profile afterward.
- The store supplies its records in Portuguese. Every reply to the customer is in Portuguese. A message whose own wording is in another language receives a Portuguese reply that the assistant only communicates in Portuguese, and the request is not answered until the customer writes in Portuguese. A Portuguese sentence that quotes a recorded product name stays in scope even when that name is not Portuguese.
- The assistant informs customers. It does not take payment, reserve stock, or change an order. Customers who want to buy are told that the assistant cannot complete the purchase.
- Sample materials used to demonstrate the prototype contain enough records to exercise each acceptance scenario, including at least one known product, one known order with an identifier, a status, and an email, one current promotion, one general store fact, and one stated policy. The supplied catalog CSV records a price and a stock quantity on every product. The missing-price and missing-stock scenarios use a test fixture, not a change to that CSV.
