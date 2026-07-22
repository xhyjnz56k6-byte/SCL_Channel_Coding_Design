#ifndef SCL_BCH_SIMULATION_BCH_AWGN_SIMULATION_HPP
#define SCL_BCH_SIMULATION_BCH_AWGN_SIMULATION_HPP

#include "bch_simulation/bch_case_adapter.hpp"

#include "common/frame_pool.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

constexpr std::uint64_t kBchNoisePolicyVersion = 1U;

struct AwgnPointConfig {
    std::string stage;
    BchCaseId caseId = BchCaseId::S200;
    double ebN0Db = 0.0;
    std::size_t snrIndex = 0U;
    std::uint64_t frameStart = 0U;
    std::uint64_t frameCount = 0U;
    std::uint64_t globalSeed = 0U;
    bool progress = true;
    double progressRefreshSeconds = 0.2;
    bool writeFrameDetail = false;
    std::string framePoolManifest;
    std::string outputDirectory;
};

struct AwgnPointResult {
    AwgnPointConfig config;
    std::uint64_t processedFrames = 0U;
    std::uint64_t processedPayloadBits = 0U;
    std::uint64_t channelHardBitErrors = 0U;
    std::uint64_t channelHardFrameErrors = 0U;
    std::uint64_t decodedBitErrors = 0U;
    std::uint64_t decodedFrameErrors = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t reportedSuccessFrames = 0U;
    std::uint64_t miscorrectedFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    std::uint64_t noErrorStatusFrames = 0U;
    std::uint64_t correctedStatusFrames = 0U;
    std::uint64_t failedStatusFrames = 0U;
    double noiseSigma = 0.0;
    double noiseVariance = 0.0;
    double encodeTimeUsSum = 0.0;
    double decodeTimeUsSum = 0.0;
    std::vector<double> decodeTimesUs;
    std::string firstNoiseHash;
    std::string lastNoiseHash;
};

std::uint64_t pairedNoiseGroupId(common::Length payloadLength, std::size_t snrIndex);
double independentSigmaReference(const BchSimulationCase& simulationCase, double ebN0Db);
std::string standardNoiseHash(const common::RealVector& standardNoise);
AwgnPointResult runAwgnPoint(const AwgnPointConfig& config);
void writeAwgnPointSummary(const AwgnPointResult& result, const std::string& path);

}  // namespace scl::bch::simulation

#endif
