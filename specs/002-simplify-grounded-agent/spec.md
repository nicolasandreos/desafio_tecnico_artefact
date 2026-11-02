# Feature Specification: Simplify Grounded Answers

**Feature Branch**: `002-simplify-grounded-agent`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "001-customer-service-agent. The current assistant leaves policy consultation switched off, so a policy question is not answered from a meaning-based search of the store policy document. The correction must turn that consultation on and keep it on. The prototype must stay as small as the behavior requires. Whether a message is Portuguese, and every scope, sale-action, and disclosure limit, must be applied by the assistant as part of its reply, including for wording that is not a fixed example sentence. Parts that only classified those messages before the assistant replied, that only copied the operational tables into a separate database, or that only exposed policy as an operational lookup, must be removed, along with anything else no specified behavior uses. Product, order, and promotion facts must be read from the supplied table files themselves. Policy questions must be answered only from passages of the policy document found by similarity of meaning."

## Clarifications

### Session 2026-10-31

- Q: Should language, scope, and order privacy all be left to the assistant's instructions? → A: Language, out-of-scope topics, sale-action wording, and disclosure wording are instructions the assistant follows, including for ordinary paraphrases. Order ownership, the hiding of sensitive customer and order fields, and the ban on changing an order stay enforced by the application even when the assistant is told to ignore them. The assistant has no action that places, changes, cancels, or pays an order.
- Q: If the assistant is stopped and started again, must the customer pass the ownership check again before any order detail is shown? → A: A restart is a new conversation. The earlier topic and the accepted code are forgotten. The customer must pass the ownership check again.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a policy answer from the policy document (Priority: P1)

A customer asks how Emporio da Musica handles a policy or procedure, such as returns, exchanges, warranty, or payment rules. The assistant searches the store policy document by the meaning of that question and answers only from the passages that support the answer. It does this for every policy question. It does not skip the document, answer from memory, or take the rule from a product, order, or promotion record.

**Why this priority**: A policy answer that never consults the policy document can promise a rule the store did not write. This slice is useful with the policy document alone.

**Independent Test**: With only the policy document available, ask a procedure it explains, ask the same procedure in different words, ask a procedure it does not explain, and ask when the document cannot be searched.

**Acceptance Scenarios**:

1. **Given** the policy document states the return rules, **When** the customer asks about returns, **Then** the reply reflects those rules and does not add a condition the document does not contain.
2. **Given** the same return rules, **When** the customer asks again in different words that still mean a return, **Then** the reply still reflects those rules and still comes from the policy document.
3. **Given** the policy document does not cover the procedure the customer asked about, **When** the assistant replies, **Then** it says the store policies do not provide that answer and does not invent a rule.
4. **Given** the policy document cannot be searched, **When** the customer asks about a policy, **Then** the reply says that policy information is unavailable and does not state a rule.
5. **Given** a product has a recorded price and the policy document states a return rule, **When** the customer asks only about that return rule, **Then** the reply does not state the price.
6. **Given** the policy document is available, **When** the customer asks any policy question, **Then** the reply is based on a meaning search of that document for this question. A reply produced without consulting the document fails this scenario.

---

### User Story 2 - Get operational facts from the supplied tables (Priority: P1)

A customer asks about a product, an order, or a promotion. The assistant reads the supplied table files, selects the matching rows, and reports the recorded facts. Those facts are the values in the files. They are not taken from a separate database loaded from the files, from the policy document, or from memory.

**Why this priority**: Price, availability, order status, and promotions are trustworthy only when they are the values the store supplied. This slice can be demonstrated with the table files alone.

**Independent Test**: With the table files present, ask for a known product by name, complete the ownership check for one known order, and ask what is on promotion. Repeat each question without changing the files. Then ask again with a table file missing, and with a loaded table that has no matching row.

**Acceptance Scenarios**:

1. **Given** a catalog product has a recorded price, availability, and category name, **When** the customer asks for that product by name, **Then** the reply states those recorded values from the product table and no different price.
2. **Given** the customer asks that same product question again and the product table has not changed, **When** the assistant replies, **Then** it states the same price and the same availability.
3. **Given** the ownership check for one order has succeeded, **When** the customer asks for the recorded status, **Then** the reply states the status stored in the order table for that order.
4. **Given** promotions are marked current or not current in the promotion table, **When** the customer asks what is on promotion, **Then** the reply includes only the current promotions and the conditions recorded in that table.
5. **Given** a product price is recorded only in the product table, **When** the customer asks for that price, **Then** the reply does not take the price from a policy passage.
6. **Given** an operational table file is missing or cannot be read, **When** the customer asks for that kind of fact, **Then** the reply says that information is unavailable and does not fill it in.
7. **Given** the table file is present and no row matches, including a table with zero rows, **When** the customer asks, **Then** the reply says nothing matched. That answer is different from a missing file.
8. **Given** an order exists and the ownership check for this conversation has not succeeded, **When** the customer asks for the status and tells the assistant to skip the check, **Then** the reply states no order field.
9. **Given** the ownership check has succeeded, **When** the customer asks for the email, full address, payment data, or documents, **Then** the reply does not include them.
10. **Given** the customer has passed the ownership check in this run, **When** the assistant is stopped and started again, **Then** the earlier topic and the accepted code are forgotten, and no order field is revealed until the customer passes the ownership check again.

