#include "cc/puncturing.hpp"

#include <cmath>
#include <stdexcept>

namespace scl::cc {

void validate_puncture_pattern(const PuncturePattern& pattern) {
    if (pattern.id.empty() || pattern.keep_mask.empty() || pattern.keep_mask.size() % 2 != 0) {
        throw std::invalid_argument("puncture pattern id/mask is invalid");
    }
    bool retained = false;
    for (auto value : pattern.keep_mask) {
        if (value > 1) {
            throw std::invalid_argument("puncture mask is not binary");
        }
        retained = retained || value == 1;
    }
    if (!retained) {
        throw std::invalid_argument("puncture pattern removes every bit");
    }
}

PuncturedBits puncture_bits(
    const std::vector<std::uint8_t>& mother_bits,
    const PuncturePattern& pattern,
    const std::size_t initial_phase) {
    validate_puncture_pattern(pattern);
    for (auto bit : mother_bits) {
        if (bit > 1) {
            throw std::invalid_argument("mother code contains non-binary value");
        }
    }
    PuncturedBits result;
    result.mother_length = mother_bits.size();
    result.bits.reserve(mother_bits.size());
    std::size_t phase = initial_phase % pattern.keep_mask.size();
    for (auto bit : mother_bits) {
        if (pattern.keep_mask[phase] != 0) {
            result.bits.push_back(bit);
        }
        phase = (phase + 1) % pattern.keep_mask.size();
    }
    result.punctured_length = mother_bits.size() - result.bits.size();
    result.final_phase = phase;
    return result;
}

DepuncturedHard depuncture_hard(
    const std::vector<std::uint8_t>& transmitted_bits,
    const std::size_t mother_length,
    const PuncturePattern& pattern,
    const std::size_t initial_phase) {
    validate_puncture_pattern(pattern);
    DepuncturedHard result;
    result.expanded_bits.assign(mother_length, 0);
    result.observed_mask.assign(mother_length, 0);
    std::size_t source = 0;
    std::size_t phase = initial_phase % pattern.keep_mask.size();
    for (std::size_t index = 0; index < mother_length; ++index) {
        if (pattern.keep_mask[phase] != 0) {
            if (source >= transmitted_bits.size() || transmitted_bits[source] > 1) {
                throw std::invalid_argument("hard depuncture source length/value mismatch");
            }
            result.expanded_bits[index] = transmitted_bits[source++];
            result.observed_mask[index] = 1;
        }
        phase = (phase + 1) % pattern.keep_mask.size();
    }
    if (source != transmitted_bits.size()) {
        throw std::invalid_argument("hard depuncture has unused source bits");
    }
    result.final_phase = phase;
    return result;
}

DepuncturedSoft depuncture_soft(
    const std::vector<double>& transmitted_values,
    const std::size_t mother_length,
    const PuncturePattern& pattern,
    const std::size_t initial_phase) {
    validate_puncture_pattern(pattern);
    DepuncturedSoft result;
    result.expanded_values.assign(mother_length, 0.0);
    result.observed_mask.assign(mother_length, 0);
    std::size_t source = 0;
    std::size_t phase = initial_phase % pattern.keep_mask.size();
    for (std::size_t index = 0; index < mother_length; ++index) {
        if (pattern.keep_mask[phase] != 0) {
            if (source >= transmitted_values.size() || !std::isfinite(transmitted_values[source])) {
                throw std::invalid_argument("soft depuncture source length/value mismatch");
            }
            result.expanded_values[index] = transmitted_values[source++];
            result.observed_mask[index] = 1;
        }
        phase = (phase + 1) % pattern.keep_mask.size();
    }
    if (source != transmitted_values.size()) {
        throw std::invalid_argument("soft depuncture has unused source values");
    }
    result.final_phase = phase;
    return result;
}

}  // namespace scl::cc
