#include "bch_segmented/bch15_encoder.hpp"
#include "bch_segmented/bch15_lookup_decoder.hpp"

#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace scl::bch::segmented;

namespace {

struct AuditCounters {
    unsigned noErrorCaseCount = 0U;
    unsigned noErrorPayloadMismatch = 0U;
    unsigned noErrorCodewordMismatch = 0U;
    unsigned noErrorStatusMismatch = 0U;
    unsigned noErrorLookupHitMismatch = 0U;
    unsigned noErrorSyndromeMismatch = 0U;
    unsigned singleErrorCaseCount = 0U;
    unsigned singleErrorPayloadMismatch = 0U;
    unsigned correctedPositionMismatch = 0U;
    unsigned postSyndromeMismatch = 0U;
    unsigned lookupMissForSingleError = 0U;
    unsigned singleErrorStatusMismatch = 0U;
    unsigned singleErrorCodewordMismatch = 0U;
    unsigned singleErrorSyndromeBeforeMismatch = 0U;
    unsigned doubleErrorCaseCount = 0U;
    unsigned doubleErrorCorrectedStatusCount = 0U;
    unsigned doubleErrorNoErrorStatusCount = 0U;
    unsigned doubleErrorPostCheckFailedCount = 0U;
    unsigned doubleErrorUnrecognizedCount = 0U;
    unsigned doubleErrorLookupHitCount = 0U;
    unsigned doubleErrorPostSyndromeZeroCount = 0U;
    unsigned decodedToOriginalCodeword = 0U;
    unsigned decodedToOriginalPayload = 0U;
    unsigned miscorrectedToAnotherValidCodeword = 0U;
    unsigned reportedCorrectedButPayloadWrong = 0U;
    unsigned fixedSeedCaseCount = 0U;
    unsigned fixedSeedParseError = 0U;
    unsigned invalidInputMismatch = 0U;
    unsigned unrecognizedSyndromeStatusMismatch = 0U;
    unsigned postCheckFailedStatusMismatch = 0U;
    unsigned invalidTablePositionMismatch = 0U;
};

struct Seed {
    std::string id;
    unsigned weight = 0U;
    std::vector<unsigned> positions;
};

std::string bitString(const scl::common::BitVector& bits) {
    std::string text;
    text.reserve(bits.size());
    for (const auto bit : bits) {
        text.push_back(bit == 0U ? '0' : '1');
    }
    return text;
}

scl::common::BitVector messageFromDecimal(unsigned value) {
    scl::common::BitVector message(11U, 0U);
    for (unsigned index = 0U; index < 11U; ++index) {
        message[index] = static_cast<std::uint8_t>((value >> (10U - index)) & 1U);
    }
    return message;
}

scl::common::BitVector messageFromString(const std::string& text) {
    if (text.size() != 11U) {
        throw std::runtime_error("fixed message length is not 11");
    }
    scl::common::BitVector message(11U, 0U);
    for (std::size_t index = 0U; index < text.size(); ++index) {
        if (text[index] != '0' && text[index] != '1') {
            throw std::runtime_error("fixed message contains non-bit value");
        }
        message[index] = static_cast<std::uint8_t>(text[index] - '0');
    }
    return message;
}

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

bool isCodeword(const scl::common::BitVector& word) {
    return syndromeValue(computeBch15Syndrome(word)) == 0U;
}

void requireStream(std::ofstream& stream, const std::string& path) {
    stream.flush();
    if (!stream) {
        throw std::runtime_error("write or flush failed: " + path);
    }
}

void writeTextFile(const std::filesystem::path& path, const std::string& body) {
    std::ofstream stream(path, std::ios::binary);
    if (!stream) {
        throw std::runtime_error("cannot open output: " + path.string());
    }
    stream << body;
    requireStream(stream, path.string());
}

std::vector<Seed> readSeeds(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open seed fixture: " + path.string());
    }

    std::string line;
    std::getline(input, line);
    if (line != "seedId,errorWeight,errorPositions") {
        throw std::runtime_error("seed fixture header mismatch");
    }

