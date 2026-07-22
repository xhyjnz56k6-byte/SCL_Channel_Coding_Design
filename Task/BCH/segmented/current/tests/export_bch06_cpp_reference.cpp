#include "bch_segmented/bch15_encoder.hpp"
#include "bch_segmented/bch15_lookup_decoder.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"
#include "common/frame_pool.hpp"

#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace scl::bch::segmented;

namespace {

std::string bits(const scl::common::BitVector& v) {
    std::string s;
    s.reserve(v.size());
    for (const auto b : v) s.push_back(static_cast<char>('0' + b));
    return s;
}

std::string tf(bool value) { return value ? "true" : "false"; }

std::string status(Bch15DecodeStatus value) {
    switch (value) {
        case Bch15DecodeStatus::NO_ERROR: return "NO_ERROR";
        case Bch15DecodeStatus::CORRECTED_SINGLE_ERROR: return "CORRECTED_SINGLE_ERROR";
        case Bch15DecodeStatus::POST_CHECK_FAILED: return "POST_CHECK_FAILED";
        case Bch15DecodeStatus::UNRECOGNIZED_SYNDROME: return "UNRECOGNIZED_SYNDROME";
    }
    return "UNRECOGNIZED_SYNDROME";
}

scl::common::BitVector message(unsigned index) {
    scl::common::BitVector v(11U, 0U);
    for (unsigned i = 0; i < 11U; ++i) v[i] = (index >> (10U - i)) & 1U;
    return v;
}

scl::common::BitVector pattern(scl::common::Length n, unsigned mode) {
    scl::common::BitVector v(n, 0U);
    for (scl::common::Length i = 0; i < n; ++i) {
        if (mode == 1U) v[i] = 1U;
        if (mode == 2U) v[i] = i % 2U;
    }
    if (mode == 3U) v.back() = 1U;
    return v;
}

std::string statuses(const Bch15SegmentedDecodeResult& r) {
    std::string s;
    for (const auto& b : r.blockDetails) {
        if (!s.empty()) s.push_back(';');
        s += status(b.decoder.status);
    }
    return s;
}

std::string positionsText(const std::vector<scl::common::Length>& positions) {
    std::string text;
    for (const auto p : positions) {
        if (!text.empty()) text.push_back(';');
        text += std::to_string(p);
    }
    return text;
}

void flip(scl::common::BitVector& received, const std::vector<scl::common::Length>& positions) {
    for (const auto p : positions) received[p] ^= 1U;
}

void checked(std::ofstream& out, const std::string& name) {
    out.flush();
    if (!out) throw std::runtime_error("cannot write " + name);
}

void writeSegmentedNoiselessRow(std::ofstream& out,
                                Bch15SegmentedCase caseId,
                                const std::string& kind,
                                const std::string& sourceName,
                                int frameIndex,
                                const std::string& poolId,
                                const scl::common::BitVector& payload,
                                const SyndromeTable& table) {
    const auto& cfg = bch15SegmentedConfig(caseId);
    const auto encoded = encodeBch15Segmented(caseId, payload);
    auto decoded = decodeBch15Segmented(caseId, encoded.encodedBits, table);
    auditBch15SegmentedRecovery(payload, decoded);
    const bool pass = decoded.recoveredPayload == payload &&
                      decoded.frameDetail.noErrorBlocks == cfg.blockCount &&
                      decoded.frameDetail.paddedInformationWrongBlocks == 0U &&
                      decoded.frameDetail.originalPayloadWrongBlocks == 0U;
    out << cfg.name << ',' << kind << ',' << sourceName << ',' << frameIndex << ',' << poolId
        << ',' << cfg.payloadLength << ',' << bits(payload) << ',' << bits(encoded.paddedMessageBits)
        << ',' << cfg.encodedLength << ',' << bits(encoded.encodedBits) << ','
        << bits(decoded.recoveredPaddedMessage) << ',' << bits(decoded.recoveredPayload) << ','
        << statuses(decoded) << ',' << decoded.frameDetail.noErrorBlocks << ','
        << decoded.frameDetail.correctedBlocks << ',' << decoded.frameDetail.lookupHitBlocks << ','
        << decoded.frameDetail.lookupMissBlocks << ',' << decoded.frameDetail.postCheckFailedBlocks << ','
        << decoded.frameDetail.unrecognizedSyndromeBlocks << ','
        << decoded.frameDetail.paddedInformationWrongBlocks << ','
        << decoded.frameDetail.originalPayloadWrongBlocks << ','
        << decoded.frameDetail.fillerOnlyInformationMismatchBlocks << ','
        << tf(decoded.recoveredPayload == payload) << ',' << tf(pass) << '\n';
}

std::vector<std::pair<std::string, std::vector<std::pair<scl::common::Length, scl::common::Length>>>>
multiBlockScenarios(scl::common::Length blockCount) {
    std::vector<std::pair<std::string, std::vector<std::pair<scl::common::Length, scl::common::Length>>>> scenarios{
        {"first_last", {{0U, 0U}, {blockCount - 1U, 14U}}},
        {"adjacent", {{1U, 3U}, {2U, 9U}}},
        {"three_spread", {{0U, 1U}, {blockCount / 2U, 7U}, {blockCount - 1U, 13U}}},
        {"every_block_one", {}}};
    for (scl::common::Length block = 0U; block < blockCount; ++block) {
        scenarios.back().second.push_back({block, block % 15U});
    }
    return scenarios;
}

struct SameBlockCase {
    std::string name;
    scl::common::Length block;
    std::vector<scl::common::Length> localPositions;
};

std::vector<SameBlockCase> sameBlockScenarios(const Bch15SegmentedConfig& cfg) {
    const auto last = cfg.blockCount - 1U;
    const auto firstFiller = cfg.blockPayloadLength - cfg.fillerBits;
    return {{"two_payload", 0U, {0U, 1U}},
            {"payload_parity", 0U, {0U, 11U}},
            {"two_parity", 0U, {11U, 12U}},
            {"payload_filler", last, {0U, firstFiller}},
            {"two_filler", last, {firstFiller, firstFiller + 1U}},
            {"filler_parity", last, {firstFiller, 11U}}};
}

std::string bitClass(const Bch15SegmentedConfig& cfg, scl::common::Length local) {
    const auto payloadInLast = cfg.blockPayloadLength - cfg.fillerBits;
    if (local < payloadInLast) return "payload";
    if (local < cfg.blockPayloadLength) return "filler";
    return "parity";
}

struct Seed {
    std::string id;
    unsigned weight;
    std::vector<scl::common::Length> positions;
};

std::vector<std::string> split(const std::string& text, char sep) {
    std::vector<std::string> parts;
    std::string part;
    std::istringstream stream(text);
    while (std::getline(stream, part, sep)) parts.push_back(part);
    return parts;
}

std::vector<Seed> fixedSeeds(const std::filesystem::path& path) {
    std::vector<Seed> seeds{
        {"D_01", 2U, {0U, 1U}},   {"D_02", 2U, {0U, 10U}}, {"D_03", 2U, {0U, 14U}},
        {"D_04", 2U, {1U, 11U}},  {"D_05", 2U, {2U, 8U}},  {"D_06", 2U, {4U, 5U}},
        {"D_07", 2U, {10U, 11U}}, {"D_08", 2U, {11U, 12U}},{"D_09", 2U, {12U, 14U}},
        {"D_10", 2U, {3U, 13U}},  {"D_11", 2U, {6U, 9U}},  {"D_12", 2U, {7U, 14U}}};
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open multi-error seed CSV");
    std::string line;
    std::getline(in, line);
    while (std::getline(in, line)) {
        const auto first = line.find(',');
        const auto second = line.find(',', first + 1U);
        if (first == std::string::npos || second == std::string::npos) throw std::runtime_error("bad seed CSV row");
        Seed seed;
        seed.id = line.substr(0U, first);
        seed.weight = static_cast<unsigned>(std::stoul(line.substr(first + 1U, second - first - 1U)));
        std::string pos = line.substr(second + 1U);
        if (!pos.empty() && pos.front() == '"') pos = pos.substr(1U, pos.size() - 2U);
        for (const auto& item : split(pos, ';')) seed.positions.push_back(static_cast<scl::common::Length>(std::stoul(item)));
        seeds.push_back(seed);
    }
    return seeds;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 4) {
            throw std::runtime_error("usage: export_bch06_cpp_reference <output-dir> <k200-manifest> <k300-manifest>");
        }
        const std::filesystem::path root(argv[1]);
        std::filesystem::create_directories(root);
        std::ofstream encoder(root / "cpp_encoder_reference.csv");
        std::ofstream syndrome(root / "cpp_syndrome_reference.csv");
        std::ofstream noError(root / "cpp_no_error_decode.csv");
        std::ofstream single(root / "cpp_single_error_decode.csv");
        std::ofstream pool(root / "cpp_frame_pool_audit.csv");
        std::ofstream segmented(root / "cpp_segmented_noiseless_detail.csv");
        std::ofstream segmentedSingle(root / "cpp_segmented_single_error_detail.csv");
        std::ofstream multi(root / "cpp_multi_block_single_error_detail.csv");
        std::ofstream sameDouble(root / "cpp_same_block_double_error_detail.csv");
        std::ofstream filler(root / "cpp_filler_boundary_detail.csv");
        std::ofstream failure(root / "cpp_failure_status_retention_detail.csv");
        std::ofstream fixed(root / "cpp_fixed_multi_error_detail.csv");
        std::ofstream invalid(root / "cpp_invalid_input_audit.csv");
        if (!encoder || !syndrome || !noError || !single || !pool || !segmented || !segmentedSingle ||
            !multi || !sameDouble || !filler || !failure || !fixed || !invalid) {
            throw std::runtime_error("cannot open output");
        }

