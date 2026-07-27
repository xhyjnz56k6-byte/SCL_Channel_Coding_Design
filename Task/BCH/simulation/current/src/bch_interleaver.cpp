#include "bch_simulation/bch_interleaver.hpp"

#include <algorithm>
#include <iomanip>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>

namespace scl::bch::simulation {
namespace {

std::string hashIndices(const std::vector<std::size_t>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (std::size_t value : values) {
        for (unsigned byte = 0U; byte < 8U; ++byte) {
            hash ^= static_cast<std::uint8_t>(
                (static_cast<std::uint64_t>(value) >> (8U * byte)) & 0xffU);
            hash *= 1099511628211ULL;
        }
    }
    std::ostringstream text;
    text << std::hex << std::setfill('0') << std::setw(16) << hash;
    return text.str();
}

}  // namespace

BchInterleaver makeBchInterleaver(
    std::size_t length, InterleaverMode mode, std::uint64_t seed) {
    if (length == 0U) throw std::invalid_argument("interleaver length is zero");
    BchInterleaver result;
    result.mode = mode;
    result.seed = seed;
    result.permutation.resize(length);
    std::iota(result.permutation.begin(), result.permutation.end(), 0U);
    if (mode == InterleaverMode::FixedRandom) {
        std::mt19937_64 engine(seed);
        std::shuffle(result.permutation.begin(), result.permutation.end(), engine);
    }
    result.inversePermutation.resize(length);
    for (std::size_t output = 0U; output < length; ++output) {
        result.inversePermutation[result.permutation[output]] = output;
    }
    result.permutationHash = hashIndices(result.permutation);
    result.inversePermutationHash = hashIndices(result.inversePermutation);
    validateBchInterleaver(result);
    return result;
}

void validateBchInterleaver(const BchInterleaver& value) {
    const std::size_t length = value.permutation.size();
    if (length == 0U || value.inversePermutation.size() != length) {
        throw std::invalid_argument("invalid interleaver dimensions");
    }
    std::vector<bool> seen(length, false);
    for (std::size_t output = 0U; output < length; ++output) {
        const std::size_t input = value.permutation[output];
        if (input >= length || seen[input]) {
            throw std::invalid_argument("interleaver permutation is not bijective");
        }
        seen[input] = true;
        if (value.inversePermutation[input] != output) {
            throw std::invalid_argument("interleaver inverse is inconsistent");
        }
    }
}

common::BitVector interleave(
    const common::BitVector& input, const BchInterleaver& value) {
    validateBchInterleaver(value);
    common::validateBits(input, "interleaver input");
    if (input.size() != value.permutation.size()) {
        throw std::invalid_argument("interleaver input length mismatch");
    }
    common::BitVector output(input.size());
    for (std::size_t index = 0U; index < input.size(); ++index) {
        output[index] = input[value.permutation[index]];
    }
    return output;
}

common::BitVector deinterleave(
    const common::BitVector& input, const BchInterleaver& value) {
    validateBchInterleaver(value);
    common::validateBits(input, "deinterleaver input");
    if (input.size() != value.permutation.size()) {
        throw std::invalid_argument("deinterleaver input length mismatch");
    }
    common::BitVector output(input.size());
    for (std::size_t original = 0U; original < input.size(); ++original) {
        output[original] = input[value.inversePermutation[original]];
    }
    return output;
}

std::string interleaverModeName(InterleaverMode mode) {
    return mode == InterleaverMode::None ? "NONE" : "FIXED_RANDOM";
}

}  // namespace scl::bch::simulation
