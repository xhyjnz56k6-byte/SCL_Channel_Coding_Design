#include "bch_simulation/bch_awgn_simulation.hpp"
#include "bch_simulation/bch_case_adapter.hpp"

#include "common/awgn_channel.hpp"
#include "common/demodulation.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"
#include "common/modulation.hpp"
#include "common/sha256.hpp"
#include "common/simulation_metrics.hpp"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using scl::bch::simulation::BchCaseId;
using scl::bch::simulation::BchSimulationCase;

namespace {

struct FormalPoint {
    std::string caseName;
    double ebn0Db = 0.0;
    std::uint64_t snrIndex = 0;
    std::uint64_t processedFrames = 0;
    std::uint64_t decodedBitErrors = 0;
    std::uint64_t decodedFrameErrors = 0;
    std::uint64_t trueSuccessFrames = 0;
    double noiseSigma = 0.0;
    std::string configHash;
};

struct Args {
    std::string formalSummary;
    std::string framePoolManifest;
    std::string outputDirectory;
    bool progress = true;
    bool encodingOnly = false;
    std::uint64_t smokeFrames = 0;
};

std::vector<std::string> splitCsv(const std::string& line) {
    std::vector<std::string> values;
    std::string value;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (c == '"') {
            if (quoted && i + 1U < line.size() && line[i + 1U] == '"') {
                value.push_back('"');
                ++i;
            } else {
                quoted = !quoted;
            }
        } else if (c == ',' && !quoted) {
            values.push_back(value);
            value.clear();
        } else {
            value.push_back(c);
        }
    }
    values.push_back(value);
    return values;
}

std::vector<FormalPoint> readFormalPoints(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open formal summary: " + path);
    std::string line;
    if (!std::getline(input, line)) throw std::runtime_error("formal summary is empty");
    const auto header = splitCsv(line);
    std::map<std::string, std::size_t> column;
    for (std::size_t i = 0; i < header.size(); ++i) column[header[i]] = i;
    for (const char* required : {"caseName", "ebn0Db", "snrIndex", "processedFrames",
                                 "decodedBitErrors", "decodedFrameErrors", "trueSuccessFrames",
                                 "noiseSigma", "configHash"}) {
        if (column.count(required) == 0U) throw std::runtime_error("formal summary missing column: " + std::string(required));
    }
    std::vector<FormalPoint> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        const auto row = splitCsv(line);
        const std::string name = row.at(column.at("caseName"));
        if (name != "BCH-S200" && name != "BCH-B200") continue;
        FormalPoint point;
        point.caseName = name;
        point.ebn0Db = std::stod(row.at(column.at("ebn0Db")));
        point.snrIndex = std::stoull(row.at(column.at("snrIndex")));
        point.processedFrames = std::stoull(row.at(column.at("processedFrames")));
        point.decodedBitErrors = std::stoull(row.at(column.at("decodedBitErrors")));
        point.decodedFrameErrors = std::stoull(row.at(column.at("decodedFrameErrors")));
        point.trueSuccessFrames = std::stoull(row.at(column.at("trueSuccessFrames")));
        point.noiseSigma = std::stod(row.at(column.at("noiseSigma")));
        point.configHash = row.at(column.at("configHash"));
        points.push_back(point);
    }
    if (points.size() != 35U) throw std::runtime_error("expected 35 S200/B200 formal points");
    return points;
}

Args parseArgs(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        auto take = [&]() -> std::string {
            if (i + 1 >= argc) throw std::invalid_argument("missing value for " + arg);
            return argv[++i];
        };
        if (arg == "--formal-summary") args.formalSummary = take();
        else if (arg == "--frame-pool-manifest") args.framePoolManifest = take();
        else if (arg == "--output-dir") args.outputDirectory = take();
        else if (arg == "--progress") args.progress = true;
        else if (arg == "--no-progress") args.progress = false;
        else if (arg == "--encoding-only") args.encodingOnly = true;
        else if (arg == "--smoke-frames") args.smokeFrames = std::stoull(take());
        else throw std::invalid_argument("unknown argument: " + arg);
    }
    if (args.formalSummary.empty() || args.framePoolManifest.empty() || args.outputDirectory.empty()) {
        throw std::invalid_argument("--formal-summary, --frame-pool-manifest and --output-dir are required");
    }
    return args;
}

std::string slug(const std::string& caseName, std::uint64_t snrIndex) {
    return (caseName == "BCH-S200" ? "bch_s200_" : "bch_b200_") + std::to_string(snrIndex);
}

