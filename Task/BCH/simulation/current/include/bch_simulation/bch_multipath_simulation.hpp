#ifndef SCL_BCH_SIMULATION_BCH_MULTIPATH_SIMULATION_HPP
#define SCL_BCH_SIMULATION_BCH_MULTIPATH_SIMULATION_HPP

#include "bch_simulation/bch_case_adapter.hpp"
#include "bch_simulation/fixed_multipath_mmse.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

struct MultipathPointConfig {
    std::string stage = "BCH_S2_04";
    BchCaseId caseId = BchCaseId::S200;
    double sourcePayloadEbN0Db = 0.0;
    std::size_t snrIndex = 0U;
    std::uint64_t frameStart = 0U;
    std::uint64_t frameCount = 0U;
    std::uint64_t globalSeed = 0U;
    std::string framePoolManifest;
    std::string outputDirectory;
    bool progress = true;
    double progressRefreshSeconds = 1.0;
    bool writeFrameDetail = false;
    bool adaptiveStop = false;
    std::uint64_t minFrames = 0U;
    std::uint64_t targetFrameErrors = 0U;
    std::uint64_t maxFrames = 0U;
    std::string checkpointPath;
    std::uint64_t checkpointInterval = 0U;
    bool resume = false;
    std::uint64_t interruptAfterFrames = 0U;
    std::uint64_t shardIndex = 0U;
    std::uint64_t shardCount = 1U;
};

struct MultipathPointResult {
    MultipathPointConfig config;
    std::uint64_t processedFrames = 0U;
    std::uint64_t processedPayloadBits = 0U;
    std::uint64_t preEqualizationHardBitErrors = 0U;
    std::uint64_t preEqualizationHardFrameErrors = 0U;
    std::uint64_t postEqualizationHardBitErrors = 0U;
    std::uint64_t postEqualizationHardFrameErrors = 0U;
    std::uint64_t decodedBitErrors = 0U;
    std::uint64_t decodedFrameErrors = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t reportedSuccessFrames = 0U;
    std::uint64_t miscorrectedFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    double snrDb = 0.0;
    double noiseSigma = 0.0;
    double noiseVariance = 0.0;
    double equalizerSetupTimeUs = 0.0;
    double equalizationTimeUsSum = 0.0;
    double decodeTimeUsSum = 0.0;
    double totalReceiverTimeUsSum = 0.0;
    std::vector<double> equalizationTimesUs;
    std::vector<double> decodeTimesUs;
    std::string stopReason = "CONTINUE";
    std::string configHash;
    std::uint64_t checkpointCount = 0U;
    std::uint64_t resumeCount = 0U;
};

MultipathPointResult runMultipathPoint(const MultipathPointConfig& config);
void writeMultipathPointSummary(const MultipathPointResult& result, const std::string& path);

}  // namespace scl::bch::simulation

#endif
