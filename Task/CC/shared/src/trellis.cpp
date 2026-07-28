#include "cc/trellis.hpp"

#include <stdexcept>

namespace scl::cc {

std::uint8_t compute_next_state(const std::uint8_t state, const std::uint8_t input_bit) {
    if (state >= kStateCount || input_bit > 1) {
        throw std::invalid_argument("invalid CC state or input bit");
    }
    return static_cast<std::uint8_t>(((input_bit & 1U) << 5U) | (state >> 1U));
}

std::array<std::uint8_t, 2> compute_output_bits(
    const std::uint8_t state,
    const std::uint8_t input_bit) {
    if (state >= kStateCount || input_bit > 1) {
        throw std::invalid_argument("invalid CC state or input bit");
    }

    const std::uint8_t m1 = static_cast<std::uint8_t>((state >> 5U) & 1U);
    const std::uint8_t m2 = static_cast<std::uint8_t>((state >> 4U) & 1U);
    const std::uint8_t m3 = static_cast<std::uint8_t>((state >> 3U) & 1U);
    const std::uint8_t m5 = static_cast<std::uint8_t>((state >> 1U) & 1U);
    const std::uint8_t m6 = static_cast<std::uint8_t>(state & 1U);

    const std::uint8_t g1 =
        static_cast<std::uint8_t>(input_bit ^ m1 ^ m2 ^ m3 ^ m6);
    const std::uint8_t g2 =
        static_cast<std::uint8_t>(input_bit ^ m2 ^ m3 ^ m5 ^ m6);
    return {g1, g2};
}

Trellis::Trellis() {
    for (std::size_t state = 0; state < kStateCount; ++state) {
        for (std::size_t input = 0; input < 2; ++input) {
            auto& item = branches_[state][input];
            item.input_bit = static_cast<std::uint8_t>(input);
            item.next_state = compute_next_state(
                static_cast<std::uint8_t>(state),
                static_cast<std::uint8_t>(input));
            item.output_bits = compute_output_bits(
                static_cast<std::uint8_t>(state),
                static_cast<std::uint8_t>(input));
        }
    }
}

const TrellisBranch& Trellis::branch(
    const std::uint8_t state,
    const std::uint8_t input_bit) const {
    if (state >= kStateCount || input_bit > 1) {
        throw std::out_of_range("invalid CC trellis lookup");
    }
    return branches_[state][input_bit];
}

const std::array<std::array<TrellisBranch, 2>, kStateCount>&
Trellis::branches() const {
    return branches_;
}

}  // namespace scl::cc
