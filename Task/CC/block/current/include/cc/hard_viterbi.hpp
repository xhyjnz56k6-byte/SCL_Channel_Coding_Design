#pragma once

#include "cc/trellis.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace scl::cc {

struct HardViterbiResult {
    std::vector<std::uint8_t> codec_input_bits;
    std::vector<std::uint8_t> payload_bits;
    std::int32_t final_path_metric = 0;
    std::size_t normalization_count = 0;
    std::size_t tie_count = 0;
    std::size_t overflow_count = 0;
    std::uint8_t traceback_final_state = 0;
};

class HardViterbiDecoder {
public:
    explicit HardViterbiDecoder(const Trellis& trellis);

    HardViterbiResult decode_terminated_mother(
        const std::vector<std::uint8_t>& received_bits,
        std::size_t codec_input_length,
        std::size_t tail_length = kMemory,
        std::uint8_t initial_state = 0,
        std::uint8_t final_state = 0) const;

    HardViterbiResult decode_terminated_masked(
        const std::vector<std::uint8_t>& expanded_bits,
        const std::vector<std::uint8_t>& observed_mask,
        std::size_t codec_input_length,
        std::size_t tail_length = kMemory,
        std::uint8_t initial_state = 0,
        std::uint8_t final_state = 0) const;

private:
    const Trellis& trellis_;
};

}  // namespace scl::cc