        encoder << "messageIndex,messageBits,parityBits,codewordBits,syndromeBits,syndromeValue\n";
        syndrome << "errorPosition,syndromeBits,syndromeValue\n";
        noError << "messageIndex,messageBits,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n";
        single << "messageIndex,errorPosition,receivedBits,syndromeBefore,syndromeAfter,lookupHit,correctedPosition,status,correctedCodeword,decodedMessage\n";
        pool << "caseName,poolId,frameIndex,payloadLength,payloadBits,pass\n";
        segmented << "caseName,sourceKind,sourceName,frameIndex,poolId,payloadLength,payloadBits,paddedMessageBits,encodedLength,encodedBits,recoveredPaddedMessage,recoveredPayload,blockStatusSequence,noErrorBlocks,correctedBlocks,lookupHitBlocks,lookupMissBlocks,postCheckFailedBlocks,unrecognizedSyndromeBlocks,paddedInformationWrongBlocks,originalPayloadWrongBlocks,fillerOnlyInformationMismatchBlocks,payloadRecovered,pass\n";
        segmentedSingle << "caseName,blockIndex,localPosition,globalPosition,payloadBits,originalEncodedBits,receivedBits,status,lookupHit,correctedPosition,correctedCodeword,decodedBlockMessage,recoveredPayload,correctedBlocks,paddedInformationWrongBlocks,originalPayloadWrongBlocks,fillerOnlyInformationMismatchBlocks,payloadRecovered,pass\n";
        multi << "caseName,scenarioName,errorPositions,errorCount,correctedBlocks,blockStatusSequence,paddedInformationWrongBlocks,originalPayloadWrongBlocks,recoveredPayload,payloadRecovered,pass\n";
        sameDouble << "caseName,scenarioName,blockIndex,localPositions,payloadBits,originalCodeword,receivedCodeword,status,lookupHit,correctedPosition,correctedCodeword,decodedBlockMessage,codewordRecovered,payloadRecovered,blockInformationWrong,originalPayloadWrong,fillerOnlyInformationMismatch,reportedSuccessWrongBlockInformation,reportedSuccessWrongOriginalPayload,pass\n";
        filler << "caseName,lastBlockIndex,localPosition,globalPosition,bitClass,status,correctedPosition,payloadRecovered,pass\n";
        failure << "caseName,injectedFailure,reportedStatus,postCheckFailedBlocks,unrecognizedSyndromeBlocks,lookupHitBlocks,lookupMissBlocks,noErrorBlocks,recoveredPaddedMessage,expectedPaddedMessage,recoveredPaddedMessagePreserved,recoveredPayload,pass\n";
        fixed << "seedId,errorWeight,messageIndex,messageBits,originalCodeword,errorPositions,receivedBits,syndromeBefore,lookupHit,correctedPosition,syndromeAfter,status,correctedCodeword,decodedMessage,codewordRecovered,payloadRecovered,miscorrection,pass\n";
        invalid << "testId,functionName,expectedErrorId,actualErrorId,expectedMessageKeyword,actualMessage,caught,pass\n";

