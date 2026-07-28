#include "stage13_burst_interleaving_validation_simulation.hpp"

#include "stage01_foundation_awgn.hpp"
#include "bch_block/bch_block.hpp"
#include "bch_segmented/bch15_lookup_table.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace scl::bch::s2::stage13 {
namespace {

using stage02::CaseContract;
using stage02::CaseId;
using stage02::Organization;

struct AuditedDecode {
    common::BitVector payload;
    bool reportedSuccess = false;
    bool allNoError = false;
};

std::uint64_t mix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
}

block::BlockBchProfile makeProfile(const CaseContract& contract,
                                   std::size_t blockIndex) {
    block::BlockBchProfile profile;
    if (contract.motherN == 255U) profile = block::makeB200Profile();
    else if (contract.motherK == 421U) profile = block::makeB300Profile();
    else if (contract.motherK == 385U) profile = block::makeB300426Profile();
    else throw std::invalid_argument("unsupported whole-block mother profile");
    profile.caseName =
        contract.caseId + "_STAGE13_BLOCK_" + std::to_string(blockIndex);
    profile.payloadLength = contract.payloadPerBlock.at(blockIndex);
    profile.shorteningLength = contract.shorteningPerBlock.at(blockIndex);
    block::validateProfile(profile);
    return profile;
}

const std::vector<block::BlockBchProfile>& profiles(CaseId id) {
    using C = CaseId;
    static const auto a = [] {
        const auto& c = stage02::caseContract(C::K200_M255K207);
        return std::vector<block::BlockBchProfile>{makeProfile(c, 0U)};
    }();
    static const auto b = [] {
        const auto& c = stage02::caseContract(C::K200_M511K421);
        return std::vector<block::BlockBchProfile>{makeProfile(c, 0U)};
    }();
    static const auto c = [] {
        const auto& v = stage02::caseContract(C::K200_M511K385);
        return std::vector<block::BlockBchProfile>{makeProfile(v, 0U)};
    }();
    static const auto d = [] {
        const auto& c = stage02::caseContract(C::K300_M255K207);
        return std::vector<block::BlockBchProfile>{
            makeProfile(c, 0U), makeProfile(c, 1U)};
    }();
    static const auto e = [] {
        const auto& c = stage02::caseContract(C::K300_M511K421);
        return std::vector<block::BlockBchProfile>{makeProfile(c, 0U)};
    }();
    static const auto f = [] {
        const auto& c = stage02::caseContract(C::K300_M511K385);
        return std::vector<block::BlockBchProfile>{makeProfile(c, 0U)};
    }();
    switch (id) {
        case C::K200_M255K207: return a;
        case C::K200_M511K421: return b;
        case C::K200_M511K385: return c;
        case C::K300_M255K207: return d;
        case C::K300_M511K421: return e;
        case C::K300_M511K385: return f;
        default:
            throw std::invalid_argument("segmented case has no block profiles");
    }
}

const segmented::SyndromeTable& syndromeTable() {
    static const auto table = segmented::buildBch15SyndromeTable();
    return table;
}

AuditedDecode decodeAudited(const CaseContract& contract,
                            const common::BitVector& received) {
    AuditedDecode result;
    std::size_t failed = 0U;
    std::size_t noError = 0U;
    if (contract.organization == Organization::Segmented15) {
        const auto id = contract.payloadLength == 200U
            ? segmented::Bch15SegmentedCase::S200
            : segmented::Bch15SegmentedCase::S300;
        const auto decoded =
            segmented::decodeBch15Segmented(id, received, syndromeTable());
        result.payload = decoded.recoveredPayload;
        for (const auto& blockDetail : decoded.blockDetails) {
            using S = segmented::Bch15DecodeStatus;
            if (blockDetail.decoder.status == S::NO_ERROR) ++noError;
            else if (blockDetail.decoder.status != S::CORRECTED_SINGLE_ERROR) {
                ++failed;
            }
        }
    } else {
        const auto& cached = profiles(contract.id);
        std::size_t encodedOffset = 0U;
        for (std::size_t blockIndex = 0U;
             blockIndex < contract.blockCount; ++blockIndex) {
            const std::size_t count =
                contract.encodedLengthPerBlock[blockIndex];
            const common::BitVector blockReceived(
                received.begin() +
                    static_cast<std::ptrdiff_t>(encodedOffset),
                received.begin() +
                    static_cast<std::ptrdiff_t>(encodedOffset + count));
            const auto decoded =
                block::decodeShortenedNoThrow(cached[blockIndex], blockReceived);
            using S = block::DecodeStatus;
            if (decoded.status == S::NoError) ++noError;
            else if (decoded.status != S::Corrected) ++failed;
            result.payload.insert(result.payload.end(),
                                  decoded.payload.begin(), decoded.payload.end());
            encodedOffset += count;
        }
    }
    result.reportedSuccess = failed == 0U;
    result.allNoError = noError == contract.blockCount;
    return result;
}

