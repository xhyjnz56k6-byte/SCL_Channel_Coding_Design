#include "bch_segmented/bch15_encoder.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"
#include "common/frame_pool.hpp"

#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace scl::bch::segmented;

namespace {

struct Counters {
    unsigned syntheticNoiselessFrames = 0U;
    unsigned poolFrames = 0U;
    unsigned noiselessPayloadMismatch = 0U;
    unsigned encodedLengthMismatch = 0U;
    unsigned fillerMismatch = 0U;
    unsigned invalidInputFailures = 0U;
    unsigned singleBlockSingleErrorCases = 0U;
    unsigned singleBlockSingleErrorMismatch = 0U;
    unsigned multiBlockSingleErrorCases = 0U;
    unsigned multiBlockSingleErrorMismatch = 0U;
    unsigned sameBlockDoubleErrorCases = 0U;
    unsigned sameBlockDoubleRecoveredPayload = 0U;
    unsigned sameBlockDoubleReportedSuccessWrongPayload = 0U;
    unsigned fillerBoundaryCases = 0U;
    unsigned fillerBoundaryMismatch = 0U;
};

std::string statusName(Bch15DecodeStatus status) {
    switch (status) {
    case Bch15DecodeStatus::NO_ERROR:
        return "NO_ERROR";
    case Bch15DecodeStatus::CORRECTED_SINGLE_ERROR:
        return "CORRECTED_SINGLE_ERROR";
    case Bch15DecodeStatus::POST_CHECK_FAILED:
        return "POST_CHECK_FAILED";
    case Bch15DecodeStatus::UNRECOGNIZED_SYNDROME:
        return "UNRECOGNIZED_SYNDROME";
    }
    return "UNKNOWN";
}

std::string caseName(Bch15SegmentedCase caseId) {
    return bch15SegmentedConfig(caseId).name;
}

scl::common::BitVector pattern(scl::common::Length length, unsigned mode) {
    scl::common::BitVector bits(length, 0U);
    for (scl::common::Length index = 0U; index < length; ++index) {
        if (mode == 1U) bits[index] = 1U;
        if (mode == 2U) bits[index] = static_cast<scl::common::Bit>(index % 2U);
    }
    if (mode == 3U) bits[length - 1U] = 1U;
    return bits;
}

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

void requireStream(std::ofstream& stream, const std::string& path) {
    stream.flush();
    if (!stream) throw std::runtime_error("write or flush failed: " + path);
}

void writeTextFile(const std::filesystem::path& path, const std::string& body) {
    std::ofstream output(path, std::ios::binary);
    if (!output) throw std::runtime_error("cannot open output: " + path.string());
    output << body;
    requireStream(output, path.string());
}

scl::common::BitVector expectedPadded(const scl::common::BitVector& payload, const Bch15SegmentedConfig& config) {
    scl::common::BitVector padded = payload;
    padded.insert(padded.end(), config.fillerBits, 0U);
    return padded;
}

void verifyCaseConfig(Bch15SegmentedCase caseId) {
    const auto& config = bch15SegmentedConfig(caseId);
    require(config.blockPayloadLength == 11U, "block payload length");
    require(config.encodedBlockLength == 15U, "encoded block length");
    require(config.blockCount * config.blockPayloadLength == config.payloadLength + config.fillerBits, "padded length");
    require(config.blockCount * config.encodedBlockLength == config.encodedLength, "encoded length");
    if (caseId == Bch15SegmentedCase::S200) {
        require(config.payloadLength == 200U && config.blockCount == 19U && config.fillerBits == 9U &&
                    config.encodedLength == 285U,
                "S200 config");
    }
    if (caseId == Bch15SegmentedCase::S300) {
        require(config.payloadLength == 300U && config.blockCount == 28U && config.fillerBits == 8U &&
                    config.encodedLength == 420U,
                "S300 config");
    }
}

Bch15SegmentedEncodeResult verifyEncode(Bch15SegmentedCase caseId,
                                         const scl::common::BitVector& payload,
                                         const SyndromeTable& table,
                                         Counters& counters) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    if (encoded.encodedBits.size() != config.encodedLength) ++counters.encodedLengthMismatch;
    require(encoded.paddedMessageBits.size() == config.payloadLength + config.fillerBits, "padded message length");
    require(encoded.lengths.payloadLength == config.payloadLength, "length payload");
    require(encoded.lengths.fillerLength == config.fillerBits, "length filler");
    require(encoded.lengths.encodedLength == config.encodedLength, "length encoded");
    require(scl::common::computeCodeRate(encoded.lengths) ==
                static_cast<double>(config.payloadLength) / static_cast<double>(config.encodedLength),
            "common code rate");
    const auto padded = expectedPadded(payload, config);
    if (encoded.paddedMessageBits != padded) ++counters.fillerMismatch;
    for (scl::common::Length block = 0U; block < config.blockCount; ++block) {
        const auto messageBegin = encoded.paddedMessageBits.begin() +
                                  static_cast<std::ptrdiff_t>(block * config.blockPayloadLength);
        const scl::common::BitVector message(messageBegin, messageBegin + static_cast<std::ptrdiff_t>(config.blockPayloadLength));
        const auto codeBegin = encoded.encodedBits.begin() +
                               static_cast<std::ptrdiff_t>(block * config.encodedBlockLength);
        const scl::common::BitVector codeword(codeBegin, codeBegin + static_cast<std::ptrdiff_t>(config.encodedBlockLength));
        require(codeword == encodeBch15Systematic(message), "block order or codeword mismatch");
        require(syndromeValue(computeBch15Syndrome(codeword)) == 0U, "encoded block is not a legal BCH codeword");
    }
    return encoded;
}

