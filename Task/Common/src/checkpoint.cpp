#include "common/checkpoint.hpp"

#include "common/frame_pool.hpp"
#include "common/sha256.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <regex>
#include <sstream>
#include <stdexcept>
#ifdef _WIN32
#include <windows.h>
#endif

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

std::uint64_t optionalUInt64(const std::string& text, const std::string& key, std::uint64_t fallback = 0U) {
    const std::regex pattern("\"" + key + "\"\\s*:\\s*([0-9]+)");
    std::smatch match;
    return std::regex_search(text, match, pattern) ? static_cast<std::uint64_t>(std::stoull(match[1].str())) : fallback;
}

std::string optionalString(const std::string& text, const std::string& key) {
    const std::regex pattern("\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
    std::smatch match;
    return std::regex_search(text, match, pattern) ? match[1].str() : std::string{};
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
    out << "\"encodeTimeNsSum\":" << record.metrics.latency.encodeTimeNsSum << ",\n";
    out << "\"channelTimeNsSum\":" << record.metrics.latency.channelTimeNsSum << ",\n";
    out << "\"decodeTimeNsSum\":" << record.metrics.latency.decodeTimeNsSum << ",\n";
    out << "\"recoveryTimeNsSum\":" << record.metrics.latency.recoveryTimeNsSum << ",\n";
    out << "\"totalTimeNsSum\":" << record.metrics.latency.totalTimeNsSum << ",\n";
    out << "\"maxDecodeTimeNs\":" << record.metrics.latency.maxDecodeTimeNs << ",\n";
    out << "\"maxTotalTimeNs\":" << record.metrics.latency.maxTotalTimeNs << ",\n";
    out << "\"channelHardBitErrors\":" << record.channelHardBitErrors << ",\n";
    out << "\"channelHardFrameErrors\":" << record.channelHardFrameErrors << ",\n";
    out << "\"reportedSuccessFrames\":" << record.reportedSuccessFrames << ",\n";
    out << "\"miscorrectedFrames\":" << record.miscorrectedFrames << ",\n";
    out << "\"decoderFailureFrames\":" << record.decoderFailureFrames << ",\n";
    out << "\"noErrorStatusFrames\":" << record.noErrorStatusFrames << ",\n";
    out << "\"correctedStatusFrames\":" << record.correctedStatusFrames << ",\n";
    out << "\"failedStatusFrames\":" << record.failedStatusFrames << ",\n";
    out << "\"noisePolicyVersion\":" << record.noisePolicyVersion << ",\n";
    out << "\"globalSeed\":" << record.globalSeed << ",\n";
    out << "\"shardIndex\":" << record.shardIndex << ",\n";
    out << "\"shardCount\":" << record.shardCount << ",\n";
    out << "\"checkpointCount\":" << record.checkpointCount << ",\n";
    out << "\"timestamp\":" << jsonString(record.timestamp) << ",\n";
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
    record.metrics.latency.encodeTimeNsSum = extractJsonUInt64(text, "encodeTimeNsSum");
    record.metrics.latency.channelTimeNsSum = extractJsonUInt64(text, "channelTimeNsSum");
    record.metrics.latency.decodeTimeNsSum = extractJsonUInt64(text, "decodeTimeNsSum");
    record.metrics.latency.recoveryTimeNsSum = extractJsonUInt64(text, "recoveryTimeNsSum");
    record.metrics.latency.totalTimeNsSum = extractJsonUInt64(text, "totalTimeNsSum");
    record.metrics.latency.maxDecodeTimeNs = extractJsonUInt64(text, "maxDecodeTimeNs");
    record.metrics.latency.maxTotalTimeNs = extractJsonUInt64(text, "maxTotalTimeNs");
    record.channelHardBitErrors = optionalUInt64(text, "channelHardBitErrors");
    record.channelHardFrameErrors = optionalUInt64(text, "channelHardFrameErrors");
    record.reportedSuccessFrames = optionalUInt64(text, "reportedSuccessFrames");
    record.miscorrectedFrames = optionalUInt64(text, "miscorrectedFrames");
    record.decoderFailureFrames = optionalUInt64(text, "decoderFailureFrames");
    record.noErrorStatusFrames = optionalUInt64(text, "noErrorStatusFrames");
    record.correctedStatusFrames = optionalUInt64(text, "correctedStatusFrames");
    record.failedStatusFrames = optionalUInt64(text, "failedStatusFrames");
    record.noisePolicyVersion = optionalUInt64(text, "noisePolicyVersion");
    record.globalSeed = optionalUInt64(text, "globalSeed");
    record.shardIndex = optionalUInt64(text, "shardIndex");
    record.shardCount = optionalUInt64(text, "shardCount", 1U);
    record.checkpointCount = optionalUInt64(text, "checkpointCount");
    record.timestamp = optionalString(text, "timestamp");
    record.stopReason = extractJsonString(text, "stopReason");
    return record;
}

void validateResumeCompatibility(const SimulationCheckpointRecord& expected, const SimulationCheckpointRecord& actual) {
    if (expected.schemaVersion != actual.schemaVersion || expected.experimentId != actual.experimentId ||
        expected.configHash != actual.configHash || expected.framePoolId != actual.framePoolId ||
        expected.noisePoolId != actual.noisePoolId || expected.payloadLength != actual.payloadLength ||
        expected.encodedLength != actual.encodedLength || expected.snrIndex != actual.snrIndex ||
        expected.ebN0_dB != actual.ebN0_dB || expected.noisePolicyVersion != actual.noisePolicyVersion ||
        expected.globalSeed != actual.globalSeed || expected.shardIndex != actual.shardIndex ||
        expected.shardCount != actual.shardCount) {
        throw std::invalid_argument("checkpoint resume compatibility mismatch");
    }
}

void validateCheckpointState(const SimulationCheckpointRecord& record, FrameIndex firstFrameIndex,
                             std::uint64_t requestedFrameCount) {
    if (record.nextFrameIndex < firstFrameIndex || record.nextFrameIndex > firstFrameIndex + requestedFrameCount) {
        throw std::invalid_argument("checkpoint nextFrameIndex outside requested range");
    }
    const std::uint64_t completed = record.nextFrameIndex - firstFrameIndex;
    if (record.metrics.processedFrames != completed) {
        throw std::invalid_argument("checkpoint processedFrames contradicts nextFrameIndex");
    }
    if (record.payloadLength == 0U || record.metrics.totalPayloadBits != completed * record.payloadLength) {
        throw std::invalid_argument("checkpoint totalPayloadBits contradicts processedFrames");
    }
    if (record.metrics.successfulFrames + record.metrics.frameErrors != completed) {
        throw std::invalid_argument("checkpoint success and error counters contradict processedFrames");
    }
}

void writeCheckpointFile(const std::string& path, const SimulationCheckpointRecord& record) {
    const std::filesystem::path target(path);
    if (!target.parent_path().empty()) std::filesystem::create_directories(target.parent_path());
    const std::filesystem::path temporary = target.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) throw std::runtime_error("failed to open checkpoint temporary output path");
        output << checkpointToJson(record);
        output.flush();
        if (!output) throw std::runtime_error("failed to flush checkpoint temporary output");
    }
#ifdef _WIN32
    if (!MoveFileExW(temporary.wstring().c_str(), target.wstring().c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        std::filesystem::remove(temporary);
        throw std::runtime_error("failed to atomically replace checkpoint output");
    }
#else
    std::filesystem::rename(temporary, target);
#endif
}

SimulationCheckpointRecord readCheckpointFile(const std::string& path) {
    return checkpointFromJson(readTextFile(path));
}

}  // namespace scl::common
