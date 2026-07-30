# Revised S4-LDPC formal final report

## Scope

This revision did not rerun Stage15 Monte Carlo. It archive-preserved the prior
derived reports, validated all 93 final checkpoint/chunk hashes, repaired only
Case metadata, and recomputed derived Eb/N0 and relative-gain products.

## Correct metadata

N480 is Zc=48, filler=84, rankHp=96; N560 is Zc=56, filler=148, rankHp=112;
N640 is Zc=40, filler=20, rankHp=320. The repaired 186 records preserve BER,
FER, frames, errors, iterations, timing, complexity, seeds, and stop fields.

## Interpretation

Raw comparisons use Eb/N0 to account for actual rate. Relative gains are based
only on the shared non-zero adjacent interpolation range, with local linear
interpolation in log10(error rate), no extrapolation, and zero-error points
excluded from interpolation. A gain is a complete frozen Direct-scheme
comparison and is not attributed solely to length. Differences below 0.1 dB
are not treated as clear gains. Runtime uses grid summaries; per-frame
payload-correct latency is not available. Complexity summaries distinguish
iterations, message updates, classified operations, and unweighted basic-event
counts; the latter is not a theoretical total-complexity claim. The grid is not
sufficient to establish an error floor.
