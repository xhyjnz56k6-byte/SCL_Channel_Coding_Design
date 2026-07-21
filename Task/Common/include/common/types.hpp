#ifndef SCL_COMMON_TYPES_HPP
#define SCL_COMMON_TYPES_HPP

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace scl::common {

using Bit = std::uint8_t;
using FrameIndex = std::uint64_t;
using SeedValue = std::uint64_t;
using Length = std::size_t;
using SnrIndex = std::size_t;
using BitVector = std::vector<Bit>;
using RealVector = std::vector<double>;

inline bool isValidBit(Bit bit) {
    return bit == static_cast<Bit>(0) || bit == static_cast<Bit>(1);
}

inline void validateBit(Bit bit, const std::string& fieldName) {
    if (!isValidBit(bit)) {
        throw std::invalid_argument(fieldName + " contains a non-binary bit");
    }
}

inline void validateBits(const BitVector& bits, const std::string& fieldName) {
    for (Bit bit : bits) {
        validateBit(bit, fieldName);
    }
}

struct CodeLengths {
    Length payloadLength = 0;
    Length codecInputLength = 0;
    Length encodedLength = 0;
    Length transmittedLength = 0;
    Length fillerLength = 0;
    Length crcLength = 0;
    Length tailLength = 0;
    Length puncturedLength = 0;
    Length shortenedLength = 0;
};

inline void validateCodeLengths(const CodeLengths& lengths) {
    if (lengths.payloadLength == 0) {
        throw std::invalid_argument("payloadLength must be positive");
    }
    if (lengths.encodedLength == 0) {
        throw std::invalid_argument("encodedLength must be positive");
    }
    if (lengths.transmittedLength == 0) {
        throw std::invalid_argument("transmittedLength must be positive");
    }
    if (lengths.codecInputLength < lengths.payloadLength) {
        throw std::invalid_argument("codecInputLength must be >= payloadLength");
    }
}

inline double computeCodeRate(const CodeLengths& lengths) {
    validateCodeLengths(lengths);
    return static_cast<double>(lengths.payloadLength) /
           static_cast<double>(lengths.encodedLength);
}

}  // namespace scl::common

#endif  // SCL_COMMON_TYPES_HPP

