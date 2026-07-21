#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/random_policy.hpp"
#include "common/simulation_pipeline.hpp"

#include <fstream>
#include <iomanip>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        return 1;
    }
    try {
        std::ofstream output(argv[1]);
        if (!output) throw std::runtime_error("failed to open reference output");
        scl::common::CodeLengths lengths{200U, 200U, 248U, 248U};
        const double sigma = scl::common::computeAwgnSigma(lengths, 2.0);
        const double received = scl::common::applyAwgn({1.0}, {0.5}, sigma).front();
        const double llr = scl::common::llrValue(received, sigma);
        scl::common::SimulationShardResult first;
        first.shardIndex = 0; first.frameStart = 0; first.frameCount = 40; first.experimentId = "merge";
        first.configHash = "hash"; first.framePoolId = "frame"; first.noisePoolId = "noise";
        first.payloadLength = 200; first.encodedLength = 200; first.metrics.processedFrames = 40;
        first.metrics.totalPayloadBits = 8000; first.metrics.bitErrors = 40; first.metrics.frameErrors = 40;
        first.metrics.latency.totalTimeNsSum = 4000; first.metrics.latency.maxTotalTimeNs = 100;
        scl::common::SimulationShardResult second = first;
        second.shardIndex = 1; second.frameStart = 40; second.frameCount = 60; second.metrics.processedFrames = 60;
        second.metrics.totalPayloadBits = 12000; second.metrics.bitErrors = 60; second.metrics.frameErrors = 60;
        second.metrics.latency.totalTimeNsSum = 6000; second.metrics.latency.maxTotalTimeNs = 101;
        const auto merged = scl::common::mergeSimulationShards({first, second});
        output << std::setprecision(17);
        output << "field,value\n";
        output << "noiseWord0," << scl::common::noiseUniformWord({2026072101ULL, 0ULL, 0ULL, 0ULL, 1ULL}) << '\n';
        output << "noiseWord1," << scl::common::noiseUniformWord({2026072101ULL, 0ULL, 0ULL, 1ULL, 1ULL}) << '\n';
        output << "gaussian0," << scl::common::standardGaussianSample({2026072101ULL, 0ULL, 0ULL, 0ULL, 1ULL}) << '\n';
        output << "bpsk0," << scl::common::bpskSymbol(0U) << '\n';
        output << "bpsk1," << scl::common::bpskSymbol(1U) << '\n';
        output << "codeRate," << scl::common::computeCodeRate(lengths) << '\n';
        output << "sigma," << sigma << '\n';
        output << "received," << received << '\n';
        output << "llr," << llr << '\n';
        output << "hardDecision," << static_cast<unsigned>(scl::common::hardDecisionBit(received)) << '\n';
        output << "llrSignDecision," << static_cast<unsigned>(scl::common::llrSignDecisionBit(llr)) << '\n';
        output << "cxxMergeProcessedFrames," << merged.metrics.processedFrames << '\n';
        output << "cxxMergeTotalPayloadBits," << merged.metrics.totalPayloadBits << '\n';
        output << "cxxMergeBitErrors," << merged.metrics.bitErrors << '\n';
        output << "cxxMergeFrameErrors," << merged.metrics.frameErrors << '\n';
        output << "cxxMergeTotalTimeNsSum," << merged.metrics.latency.totalTimeNsSum << '\n';
        output << "cxxMergeMaxTotalTimeNs," << merged.metrics.latency.maxTotalTimeNs << '\n';
    } catch (...) {
        return 1;
    }
    return 0;
}