std::uint64_t hashBits(const common::BitVector& bits) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const auto bit : bits) {
        hash ^= static_cast<std::uint64_t>(bit);
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::uint64_t hashNoise(const std::vector<double>& values) {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const double value : values) {
        std::uint64_t word = 0U;
        std::memcpy(&word, &value, sizeof(word));
        for (unsigned byte = 0U; byte < 8U; ++byte) {
            hash ^= (word >> (byte * 8U)) & 0xffU;
            hash *= 1099511628211ULL;
        }
    }
    return hash;
}

InterleaverSpec interleaverSpec(const SimulationPoint& point,
                                const CaseContract& contract) {
    return {
        point.mode,
        point.mode == InterleaverMode::None ? 1U : point.depth,
        point.mode == InterleaverMode::Pseudorandom
            ? point.interleaverSeed : 0U,
        contract.caseId};
}

}  // namespace

std::uint64_t bitErrors(const common::BitVector& left,
                        const common::BitVector& right) {
    if (left.size() != right.size()) {
        throw std::invalid_argument("payload comparison length mismatch");
    }
    std::uint64_t count = 0U;
    for (std::size_t index = 0U; index < left.size(); ++index) {
        count += left[index] != right[index] ? 1U : 0U;
    }
    return count;
}

FrameTrace simulateFrame(const SimulationPoint& point,
                         std::uint64_t masterSeed,
                         std::uint64_t frameIndex,
                         const std::vector<std::size_t>& permutation) {
    const auto& contract = stage02::caseContract(point.caseId);
    stage02::validateCaseContract(contract);
    validatePermutation(permutation);
    if (permutation.size() != contract.totalEncodedLength) {
        throw std::invalid_argument("simulation permutation length mismatch");
    }
    if (point.burstLength > contract.totalEncodedLength) {
        throw std::invalid_argument("simulation burst length exceeds frame");
    }

    const stage01::RandomIdentity payloadIdentity{
        masterSeed, "bch_s2_burst_payload", contract.caseId,
        point.snrIndex, frameIndex};
    const auto payloadSource =
        stage01::payloadFrame(payloadIdentity, contract.payloadLength);
    FrameTrace trace;
    trace.payload.assign(payloadSource.begin(), payloadSource.end());
    trace.encoded =
        stage02::encodeFrame(contract.id, trace.payload).encodedBits;
    trace.interleaved = applyPermutation(trace.encoded, permutation);
    trace.channelBitsBeforeBurst = trace.interleaved;

    if (point.awgnEnabled) {
        const double derivedEbN0Db =
            point.targetSnrDb - 10.0 * std::log10(contract.actualRate);
        const double sigma = std::sqrt(
            stage01::awgnSigma2(contract.actualRate, derivedEbN0Db));
        const stage01::RandomIdentity awgnIdentity{
            masterSeed, "bch_s2_burst_awgn", contract.caseId,
            point.snrIndex, frameIndex};
        const auto noise = stage01::standardGaussianFrame(
            awgnIdentity, stage01::RandomDomain::Awgn,
            trace.interleaved.size());
        for (std::size_t index = 0U;
             index < trace.channelBitsBeforeBurst.size(); ++index) {
            const double received =
                stage01::bpsk(trace.interleaved[index]) +
                sigma * noise[index];
            trace.channelBitsBeforeBurst[index] =
                static_cast<common::Bit>(stage01::hardDecision(received));
        }
    }

    const BurstIdentity burstIdentity{
        masterSeed, "bch_s2_burst_shared", contract.caseId,
        0U, point.snrIndex, point.burstLengthIndex, frameIndex};
    trace.burstStart = burstStart(
        burstIdentity, contract.totalEncodedLength, point.burstLength);
    trace.channelBitsAfterBurst = flipContiguousBits(
        trace.channelBitsBeforeBurst, trace.burstStart, point.burstLength);
    trace.deinterleaved =
        removePermutation(trace.channelBitsAfterBurst, permutation);
    const auto decoded = decodeAudited(contract, trace.deinterleaved);
    trace.recoveredPayload = decoded.payload;
    trace.decoderDeclaredSuccess = decoded.reportedSuccess;
    trace.decoderAllNoError = decoded.allNoError;
    return trace;
}