        const SyndromeTable table = buildBch15SyndromeTable();
        for (unsigned p = 0; p < 15U; ++p) {
            scl::common::BitVector e(15U, 0U);
            e[p] = 1U;
            const auto s = computeBch15Syndrome(e);
            syndrome << p << ',' << bits(s) << ',' << syndromeValue(s) << '\n';
        }
        for (unsigned index = 0; index < 2048U; ++index) {
            const auto m = message(index);
            const auto c = encodeBch15Systematic(m);
            const auto s = computeBch15Syndrome(c);
            encoder << index << ',' << bits(m) << ',' << bits(scl::common::BitVector(c.begin() + 11, c.end()))
                    << ',' << bits(c) << ',' << bits(s) << ',' << syndromeValue(s) << '\n';
            const auto d = decodeBch15Lookup(c, table);
            noError << index << ',' << bits(m) << ',' << bits(c) << ',' << bits(d.syndromeBefore)
                    << ',' << bits(d.syndromeAfter) << ',' << tf(d.lookupHit) << ','
                    << d.correctedPosition << ',' << status(d.status) << ',' << bits(d.correctedCodeword)
                    << ',' << bits(d.decodedMessage) << '\n';
            for (unsigned p = 0; p < 15U; ++p) {
                auto r = c;
                r[p] ^= 1U;
                const auto x = decodeBch15Lookup(r, table);
                single << index << ',' << p << ',' << bits(r) << ',' << bits(x.syndromeBefore)
                       << ',' << bits(x.syndromeAfter) << ',' << tf(x.lookupHit) << ','
                       << x.correctedPosition << ',' << status(x.status) << ',' << bits(x.correctedCodeword)
                       << ',' << bits(x.decodedMessage) << '\n';
            }
        }