Bch15SegmentedDecodeResult verifyNoiselessFrame(Bch15SegmentedCase caseId,
                                                 const scl::common::BitVector& payload,
                                                 const SyndromeTable& table,
                                                 Counters& counters) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto encoded = verifyEncode(caseId, payload, table, counters);
    auto decoded = decodeBch15Segmented(caseId, encoded.encodedBits, table);
    auditBch15SegmentedRecovery(payload, decoded);
    if (decoded.recoveredPayload != payload) ++counters.noiselessPayloadMismatch;
    require(decoded.recoveredPayload.size() == config.payloadLength, "recovered payload length");
    require(decoded.recoveredPaddedMessage.size() == config.payloadLength + config.fillerBits, "recovered padded length");
    require(decoded.recoveredPaddedMessage == encoded.paddedMessageBits, "recovered padded message");
    require(decoded.frameDetail.noErrorBlocks == config.blockCount, "noiseless NO_ERROR count");
    require(decoded.frameDetail.payloadCorrectBlocks == config.blockCount, "noiseless true block count");
    return decoded;
}

void verifyLastBlockMapping(Bch15SegmentedCase caseId, const scl::common::BitVector& payload) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    const scl::common::Length lastBlock = config.blockCount - 1U;
    const scl::common::Length payloadInLastBlock = config.blockPayloadLength - config.fillerBits;
    for (scl::common::Length local = 0U; local < config.blockPayloadLength; ++local) {
        const scl::common::Length paddedIndex = lastBlock * config.blockPayloadLength + local;
        if (local < payloadInLastBlock) {
            require(encoded.paddedMessageBits[paddedIndex] == payload[paddedIndex], "last block payload mapping");
        } else {
            require(encoded.paddedMessageBits[paddedIndex] == 0U, "last block filler mapping");
        }
    }
    if (caseId == Bch15SegmentedCase::S200) require(payloadInLastBlock == 2U, "S200 last block payload count");
    if (caseId == Bch15SegmentedCase::S300) require(payloadInLastBlock == 3U, "S300 last block payload count");
}

void verifyInvalidInputs(const SyndromeTable& table, Counters& counters) {
    try {
        static_cast<void>(encodeBch15Segmented(Bch15SegmentedCase::S200, pattern(300U, 0U)));
        ++counters.invalidInputFailures;
    } catch (const std::invalid_argument&) {
    }
    try {
        auto bad = pattern(200U, 0U);
        bad[7U] = 2U;
        static_cast<void>(encodeBch15Segmented(Bch15SegmentedCase::S200, bad));
        ++counters.invalidInputFailures;
    } catch (const std::invalid_argument&) {
    }
    try {
        static_cast<void>(decodeBch15Segmented(Bch15SegmentedCase::S300, scl::common::BitVector(285U, 0U), table));
        ++counters.invalidInputFailures;
    } catch (const std::invalid_argument&) {
    }
    try {
        auto bad = scl::common::BitVector(420U, 0U);
        bad[11U] = 2U;
        static_cast<void>(decodeBch15Segmented(Bch15SegmentedCase::S300, bad, table));
        ++counters.invalidInputFailures;
    } catch (const std::invalid_argument&) {
    }
}

