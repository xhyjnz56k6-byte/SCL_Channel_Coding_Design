#include "cc/block_encoder.hpp"

#include <stdexcept>

namespace scl::cc {

namespace {

void validate_state(const std::uint8_t state) {
    if (state >= kStateCount) {
        throw std::invalid_argument("CC encoder state must be in [0, 63]");
    }
}

void validate_bits(const std::vector<std::uint8_t>& bits) {
    for (const std::uint8_t bit : bits) {
        if (bit > 1) {
            throw std::invalid_argument("CC encoder input contains a non-binary value");
        }
    }
}

}  // namespace

ConvolutionalEncoder::ConvolutionalEncoder(
    const Trellis& trellis,
    const std::uint8_t initial_state)
    : trellis_(trellis), state_(initial_state) {
    validate_state(initial_state);
}

void ConvolutionalEncoder::reset(const std::uint8_t initial_state) {
    validate_state(initial_state);
    state_ = initial_state;
}

std::uint8_t ConvolutionalEncoder::state() const {
    return state_;
}

void ConvolutionalEncoder::import_state(const std::uint8_t state) {
    validate_state(state);
    state_ = state;
}

void ConvolutionalEncoder::encode_segment(
    const std::vector<std::uint8_t>& input_bits,
    std::vector<std::uint8_t>& output_bits) {
    validate_bits(input_bits);
    output_bits.reserve(output_bits.size() + input_bits.size() * kOutputBitsPerInput);
    for (const std::uint8_t bit : input_bits) {
        const TrellisBranch& branch = trellis_.branch(state_, bit);
        output_bits.push_back(branch.output_bits[0]);
        output_bits.push_back(branch.output_bits[1]);
        state_ = branch.next_state;
    }
}

EncodeResult ConvolutionalEncoder::encode_block(
    const std::vector<std::uint8_t>& payload_bits,
    const bool append_zero_tail,
    const std::uint8_t initial_state) {
    validate_bits(payload_bits);
    reset(initial_state);

    EncodeResult result;
    result.initial_state = initial_state;
    result.payload_length = payload_bits.size();
    result.tail_length = append_zero_tail ? kMemory : 0;
    result.codec_input_bits.reserve(result.payload_length + result.tail_length);
    result.codec_input_bits.insert(
        result.codec_input_bits.end(),
        payload_bits.begin(),
        payload_bits.end());
    result.codec_input_bits.insert(
        result.codec_input_bits.end(),
        result.tail_length,
        static_cast<std::uint8_t>(0));
    result.mother_bits.reserve(result.codec_input_bits.size() * kOutputBitsPerInput);
    encode_segment(result.codec_input_bits, result.mother_bits);
    result.final_state = state_;

    if (result.mother_bits.size() != result.codec_input_bits.size() * 2) {
        throw std::logic_error("CC encoder output length invariant failed");
    }
    if (append_zero_tail && result.final_state != 0) {
        throw std::logic_error("CC zero-tail encoder did not terminate in state 0");
    }
    return result;
}

}  // namespace scl::cc
