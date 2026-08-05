#include "s7/s7.hpp"

#include "common/sha256.hpp"

#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr std::size_t kFramesPerStart = 200;
const std::string kConfigHash = scl::common::sha256Hex(
    "s7-stage12-v1|ratios=0.05,0.10|framesPerStart=200|all-valid-starts|"
    "BCH=NONE,CODEBLOCK19,ROW15,GLOBAL285|CC=NONE,SHORT8,PSEUDO128,SHORT16_CONTROL128");

struct Candidate {
    std::string id;
    std::string method;
    std::size_t parameter;
    std::string comparisonRole;
    std::string engineeringGroup;
    std::string controlledGroup;
    s7::Mapping mapping;
};

struct Aggregate {
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
};

std::vector<Candidate> candidatesFor(const std::string& scheme) {
    if (scheme == "BCH") {
        return {
            {"BCH_NONE", "NONE", 0, "BASELINE", "", "", s7::makeBchMapping(s7::BchInterleaver::None)},
            {"BCH_CODEBLOCK_D19", "BCH_CODEBLOCK", 19, "FORMAL_METHOD", "", "BCH_EQUAL_SPAN_285", s7::makeBchMapping(s7::BchInterleaver::Codeblock, 19)},
            {"BCH_ROW_COLUMN_R15", "ROW_COLUMN", 15, "FORMAL_METHOD", "", "BCH_EQUAL_SPAN_285", s7::makeBchMapping(s7::BchInterleaver::RowColumn, 15)},
            {"BCH_GLOBAL_PSEUDO_285", "GLOBAL_PSEUDORANDOM", 285, "FORMAL_METHOD", "", "BCH_EQUAL_SPAN_285", s7::makeBchMapping(s7::BchInterleaver::GlobalPseudorandom, 285)}};
    }
    return {
        {"CC_NONE", "NONE", 0, "BASELINE", "", "", s7::makeCcMapping(s7::CcInterleaver::None)},
        {"CC_SHORT_D8_RECOMMENDED", "SHORT_DEPTH_BLOCK", 8, "RECOMMENDED_ENGINEERING_CONFIGURATION", "CC_RECOMMENDED_ENGINEERING_CONFIG", "", s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock, 8)},
        {"CC_PSEUDO_128_RECOMMENDED", "PSEUDORANDOM", 128, "RECOMMENDED_ENGINEERING_CONFIGURATION", "CC_RECOMMENDED_ENGINEERING_CONFIG", "CC_EQUAL_SPAN_128", s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, 128)},
        {"CC_SHORT_D16_CONTROL_128", "SHORT_DEPTH_BLOCK", 16, "CONTROLLED_EQUAL_SPAN_128", "", "CC_EQUAL_SPAN_128", s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock, 16)}};
}

std::tuple<std::string, std::string, std::string> sharedHashes(std::size_t payloadLength,
                                                               std::size_t encodedLength) {
    scl::common::Sha256 payloadHash, noiseHash, frameHash;
    for (std::size_t frame = 0; frame < kFramesPerStart; ++frame) {
        const auto payload = s7::deterministicPayload(payloadLength, frame);
        payloadHash.update(payload);
        const auto noise = s7::deterministicStandardNoise(encodedLength, frame);
        noiseHash.update(reinterpret_cast<const std::uint8_t*>(noise.data()), noise.size() * sizeof(double));
        frameHash.update(std::to_string(frame) + ",");
    }
    return {payloadHash.finalHex(), noiseHash.finalHex(), frameHash.finalHex()};
}

