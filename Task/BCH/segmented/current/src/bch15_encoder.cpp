#include "bch_segmented/bch15_encoder.hpp"

#include <cstdint>
#include <stdexcept>

namespace scl::bch::segmented {
namespace {

constexpr std::uint16_t kGenerator = 0x13U;  // x^4 + x + 1

std::uint16_t messageToShiftedDividend(const common::BitVector& messageBits) {
    std::uint16_t dividend = 0U;
    for (common::Length index = 0; index < kBch15MessageLength; ++index) {
        dividend |= static_cast<std::uint16_t>(messageBits[index])
                    << static_cast<unsigned>(kBch15CodewordLength - 1U - index);
    }
    return dividend;
}

}  // namespace

common::BitVector encodeBch15Systematic(const common::BitVector& messageBits) {
    if (messageBits.size() != kBch15MessageLength) {
        throw std::invalid_argument("BCH(15,11,1) message length must be 11");
    }
    common::validateBits(messageBits, "BCH(15,11,1) messageBits");

    const std::uint16_t shiftedDividend = messageToShiftedDividend(messageBits);
    std::uint16_t division = shiftedDividend;
    for (int degree = 14; degree >= 4; --degree) {
        if ((division & (static_cast<std::uint16_t>(1U) << degree)) != 0U) {
            division ^= static_cast<std::uint16_t>(kGenerator << (degree - 4));
        }
    }
    const std::uint16_t codeword = static_cast<std::uint16_t>(shiftedDividend | (division & 0x0FU));
    common::BitVector result(kBch15CodewordLength, 0U);
    for (common::Length index = 0; index < kBch15CodewordLength; ++index) {
        result[index] = static_cast<common::Bit>((codeword >> (kBch15CodewordLength - 1U - index)) & 1U);
    }
    return result;
}

}  // namespace scl::bch::segmented
