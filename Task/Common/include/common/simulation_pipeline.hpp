#ifndef SCL_COMMON_SIMULATION_PIPELINE_HPP
#define SCL_COMMON_SIMULATION_PIPELINE_HPP

#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/noise_pool.hpp"
#include "common/result_schema.hpp"
#include "common/simulation_control.hpp"

#include <optional>

namespace scl::common {

enum class DecisionMode {
    Hard,
    LlrSign,
};

enum class SimulationInputMode {
    Immediate,
    PoolBacked,
};

struct IdentitySimulationConfig {
    std::string experimentId = "common04_identity";
    std::string caseName = "identity";
    std::string framePoolId = "generated";
    std::string noisePoolId = "generated";
    std::string framePoolManifestPath;
    std::string noisePoolManifestPath;
    std::uint64_t payloadSeed = 2026072001ULL;
    std::uint64_t masterNoiseSeed = 2026072101ULL;
    std::uint64_t noiseGroupId = kDefaultNoiseGroupId;
    Length payloadLength = 200;
    Length encodedLength = 200;
    FrameIndex frameStart = 0;
    std::uint64_t frameCount = 100;
    double ebN0_dB = 0.0;
    SnrIndex snrIndex = 0;
    DecisionMode decisionMode = DecisionMode::Hard;
    SimulationInputMode inputMode = SimulationInputMode::Immediate;
    StopConfig stopConfig{0, 100, 0, false};
};

struct IdentitySimulationRunOptions {
    std::optional<SimulationCheckpointRecord> resumeCheckpoint;
    std::uint64_t checkpointIntervalFrames = 0;
    std::string checkpointOutputPath;
};

struct IdentitySimulationRunResult {
    SummaryRow summary;
    SimulationCheckpointRecord finalCheckpoint;
};

struct SimulationShardResult {
    std::uint64_t shardIndex = 0;
    FrameIndex frameStart = 0;
    std::uint64_t frameCount = 0;
    SnrIndex snrIndex = 0;
    double ebN0_dB = 0.0;
    std::string experimentId;
    std::string configHash;
    std::string framePoolId;
    std::string noisePoolId;
    Length payloadLength = 0;
    Length encodedLength = 0;
    ErrorMetrics metrics;
};

struct MergedShardResult {
    FrameIndex frameStart = 0;
    std::uint64_t frameCount = 0;
    ErrorMetrics metrics;
};

SummaryRow runIdentitySimulation(const IdentitySimulationConfig& config);
IdentitySimulationRunResult runIdentitySimulation(const IdentitySimulationConfig& config,
                                                  const IdentitySimulationRunOptions& options);
ErrorMetrics mergeShardMetrics(const std::vector<ErrorMetrics>& shards);
MergedShardResult mergeSimulationShards(std::vector<SimulationShardResult> shards);

}  // namespace scl::common

#endif  // SCL_COMMON_SIMULATION_PIPELINE_HPP
