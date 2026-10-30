# 0004: Deploy the few-shot answerer

- **Status:** accepted
- **Date:** 2026-10-22
- **Author:** *a fourth member*
- **Lesson:** L04

## Context

30 questions, three runs each (claude-haiku-4-5, 2026-10-22; runs
`20261022-154019-answer30`, `-r1`, `-r2`; retrieval as in decision 0003):

| Strategy | Wrong, 3 runs | Faithfulness (judge, 0-2) | Says "I don't know" when it should | Per 1,000 | p95 |
|---|---|---|---|---|---|
| zero-shot | 2, 2, 1 | 1.82 | 2/3 | $1.86-1.98 | 4.1 s |
| few-shot | 0, 0, 0 | 2.00 | 3/3 | $2.18-2.26 | 3.3 s |
| chain-of-thought | 0, 0, 0 | 1.98 | 3/3 | $2.32-2.42 | 4.7 s |

## Options considered

| Option | For | Against |
|---|---|---|
| Zero-shot | Cheapest | The only one to answer in the wrong language, to answer an unanswerable question, and to add unsupported details |
| **Few-shot** | No error in three runs, fully faithful, cheaper and faster than chain-of-thought | Three examples to maintain; ~$0.30 more per 1,000 than zero-shot |
| Chain-of-thought | No error in three runs | Dearest and slowest; its reasoning is never shown to the customer |

## Criteria

A wrong promise to a customer costs more than a cent: errors and faithfulness
first, then cost and latency. Here the cheaper strategy is not good enough.

## Decision

Deploy `answer_few_shot_v1`.

## Consequences

- About $2.25 per 1,000 questions.
- 0 errors on 30 questions is a reason to test on real customer questions
  (the tickets' questions), not a guarantee: 17 of our 30 were written by our
  assistant from the policies.