    std::vector<Seed> seeds;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const std::size_t first = line.find(',');
        const std::size_t second = line.find(',', first + 1U);
        if (first == std::string::npos || second == std::string::npos) {
            throw std::runtime_error("seed fixture row malformed");
        }
        Seed seed;
        seed.id = line.substr(0U, first);
        seed.weight = static_cast<unsigned>(std::stoul(line.substr(first + 1U, second - first - 1U)));
        std::string positions = line.substr(second + 1U);
        if (positions.size() >= 2U && positions.front() == '"' && positions.back() == '"') {
            positions = positions.substr(1U, positions.size() - 2U);
        }
        std::stringstream parser(positions);
        std::string position;
        while (std::getline(parser, position, ';')) {
            seed.positions.push_back(static_cast<unsigned>(std::stoul(position)));
        }
        if (seed.positions.size() != seed.weight || (seed.weight != 3U && seed.weight != 4U)) {
            throw std::runtime_error("seed fixture weight mismatch");
        }
        for (const unsigned value : seed.positions) {
            if (value >= 15U) {
                throw std::runtime_error("seed fixture position out of range");
            }
        }
        seeds.push_back(seed);
    }
    if (seeds.size() != 12U) {
        throw std::runtime_error("seed fixture must contain 12 rows");
    }
    return seeds;
}

void verifyNoErrorCases(const SyndromeTable& table, AuditCounters& counters) {
    for (unsigned value = 0U; value < 2048U; ++value) {
        const auto message = messageFromDecimal(value);
        const auto codeword = encodeBch15Systematic(message);
        const auto decoded = decodeBch15Lookup(codeword, table);
        ++counters.noErrorCaseCount;
        if (decoded.decodedMessage != message) ++counters.noErrorPayloadMismatch;
        if (decoded.correctedCodeword != codeword) ++counters.noErrorCodewordMismatch;
        if (decoded.status != Bch15DecodeStatus::NO_ERROR) ++counters.noErrorStatusMismatch;
        if (decoded.lookupHit || decoded.correctedPosition != -1) ++counters.noErrorLookupHitMismatch;
        if (syndromeValue(decoded.syndromeBefore) != 0U || syndromeValue(decoded.syndromeAfter) != 0U) ++counters.noErrorSyndromeMismatch;
    }
}

void verifySingleErrorCases(const SyndromeTable& table, AuditCounters& counters) {
    for (unsigned value = 0U; value < 2048U; ++value) {
        const auto message = messageFromDecimal(value);
        const auto codeword = encodeBch15Systematic(message);
        for (unsigned position = 0U; position < 15U; ++position) {
            auto received = codeword;
            received[position] ^= 1U;
            const auto decoded = decodeBch15Lookup(received, table);
            const auto expectedSyndrome = syndromeValue(computeBch15Syndrome(received));
            ++counters.singleErrorCaseCount;
            if (decoded.decodedMessage != message) ++counters.singleErrorPayloadMismatch;
            if (decoded.correctedCodeword != codeword) ++counters.singleErrorCodewordMismatch;
            if (decoded.correctedPosition != static_cast<int>(position)) ++counters.correctedPositionMismatch;
            if (syndromeValue(decoded.syndromeAfter) != 0U) ++counters.postSyndromeMismatch;
            if (!decoded.lookupHit) ++counters.lookupMissForSingleError;
            if (decoded.status != Bch15DecodeStatus::CORRECTED_SINGLE_ERROR) ++counters.singleErrorStatusMismatch;
            if (syndromeValue(decoded.syndromeBefore) != expectedSyndrome) ++counters.singleErrorSyndromeBeforeMismatch;
        }
    }
}

void verifyDoubleErrorCases(const SyndromeTable& table, AuditCounters& counters) {
    for (unsigned value = 0U; value < 2048U; ++value) {
        const auto message = messageFromDecimal(value);
        const auto codeword = encodeBch15Systematic(message);
        for (unsigned first = 0U; first < 15U; ++first) {
            for (unsigned second = first + 1U; second < 15U; ++second) {
                auto received = codeword;
                received[first] ^= 1U;
                received[second] ^= 1U;
                const auto decoded = decodeBch15Lookup(received, table);
                ++counters.doubleErrorCaseCount;
                if (decoded.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR) ++counters.doubleErrorCorrectedStatusCount;
                if (decoded.status == Bch15DecodeStatus::NO_ERROR) ++counters.doubleErrorNoErrorStatusCount;
                if (decoded.status == Bch15DecodeStatus::POST_CHECK_FAILED) ++counters.doubleErrorPostCheckFailedCount;
                if (decoded.status == Bch15DecodeStatus::UNRECOGNIZED_SYNDROME) ++counters.doubleErrorUnrecognizedCount;
                if (decoded.lookupHit) ++counters.doubleErrorLookupHitCount;
                if (syndromeValue(decoded.syndromeAfter) == 0U) ++counters.doubleErrorPostSyndromeZeroCount;
                if (decoded.correctedCodeword == codeword) ++counters.decodedToOriginalCodeword;
                if (decoded.decodedMessage == message) ++counters.decodedToOriginalPayload;
                if (decoded.correctedCodeword != codeword && isCodeword(decoded.correctedCodeword)) ++counters.miscorrectedToAnotherValidCodeword;
                if (decoded.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR && decoded.decodedMessage != message) ++counters.reportedCorrectedButPayloadWrong;
            }
        }
    }
}