void writeCheckpoint(const fs::path& path, const std::string& scheme, std::size_t completed,
                     std::size_t total) {
    const fs::path temporary = path.string() + ".tmp";
    std::ofstream out(temporary, std::ios::trunc);
    if (!out) throw std::runtime_error("cannot write Stage12 checkpoint");
    out << "{\n  \"status\": \"" << (completed == total ? "COMPLETE" : "RUNNING")
        << "\",\n  \"scheme\": \"" << scheme << "\",\n  \"configHash\": \""
        << kConfigHash << "\",\n  \"completedGroups\": " << completed
        << ",\n  \"totalGroups\": " << total << ",\n  \"framesPerStart\": "
        << kFramesPerStart << ",\n  \"resumeSource\": \"validated_csv_row_count\",\n"
        << "  \"mergeStatus\": \"NOT_MERGED\"\n}\n";
    out.close();
    if (!out) throw std::runtime_error("Stage12 checkpoint write failed");
    std::error_code error;
    fs::remove(path, error);
    error.clear();
    fs::rename(temporary, path, error);
    if (error) throw std::runtime_error("cannot activate Stage12 checkpoint");
}

std::size_t completedGroupsFromCsv(const fs::path& path, std::size_t candidateCount) {
    if (!fs::exists(path)) return 0;
    std::ifstream in(path);
    std::string line;
    if (!std::getline(in, line) || line.find("scheme,configurationId") != 0)
        throw std::runtime_error("invalid Stage12 CSV header");
    std::size_t rows = 0;
    while (std::getline(in, line)) if (!line.empty()) ++rows;
    if (rows % candidateCount != 0) throw std::runtime_error("partial Stage12 comparison group in CSV");
    return rows / candidateCount;
}