void writeLe16(std::ostream& out, std::uint16_t value) {
    const char bytes[2] = {static_cast<char>(value & 0xffU), static_cast<char>((value >> 8U) & 0xffU)};
    out.write(bytes, 2);
}

void writeLe32(std::ostream& out, std::uint32_t value) {
    const char bytes[4] = {
        static_cast<char>(value & 0xffU),
        static_cast<char>((value >> 8U) & 0xffU),
        static_cast<char>((value >> 16U) & 0xffU),
        static_cast<char>((value >> 24U) & 0xffU)};
    out.write(bytes, 4);
}

std::string bitString(const scl::common::BitVector& bits) {
    std::string text;
    text.reserve(bits.size());
    for (auto bit : bits) text.push_back(bit == 0U ? '0' : '1');
    return text;
}

scl::common::BitVector namedPayload(const std::string& name, std::size_t length) {
    scl::common::BitVector bits(length, 0U);
    if (name == "all_one") {
        std::fill(bits.begin(), bits.end(), 1U);
    } else if (name == "first_one") {
        bits.front() = 1U;
    } else if (name == "last_one") {
        bits.back() = 1U;
    } else if (name == "alternating_01") {
        for (std::size_t i = 0; i < length; ++i) bits[i] = static_cast<scl::common::Bit>(i & 1U);
    } else if (name == "alternating_10") {
        for (std::size_t i = 0; i < length; ++i) bits[i] = static_cast<scl::common::Bit>((i + 1U) & 1U);
    }
    return bits;
}

void writeEncodingVectors(const fs::path& output,
                          const scl::common::PackedFramePoolReader& pool) {
    std::ofstream csv(output / "cpp_official_encoding_vectors.csv");
    if (!csv) throw std::runtime_error("cannot write encoding vectors");
    csv << "caseName,vectorName,payloadBits,cppEncodedBits\n";
    const std::vector<std::string> names = {
        "all_zero", "all_one", "first_one", "last_one", "alternating_01", "alternating_10"};
    for (const std::string& caseName : {"BCH-S200", "BCH-B200"}) {
        const auto& simulationCase = scl::bch::simulation::bchSimulationCase(caseName);
        for (const auto& name : names) {
            const auto payload = namedPayload(name, simulationCase.payloadLength);
            csv << caseName << ',' << name << ',' << bitString(payload) << ','
                << bitString(scl::bch::simulation::encodeBchFrame(simulationCase, payload).codeword) << '\n';
        }
        for (std::uint64_t frame = 0; frame < 100U; ++frame) {
            const auto payload = pool.readFrame(frame).payloadBits;
            csv << caseName << ",common_" << frame << ',' << bitString(payload) << ','
                << bitString(scl::bch::simulation::encodeBchFrame(simulationCase, payload).codeword) << '\n';
        }
    }
}

struct PointAudit {
    std::uint64_t decodedBitErrors = 0;
    std::uint64_t decodedFrameErrors = 0;
    std::uint64_t trueSuccessFrames = 0;
    std::uint64_t withinCapabilityFrames = 0;
    std::uint64_t beyondCapabilityFrames = 0;
    std::string noiseFile;
    std::string noiseHash;
    std::string referenceFile;
    std::string referenceHash;
};

