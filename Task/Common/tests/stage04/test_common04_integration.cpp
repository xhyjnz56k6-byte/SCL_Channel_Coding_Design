#include "common/simulation_pipeline.hpp"

#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) { if (!condition) throw std::runtime_error(message); }
void requireThrows(const std::string& name, const std::function<void()>& fn) {
    try { fn(); } catch (const std::exception&) { return; }
    throw std::runtime_error(name + " did not fail");
}

scl::common::SimulationShardResult shard(std::uint64_t index, scl::common::FrameIndex start, std::uint64_t count) {
    scl::common::SimulationShardResult value;
    value.shardIndex = index; value.frameStart = start; value.frameCount = count; value.experimentId = "exp";
    value.configHash = "hash"; value.framePoolId = "frame"; value.noisePoolId = "noise"; value.payloadLength = 200;
    value.encodedLength = 200; value.metrics.processedFrames = count; value.metrics.totalPayloadBits = count * 200;
    value.metrics.successfulFrames = count;
    return value;
}
}

int main() {
    for (const scl::common::Length length : {200U, 300U}) {
        scl::common::IdentitySimulationConfig config;
        config.payloadLength = length; config.encodedLength = length; config.frameCount = 100;
        config.stopConfig = {0, 100, 0, false};
        const auto hard = scl::common::runIdentitySimulation(config);
        config.decisionMode = scl::common::DecisionMode::LlrSign;
        const auto llr = scl::common::runIdentitySimulation(config);
        require(hard.metrics.processedFrames == 100U && hard.metrics.bitErrors == llr.metrics.bitErrors, "identity decision mismatch");
        config.ebN0_dB = 4.0;
        const auto high = scl::common::runIdentitySimulation(config);
        require(high.metrics.bitErrors <= hard.metrics.bitErrors + length, "gross SNR trend failed");
    }
    for (const scl::common::Length length : {200U, 300U}) {
        for (scl::common::FrameIndex frame = 0; frame < 4U; ++frame) {
            const auto payload = scl::common::generatePayloadBits(2026072001ULL, length, frame);
            const auto symbols = scl::common::bpskModulate(payload);
            const auto hard = scl::common::hardDecision(symbols);
            scl::common::RealVector finiteLlr;
            finiteLlr.reserve(symbols.size());
            for (double symbol : symbols) finiteLlr.push_back(symbol > 0.0 ? 100.0 : -100.0);
            const auto llr = scl::common::llrSignDecision(finiteLlr);
            require(hard == payload && llr == payload, "no-noise hard or finite LLR identity mismatch");
        }
    }
    const auto merged = scl::common::mergeSimulationShards({shard(0, 0, 40), shard(1, 40, 60)});
    require(merged.frameStart == 0U && merged.frameCount == 100U && merged.metrics.processedFrames == 100U, "valid merge failed");
    requireThrows("gap", [] { (void)scl::common::mergeSimulationShards({shard(0, 0, 40), shard(1, 41, 59)}); });
    requireThrows("overlap", [] { (void)scl::common::mergeSimulationShards({shard(0, 0, 40), shard(1, 39, 60)}); });
    requireThrows("duplicate index", [] { (void)scl::common::mergeSimulationShards({shard(0, 0, 40), shard(0, 40, 60)}); });
    auto bad = shard(1, 40, 60); bad.configHash = "other";
    requireThrows("config mismatch", [&] { (void)scl::common::mergeSimulationShards({shard(0, 0, 40), bad}); });
    bad = shard(1, 40, 60); bad.metrics.processedFrames = 59;
    requireThrows("metric mismatch", [&] { (void)scl::common::mergeSimulationShards({shard(0, 0, 40), bad}); });
    return 0;
}