void auditSingleBlockSingleErrors(Bch15SegmentedCase caseId,
                                  const SyndromeTable& table,
                                  Counters& counters,
                                  std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto payload = pattern(config.payloadLength, 2U);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    const scl::common::Length coveredBlocks = caseId == Bch15SegmentedCase::S200 ? 9U : 8U;
    for (scl::common::Length block = 0U; block < coveredBlocks; ++block) {
        for (scl::common::Length local = 0U; local < config.encodedBlockLength; ++local) {
            auto received = encoded.encodedBits;
            const scl::common::Length global = block * config.encodedBlockLength + local;
            received[global] ^= 1U;
            auto decoded = decodeBch15Segmented(caseId, received, table);
            auditBch15SegmentedRecovery(payload, decoded);
            const auto& detail = decoded.blockDetails[block].decoder;
            const bool pass = decoded.recoveredPayload == payload &&
                              detail.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR &&
                              detail.correctedPosition == static_cast<int>(local) &&
                              detail.correctedCodeword == scl::common::BitVector(encoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(block * 15U),
                                                                                 encoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(block * 15U + 15U));
            ++counters.singleBlockSingleErrorCases;
            if (!pass) ++counters.singleBlockSingleErrorMismatch;
            output << caseName(caseId) << ',' << block << ',' << local << ',' << global << ','
                   << statusName(detail.status) << ',' << detail.correctedPosition << ','
                   << (decoded.recoveredPayload == payload ? "true" : "false") << ','
                   << (pass ? "true" : "false") << '\n';
        }
    }
}

void runMultiBlockCase(Bch15SegmentedCase caseId,
                       const std::string& name,
                       const std::vector<std::pair<scl::common::Length, scl::common::Length>>& flips,
                       const SyndromeTable& table,
                       Counters& counters,
                       std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto payload = pattern(config.payloadLength, 3U);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    auto received = encoded.encodedBits;
    for (const auto& flip : flips) {
        received[flip.first * config.encodedBlockLength + flip.second] ^= 1U;
    }
    auto decoded = decodeBch15Segmented(caseId, received, table);
    auditBch15SegmentedRecovery(payload, decoded);
    const bool pass = decoded.recoveredPayload == payload && decoded.frameDetail.correctedBlocks == flips.size();
    ++counters.multiBlockSingleErrorCases;
    if (!pass) ++counters.multiBlockSingleErrorMismatch;
    output << caseName(caseId) << ',' << name << ',' << flips.size() << ','
           << decoded.frameDetail.correctedBlocks << ',' << decoded.frameDetail.payloadWrongBlocks << ','
           << (decoded.recoveredPayload == payload ? "true" : "false") << ',' << (pass ? "true" : "false") << '\n';
}

void auditMultiBlockSingleErrors(Bch15SegmentedCase caseId,
                                 const SyndromeTable& table,
                                 Counters& counters,
                                 std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    runMultiBlockCase(caseId, "first_last", {{0U, 0U}, {config.blockCount - 1U, 14U}}, table, counters, output);
    runMultiBlockCase(caseId, "adjacent", {{1U, 3U}, {2U, 9U}}, table, counters, output);
    runMultiBlockCase(caseId, "three_spread", {{0U, 1U}, {config.blockCount / 2U, 7U}, {config.blockCount - 1U, 13U}}, table, counters, output);
    std::vector<std::pair<scl::common::Length, scl::common::Length>> everyBlock;
    for (scl::common::Length block = 0U; block < config.blockCount; ++block) {
        everyBlock.push_back({block, block % 15U});
    }
    runMultiBlockCase(caseId, "every_block_one", everyBlock, table, counters, output);
}

