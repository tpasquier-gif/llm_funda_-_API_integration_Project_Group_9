# 0001: Build a help-centre answerer with retrieval

- **Status:** accepted
- **Date:** 2026-10-22
- **Author:** *the member who defends it* (drafted with an AI assistant, see the defence notes)
- **Lesson:** L01

## Context

Customers ask questions the help centre answers (returns, delivery, payment,
account). A model alone does not know Albert's Marketplace's policies, which
were chosen to differ from common practice: measured in step 1, it gave a
wrong policy for 8 of 10 questions. The course offers three components.

## Options considered

| Option | For | Against |
|---|---|---|
| Classifier (route tickets) | 120 human-checked labels | Routes the question, answers no one |
| Extraction (tickets into records) | Ground truth in the database | Saves agents' time, not customers' |
| **Retrieval: answer from the help centre** | Answers the customer directly; the model's ignorance is measured (8/10 wrong without documents); the documents are versioned | No checked question-answer set: 13 questions from the course, 17 we write from the policies; an error is a wrong promise to a customer, the most expensive failure of the three |

## Criteria

Value to the customer; risk of a wrong answer, and whether we can control it
(citations checked in code, "I don't know", the output check); test
questions with answers taken from the policies themselves.

## Decision

Answer customers' questions from the help centre with retrieval, citations
validated in code, and an explicit "I don't know".

## Consequences

- The expected answers are quotes of the policies, not opinions; 17 of 30
  questions were drafted by our assistant and must be re-read by a member.
- The documents are a dependency: every figure names their version, and the
  index must be rebuilt when they change.
- Seller-written pages are part of the corpus and untrusted: injection is a
  first-class concern from step 3.