void verifyInvalidInputs(const SyndromeTable& table, AuditCounters& counters) {
    const std::array<scl::common::BitVector, 3> invalid = {
        scl::common::BitVector(14U, 0U), scl::common::BitVector(16U, 0U), scl::common::BitVector(15U, 0U)};
    auto nonBit = invalid[2];
    nonBit[4] = 2U;
    for (const auto& value : {invalid[0], invalid[1], nonBit}) {
        try {
            static_cast<void>(decodeBch15Lookup(value, table));
            ++counters.invalidInputMismatch;
        } catch (const std::invalid_argument&) {
        }
    }
    try {
        static_cast<void>(decodeBch15Lookup(encodeBch15Systematic(messageFromDecimal(0U)), table));
    } catch (const std::exception&) {
        ++counters.invalidInputMismatch;
    }
}

void verifyCorruptedTableStatuses(const SyndromeTable& original, AuditCounters& counters) {
    const auto codeword = encodeBch15Systematic(messageFromDecimal(0U));
    auto received = codeword;
    received[14U] ^= 1U;

    SyndromeTable missing = original;
    for (auto& entry : missing.entries) {
        if (entry.syndrome == 1U) entry.syndrome = 2U;
    }
    const auto unknown = decodeBch15Lookup(received, missing);
    if (unknown.status != Bch15DecodeStatus::UNRECOGNIZED_SYNDROME || unknown.lookupHit ||
        unknown.correctedPosition != -1 || unknown.correctedCodeword != received ||
        unknown.syndromeAfter != unknown.syndromeBefore || unknown.decodedMessage != scl::common::BitVector(received.begin(), received.begin() + 11)) {
        ++counters.unrecognizedSyndromeStatusMismatch;
    }

    SyndromeTable wrong = original;
    for (auto& entry : wrong.entries) {
        if (entry.syndrome == 1U) entry.errorPosition = 0U;
    }
    const auto post = decodeBch15Lookup(received, wrong);
    if (post.status != Bch15DecodeStatus::POST_CHECK_FAILED || !post.lookupHit || post.correctedPosition != 0 ||
        syndromeValue(post.syndromeAfter) == 0U || post.correctedCodeword == received) {
        ++counters.postCheckFailedStatusMismatch;
    }

    for (const unsigned invalidPosition : {15U, 100U}) {
        SyndromeTable invalid = original;
        for (auto& entry : invalid.entries) {
            if (entry.syndrome == 1U) entry.errorPosition = invalidPosition;
        }
        const auto result = decodeBch15Lookup(received, invalid);
        if (result.status != Bch15DecodeStatus::POST_CHECK_FAILED || !result.lookupHit ||
            result.correctedPosition != static_cast<int>(invalidPosition) || result.correctedCodeword != received ||
            result.syndromeAfter != result.syndromeBefore) {
            ++counters.invalidTablePositionMismatch;
        }
    }
}

void verifyFixedMultiErrorSeeds(const SyndromeTable& table, const std::vector<Seed>& seeds,
                                AuditCounters& counters, std::ofstream& output) {
    const std::array<std::string, 4> messages = {"00000000000", "11111111111", "10101010101", "01010101010"};
    output << "seedId,messageBits,originalCodeword,errorWeight,errorPositions,receivedCodeword,syndromeBefore,lookupHit,correctedPosition,syndromeAfter,status,correctedCodeword,decodedMessage,payloadRecovered,codewordRecovered,miscorrection\n";
    for (const auto& seed : seeds) {
        std::string positions;
        for (std::size_t index = 0U; index < seed.positions.size(); ++index) {
            if (index != 0U) positions += ';';
            positions += std::to_string(seed.positions[index]);
        }
        for (const auto& messageText : messages) {
            const auto message = messageFromString(messageText);
            const auto codeword = encodeBch15Systematic(message);
            auto received = codeword;
            for (const unsigned position : seed.positions) received[position] ^= 1U;
            const auto decoded = decodeBch15Lookup(received, table);
            const bool payloadRecovered = decoded.decodedMessage == message;
            const bool codewordRecovered = decoded.correctedCodeword == codeword;
            const bool miscorrection = decoded.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR && !payloadRecovered;
            output << seed.id << ',' << messageText << ',' << bitString(codeword) << ',' << seed.weight << ','
                   << '"' << positions << '"' << ',' << bitString(received) << ',' << bitString(decoded.syndromeBefore) << ','
                   << (decoded.lookupHit ? "true" : "false") << ',' << decoded.correctedPosition << ','
                   << bitString(decoded.syndromeAfter) << ',' << statusName(decoded.status) << ','
                   << bitString(decoded.correctedCodeword) << ',' << bitString(decoded.decodedMessage) << ','
                   << (payloadRecovered ? "true" : "false") << ',' << (codewordRecovered ? "true" : "false") << ','
                   << (miscorrection ? "true" : "false") << '\n';
            ++counters.fixedSeedCaseCount;
        }
    }
}

