"""Query rewriting (FinSage MPR): split the user question into self-contained sub-questions.

Adapted from the rewrite prompt in the official FinSage repository (src/prompts/qa.py), which
splits the query, resolves pronouns with the chat history and defaults to the company in scope.
"""

from __future__ import annotations

import json
import re

from finsage_replica.ports.llm import LanguageModel

MAX_SUBQUESTIONS = 4

INSTRUCTIONS = (
    "You rewrite questions about a company's SEC filing for a search engine. Split the user's question into "
    "self-contained sub-questions in English. Each sub-question must name the company and the fiscal period "
    "explicitly, replace pronouns with the subject they refer to, and use the conversation history to fill in "
    "missing context. If the question asks for one thing, return exactly one sub-question. "
    f"Return at most {MAX_SUBQUESTIONS}. Answer with a JSON array of strings and nothing else."
)


def parse_subquestions(text: str, fallback: str) -> list[str]:
    """JSON array of strings from the model, tolerating code fences. Falls back to the original question."""
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    try:
        items = json.loads(match.group(0)) if match else []
    except json.JSONDecodeError:
        items = []
    seen: list[str] = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, str) and item.strip() and item.strip() not in seen:
            seen.append(item.strip())
    return seen[:MAX_SUBQUESTIONS] or [fallback]


def rewrite_question(llm: LanguageModel, question: str, company: str, doc_title: str,
                     history: list[tuple[str, str]] | None = None):
    """Sub-questions plus the completion (for cost accounting)."""
    turns = "\n".join(f"{role}: {text}" for role, text in (history or [])) or "(no previous turns)"
    prompt = (f"Company in scope: {company}\nDocument: {doc_title}\n\nConversation history:\n{turns}\n\n"
              f"User question: {question}")
    completion = llm.complete(INSTRUCTIONS, prompt, max_output_tokens=400)
    return parse_subquestions(completion.text, fallback=question), completion
