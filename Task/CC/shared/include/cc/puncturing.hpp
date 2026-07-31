#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace scl::cc {

struct PuncturePattern {
    std::string id;
    std::vector<std::uint8_t> keep_mask;
};

struct PuncturedBits {
    std::vector<std::uint8_t> bits;
    std::size_t mother_length = 0;
    std::size_t punctured_length = 0;
    std::size_t final_phase = 0;
};

struct DepuncturedHard {
    std::vector<std::uint8_t> expanded_bits;
    std::vector<std::uint8_t> observed_mask;
    std::size_t final_phase = 0;
};

struct DepuncturedSoft {
    std::vector<double> expanded_values;
    std::vector<std::uint8_t> observed_mask;
    std::size_t final_phase = 0;
};

void validate_puncture_pattern(const PuncturePattern& pattern);
PuncturedBits puncture_bits(
    const std::vector<std::uint8_t>& mother_bits,
    const PuncturePattern& pattern,
    std::size_t initial_phase = 0);
DepuncturedHard depuncture_hard(
    const std::vector<std::uint8_t>& transmitted_bits,
    std::size_t mother_length,
    const PuncturePattern& pattern,
    std::size_t initial_phase = 0);
DepuncturedSoft depuncture_soft(
    const std::vector<double>& transmitted_values,
    std::size_t mother_length,
    const PuncturePattern& pattern,
    std::size_t initial_phase = 0);

}  // namespace scl::cc
