import json

from finsage_replica.ffp.summaries import group_sections, summarize_sections
from finsage_replica.ports.llm import Completion


def words(text: str) -> int:
    return len(text.split())


def _chunk(i: int, section: str, page: int, text: str) -> dict:
    return {"chunk_id": f"DOC:{page}:{i}", "doc_name": "DOC", "page_index": page, "section": section,
            "text": text, "n_tokens": words(text), "also_on_pages": []}


class FakeLLM:
    model = "fake-llm"

    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, instructions: str, prompt: str, max_output_tokens: int = 512) -> Completion:
        self.prompts.append(prompt)
        return Completion(text=f"summary {len(self.prompts)}", tokens_in=words(prompt), tokens_out=2,
                          model=self.model, cost_usd=0.01)


LONG = " ".join(f"w{i}" for i in range(60))


def test_sections_are_consecutive_runs_of_the_same_heading():
    chunks = [_chunk(0, "Revenue", 3, "a"), _chunk(1, "Revenue", 4, "b"), _chunk(2, "Risks", 5, "c"),
              _chunk(3, "Revenue", 9, "d")]

    groups = group_sections(chunks)

    assert [(g.section_id, g.section, g.chunk_ids, g.first_page, g.last_page) for g in groups] == [
        ("DOC:s0", "Revenue", ["DOC:3:0", "DOC:4:1"], 3, 4),
        ("DOC:s1", "Risks", ["DOC:5:2"], 5, 5),
        ("DOC:s2", "Revenue", ["DOC:9:3"], 9, 9),
    ]
    assert groups[0].text == "a\n\nb"


def test_each_section_gets_one_summary_record_and_tiny_sections_reuse_their_heading(tmp_path):
    chunks = [_chunk(0, "Revenue", 3, LONG), _chunk(1, "Signatures", 7, "John Doe")]
    llm = FakeLLM()
    out = tmp_path / "summaries.jsonl"

    stats = summarize_sections(group_sections(chunks), llm, company="AMD", doc_title="AMD 2022 10K",
                               out_path=out, count_tokens=words, max_input_tokens=1000, min_tokens=40)

    records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [(r["section_id"], r["summary"], r["source"]) for r in records] == [
        ("DOC:s0", "summary 1", "llm"),
        ("DOC:s1", "Signatures", "heading"),
    ]
    assert records[0]["chunk_ids"] == ["DOC:3:0"]
    assert len(llm.prompts) == 1
    assert "AMD" in llm.prompts[0] and "Revenue" in llm.prompts[0] and "AMD 2022 10K" in llm.prompts[0]
    assert stats.llm_calls == 1 and stats.from_heading == 1 and stats.cached == 0
    assert stats.cost_usd == 0.01


def test_long_sections_are_truncated_to_the_input_budget(tmp_path):
    big = " ".join(f"x{i}" for i in range(500))
    llm = FakeLLM()

    summarize_sections(group_sections([_chunk(0, "Notes", 1, big)]), llm, company="AMD", doc_title="T",
                       out_path=tmp_path / "s.jsonl", count_tokens=words, max_input_tokens=100, min_tokens=40)

    section_text = llm.prompts[0].split("Section text:\n", 1)[1]
    assert words(section_text) <= 100
    assert section_text.startswith("x0 x1")


def test_rerun_skips_sections_already_summarized(tmp_path):
    chunks = [_chunk(0, "Revenue", 3, LONG), _chunk(1, "Risks", 4, LONG)]
    out = tmp_path / "s.jsonl"
    kwargs = dict(company="AMD", doc_title="T", out_path=out, count_tokens=words, max_input_tokens=1000, min_tokens=40)
    summarize_sections(group_sections(chunks), FakeLLM(), **kwargs)

    second = FakeLLM()
    stats = summarize_sections(group_sections(chunks), second, **kwargs)

    assert second.prompts == []
    assert stats.cached == 2 and stats.llm_calls == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2
