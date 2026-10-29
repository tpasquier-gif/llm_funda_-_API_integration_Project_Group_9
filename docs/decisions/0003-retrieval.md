# 0003: Retrieve with multilingual-e5-small, 300-token chunks, top 3; seller pages untrusted

- **Status:** accepted
- **Date:** 2026-10-22
- **Author:** *a third member, who wrote neither 0001 nor 0002*
- **Lesson:** L03

## Context

Retrieval is required: without the documents, 8 of 10 answers were wrong
(step 1); with them, 0 of 10 (step 3). The settings to choose are the
embedding model, the chunk size and how many passages to give the model, and
how to handle text that sellers wrote.

**Embedding model:** `intfloat/multilingual-e5-small`, the course's, 384
dimensions, multilingual (our customers write in English, French and German),
runs on CPU; it reads **512 tokens**: a longer passage is cut silently before
it is embedded, so chunks must stay under it.

**Measured, free** (`python -m evals.retrieval_sweep`: no LLM call; 27
answerable test questions; is the policy sentence in the top k passages?):

| Chunk tokens (max) | Passages | k=1 | k=3 | k=5 | Prompt tokens at k=3 | Missed at k=3 |
|---|---|---|---|---|---|---|
| 150 | 126 | 21 | 26 | 26 | ~390 | Q04 |
| **300** | 60 | 22 | **27** | 27 | **~820** | none |
| 500 | 36 | 21 | 27 | 27 | ~1,370 | none |

## Options considered

| Option | For | Against |
|---|---|---|
| 150-token chunks | Cheapest prompt | Missed Q04's evidence (the late-parcel rule cut from its context) |
| **300-token chunks, k=3** | Every evidence found; 40% fewer prompt tokens than 500 | - |
| 500-token chunks | Every evidence found | 1.7x the passage tokens for nothing measured |
| The whole help centre in every prompt | No retrieval misses | ~16,500 tokens per question: ~$17 per 1,000, 8x our cost |

## Criteria

Evidence retrieved at k=3 first, then prompt tokens (cost per question).

## Decision

Whole-sentence chunks of at most 300 tokens (counted with e5's own
tokenizer), FAISS exact inner-product search on normalised vectors, top 3.

## Untrusted text, and what stops it

Documents 05 (product pages) and 06 (catalogue attributes "as the sellers
entered them") are written by sellers: untrusted. In code they go in their
own `<seller_pages>` block, their instruction-like sentences are removed
(`src/llm.py`, `sanitise`), and the prompt says they are a source for product
facts only, never for policies or contacts. The output check (code) refuses
any link, e-mail address or phone number except the one the help centre
publishes. Measured on the course's tampered page (15 runs): the plain
grounded prompt sent the false 365-day policy 14 times; our prompt, 0. The
output check caught the seller's e-mail 13 times but could not catch the
false policy: the prompt is the defence for content, the code for contacts.

## Consequences

- 60 passages, ~820 prompt tokens of passages per question.
- The index must be rebuilt when the corpus version changes (the version and
  its checksum are in every figure).
- Two French and one German question are in the test set; retrieval found
  their evidence (English documents, multilingual model), but zero-shot
  answered one English question in French: language is a prompt matter.