void runDoubleErrorCase(Bch15SegmentedCase caseId,
                        const std::string& name,
                        scl::common::Length block,
                        scl::common::Length firstLocal,
                        scl::common::Length secondLocal,
                        const SyndromeTable& table,
                        Counters& counters,
                        std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto payload = pattern(config.payloadLength, 2U);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    auto received = encoded.encodedBits;
    received[block * config.encodedBlockLength + firstLocal] ^= 1U;
    received[block * config.encodedBlockLength + secondLocal] ^= 1U;
    auto decoded = decodeBch15Segmented(caseId, received, table);
    auditBch15SegmentedRecovery(payload, decoded);
    const bool payloadRecovered = decoded.recoveredPayload == payload;
    const bool reportedSuccessWrong = decoded.blockDetails[block].decoder.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR &&
                                      decoded.frameDetail.payloadWrongBlocks > 0U;
    ++counters.sameBlockDoubleErrorCases;
    if (payloadRecovered) ++counters.sameBlockDoubleRecoveredPayload;
    if (reportedSuccessWrong) ++counters.sameBlockDoubleReportedSuccessWrongPayload;
    output << caseName(caseId) << ',' << name << ',' << block << ',' << firstLocal << ';' << secondLocal << ','
           << statusName(decoded.blockDetails[block].decoder.status) << ','
           << (decoded.blockDetails[block].decoder.correctedCodeword ==
               scl::common::BitVector(encoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(block * 15U),
                                      encoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(block * 15U + 15U))
                   ? "true"
                   : "false")
           << ',' << (payloadRecovered ? "true" : "false") << ','
           << (reportedSuccessWrong ? "true" : "false") << '\n';
}

void auditSameBlockDoubleErrors(Bch15SegmentedCase caseId,
                                const SyndromeTable& table,
                                Counters& counters,
                                std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    const scl::common::Length lastBlock = config.blockCount - 1U;
    const scl::common::Length firstFiller = config.blockPayloadLength - config.fillerBits;
    runDoubleErrorCase(caseId, "two_payload", 0U, 0U, 1U, table, counters, output);
    runDoubleErrorCase(caseId, "payload_parity", 0U, 0U, 11U, table, counters, output);
    runDoubleErrorCase(caseId, "two_parity", 0U, 11U, 12U, table, counters, output);
    runDoubleErrorCase(caseId, "payload_filler", lastBlock, 0U, firstFiller, table, counters, output);
    runDoubleErrorCase(caseId, "two_filler", lastBlock, firstFiller, firstFiller + 1U, table, counters, output);
    runDoubleErrorCase(caseId, "filler_parity", lastBlock, firstFiller, 11U, table, counters, output);
}

void auditFillerBoundary(Bch15SegmentedCase caseId,
                         const SyndromeTable& table,
                         Counters& counters,
                         std::ofstream& output) {
    const auto& config = bch15SegmentedConfig(caseId);
    const auto payload = pattern(config.payloadLength, 3U);
    verifyLastBlockMapping(caseId, payload);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    const scl::common::Length lastBlock = config.blockCount - 1U;
    const scl::common::Length payloadInLastBlock = config.blockPayloadLength - config.fillerBits;
    for (scl::common::Length local = 0U; local < config.encodedBlockLength; ++local) {
        auto received = encoded.encodedBits;
        received[lastBlock * config.encodedBlockLength + local] ^= 1U;
        auto decoded = decodeBch15Segmented(caseId, received, table);
        auditBch15SegmentedRecovery(payload, decoded);
        const bool pass = decoded.recoveredPayload == payload &&
                          decoded.blockDetails[lastBlock].decoder.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR;
        ++counters.fillerBoundaryCases;
        if (!pass) ++counters.fillerBoundaryMismatch;
        const char* kind = local < payloadInLastBlock ? "payload" : (local < 11U ? "filler" : "parity");
        output << caseName(caseId) << ',' << lastBlock << ',' << local << ',' << kind << ','
               << statusName(decoded.blockDetails[lastBlock].decoder.status) << ','
               << (decoded.recoveredPayload == payload ? "true" : "false") << ','
               << (pass ? "true" : "false") << '\n';
    }
}

