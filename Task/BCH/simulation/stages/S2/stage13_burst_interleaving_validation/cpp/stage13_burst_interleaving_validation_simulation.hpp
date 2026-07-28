#ifndef SCL_BCH_S2_STAGE13_BURST_INTERLEAVING_VALIDATION_SIMULATION_HPP
#define SCL_BCH_S2_STAGE13_BURST_INTERLEAVING_VALIDATION_SIMULATION_HPP

#include "stage13_burst_interleaving_validation_core.hpp"
#include "stage02_case_contract.hpp"

#include <cstdint>
#include <vector>

namespace scl::bch::s2::stage13 {

struct SimulationPoint {
    stage02::CaseId caseId;
    InterleaverMode mode = InterleaverMode::None;
    std::size_t depth = 1U;
    std::uint64_t interleaverSeed = 0U;
    std::size_t burstLength = 0U;
    std::size_t burstLengthIndex = 0U;
    std::size_t snrIndex = 0U;
    double targetSnrDb = 0.0;
    bool awgnEnabled = false;
};

struct SimulationCounters {
    std::uint64_t framesProcessed = 0U;
    std::uint64_t payloadBitsProcessed = 0U;
    std::uint64_t payloadErrorBits = 0U;
    std::uint64_t payloadErrorFrames = 0U;
    std::uint64_t decoderDeclaredSuccessFrames = 0U;
    std::uint64_t decoderDeclaredFailureFrames = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t miscorrectionFrames = 0U;
    std::uint64_t undetectedErrorFrames = 0U;
    std::uint64_t affectedCodeBlocksTotal = 0U;
    std::uint64_t maxAffectedCodeBlocks = 0U;
    std::uint64_t maxErrorsInOneCodeBlockObserved = 0U;
    std::uint64_t sumMaxErrorsInOneCodeBlock = 0U;
    std::uint64_t burstStartChecksum = 0U;
    std::uint64_t payloadChecksum = 0U;
    std::uint64_t awgnChecksum = 0U;
    std::uint64_t interleaverApplyTimeTotalNs = 0U;
    std::uint64_t deinterleaverApplyTimeTotalNs = 0U;
    std::uint64_t decoderTimeTotalNs = 0U;
    std::vector<std::uint64_t> decoderTimesNs;
    std::vector<std::uint64_t> interleaverTimesNs;
    std::vector<std::uint64_t> deinterleaverTimesNs;
};

struct FrameTrace {
    common::BitVector payload;
    common::BitVector encoded;
    common::BitVector interleaved;
    common::BitVector channelBitsBeforeBurst;
    common::BitVector channelBitsAfterBurst;
    common::BitVector deinterleaved;
    common::BitVector recoveredPayload;
    std::size_t burstStart = 0U;
    bool decoderDeclaredSuccess = false;
    bool decoderAllNoError = false;
};

FrameTrace simulateFrame(const SimulationPoint& point,
                         std::uint64_t masterSeed,
                         std::uint64_t frameIndex,
                         const std::vector<std::size_t>& permutation);

SimulationCounters simulateRange(const SimulationPoint& point,
                                 std::uint64_t masterSeed,
                                 std::uint64_t frameStart,
                                 std::uint64_t frameCount,
                                 bool collectTiming);

void addCounters(SimulationCounters& target,
                 const SimulationCounters& source,
                 bool includeTiming);
bool sameDeterministicCounters(const SimulationCounters& left,
                               const SimulationCounters& right);
std::uint64_t percentile(std::vector<std::uint64_t> values, double probability);
std::uint64_t bitErrors(const common::BitVector& left,
                        const common::BitVector& right);

}  // namespace scl::bch::s2::stage13

#endif

