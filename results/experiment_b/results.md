# Experiment B: FinSage replica vs naive dense RAG (AMD_2022_10K)

Generator gpt-6-luna for both systems. Judge claude-opus-5-5 (different model family). Score: correct 1, partially correct 0.5, incorrect 0. Pages are 1-based.

| System | Score | Correct | Partial | Incorrect | Cited page is evidence | Mean latency s | Mean cost US$ |
|---|---|---|---|---|---|---|---|
| finsage | 7.0/7 | 7 | 0 | 0 | 6/7 | 20.4 | 0.0014 |
| naive | 3.5/7 | 3 | 1 | 3 | 1/7 | 3.1 | 0.0002 |

| Question | FinSage | Naive | FinSage cited pages | Naive cited pages | Evidence pages |
|---|---|---|---|---|---|
| Does AMD have a reasonably healthy liquidity profile based o | correct | incorrect | 56 | 4 | 56 |
| What are the major products and services that AMD sells as o | correct | correct | 4, 6, 43, 60 | 11, 43, 60 | 4 |
| What drove revenue change as of the FY22 for AMD? | correct | correct | 43, 48 | 43 | 43 |
| What drove operating margin change as of the FY22 for AMD? I | correct | partially_correct | 43, 49 | 49 | 43 |
| Among operations, investing, and financing activities, which | correct | incorrect | 51 | none | 58 |
| From FY21 to FY22, excluding Embedded, in which AMD reportin | correct | correct | 48, 49 | 43 | 48 |
| Did AMD report customer concentration in FY22? | correct | incorrect | 12 | 5, 6, 43, 60 | 12 |

## Experiment C: FinSage time per stage (mean over the questions, seconds)

| rewrite | hyde | retrieval | rerank | answer | total |
|---|---|---|---|---|---|
| 3.2 | 6.2 | 0.5 | 6.7 | 3.8 | 20.4 |

Generator cost: US$0.0115. Judge cost: US$0.0957.

- financebench_id_00222 finsage: The candidate gives the same 1.57 quick ratio and the same conclusion that AMD's liquidity is reasonably healthy; leaving out the negligible related-party receivables does not change the result.

- financebench_id_00222 naive: The candidate says it cannot determine the quick ratio and gives no figure or conclusion, whereas the reference computes a quick ratio of 1.57 and concludes AMD's liquidity is reasonably healthy.

- financebench_id_00995 finsage: The candidate covers the reference's key products (CPUs, GPUs, APUs, chipsets, DPUs, FPGAs, Adaptive SoCs, semi-custom SoCs and development services, embedded products) across data center, PC, gaming and embedded markets, with extra correct detail.

- financebench_id_00995 naive: The candidate covers the reference's key product categories (server CPUs and GPUs, DPUs, FPGAs, Adaptive SoCs, client CPUs, APUs and chipsets, discrete GPUs, semi-custom SoCs and development services, and embedded products) and adds accurate extra detail.

- financebench_id_01198 finsage: The candidate names all three drivers in the reference: higher EPYC server processor sales, higher semi-custom product sales, and the inclusion of Xilinx embedded products. Its extra figures (44% growth to $23.6B) and the note on the Client revenue offset are accurate and consistent with the reference.

- financebench_id_01198 naive: The candidate attributes the FY22 revenue increase to Data Center growth (EPYC server processors), Gaming growth (semi-custom products) and Xilinx embedded sales, which matches the reference's drivers; it frames them at segment level and adds accurate figures.

- financebench_id_00917 finsage: The candidate attributes the FY22 operating margin decline mainly to Xilinx acquisition-related intangible amortization, which matches the reference, and its supporting figures are accurate.

- financebench_id_00917 naive: The candidate names the correct driver (amortization of Xilinx acquisition intangibles), but it ties that driver to gross margin and declines to give a clear conclusion on operating margin, which hedges away from the reference's conclusion.

- financebench_id_01279 finsage: The candidate names operating activities as the largest cash source in FY22, matching the reference, and its figures are consistent with AMD's filing.

- financebench_id_01279 naive: The candidate says it cannot answer, whereas the reference identifies operating activities as bringing in the most cash flow for AMD in FY22.

- financebench_id_00563 finsage: The candidate identifies Data Center as the segment with the largest proportional sales increase (about 64%), matching the reference answer.

- financebench_id_00563 naive: The candidate identifies Data Center as the segment with the largest proportional sales increase excluding Embedded, matching the reference answer, and its supporting figures (about 64% for Data Center, 21% for Gaming, Client down 10%) agree with AMD's reported FY22 results.

- financebench_id_00757 finsage: The candidate confirms AMD reported customer concentration with one customer accounting for 16% of consolidated net revenue in FY22, matching the reference, and the added Gaming segment detail is consistent with the filing.

- financebench_id_00757 naive: The candidate says it cannot answer, missing the reference's key fact that one customer accounted for 16% of AMD's FY22 consolidated net revenue.
