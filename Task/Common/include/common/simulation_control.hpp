#ifndef SCL_COMMON_SIMULATION_CONTROL_HPP
#define SCL_COMMON_SIMULATION_CONTROL_HPP

#include "common/simulation_metrics.hpp"

#include <cstdint>
#include <string>

namespace scl::common {

struct StopConfig {
    std::uint64_t minFrames = 0;
    std::uint64_t maxFrames = 0;
    std::uint64_t targetFrameErrors = 0;
    bool enableTargetFrameErrors = true;
};

struct StopDecision {
    bool shouldStop = false;
    std::string reason = "CONTINUE";
};

StopConfig formalStopConfig();
void validateStopConfig(const StopConfig& config);
StopDecision evaluateStop(const StopConfig& config, const ErrorMetrics& metrics);

}  // namespace scl::common

#endif  // SCL_COMMON_SIMULATION_CONTROL_HPP
