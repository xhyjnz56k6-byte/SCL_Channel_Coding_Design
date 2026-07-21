#ifndef SCL_COMMON_SIMULATION_PIPELINE_HPP
#define SCL_COMMON_SIMULATION_PIPELINE_HPP

#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/result_schema.hpp"
#include "common/simulation_control.hpp"

namespace scl::common {

enum class DecisionMode {
    Hard,
    LlrSign,
};

struct IdentitySimulationConfig {
    std::string experimentId = "common04_identity";
    std::string caseName = "identity";
    std::string framePoolId = "generated";
    std::string noisePoolId = "generated";
    std::uint64_t payloadSeed = 2026072001ULL;
    std::uint64_t masterNoiseSeed = 2026072101ULL;
    std::uint64_t noiseGroupId = kDefaultNoiseGroupId;
    Length payloadLength = 200;
    Length encodedLength = 248;
    FrameIndex frameStart = 0;
    std::uint64_t frameCount = 100;
    double ebN0_dB = 0.0;
    SnrIndex snrIndex = 0;
    DecisionMode decisionMode = DecisionMode::Hard;
    StopConfig stopConfig{0, 100, 0, false};
};

SummaryRow runIdentitySimulation(const IdentitySimulationConfig& config);
ErrorMetrics mergeShardMetrics(const std::vector<ErrorMetrics>& shards);

}  // namespace scl::common

#endif  // SCL_COMMON_SIMULATION_PIPELINE_HPP