void verifyPool(Bch15SegmentedCase caseId,
                const std::string& manifestPath,
                const std::string& expectedId,
                const SyndromeTable& table,
                Counters& counters,
                std::ofstream& output) {
    const scl::common::PackedFramePoolReader reader(manifestPath);
    require(reader.framePoolId() == expectedId, "pool id mismatch");
    require(reader.frameCount() >= 100U, "pool count");
    for (scl::common::FrameIndex index = 0U; index < 100U; ++index) {
        const auto frame = reader.readFrame(index);
        require(frame.frameIndex == index, "frame index mismatch");
        require(frame.payloadLength == bch15SegmentedConfig(caseId).payloadLength, "pool payload length");
        verifyNoiselessFrame(caseId, frame.payloadBits, table, counters);
        ++counters.poolFrames;
        output << caseName(caseId) << ',' << expectedId << ',' << index << ','
               << frame.payloadBits.size() << ",true\n";
    }
}

void writeConfigCsv(const std::filesystem::path& path) {
    std::ofstream output(path, std::ios::binary);
    if (!output) throw std::runtime_error("cannot open adapter_config.csv");
    output << "caseName,payloadLength,blockPayloadLength,blockCount,fillerBits,encodedBlockLength,encodedLength,codeRate,lastBlockPayload,lastBlockFiller\n";
    for (const auto caseId : {Bch15SegmentedCase::S200, Bch15SegmentedCase::S300}) {
        const auto& config = bch15SegmentedConfig(caseId);
        scl::common::CodeLengths lengths;
        lengths.payloadLength = config.payloadLength;
        lengths.codecInputLength = config.payloadLength + config.fillerBits;
        lengths.encodedLength = config.encodedLength;
        lengths.transmittedLength = config.encodedLength;
        lengths.fillerLength = config.fillerBits;
        output << config.name << ',' << config.payloadLength << ',' << config.blockPayloadLength << ','
               << config.blockCount << ',' << config.fillerBits << ',' << config.encodedBlockLength << ','
               << config.encodedLength << ',' << scl::common::computeCodeRate(lengths) << ','
               << (config.blockPayloadLength - config.fillerBits) << ',' << config.fillerBits << '\n';
    }
    requireStream(output, path.string());
}

