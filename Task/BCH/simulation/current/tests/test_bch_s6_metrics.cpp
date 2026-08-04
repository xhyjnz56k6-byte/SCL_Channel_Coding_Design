#include "bch_simulation/bch_case_adapter.hpp"

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>

namespace {

using scl::common::BitVector;
using scl::bch::simulation::BchCaseId;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

BitVector payloadFromValue(std::uint64_t value, std::size_t length) {
    BitVector payload(length, 0U);
    for (std::size_t i = 0; i < std::min<std::size_t>(length, 64U); ++i) {
        payload[length - 1U - i] = static_cast<unsigned char>((value >> i) & 1U);
    }
    return payload;
}

void testS200AllMessagesAndCounters() {
    const auto& simulationCase = scl::bch::simulation::bchSimulationCase(BchCaseId::S200);
    for (std::uint64_t value = 0; value < 2048U; ++value) {
        BitVector payload(200U, 0U);
        const BitVector block = payloadFromValue(value, 11U);
        std::copy(block.begin(), block.end(), payload.begin());
        const auto encoded = scl::bch::simulation::encodeBchFrame(simulationCase, payload);
        auto decoded = scl::bch::simulation::decodeBchFrame(simulationCase, encoded.codeword);
        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
        require(decoded.trueSuccess, "S200 noiseless payload mismatch");
        require(decoded.complexity.segmentCount == 19U, "S200 segment count mismatch");
        require(decoded.complexity.initialSyndromeCount == 19U, "S200 initial syndrome count mismatch");
        require(decoded.complexity.syndromeCalculationCount == 19U, "S200 syndrome calculation mismatch");
        require(decoded.complexity.tableLookupCount == 0U, "S200 zero syndrome must not look up");
    }

    const BitVector payload = payloadFromValue(0xA55AU, 200U);
    const auto encoded = scl::bch::simulation::encodeBchFrame(simulationCase, payload);
    BitVector received = encoded.codeword;
    for (std::size_t segment = 0; segment < 19U; ++segment) received[segment * 15U] ^= 1U;
    auto decoded = scl::bch::simulation::decodeBchFrame(simulationCase, received);
    scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
    require(decoded.trueSuccess, "S200 all-segment single-error recovery failed");
    require(decoded.complexity.nonzeroSyndromeCount == 19U, "S200 nonzero syndrome mismatch");
    require(decoded.complexity.tableLookupCount == 19U, "S200 lookup count mismatch");
    require(decoded.complexity.lookupHitCount == 19U, "S200 lookup hit mismatch");
    require(decoded.complexity.bitFlipCount == 19U, "S200 bit flip mismatch");
    require(decoded.complexity.postSyndromeCheckCount == 19U, "S200 post-check mismatch");
    require(decoded.memory.lookupTableBytes > 0U, "S200 lookup memory missing");
    require(decoded.memory.totalDecoderMemoryBytes >= decoded.memory.lookupTableBytes,
            "S200 total memory mismatch");
    require(decoded.memory.memoryMeasurementMethod == "EXACT_FROM_TYPE_AND_COUNT",
            "S200 memory method mismatch");
}

void testB200ErrorCapabilityAndCounters() {
    const auto& simulationCase = scl::bch::simulation::bchSimulationCase(BchCaseId::B200);
    const BitVector payload = payloadFromValue(0x12345678U, 200U);
    const auto encoded = scl::bch::simulation::encodeBchFrame(simulationCase, payload);
    for (std::size_t weight = 0; weight <= 6U; ++weight) {
        BitVector received = encoded.codeword;
        for (std::size_t i = 0; i < weight; ++i) received[(i * 37U + 11U) % received.size()] ^= 1U;
        auto decoded = scl::bch::simulation::decodeBchFrame(simulationCase, received);
        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
        require(decoded.trueSuccess, "B200 failed within t=6");
        require(decoded.complexity.syndromeValueCount == 12U, "B200 syndrome value count mismatch");
        require(decoded.complexity.postSyndromeCheckCount == 1U, "B200 post-check count mismatch");
        if (weight == 0U) {
            require(decoded.complexity.bmIterationCount == 0U, "B200 no-error BM count mismatch");
            require(decoded.complexity.chienPositionTestCount == 0U, "B200 no-error Chien count mismatch");
        } else {
            require(decoded.complexity.bmIterationCount == 12U, "B200 BM iteration mismatch");
            require(decoded.complexity.chienPositionTestCount == 255U, "B200 Chien length mismatch");
            require(decoded.complexity.bitFlipCount == weight, "B200 bit flip mismatch");
            require(decoded.complexity.gfMultiplyCount > 0U, "B200 GF multiply count missing");
        }
        require(decoded.memory.gfTableBytes > 0U, "B200 GF table memory missing");
        require(decoded.memory.totalDecoderMemoryBytes > decoded.memory.gfTableBytes,
                "B200 total memory mismatch");
        require(decoded.memory.memoryMeasurementMethod == "EXACT_FROM_TYPE_AND_COUNT",
                "B200 memory method mismatch");
    }
}

}  // namespace

int main() {
    try {
        testS200AllMessagesAndCounters();
        testB200ErrorCapabilityAndCounters();
        std::cout << "PASS_BCH_S6_METRICS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_BCH_S6_METRICS: " << error.what() << '\n';
        return 1;
    }
}
