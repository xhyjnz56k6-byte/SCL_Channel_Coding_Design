#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace scl::cc {

constexpr std::size_t kConstraintLength = 7;
constexpr std::size_t kMemory = 6;
constexpr std::size_t kStateCount = 64;
constexpr std::size_t kOutputBitsPerInput = 2;
constexpr std::uint8_t kInitialState = 0;

struct TrellisBranch {
    std::uint8_t input_bit = 0;
    std::uint8_t next_state = 0;
    std::array<std::uint8_t, kOutputBitsPerInput> output_bits{};
};

class Trellis {
public:
    Trellis();

    const TrellisBranch& branch(std::uint8_t state, std::uint8_t input_bit) const;
    const std::array<std::array<TrellisBranch, 2>, kStateCount>& branches() const;

private:
    std::array<std::array<TrellisBranch, 2>, kStateCount> branches_{};
};

std::uint8_t compute_next_state(std::uint8_t state, std::uint8_t input_bit);
std::array<std::uint8_t, 2> compute_output_bits(std::uint8_t state, std::uint8_t input_bit);

}  // namespace scl::cc
