# BCH-06 known issues

Communications Toolbox is available but auxiliary only. BCH-07, AWGN, BPSK, whole-block BCH, BM, and Chien work were not started. This branch is not merged into `main`.

Blocking issue: C++/MATLAB field-level comparison is complete for single-block datasets but not yet for segmented 208/705/8/12/30/4 detail datasets. The final BCH-06 Gate must remain blocked until a C++ segmented exporter and matching MATLAB detail outputs are added and checked.
