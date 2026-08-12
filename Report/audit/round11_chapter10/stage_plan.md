# ROUND11 Chapter 10 stage plan

## Goal

Rewrite Chapter 10 as the final recommendation and conclusion chapter, merge the planned Chapter 11 responsibilities into Section 10.8, remove the standalone Chapter 11, and produce a compiled and visually reviewed final report.

## Non-goals

- Do not rerun any simulation or Formal job.
- Do not modify Formal CSV files or regenerate performance figures.
- Do not change the substantive content of Chapters 1-9.
- Do not modify BCH, CC, LDPC, Common, or Comparison implementations.
- Do not create a cross-code weighted score or universal ranking.
- Do not commit, push, or merge main.

## Allowed scope

- `Report/sections/10_综合方案推荐.tex`
- `Report/main.tex`
- Delete `Report/sections/11_结论与后续建议.tex`
- `Report/main.pdf` and ordinary generated LaTeX files
- `Report/audit/round11_chapter10/`

## Interfaces and formats

- Formal title: `综合方案推荐与结论`
- Structure: Sections 10.1-10.8; Section 10.8 contains three subsections.
- Decision assets: seven three-line tables and one Visio replacement placeholder.
- Evidence: existing stable labels for Tables 4.4, 5.12, 5.13, 6.10, 6.11, 7.8, 8.10, and 9.12.
- Final flow: Chapter 10 is followed directly by Appendix A.

## Acceptance matrix

| Requirement | Implementation location | Positive test | Negative test | Gate condition |
|---|---|---|---|---|
| Complete final chapter | Chapter 10 tex | Section and subsection counts | TODO/language scan | 10.1-10.8 and three 10.8 subsections present |
| Evidence-backed recommendations | Chapter 10 text and tables | Stable-label and parameter review | Unsupported score/ranking scan | Recommendations match Chapters 4-9 |
| Decision tables and flow | Tables 10.1-10.7, Figure 10.1 | Environment and render count | Repeated performance-figure scan | Seven tables and one Visio placeholder |
| Remove Chapter 11 | main and deleted tex | Include/TOC scan | Chapter 11 token scan | No Chapter 11; Appendix A follows Chapter 10 |
| Preserve formal evidence | Git diff and aggregate hash | Task CSV diff scan | Formal rerun/output scan | Zero Task CSV differences |
| Preserve Chapters 1-9 | Git diff scope | Source diff scan | Out-of-scope path scan | Zero substantive source differences |
| Compile and visual QA | `Report/main.pdf` | XeLaTeX, xdvipdfmx, page render | Error/reference/overfull scan | Zero fatal findings and no material layout defect |

## Gate

`PASS_ROUND11_CHAPTER10_FINAL_RECOMMENDATION_AND_CONCLUSION`
