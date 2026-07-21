#ifndef SCL_COMMON_RESULT_SCHEMA_HPP
#define SCL_COMMON_RESULT_SCHEMA_HPP

#include "common/checkpoint.hpp"
#include "common/simulation_metrics.hpp"

#include <string>
#include <vector>

namespace scl::common {

constexpr const char* kResultSchemaVersion = "common04.result_summary.v1";
constexpr const char* kMetadataSchemaVersion = "common04.metadata.v1";

struct SummaryRow {
    std::string schemaVersion = kResultSchemaVersion;
    std::string experimentId;
    std::string stage = "stage04_common_simulation_foundation";
    std::string codeType = "IDENTITY";
    std::string caseName;
    Length payloadLength = 0;
    Length encodedLength = 0;
    double codeRate = 0.0;
    double ebN0_dB = 0.0;
    SnrIndex snrIndex = 0;
    ErrorMetrics metrics;
    std::string stopReason;
    std::string framePoolId;
    std::string noisePoolId;
    std::string configHash;
};

std::string summaryCsvHeader();
std::string summaryRowToCsv(const SummaryRow& row);
void validateSummaryRow(const SummaryRow& row);
std::string metadataJson(const SummaryRow& row, const std::string& createdTime);

}  // namespace scl::common

#endif  // SCL_COMMON_RESULT_SCHEMA_HPP
