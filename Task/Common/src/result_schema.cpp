#include "common/result_schema.hpp"

#include <sstream>
#include <stdexcept>

namespace scl::common {

std::string summaryCsvHeader() {
    return "schemaVersion,experimentId,stage,codeType,caseName,payloadLength,encodedLength,codeRate,ebN0_dB,snrIndex,"
           "processedFrames,totalPayloadBits,bitErrors,frameErrors,successfulFrames,ber,fer,successRate,"
           "avgEncodeTimeUs,avgChannelTimeUs,avgDecodeTimeUs,maxDecodeTimeUs,avgRecoveryTimeUs,avgTotalTimeUs,"
           "maxTotalTimeUs,stopReason,framePoolId,noisePoolId,configHash";
}

void validateSummaryRow(const SummaryRow& row) {
    if (row.schemaVersion != kResultSchemaVersion || row.codeType.empty() || row.payloadLength == 0U || row.encodedLength == 0U) {
        throw std::invalid_argument("invalid summary row identity fields");
    }
    const MetricsSummary summary = summarizeMetrics(row.metrics);
    if (summary.ber < 0.0 || summary.fer < 0.0 || summary.successRate < 0.0) {
        throw std::invalid_argument("invalid summary ratios");
    }
}

std::string summaryRowToCsv(const SummaryRow& row) {
    validateSummaryRow(row);
    const MetricsSummary summary = summarizeMetrics(row.metrics);
    std::ostringstream out;
    out << row.schemaVersion << ',' << row.experimentId << ',' << row.stage << ',' << row.codeType << ','
        << row.caseName << ',' << row.payloadLength << ',' << row.encodedLength << ',' << row.codeRate << ','
        << row.ebN0_dB << ',' << row.snrIndex << ',' << row.metrics.processedFrames << ','
        << row.metrics.totalPayloadBits << ',' << row.metrics.bitErrors << ',' << row.metrics.frameErrors << ','
        << row.metrics.successfulFrames << ',' << summary.ber << ',' << summary.fer << ',' << summary.successRate << ','
        << summary.avgEncodeTimeUs << ',' << summary.avgChannelTimeUs << ',' << summary.avgDecodeTimeUs << ','
        << summary.maxDecodeTimeUs << ',' << summary.avgRecoveryTimeUs << ',' << summary.avgTotalTimeUs << ','
        << summary.maxTotalTimeUs << ',' << row.stopReason << ',' << row.framePoolId << ',' << row.noisePoolId << ','
        << row.configHash;
    return out.str();
}

std::string metadataJson(const SummaryRow& row, const std::string& createdTime) {
    std::ostringstream out;
    out << "{\n";
    out << "\"schemaVersion\":\"" << kMetadataSchemaVersion << "\",\n";
    out << "\"experimentId\":\"" << row.experimentId << "\",\n";
    out << "\"stage\":\"" << row.stage << "\",\n";
    out << "\"codeType\":\"" << row.codeType << "\",\n";
    out << "\"configHash\":\"" << row.configHash << "\",\n";
    out << "\"framePoolId\":\"" << row.framePoolId << "\",\n";
    out << "\"noisePoolId\":\"" << row.noisePoolId << "\",\n";
    out << "\"createdTime\":\"" << createdTime << "\"\n";
    out << "}\n";
    return out.str();
}

}  // namespace scl::common
