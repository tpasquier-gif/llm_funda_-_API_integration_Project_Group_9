"""Chunking, the index and the search (step 3).

- read: pypdf, line breaks inside sentences joined, paragraphs kept;
- chunk: whole sentences, packed up to `size` tokens counted with the embedding
  model's own tokenizer, because a passage longer than what the model reads
  (512 tokens for multilingual-e5-small) is silently cut before it is embedded;
- embed: intfloat/multilingual-e5-small (384 dimensions, multilingual: our
  customers write in English, French and German), with the "passage: " and
  "query: " prefixes e5 was trained with;
- index: FAISS IndexFlatIP on normalised vectors (inner product = cosine),
  exact search, which at ~100 passages costs nothing.

Every passage keeps its document in its id (`02-delivery#3`), so a citation
says where a fact comes from, and the document says whether the text is the
company's own (01-04) or written by sellers (05 product pages, 06 catalogue
attributes "as the sellers entered them"): untrusted.

For beginners — the "R" of RAG (Retrieval-Augmented Generation)
-----------------------------------------------------------------
The language model has never read our help centre, and we cannot paste all
of it into every question (too long, too expensive). So, before asking the
model, we RETRIEVE the few passages that matter for the question:

1. CHUNK: cut each PDF into small passages ("chunks") of whole sentences.
2. EMBED: turn every passage into an *embedding*: a list of 384 numbers that
   captures its meaning. Two texts about the same thing get similar numbers,
   even in different languages ("return window" ~ "délai de retour").
3. INDEX: store all those vectors in FAISS, a library built to find the
   closest vectors very fast.
4. SEARCH: embed the customer's question the same way, and ask FAISS for the
   3 passages whose vectors are closest to it (TOP_K = 3).

Those 3 passages are then given to the model (src/llm.py), which must answer
from them and cite them.
"""
import os
# re: regular expressions, a mini-language to find patterns in text.
import re
# lru_cache: remembers the result of a function so it is computed only once.
from functools import lru_cache

# numpy: the standard library for arrays of numbers (our vectors).
import numpy as np
# PdfReader: reads the text out of a PDF file.
from pypdf import PdfReader

from src.data import corpus_files

# Hugging Face's Xet transfer failed on our network; the plain HTTP download works.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
# PyTorch and FAISS each bring an OpenMP runtime; on macOS two of them in one process crash it
# (exit 139). One thread each avoids it, and at ~100 passages costs nothing measurable.
os.environ.setdefault("OMP_NUM_THREADS", "1")

# The embedding model: small (runs on a laptop CPU), multilingual, ~470 MB, from Hugging Face.
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
# The model reads at most 512 tokens; anything longer would be silently cut off.
MODEL_MAX_TOKENS = 512
# Our chunk size, in tokens. Chosen by measurement (evals/retrieval_sweep.py, decision 0003):
# 150 missed one piece of evidence, 300 and 500 found all 27, and 300 is cheaper than 500.
CHUNK_TOKENS = 300          # chosen on the 30 test questions' evidence, decision 0003
# How many passages we give the model for each question.
TOP_K = 3
# Document name prefixes written by SELLERS, not by the company: we never trust them for policies.
SELLER_DOCS = ("05-", "06-")


def load_pdf(path):
    """Read a PDF and return its text as one string, with sentences put back on one line.

    PDFs break lines in the middle of sentences ("You can return an item\\nwithin
    21 days"). We join those single line breaks with a space, but keep double
    line breaks, which separate paragraphs.
    """
    # Read every page's text and join pages with a blank line.
    # `page.extract_text() or ""` uses "" when a page has no text (an image, say).
    text = "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    # Regular expression: a "\n" that is NOT preceded by "\n" and NOT followed by "\n",
    # i.e. a single line break, is replaced by a space. Double breaks are untouched.
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


