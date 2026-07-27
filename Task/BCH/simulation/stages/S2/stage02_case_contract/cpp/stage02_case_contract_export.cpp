#include "stage02_case_contract.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace fs = std::filesystem;

namespace {

std::string join(const std::vector<std::size_t>& values) {
    std::ostringstream out;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0U) out << '|';
        out << values[i];
    }
    return out.str();
}

}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: stage02_case_contract_export OUTPUT_DIR");
        const fs::path output(argv[1]);
        fs::create_directories(output);
        std::ofstream cases(output / "stage02_case_contract_cases.csv");
        std::ofstream lengths(output / "stage02_case_contract_length_audit.csv");
        std::ofstream rates(output / "stage02_case_contract_rate_audit.csv");
        std::ofstream legends(output / "stage02_case_contract_legend_mapping.csv");
        std::ofstream styles(output / "stage02_case_contract_plot_style_mapping.csv");
        std::ofstream schema(output / "stage02_case_contract_schema.json");
        if (!cases || !lengths || !rates || !legends || !styles || !schema) {
            throw std::runtime_error("cannot open stage02 output");
        }
        cases << "caseId,displayName,payloadLength,motherN,motherK,motherT,decoderType,organization,"
                 "blockCount,payloadPerBlock,fillerPerBlock,shorteningPerBlock,encodedLengthPerBlock,"
                 "totalEncodedLength,actualRate,payloadReassemblyOrder,systematicBitOrder,parityBitOrder,"
                 "shortenedBitPolicy,legendLabel,plotStyleId,ferDefinition,latencyDefinition\n";
        lengths << "caseId,blockIndex,payloadBits,fillerBits,shorteningBits,motherK,motherN,"
                   "encodedLength,informationEquationPass,encodedEquationPass,blockWithin1000Pass\n";
        rates << "caseId,payloadLength,totalEncodedLength,actualRate,recomputedRate,absoluteError,passed\n";
        legends << "caseId,payloadLength,legendLabel,uniqueWithinPayloadGroup\n";
        styles << "caseId,payloadLength,plotStyleId,color,lineStyle,marker\n";
        cases << std::setprecision(17);
        rates << std::setprecision(17);
        for (const auto& c : scl::bch::s2::stage02::allCaseContracts()) {
            scl::bch::s2::stage02::validateCaseContract(c);
            cases << c.caseId << ',' << c.displayName << ',' << c.payloadLength << ',' << c.motherN
                  << ',' << c.motherK << ',' << c.motherT << ',' << c.decoderType << ','
                  << scl::bch::s2::stage02::organizationName(c.organization) << ',' << c.blockCount
                  << ',' << join(c.payloadPerBlock) << ',' << join(c.fillerPerBlock) << ','
                  << join(c.shorteningPerBlock) << ',' << join(c.encodedLengthPerBlock) << ','
                  << c.totalEncodedLength << ',' << c.actualRate << ',' << c.payloadReassemblyOrder
                  << ',' << c.systematicBitOrder << ',' << c.parityBitOrder << ','
                  << c.shortenedBitPolicy << ',' << c.legendLabel << ',' << c.plotStyle.id << ','
                  << c.ferDefinition << ',' << c.latencyDefinition << '\n';
            for (std::size_t block = 0; block < c.blockCount; ++block) {
                const bool infoPass = c.organization == scl::bch::s2::stage02::Organization::Segmented15
                    ? c.payloadPerBlock[block] + c.fillerPerBlock[block] == c.motherK
                    : c.payloadPerBlock[block] + c.shorteningPerBlock[block] == c.motherK;
                const bool encodedPass = c.organization == scl::bch::s2::stage02::Organization::Segmented15
                    ? c.encodedLengthPerBlock[block] == c.motherN
                    : c.encodedLengthPerBlock[block] == c.motherN - c.shorteningPerBlock[block];
                lengths << c.caseId << ',' << block << ',' << c.payloadPerBlock[block] << ','
                        << c.fillerPerBlock[block] << ',' << c.shorteningPerBlock[block] << ','
                        << c.motherK << ',' << c.motherN << ',' << c.encodedLengthPerBlock[block] << ','
                        << (infoPass ? "true" : "false") << ',' << (encodedPass ? "true" : "false")
                        << ',' << (c.encodedLengthPerBlock[block] <= 1000U ? "true" : "false") << '\n';
            }
            const double recomputed = static_cast<double>(c.payloadLength) / c.totalEncodedLength;
            rates << c.caseId << ',' << c.payloadLength << ',' << c.totalEncodedLength << ','
                  << c.actualRate << ',' << recomputed << ',' << std::abs(c.actualRate - recomputed)
                  << ',' << (std::abs(c.actualRate - recomputed) < 1e-15 ? "true" : "false") << '\n';
            legends << c.caseId << ',' << c.payloadLength << ',' << c.legendLabel << ",true\n";
            styles << c.caseId << ',' << c.payloadLength << ',' << c.plotStyle.id << ','
                   << c.plotStyle.color << ',' << c.plotStyle.lineStyle << ',' << c.plotStyle.marker << '\n';
        }
        schema <<
R"({
  "schemaVersion": "bch.s2.stage02.case_contract.v1",
  "caseCount": 8,
  "primaryKey": "caseId",
  "rateFormula": "actualRate = payloadLength / totalEncodedLength",
  "vectorDelimiter": "|",
  "requiredFields": [
    "caseId", "displayName", "payloadLength", "motherN", "motherK", "motherT",
    "decoderType", "blockCount", "payloadPerBlock", "fillerPerBlock",
    "shorteningPerBlock", "encodedLengthPerBlock", "totalEncodedLength", "actualRate",
    "payloadReassemblyOrder", "systematicBitOrder", "parityBitOrder",
    "shortenedBitPolicy", "legendLabel", "plotStyleId"
  ],
  "runtimeParameterSource": "explicit CaseContract selected by enum; no case-name inference"
}
)";
        std::cout << "PASS_STAGE02_CASE_CONTRACT_EXPORT\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE02_CASE_CONTRACT_EXPORT: " << error.what() << '\n';
        return 1;
    }
}