void writeSummaryFiles(const std::filesystem::path& outputDirectory, const AuditCounters& c) {
    writeTextFile(outputDirectory / "no_error_summary.csv", "metric,value\nnoErrorCaseCount," + std::to_string(c.noErrorCaseCount) +
        "\nnoErrorPayloadMismatch," + std::to_string(c.noErrorPayloadMismatch) + "\nnoErrorCodewordMismatch," + std::to_string(c.noErrorCodewordMismatch) +
        "\nnoErrorStatusMismatch," + std::to_string(c.noErrorStatusMismatch) + "\nnoErrorLookupHitMismatch," + std::to_string(c.noErrorLookupHitMismatch) +
        "\nnoErrorSyndromeMismatch," + std::to_string(c.noErrorSyndromeMismatch) + "\n");
    writeTextFile(outputDirectory / "single_error_summary.csv", "metric,value\nsingleErrorCaseCount," + std::to_string(c.singleErrorCaseCount) +
        "\nsingleErrorPayloadMismatch," + std::to_string(c.singleErrorPayloadMismatch) + "\ncorrectedPositionMismatch," + std::to_string(c.correctedPositionMismatch) +
        "\npostSyndromeMismatch," + std::to_string(c.postSyndromeMismatch) + "\nlookupMissForSingleError," + std::to_string(c.lookupMissForSingleError) +
        "\nsingleErrorStatusMismatch," + std::to_string(c.singleErrorStatusMismatch) + "\nsingleErrorCodewordMismatch," + std::to_string(c.singleErrorCodewordMismatch) +
        "\nsingleErrorSyndromeBeforeMismatch," + std::to_string(c.singleErrorSyndromeBeforeMismatch) + "\n");
    writeTextFile(outputDirectory / "double_error_audit.csv", "metric,value\ndoubleErrorCaseCount," + std::to_string(c.doubleErrorCaseCount) +
        "\ndoubleErrorCorrectedStatusCount," + std::to_string(c.doubleErrorCorrectedStatusCount) + "\ndoubleErrorNoErrorStatusCount," + std::to_string(c.doubleErrorNoErrorStatusCount) +
        "\ndoubleErrorPostCheckFailedCount," + std::to_string(c.doubleErrorPostCheckFailedCount) + "\ndoubleErrorUnrecognizedCount," + std::to_string(c.doubleErrorUnrecognizedCount) +
        "\ndoubleErrorLookupHitCount," + std::to_string(c.doubleErrorLookupHitCount) + "\ndoubleErrorPostSyndromeZeroCount," + std::to_string(c.doubleErrorPostSyndromeZeroCount) +
        "\ndecodedToOriginalCodeword," + std::to_string(c.decodedToOriginalCodeword) + "\ndecodedToOriginalPayload," + std::to_string(c.decodedToOriginalPayload) +
        "\nmiscorrectedToAnotherValidCodeword," + std::to_string(c.miscorrectedToAnotherValidCodeword) + "\nreportedCorrectedButPayloadWrong," + std::to_string(c.reportedCorrectedButPayloadWrong) + "\n");
    writeTextFile(outputDirectory / "status_summary.csv", "status,count\nNO_ERROR," + std::to_string(c.doubleErrorNoErrorStatusCount) +
        "\nCORRECTED_SINGLE_ERROR," + std::to_string(c.doubleErrorCorrectedStatusCount) + "\nPOST_CHECK_FAILED," + std::to_string(c.doubleErrorPostCheckFailedCount) +
        "\nUNRECOGNIZED_SYNDROME," + std::to_string(c.doubleErrorUnrecognizedCount) + "\n");
    writeTextFile(outputDirectory / "test_summary.csv", "metric,value\nnoErrorCaseCount," + std::to_string(c.noErrorCaseCount) +
        "\nsingleErrorCaseCount," + std::to_string(c.singleErrorCaseCount) + "\ndoubleErrorCaseCount," + std::to_string(c.doubleErrorCaseCount) +
        "\nfixedSeedCaseCount," + std::to_string(c.fixedSeedCaseCount) + "\nnoErrorPayloadMismatch," + std::to_string(c.noErrorPayloadMismatch) +
        "\nsingleErrorPayloadMismatch," + std::to_string(c.singleErrorPayloadMismatch) + "\ncorrectedPositionMismatch," + std::to_string(c.correctedPositionMismatch) +
        "\npostSyndromeMismatch," + std::to_string(c.postSyndromeMismatch) + "\nlookupMissForSingleError," + std::to_string(c.lookupMissForSingleError) +
        "\ndecodedToOriginalCodeword," + std::to_string(c.decodedToOriginalCodeword) + "\ndecodedToOriginalPayload," + std::to_string(c.decodedToOriginalPayload) +
        "\nmiscorrectedToAnotherValidCodeword," + std::to_string(c.miscorrectedToAnotherValidCodeword) + "\nreportedCorrectedButPayloadWrong," + std::to_string(c.reportedCorrectedButPayloadWrong) +
        "\nunrecognizedSyndromeStatusMismatch," + std::to_string(c.unrecognizedSyndromeStatusMismatch) + "\npostCheckFailedStatusMismatch," + std::to_string(c.postCheckFailedStatusMismatch) +
        "\ninvalidTablePositionMismatch," + std::to_string(c.invalidTablePositionMismatch) + "\ninvalidInputMismatch," + std::to_string(c.invalidInputMismatch) + "\n");
}