def chunk(name, text, tokenizer, size=CHUNK_TOKENS):
    """Whole sentences packed into passages of at most `size` tokens (a longer sentence stands alone).

    Arguments:
        name:      the document name, e.g. "02-delivery"; it becomes the start of each passage id.
        text:      the document's full text (from load_pdf).
        tokenizer: the embedding model's tokenizer, used to COUNT tokens exactly as the model will.
        size:      the maximum number of tokens per passage (300 by default).

    Returns a list of passages, each a dictionary:
        {"id": "02-delivery#0", "text": "..."}, {"id": "02-delivery#1", "text": "..."}, ...

    Why whole sentences? A rule cut in half ("A parcel is late if..." / "...2 days
    after...") would be found by neither half. Packing whole sentences keeps
    every rule readable inside one passage.
    """
    # A small function stored in a variable (a "lambda"): how many tokens does sentence s have?
    count = lambda s: len(tokenizer(s, add_special_tokens=False)["input_ids"])
    # Split the text into sentences: after ".", "!", "?" or ":" followed by spaces, when the
    # next character starts a new sentence (a capital, a digit, a quote, "(" or "€").
    sentences = [s.strip() for s in re.split(r"(?<=[.!?:])\s+(?=[A-Z0-9\"(€])", text) if s.strip()]
    # passages: finished passages; current: sentences of the passage being filled; n: its token count.
    passages, current, n = [], [], 0
    for s in sentences:
        k = count(s)
        # If adding this sentence would overflow the passage, close the passage first.
        if current and n + k > size:
            passages.append(" ".join(current))
            current, n = [], 0
        current.append(s)
        n += k
    # Do not forget the last, partly filled passage.
    if current:
        passages.append(" ".join(current))
    # enumerate() numbers the passages 0, 1, 2...; the id is "<document>#<number>".
    return [{"id": f"{name}#{i}", "text": p} for i, p in enumerate(passages)]


def is_untrusted(passage):
    """True when the passage was written by a seller (documents 05 and 06), not by the company.

    Seller text may be wrong, or even malicious (the injection test): it is used
    for product facts only, never for policies, and it is cleaned before use.
    """
    return passage["id"].startswith(SELLER_DOCS)


@lru_cache
def embedder():
    """Load the embedding model once (it takes a few seconds) and reuse it afterwards.

    @lru_cache means: the first call loads the model; every later call returns
    the same, already loaded model instantly.
    """
    # Imported here, not at the top, so that the rest of the package (and the
    # tests) can be used without loading this heavy library.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


class Index:
    """A searchable collection of passages: the vectors of every passage, stored in FAISS.

    Usage:
        index = Index(passages)
        index.search("How many days do I have to return an item?")   # -> the 3 closest passages
    """

    def __init__(self, passages, model=None):
        """Embed every passage and store the vectors in a FAISS index.

        `model` can be given (the retrieval sweep reuses one); by default the
        shared embedding model is loaded.
        """
        self.passages = passages
        self.model = model or embedder()
        # e5 was trained with the prefix "passage: " in front of documents. normalize_embeddings=True
        # gives every vector a length of 1, so that the inner product of two vectors is their
        # cosine similarity (1 = same meaning, 0 = unrelated).
        vectors = self.model.encode(["passage: " + p["text"] for p in passages], normalize_embeddings=True)
        import faiss                    # after torch has loaded its OpenMP runtime: see the top of the file
        faiss.omp_set_num_threads(1)
        # IndexFlatIP = an exact index ("Flat": compares the question with EVERY passage) using
        # the Inner Product. With ~60 passages this is instantaneous, and never misses a match.
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        # FAISS wants 32-bit floating-point numbers.
        self.index.add(np.asarray(vectors, dtype="float32"))

    def search(self, question, k=TOP_K):
        """Return the k passages closest in meaning to the question, best first.

        Each returned passage is the original dictionary plus a "score" (the
        cosine similarity: higher means closer).
        """
        # The question gets the prefix "query: ", as e5 was trained.
        q = self.model.encode(["query: " + question], normalize_embeddings=True)
        # FAISS returns two arrays: the similarity scores and the positions of the k best passages.
        scores, ids = self.index.search(np.asarray(q, dtype="float32"), k)
        # zip() walks the two arrays side by side. `**self.passages[i]` copies the passage's
        # fields into a new dictionary, to which we add the score. i is -1 when FAISS found
        # fewer than k passages, so those are skipped.
        return [{**self.passages[i], "score": float(s)} for s, i in zip(scores[0], ids[0]) if i >= 0]


def build_passages(size=CHUNK_TOKENS, injected=False):
    """Read every PDF of the help centre and cut it into passages (all documents together).

    With injected=True, the tampered product page is used instead of the real
    one (the injection test). Returns the list of passages (60 with size=300).
    """
    tok = embedder().tokenizer
    out = []
    for f in corpus_files(injected=injected):
        # f.stem is the file name without ".pdf", e.g. "02-delivery". The tampered page keeps
        # the real page's name, so citations look the same in both settings.
        out += chunk(f.stem.replace("-injected", ""), load_pdf(f), tok, size)
    return out


@lru_cache
def default_index(size=CHUNK_TOKENS, injected=False):
    """The index used by the evaluation scripts, built once per (size, injected) and then reused."""
    return Index(build_passages(size, injected))
