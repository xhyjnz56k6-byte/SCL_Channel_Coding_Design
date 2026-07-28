#include "stage02_case_contract.hpp"

#include "bch_block/bch_block.hpp"
#include "bch_segmented/bch15_lookup_table.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

using scl::bch::s2::stage02::CaseContract;
using scl::bch::s2::stage02::CaseId;
using scl::bch::s2::stage02::Organization;

enum class TruthStatus {
    TrueSuccess,
    DetectedFailure,
    Miscorrection,
    UndetectedError,
    InvalidConfiguration
};

struct TruthDecode {
    scl::common::BitVector payload;
    TruthStatus status = TruthStatus::InvalidConfiguration;
    std::size_t failedBlocks = 0U;
    std::size_t correctedBlocks = 0U;
    std::size_t noErrorBlocks = 0U;
};

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

const char* statusName(TruthStatus status) {
    switch (status) {
        case TruthStatus::TrueSuccess: return "TRUE_SUCCESS";
        case TruthStatus::DetectedFailure: return "DETECTED_FAILURE";
        case TruthStatus::Miscorrection: return "MISCORRECTION";
        case TruthStatus::UndetectedError: return "UNDETECTED_ERROR";
        case TruthStatus::InvalidConfiguration: return "INVALID_CONFIGURATION";
    }
    return "INVALID_CONFIGURATION";
}

std::string bitsText(const scl::common::BitVector& bits) {
    std::string text;
    text.reserve(bits.size());
    for (auto bit : bits) text.push_back(bit == 0U ? '0' : '1');
    return text;
}

scl::common::BitVector payloadFor(const CaseContract& contract, std::uint64_t seed) {
    scl::common::BitVector bits(contract.payloadLength, 0U);
    for (std::size_t i = 0; i < bits.size(); ++i) {
        bits[i] = static_cast<scl::common::Bit>(((i * 37U + seed * 19U + 11U) % 101U) < 50U);
    }
    return bits;
}

scl::bch::block::BlockBchProfile profile(const CaseContract& contract, std::size_t blockIndex) {
    scl::bch::block::BlockBchProfile result;
    if (contract.motherN == 255U) result = scl::bch::block::makeB200Profile();
    else if (contract.motherK == 421U) result = scl::bch::block::makeB300Profile();
    else if (contract.motherK == 385U) result = scl::bch::block::makeB300426Profile();
    else throw std::invalid_argument("unsupported block profile");
    result.caseName = contract.caseId + "_STAGE04_BLOCK_" + std::to_string(blockIndex);
    result.payloadLength = contract.payloadPerBlock.at(blockIndex);
    result.shorteningLength = contract.shorteningPerBlock.at(blockIndex);
    scl::bch::block::validateProfile(result);
    return result;
}

const scl::bch::segmented::SyndromeTable& syndromeTable() {
    static const auto table = scl::bch::segmented::buildBch15SyndromeTable();
    return table;
}

TruthDecode decodeTruth(const CaseContract& contract,
                        const scl::common::BitVector& original,
                        const scl::common::BitVector& received) {
    TruthDecode truth;
    if (contract.organization == Organization::Segmented15) {
        const auto id = contract.payloadLength == 200U
            ? scl::bch::segmented::Bch15SegmentedCase::S200
            : scl::bch::segmented::Bch15SegmentedCase::S300;
        const auto decoded = scl::bch::segmented::decodeBch15Segmented(id, received, syndromeTable());
        truth.payload = decoded.recoveredPayload;
        for (const auto& block : decoded.blockDetails) {
            using Status = scl::bch::segmented::Bch15DecodeStatus;
            if (block.decoder.status == Status::NO_ERROR) ++truth.noErrorBlocks;
            else if (block.decoder.status == Status::CORRECTED_SINGLE_ERROR) ++truth.correctedBlocks;
            else ++truth.failedBlocks;
        }
    } else {
        std::size_t encodedOffset = 0U;
        for (std::size_t blockIndex = 0; blockIndex < contract.blockCount; ++blockIndex) {
            const std::size_t count = contract.encodedLengthPerBlock[blockIndex];
            const scl::common::BitVector blockReceived(
                received.begin() + static_cast<std::ptrdiff_t>(encodedOffset),
                received.begin() + static_cast<std::ptrdiff_t>(encodedOffset + count));
            const auto decoded = scl::bch::block::decodeShortenedNoThrow(
                profile(contract, blockIndex), blockReceived);
            using Status = scl::bch::block::DecodeStatus;
            if (decoded.status == Status::NoError) ++truth.noErrorBlocks;
            else if (decoded.status == Status::Corrected) ++truth.correctedBlocks;
            else ++truth.failedBlocks;
            truth.payload.insert(truth.payload.end(), decoded.payload.begin(), decoded.payload.end());
            encodedOffset += count;
        }
    }
    if (truth.payload == original) truth.status = TruthStatus::TrueSuccess;
    else if (truth.failedBlocks > 0U) truth.status = TruthStatus::DetectedFailure;
    else if (truth.correctedBlocks > 0U) truth.status = TruthStatus::Miscorrection;
    else if (truth.noErrorBlocks == contract.blockCount) truth.status = TruthStatus::UndetectedError;
    else truth.status = TruthStatus::InvalidConfiguration;
    return truth;
}

