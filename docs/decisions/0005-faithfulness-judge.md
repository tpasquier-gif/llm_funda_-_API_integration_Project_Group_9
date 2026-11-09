# 0005: Score faithfulness with a bias-controlled Claude Opus 5.5 judge

- **Status:** accepted
- **Date:** 2026-10-29 (records the choice made for the step-4 run of 2026-10-22)
- **Author:** Robin Cacarié
- **Lesson:** L04

## Context

Code already scores most of the rubric against the policies (`evals/run.py`):
the expected fact is in the answer (R1), the evidence was retrieved (R2), the
answer says "I don't know" when it should (R3), every citation was retrieved
(R5), no unpublished contact leaks (`src/schema.py`). One thing code cannot
check: **that nothing else in the answer was invented.** A correct fact plus an
invented one ("21 days, and gift wrapping is free") passes the fact check. For
a help desk that is the dangerous failure: a confident promise the company
never made.

Faithfulness needs judgement, so the choice is who judges, and how to keep
that judge honest. The volume is small but repeated: the main step-4 run has
82 answers that claim to be answerable (zero-shot 28, few-shot 27,
chain-of-thought 27), and every change of prompt or model means judging again.

## Options considered

| Option | For | Against |
|---|---|---|
| No faithfulness check (code only) | Free, deterministic | Blind to the failure that matters most: an added, unsupported claim |
| A member scores every answer | The reference: a human reading the policies | 82 answers × 3 strategies to re-read at each change; tiring, so inconsistent; nobody would re-run it |
| Claude Haiku 4.5 as judge (the answering model) | Cheapest | Self-preference: a model rates its own style higher, and it would judge text it wrote |
| **Claude Opus 5.5 as judge, with bias controls** | A different, stronger model; consistent; re-runs with one command | Costs money; it is still a model, with biases to control and a score to check against humans |
| A similarity metric (embeddings, overlap with the passages) | Free | Not tried: an answer can be close to its passages and still add one false detail |

## Criteria

1. **It must catch an added claim**, not just a missing fact: only a reader
   (human or model) does.
2. **The score must not depend on how the question is put to the judge:**
   who wrote the answer, its length, the order of the inputs.
3. **It must be cheap and quick enough to re-run** after every prompt change.
4. **It must be checkable** against human judgement.

## Decision

Faithfulness (rubric criterion R4) is scored by **Claude Opus 5.5**
(`evals/judge.py`), on every answer that claims to be answerable, on a 0-2
scale: 0 = states something the cited passages do not say; 1 = main claim
supported, a detail is not; 2 = every claim is in the cited passages. The
judge must name the unsupported claim before giving its score.

The judge's biases are controlled in the design:

- **Self-preference:** the judge (Opus 5.5) is not the judged model (Haiku 4.5),
  and never learns which strategy wrote the answer.
- **Length:** the judge never sees the chain-of-thought reasoning (only what the
  customer would read), is told that length is not a criterion, and we report
  the correlation between an answer's length and its score.
- **Position:** each answer is judged **twice**, once with the scale written
  0 -> 2 and the passages before the answer, once with the scale 2 -> 0 and the
  answer first; the mean is kept and every disagreement is reported.
- **Strictness:** the judge sees only the passages the answer **cited**, so an
  answer is faithful to its own citations, not to everything retrieved.
- **Injection:** passages and answer are wrapped in tags and declared data;
  the judge is told never to follow instructions inside them.

## What it measured

`python -m evals.judge runs/20261022-154019-answer30__*.csv`, run
`20261022-154019-answer30-judge`, 2026-10-22, 164 judge calls (154 paid,
10 answered from the cache), every verdict valid:

| Strategy | Faithfulness (0-2) | Fully supported | Below 2 |
|---|---|---|---|
| zero-shot | 1.82 | 23 / 28 | Q03, Q10, Q12, Q14, Q17 |
| few-shot | **2.00** | **27 / 27** | none |
| chain-of-thought | 1.98 | 26 / 27 | Q14 |

- What it caught, that code could not: zero-shot adding small claims that are
  not in the passages ("specifically formulated for oily skin types", Q10;
  "you would need to request a new reset link", Q14).
- **Position control:** 3 of 82 answers were scored differently when the order
  was swapped (zero-shot Q03 and Q17, chain-of-thought Q14), each by one point;
  the mean (1.5) is kept.
- **Length control:** correlation(answer words, score) = **+0.04**: no sign
  that longer answers score higher.
- **Cost:** $0.80 for the 154 paid judge calls (`runs/calls.csv`), about
  $0.005 per judgement; half of the whole study's $1.59.

This score is one of the two reasons few-shot is deployed (decision 0004):
same error count as chain-of-thought, but fully faithful and cheaper.

## Consequences

- **Faithfulness is now a number we can re-measure** in one command after any
  change of prompt, model or retrieval. It costs about a cent per answer
  (two judgements), so a full 3-strategy run is under a dollar.
- **The judge, checked against a human (2026-11-09):** ten of its judgements,
  drawn at random (seed 9) into `runs/judge_sample_for_humans.csv`, were scored
  by Robin Cacarié against the passages each answer cites. **He agreed with the
  judge on 10 of 10** (all ten scored 2). Two limits: the check was not blind
  (he had seen that an AI review of the same ten agreed with the judge), and
  all ten were judged 2, so it says nothing yet about how the judge scores a
  weak answer. If a later check disagrees with more than a couple of ten, we
  stop quoting R4 as a measurement and look at where the judge goes wrong.
- **A judge score is a model's output:** it varies from run to run like any
  other. We ran the judge once; the 3/82 position disagreements are our only
  measure of its noise. Small gaps (1.98 against 2.00) are not differences.
- **Strict by design:** an answer that uses a retrieved but uncited passage is
  marked unsupported. That is intended (an answer must cite what it uses), but
  it means R4 also measures citation discipline, not only invention.
- **Re-judge when:** the judge model changes (scores are only comparable with
  the same judge), the scale or the judge's prompt changes, or the answers
  change. The judge's prompt lives in `evals/judge.py` rather than `prompts/`:
  a change to it is a change to the measure, and gets a new record.
