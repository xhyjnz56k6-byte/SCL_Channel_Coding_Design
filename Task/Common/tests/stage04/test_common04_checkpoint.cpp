#include "common/checkpoint.hpp"
#include "common/result_schema.hpp"

#include <functional>
#include <stdexcept>
#include <string>

namespace {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void requireThrows(const std::string& name, const std::function<void()>& fn) {
    try {
        fn();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(name + " did not fail");
}
}

int main() {
    const std::string a = scl::common::canonicalConfigText("case", 200, 248, "0;2;4", "frame", "noise", "stop", "HARD");
    const std::string b = scl::common::canonicalConfigText("case", 200, 248, "0;2;4", "frame", "noise", "stop", "HARD");
    require(scl::common::computeConfigHash(a) == scl::common::computeConfigHash(b), "config hash determinism mismatch");
    require(a.find("createdTime") == std::string::npos, "createdTime leaked into configHash canonical text");

    scl::common::SimulationCheckpointRecord record;
    record.experimentId = "exp";
    record.configHash = scl::common::computeConfigHash(a);
    record.framePoolId = "frame";
    record.noisePoolId = "noise";
    record.payloadLength = 200;
    record.encodedLength = 248;
    record.ebN0_dB = 2.0;
    record.nextFrameIndex = 10;
    record.metrics.processedFrames = 10;
    record.metrics.totalPayloadBits = 2000;
    record.metrics.successfulFrames = 10;
    const auto parsed = scl::common::checkpointFromJson(scl::common::checkpointToJson(record));
    require(parsed.configHash == record.configHash && parsed.nextFrameIndex == 10U, "checkpoint round trip mismatch");
    scl::common::validateResumeCompatibility(record, parsed);
    auto bad = parsed;
    bad.noisePoolId = "other";
    requireThrows("bad resume", [&] { scl::common::validateResumeCompatibility(record, bad); });
    requireThrows("bad schema", [] { (void)scl::common::checkpointFromJson("{\"schemaVersion\":\"bad\"}"); });

    scl::common::SummaryRow row;
    row.experimentId = "exp";
    row.caseName = "case";
    row.payloadLength = 200;
    row.encodedLength = 248;
    row.codeRate = 200.0 / 248.0;
    row.metrics = record.metrics;
    row.stopReason = "MAX_FRAMES";
    row.framePoolId = "frame";
    row.noisePoolId = "noise";
    row.configHash = record.configHash;
    const std::string csv = scl::common::summaryCsvHeader() + "\n" + scl::common::summaryRowToCsv(row);
    require(csv.find("schemaVersion") != std::string::npos && csv.find("common04.result_summary.v1") != std::string::npos, "summary CSV mismatch");
    const std::string metadata = scl::common::metadataJson(row, "2026-07-21T00:00:00Z");
    require(metadata.find("createdTime") != std::string::npos, "metadata createdTime missing");
    require(row.configHash.find("2026") == std::string::npos, "createdTime leaked into configHash");
    return 0;
}
