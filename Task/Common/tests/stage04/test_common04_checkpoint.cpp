#include "common/checkpoint.hpp"
#include "common/simulation_pipeline.hpp"

#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void requireThrows(const std::string& name, const std::function<void()>& fn) {
    try { fn(); } catch (const std::exception&) { return; }
    throw std::runtime_error(name + " did not fail");
}

void requireSameCounters(const scl::common::ErrorMetrics& left, const scl::common::ErrorMetrics& right) {
    require(left.processedFrames == right.processedFrames, "processedFrames mismatch");
    require(left.totalPayloadBits == right.totalPayloadBits, "totalPayloadBits mismatch");
    require(left.bitErrors == right.bitErrors, "bitErrors mismatch");
    require(left.frameErrors == right.frameErrors, "frameErrors mismatch");
    require(left.successfulFrames == right.successfulFrames, "successfulFrames mismatch");
}
}

int main() {
    scl::common::IdentitySimulationConfig full;
    full.experimentId = "resume_identity";
    full.caseName = "k200_identity";
    full.payloadLength = 200;
    full.encodedLength = 200;
    full.frameCount = 100;
    full.stopConfig = {0, 100, 0, false};
    full.ebN0_dB = 2.0;
    const auto continuous = scl::common::runIdentitySimulation(full, {});

    auto firstPart = full;
    firstPart.frameCount = 37;
    const std::filesystem::path checkpointPath = "Task/Common/build/stage04/checkpoint_resume.json";
    scl::common::IdentitySimulationRunOptions firstOptions;
    firstOptions.checkpointOutputPath = checkpointPath.string();
    firstOptions.checkpointIntervalFrames = 37;
    const auto partial = scl::common::runIdentitySimulation(firstPart, firstOptions);
    require(partial.finalCheckpoint.nextFrameIndex == 37U, "partial nextFrameIndex mismatch");
    require(!std::filesystem::exists(checkpointPath.string() + ".tmp"), "atomic checkpoint temporary file remained");

    scl::common::IdentitySimulationRunOptions resumedOptions;
    resumedOptions.resumeCheckpoint = scl::common::readCheckpointFile(checkpointPath.string());
    const auto resumed = scl::common::runIdentitySimulation(full, resumedOptions);
    requireSameCounters(continuous.summary.metrics, resumed.summary.metrics);
    require(continuous.summary.stopReason == resumed.summary.stopReason, "resume stopReason mismatch");
    require(resumed.finalCheckpoint.nextFrameIndex == 100U, "resume final nextFrameIndex mismatch");
    require(resumed.summary.metrics.latency.totalTimeNsSum >= partial.summary.metrics.latency.totalTimeNsSum,
            "resumed timing must be cumulative");

    auto bad = partial.finalCheckpoint;
    bad.schemaVersion = "bad";
    requireThrows("schema mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.experimentId = "other";
    requireThrows("experiment mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.configHash = "other";
    requireThrows("config hash mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.framePoolId = "other";
    requireThrows("frame pool mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.noisePoolId = "other";
    requireThrows("noise pool mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.payloadLength = 300;
    requireThrows("payload length mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.encodedLength = 300;
    requireThrows("encoded length mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.snrIndex = 1;
    requireThrows("snr mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.ebN0_dB = 3.0;
    requireThrows("Eb/N0 mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.noisePolicyVersion += 1U;
    requireThrows("noise policy mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.globalSeed += 1U;
    requireThrows("global seed mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.shardIndex += 1U;
    requireThrows("shard index mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.shardCount += 1U;
    requireThrows("shard count mismatch", [&] { scl::common::validateResumeCompatibility(partial.finalCheckpoint, bad); });
    bad = partial.finalCheckpoint; bad.nextFrameIndex = 101;
    requireThrows("range mismatch", [&] { scl::common::validateCheckpointState(bad, 0, 100); });
    bad = partial.finalCheckpoint; bad.metrics.processedFrames = 36;
    requireThrows("counter mismatch", [&] { scl::common::validateCheckpointState(bad, 0, 37); });
    bad = partial.finalCheckpoint; bad.metrics.totalPayloadBits = 1;
    requireThrows("bit total mismatch", [&] { scl::common::validateCheckpointState(bad, 0, 37); });
    bad = partial.finalCheckpoint; bad.metrics.successfulFrames = partial.finalCheckpoint.metrics.processedFrames;
    requireThrows("success count mismatch", [&] { scl::common::validateCheckpointState(bad, 0, 37); });
    requireThrows("truncated JSON", [] { (void)scl::common::checkpointFromJson("{"); });
    requireThrows("wrong checkpoint path", [] { (void)scl::common::readCheckpointFile("missing_checkpoint.json"); });
    return 0;
}
