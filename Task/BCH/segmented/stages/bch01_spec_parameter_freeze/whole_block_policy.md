# Whole-block BCH policy

The only planned whole-block cases are BCH-B200, mother `BCH(255,207)`, shortened length 248, and BCH-B300, mother `BCH(511,421)`, shortened length 390. Their decoder strategy is BM plus Chien, never syndrome lookup. Their exact shortening and parameter interpretation require MATLAB confirmation and are not implemented or validated in BCH-01.

`BCH(511,385)`, a 426-bit extension case, and every other unconfirmed whole-block case are `OPTIONAL_NOT_SCHEDULED`.