bool allPassed(const Counters& c) {
    return c.syntheticNoiselessFrames == 8U && c.poolFrames == 200U && c.noiselessPayloadMismatch == 0U &&
           c.encodedLengthMismatch == 0U && c.fillerMismatch == 0U && c.invalidInputFailures == 0U &&
           c.singleBlockSingleErrorCases == 255U && c.singleBlockSingleErrorMismatch == 0U &&
           c.multiBlockSingleErrorCases == 8U && c.multiBlockSingleErrorMismatch == 0U &&
           c.sameBlockDoubleErrorCases == 12U && c.sameBlockDoubleRecoveredPayload <= c.sameBlockDoubleErrorCases &&
           c.sameBlockDoubleReportedSuccessWrongPayload == 12U && c.fillerBoundaryCases == 30U &&
           c.fillerBoundaryMismatch == 0U;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error("usage: <output-dir> <k200-manifest> <k300-manifest>");
        const std::filesystem::path outputDirectory(argv[1]);
        std::filesystem::create_directories(outputDirectory);
        Counters counters;
        const SyndromeTable table = buildBch15SyndromeTable();

        for (const auto caseId : {Bch15SegmentedCase::S200, Bch15SegmentedCase::S300}) {
            verifyCaseConfig(caseId);
            for (const unsigned mode : {0U, 1U, 2U, 3U}) {
                verifyNoiselessFrame(caseId, pattern(bch15SegmentedConfig(caseId).payloadLength, mode), table, counters);
                ++counters.syntheticNoiselessFrames;
            }
        }

        std::ofstream poolCsv(outputDirectory / "frame_pool_audit.csv", std::ios::binary);
        std::ofstream singleCsv(outputDirectory / "single_error_block_audit.csv", std::ios::binary);
        std::ofstream multiCsv(outputDirectory / "multi_block_single_error_audit.csv", std::ios::binary);
        std::ofstream doubleCsv(outputDirectory / "double_error_block_audit.csv", std::ios::binary);
        std::ofstream fillerCsv(outputDirectory / "filler_boundary_audit.csv", std::ios::binary);
        if (!poolCsv || !singleCsv || !multiCsv || !doubleCsv || !fillerCsv) throw std::runtime_error("cannot open audit csv");
        poolCsv << "caseName,poolId,frameIndex,payloadLength,payloadRecovered\n";
        singleCsv << "caseName,blockIndex,localPosition,globalPosition,status,correctedPosition,payloadRecovered,pass\n";
        multiCsv << "caseName,caseId,errorCount,correctedBlocks,payloadWrongBlocks,payloadRecovered,pass\n";
        doubleCsv << "caseName,doubleCase,blockIndex,localPositions,status,codewordRecovered,payloadRecovered,reportedSuccessWrongPayload\n";
        fillerCsv << "caseName,lastBlock,localPosition,bitClass,status,payloadRecovered,pass\n";

        verifyPool(Bch15SegmentedCase::S200, argv[2], "payload_k200_seed2026072001_policy1_frames100", table, counters, poolCsv);
        verifyPool(Bch15SegmentedCase::S300, argv[3], "payload_k300_seed2026072001_policy1_frames100", table, counters, poolCsv);
        verifyInvalidInputs(table, counters);
        for (const auto caseId : {Bch15SegmentedCase::S200, Bch15SegmentedCase::S300}) {
            auditSingleBlockSingleErrors(caseId, table, counters, singleCsv);
            auditMultiBlockSingleErrors(caseId, table, counters, multiCsv);
            auditSameBlockDoubleErrors(caseId, table, counters, doubleCsv);
            auditFillerBoundary(caseId, table, counters, fillerCsv);
        }
        requireStream(poolCsv, (outputDirectory / "frame_pool_audit.csv").string());
        requireStream(singleCsv, (outputDirectory / "single_error_block_audit.csv").string());
        requireStream(multiCsv, (outputDirectory / "multi_block_single_error_audit.csv").string());
        requireStream(doubleCsv, (outputDirectory / "double_error_block_audit.csv").string());
        requireStream(fillerCsv, (outputDirectory / "filler_boundary_audit.csv").string());

        writeConfigCsv(outputDirectory / "adapter_config.csv");
        writeTextFile(outputDirectory / "noiseless_recovery_summary.csv",
                      "metric,value\nsyntheticNoiselessFrames," + std::to_string(counters.syntheticNoiselessFrames) +
                          "\npoolFrames," + std::to_string(counters.poolFrames) +
                          "\nnoiselessPayloadMismatch," + std::to_string(counters.noiselessPayloadMismatch) +
                          "\nencodedLengthMismatch," + std::to_string(counters.encodedLengthMismatch) +
                          "\nfillerMismatch," + std::to_string(counters.fillerMismatch) + "\n");
        writeTextFile(outputDirectory / "test_summary.csv",
                      "metric,value\nsyntheticNoiselessFrames," + std::to_string(counters.syntheticNoiselessFrames) +
                          "\npoolFrames," + std::to_string(counters.poolFrames) +
                          "\ninvalidInputFailures," + std::to_string(counters.invalidInputFailures) +
                          "\nsingleBlockSingleErrorCases," + std::to_string(counters.singleBlockSingleErrorCases) +
                          "\nsingleBlockSingleErrorMismatch," + std::to_string(counters.singleBlockSingleErrorMismatch) +
                          "\nmultiBlockSingleErrorCases," + std::to_string(counters.multiBlockSingleErrorCases) +
                          "\nmultiBlockSingleErrorMismatch," + std::to_string(counters.multiBlockSingleErrorMismatch) +
                          "\nsameBlockDoubleErrorCases," + std::to_string(counters.sameBlockDoubleErrorCases) +
                          "\nsameBlockDoubleRecoveredPayload," + std::to_string(counters.sameBlockDoubleRecoveredPayload) +
                          "\nsameBlockDoubleReportedSuccessWrongPayload," + std::to_string(counters.sameBlockDoubleReportedSuccessWrongPayload) +
                          "\nfillerBoundaryCases," + std::to_string(counters.fillerBoundaryCases) +
                          "\nfillerBoundaryMismatch," + std::to_string(counters.fillerBoundaryMismatch) + "\n");
        if (!allPassed(counters)) throw std::runtime_error("BCH-05 segmented adapter gate counters mismatch");
        std::cout << "BCH15 segmented adapter PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BCH15 segmented adapter FAIL: " << error.what() << '\n';
        return 1;
    }
}
