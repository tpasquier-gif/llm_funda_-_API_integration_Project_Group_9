"""The company's help centre: six PDFs from release policy-corpus-v1.0.0, checked against their sha256.

Not committed (data/ is in .gitignore): downloaded once into data/policy-corpus/
and refused if any file differs from the release's CHECKSUMS, so every figure
in docs/ is tied to one version of the documents (the policies say "Version
1.0, effective 1 September 2026"; the product pages are an extract of
1 October 2026).

The course's injected product page (one seller's page with instructions
hidden in it, lesson 3) is fetched the same way, for the injection test only.

For beginners — what this file does, in plain words
---------------------------------------------------
A RAG system answers from documents, so the very first step is to *get* the
documents. This file:

1. downloads the six PDF files of the help centre from the course's GitHub
   release (only the first time: afterwards they are already on disk);
2. checks each file with a SHA-256 "fingerprint" (see `sha256` below), so we
   are sure we are working on exactly the same documents as the course, not
   a corrupted or modified copy;
3. for the injection test only, swaps one PDF for a tampered version that
   contains hidden instructions (an attack we must resist).
"""
# hashlib: Python's standard library for cryptographic fingerprints (SHA-256 here).
import hashlib
# urllib.request: Python's built-in way to download a file from a URL.
import urllib.request
# Path: an object for file paths that works the same on Mac, Windows and Linux.
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants: values that never change while the program runs.
# By convention, Python constants are written in CAPITAL LETTERS.
# ---------------------------------------------------------------------------

# ROOT is the repository's top folder. __file__ is the path of THIS file
# (src/data.py); .resolve() makes it absolute; .parent goes up one folder
# (to src/), and .parent again goes up to the repository root.
ROOT = Path(__file__).resolve().parent.parent

# Where the six PDFs are stored once downloaded. The "/" operator joins paths.
CORPUS = ROOT / "data" / "policy-corpus"

# The base URL of the course's GitHub release; a file name is appended to it.
# (Two strings side by side inside parentheses are glued together by Python.)
RELEASE = ("https://github.com/TangoAI-AlbertSchool-Data-Eng-Cloud/albert-marketplace"
           "/releases/download/policy-corpus-v1.0.0/")

# The version name, quoted in error messages and next to every figure.
VERSION = "policy-corpus-v1.0.0"

# The tampered product page used by the injection test (lesson 3), where it is
# saved, where it is downloaded from, and the fingerprint it must have.
INJECTED = ROOT / "data" / "05-product-pages-injected.pdf"
INJECTED_URL = ("https://raw.githubusercontent.com/TangoAI-AlbertSchool-Data-Eng-Cloud"
                "/llm-course-labs/main/l03-rag/data/05-product-pages-injected.pdf")
INJECTED_SHA256 = "4cd2b1ee432762d74c08b47454a8a04d8ef56c7f760b19788c1011ff1aec69d1"


def sha256(path):
    """Return the SHA-256 fingerprint of a file, as a 64-character hexadecimal string.

    A fingerprint (or "hash") is computed from every byte of the file. Change a
    single byte and the fingerprint is completely different. Comparing it with
    the fingerprint published by the course therefore proves we have exactly
    the right file.

    Example: sha256("data/policy-corpus/02-delivery.pdf") -> "3c6bd6810dd4...".
    """
    # read_bytes() loads the whole file as raw bytes; hexdigest() writes the
    # fingerprint as readable hexadecimal characters (0-9, a-f).
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def corpus_files(injected=False):
    """The six PDFs, sorted, downloaded and checked. With injected=True, the course's tampered
    product page replaces 05-product-pages.pdf (the injection test).

    Returns a list of Path objects, one per PDF, in alphabetical order
    (01-returns-and-refunds.pdf, 02-delivery.pdf, ...).

    Raises RuntimeError if a file on disk is not the released one: delete it
    and run again, it will be downloaded afresh.
    """
    # Create data/policy-corpus/ if it does not exist yet. parents=True also
    # creates data/; exist_ok=True means "no error if it already exists".
    CORPUS.mkdir(parents=True, exist_ok=True)

    # CHECKSUMS is a small text file published with the release. Each line is
    # "<fingerprint>  <file name>". We download it once.
    sums_path = CORPUS / "CHECKSUMS"
    if not sums_path.exists():
        urllib.request.urlretrieve(RELEASE + "CHECKSUMS", sums_path)

    # Turn the CHECKSUMS lines into a dictionary {file name: fingerprint}.
    # line.split() gives [fingerprint, name]; reversed(...) gives (name, fingerprint);
    # dict(...) builds the dictionary. Empty lines are skipped by `if line.strip()`.
    sums = dict(reversed(line.split()) for line in sums_path.read_text().splitlines() if line.strip())

    files = []
    # sorted(...) walks the files in alphabetical order, so 01 comes before 02, etc.
    for name, digest in sorted(sums.items()):
        # CHECKSUMS may list other files; we only want the PDFs.
        if not name.endswith(".pdf"):
            continue
        path = CORPUS / name
        # Download the PDF only if it is not already on disk.
        if not path.exists():
            urllib.request.urlretrieve(RELEASE + name, path)
        # The safety check: the file's fingerprint must match the published one.
        if sha256(path) != digest:
            raise RuntimeError(f"{path} is not the file of {VERSION}: delete it and run again")
        files.append(path)

    # The injection test: replace the real product pages with the tampered ones.
    if injected:
        if not INJECTED.exists():
            urllib.request.urlretrieve(INJECTED_URL, INJECTED)
        if sha256(INJECTED) != INJECTED_SHA256:
            raise RuntimeError(f"{INJECTED} is not the course's file")
        # A "list comprehension": a new list where the file starting with "05-"
        # is replaced by the tampered one, and every other file is kept as is.
        files = [INJECTED if f.name.startswith("05-") else f for f in files]
    return files


def corpus_digest():
    """One short fingerprint of the six released files, quoted next to every figure.

    It is the fingerprint of the CHECKSUMS file itself (which lists the six
    fingerprints), cut to 12 characters. If any document ever changed, this
    short code would change too, so a figure in docs/ always says which
    version of the documents produced it.
    """
    # Make sure the files are present and checked before quoting their version.
    corpus_files()
    # [:12] keeps the first 12 characters: short enough to print, long enough to be unique.
    return hashlib.sha256((CORPUS / "CHECKSUMS").read_bytes()).hexdigest()[:12]