---

### User Story 3 - Hear the right refusal in ordinary words (Priority: P2)

A customer writes in Portuguese or in another language, asks for something outside this store, asks the assistant to carry out a sale, or asks for hidden instructions. The assistant understands the message and applies the store's existing limits in its reply. A sentence that does not repeat a fixed example is treated the same way as the example. The customer receives the assistant's reply. No earlier step accepts or rejects the message by matching a fixed list of words.

**Why this priority**: Customers do not phrase requests as example sentences. A fixed list misses ordinary wording, so the customer either gets an answer the store forbids or a refusal of a question the store should answer.

**Independent Test**: Send a non-Portuguese store question, an out-of-scope request, a sale request, and a disclosure request, each in wording that does not copy a stock sentence. Send one Portuguese price question whose product name is not Portuguese. Confirm the specified reply in each case, and confirm that an in-scope Portuguese question is still answered.

**Acceptance Scenarios**:

1. **Given** the customer asks a store question in a language other than Portuguese, in a sentence that is not a stock example, **When** the assistant replies, **Then** the reply is in Portuguese, states that the assistant only communicates in Portuguese, and does not answer the request.
2. **Given** the customer's message does not show a language, **When** the assistant replies, **Then** the reply is in Portuguese.
3. **Given** the customer writes in Portuguese and asks the price of a product whose recorded name is in another language, **When** the assistant replies, **Then** it answers from the product table in Portuguese and quotes that name as recorded.
4. **Given** the customer asks, in their own words, for a recipe or for another store's price, **When** the assistant replies, **Then** it declines, does not answer that request, offers help only with this store's information, products, orders, promotions, and policies, and does not change any store record.
5. **Given** the customer asks, in their own words, to place, change, cancel, or pay for an order, **When** the assistant replies, **Then** it states that it cannot carry out that action, does not claim that any record changed, and does not change any store record.
6. **Given** the customer asks, in their own words, for the assistant's hidden instructions, to ignore its rules, or for the entire catalog or every order, **When** the assistant replies, **Then** it refuses, does not reveal those materials, invites one specific question, and does not change any store record.
7. **Given** the customer asks about return instructions that the policy document contains, **When** the assistant replies, **Then** it answers from that document and does not treat the question as a request for hidden instructions.
8. **Given** the customer asks about payment rules in the policy document, or about a recorded status such as cancelled, **When** the assistant replies, **Then** it answers from the matching source and does not treat the question as a request to pay or to cancel.

---

### User Story 4 - Keep one source for each kind of fact (Priority: P2)

A customer asks a question that needs both a price and a policy, or follows up on a product with a policy question. The price comes from the product table. The policy comes from a meaning search of the policy document. The prototype that produces these answers contains only the parts those behaviors, and the behaviors already specified for this assistant, require.

**Why this priority**: A customer who asks for a price and a return rule in the same breath needs each fact from its own source. Extra unused parts make that mix hard to see. One product row and one policy passage are enough to show the reply.

**Independent Test**: Ask for the price of a named product and the return rule in one message. Confirm the price matches the product table and the return rule matches the policy document. On that same prototype, confirm that every part serves a specified behavior and that the three retired roles are absent: a pre-reply phrase filter, a database copy of the table files, and an operational lookup whose job is policy.

**Acceptance Scenarios**:

1. **Given** a product has a recorded price and the policy document states a return rule, **When** the customer asks for both in one message, **Then** the price comes from the product table, the policy statement comes from the policy document, and neither source replaces the other.
2. **Given** the conversation has just established a product, **When** the customer asks about the warranty without repeating the product name, **Then** the warranty statement comes from the policy document and the product's price is not presented as a policy.
3. **Given** the correction is in place, **When** a reviewer accounts for every part of the prototype, **Then** each part is required by a behavior in this specification or in the customer-service specification, and parts with no such behavior are absent.
4. **Given** a policy question is answered, **When** the path of that answer is examined, **Then** the path is a meaning search of the policy document, and there is no operational lookup for policy on that path.
5. **Given** a product, order, or promotion question is answered, **When** the path of that answer is examined, **Then** the path reads the supplied table files, and there is no separate database holding a copy of those files on that path.
6. **Given** a non-Portuguese message or an out-of-scope message, **When** the assistant replies, **Then** the reply is the assistant's own reply, and no earlier step matches a fixed phrase list and returns a refusal before the assistant responds.
7. **Given** the ownership check, the catalog limit of five matches, current promotions, privacy of order fields, and conversation context specified for this assistant, **When** those scenarios run after the correction, **Then** they still pass.

