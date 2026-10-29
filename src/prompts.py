"""Prompt files: prompts/<name>.md, with a '## System' and a '## User' section.

The user section is a template with placeholders: {question}, and the passages {policy} and {seller}. Keeping prompts
in files, not in code, means every figure names the exact prompt that made it.

For beginners
-------------
A call to Claude has two kinds of text:
- the SYSTEM prompt: the standing instructions ("you are the help-centre
  assistant of Albert's Marketplace; answer only from the passages...");
- the USER message: what changes at every call (the customer's question and
  the passages retrieved for it).

Each prompt file in prompts/ holds both, under two headings. The user part
contains placeholders in curly braces, like {question}, that this module
replaces with the real text before the call.
"""
# dataclass: a shortcut to write a small class that just holds a few named values.
from dataclasses import dataclass
from pathlib import Path

# The prompts/ folder, at the root of the repository.
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    """One prompt, as read from prompts/<name>.md.

    frozen=True makes it read-only: a prompt cannot be modified by accident
    once loaded, so the text sent is always the text in the file.
    """
    name: str       # the file name without .md, e.g. "answer_few_shot_v1"; logged with every call
    system: str     # the text under "## System"
    user: str       # the text under "## User", with its {placeholders} still in it

    def user_message(self, ticket_text=None, **fields):
        """The user section with its placeholders filled: {question}, {policy}, {seller}.

        Example:
            prompt.user_message(question="Can I pay by bank transfer?", policy="[03-payments#0] ...", seller="(none)")

        `**fields` collects every keyword argument into a dictionary
        {"question": ..., "policy": ..., "seller": ...}. `ticket_text` is unused
        (kept from the course template).
        """
        text = self.user
        for k, v in fields.items():
            # Replace "{question}" by the question, "{policy}" by the policy passages, etc.
            text = text.replace("{" + k + "}", v)
        return text


def load_prompt(name):
    """Read prompts/<name>.md and split it into its system and user parts.

    The file must contain a line "## System" followed later by a line "## User".
    Anything before "## System" (a title, notes for the team) is ignored.
    """
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    # split(..., 1) cuts the text in two at the first occurrence. `_` holds the part before
    # "## System", which we do not need.
    _, rest = text.split("\n## System\n", 1)
    system, user = rest.split("\n## User\n", 1)
    # .strip() removes the blank lines around each part.
    return Prompt(name, system.strip(), user.strip())
