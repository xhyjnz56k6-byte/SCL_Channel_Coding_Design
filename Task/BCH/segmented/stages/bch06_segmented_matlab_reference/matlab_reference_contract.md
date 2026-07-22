# MATLAB reference contract

Inputs are row vectors of logical or numeric 0/1 values. The left-most bit is the highest polynomial coefficient. `g=[1 0 0 1 1]`, codeword layout is `[message parity]`, syndrome bits are `[s3 s2 s1 s0]`, and error positions are 0-based (`position+1` only for MATLAB indexing). CSV uses ASCII bit strings and uppercase statuses. The primary reference is explicit GF(2) XOR long division; Communications Toolbox availability is auxiliary only.