SimulationCounters simulateRange(const SimulationPoint& point,
                                 std::uint64_t masterSeed,
                                 std::uint64_t frameStart,
                                 std::uint64_t frameCount,
                                 bool collectTiming) {
    const auto& contract = stage02::caseContract(point.caseId);
    const auto permutation =
        makePermutation(contract.totalEncodedLength,
                        interleaverSpec(point, contract));
    SimulationCounters result;
    if (collectTiming) {
        result.decoderTimesNs.reserve(static_cast<std::size_t>(frameCount));
        result.interleaverTimesNs.reserve(static_cast<std::size_t>(frameCount));
        result.deinterleaverTimesNs.reserve(
            static_cast<std::size_t>(frameCount));
    }
    for (std::uint64_t frameIndex = frameStart;
         frameIndex < frameStart + frameCount; ++frameIndex) {
        const stage01::RandomIdentity payloadIdentity{
            masterSeed, "bch_s2_burst_payload", contract.caseId,
            point.snrIndex, frameIndex};
        const auto payloadSource =
            stage01::payloadFrame(payloadIdentity, contract.payloadLength);
        const common::BitVector payload(
            payloadSource.begin(), payloadSource.end());
        const auto encodedFrame =
            stage02::encodeFrame(contract.id, payload);
        const auto& encoded = encodedFrame.encodedBits;

        const auto interleaverStart = std::chrono::steady_clock::now();
        auto channel = applyPermutation(encoded, permutation);
        const auto interleaverEnd = std::chrono::steady_clock::now();

        std::vector<double> noise;
        if (point.awgnEnabled) {
            const double derivedEbN0Db =
                point.targetSnrDb - 10.0 * std::log10(contract.actualRate);
            const double sigma = std::sqrt(
                stage01::awgnSigma2(contract.actualRate, derivedEbN0Db));
            const stage01::RandomIdentity awgnIdentity{
                masterSeed, "bch_s2_burst_awgn", contract.caseId,
                point.snrIndex, frameIndex};
            noise = stage01::standardGaussianFrame(
                awgnIdentity, stage01::RandomDomain::Awgn, channel.size());
            for (std::size_t index = 0U; index < channel.size(); ++index) {
                channel[index] = static_cast<common::Bit>(
                    stage01::hardDecision(
                        stage01::bpsk(channel[index]) +
                        sigma * noise[index]));
            }
        }

        const BurstIdentity burstIdentity{
            masterSeed, "bch_s2_burst_shared", contract.caseId,
            0U, point.snrIndex, point.burstLengthIndex, frameIndex};
        const std::size_t start =
            burstStart(burstIdentity, channel.size(), point.burstLength);
        channel = flipContiguousBits(channel, start, point.burstLength);
        const auto affected = affectedBlocks(
            encodedFrame.blockOffsets, permutation, start, point.burstLength);

        const auto deinterleaverStart = std::chrono::steady_clock::now();
        const auto deinterleaved = removePermutation(channel, permutation);
        const auto deinterleaverEnd = std::chrono::steady_clock::now();
        const auto decoderStart = std::chrono::steady_clock::now();
        const auto decoded = decodeAudited(contract, deinterleaved);
        const auto decoderEnd = std::chrono::steady_clock::now();

        const std::uint64_t errors = bitErrors(payload, decoded.payload);
        const bool trueSuccess = errors == 0U;
        ++result.framesProcessed;
        result.payloadBitsProcessed += contract.payloadLength;
        result.payloadErrorBits += errors;
        result.payloadErrorFrames += trueSuccess ? 0U : 1U;
        result.decoderDeclaredSuccessFrames +=
            decoded.reportedSuccess ? 1U : 0U;
        result.decoderDeclaredFailureFrames +=
            decoded.reportedSuccess ? 0U : 1U;
        result.trueSuccessFrames += trueSuccess ? 1U : 0U;
        result.miscorrectionFrames +=
            decoded.reportedSuccess && !trueSuccess ? 1U : 0U;
        result.undetectedErrorFrames +=
            decoded.allNoError && !trueSuccess ? 1U : 0U;
        result.affectedCodeBlocksTotal += affected.affectedCount;
        result.maxAffectedCodeBlocks = std::max<std::uint64_t>(
            result.maxAffectedCodeBlocks, affected.affectedCount);
        result.maxErrorsInOneCodeBlockObserved =
            std::max<std::uint64_t>(
                result.maxErrorsInOneCodeBlockObserved,
                affected.maxErrorsInOneBlock);
        result.sumMaxErrorsInOneCodeBlock += affected.maxErrorsInOneBlock;
        result.burstStartChecksum +=
            mix64(static_cast<std::uint64_t>(start) ^ frameIndex);
        result.payloadChecksum += hashBits(payload);
        if (point.awgnEnabled) result.awgnChecksum += hashNoise(noise);

        if (collectTiming) {
            const auto interleaverNs = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    interleaverEnd - interleaverStart).count());
            const auto deinterleaverNs = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    deinterleaverEnd - deinterleaverStart).count());
            const auto decoderNs = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    decoderEnd - decoderStart).count());
            result.interleaverApplyTimeTotalNs += interleaverNs;
            result.deinterleaverApplyTimeTotalNs += deinterleaverNs;
            result.decoderTimeTotalNs += decoderNs;
            result.interleaverTimesNs.push_back(interleaverNs);
            result.deinterleaverTimesNs.push_back(deinterleaverNs);
            result.decoderTimesNs.push_back(decoderNs);
        }
    }
    return result;
}

