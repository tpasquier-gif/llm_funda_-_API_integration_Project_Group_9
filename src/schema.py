"""What the assistant returns to a customer, and the rules a JSON schema cannot express.

The API enforces the shape (structured outputs); this module enforces what
makes an answer safe to send, with error messages written for the model,
because each one becomes the text of a re-prompt (src/llm.py):
- every citation is a passage the assistant was actually given;
- an answer that claims to be answerable cites at least one passage; one that
  says it cannot answer cites none;
- the output check: no link, e-mail address or phone number reaches a
  customer, except the one contact the company publishes.

For beginners
-------------
We do not let the model answer in free text. We ask it for a small JSON
record with three fields:

    {"answer": "You can return an item within 21 days...",
     "answerable": true,
     "citations": ["01-returns-and-refunds#0"]}

`pydantic` (a Python library) describes that record as a class and checks it.
- The SHAPE (three fields, the right types) is guaranteed by the API itself
  ("structured outputs").
- The MEANING (are the citations real? is there a phone number that should
  not be there?) is checked here, by "validators": small functions that raise
  an error when a rule is broken. Each error message is written to the model,
  because src/llm.py sends it back as "Your answer broke a rule: ...".
"""
import re

# BaseModel: the pydantic base class for a checked record. Field: adds a description to a field
# (the description is sent to the model, inside the JSON schema, to tell it what to write).
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

# The only contact the help centre publishes: the data protection officer's e-mail address.
PUBLISHED_CONTACTS = {"privacy@albertsmarketplace.example"}

# Regular expressions that find contacts in a text:
# an e-mail address (something@something.something),
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# a link (http://..., www...., or a bare domain ending in .com, .net, .org, .io, .shop, .example),
LINK = re.compile(r"https?://\S+|www\.\S+|\b[\w-]+\.(?:com|net|org|io|shop|example)(?:/\S*)?\b", re.I)
# and a phone number (a digit, then at least 7 digits/spaces/brackets/dots/dashes, ending with a digit).
PHONE = re.compile(r"\+?\d[\d ()./-]{7,}\d")


def output_check(text):
    """The contacts and links in text that the company does not publish: what must never reach a customer.

    Returns a sorted list of the forbidden contacts found (an empty list means
    the text is safe). Example:
        output_check("Email returns@ozglow-direct.example") -> ["returns@ozglow-direct.example"]

    This is our defence against a seller page that tries to make the assistant
    send customers to the seller's own e-mail address (the injection test).
    """
    # Candidate phone numbers; a real phone number has at least 9 digits, which rules out
    # dates (2026-10-22) and amounts (€1,330.26).
    phones = {p for p in PHONE.findall(text) if sum(c.isdigit() for c in p) >= 9}   # not a date or an amount
    # Every e-mail, link and phone number found ("|" joins Python sets).
    found = set(EMAIL.findall(text)) | {m.group(0) for m in LINK.finditer(text)} | phones
    # What is allowed: the published address, and its domain (albertsmarketplace.example).
    allowed = PUBLISHED_CONTACTS | {c.split("@", 1)[1] for c in PUBLISHED_CONTACTS}
    # Keep only what is NOT allowed. strip(".,;") ignores punctuation glued to the end of a match.
    return sorted(f for f in found if f.strip(".,;") not in allowed and not any(f in a for a in allowed))


# The record the assistant must return (its shape only; the rules are in _Rules below).
# NOTE: no docstring on these classes on purpose. pydantic copies a class docstring into the JSON
# schema sent to the model, so adding one would change every request (and the cached answers).
class Answer(BaseModel):
    answer: str = Field(description="the reply to the customer, in the customer's language")
    answerable: bool = Field(description="false when the passages do not contain the answer")
    citations: list[str] = Field(description="the ids of the passages the answer uses")


# The model writes the fields in order, so putting `reasoning` first makes it "think" before it
# answers. The customer never sees the reasoning. (The docstring below IS sent to the model.)
class AnswerWithReasoning(BaseModel):
    """Chain-of-thought: the reasoning comes first, so it is written before the answer."""
    reasoning: str = Field(description="which passages answer the question and what they say, in two to four sentences")
    answer: str = Field(description="the reply to the customer, in the customer's language")
    answerable: bool = Field(description="false when the passages do not contain the answer")
    citations: list[str] = Field(description="the ids of the passages the answer uses")


# The safety rules, written once and shared by both answer shapes (see the two classes below).
# A "validator" is a method that pydantic calls automatically when a record is loaded. It returns
# the value if it is fine, or raises ValueError with a message; that message is what the model
# reads in its re-prompt. (Comments, not a docstring: a docstring here would be inherited by
# CheckedAnswer and sent to the model inside its schema.)
class _Rules:

    @field_validator("answer")
    @classmethod
    def answer_is_safe(cls, v):
        """Rule: the answer is not empty, and contains no contact the company does not publish."""
        if not v.strip():
            raise ValueError("answer is empty: write the reply to the customer")
        bad = output_check(v)
        if bad:
            raise ValueError(f"the answer contains {bad}: never give a link, an e-mail address or a phone number "
                             "that Albert's Marketplace does not publish; tell the customer to use their order page")
        return v

    @field_validator("citations")
    @classmethod
    def citations_were_retrieved(cls, v, info: ValidationInfo):
        """Rule: every cited id is one of the passages actually given to the model.

        The allowed ids are passed in by src/llm.py through the validation
        "context" ({"passage_ids": [...]}). This is the rule that caught the
        invented citation 02-delivery#5 in step 3.
        """
        allowed = (info.context or {}).get("passage_ids")
        # No context given (e.g. a test that loads a record directly): nothing to compare with.
        if allowed is not None:
            # Set difference: the citations that are not in the allowed list.
            invented = sorted(set(v) - set(allowed))
            if invented:
                raise ValueError(f"citations {invented} were not among the passages you were given: cite only "
                                 f"these ids: {', '.join(allowed)}")
        return v

    @model_validator(mode="after")
    def citations_match_answerable(self):
        """Rule: "answerable" and the citations must agree.

        - answerable=True  -> at least one citation (an answer must say where it comes from);
        - answerable=False -> no citation (an "I don't know" cannot cite a source).
        mode="after" means this runs once all fields are loaded, so it can compare two of them.
        """
        if self.answerable and not self.citations:
            raise ValueError("answerable is true but no passage is cited: cite the passages the answer comes from, "
                             "or set answerable to false")
        if not self.answerable and self.citations:
            raise ValueError("answerable is false but passages are cited: if a passage answers, set answerable to "
                             "true; otherwise cite nothing")
        return self


# The answer shape (Answer) + the safety rules (_Rules): what zero-shot and few-shot return.
# Python "multiple inheritance": the class gets the fields of Answer and the validators of _Rules.
class CheckedAnswer(_Rules, Answer):
    pass


# The chain-of-thought shape + the same safety rules: what the chain-of-thought prompt returns.
class CheckedAnswerWithReasoning(_Rules, AnswerWithReasoning):
    pass


# No citations here: in step 2 the model has no passages to cite. (The docstring is sent to the model.)
class ClosedBookAnswer(BaseModel):
    """Step 2, before retrieval: the model alone, asked to say when it does not know."""
    answer: str = Field(description="the reply to the customer")
    answerable: bool = Field(description="false if you do not know Albert's Marketplace's own policy for this")
