from finsage_replica.ffp.chunking import Page, chunk_pages


def words(text: str) -> int:
    """Deterministic token counter for tests: one token per whitespace-separated word."""
    return len(text.split())


def test_chunks_respect_the_token_limit():
    paragraphs = "\n\n".join(" ".join(f"w{i}_{j}" for j in range(30)) for i in range(10))
    chunks = chunk_pages("DOC", [Page(0, paragraphs)], max_tokens=50, count_tokens=words)

    assert len(chunks) > 1
    assert all(words(c.text) <= 50 for c in chunks)


def test_oversized_paragraph_is_split_by_tokens():
    long_paragraph = " ".join(f"w{j}" for j in range(120))
    chunks = chunk_pages("DOC", [Page(0, long_paragraph)], max_tokens=50, count_tokens=words)

    assert [words(c.text) for c in chunks] == [50, 50, 20]


def test_chunks_never_cross_pages_and_keep_zero_based_page_index():
    pages = [Page(0, "alpha beta"), Page(1, "gamma delta")]
    chunks = chunk_pages("DOC", pages, max_tokens=50, count_tokens=words)

    assert [(c.page_index, c.text) for c in chunks] == [(0, "alpha beta"), (1, "gamma delta")]


def test_section_comes_from_the_latest_heading_and_carries_across_pages():
    pages = [
        Page(0, "# **Item 7. Management's Discussion**\n\nrevenue grew"),
        Page(1, "margins improved"),
        Page(2, "## Cash Flows\n\ncapex was 1,577"),
    ]
    chunks = chunk_pages("DOC", pages, max_tokens=50, count_tokens=words)

    assert [c.section for c in chunks] == [
        "Item 7. Management's Discussion",
        "Item 7. Management's Discussion",
        "Cash Flows",
    ]


def test_large_table_is_split_by_rows_repeating_its_header():
    header = "|(Millions)|2018|2017|\n|---|---|---|"
    rows = "\n".join(f"|line item {i}|{i}|{i}|" for i in range(40))
    chunks = chunk_pages("DOC", [Page(0, f"{header}\n{rows}")], max_tokens=40, count_tokens=words)

    assert len(chunks) > 1
    assert all(c.text.startswith(header) for c in chunks)
    assert all(words(c.text) <= 40 for c in chunks)
    body_rows = [line for c in chunks for line in c.text.splitlines()[2:]]
    assert body_rows == rows.splitlines()


def test_chunk_ids_are_unique_and_follow_reading_order():
    pages = [Page(0, "a b c\n\nd e f"), Page(3, "g h i")]
    chunks = chunk_pages("DOC", pages, max_tokens=3, count_tokens=words)

    assert [c.chunk_id for c in chunks] == ["DOC:0:0", "DOC:0:1", "DOC:3:0"]
    assert all(c.doc_name == "DOC" for c in chunks)


def test_blank_pages_produce_no_chunks():
    chunks = chunk_pages("DOC", [Page(0, "   \n\n "), Page(1, "text")], max_tokens=50, count_tokens=words)

    assert [c.page_index for c in chunks] == [1]