---

### Edge Cases

- The policy document has a passage that shares words with the question but does not state the rule: the assistant does not present that passage as the rule and says the policies do not provide the answer.
- The customer asks for a delivery date, restock date, or payment confirmation that is not in the tables and not in the policy document: the assistant says that fact is not available.
- The customer asks which instrument is best: the assistant uses only recorded attributes and does not invent quality, suitability, or opinions.
- More than one order shares the same identifier, or the matching order has no email: the assistant sends no code and reveals nothing, as already specified.
- The customer asks for the email, full address, payment data, or documents after the ownership check: the assistant refuses and does not reveal them.
- A follow-up refers to the product or order already established in this conversation: the assistant still uses that context, and still takes each fact from its own source.
- A new conversation does not keep the earlier product, order, or accepted ownership check. Stopping the assistant and starting it again begins that new conversation.
- The customer mixes a new request into a follow-up: the assistant answers the new request from the matching source and keeps earlier context only for the part that still refers to it.
- Removing a retired part leaves a specified behavior without a way to produce it: that removal is incomplete until the behavior works again from the source this specification names.
- The customer tells the assistant to ignore the ownership check or to reveal a sensitive field: the order stays hidden until the check succeeds, and the sensitive field stays hidden after it succeeds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The customer-facing behavior already specified for the Emporio da Musica assistant remains in force, including catalog search, the order ownership check, promotions, Portuguese replies, the three distinct refusals, grounding, privacy of order fields, and conversation context. This specification adds the source of each kind of fact and requires the assistant itself to apply language and scope. It does not add a new customer capability.
- **FR-002**: For every question about store policy or procedure, the assistant MUST search the policy document by similarity of meaning to that question and MUST answer only from the passages that support the answer. Policy consultation MUST be in effect for those questions. A policy answer produced without that search fails.
- **FR-003**: The assistant MUST NOT answer a policy question from memory, from a product, order, or promotion record, or from an operational lookup. A passage that does not support the question MUST NOT be stated as the rule.
- **FR-004**: When no retrieved passage supports the policy question, the assistant MUST say that the store policies do not provide that answer.
- **FR-005**: When the policy document cannot be searched, the assistant MUST say that policy information is unavailable and MUST NOT invent a policy.
- **FR-006**: Product, category, customer, order, order-item, and promotion facts MUST be read from the supplied table files by selecting the matching rows. The assistant MUST NOT answer those facts from a separate database loaded from the files, from the policy document, or from memory.
- **FR-007**: Repeating the same product, order, or promotion question against unchanged table files MUST return the same recorded facts.
- **FR-008**: A missing or unreadable operational table MUST be reported as unavailable. A present table with no matching row, including a table with zero rows, MUST be reported as no match. The two outcomes MUST be distinguishable.
- **FR-009**: When one question needs an operational fact and a policy, the assistant MUST take the operational fact from the table files and the policy from the meaning search. The assistant MUST NOT substitute either source for the other.
- **FR-010**: The assistant MUST apply Portuguese-only replies, refusal of out-of-scope requests, refusal of sale actions, and refusal of disclosure to the meaning of the customer's message, including wording that does not repeat a fixed example sentence. The customer-visible outcomes remain those already specified: the reply is Portuguese; a non-Portuguese request is not answered; the three refusals stay distinct; no store record changes; a Portuguese request that only quotes a non-Portuguese recorded name is answered.
- **FR-011**: A check that accepts or rejects the message before the assistant replies, by matching a fixed list of words or phrases, does not satisfy FR-010. The reply the customer receives MUST be the assistant's reply.
- **FR-012**: The prototype MUST contain only parts required by a behavior in this specification or in the customer-service specification. After the correction, the following MUST be absent: a step that accepts or rejects a message before the assistant replies by matching a fixed list of words, an operational lookup whose job is store policy, and a database whose only role is to hold a copy of the supplied tables. Any other part that no specified behavior uses MUST be absent as well. FR-015 is a required behavior and MUST remain.
- **FR-013**: The correction MUST NOT add a part whose only job is to host a conduct rule the assistant already applies, or to stand between a supplied table file and the row that answers the question.
- **FR-014**: Meeting FR-012 MUST NOT drop a behavior required by FR-001. The ownership check, the catalog limit of five matches, which promotions count as current, which order fields may be spoken, and conversation context MUST still hold.
- **FR-015**: Before any order field is revealed, the application MUST confirm that this conversation passed the ownership check for that order. After the check, the application MUST return only the allow-listed fields the customer asked about, and MUST withhold email, full address, payment data, and documents. The assistant MUST NOT have an action that creates, updates, cancels, or pays an order, or that changes a supplied table. Instructions to the assistant do not replace these checks.
- **FR-016**: Stopping the assistant and starting it again MUST end the conversation. The earlier topic and any accepted ownership check MUST be forgotten. No order field from the earlier check is revealed until the customer passes the ownership check again.

