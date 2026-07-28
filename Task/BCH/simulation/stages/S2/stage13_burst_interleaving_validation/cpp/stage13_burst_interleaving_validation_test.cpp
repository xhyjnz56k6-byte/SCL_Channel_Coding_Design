#include "stage13_burst_interleaving_validation_core.hpp"
#include "stage02_case_contract.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using scl::bch::s2::stage13::InterleaverMode;
using scl::bch::s2::stage13::InterleaverSpec;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void requireInvalid(const std::function<void()>& operation,
                    const std::string& message) {
    bool rejected = false;
    try {
        operation();
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected, message);
}

scl::common::BitVector pattern(std::size_t length, unsigned kind) {
    scl::common::BitVector bits(length, 0U);
    for (std::size_t index = 0U; index < length; ++index) {
        if (kind == 1U) bits[index] = 1U;
        else if (kind == 2U) bits[index] = static_cast<unsigned>(index & 1U);
        else if (kind == 3U) bits[index] = index == length / 2U ? 1U : 0U;
        else if (kind == 4U) bits[index] =
            static_cast<unsigned>(((index * 37U + 11U) ^ (index >> 1U)) & 1U);
    }
    return bits;
}

}  // namespace

int main() {
    try {
        namespace stage13 = scl::bch::s2::stage13;
        const std::vector<InterleaverMode> modes{
            InterleaverMode::None, InterleaverMode::Block,
            InterleaverMode::RowColumn, InterleaverMode::Pseudorandom};
        const std::vector<std::size_t> depths{4U, 8U, 16U};

        for (const auto& contract :
             scl::bch::s2::stage02::allCaseContracts()) {
            for (const std::size_t depth : depths) {
                std::vector<std::size_t> blockPermutation;
                std::vector<std::size_t> rowColumnPermutation;
                for (const InterleaverMode mode : modes) {
                    const InterleaverSpec spec{
                        mode, mode == InterleaverMode::None ? 1U : depth,
                        mode == InterleaverMode::Pseudorandom
                            ? 1140071481932319848ULL : 0U,
                        contract.caseId};
                    const auto permutation =
                        stage13::makePermutation(contract.totalEncodedLength, spec);
                    require(permutation.size() == contract.totalEncodedLength,
                            "permutation length mismatch");
                    const auto inverse = stage13::inversePermutation(permutation);
                    for (std::size_t index = 0U;
                         index < permutation.size(); ++index) {
                        require(inverse[permutation[index]] == index,
                                "inverse permutation mismatch");
                    }
                    for (unsigned kind = 0U; kind < 5U; ++kind) {
                        const auto input =
                            pattern(contract.totalEncodedLength, kind);
                        const auto interleaved =
                            stage13::applyPermutation(input, permutation);
                        require(interleaved.size() == input.size(),
                                "interleaved length changed");
                        require(stage13::removePermutation(
                                    interleaved, permutation) == input,
                                "interleave/deinterleave did not round trip");
                    }
                    if (mode == InterleaverMode::Block) {
                        blockPermutation = permutation;
                    } else if (mode == InterleaverMode::RowColumn) {
                        rowColumnPermutation = permutation;
                    }
                    if (mode == InterleaverMode::Pseudorandom) {
                        require(permutation == stage13::makePermutation(
                                contract.totalEncodedLength, spec),
                                "pseudorandom permutation changed");
                    }
                }
                require(blockPermutation != rowColumnPermutation,
                        "BLOCK and ROW_COLUMN unexpectedly identical");
            }
        }

        const scl::common::BitVector bits{0U, 1U, 0U, 1U, 1U};
        require(stage13::flipContiguousBits(bits, 0U, 0U) == bits,
                "L=0 changed bits");
        require(stage13::flipContiguousBits(bits, 0U, bits.size()) ==
                    scl::common::BitVector({1U, 0U, 1U, 0U, 0U}),
                "L=N did not flip whole frame");
        require(stage13::flipContiguousBits(bits, 3U, 2U) ==
                    scl::common::BitVector({0U, 1U, 0U, 0U, 0U}),
                "tail burst mismatch");

        const stage13::BurstIdentity identity{
            1397048147U, "bch_s2_burst_shared", "K300_M255K207",
            9U, 0U, 4U, 123U};
        const auto start = stage13::burstStart(identity, 396U, 20U);
        require(start <= 376U &&
                    start == stage13::burstStart(identity, 396U, 20U),
                "burst start is not deterministic/legal");
        require(stage13::burstStart(identity, 396U, 396U) == 0U,
                "full-frame burst must start at zero");

        const auto identityPermutation = stage13::makePermutation(
            10U, {InterleaverMode::None, 1U, 0U, "case"});
        const auto affected = stage13::affectedBlocks(
            {0U, 5U, 10U}, identityPermutation, 3U, 5U);
        require(affected.affectedCount == 2U &&
                    affected.maxErrorsInOneBlock == 3U,
                "affected-block accounting mismatch");

        requireInvalid([] {
            stage13::makePermutation(
                0U, {InterleaverMode::None, 1U, 0U, "case"});
        }, "zero length accepted");
        requireInvalid([] {
            stage13::makePermutation(
                10U, {InterleaverMode::Block, 0U, 0U, "case"});
        }, "D=0 accepted");
        requireInvalid([] {
            stage13::makePermutation(
                10U, {InterleaverMode::RowColumn, 11U, 0U, "case"});
        }, "D>N accepted");
        requireInvalid([] {
            stage13::makePermutation(
                10U, {InterleaverMode::Pseudorandom, 4U, 0U, "case"});
        }, "missing pseudorandom seed accepted");
        requireInvalid([] {
            stage13::parseInterleaverMode("INVALID");
        }, "invalid mode accepted");
        requireInvalid([] {
            stage13::validatePermutation({0U, 1U, 1U});
        }, "duplicate permutation accepted");
        requireInvalid([] {
            stage13::validatePermutation({0U, 2U});
        }, "out-of-range permutation accepted");
        requireInvalid([&bits] {
            stage13::flipContiguousBits(bits, 4U, 2U);
        }, "wrapped burst accepted");
        requireInvalid([&identity] {
            stage13::burstStart(identity, 10U, 11U);
        }, "L>N accepted");
        requireInvalid([&identityPermutation] {
            stage13::affectedBlocks(
                {1U, 5U, 10U}, identityPermutation, 0U, 1U);
        }, "invalid block offsets accepted");

        std::cout <<
            "PASS_STAGE13_BURST_INTERLEAVING_VALIDATION_UNIT_TEST\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr <<
            "BLOCKED_STAGE13_BURST_INTERLEAVING_VALIDATION_UNIT_TEST: "
                  << error.what() << '\n';
        return 1;
    }
}

