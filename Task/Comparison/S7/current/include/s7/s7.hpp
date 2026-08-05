#pragma once

#include "bch_segmented/bch15_segmented_adapter.hpp"
#include "cc/block_encoder.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace s7 {

constexpr std::size_t kBchPayloadBits = 200;
constexpr std::size_t kBchEncodedBits = 285;
constexpr std::size_t kBchBlockCount = 19;
constexpr std::size_t kCcPayloadBits = 300;
constexpr std::size_t kCcTrellisSteps = 306;
constexpr std::size_t kCcEncodedBits = 612;

enum class BchInterleaver { None, Codeblock, RowColumn, GlobalPseudorandom };
enum class CcInterleaver { None, ShortDepthBlock, Pseudorandom };
enum class BurstPosition { Head, Quarter, Middle, ThreeQuarter, Tail, Random };

struct Mapping {
    std::vector<std::size_t> outputToInput;
    std::vector<std::size_t> inputToOutput;
    std::string method;
    std::string fairnessGroupId;
    std::string permutationUnit = "BIT";
    bool preserveMotherOutputPair = false;
    std::size_t spanBits = 0;
    std::size_t spanTrellisSteps = 0;
    std::size_t bufferBits = 0;
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::string sha256;
};

Mapping makeBchMapping(BchInterleaver method, std::size_t parameter = 0,
                       std::uint64_t seed = 2026080407ULL);
Mapping makeCcMapping(CcInterleaver method, std::size_t parameter = 0,
                      std::uint64_t seed = 2026080417ULL);
void validateMapping(const Mapping& mapping, std::size_t expectedLength);
std::vector<std::uint8_t> interleaveBits(const std::vector<std::uint8_t>& input,
                                         const Mapping& mapping);
std::vector<std::uint8_t> deinterleaveBits(const std::vector<std::uint8_t>& input,
                                           const Mapping& mapping);
std::vector<double> interleaveValues(const std::vector<double>& input,
                                     const Mapping& mapping);
std::vector<double> deinterleaveValues(const std::vector<double>& input,
                                       const Mapping& mapping);

struct BurstSpec {
    double ratioRequested = 0.0;
    std::size_t lengthBits = 0;
    std::size_t start = 0;
    std::size_t end = 0;
    BurstPosition position = BurstPosition::Head;
    bool wrapAround = false;
};

BurstSpec makeBurstSpec(std::size_t encodedLength, double ratio,
                        BurstPosition position, std::uint64_t frameIndex,
                        std::uint64_t seed = 2026080427ULL);
std::string burstPositionName(BurstPosition position);
double sigmaSquaredFromEsN0(double esN0Db);
std::vector<double> bpskModulate(const std::vector<std::uint8_t>& bits);
std::vector<double> applyPolarityReversalAwgn(const std::vector<double>& symbols,
                                               const std::vector<double>& standardNoise,
                                               double sigmaSquared,
                                               const BurstSpec& burst);
std::vector<std::uint8_t> hardDecision(const std::vector<double>& received);
std::vector<double> llrFromReceived(const std::vector<double>& received,
                                    double sigmaSquared);
std::vector<std::uint8_t> deterministicPayload(std::size_t length,
                                               std::uint64_t frameIndex,
                                               std::uint64_t seed = 2026080437ULL);
std::vector<double> deterministicStandardNoise(std::size_t length,
                                               std::uint64_t frameIndex,
                                               std::uint64_t seed = 2026080447ULL);

struct DecodeTiming {
    double decodeTimeNs = 0.0;
    double interleaveTimeNs = 0.0;
    double deinterleaveTimeNs = 0.0;
};

struct BchFrameResult {
    std::vector<std::uint8_t> encodedBits;
    std::vector<std::uint8_t> decodedPayload;
    std::size_t bitErrors = 0;
    std::size_t affectedBlocks = 0;
    std::size_t maximumErrorsInBlock = 0;
    std::size_t correctedBlocks = 0;
    std::size_t lookupMissBlocks = 0;
    std::size_t postCheckFailedBlocks = 0;
    std::size_t miscorrectedBlocks = 0;
    bool decoderDetectedFailure = false;
    bool undetectedFrameError = false;
    DecodeTiming timing;
};

struct BchCodecContext {
    BchCodecContext();
    scl::bch::segmented::SyndromeTable syndromeTable;
};

struct CcFrameResult {
    std::vector<std::uint8_t> encodedBits;
    std::vector<std::uint8_t> decodedPayload;
    std::size_t bitErrors = 0;
    std::size_t tieCount = 0;
    std::uint8_t tracebackFinalState = 0;
    bool decoderFailure = false;
    DecodeTiming timing;
};

BchFrameResult runBchFrame(const std::vector<std::uint8_t>& payload,
                           const Mapping& mapping,
                           const std::vector<double>& standardNoise,
                           double sigmaSquared,
                           const BurstSpec& burst);
BchFrameResult runBchFrame(const BchCodecContext& context,
                           const std::vector<std::uint8_t>& payload,
                           const Mapping& mapping,
                           const std::vector<double>& standardNoise,
                           double sigmaSquared,
                           const BurstSpec& burst);
CcFrameResult runCcFrame(const std::vector<std::uint8_t>& payload,
                         const Mapping& mapping,
                         const std::vector<double>& standardNoise,
                         double sigmaSquared,
                         const BurstSpec& burst);
std::size_t bitErrors(const std::vector<std::uint8_t>& a,
                      const std::vector<std::uint8_t>& b);

}  // namespace s7