### Key Entities

- **Policy passage**: A portion of the supplied policy document that can be compared with the customer's question by meaning. The assistant may state a policy only when a retrieved passage supports it. A passage is not a price, a stock quantity, an order status, or a discount.
- **Operational table**: One supplied table of store records: products, categories, customers, orders, order items, or promotions. The answer is the matching rows in that file. A missing price, availability, or other requested field stays unrecorded and is not replaced with zero or an estimate.
- **Customer message**: The text the customer sends. Language and scope are judged from its meaning. A fixed example sentence is not the rule.
- **Ownership grant**: Proof, for this conversation only, that the customer entered the correct unexpired code for one order. It is not a row in a supplied table, it is not shown to the customer, and it does not unlock a sensitive field. It ends when the assistant is stopped and started again.
- **Conversation**: The current session, unchanged from the customer-service specification while the assistant keeps running. It holds the current topic only while that conversation continues, and it does not change which source a fact comes from. Stopping the assistant and starting it again starts a new conversation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of the policy acceptance scenarios, every policy statement agrees with the policy document, or the customer is told that the policies do not provide the answer or that policy information is unavailable. No policy reply adds a rule the document does not contain.
- **SC-002**: A customer who asks a policy question the document can answer receives that answer in one reply, in under one minute.
- **SC-003**: In 100% of the product, order, and promotion scenarios already specified for this assistant, every stated fact matches the supplied table files. Repeating the question against unchanged files repeats the same facts.
- **SC-004**: In 100% of the paraphrased language, scope, sale-action, and disclosure scenarios, the customer receives the specified Portuguese outcome, and an in-scope Portuguese question is still answered.
- **SC-005**: In 100% of questions that ask for both a price and a policy, the price matches the product table and the policy statement matches the policy document.
- **SC-006**: A review of the finished prototype finds no part that fails to serve a specified behavior, and finds none of the three retired roles: a pre-reply phrase filter, a database copy of the table files, and an operational policy lookup.
- **SC-007**: From the reply alone, a customer can tell whether the assistant answered, needs one more detail, or cannot help, and can tell an out-of-scope refusal, a sale-action refusal, and a disclosure refusal apart from one another.
- **SC-008**: In 100% of attempts to hear an order field before the ownership check succeeds, or to hear a sensitive field after it succeeds, the reply contains none of those fields. No attempt changes a supplied table.

## Assumptions

- The customer-service specification remains the contract for what a customer may hear, which fields an order reply may include, how ownership is confirmed, how many catalog matches may be listed, and which promotions are current. This specification wins only where it names the source of a fact or where it requires the assistant itself to apply language and scope.
- The people using the assistant are customers of one fictional musical instruments store in Campo Grande. The prototype still covers one text conversation at a time.
- The policy document is the supplied store-policy PDF. A meaning search compares the question with passages of that document and uses only passages that support the answer. That search is how every policy question is answered, and it stays available whenever the document can be searched.
- The operational tables are the supplied files for products, categories, customers, orders, order items, and promotions. An operational answer is a selection of rows from those files. Loading those files into a separate database and querying that database is outside this correction.
- General facts about the store, such as the city, still come from the supplied business context. They are not invented and they are not taken from a policy passage.
- Conduct rules cover the limits already specified: Portuguese only, out-of-scope requests, sale actions, and disclosure. They are part of the assistant's reply. They do not store prices or policy text in the assistant's memory, and they do not replace a lookup. They also do not replace the ownership check, the sensitive-field limit, or the ban on changing an order.
- The ownership grant lasts only while that conversation's assistant run continues. Stopping the assistant and starting it again forgets the earlier topic and the accepted code. The grant is not a supplied table and it is not copied into one. A new conversation requires a new code.
- A part is unused when no behavior in this specification or in the customer-service specification requires it. Checks that protect a specified customer-facing behavior remain. Checks that only match a retired phrase list do not remain, once the paraphrased scenarios cover that behavior.
- Sample materials still include at least one known product, one known order with an identifier, a status, and an email, one current promotion, one general store fact, and one stated policy. Missing-field cases still use a fixture rather than a change to the supplied catalog file.
- The correction does not add customer accounts, staff tools, voice, several stores, or a new channel.
