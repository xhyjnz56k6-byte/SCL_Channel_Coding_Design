#include "bch_simulation/bch_burst_simulation.hpp"
#include "bch_simulation/bch_interleaver.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

namespace sim = scl::bch::simulation;

namespace {

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

template <typename Function>
void requireThrows(Function function, const char* message) {
    try {
        function();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(message);
}

scl::common::BitVector payload(const sim::BchSimulationCase& value, std::uint64_t seed) {
    scl::common::BitVector bits(value.payloadLength);
    for (std::size_t index = 0U; index < bits.size(); ++index) {
        bits[index] = static_cast<std::uint8_t>(
            sim::burstDomainValue(seed, index, 17U) & 1U);
    }
    return bits;
}

void testInjector() {
    const scl::common::BitVector source{0U, 1U, 0U, 1U, 0U};
    require(sim::injectConsecutiveBitBurst(source, 0U, 0U) == source, "L=0");
    require(sim::injectConsecutiveBitBurst(source, 0U, 1U)[0] == 1U, "frame start");
    require(sim::injectConsecutiveBitBurst(source, 4U, 1U)[4] == 1U, "frame end");
    const auto all = sim::injectConsecutiveBitBurst(source, 0U, source.size());
    require(sim::errorPositions(source, all).size() == source.size(), "L=N");
    require(sim::errorPositions(
        source, sim::injectConsecutiveBitBurst(source, 1U, 3U)).size() == 3U,
        "exactly L flips");
    requireThrows([&] { sim::injectConsecutiveBitBurst(source, 1U, 0U); },
                  "noncanonical zero burst");
    requireThrows([&] { sim::injectConsecutiveBitBurst(source, 0U, 6U); },
                  "L>N");
    requireThrows([&] { sim::injectConsecutiveBitBurst(source, 4U, 2U); },
                  "start+L>N");
}

void testInterleaver() {
    for (std::size_t length : {248U, 285U, 390U, 420U, 426U}) {
        for (sim::InterleaverMode mode :
             {sim::InterleaverMode::None, sim::InterleaverMode::FixedRandom}) {
            const auto value = sim::makeBchInterleaver(length, mode, 20260726U);
            sim::validateBchInterleaver(value);
            for (unsigned pattern = 0U; pattern < 4U; ++pattern) {
                scl::common::BitVector bits(length);
                for (std::size_t index = 0U; index < length; ++index) {
                    bits[index] = pattern == 0U ? 0U :
                                  pattern == 1U ? 1U :
                                  pattern == 2U ? index % 2U :
                                  sim::burstDomainValue(9U, index, length) & 1U;
                }
                require(sim::deinterleave(sim::interleave(bits, value), value) == bits,
                        "interleave/deinterleave identity");
            }
            auto invalid = value;
            invalid.permutation[0] = invalid.permutation[1];
            requireThrows([&] { sim::validateBchInterleaver(invalid); },
                          "non-bijection rejected");
            invalid = value;
            invalid.inversePermutation[0] = invalid.inversePermutation[1];
            requireThrows([&] { sim::validateBchInterleaver(invalid); },
                          "bad inverse rejected");
        }
    }
}

void testGuaranteedRegions() {
    for (sim::BchCaseId id :
         {sim::BchCaseId::B200, sim::BchCaseId::B300,
          sim::BchCaseId::B300_426}) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        const auto source = payload(value, 41U);
        const auto encoded = sim::encodeBchFrame(value, source).codeword;
        for (std::size_t length = 0U;
             length <= value.correctionCapability; ++length) {
            const std::vector<std::size_t> starts{
                0U,
                length == 0U ? 0U :
                    static_cast<std::size_t>((value.encodedLength - length) / 2U),
                length == 0U ? 0U :
                    static_cast<std::size_t>(value.encodedLength - length)};
            for (std::size_t start : starts) {
                auto decoded = sim::decodeBchFrame(
                    value, sim::injectConsecutiveBitBurst(encoded, start, length));
                sim::auditDecodedBchFrame(source, decoded);
                require(decoded.trueSuccess, "whole BCH guaranteed correction");
                require(!decoded.miscorrected, "no guaranteed-region miscorrection");
            }
        }
    }
}

void testSegmentBoundaryAndWeight() {
    for (sim::BchCaseId id : {sim::BchCaseId::S200, sim::BchCaseId::S300}) {
        const auto& value = sim::bchSimulationCase(id);
        sim::prepareBchCase(value);
        const auto source = payload(value, 83U);
        const auto encoded = sim::encodeBchFrame(value, source).codeword;
        const std::vector<std::size_t> starts{
            14U, static_cast<std::size_t>(value.encodedLength - 16U)};
        for (std::size_t start : starts) {
            const auto received = sim::injectConsecutiveBitBurst(encoded, start, 2U);
            const auto structure = sim::analyzeBurstStructure(
                value, sim::errorPositions(encoded, received), start, 2U);
            require(structure.maximumSubblockErrorWeight == 1U,
                    "cross-boundary max weight");
            require(structure.touchedSubblockCount == 2U, "cross-boundary blocks");
            auto decoded = sim::decodeBchFrame(value, received);
            sim::auditDecodedBchFrame(source, decoded);
            require(decoded.trueSuccess, "cross-boundary recovery");
        }
        const auto same = sim::analyzeBurstStructure(
            value, sim::errorPositions(
                encoded, sim::injectConsecutiveBitBurst(encoded, 0U, 2U)),
            0U, 2U);
        require(same.maximumSubblockErrorWeight == 2U &&
                !same.allSubblocksWithinGuaranteedRegion,
                "same-block L=2 is outside guarantee");
    }
}

void testReproducibilityAndConservation() {
    for (std::size_t length : {248U, 285U, 390U, 420U, 426U}) {
        for (std::size_t frame = 0U; frame < 50U; ++frame) {
            const auto a = sim::uniformBurstStart(length, 16U, 99U, frame, 7U);
            const auto b = sim::uniformBurstStart(length, 16U, 99U, frame, 7U);
            require(a == b && a + 16U <= length, "random-start reproducibility");
        }
        const auto inter = sim::makeBchInterleaver(
            length, sim::InterleaverMode::FixedRandom, 71U + length);
        scl::common::BitVector zero(length, 0U);
        const auto transmitted = sim::interleave(zero, inter);
        const auto damaged = sim::injectConsecutiveBitBurst(transmitted, 3U, 16U);
        const auto restored = sim::deinterleave(damaged, inter);
        require(sim::errorPositions(zero, damaged).size() == 16U, "before weight");
        require(sim::errorPositions(zero, restored).size() == 16U, "after weight");
    }
    bool changed = false;
    for (std::size_t frame = 0U; frame < 30U; ++frame) {
        changed = changed ||
            sim::uniformBurstStart(285U, 8U, 1U, frame, 9U) !=
            sim::uniformBurstStart(285U, 8U, 2U, frame, 9U);
    }
    require(changed, "different seeds should change start sequence");
    constexpr std::size_t legalCount = 17U;
    std::vector<std::uint64_t> frequencies(legalCount, 0U);
    constexpr std::uint64_t samples = 170000U;
    for (std::uint64_t frame = 0U; frame < samples; ++frame) {
        const auto start = sim::uniformBurstStart(
            32U, 16U, 20260726U, frame, 7001U);
        require(start < legalCount, "unbiased start outside legal range");
        ++frequencies[start];
    }
    const double expected = static_cast<double>(samples) / legalCount;
    double chiSquare = 0.0;
    for (std::uint64_t observed : frequencies) {
        const double delta = static_cast<double>(observed) - expected;
        chiSquare += delta * delta / expected;
        require(observed > 0U, "uniform-start coverage missing legal start");
    }
    // Sanity check only, not a mathematical proof. The fixed deterministic
    // sample has 16 degrees of freedom; 60 is deliberately conservative.
    require(chiSquare < 60.0, "uniform-start frequency sanity check");
}

struct RawCounts {
    std::uint64_t frames = 0, frameErrors = 0, bitErrors = 0;
};

RawCounts deterministicRange(std::uint64_t begin, std::uint64_t end,
                             std::uint64_t stride = 1U) {
    const auto& value = sim::bchSimulationCase(sim::BchCaseId::S200);
    RawCounts counts;
    for (std::uint64_t frame = begin; frame < end; frame += stride) {
        const auto source = payload(value, 9000U + frame);
        const auto encoded = sim::encodeBchFrame(value, source).codeword;
        const auto start = sim::uniformBurstStart(
            value.encodedLength, 2U, 2026072607ULL, frame, 91U);
        auto decoded = sim::decodeBchFrame(
            value, sim::injectConsecutiveBitBurst(encoded, start, 2U));
        sim::auditDecodedBchFrame(source, decoded);
        ++counts.frames;
        counts.frameErrors += decoded.trueSuccess ? 0U : 1U;
        for (std::size_t i = 0; i < source.size(); ++i)
            counts.bitErrors += source[i] != decoded.payload[i] ? 1U : 0U;
    }
    return counts;
}

RawCounts add(RawCounts a, const RawCounts& b) {
    a.frames += b.frames; a.frameErrors += b.frameErrors; a.bitErrors += b.bitErrors;
    return a;
}

void testResumeAndShardCounts() {
    const auto uninterrupted = deterministicRange(0U, 300U);
    const auto resumed = add(deterministicRange(0U, 113U),
                             deterministicRange(113U, 300U));
    require(uninterrupted.frames == resumed.frames &&
            uninterrupted.frameErrors == resumed.frameErrors &&
            uninterrupted.bitErrors == resumed.bitErrors,
            "resume raw counts differ");
    RawCounts merged;
    for (std::uint64_t shard = 0; shard < 3U; ++shard)
        merged = add(merged, deterministicRange(shard, 300U, 3U));
    require(uninterrupted.frames == merged.frames &&
            uninterrupted.frameErrors == merged.frameErrors &&
            uninterrupted.bitErrors == merged.bitErrors,
            "three-shard raw counts differ");
}

}  // namespace

int main() {
    try {
        testInjector();
        testInterleaver();
        testGuaranteedRegions();
        testSegmentBoundaryAndWeight();
        testReproducibilityAndConservation();
        testResumeAndShardCounts();
        std::cout << "PASS_BCH_S2_BURST_REDESIGN_CTEST\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_BCH_S2_BURST_REDESIGN_CTEST: " << error.what() << '\n';
        return 1;
    }
}
