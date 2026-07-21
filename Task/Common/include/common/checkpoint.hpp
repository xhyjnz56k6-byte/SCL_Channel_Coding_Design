#ifndef SCL_COMMON_CHECKPOINT_HPP
#define SCL_COMMON_CHECKPOINT_HPP

#include "common/simulation_metrics.hpp"
#include "common/types.hpp"

#include <cstdint>
#include <optional>
#include <string>

namespace scl::common {

constexpr const char* kCheckpointSchemaVersion = "common04.checkpoint.v1";

struct SimulationCheckpointRecord {
    std::string schemaVersion = kCheckpointSchemaVersion;
    std::string experimentId;
    std::string configHash;
    std::string framePoolId;
    std::string noisePoolId;
    Length payloadLength = 0;
    Length encodedLength = 0;
    SnrIndex snrIndex = 0;
    double ebN0_dB = 0.0;
    FrameIndex nextFrameIndex = 0;
    ErrorMetrics metrics;
    std::string stopReason = "CONTINUE";
};

std::string canonicalConfigText(const std::string& caseName,
                                Length payloadLength,
                                Length encodedLength,
                                const std::string& ebN0List,
                                const std::string& framePoolId,
                                const std::string& noisePoolId,
                                const std::string& stopConfig,
                                const std::string& decoderInputMode);
std::string computeConfigHash(const std::string& canonicalText);
std::string checkpointToJson(const SimulationCheckpointRecord& record);
SimulationCheckpointRecord checkpointFromJson(const std::string& text);
void validateResumeCompatibility(const SimulationCheckpointRecord& expected, const SimulationCheckpointRecord& actual);
void validateCheckpointState(const SimulationCheckpointRecord& record, FrameIndex firstFrameIndex,
                             std::uint64_t requestedFrameCount);
void writeCheckpointFile(const std::string& path, const SimulationCheckpointRecord& record);
SimulationCheckpointRecord readCheckpointFile(const std::string& path);

}  // namespace scl::common

#endif  // SCL_COMMON_CHECKPOINT_HPP
