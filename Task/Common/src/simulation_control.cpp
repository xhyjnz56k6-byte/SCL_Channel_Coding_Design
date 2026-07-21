#include "common/simulation_control.hpp"

#include <stdexcept>

namespace scl::common {

StopConfig formalStopConfig() {
    return {5000U, 50000U, 200U, true};
}

void validateStopConfig(const StopConfig& config) {
    if (config.maxFrames == 0U) {
        throw std::invalid_argument("maxFrames must be positive");
    }
    if (config.minFrames > config.maxFrames) {
        throw std::invalid_argument("minFrames must be <= maxFrames");
    }
}

StopDecision evaluateStop(const StopConfig& config, const ErrorMetrics& metrics) {
    validateStopConfig(config);
    if (metrics.processedFrames >= config.maxFrames) {
        return {true, "MAX_FRAMES"};
    }
    if (metrics.processedFrames < config.minFrames) {
        return {false, "CONTINUE"};
    }
    if (config.enableTargetFrameErrors && config.targetFrameErrors > 0U && metrics.frameErrors >= config.targetFrameErrors) {
        return {true, "TARGET_FRAME_ERRORS"};
    }
    return {false, "CONTINUE"};
}

}  // namespace scl::common
