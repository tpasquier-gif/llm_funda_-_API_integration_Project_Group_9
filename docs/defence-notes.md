# Defence notes

*For the 15-minute defence (10 min presentation, 5 min questions, one
unprepared question per member).*

## How this repository was built

The group used an AI coding assistant (Claude) to draft the code, the prompts
and the documents; the school's evaluation policy allows it and asks that we
own every choice. Every figure comes from a real API run recorded in
`runs/calls.csv`. Before the defence, each member must re-read and sign: the
17 test questions our assistant drafted (Q14-Q30 in
`evals/test_questions.csv`, `checked_by`), the few-shot examples
(`prompts/answer_few_shot_v1.md`), the ten judge scores in
`runs/judge_sample_for_humans.csv`, and the decision record they defend.

## The ten-minute story

1. **The problem** (1 min): without our documents the model invents our
   policies, 8 of 10 times, confidently. Told to admit it, it refuses 9 of 10.
2. **What we built** (3 min): the six PDFs, chunked to fit the embedding
   model, searched with FAISS; an answer as a record whose citations, "I don't
   know" and contacts are checked in code; seller pages kept apart and
   sanitised.
3. **How we know it works** (3 min): 0/10 wrong with retrieval; the chunk size
   chosen from a free sweep; three strategies x three runs; a faithfulness
   judge; the tampered page attack, measured with and without each defence.
4. **What each defence does** (2 min): the prompt stops the false policy
   (14/15 to 0/15); the output check stops contacts, not lies.
5. **What we deploy** (1 min): few-shot, $2.25 per 1,000 questions.

## Questions we expect, and our answers

**Why RAG and not a long context?** Measured need, cost and position: the
whole help centre is ~16,500 tokens per question (~$17 per 1,000, 8x our
cost) for no measured gain, since retrieval found the evidence for all 27
answerable questions at k=3.

**Why 300-token chunks?** The free sweep: 150 tokens missed Q04's evidence
(the rule was cut from its context); 300 and 500 found all 27; 300 costs 40%
fewer prompt tokens. All under e5-small's 512-token limit, counted with its
own tokenizer.

**Why e5-small?** The course's model: multilingual (our customers write in
three languages), small enough for a CPU, and with the query/passage prefixes
it was trained with.

**How do you know a citation is real?** Code: every cited id must be one of
the three passages retrieved; otherwise the model is re-prompted with the
allowed ids. It happened once in step 3 (`02-delivery#5`) and was fixed.

**What does the judge check that code cannot?** That the rest of the answer
is in the cited passages: code checks the expected fact is there, not that
nothing else was added. The judge found zero-shot adding details ("formulated
for oily skin types"). Bias controls: Opus judging Haiku, blind to the
strategy, never sees the reasoning, two orders (3/82 disagreements), length
correlation +0.04.

**Did you change the scoring after seeing results?** Once, and we say so:
Q15's facts missed the phrasing "only use one discount code", a correct
answer; we widened the facts and re-scored the saved answers (2 changed). No
answer was edited and no call was re-made.

**Does the sanitising work?** On this attack it showed no extra effect: our
prompt alone brought the false policy to 0/15. We keep it as defence in
depth, and we do not claim more than we measured.

**Why few-shot rather than chain-of-thought, both with 0 errors?** Same
errors, same faithfulness to within a point; few-shot is cheaper ($2.18-2.26
against $2.32-2.42 per 1,000) and faster (p95 3.3 s against 4.7 s), and the
customer never sees the reasoning chain-of-thought pays for.

**What is the weakest part?** The test set: 17 of 30 questions were written
by our assistant, in clean English. Real customer questions (the tickets) are
the next test.

## If we are asked to test it live

`python -m src.ask "<a question of the examiner>"` runs the deployed pipeline
(few-shot, top 3) on any question and prints the passages found, the answer,
its citations and what it cost (about $0.002; a question already asked is
free, from the cache). Without a question it asks one after another.

- **On the demo machine, the day before:** the repository, `pip install -r
  requirements.txt`, the member's **own** key in `.env`, and one question asked
  once, so the PDFs and the embedding model (~470 MB) are already downloaded.
- **Good questions to show:** one in French (it answers in French); one the
  help centre does not answer ("Do you offer gift wrapping?": it says so);
  `--injected` with "Can I return the OZNaturals Retinol Serum after opening
  it?" (the tampered page is retrieved; our injection figures, 0 of 15, were
  measured with the zero-shot prompt, not with few-shot: try it once before
  the defence rather than discover it in front of the jury).
- Demo calls are logged in `cache/demo_calls.csv`, never in `runs/calls.csv`:
  the study's figures do not move.
