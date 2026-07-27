#include "bch_simulation/bch_burst_simulation.hpp"

#include <algorithm>
#include <stdexcept>

namespace scl::bch::simulation {
namespace {

std::uint64_t mix64(std::uint64_t value) {
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;
    return value;
}

}  // namespace

common::BitVector injectConsecutiveBitBurst(
    const common::BitVector& bits, std::size_t start, std::size_t length) {
    common::validateBits(bits, "consecutive-bit-burst input");
    if (start > bits.size() || length > bits.size() - start) {
        throw std::invalid_argument("consecutive-bit-burst range exceeds frame");
    }
    if (length == 0U && start != 0U) {
        throw std::invalid_argument("zero-length burst uses canonical start zero");
    }
    common::BitVector output = bits;
    for (std::size_t index = start; index < start + length; ++index) {
        output[index] ^= 1U;
    }
    return output;
}

std::vector<std::size_t> errorPositions(
    const common::BitVector& expected, const common::BitVector& observed) {
    if (expected.size() != observed.size()) {
        throw std::invalid_argument("error-position vectors have different lengths");
    }
    common::validateBits(expected, "expected bits");
    common::validateBits(observed, "observed bits");
    std::vector<std::size_t> positions;
    positions.reserve(expected.size());
    for (std::size_t index = 0U; index < expected.size(); ++index) {
        if (expected[index] != observed[index]) positions.push_back(index);
    }
    return positions;
}

BurstStructure analyzeBurstStructure(
    const BchSimulationCase& simulationCase,
    const std::vector<std::size_t>& positions,
    std::size_t transmittedStart,
    std::size_t transmittedLength) {
    BurstStructure result;
    result.burstLength = transmittedLength;
    result.burstStart = transmittedStart;
    result.relativeStartInSubblock = transmittedStart % 15U;
    const std::size_t blockCount =
        simulationCase.organization == BchOrganization::Segmented
            ? simulationCase.segmentCount : 1U;
    result.perSubblockErrorWeights.assign(blockCount, 0U);
    for (std::size_t position : positions) {
        if (position >= simulationCase.encodedLength) {
            throw std::invalid_argument("error position exceeds encoded frame");
        }
        const std::size_t block =
            simulationCase.organization == BchOrganization::Segmented
                ? position / 15U : 0U;
        ++result.perSubblockErrorWeights[block];
    }
    for (std::size_t weight : result.perSubblockErrorWeights) {
        if (weight > 0U) ++result.touchedSubblockCount;
        if (weight == 1U) ++result.numberOfSubblocksWithOneError;
        if (weight > 1U) ++result.numberOfSubblocksWithMoreThanOneError;
        result.maximumSubblockErrorWeight =
            std::max(result.maximumSubblockErrorWeight, weight);
    }
    result.allSubblocksWithinGuaranteedRegion =
        simulationCase.organization == BchOrganization::Segmented
            ? result.maximumSubblockErrorWeight <= 1U
            : result.maximumSubblockErrorWeight <=
                  simulationCase.correctionCapability;
    return result;
}

std::uint64_t burstDomainValue(
    std::uint64_t seed, std::uint64_t frameIndex, std::uint64_t domain) {
    return mix64(mix64(seed) ^ mix64(frameIndex + 0x9e3779b97f4a7c15ULL) ^
                 mix64(domain + 0x243f6a8885a308d3ULL));
}

std::size_t uniformBurstStart(
    std::size_t frameLength, std::size_t burstLength,
    std::uint64_t seed, std::uint64_t frameIndex, std::uint64_t domain) {
    if (burstLength > frameLength) {
        throw std::invalid_argument("burst length exceeds frame length");
    }
    if (burstLength == 0U) return 0U;
    const std::uint64_t legalCount =
        static_cast<std::uint64_t>(frameLength - burstLength + 1U);
    // Rejection removes the short low-end interval which would otherwise
    // receive one extra preimage under modulo reduction. Each retry uses a
    // separate deterministic domain, so resume/shard order cannot affect it.
    const std::uint64_t threshold =
        (std::uint64_t{0} - legalCount) % legalCount;
    for (std::uint64_t attempt = 0U;; ++attempt) {
        const std::uint64_t sample = burstDomainValue(
            seed, frameIndex,
            domain ^ (attempt * 0x9e3779b97f4a7c15ULL));
        if (sample >= threshold) {
            return static_cast<std::size_t>(sample % legalCount);
        }
    }
}

}  // namespace scl::bch::simulation