std::vector<std::size_t> localPositions(
    std::size_t length, std::size_t systematicLength, unsigned weight,
    unsigned mode, std::uint64_t seed) {
    if (weight == 0U) return {};
    require(weight <= length, "error weight exceeds block length");
    std::vector<std::size_t> positions;
    positions.reserve(weight);
    std::set<std::size_t> used;
    auto add = [&](std::size_t value) {
        value %= length;
        for (std::size_t attempts = 0; used.count(value) != 0U && attempts < length; ++attempts) {
            value = (value + 1U) % length;
        }
        require(used.insert(value).second, "cannot generate unique error position");
        positions.push_back(value);
    };
    for (unsigned i = 0; i < weight; ++i) {
        if (mode == 0U) add(i);
        else if (mode == 1U) add(length - 1U - i);
        else if (mode == 2U) add((i & 1U) == 0U ? i / 2U : length - 1U - i / 2U);
        else if (mode == 3U) add(seed % length + i);
        else if (mode == 4U) add(systematicLength - 1U + i);
        else add(seed * 17U + i * 37U + 7U);
    }
    return positions;
}

std::string positionsText(const std::vector<std::size_t>& positions) {
    std::ostringstream out;
    for (std::size_t i = 0; i < positions.size(); ++i) {
        if (i) out << '|';
        out << positions[i];
    }
    return out.str();
}

void executePattern(const CaseContract& contract,
                    const scl::common::BitVector& payload,
                    const scl::common::BitVector& encoded,
                    std::size_t blockIndex,
                    unsigned weight,
                    unsigned mode,
                    const std::string& patternName,
                    std::uint64_t patternId,
                    std::map<std::string,std::uint64_t>& statusCounts,
                    std::ofstream& cases,
                    std::ofstream& results,
                    std::ofstream& samples) {
    std::size_t blockOffset = 0U;
    for (std::size_t i = 0; i < blockIndex; ++i) blockOffset += contract.encodedLengthPerBlock[i];
    const auto local = localPositions(contract.encodedLengthPerBlock[blockIndex],
        contract.organization == Organization::Segmented15 ? 11U : contract.payloadPerBlock[blockIndex],
        weight, mode, patternId);
    scl::common::BitVector received = encoded;
    std::vector<std::size_t> global;
    for (std::size_t position : local) {
        received[blockOffset + position] ^= 1U;
        global.push_back(blockOffset + position);
    }
    const auto decoded = decodeTruth(contract, payload, received);
    const bool withinCapability = weight <= contract.motherT;
    const bool guaranteePass = !withinCapability || decoded.status == TruthStatus::TrueSuccess;
    ++statusCounts[statusName(decoded.status)];
    cases << contract.caseId << ',' << patternId << ',' << blockIndex << ',' << weight << ','
          << patternName << ',' << positionsText(global) << ',' << withinCapability << '\n';
    results << contract.caseId << ',' << patternId << ',' << blockIndex << ',' << weight << ','
            << patternName << ',' << statusName(decoded.status) << ',' << decoded.failedBlocks << ','
            << decoded.correctedBlocks << ',' << decoded.noErrorBlocks << ',' << withinCapability << ','
            << guaranteePass << '\n';
    if ((weight == 0U || weight == contract.motherT) && mode == 5U && blockIndex == 0U) {
        samples << contract.caseId << ',' << patternId << ',' << weight << ',' << bitsText(payload) << ','
                << bitsText(encoded) << ',' << bitsText(received) << ',' << bitsText(decoded.payload) << ','
                << statusName(decoded.status) << '\n';
    }
    require(guaranteePass, contract.caseId + " failed within guaranteed correction capability");
}

