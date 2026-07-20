#ifndef SCL_COMMON_FRAME_HPP
#define SCL_COMMON_FRAME_HPP

#include "common/types.hpp"

#include <stdexcept>
#include <string>

namespace scl::common {

struct PayloadFrame {
    std::string framePoolId;
    FrameIndex frameIndex = 0;
    Length payloadLength = 0;
    SeedValue masterSeed = 0;
    BitVector payloadBits;
};

inline void validatePayloadFrame(const PayloadFrame& frame) {
    if (frame.framePoolId.empty()) {
        throw std::invalid_argument("framePoolId must not be empty");
    }
    if (frame.payloadBits.size() != frame.payloadLength) {
        throw std::invalid_argument("payloadBits.size must equal payloadLength");
    }
    validateBits(frame.payloadBits, "payloadBits");
}

}  // namespace scl::common

#endif  // SCL_COMMON_FRAME_HPP