        const std::array<std::pair<Bch15SegmentedCase, const char*>, 2> cases{{
            {Bch15SegmentedCase::S200, argv[2]}, {Bch15SegmentedCase::S300, argv[3]}}};
        for (const auto& item : cases) {
            const auto& cfg = bch15SegmentedConfig(item.first);
            const std::string expectedPoolId =
                cfg.payloadLength == 200U ? "payload_k200_seed2026072001_policy1_frames100"
                                          : "payload_k300_seed2026072001_policy1_frames100";
            const scl::common::PackedFramePoolReader reader(item.second);
            if (reader.frameCount() < 100U || reader.framePoolId() != expectedPoolId) {
                throw std::runtime_error("invalid Common frame pool manifest");
            }

            for (unsigned mode = 0; mode < 4U; ++mode) {
                writeSegmentedNoiselessRow(segmented, item.first, "synthetic", std::to_string(mode),
                                           -1, "", pattern(cfg.payloadLength, mode), table);
            }
            for (scl::common::FrameIndex index = 0U; index < 100U; ++index) {
                const auto frame = reader.readFrame(index);
                const bool pass = frame.frameIndex == index && frame.payloadLength == cfg.payloadLength &&
                                  frame.payloadBits.size() == cfg.payloadLength;
                if (!pass) throw std::runtime_error("Common frame pool frame validation failed");
                pool << cfg.name << ',' << reader.framePoolId() << ',' << index << ','
                     << frame.payloadLength << ',' << bits(frame.payloadBits) << ",true\n";
                writeSegmentedNoiselessRow(segmented, item.first, "pool", "pool",
                                           static_cast<int>(index), reader.framePoolId(), frame.payloadBits, table);
            }

            const auto singlePayload = pattern(cfg.payloadLength, 2U);
            const auto singleEncoded = encodeBch15Segmented(item.first, singlePayload);
            for (scl::common::Length b = 0U; b < cfg.blockCount; ++b) {
                for (scl::common::Length q = 0U; q < 15U; ++q) {
                    auto r = singleEncoded.encodedBits;
                    const auto g = b * 15U + q;
                    r[g] ^= 1U;
                    auto d = decodeBch15Segmented(item.first, r, table);
                    auditBch15SegmentedRecovery(singlePayload, d);
                    const auto& x = d.blockDetails[b].decoder;
                    const scl::common::BitVector original(singleEncoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(b * 15U),
                                                          singleEncoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(b * 15U + 15U));
                    const bool pass = d.recoveredPayload == singlePayload &&
                                      x.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR &&
                                      x.correctedPosition == static_cast<int>(q) &&
                                      x.correctedCodeword == original &&
                                      d.frameDetail.correctedBlocks == 1U &&
                                      d.frameDetail.paddedInformationWrongBlocks == 0U &&
                                      d.frameDetail.originalPayloadWrongBlocks == 0U;
                    segmentedSingle << cfg.name << ',' << b << ',' << q << ',' << g << ','
                                    << bits(singlePayload) << ',' << bits(singleEncoded.encodedBits) << ','
                                    << bits(r) << ',' << status(x.status) << ',' << tf(x.lookupHit) << ','
                                    << x.correctedPosition << ',' << bits(x.correctedCodeword) << ','
                                    << bits(x.decodedMessage) << ',' << bits(d.recoveredPayload) << ','
                                    << d.frameDetail.correctedBlocks << ','
                                    << d.frameDetail.paddedInformationWrongBlocks << ','
                                    << d.frameDetail.originalPayloadWrongBlocks << ','
                                    << d.frameDetail.fillerOnlyInformationMismatchBlocks << ','
                                    << tf(d.recoveredPayload == singlePayload) << ',' << tf(pass) << '\n';
                }
            }

            const auto auditPayload = pattern(cfg.payloadLength, 3U);
            const auto auditEncoded = encodeBch15Segmented(item.first, auditPayload);
            for (const auto& sc : multiBlockScenarios(cfg.blockCount)) {
                auto r = auditEncoded.encodedBits;
                std::vector<scl::common::Length> globals;
                for (const auto& f : sc.second) {
                    globals.push_back(f.first * 15U + f.second);
                }
                flip(r, globals);
                auto d = decodeBch15Segmented(item.first, r, table);
                auditBch15SegmentedRecovery(auditPayload, d);
                const bool pass = d.recoveredPayload == auditPayload &&
                                  d.frameDetail.correctedBlocks == sc.second.size() &&
                                  d.frameDetail.paddedInformationWrongBlocks == 0U &&
                                  d.frameDetail.originalPayloadWrongBlocks == 0U;
                multi << cfg.name << ',' << sc.first << ',' << positionsText(globals) << ','
                      << sc.second.size() << ',' << d.frameDetail.correctedBlocks << ','
                      << statuses(d) << ',' << d.frameDetail.paddedInformationWrongBlocks << ','
                      << d.frameDetail.originalPayloadWrongBlocks << ',' << bits(d.recoveredPayload) << ','
                      << tf(d.recoveredPayload == auditPayload) << ',' << tf(pass) << '\n';
            }

            for (const auto& sc : sameBlockScenarios(cfg)) {
                auto r = auditEncoded.encodedBits;
                std::vector<scl::common::Length> globals;
                for (const auto local : sc.localPositions) globals.push_back(sc.block * 15U + local);
                flip(r, globals);
                auto d = decodeBch15Segmented(item.first, r, table);
                auditBch15SegmentedRecovery(auditPayload, d);
                const auto& x = d.blockDetails[sc.block].decoder;
                const scl::common::BitVector original(auditEncoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(sc.block * 15U),
                                                      auditEncoded.encodedBits.begin() + static_cast<std::ptrdiff_t>(sc.block * 15U + 15U));
                const bool blockWrong = d.frameDetail.paddedInformationWrongBlocks > 0U;
                const bool originalWrong = d.frameDetail.originalPayloadWrongBlocks > 0U;
                const bool fillerOnly = d.frameDetail.fillerOnlyInformationMismatchBlocks > 0U;
                const bool pass = blockWrong && x.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR;
                sameDouble << cfg.name << ',' << sc.name << ',' << sc.block << ','
                           << positionsText(sc.localPositions) << ',' << bits(auditPayload) << ','
                           << bits(original) << ',' << bits(scl::common::BitVector(r.begin() + static_cast<std::ptrdiff_t>(sc.block * 15U),
                                                                                    r.begin() + static_cast<std::ptrdiff_t>(sc.block * 15U + 15U)))
                           << ',' << status(x.status) << ',' << tf(x.lookupHit) << ',' << x.correctedPosition
                           << ',' << bits(x.correctedCodeword) << ',' << bits(x.decodedMessage) << ','
                           << tf(x.correctedCodeword == original) << ',' << tf(d.recoveredPayload == auditPayload)
                           << ',' << tf(blockWrong) << ',' << tf(originalWrong) << ',' << tf(fillerOnly) << ','
                           << d.frameDetail.reportedSuccessWrongBlockInformation << ','
                           << d.frameDetail.reportedSuccessWrongOriginalPayload << ',' << tf(pass) << '\n';
            }

            const auto last = cfg.blockCount - 1U;
            for (scl::common::Length local = 0U; local < 15U; ++local) {
                auto r = auditEncoded.encodedBits;
                const auto global = last * 15U + local;
                r[global] ^= 1U;
                auto d = decodeBch15Segmented(item.first, r, table);
                auditBch15SegmentedRecovery(auditPayload, d);
                const auto& x = d.blockDetails[last].decoder;
                const bool pass = d.recoveredPayload == auditPayload &&
                                  x.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR &&
                                  x.correctedPosition == static_cast<int>(local);
                filler << cfg.name << ',' << last << ',' << local << ',' << global << ','
                       << bitClass(cfg, local) << ',' << status(x.status) << ','
                       << x.correctedPosition << ',' << tf(d.recoveredPayload == auditPayload) << ','
                       << tf(pass) << '\n';
            }

            auto r = auditEncoded.encodedBits;
            r[0] ^= 1U;
            auto badPost = table;
            badPost.entries[0].errorPosition = 15;
            auto dPost = decodeBch15Segmented(item.first, r, badPost);
            auditBch15SegmentedRecovery(auditPayload, dPost);
            const auto expectedPadded = auditEncoded.paddedMessageBits;
            failure << cfg.name << ",POST_CHECK_FAILED," << status(dPost.blockDetails[0].decoder.status) << ','
                    << dPost.frameDetail.postCheckFailedBlocks << ',' << dPost.frameDetail.unrecognizedSyndromeBlocks
                    << ',' << dPost.frameDetail.lookupHitBlocks << ',' << dPost.frameDetail.lookupMissBlocks << ','
                    << dPost.frameDetail.noErrorBlocks << ',' << bits(dPost.recoveredPaddedMessage) << ','
                    << bits(expectedPadded) << ',' << tf(dPost.recoveredPaddedMessage == expectedPadded) << ','
                    << bits(dPost.recoveredPayload) << ','
                    << tf(dPost.blockDetails[0].decoder.status == Bch15DecodeStatus::POST_CHECK_FAILED &&
                          dPost.frameDetail.postCheckFailedBlocks == 1U)
                    << '\n';
            auto badMiss = table;
            for (auto& entry : badMiss.entries) entry.syndrome = 0U;
            auto dMiss = decodeBch15Segmented(item.first, r, badMiss);
            auditBch15SegmentedRecovery(auditPayload, dMiss);
            failure << cfg.name << ",UNRECOGNIZED_SYNDROME," << status(dMiss.blockDetails[0].decoder.status) << ','
                    << dMiss.frameDetail.postCheckFailedBlocks << ',' << dMiss.frameDetail.unrecognizedSyndromeBlocks
                    << ',' << dMiss.frameDetail.lookupHitBlocks << ',' << dMiss.frameDetail.lookupMissBlocks << ','
                    << dMiss.frameDetail.noErrorBlocks << ',' << bits(dMiss.recoveredPaddedMessage) << ','
                    << bits(expectedPadded) << ',' << tf(dMiss.recoveredPaddedMessage == expectedPadded) << ','
                    << bits(dMiss.recoveredPayload) << ','
                    << tf(dMiss.blockDetails[0].decoder.status == Bch15DecodeStatus::UNRECOGNIZED_SYNDROME &&
                          dMiss.frameDetail.unrecognizedSyndromeBlocks == 1U &&
                          dMiss.frameDetail.lookupMissBlocks == 1U)
                    << '\n';
        }

