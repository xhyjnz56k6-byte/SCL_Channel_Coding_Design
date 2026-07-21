# Common interface audit

Audited headers: `types.hpp`, `frame.hpp`, `interfaces.hpp`, `decoder_input.hpp`, `result_types.hpp`, `common.hpp`, `random_policy.hpp`, `noise_pool.hpp`, `simulation_metrics.hpp`, `simulation_control.hpp`, `checkpoint.hpp`, and `result_schema.hpp`; implementations and CMake were also inspected.

| Need | Actual API / field |
|---|---|
| Frame pool | `scl::common::PackedFramePoolReader`, `PayloadFrame` |
| Encoder contract | `IChannelEncoder::encode(BitVector)` and `CodeLengths` |
| Decoder contract | `IChannelDecoder::decode(DecoderInput)`, `HardBitInput`, `DecodeResult` |
| Rate | `computeCodeRate(const CodeLengths&) = payloadLength / encodedLength` |
| BPSK/AWGN/hard decision | `bpskModulate`, `computeAwgnSigma`, `applyAwgn`, `hardDecision` |
| Noise | `NoisePoolReader::readFramePrefix(FrameIndex, symbolCount)` |
| Metrics | `ErrorMetrics{processedFrames,totalPayloadBits,bitErrors,frameErrors,successfulFrames,latency}` |
| Stop | `StopConfig`, `evaluateStop` |
| Checkpoint | `SimulationCheckpointRecord`, `validateResumeCompatibility` |
| Results | `SummaryRow`, `summaryRowToCsv`, `metadataJson` |

No Common API is guessed or reimplemented by BCH-01.

