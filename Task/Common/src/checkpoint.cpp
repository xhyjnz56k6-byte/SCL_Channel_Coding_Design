#include "common/checkpoint.hpp"

#include "common/frame_pool.hpp"
#include "common/sha256.hpp"

#include <cmath>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace scl::common {

namespace {
std::string jsonString(const std::string& value) {
    std::string out = "\"";
    for (char c : value) {
        if (c == '"' || c == '\\') {
            out.push_back('\\');
        }
        out.push_back(c);
    }
    out.push_back('"');
    return out;
}
}

std::string canonicalConfigText(const std::string& caseName,
                                Length payloadLength,
                                Length encodedLength,
                                const std::string& ebN0List,
                                const std::string& framePoolId,
                                const std::string& noisePoolId,
                                const std::string& stopConfig,
                                const std::string& decoderInputMode) {
    std::ostringstream out;
    out << "caseName=" << caseName << '\n';
    out << "payloadLength=" << payloadLength << '\n';
    out << "encodedLength=" << encodedLength << '\n';
    out << "ebN0List=" << ebN0List << '\n';
    out << "framePoolId=" << framePoolId << '\n';
    out << "noisePoolId=" << noisePoolId << '\n';
    out << "stopConfig=" << stopConfig << '\n';
    out << "decoderInputMode=" << decoderInputMode << '\n';
    return out.str();
}

std::string computeConfigHash(const std::string& canonicalText) {
    return sha256Hex(canonicalText);
}

std::string checkpointToJson(const SimulationCheckpointRecord& record) {
    std::ostringstream out;
    out << "{\n";
    out << "\"schemaVersion\":" << jsonString(record.schemaVersion) << ",\n";
    out << "\"experimentId\":" << jsonString(record.experimentId) << ",\n";
    out << "\"configHash\":" << jsonString(record.configHash) << ",\n";
    out << "\"framePoolId\":" << jsonString(record.framePoolId) << ",\n";
    out << "\"noisePoolId\":" << jsonString(record.noisePoolId) << ",\n";
    out << "\"payloadLength\":" << record.payloadLength << ",\n";
    out << "\"encodedLength\":" << record.encodedLength << ",\n";
    out << "\"snrIndex\":" << record.snrIndex << ",\n";
    out << "\"ebN0_dB\":" << record.ebN0_dB << ",\n";
    out << "\"nextFrameIndex\":" << record.nextFrameIndex << ",\n";
    out << "\"processedFrames\":" << record.metrics.processedFrames << ",\n";
    out << "\"totalPayloadBits\":" << record.metrics.totalPayloadBits << ",\n";
    out << "\"bitErrors\":" << record.metrics.bitErrors << ",\n";
    out << "\"frameErrors\":" << record.metrics.frameErrors << ",\n";
    out << "\"successfulFrames\":" << record.metrics.successfulFrames << ",\n";
    out << "\"stopReason\":" << jsonString(record.stopReason) << "\n";
    out << "}\n";
    return out.str();
}

SimulationCheckpointRecord checkpointFromJson(const std::string& text) {
    SimulationCheckpointRecord record;
    record.schemaVersion = extractJsonString(text, "schemaVersion");
    if (record.schemaVersion != kCheckpointSchemaVersion) {
        throw std::invalid_argument("unsupported checkpoint schemaVersion");
    }
    record.experimentId = extractJsonString(text, "experimentId");
    record.configHash = extractJsonString(text, "configHash");
    record.framePoolId = extractJsonString(text, "framePoolId");
    record.noisePoolId = extractJsonString(text, "noisePoolId");
    record.payloadLength = static_cast<Length>(extractJsonUInt64(text, "payloadLength"));
    record.encodedLength = static_cast<Length>(extractJsonUInt64(text, "encodedLength"));
    record.snrIndex = static_cast<SnrIndex>(extractJsonUInt64(text, "snrIndex"));
    const std::regex ebPattern("\"ebN0_dB\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?)");
    std::smatch match;
    if (std::regex_search(text, match, ebPattern)) {
        record.ebN0_dB = std::stod(match[1].str());
    } else {
        throw std::runtime_error("checkpoint missing ebN0_dB");
    }
    record.nextFrameIndex = static_cast<FrameIndex>(extractJsonUInt64(text, "nextFrameIndex"));
    record.metrics.processedFrames = extractJsonUInt64(text, "processedFrames");
    record.metrics.totalPayloadBits = extractJsonUInt64(text, "totalPayloadBits");
    record.metrics.bitErrors = extractJsonUInt64(text, "bitErrors");
    record.metrics.frameErrors = extractJsonUInt64(text, "frameErrors");
    record.metrics.successfulFrames = extractJsonUInt64(text, "successfulFrames");
    record.stopReason = extractJsonString(text, "stopReason");
    return record;
}

void validateResumeCompatibility(const SimulationCheckpointRecord& expected, const SimulationCheckpointRecord& actual) {
    if (expected.schemaVersion != actual.schemaVersion || expected.experimentId != actual.experimentId ||
        expected.configHash != actual.configHash || expected.framePoolId != actual.framePoolId ||
        expected.noisePoolId != actual.noisePoolId || expected.payloadLength != actual.payloadLength ||
        expected.encodedLength != actual.encodedLength || expected.snrIndex != actual.snrIndex ||
        expected.ebN0_dB != actual.ebN0_dB || actual.nextFrameIndex < expected.nextFrameIndex) {
        throw std::invalid_argument("checkpoint resume compatibility mismatch");
    }
}

}  // namespace scl::common
