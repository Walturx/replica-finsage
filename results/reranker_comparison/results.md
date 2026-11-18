# Reranker comparison on AMD_2022_10K

Same candidates for both rerankers (full FinSage retrieval). Rank = position of the first chunk on an evidence page after reranking (1 is best).

| Reranker | Evidence kept in top 5 | Mean precision@5 |
|---|---|---|
| bge-reranker-v2-m3 (generic cross-encoder) | 4/7 | 0.21 |
| gpt-6-luna (LLM grader) | 7/7 | 0.30 |

| Question | Evidence pages | Rank, bge-reranker-v2-m3 | Rank, gpt-6-luna |
|---|---|---|---|
| Does AMD have a reasonably healthy liquidity profile based o | 56 | 32 | 1 |
| What are the major products and services that AMD sells as o | 4 | 16 | 2 |
| What drove revenue change as of the FY22 for AMD? | 43 | 2 | 1 |
| What drove operating margin change as of the FY22 for AMD? I | 43 | 1 | 3 |
| Among operations, investing, and financing activities, which | 58 | 5 | 5 |
| From FY21 to FY22, excluding Embedded, in which AMD reportin | 48 | 5 | 2 |
| Did AMD report customer concentration in FY22? | 12 | 6 | 1 |

LLM reranker cost: US$0.0067. Pages are 1-based.
