#ifndef SCL_BCH_SIMULATION_BCH_INTERLEAVER_HPP
#define SCL_BCH_SIMULATION_BCH_INTERLEAVER_HPP

#include "common/types.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::bch::simulation {

enum class InterleaverMode { None, FixedRandom };

struct BchInterleaver {
    InterleaverMode mode = InterleaverMode::None;
    std::uint64_t seed = 0U;
    std::vector<std::size_t> permutation;
    std::vector<std::size_t> inversePermutation;
    std::string permutationHash;
    std::string inversePermutationHash;
};

BchInterleaver makeBchInterleaver(
    std::size_t length, InterleaverMode mode, std::uint64_t seed);
void validateBchInterleaver(const BchInterleaver& interleaver);
common::BitVector interleave(
    const common::BitVector& input, const BchInterleaver& interleaver);
common::BitVector deinterleave(
    const common::BitVector& input, const BchInterleaver& interleaver);
std::string interleaverModeName(InterleaverMode mode);

}  // namespace scl::bch::simulation

#endif
