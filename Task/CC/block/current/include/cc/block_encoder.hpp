#pragma once

#include "cc/trellis.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace scl::cc {

struct EncodeResult {
    std::vector<std::uint8_t> codec_input_bits;
    std::vector<std::uint8_t> mother_bits;
    std::uint8_t initial_state = kInitialState;
    std::uint8_t final_state = kInitialState;
    std::size_t payload_length = 0;
    std::size_t tail_length = 0;
};

class ConvolutionalEncoder {
public:
    explicit ConvolutionalEncoder(const Trellis& trellis, std::uint8_t initial_state = kInitialState);

    void reset(std::uint8_t initial_state = kInitialState);
    std::uint8_t state() const;
    void import_state(std::uint8_t state);

    void encode_segment(
        const std::vector<std::uint8_t>& input_bits,
        std::vector<std::uint8_t>& output_bits);

    EncodeResult encode_block(
        const std::vector<std::uint8_t>& payload_bits,
        bool append_zero_tail = true,
        std::uint8_t initial_state = kInitialState);

private:
    const Trellis& trellis_;
    std::uint8_t state_;
};

}  // namespace scl::cc