bool allPassed(const AuditCounters& c) {
    return c.noErrorCaseCount == 2048U && c.singleErrorCaseCount == 30720U && c.doubleErrorCaseCount == 215040U &&
        c.doubleErrorCorrectedStatusCount == 215040U && c.doubleErrorLookupHitCount == 215040U && c.doubleErrorPostSyndromeZeroCount == 215040U &&
        c.miscorrectedToAnotherValidCodeword == 215040U && c.reportedCorrectedButPayloadWrong == 215040U && c.fixedSeedCaseCount == 48U &&
        c.noErrorPayloadMismatch == 0U && c.noErrorCodewordMismatch == 0U && c.noErrorStatusMismatch == 0U && c.noErrorLookupHitMismatch == 0U &&
        c.noErrorSyndromeMismatch == 0U && c.singleErrorPayloadMismatch == 0U && c.singleErrorCodewordMismatch == 0U &&
        c.correctedPositionMismatch == 0U && c.postSyndromeMismatch == 0U && c.lookupMissForSingleError == 0U &&
        c.singleErrorStatusMismatch == 0U && c.singleErrorSyndromeBeforeMismatch == 0U && c.decodedToOriginalCodeword == 0U &&
        c.decodedToOriginalPayload == 0U && c.doubleErrorNoErrorStatusCount == 0U && c.doubleErrorPostCheckFailedCount == 0U &&
        c.doubleErrorUnrecognizedCount == 0U && c.unrecognizedSyndromeStatusMismatch == 0U && c.postCheckFailedStatusMismatch == 0U &&
        c.invalidTablePositionMismatch == 0U && c.invalidInputMismatch == 0U;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::runtime_error("usage: test_bch15_lookup_decoder <output-directory> <seed-fixture>");
        }
        const std::filesystem::path outputDirectory(argv[1]);
        const std::filesystem::path seedFixture(argv[2]);
        const auto table = buildBch15SyndromeTable();
        AuditCounters counters;
        const auto seeds = readSeeds(seedFixture);
        verifyNoErrorCases(table, counters);
        verifySingleErrorCases(table, counters);
        verifyDoubleErrorCases(table, counters);
        verifyInvalidInputs(table, counters);
        verifyCorruptedTableStatuses(table, counters);
        std::ofstream multiOutput(outputDirectory / "multi_error_seed_audit.csv", std::ios::binary);
        if (!multiOutput) throw std::runtime_error("cannot open multi_error_seed_audit.csv");
        verifyFixedMultiErrorSeeds(table, seeds, counters, multiOutput);
        requireStream(multiOutput, (outputDirectory / "multi_error_seed_audit.csv").string());
        writeSummaryFiles(outputDirectory, counters);
        if (!allPassed(counters)) throw std::runtime_error("audit counters did not meet BCH-04 gate");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BCH15 lookup decoder FAIL: " << error.what() << '\n';
        return 1;
    }
}