void executeCustom(const CaseContract& contract,
                   const scl::common::BitVector& payload,
                   const scl::common::BitVector& encoded,
                   const std::vector<std::size_t>& globalPositions,
                   const std::string& patternName,
                   std::uint64_t patternId,
                   bool requireSuccess,
                   std::map<std::string,std::uint64_t>& statusCounts,
                   std::ofstream& cases,
                   std::ofstream& results) {
    auto received = encoded;
    for (auto position : globalPositions) received.at(position) ^= 1U;
    const auto decoded = decodeTruth(contract, payload, received);
    ++statusCounts[statusName(decoded.status)];
    cases << contract.caseId << ',' << patternId << ",-1," << globalPositions.size() << ','
          << patternName << ',' << positionsText(globalPositions) << ',' << requireSuccess << '\n';
    results << contract.caseId << ',' << patternId << ",-1," << globalPositions.size() << ','
            << patternName << ',' << statusName(decoded.status) << ',' << decoded.failedBlocks << ','
            << decoded.correctedBlocks << ',' << decoded.noErrorBlocks << ',' << requireSuccess << ','
            << (!requireSuccess || decoded.status == TruthStatus::TrueSuccess) << '\n';
    if (requireSuccess) require(decoded.status == TruthStatus::TrueSuccess,
                                contract.caseId + " cross-block guaranteed pattern failed");
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: stage04_error_capability_runner OUTPUT_DIR");
        const fs::path output(argv[1]);
        fs::create_directories(output);
        std::ofstream cases(output / "stage04_error_capability_cases.csv");
        std::ofstream results(output / "stage04_error_capability_results.csv");
        std::ofstream summary(output / "stage04_error_capability_status_summary.csv");
        std::ofstream samples(output / "stage04_error_capability_cpp_matlab_samples.csv");
        if (!cases || !results || !summary || !samples) throw std::runtime_error("cannot open stage04 output");
        cases << "caseId,patternId,blockIndex,errorWeight,patternName,errorPositions,withinCapability\n";
        results << "caseId,patternId,blockIndex,errorWeight,patternName,status,failedBlocks,"
                   "correctedBlocks,noErrorBlocks,withinCapability,guaranteePass\n";
        summary << "caseId,totalPatterns,TRUE_SUCCESS,DETECTED_FAILURE,MISCORRECTION,"
                   "UNDETECTED_ERROR,INVALID_CONFIGURATION,withinCapabilityFailures,stopReason\n";
        samples << "caseId,patternId,errorWeight,payloadBits,encodedBits,receivedBits,"
                   "cppRecoveredBits,cppStatus\n";

        for (const auto& contract : scl::bch::s2::stage02::allCaseContracts()) {
            const auto payload = payloadFor(contract, static_cast<std::uint64_t>(contract.payloadLength + contract.motherK));
            const auto encoded = scl::bch::s2::stage02::encodeFrame(contract.id, payload).encodedBits;
            std::map<std::string,std::uint64_t> counts;
            std::uint64_t patternId = 0U;
            for (std::size_t block = 0; block < contract.blockCount; ++block) {
                for (unsigned weight = 0U; weight <= contract.motherT + 2U; ++weight) {
                    const unsigned firstMode = weight == 0U ? 5U : 0U;
                    for (unsigned mode = firstMode; mode < 6U; ++mode) {
                        static const char* names[] = {
                            "SYSTEMATIC","PARITY","HEAD_TAIL","CONTIGUOUS","SYSTEMATIC_PARITY_BOUNDARY","RANDOM"
                        };
                        executePattern(contract, payload, encoded, block, weight, mode, names[mode],
                                       patternId++, counts, cases, results, samples);
                    }
                }
            }
            if (contract.organization == Organization::Segmented15) {
                for (std::size_t position = 0; position < 15U; ++position) {
                    executeCustom(contract, payload, encoded, {position}, "BCH15_SINGLE_ALL_POSITIONS",
                                  patternId++, true, counts, cases, results);
                }
                executeCustom(contract, payload, encoded, {0U,1U}, "BCH15_DOUBLE_SAME_BLOCK",
                              patternId++, false, counts, cases, results);
                executeCustom(contract, payload, encoded, {0U,15U}, "BCH15_DOUBLE_CROSS_BLOCK",
                              patternId++, true, counts, cases, results);
                std::vector<std::size_t> onePerBlock;
                for (std::size_t block = 0; block < contract.blockCount; ++block) onePerBlock.push_back(block*15U);
                executeCustom(contract, payload, encoded, onePerBlock, "BCH15_ONE_ERROR_EACH_BLOCK",
                              patternId++, true, counts, cases, results);
            }
            if (contract.organization == Organization::ShortenedMultiBlock) {
                executeCustom(contract, payload, encoded, {0U,contract.encodedLengthPerBlock[0]},
                              "MULTIBLOCK_ONE_ERROR_EACH_BLOCK", patternId++, true,
                              counts, cases, results);
            }
            const std::uint64_t total = counts["TRUE_SUCCESS"] + counts["DETECTED_FAILURE"] +
                counts["MISCORRECTION"] + counts["UNDETECTED_ERROR"] + counts["INVALID_CONFIGURATION"];
            summary << contract.caseId << ',' << total << ',' << counts["TRUE_SUCCESS"] << ','
                    << counts["DETECTED_FAILURE"] << ',' << counts["MISCORRECTION"] << ','
                    << counts["UNDETECTED_ERROR"] << ',' << counts["INVALID_CONFIGURATION"]
                    << ",0,ERROR_CAPABILITY_FIXED_CASES\n";
        }
        std::cout << "PASS_STAGE04_ERROR_CAPABILITY\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_STAGE04_ERROR_CAPABILITY: " << error.what() << '\n';
        return 1;
    }
}
