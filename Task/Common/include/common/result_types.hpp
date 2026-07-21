#ifndef SCL_COMMON_RESULT_TYPES_HPP
#define SCL_COMMON_RESULT_TYPES_HPP

#include "common/types.hpp"

#include <cstdint>
#include <string>

namespace scl::common {

struct DecodeResult {
    BitVector payloadBits;
    bool decoderDeclaredSuccess = false;
    std::size_t iterationsUsed = 0;
    std::string decoderStatus;
};

struct PointResultRecord {
    std::string stageId;
    std::string runId;
    std::string experimentId;
    std::string caseId;
    std::string codeType;
    std::string decoderType;
    std::string channelType;
    std::string noiseGroupId;
    Length payloadLength = 0;
    Length codecInputLength = 0;
    Length encodedLength = 0;
    Length transmittedLength = 0;
    double codeRate = 0.0;
    SnrIndex snrIndex = 0;
    double ebN0_dB = 0.0;
};

struct CheckpointRecord {
    std::string stageId;
    std::string runId;
    std::string experimentId;
    std::string caseId;
    SnrIndex snrIndex = 0;
    double ebN0_dB = 0.0;
    FrameIndex nextFrameIndex = 0;
    std::uint64_t framesProcessed = 0;
    std::uint64_t payloadBitsProcessed = 0;
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
    std::uint64_t payloadSuccessFrames = 0;
    std::uint64_t decoderDeclaredSuccessFrames = 0;
    std::uint64_t undetectedErrorFrames = 0;
    double timingAccumulator = 0.0;
    double iterationAccumulator = 0.0;
    std::string configHash;
    std::string framePoolHash;
    std::string noisePolicyVersion;
    std::string codeVersion;
    std::string gitCommit;
};

}  // namespace scl::common

#endif  // SCL_COMMON_RESULT_TYPES_HPP

