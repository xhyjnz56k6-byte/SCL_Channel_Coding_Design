#ifndef SCL_COMMON_DECODER_INPUT_HPP
#define SCL_COMMON_DECODER_INPUT_HPP

#include "common/types.hpp"

#include <variant>

namespace scl::common {

enum class DecoderInputKind {
    HardBits,
    ReceivedSymbols,
    LlrValues
};

struct HardBitInput {
    BitVector hardBits;
};

struct ReceivedSymbolInput {
    RealVector receivedSymbols;
};

struct LlrInput {
    RealVector llrValues;
};

using DecoderInput = std::variant<HardBitInput, ReceivedSymbolInput, LlrInput>;

inline DecoderInputKind decoderInputKind(const DecoderInput& input) {
    if (std::holds_alternative<HardBitInput>(input)) {
        return DecoderInputKind::HardBits;
    }
    if (std::holds_alternative<ReceivedSymbolInput>(input)) {
        return DecoderInputKind::ReceivedSymbols;
    }
    return DecoderInputKind::LlrValues;
}

}  // namespace scl::common

#endif  // SCL_COMMON_DECODER_INPUT_HPP

