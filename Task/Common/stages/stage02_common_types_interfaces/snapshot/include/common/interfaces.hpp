#ifndef SCL_COMMON_INTERFACES_HPP
#define SCL_COMMON_INTERFACES_HPP

#include "common/decoder_input.hpp"
#include "common/frame.hpp"
#include "common/result_types.hpp"
#include "common/types.hpp"

#include <string>

namespace scl::common {

class IChannelEncoder {
public:
    virtual ~IChannelEncoder() = default;

    virtual std::string codeType() const = 0;
    virtual CodeLengths lengths() const = 0;
    virtual BitVector encode(const BitVector& payload) const = 0;
};

class IChannelDecoder {
public:
    virtual ~IChannelDecoder() = default;

    virtual std::string decoderType() const = 0;
    virtual DecoderInputKind inputKind() const = 0;
    virtual DecodeResult decode(const DecoderInput& input) const = 0;
};

struct ChannelTransmissionRequest {
    BitVector codedBits;
    CodeLengths lengths;
    double ebN0_dB = 0.0;
};

struct ChannelTransmissionView {
    RealVector receivedSymbols;
};

class IChannel {
public:
    virtual ~IChannel() = default;

    virtual std::string channelType() const = 0;
    virtual ChannelTransmissionView transmit(const ChannelTransmissionRequest& request) const = 0;
};

class IFramePoolReader {
public:
    virtual ~IFramePoolReader() = default;

    virtual std::string framePoolId() const = 0;
    virtual Length payloadLength() const = 0;
    virtual std::uint64_t frameCount() const = 0;
    virtual PayloadFrame readFrame(FrameIndex index) const = 0;
};

}  // namespace scl::common

#endif  // SCL_COMMON_INTERFACES_HPP

