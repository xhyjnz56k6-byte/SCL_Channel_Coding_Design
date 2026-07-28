#include "stage13_burst_interleaving_validation_core.hpp"

#include <algorithm>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace scl::bch::s2::stage13 {
namespace {

std::uint64_t splitmix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
}

std::uint64_t stableTextId(const std::string& text) {
    std::uint64_t value = 1469598103934665603ULL;
    for (const unsigned char byte : text) {
        value ^= static_cast<std::uint64_t>(byte);
        value *= 1099511628211ULL;
    }
    return value;
}

template <typename Word>
std::size_t uniformIndex(Word word, std::size_t inclusiveMaximum) {
    const std::uint64_t span = static_cast<std::uint64_t>(inclusiveMaximum) + 1U;
    const std::uint64_t threshold = static_cast<std::uint64_t>(-span) % span;
    for (std::uint64_t counter = 0U;; ++counter) {
        const std::uint64_t value = word(counter);
        if (value >= threshold) return static_cast<std::size_t>(value % span);
    }
}

std::vector<std::size_t> makeBlockPermutation(std::size_t length,
                                               std::size_t depth) {
    std::vector<std::vector<std::size_t>> segments(depth);
    const std::size_t base = length / depth;
    const std::size_t remainder = length % depth;
    std::size_t next = 0U;
    for (std::size_t segment = 0U; segment < depth; ++segment) {
        const std::size_t count = base + (segment < remainder ? 1U : 0U);
        segments[segment].reserve(count);
        for (std::size_t offset = 0U; offset < count; ++offset) {
            segments[segment].push_back(next++);
        }
    }
    std::vector<std::size_t> permutation;
    permutation.reserve(length);
    const std::size_t maximum =
        base + (remainder == 0U ? 0U : 1U);
    for (std::size_t offset = 0U; offset < maximum; ++offset) {
        // Rotating the segment visit order makes BLOCK mathematically distinct
        // from row-write/column-read even when N is divisible by depth.
        for (std::size_t visit = 0U; visit < depth; ++visit) {
            const std::size_t segment = (visit + offset) % depth;
            if (offset < segments[segment].size()) {
                permutation.push_back(segments[segment][offset]);
            }
        }
    }
    return permutation;
}

std::vector<std::size_t> makeRowColumnPermutation(std::size_t length,
                                                   std::size_t rows) {
    const std::size_t columns = (length + rows - 1U) / rows;
    std::vector<std::size_t> permutation;
    permutation.reserve(length);
    for (std::size_t column = 0U; column < columns; ++column) {
        for (std::size_t row = 0U; row < rows; ++row) {
            const std::size_t inputIndex = row * columns + column;
            if (inputIndex < length) permutation.push_back(inputIndex);
        }
    }
    return permutation;
}

std::vector<std::size_t> makePseudorandomPermutation(
    std::size_t length, const InterleaverSpec& spec) {
    if (spec.seed == 0U) {
        throw std::invalid_argument("PSEUDORANDOM interleaver seed is missing");
    }
    if (spec.caseId.empty()) {
        throw std::invalid_argument("PSEUDORANDOM caseId is missing");
    }
    std::vector<std::size_t> permutation(length);
    std::iota(permutation.begin(), permutation.end(), std::size_t{0U});
    std::uint64_t drawCounter = 0U;
    const std::uint64_t base =
        splitmix64(spec.seed ^ stableTextId(spec.caseId) ^
                   splitmix64(length) ^ splitmix64(spec.depth));
    for (std::size_t remaining = length; remaining > 1U; --remaining) {
        const auto source = [base, &drawCounter](std::uint64_t rejection) {
            return splitmix64(base ^ splitmix64(drawCounter++) ^
                              splitmix64(rejection));
        };
        const std::size_t selected = uniformIndex(source, remaining - 1U);
        std::swap(permutation[remaining - 1U], permutation[selected]);
    }
    return permutation;
}

}  // namespace

const char* interleaverModeName(InterleaverMode mode) {
    switch (mode) {
        case InterleaverMode::None: return "NONE";
        case InterleaverMode::Block: return "BLOCK";
        case InterleaverMode::RowColumn: return "ROW_COLUMN";
        case InterleaverMode::Pseudorandom: return "PSEUDORANDOM";
    }
    throw std::invalid_argument("invalid interleaver mode");
}

InterleaverMode parseInterleaverMode(const std::string& value) {
    if (value == "NONE") return InterleaverMode::None;
    if (value == "BLOCK") return InterleaverMode::Block;
    if (value == "ROW_COLUMN") return InterleaverMode::RowColumn;
    if (value == "PSEUDORANDOM") return InterleaverMode::Pseudorandom;
    throw std::invalid_argument("unknown interleaver mode");
}

std::vector<std::size_t> makePermutation(std::size_t length,
                                         const InterleaverSpec& spec) {
    if (length == 0U) throw std::invalid_argument("interleaver length is zero");
    if (spec.mode == InterleaverMode::None) {
        std::vector<std::size_t> permutation(length);
        std::iota(permutation.begin(), permutation.end(), std::size_t{0U});
        return permutation;
    }
    if (spec.depth == 0U || spec.depth > length) {
        throw std::invalid_argument("interleaver depth outside 1..N");
    }
    std::vector<std::size_t> permutation;
    if (spec.mode == InterleaverMode::Block) {
        permutation = makeBlockPermutation(length, spec.depth);
    } else if (spec.mode == InterleaverMode::RowColumn) {
        permutation = makeRowColumnPermutation(length, spec.depth);
    } else if (spec.mode == InterleaverMode::Pseudorandom) {
        permutation = makePseudorandomPermutation(length, spec);
    } else {
        throw std::invalid_argument("invalid interleaver mode");
    }
    validatePermutation(permutation);
    return permutation;
}

