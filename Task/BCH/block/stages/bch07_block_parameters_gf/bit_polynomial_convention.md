# Bit/polynomial convention

Index 0 is the leftmost, highest-degree coefficient. Generator coefficients are descending degree. Syndrome evaluates `r(alpha^j)` with codeword index `i` mapped to exponent `n-1-i`; Chien tests `alpha^-(n-1-i)`. C++ positions are 0-based; MATLAB converts its 1-based indices to 0-based output.
