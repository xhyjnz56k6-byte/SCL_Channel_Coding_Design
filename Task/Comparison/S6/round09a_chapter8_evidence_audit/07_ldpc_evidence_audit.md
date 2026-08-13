# LDPC_S6_FORMAL_EVIDENCE_AUDIT

Formal source: S6 integrates 62 N560 rows from `Task/LDPC/block/stages/stage23_s4_final_reintegration/results/s4_revised_formal_point_results.csv`. Integration summary records formalRerun=false, pairedSnrPoints=31, sharedPayloadCodewordLlr=true, maxIterations=32, nmsAlpha=0.95.

N560 origin: `freezeS4Cases()` calls `selectDirectCase(300,576,300/576,2,640)` (`s4_ldpc.cpp:222-226`). `selectDirectCase` sorts by closeness to target length, rate, Zc, nb (`s4_ldpc.cpp:201-219`). Metadata: targetLength=576, actualLength=560, Zc=56, kb=8, nb=10, mb=2, informationCapacity=448, fillerLength=148, parityLength=112, rankHp=112, actualRate=300/560.

Pairing: `main.cpp:282-298` creates one payload/codeword/LLR and decodes BP then NMS on the same LLR. Integrated CSV confirms same payloadHash, codewordHash, and llrHash for BP/NMS at every SNR.

maxIterations: all N560 rows use 32. Evidence: `ldpc_integration_summary.json`, Stage23 `frozen_config.csv`, and `main.cpp:249,287-295`. No separate evidence confirms teacher-suggested 10/20/30 were formal S6 results.

NMS alpha: N560 alpha=0.95, from Stage23/S4 final reintegration (`frozen_config.csv` alphaByLength and integration summary). It is not reselected in S6.

BP counters: `s4_ldpc.cpp:322-384` counts check-node updates, tanh prefix/suffix operations, atanh operations, message updates, and variable-node updates.

NMS counters: `s4_ldpc.cpp:387-459` counts abs, comparisons, min1/min2, sign operations, alpha multiplications, message updates, and variable-node updates.

Timing/memory: `main.cpp:287-298` times only `decodeLayeredBp/Nms`; encoding/channel/LLR generation are outside. `main.cpp:318-319` models memory as posterior LLR + edge messages + hard decisions; not full process RSS.