void validatePermutation(const std::vector<std::size_t>& permutation) {
    if (permutation.empty()) throw std::invalid_argument("permutation is empty");
    std::vector<unsigned char> seen(permutation.size(), 0U);
    for (const std::size_t value : permutation) {
        if (value >= permutation.size()) {
            throw std::invalid_argument("permutation index outside range");
        }
        if (seen[value] != 0U) {
            throw std::invalid_argument("permutation contains duplicate index");
        }
        seen[value] = 1U;
    }
}

std::vector<std::size_t> inversePermutation(
    const std::vector<std::size_t>& permutation) {
    validatePermutation(permutation);
    std::vector<std::size_t> inverse(permutation.size());
    for (std::size_t output = 0U; output < permutation.size(); ++output) {
        inverse[permutation[output]] = output;
    }
    return inverse;
}

common::BitVector applyPermutation(
    const common::BitVector& input,
    const std::vector<std::size_t>& permutation) {
    validatePermutation(permutation);
    common::validateBits(input, "interleaver input");
    if (input.size() != permutation.size()) {
        throw std::invalid_argument("interleaver input length mismatch");
    }
    common::BitVector output(input.size(), 0U);
    for (std::size_t index = 0U; index < input.size(); ++index) {
        output[index] = input[permutation[index]];
    }
    return output;
}

common::BitVector removePermutation(
    const common::BitVector& input,
    const std::vector<std::size_t>& permutation) {
    validatePermutation(permutation);
    common::validateBits(input, "deinterleaver input");
    if (input.size() != permutation.size()) {
        throw std::invalid_argument("deinterleaver input length mismatch");
    }
    common::BitVector output(input.size(), 0U);
    for (std::size_t index = 0U; index < input.size(); ++index) {
        output[permutation[index]] = input[index];
    }
    return output;
}

std::uint64_t burstRandomWord(const BurstIdentity& identity,
                              std::uint64_t counter) {
    if (identity.stageId.empty() || identity.caseId.empty()) {
        throw std::invalid_argument("burst random identity text is empty");
    }
    std::uint64_t value =
        splitmix64(identity.masterSeed ^ 0x42555253545f5354ULL);
    value = splitmix64(value ^ stableTextId(identity.stageId));
    value = splitmix64(value ^ stableTextId(identity.caseId));
    value = splitmix64(value ^ identity.parameterSetId);
    value = splitmix64(value ^ identity.snrIndex);
    value = splitmix64(value ^ identity.burstLengthIndex);
    value = splitmix64(value ^ identity.frameIndex);
    return splitmix64(value ^ counter);
}

std::size_t burstStart(const BurstIdentity& identity,
                       std::size_t encodedLength,
                       std::size_t burstLength) {
    if (encodedLength == 0U || burstLength > encodedLength) {
        throw std::invalid_argument("burst length outside 0..N");
    }
    const std::size_t maximum = encodedLength - burstLength;
    const auto source = [&identity](std::uint64_t counter) {
        return burstRandomWord(identity, counter);
    };
    return uniformIndex(source, maximum);
}

common::BitVector flipContiguousBits(const common::BitVector& input,
                                     std::size_t start,
                                     std::size_t burstLength) {
    common::validateBits(input, "burst input");
    if (start > input.size() || burstLength > input.size() - start) {
        throw std::invalid_argument("burst range outside frame");
    }
    common::BitVector output = input;
    for (std::size_t index = start; index < start + burstLength; ++index) {
        output[index] = static_cast<common::Bit>(output[index] ^ 1U);
    }
    return output;
}

AffectedBlocks affectedBlocks(
    const std::vector<std::size_t>& blockOffsets,
    const std::vector<std::size_t>& permutation,
    std::size_t burstStartIndex,
    std::size_t burstLength) {
    validatePermutation(permutation);
    if (blockOffsets.size() < 2U || blockOffsets.front() != 0U ||
        blockOffsets.back() != permutation.size() ||
        !std::is_sorted(blockOffsets.begin(), blockOffsets.end())) {
        throw std::invalid_argument("invalid block offsets");
    }
    if (burstStartIndex > permutation.size() ||
        burstLength > permutation.size() - burstStartIndex) {
        throw std::invalid_argument("affected-block burst outside frame");
    }
    std::vector<std::size_t> counts(blockOffsets.size() - 1U, 0U);
    for (std::size_t channel = burstStartIndex;
         channel < burstStartIndex + burstLength; ++channel) {
        const std::size_t original = permutation[channel];
        const auto upper = std::upper_bound(
            blockOffsets.begin(), blockOffsets.end(), original);
        const std::size_t block =
            static_cast<std::size_t>(upper - blockOffsets.begin() - 1);
        ++counts[block];
    }
    AffectedBlocks result;
    for (const std::size_t count : counts) {
        result.affectedCount += count != 0U ? 1U : 0U;
        result.maxErrorsInOneBlock =
            std::max(result.maxErrorsInOneBlock, count);
    }
    return result;
}

std::uint64_t fnv1a64(const std::vector<std::size_t>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const std::size_t value : values) {
        const std::uint64_t word = static_cast<std::uint64_t>(value);
        for (unsigned byte = 0U; byte < 8U; ++byte) {
            hash ^= (word >> (byte * 8U)) & 0xffU;
            hash *= 1099511628211ULL;
        }
    }
    return hash;
}

}  // namespace scl::bch::s2::stage13
