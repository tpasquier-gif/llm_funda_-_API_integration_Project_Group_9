# 0002: Answer as a checked record (answer, answerable, citations), one retry layer

- **Status:** accepted
- **Date:** 2026-10-22
- **Author:** *a member who did not write 0001*
- **Lesson:** L02

## Context

A free-text answer cannot be checked: nothing says which page it came from,
or whether the model knows that it does not know. Measured in step 2 (closed
book, claude-haiku-4-5, 2026-10-22, Q01-Q10): asked for a record with an
`answerable` field and told it had not seen the policies, the model refused
9 of 10 questions instead of inventing 8 of 10. The record makes "I don't
know" something code can read; only retrieval (step 3) gives it something to
say.

## Options considered

| Option | For | Against |
|---|---|---|
| Free text | Cheapest | No citation, no "I don't know" a program can read |
| `messages.parse()` (the L03 exercise) | Shortest | Validation inside the SDK: an invalid citation loses the text we re-prompt with |
| **Structured outputs + our rules in code** | Citations checked against the passages retrieved, `answerable` consistent with citations, the output check, each error a re-prompt | More code |

Retry layer: ours (tenacity, transient errors only) with the SDK's off.

## Criteria

Can an answer be sent without a person reading it? Only if code checked its
citations and its contacts.

## Decision

Structured outputs; four rules in code (citations retrieved, answerable iff
cited, no unpublished link, e-mail or phone, not empty); at most two
re-prompts, then a give-up; one retry layer; `stop_reason` checked.

## Consequences

- Measured: in step 3 one answer cited a passage it had not been given
  (`02-delivery#5`); the rule refused it and the re-prompt fixed it. On the 30
  test questions, 1 or 2 first answers per run were re-prompted, none given up.
- No temperature in SDK 1.10.0: three runs per strategy.