PointAudit exportPoint(const FormalPoint& point,
                       const BchSimulationCase& simulationCase,
                       const scl::common::PackedFramePoolReader& pool,
                       const fs::path& output,
                       bool progress,
                       bool validateFormalReplay) {
    const std::string base = slug(point.caseName, point.snrIndex);
    const fs::path noisePath = output / (base + "_standard_gaussian_f64le.bin");
    const fs::path referencePath = output / (base + "_cpp_reference.bin");
    std::ofstream noise(noisePath, std::ios::binary);
    std::ofstream reference(referencePath, std::ios::binary);
    if (!noise || !reference) throw std::runtime_error("cannot create point binary output");

    PointAudit audit;
    audit.noiseFile = noisePath.filename().generic_string();
    audit.referenceFile = referencePath.filename().generic_string();
    const double sigma = scl::bch::simulation::independentSigmaReference(simulationCase, point.ebn0Db);
    if (std::abs(sigma - point.noiseSigma) > 1e-15) {
        throw std::runtime_error("BLOCKED_BCH16V_SIGMA_MISMATCH");
    }
    const std::uint64_t noiseGroup =
        scl::bch::simulation::pairedNoiseGroupId(simulationCase.payloadLength, point.snrIndex);
    const auto started = std::chrono::steady_clock::now();
    for (std::uint64_t frame = 0; frame < point.processedFrames; ++frame) {
        const auto payload = pool.readFrame(frame).payloadBits;
        const auto encoded = scl::bch::simulation::encodeBchFrame(simulationCase, payload).codeword;
        const auto z = scl::common::generateStandardGaussianFrame(
            2026072201ULL, noiseGroup, frame, simulationCase.encodedLength, 1U);
        noise.write(reinterpret_cast<const char*>(z.data()),
                    static_cast<std::streamsize>(z.size() * sizeof(double)));
        const auto hard = scl::common::hardDecision(
            scl::common::applyAwgn(scl::common::bpskModulate(encoded), z, sigma));
        auto decoded = scl::bch::simulation::decodeBchFrame(simulationCase, hard);
        scl::bch::simulation::auditDecodedBchFrame(payload, decoded);
        const std::uint64_t channelWeight = scl::common::countBitErrors(encoded, hard);
        const std::uint64_t decodedErrors = scl::common::countBitErrors(payload, decoded.payload);
        std::uint8_t maxSegmentWeight = 0U;
        if (point.caseName == "BCH-S200") {
            for (std::size_t segment = 0; segment < 19U; ++segment) {
                std::uint8_t weight = 0U;
                for (std::size_t bit = 0; bit < 15U; ++bit) {
                    weight += encoded[segment * 15U + bit] != hard[segment * 15U + bit];
                }
                maxSegmentWeight = std::max(maxSegmentWeight, weight);
            }
        }
        const bool within = point.caseName == "BCH-S200" ? maxSegmentWeight <= 1U : channelWeight <= 6U;
        audit.decodedBitErrors += decodedErrors;
        audit.decodedFrameErrors += decodedErrors != 0U;
        audit.trueSuccessFrames += decoded.trueSuccess;
        audit.withinCapabilityFrames += within;
        audit.beyondCapabilityFrames += !within;

        writeLe32(reference, static_cast<std::uint32_t>(frame));
        writeLe16(reference, static_cast<std::uint16_t>(channelWeight));
        writeLe16(reference, static_cast<std::uint16_t>(decodedErrors));
        reference.put(static_cast<char>(decoded.trueSuccess));
        reference.put(static_cast<char>(decoded.reportedSuccess));
        reference.put(static_cast<char>(decoded.miscorrected));
        reference.put(static_cast<char>(decoded.decoderFailure));
        reference.put(static_cast<char>(maxSegmentWeight));
        const auto packedDecoded = scl::common::packPayloadBits(decoded.payload);
        reference.write(reinterpret_cast<const char*>(packedDecoded.data()),
                        static_cast<std::streamsize>(packedDecoded.size()));
        if (progress && ((frame + 1U) % 1000U == 0U || frame + 1U == point.processedFrames)) {
            const double elapsed = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - started).count();
            const double rate = elapsed > 0.0 ? (frame + 1U) / elapsed : 0.0;
            const double eta = rate > 0.0 ? (point.processedFrames - frame - 1U) / rate : 0.0;
            std::cout << "\r[BCH-16V][EXPORT][" << point.caseName << "][" << point.ebn0Db
                      << " dB] frames " << (frame + 1U) << '/' << point.processedFrames
                      << " speed " << std::fixed << std::setprecision(1) << rate
                      << " frame/s ETA " << eta << "s" << std::flush;
        }
    }
    if (progress) std::cout << '\n';
    noise.close();
    reference.close();
    if (validateFormalReplay && (audit.decodedBitErrors != point.decodedBitErrors ||
        audit.decodedFrameErrors != point.decodedFrameErrors ||
        audit.trueSuccessFrames != point.trueSuccessFrames)) {
        throw std::runtime_error("BLOCKED_BCH16V_CPP_FORMAL_REPLAY_MISMATCH");
    }
    audit.noiseHash = scl::common::sha256FileHex(noisePath.string());
    audit.referenceHash = scl::common::sha256FileHex(referencePath.string());
    return audit;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parseArgs(argc, argv);
        const auto points = readFormalPoints(args.formalSummary);
        const auto poolManifest = scl::common::loadFramePoolManifest(args.framePoolManifest);
        if (poolManifest.payloadLength != 200U || poolManifest.totalFrames != 50000U) {
            throw std::runtime_error("BCH-16V requires the frozen 200-bit/50000-frame pool");
        }
        scl::common::PackedFramePoolReader pool(args.framePoolManifest);
        const fs::path output = fs::absolute(args.outputDirectory);
        fs::create_directories(output);
        writeEncodingVectors(output, pool);
        if (args.encodingOnly) {
            std::cout << "PASS_BCH16V_CPP_ENCODING_VECTORS vectors=212\n";
            return 0;
        }

        std::ofstream summary(output / "cpp_reference_summary.csv");
        if (!summary) throw std::runtime_error("cannot create C++ reference summary");
        summary << "caseName,ebn0Db,snrIndex,processedFrames,decodedBitErrors,decodedFrameErrors,"
                   "trueSuccessFrames,withinCapabilityFrames,beyondCapabilityFrames,noiseSigma,"
                   "noiseFile,noiseSha256,cppReferenceFile,cppReferenceSha256,cppReferenceRecordBytes\n";
        std::vector<std::pair<FormalPoint, PointAudit>> exported;
        for (auto point : points) {
            if (args.smokeFrames > 0U) point.processedFrames = std::min(point.processedFrames, args.smokeFrames);
            const auto& simulationCase = scl::bch::simulation::bchSimulationCase(point.caseName);
            auto audit = exportPoint(point, simulationCase, pool, output, args.progress, args.smokeFrames == 0U);
            summary << point.caseName << ',' << std::setprecision(17) << point.ebn0Db << ','
                    << point.snrIndex << ',' << point.processedFrames << ',' << audit.decodedBitErrors
                    << ',' << audit.decodedFrameErrors << ',' << audit.trueSuccessFrames << ','
                    << audit.withinCapabilityFrames << ',' << audit.beyondCapabilityFrames << ','
                    << point.noiseSigma << ',' << audit.noiseFile << ',' << audit.noiseHash << ','
                    << audit.referenceFile << ',' << audit.referenceHash << ",38\n";
            exported.push_back({point, audit});
        }
        summary.close();

        std::ofstream manifest(output / "shared_input_manifest.json");
        if (!manifest) throw std::runtime_error("cannot create shared input manifest");
        manifest << "{\n"
                 << "  \"schemaVersion\": \"bch16v.shared_input.v1\",\n"
                 << "  \"byteOrder\": \"little_endian\",\n"
                 << "  \"noiseType\": \"float64_standard_gaussian_frame_major\",\n"
                 << "  \"payloadStorage\": \"common03.packed_bits.lsb_first\",\n"
                 << "  \"payloadManifest\": \"" << fs::absolute(args.framePoolManifest).generic_string() << "\",\n"
                 << "  \"payloadManifestSha256\": \"" << scl::common::sha256FileHex(args.framePoolManifest) << "\",\n"
                 << "  \"payloadOverallHash\": \"" << poolManifest.overallHash << "\",\n"
                 << "  \"formalSummary\": \"" << fs::absolute(args.formalSummary).generic_string() << "\",\n"
                 << "  \"formalSummarySha256\": \"" << scl::common::sha256FileHex(args.formalSummary) << "\",\n"
                 << "  \"globalSeed\": 2026072201,\n"
                 << "  \"noisePolicyVersion\": 1,\n"
                 << "  \"points\": [\n";
        for (std::size_t i = 0; i < exported.size(); ++i) {
            const auto& point = exported[i].first;
            const auto& audit = exported[i].second;
            const auto& simulationCase = scl::bch::simulation::bchSimulationCase(point.caseName);
            manifest << "    {\"caseName\":\"" << point.caseName << "\",\"ebn0Db\":"
                     << std::setprecision(17) << point.ebn0Db << ",\"snrIndex\":" << point.snrIndex
                     << ",\"processedFrames\":" << point.processedFrames
                     << ",\"payloadLength\":200,\"encodedLength\":" << simulationCase.encodedLength
                     << ",\"frameRate\":" << simulationCase.frameRate
                     << ",\"noiseSigma\":" << point.noiseSigma
                     << ",\"noisePairGroup\":" << scl::bch::simulation::pairedNoiseGroupId(200U, point.snrIndex)
                     << ",\"sourceFormalConfigHash\":\"" << point.configHash
                     << "\",\"noiseFile\":\"" << audit.noiseFile
                     << "\",\"noiseSha256\":\"" << audit.noiseHash
                     << "\",\"cppReferenceFile\":\"" << audit.referenceFile
                     << "\",\"cppReferenceSha256\":\"" << audit.referenceHash
                     << "\",\"cppReferenceRecordBytes\":38}";
            manifest << (i + 1U == exported.size() ? "\n" : ",\n");
        }
        manifest << "  ]\n}\n";
        std::cout << "PASS_BCH16V_SHARED_INPUT_EXPORT points=35 mode="
                  << (args.smokeFrames == 0U ? "formal" : "smoke") << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
