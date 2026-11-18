# Experiment A on AMD_2022_10K

Evidence-page recall: share of questions where a retrieved chunk covers an evidence page.

| Configuration | Recall | Hits | Precision | Avg retrieved |
|---|---|---|---|---|
| Dense (FAISS) | 0.71 | 5/7 | 0.133 | 10.4 |
| Dense + Expansion | 0.71 | 5/7 | 0.123 | 11.3 |
| Dense + BM25 | 0.86 | 6/7 | 0.096 | 19.1 |
| Dense + BM25 + Metadata | 0.86 | 6/7 | 0.088 | 22.0 |
| Dense + HyDE | 1.00 | 7/7 | 0.163 | 16.7 |
| FinSage (all paths + Expansion) | 1.00 | 7/7 | 0.096 | 33.7 |

Which path alone reached an evidence page (full configuration):

| Question | dense | bm25 | metadata | hyde |
|---|---|---|---|---|
| Does AMD have a reasonably healthy liquidity profile based on its quic | no | no | no | yes |
| What are the major products and services that AMD sells as of FY22? | yes | no | no | yes |
| What drove revenue change as of the FY22 for AMD? | yes | no | no | yes |
| What drove operating margin change as of the FY22 for AMD? If operatin | yes | yes | no | yes |
| Among operations, investing, and financing activities, which brought i | no | yes | no | yes |
| From FY21 to FY22, excluding Embedded, in which AMD reporting segment  | yes | yes | no | yes |
| Did AMD report customer concentration in FY22? | yes | no | yes | yes |

LLM cost for rewriting and HyDE: US$0.0021 (gpt-6-luna).
