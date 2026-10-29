"""Choose the chunk size and k from measurements: is the evidence among the passages retrieved?

Free: no LLM call, only the embedding model on this machine. For every
answerable test question, the evidence (a phrase of the help centre, written
in evals/test_questions.csv) must appear in one of the top-k passages.

    python -m evals.retrieval_sweep

For beginners
-------------
Two settings shape retrieval: how big each passage is (the chunk size, in
tokens) and how many passages we give the model (k). Instead of guessing, we
try 3 chunk sizes x 3 values of k and count, for each, how many of the 27
answerable questions get their evidence retrieved. The result (decision
0003): 300 tokens and k = 3 find all 27, with fewer tokens than 500.
"""
import csv

from src.data import ROOT
from src.retrieve import Index, build_passages, embedder

# Collapse whitespace so a phrase compares equal whatever its line breaks (as in evals/run.py).
norm = lambda s: " ".join(s.split())


def main():
    """Print one table line per chunk size: number of passages, evidence found at k=1, 3, 5,
    the average prompt size at k=3, and which questions were missed at k=3."""
    # Only the questions the help centre answers have evidence to find.
    qs = [q for q in csv.DictReader((ROOT / "evals" / "test_questions.csv").open(encoding="utf-8"))
          if q["answerable"] == "yes"]
    tok = embedder().tokenizer
    print(f"{len(qs)} answerable questions | evidence found in the top k passages")
    print(f"{'chunk tokens':>12} {'passages':>9} {'k=1':>6} {'k=3':>6} {'k=5':>6} {'prompt tokens at k=3':>22}  missed at k=3")
    for size in (150, 300, 500):
        # Re-cut the documents at this size and build a fresh index.
        passages = build_passages(size)
        index = Index(passages)
        found = {}
        for k in (1, 3, 5):
            # The ids of the questions whose evidence is in one of the k passages retrieved.
            found[k] = [q["case_id"] for q in qs
                        if any(q["evidence"] in norm(p["text"]) for p in index.search(q["question"], k))]
        # Average passage length in tokens; 3 x that = the size of the passages block at k=3.
        avg = sum(len(tok(p["text"], add_special_tokens=False)["input_ids"]) for p in passages) / len(passages)
        missed = [q["case_id"] for q in qs if q["case_id"] not in found[3]]
        # :>6 right-aligns a value in 6 characters, to print a neat table.
        print(f"{size:>12} {len(passages):>9} {len(found[1]):>6} {len(found[3]):>6} {len(found[5]):>6} "
              f"{3 * avg:>22.0f}  {' '.join(missed)}")


if __name__ == "__main__":
    main()
