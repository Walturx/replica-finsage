"""HyDE path (FinSage MPR): search with a hypothetical answer instead of the question.

The paper fine-tunes Qwen-2.5-7B for this. The replica prompts the configured generator without
fine-tuning, because the paper's training data was not released (declared limitation).
"""

from __future__ import annotations

from finsage_replica.ports.llm import Completion, LanguageModel

INSTRUCTIONS = (
    "Write a short passage of two to four sentences that could appear in the company's SEC filing and that answers "
    "the question. Imitate the wording of an annual report. If you do not know the exact figures, write plausible "
    "ones: the passage is only used to find similar text in the real document. Plain text only."
)


# Reasoning models spend part of the output budget thinking before they write; 300 tokens left
# 4 of 7 passages empty with gpt-6-luna, so the budget leaves room for both.
MAX_OUTPUT_TOKENS = 1500


def hypothetical_document(llm: LanguageModel, subquestion: str, company: str, doc_title: str) -> Completion:
    prompt = f"Company: {company}\nDocument: {doc_title}\n\nQuestion: {subquestion}"
    return llm.complete(INSTRUCTIONS, prompt, max_output_tokens=MAX_OUTPUT_TOKENS)
