#ifndef SCL_BCH_SIMULATION_BCH_BURST_SIMULATION_HPP
#define SCL_BCH_SIMULATION_BCH_BURST_SIMULATION_HPP

#include "bch_simulation/bch_case_adapter.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace scl::bch::simulation {

struct BurstStructure {
    std::size_t burstLength = 0U;
    std::size_t burstStart = 0U;
    std::size_t relativeStartInSubblock = 0U;
    std::size_t touchedSubblockCount = 0U;
    std::vector<std::size_t> perSubblockErrorWeights;
    std::size_t maximumSubblockErrorWeight = 0U;
    std::size_t numberOfSubblocksWithOneError = 0U;
    std::size_t numberOfSubblocksWithMoreThanOneError = 0U;
    bool allSubblocksWithinGuaranteedRegion = true;
};

common::BitVector injectConsecutiveBitBurst(
    const common::BitVector& bits, std::size_t start, std::size_t length);
std::vector<std::size_t> errorPositions(
    const common::BitVector& expected, const common::BitVector& observed);
BurstStructure analyzeBurstStructure(
    const BchSimulationCase& simulationCase,
    const std::vector<std::size_t>& positions,
    std::size_t transmittedStart,
    std::size_t transmittedLength);
std::uint64_t burstDomainValue(
    std::uint64_t seed, std::uint64_t frameIndex, std::uint64_t domain);
std::size_t uniformBurstStart(
    std::size_t frameLength, std::size_t burstLength,
    std::uint64_t seed, std::uint64_t frameIndex, std::uint64_t domain);

}  // namespace scl::bch::simulation

#endif