void addCounters(SimulationCounters& target,
                 const SimulationCounters& source,
                 bool includeTiming) {
    target.framesProcessed += source.framesProcessed;
    target.payloadBitsProcessed += source.payloadBitsProcessed;
    target.payloadErrorBits += source.payloadErrorBits;
    target.payloadErrorFrames += source.payloadErrorFrames;
    target.decoderDeclaredSuccessFrames +=
        source.decoderDeclaredSuccessFrames;
    target.decoderDeclaredFailureFrames +=
        source.decoderDeclaredFailureFrames;
    target.trueSuccessFrames += source.trueSuccessFrames;
    target.miscorrectionFrames += source.miscorrectionFrames;
    target.undetectedErrorFrames += source.undetectedErrorFrames;
    target.affectedCodeBlocksTotal += source.affectedCodeBlocksTotal;
    target.maxAffectedCodeBlocks =
        std::max(target.maxAffectedCodeBlocks, source.maxAffectedCodeBlocks);
    target.maxErrorsInOneCodeBlockObserved =
        std::max(target.maxErrorsInOneCodeBlockObserved,
                 source.maxErrorsInOneCodeBlockObserved);
    target.sumMaxErrorsInOneCodeBlock +=
        source.sumMaxErrorsInOneCodeBlock;
    target.burstStartChecksum += source.burstStartChecksum;
    target.payloadChecksum += source.payloadChecksum;
    target.awgnChecksum += source.awgnChecksum;
    if (includeTiming) {
        target.interleaverApplyTimeTotalNs +=
            source.interleaverApplyTimeTotalNs;
        target.deinterleaverApplyTimeTotalNs +=
            source.deinterleaverApplyTimeTotalNs;
        target.decoderTimeTotalNs += source.decoderTimeTotalNs;
        target.decoderTimesNs.insert(target.decoderTimesNs.end(),
            source.decoderTimesNs.begin(), source.decoderTimesNs.end());
        target.interleaverTimesNs.insert(target.interleaverTimesNs.end(),
            source.interleaverTimesNs.begin(),
            source.interleaverTimesNs.end());
        target.deinterleaverTimesNs.insert(
            target.deinterleaverTimesNs.end(),
            source.deinterleaverTimesNs.begin(),
            source.deinterleaverTimesNs.end());
    }
}

bool sameDeterministicCounters(const SimulationCounters& a,
                               const SimulationCounters& b) {
    return a.framesProcessed == b.framesProcessed &&
        a.payloadBitsProcessed == b.payloadBitsProcessed &&
        a.payloadErrorBits == b.payloadErrorBits &&
        a.payloadErrorFrames == b.payloadErrorFrames &&
        a.decoderDeclaredSuccessFrames == b.decoderDeclaredSuccessFrames &&
        a.decoderDeclaredFailureFrames == b.decoderDeclaredFailureFrames &&
        a.trueSuccessFrames == b.trueSuccessFrames &&
        a.miscorrectionFrames == b.miscorrectionFrames &&
        a.undetectedErrorFrames == b.undetectedErrorFrames &&
        a.affectedCodeBlocksTotal == b.affectedCodeBlocksTotal &&
        a.maxAffectedCodeBlocks == b.maxAffectedCodeBlocks &&
        a.maxErrorsInOneCodeBlockObserved ==
            b.maxErrorsInOneCodeBlockObserved &&
        a.sumMaxErrorsInOneCodeBlock ==
            b.sumMaxErrorsInOneCodeBlock &&
        a.burstStartChecksum == b.burstStartChecksum &&
        a.payloadChecksum == b.payloadChecksum &&
        a.awgnChecksum == b.awgnChecksum;
}

std::uint64_t percentile(std::vector<std::uint64_t> values,
                         double probability) {
    if (values.empty()) return 0U;
    if (!std::isfinite(probability) ||
        probability <= 0.0 || probability > 1.0) {
        throw std::invalid_argument("percentile probability outside (0,1]");
    }
    std::sort(values.begin(), values.end());
    const auto index = static_cast<std::size_t>(
        std::ceil(probability * values.size()) - 1.0);
    return values[std::min(index, values.size() - 1U)];
}

}  // namespace scl::bch::s2::stage13
