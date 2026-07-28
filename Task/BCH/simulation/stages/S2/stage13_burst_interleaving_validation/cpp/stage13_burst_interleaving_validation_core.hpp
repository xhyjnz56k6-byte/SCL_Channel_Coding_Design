#ifndef SCL_BCH_S2_STAGE13_BURST_INTERLEAVING_VALIDATION_CORE_HPP
#define SCL_BCH_S2_STAGE13_BURST_INTERLEAVING_VALIDATION_CORE_HPP

#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::s2::stage13 {

enum class InterleaverMode {
    None,
    Block,
    RowColumn,
    Pseudorandom
};

struct BurstIdentity {
    std::uint64_t masterSeed = 0U;
    std::string stageId;
    std::string caseId;
    std::uint64_t parameterSetId = 0U;
    std::uint64_t snrIndex = 0U;
    std::uint64_t burstLengthIndex = 0U;
    std::uint64_t frameIndex = 0U;
};

struct InterleaverSpec {
    InterleaverMode mode = InterleaverMode::None;
    std::size_t depth = 1U;
    std::uint64_t seed = 0U;
    std::string caseId;
};

struct AffectedBlocks {
    std::size_t affectedCount = 0U;
    std::size_t maxErrorsInOneBlock = 0U;
};

const char* interleaverModeName(InterleaverMode mode);
InterleaverMode parseInterleaverMode(const std::string& value);

std::vector<std::size_t> makePermutation(std::size_t length,
                                         const InterleaverSpec& spec);
void validatePermutation(const std::vector<std::size_t>& permutation);
std::vector<std::size_t> inversePermutation(
    const std::vector<std::size_t>& permutation);
common::BitVector applyPermutation(
    const common::BitVector& input,
    const std::vector<std::size_t>& permutation);
common::BitVector removePermutation(
    const common::BitVector& input,
    const std::vector<std::size_t>& permutation);

std::uint64_t burstRandomWord(const BurstIdentity& identity,
                              std::uint64_t counter);
std::size_t burstStart(const BurstIdentity& identity,
                       std::size_t encodedLength,
                       std::size_t burstLength);
common::BitVector flipContiguousBits(const common::BitVector& input,
                                     std::size_t start,
                                     std::size_t burstLength);

AffectedBlocks affectedBlocks(
    const std::vector<std::size_t>& blockOffsets,
    const std::vector<std::size_t>& permutation,
    std::size_t burstStartIndex,
    std::size_t burstLength);

std::uint64_t fnv1a64(const std::vector<std::size_t>& values);

}  // namespace scl::bch::s2::stage13

#endif

