# ROUND10-B S7 Chapter 9 stage plan

## Goal

Use frozen S7 Formal, Stage12-Stage16, Stage15 figure data, the Round10-A evidence audit, and the integrated LDPC no-interleaving baseline to complete Chapter 9 writing, tables, figure integration, compilation, visual QA, language checks, and evidence coverage.

## Non-goals

- Do not rerun Formal.
- Do not modify BCH, CC, or LDPC codec implementations.
- Do not modify the substantive content of Chapters 1-8.
- Do not delete or overwrite Stage15, Stage16, or original experiment assets.
- Do not make LDPC burst-error or interleaver claims.
- Do not commit, push, or merge main.

## Allowed scope

- `Report/sections/09_交织抗突发错误分析.tex`
- `Report/main.pdf` and ordinary LaTeX generated files
- `Report/audit/round10_b_s7_chapter9/`
- `Task/Comparison/S7/chapter9_evidence_audit/` report-specific derived tables and audits

## Interfaces and formats

- Chapter structure: Sections 9.1-9.7.
- Formal display scope: burst ratios 2% and 5% only.
- Tables: 12 three-line tables backed by `report_table_data_9_*.csv`.
- Figures: existing validated Stage15 PNGs; mixed-ratio timing/tolerance figures replaced by filtered tables.
- PDF: XeLaTeX output at `Report/main.pdf`.

## Acceptance matrix

| Requirement | Implementation location | Positive test | Negative test | Gate condition |
|---|---|---|---|---|
| Complete 9.1-9.7 chapter | Chapter 9 tex | Section scan and PDF render | TODO/placeholder scan | Seven sections present; only one authorized Visio placeholder |
| Correct channel model | 9.2 equations | Formula review | Forbidden long-name/meta wording scan | BPSK, polarity reversal, and AWGN variance are correct |
| Report only 2%/5% | tex and filter CSV | Figure/table audit | Search `10%`, `0.10`, `burst_10` | Zero formal displays of excluded ratio |
| BCH evidence chain | 9.3 and Tables 9.5-9.6 | Formal-row trace | Intrinsic-capability wording scan | Distribution mechanism and FER are both evidenced |
| CC mechanism and fairness boundary | 9.4 and Table 9.8 | D8/D16/Pseudo128 checks | Pure-comparison misuse scan | D8 engineering and D16 controlled roles are distinct |
| LDPC boundary | 9.5 and Table 9.11 | Baseline source check | Burst/ranking scan | AWGN-only role is explicit |
| Timing and buffer boundary | Tables 9.9-9.10 | 2%/5% weighted recomputation | Physical-delay conversion scan | CPU time and buffer depth remain separate |
| Compiled and visually usable PDF | `Report/main.pdf` | Latexmk, render, page review | Error/reference/overfull scans | 0 errors and no material layout defect |

## Gate

`PASS_ROUND10_B_S7_CHAPTER9_FORMAL_WRITING`