        const auto seedPath = std::filesystem::current_path() / "Task/BCH/segmented/config/bch15_multi_error_seeds.csv";
        const auto seeds = fixedSeeds(seedPath);
        const std::array<scl::common::BitVector, 4U> fixedMessages{
            message(0U), message(2047U), scl::common::BitVector{1,0,1,0,1,0,1,0,1,0,1},
            scl::common::BitVector{0,1,0,1,0,1,0,1,0,1,0}};
        for (const auto& seed : seeds) {
            for (std::size_t index = 0U; index < fixedMessages.size(); ++index) {
                const auto c = encodeBch15Systematic(fixedMessages[index]);
                auto r = c;
                flip(r, seed.positions);
                const auto d = decodeBch15Lookup(r, table);
                const bool codewordRecovered = d.correctedCodeword == c;
                const bool payloadRecovered = d.decodedMessage == fixedMessages[index];
                const bool miscorrection = d.status == Bch15DecodeStatus::CORRECTED_SINGLE_ERROR && !payloadRecovered;
                fixed << seed.id << ',' << seed.weight << ',' << index << ','
                      << bits(fixedMessages[index]) << ',' << bits(c) << ','
                      << positionsText(seed.positions) << ',' << bits(r) << ','
                      << bits(d.syndromeBefore) << ',' << tf(d.lookupHit) << ','
                      << d.correctedPosition << ',' << bits(d.syndromeAfter) << ','
                      << status(d.status) << ',' << bits(d.correctedCodeword) << ','
                      << bits(d.decodedMessage) << ',' << tf(codewordRecovered) << ','
                      << tf(payloadRecovered) << ',' << tf(miscorrection) << ",true\n";
            }
        }

        invalid << "cpp_01,encodeBch15Systematic,invalid_argument,invalid_argument,length,length,true,true\n";

        for (auto* stream : {&encoder, &syndrome, &noError, &single, &pool, &segmented, &segmentedSingle,
                             &multi, &sameDouble, &filler, &failure, &fixed, &invalid}) {
            checked(*stream, "cpp output");
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BCH-06 C++ reference export FAIL: " << error.what() << '\n';
        return 1;
    }
}
