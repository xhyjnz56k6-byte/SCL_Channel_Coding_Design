# BCH-11 validation report

Base commit: `8c6f6593fa6c8999bdea600d72abe0e08099a2a3`

Functional commit: `7761d423b6cc7b1d5c7af0cb4621800561bc4bbf`

The Release build completed with MinGW GCC 15.2.0. CTest `bch11_common_noiseless` passed. The
standalone evidence run passed 828 frames: 200 real Common frame-pool frames and seven boundary
patterns for each of four BCH cases. All decoded bit errors, frame errors, channel hard-decision bit
errors, miscorrections, and decoder failures were zero. True and reported success were 828/828. The
exact hard-decision boundary `y=0 -> 0` passed. Invalid case name and invalid payload length were
rejected.

Gate: `PASS_BCH11_COMMON_INTEGRATION_NOISELESS`.
