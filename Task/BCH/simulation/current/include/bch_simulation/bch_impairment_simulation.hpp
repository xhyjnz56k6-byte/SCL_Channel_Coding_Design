#ifndef SCL_BCH_SIMULATION_BCH_IMPAIRMENT_SIMULATION_HPP
#define SCL_BCH_SIMULATION_BCH_IMPAIRMENT_SIMULATION_HPP

#include "bch_simulation/bch_case_adapter.hpp"
#include "bch_simulation/bch_impairment_channels.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

enum class ImpairmentChannel { ResidualCfo, ShortBlockage, Burst };
enum class BurstMode { Pure, Awgn };

struct ImpairmentPointConfig {
    std::string stage;
    ImpairmentChannel channel = ImpairmentChannel::ResidualCfo;
    BchCaseId caseId = BchCaseId::S200;
    double sourcePayloadEbN0Db = 0.0;
    std::uint64_t frameStart = 0U;
    std::uint64_t frameCount = 0U;
    std::uint64_t logicalFrameCount = 0U;
    std::uint64_t globalSeed = 0U;
    std::uint64_t noisePolicyVersion = 2U;
    std::string framePoolManifest;
    std::string outputDirectory;
    bool progress = true;
    double progressRefreshSeconds = 1.0;
    double initialPhaseDeg = 0.0;
    double frameRotationDeg = 0.0;
    CfoCompensationMode compensationMode = CfoCompensationMode::None;
    double attenuationDb = 0.0;
    bool completeBlockage = false;
    std::size_t blockageLength = 1U;
    StartPolicy blockageStartPolicy = StartPolicy::UniformRandom;
    BurstMode burstMode = BurstMode::Pure;
    std::size_t burstLength = 1U;
    StartPolicy burstStartPolicy = StartPolicy::UniformRandom;
    std::string checkpointPath;
    std::uint64_t checkpointInterval = 0U;
    bool resume = false;
    std::uint64_t interruptAfterFrames = 0U;
    bool adaptiveStop = false;
    std::uint64_t minFrames = 0U;
    std::uint64_t targetFrameErrors = 0U;
    std::uint64_t maxFrames = 0U;
    std::uint64_t shardIndex = 0U;
    std::uint64_t shardCount = 1U;
};

struct ImpairmentPointResult {
    ImpairmentPointConfig config;
    double snrDb = 0.0;
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
    double decodeTimeUsSum = 0.0;
    double totalReceiverTimeUsSum = 0.0;
    std::vector<double> decodeTimesUs;
    std::vector<double> receiverTimesUs;
    std::string stopReason = "CONTINUE";
    std::string configHash;
    std::uint64_t checkpointCount = 0U;
    std::uint64_t resumeCount = 0U;
};

ImpairmentChannel parseImpairmentChannel(const std::string& value);
std::string impairmentChannelName(ImpairmentChannel value);
BurstMode parseBurstMode(const std::string& value);
std::string burstModeName(BurstMode value);
ImpairmentPointResult runImpairmentPoint(const ImpairmentPointConfig& config);
void writeImpairmentPointSummary(
    const ImpairmentPointResult& result, const std::string& path);

}  // namespace scl::bch::simulation

#endif
