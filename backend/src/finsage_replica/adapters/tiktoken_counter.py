"""TokenCounter adapter backed by tiktoken."""

from __future__ import annotations

DEFAULT_ENCODING = "o200k_base"  # GPT-5.x / GPT-6 tokenizer. The paper does not name its tokenizer.


class TiktokenCounter:
    def __init__(self, encoding: str = DEFAULT_ENCODING):
        import tiktoken

        self.encoding = encoding
        self._encoder = tiktoken.get_encoding(encoding)

    def __call__(self, text: str) -> int:
        return len(self._encoder.encode(text, disallowed_special=()))