void writeHeader(std::ofstream& out) {
    out << "scheme,configurationId,method,parameter,comparisonRole,engineeringComparisonGroup,"
           "controlledComparisonGroup,pureMethodDifferenceAllowed,fairnessGroupId,spanBits,"
           "spanTrellisSteps,bufferBits,mappingHash,workpointRole,EsN0Db,sigmaSquared,"
           "burstRatioRequested,burstLengthBits,burstRatioActual,burstStart,burstEnd,framesProcessed,"
           "totalBits,bitErrors,frameErrors,BER,FER,payloadChecksum,noiseChecksum,frameSequenceHash,configHash\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 6)
            throw std::invalid_argument("usage: s7_all_start_runner BCH|CC OUTPUT_DIR LOW MID HIGH [--group-limit N]");
        const std::string scheme = argv[1];
        if (scheme != "BCH" && scheme != "CC") throw std::invalid_argument("scheme must be BCH or CC");
        const fs::path output = fs::absolute(argv[2]);
        const std::vector<double> snrs{std::stod(argv[3]), std::stod(argv[4]), std::stod(argv[5])};
        if (!(snrs[0] < snrs[1] && snrs[1] < snrs[2])) throw std::invalid_argument("workpoints must be strictly increasing");
        std::size_t groupLimit = static_cast<std::size_t>(-1);
        for (int i = 6; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--group-limit" && i + 1 < argc) groupLimit = std::stoull(argv[++i]);
            else throw std::invalid_argument("unknown Stage12 runner option");
        }

        fs::create_directories(output);
        const auto candidates = candidatesFor(scheme);
        const std::size_t payloadLength = scheme == "BCH" ? s7::kBchPayloadBits : s7::kCcPayloadBits;
        const std::size_t encodedLength = scheme == "BCH" ? s7::kBchEncodedBits : s7::kCcEncodedBits;
        const std::vector<double> ratios{0.05, 0.10};
        std::size_t totalGroups = 0;
        for (double ratio : ratios) totalGroups += encodedLength - static_cast<std::size_t>(std::llround(ratio * encodedLength)) + 1;
        totalGroups *= snrs.size();
        groupLimit = std::min(groupLimit, totalGroups);

        const fs::path csvPath = output / "all_start_results.csv";
        std::size_t completed = completedGroupsFromCsv(csvPath, candidates.size());
        if (completed > groupLimit) throw std::runtime_error("existing Stage12 CSV exceeds requested group limit");
        std::ofstream csv(csvPath, completed == 0 ? std::ios::trunc : std::ios::app);
        if (!csv) throw std::runtime_error("cannot open Stage12 CSV");
        if (completed == 0) writeHeader(csv);

        const auto hashes = sharedHashes(payloadLength, encodedLength);
        const std::vector<std::string> workpointRoles{"LOW", "WATERFALL", "HIGH"};
        const s7::BchCodecContext bchContext;
        std::size_t groupIndex = 0;
        for (std::size_t snrIndex = 0; snrIndex < snrs.size() && groupIndex < groupLimit; ++snrIndex) {
            const double variance = s7::sigmaSquaredFromEsN0(snrs[snrIndex]);
            for (double ratio : ratios) {
                const std::size_t length = static_cast<std::size_t>(std::llround(ratio * encodedLength));
                for (std::size_t start = 0; start + length <= encodedLength && groupIndex < groupLimit; ++start, ++groupIndex) {
                    if (groupIndex < completed) continue;
                    std::vector<Aggregate> aggregates(candidates.size());
                    for (std::size_t frame = 0; frame < kFramesPerStart; ++frame) {
                        const auto payload = s7::deterministicPayload(payloadLength, frame);
                        const auto noise = s7::deterministicStandardNoise(encodedLength, frame);
                        const s7::BurstSpec burst{ratio, length, start, start + length, s7::BurstPosition::Head, false};
                        for (std::size_t c = 0; c < candidates.size(); ++c) {
                            std::size_t errors = 0;
                            if (scheme == "BCH") errors = s7::runBchFrame(bchContext, payload, candidates[c].mapping, noise, variance, burst).bitErrors;
                            else errors = s7::runCcFrame(payload, candidates[c].mapping, noise, variance, burst).bitErrors;
                            aggregates[c].bitErrors += errors;
                            aggregates[c].frameErrors += errors != 0;
                        }
                    }
                    csv << std::setprecision(17);
                    for (std::size_t c = 0; c < candidates.size(); ++c) {
                        const auto& candidate = candidates[c];
                        const auto& aggregate = aggregates[c];
                        const std::uint64_t totalBits = kFramesPerStart * payloadLength;
                        csv << scheme << ',' << candidate.id << ',' << candidate.method << ',' << candidate.parameter << ','
                            << candidate.comparisonRole << ',' << candidate.engineeringGroup << ',' << candidate.controlledGroup
                            << ",false," << candidate.mapping.fairnessGroupId << ',' << candidate.mapping.spanBits << ','
                            << candidate.mapping.spanTrellisSteps << ',' << candidate.mapping.bufferBits << ',' << candidate.mapping.sha256 << ','
                            << workpointRoles[snrIndex] << ',' << snrs[snrIndex] << ',' << variance << ',' << ratio << ',' << length << ','
                            << static_cast<double>(length) / encodedLength << ',' << start << ',' << start + length << ','
                            << kFramesPerStart << ',' << totalBits << ',' << aggregate.bitErrors << ',' << aggregate.frameErrors << ','
                            << static_cast<double>(aggregate.bitErrors) / totalBits << ','
                            << static_cast<double>(aggregate.frameErrors) / kFramesPerStart << ','
                            << std::get<0>(hashes) << ',' << std::get<1>(hashes) << ',' << std::get<2>(hashes) << ',' << kConfigHash << '\n';
                    }
                    csv.flush();
                    if (!csv) throw std::runtime_error("Stage12 CSV write failed");
                    writeCheckpoint(output / "checkpoint_manifest.json", scheme, groupIndex + 1, totalGroups);
                    if ((groupIndex + 1) % 25 == 0 || groupIndex + 1 == groupLimit)
                        std::cout << "STAGE12_PROGRESS scheme=" << scheme << " groups=" << groupIndex + 1 << '/' << groupLimit << '\n';
                }
            }
        }
        std::cout << "PASS_S7_STAGE12_RUNNER scheme=" << scheme << " groups=" << groupIndex << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S7_STAGE12_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
