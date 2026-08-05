#include "s7/s7.hpp"

#include "common/sha256.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>

namespace s7 {
namespace {

using Clock = std::chrono::steady_clock;

double elapsedNs(const Clock::time_point begin, const Clock::time_point end) {
    return std::chrono::duration<double, std::nano>(end - begin).count();
}

std::uint64_t mix64(std::uint64_t value) {
    value += 0x9e3779b97f4a7c15ULL;
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
}

std::uint64_t nextXorShift64(std::uint64_t& state) {
    if (state == 0) state = 0x6a09e667f3bcc909ULL;
    state ^= state << 13U;
    state ^= state >> 7U;
    state ^= state << 17U;
    return state;
}

void deterministicShuffle(std::vector<std::size_t>& values, std::uint64_t seed) {
    if (seed == 0) seed = 0x6a09e667f3bcc909ULL;
    for (std::size_t i = values.size(); i > 1; --i) {
        const std::size_t j = static_cast<std::size_t>(nextXorShift64(seed) % i);
        std::swap(values[i - 1], values[j]);
    }
}

std::string mappingHash(const std::vector<std::size_t>& values) {
    std::ostringstream text;
    for (std::size_t value : values) text << value << ',';
    return scl::common::sha256Hex(text.str());
}

void finalizeMapping(Mapping& result) {
    result.inputToOutput.assign(result.outputToInput.size(), 0);
    for (std::size_t out = 0; out < result.outputToInput.size(); ++out) {
        const std::size_t in = result.outputToInput[out];
        if (in >= result.outputToInput.size()) throw std::invalid_argument("mapping index out of range");
        result.inputToOutput[in] = out;
    }
    result.sha256 = mappingHash(result.outputToInput);
    validateMapping(result, result.outputToInput.size());
}

std::vector<std::size_t> rowColumnIndices(std::size_t length, std::size_t rows) {
    if (rows == 0 || rows > length) throw std::invalid_argument("rows must be in [1,length]");
    const std::size_t columns = (length + rows - 1) / rows;
    std::vector<std::size_t> indices;
    indices.reserve(length);
    for (std::size_t column = 0; column < columns; ++column)
        for (std::size_t row = 0; row < rows; ++row) {
            const std::size_t index = row * columns + column;
            if (index < length) indices.push_back(index);
        }
    return indices;
}

template <typename T>
std::vector<T> applyForward(const std::vector<T>& input, const Mapping& mapping) {
    if (input.size() != mapping.outputToInput.size()) throw std::invalid_argument("interleave length mismatch");
    std::vector<T> output(input.size());
    for (std::size_t i = 0; i < output.size(); ++i) output[i] = input[mapping.outputToInput[i]];
    return output;
}

template <typename T>
std::vector<T> applyInverse(const std::vector<T>& input, const Mapping& mapping) {
    if (input.size() != mapping.outputToInput.size()) throw std::invalid_argument("deinterleave length mismatch");
    std::vector<T> output(input.size());
    for (std::size_t i = 0; i < input.size(); ++i) output[mapping.outputToInput[i]] = input[i];
    return output;
}

std::vector<std::size_t> ccStepMapping(CcInterleaver method, std::size_t parameter,
                                       std::uint64_t seed) {
    std::vector<std::size_t> steps(kCcTrellisSteps);
    std::iota(steps.begin(), steps.end(), 0);
    if (method == CcInterleaver::None) return steps;
    if (method == CcInterleaver::ShortDepthBlock) {
        if (parameter != 4 && parameter != 8 && parameter != 16)
            throw std::invalid_argument("CC block depth must be 4, 8, or 16");
        const std::size_t window = parameter * 8;
        std::vector<std::size_t> output;
        output.reserve(steps.size());
        for (std::size_t base = 0; base < steps.size(); base += window) {
            const std::size_t count = std::min(window, steps.size() - base);
            const auto local = rowColumnIndices(count, std::min(parameter, count));
            for (std::size_t value : local) output.push_back(base + value);
        }
        return output;
    }
    if (parameter != 32 && parameter != 64 && parameter != 128)
        throw std::invalid_argument("CC pseudorandom span must be 32, 64, or 128 trellis steps");
    std::vector<std::size_t> output;
    output.reserve(steps.size());
    for (std::size_t base = 0; base < steps.size(); base += parameter) {
        const std::size_t count = std::min(parameter, steps.size() - base);
        std::vector<std::size_t> local(count);
        std::iota(local.begin(), local.end(), 0);
        deterministicShuffle(local, seed ^ static_cast<std::uint64_t>(base) ^ static_cast<std::uint64_t>(count));
        for (std::size_t value : local) output.push_back(base + value);
    }
    return output;
}

}  // namespace

Mapping makeBchMapping(const BchInterleaver method, const std::size_t parameter,
                       const std::uint64_t seed) {
    Mapping result;
    result.permutationUnit = "BIT";
    if (method == BchInterleaver::None) {
        result.method = "NONE";
        result.outputToInput.resize(kBchEncodedBits);
        std::iota(result.outputToInput.begin(), result.outputToInput.end(), 0);
        result.spanBits = 1; result.bufferBits = 0; result.fairnessGroupId = "IDENTITY";
    } else if (method == BchInterleaver::Codeblock) {
        if (parameter != 4 && parameter != 8 && parameter != 16 && parameter != 19)
            throw std::invalid_argument("BCH codeblock depth must be 4, 8, 16, or 19");
        result.method = "BCH_CODEBLOCK"; result.rows = parameter; result.columns = 15;
        result.spanBits = std::min(parameter, kBchBlockCount) * 15;
        result.bufferBits = result.spanBits;
        result.fairnessGroupId = result.spanBits == kBchEncodedBits ? "FULL_FRAME_285" :
            "LOCAL_SPAN_" + std::to_string(result.spanBits);
        for (std::size_t blockBase = 0; blockBase < kBchBlockCount; blockBase += parameter) {
            const std::size_t rows = std::min(parameter, kBchBlockCount - blockBase);
            for (std::size_t column = 0; column < 15; ++column)
                for (std::size_t row = 0; row < rows; ++row)
                    result.outputToInput.push_back((blockBase + row) * 15 + column);
        }
    } else if (method == BchInterleaver::RowColumn) {
        if (parameter != 4 && parameter != 8 && parameter != 15 && parameter != 19)
            throw std::invalid_argument("BCH row-column rows must be 4, 8, 15, or 19");
        result.method = "ROW_COLUMN"; result.rows = parameter;
        result.columns = (kBchEncodedBits + parameter - 1) / parameter;
        result.spanBits = kBchEncodedBits; result.bufferBits = kBchEncodedBits;
        result.fairnessGroupId = "FULL_FRAME_285";
        result.outputToInput = rowColumnIndices(kBchEncodedBits, parameter);
    } else {
        if (parameter != 0 && parameter != kBchEncodedBits)
            throw std::invalid_argument("global pseudorandom BCH span is fixed to 285 bits");
        result.method = "GLOBAL_PSEUDORANDOM"; result.spanBits = kBchEncodedBits;
        result.bufferBits = kBchEncodedBits; result.fairnessGroupId = "FULL_FRAME_285";
        result.outputToInput.resize(kBchEncodedBits);
        std::iota(result.outputToInput.begin(), result.outputToInput.end(), 0);
        deterministicShuffle(result.outputToInput, seed);
    }
    finalizeMapping(result);
    return result;
}

Mapping makeCcMapping(const CcInterleaver method, const std::size_t parameter,
                      const std::uint64_t seed) {
    Mapping result;
    result.permutationUnit = "TRELLIS_STEP";
    result.preserveMotherOutputPair = true;
    result.method = method == CcInterleaver::None ? "NONE" :
                    method == CcInterleaver::ShortDepthBlock ? "SHORT_DEPTH_BLOCK" : "PSEUDORANDOM";
    const auto steps = ccStepMapping(method, parameter, seed);
    result.outputToInput.reserve(kCcEncodedBits);
    for (std::size_t step : steps) {
        result.outputToInput.push_back(2 * step);
        result.outputToInput.push_back(2 * step + 1);
    }
    result.spanTrellisSteps = method == CcInterleaver::None ? 1 :
                              method == CcInterleaver::ShortDepthBlock ? parameter * 8 : parameter;
    result.spanBits = 2 * result.spanTrellisSteps;
    result.bufferBits = method == CcInterleaver::None ? 0 : result.spanBits;
    result.rows = method == CcInterleaver::ShortDepthBlock ? parameter : 0;
    result.columns = method == CcInterleaver::ShortDepthBlock ? 8 : 0;
    result.fairnessGroupId = method == CcInterleaver::None ? "IDENTITY" :
        "TRELLIS_SPAN_" + std::to_string(result.spanTrellisSteps);
    finalizeMapping(result);
    return result;
}

void validateMapping(const Mapping& mapping, const std::size_t expectedLength) {
    if (mapping.outputToInput.size() != expectedLength || mapping.inputToOutput.size() != expectedLength)
        throw std::invalid_argument("mapping length mismatch");
    std::vector<bool> seen(expectedLength, false);
    for (std::size_t out = 0; out < expectedLength; ++out) {
        const std::size_t in = mapping.outputToInput[out];
        if (in >= expectedLength || seen[in]) throw std::invalid_argument("mapping is not a permutation");
        seen[in] = true;
        if (mapping.inputToOutput[in] != out) throw std::invalid_argument("mapping inverse mismatch");
    }
    if (mapping.preserveMotherOutputPair) {
        for (std::size_t out = 0; out < expectedLength; out += 2) {
            if (mapping.outputToInput[out] % 2 != 0 || mapping.outputToInput[out + 1] != mapping.outputToInput[out] + 1)
                throw std::invalid_argument("mother-code output pair was split");
        }
    }
}

std::vector<std::uint8_t> interleaveBits(const std::vector<std::uint8_t>& input, const Mapping& mapping) { return applyForward(input, mapping); }
std::vector<std::uint8_t> deinterleaveBits(const std::vector<std::uint8_t>& input, const Mapping& mapping) { return applyInverse(input, mapping); }
std::vector<double> interleaveValues(const std::vector<double>& input, const Mapping& mapping) { return applyForward(input, mapping); }
std::vector<double> deinterleaveValues(const std::vector<double>& input, const Mapping& mapping) { return applyInverse(input, mapping); }

std::string burstPositionName(const BurstPosition position) {
    switch (position) {
        case BurstPosition::Head: return "HEAD"; case BurstPosition::Quarter: return "QUARTER";
        case BurstPosition::Middle: return "MIDDLE"; case BurstPosition::ThreeQuarter: return "THREE_QUARTER";
        case BurstPosition::Tail: return "TAIL"; case BurstPosition::Random: return "RANDOM";
    }
    throw std::invalid_argument("unknown burst position");
}

BurstSpec makeBurstSpec(const std::size_t encodedLength, const double ratio,
                        const BurstPosition position, const std::uint64_t frameIndex,
                        const std::uint64_t seed) {
    if (encodedLength == 0 || !std::isfinite(ratio) || ratio < 0.0 || ratio > 1.0)
        throw std::invalid_argument("invalid burst length or ratio");
    BurstSpec result;
    result.ratioRequested = ratio;
    result.lengthBits = static_cast<std::size_t>(std::llround(ratio * encodedLength));
    if (result.lengthBits > encodedLength) result.lengthBits = encodedLength;
    const std::size_t available = encodedLength - result.lengthBits;
    result.position = position;
    switch (position) {
        case BurstPosition::Head: result.start = 0; break;
        case BurstPosition::Quarter: result.start = static_cast<std::size_t>(std::llround(available / 4.0)); break;
        case BurstPosition::Middle: result.start = static_cast<std::size_t>(std::llround(available / 2.0)); break;
        case BurstPosition::ThreeQuarter: result.start = static_cast<std::size_t>(std::llround(3.0 * available / 4.0)); break;
        case BurstPosition::Tail: result.start = available; break;
        case BurstPosition::Random: result.start = available == 0 ? 0 : mix64(seed ^ frameIndex) % (available + 1); break;
    }
    result.end = result.start + result.lengthBits;
    return result;
}

double sigmaSquaredFromEsN0(const double esN0Db) {
    if (!std::isfinite(esN0Db)) throw std::invalid_argument("Es/N0 must be finite");
    return 1.0 / (2.0 * std::pow(10.0, esN0Db / 10.0));
}

std::vector<double> bpskModulate(const std::vector<std::uint8_t>& bits) {
    std::vector<double> symbols(bits.size());
    for (std::size_t i = 0; i < bits.size(); ++i) {
        if (bits[i] > 1) throw std::invalid_argument("non-binary input");
        symbols[i] = bits[i] == 0 ? 1.0 : -1.0;
    }
    return symbols;
}

std::vector<double> applyPolarityReversalAwgn(const std::vector<double>& symbols,
                                               const std::vector<double>& standardNoise,
                                               const double sigmaSquared,
                                               const BurstSpec& burst) {
    if (symbols.size() != standardNoise.size() || burst.end > symbols.size() || burst.start > burst.end ||
        !std::isfinite(sigmaSquared) || sigmaSquared < 0.0 || burst.wrapAround)
        throw std::invalid_argument("invalid polarity-reversal channel input");
    std::vector<double> received(symbols.size());
    const double sigma = std::sqrt(sigmaSquared);
    for (std::size_t i = 0; i < symbols.size(); ++i) {
        const double h = i >= burst.start && i < burst.end ? -1.0 : 1.0;
        received[i] = h * symbols[i] + sigma * standardNoise[i];
    }
    return received;
}

std::vector<std::uint8_t> hardDecision(const std::vector<double>& received) {
    std::vector<std::uint8_t> bits(received.size());
    for (std::size_t i = 0; i < received.size(); ++i) {
        if (!std::isfinite(received[i])) throw std::invalid_argument("non-finite received symbol");
        bits[i] = received[i] >= 0.0 ? 0 : 1;
    }
    return bits;
}

std::vector<double> llrFromReceived(const std::vector<double>& received, const double sigmaSquared) {
    if (!std::isfinite(sigmaSquared) || sigmaSquared < 0.0) throw std::invalid_argument("invalid noise variance");
    std::vector<double> llr(received.size());
    for (std::size_t i = 0; i < received.size(); ++i) {
        if (!std::isfinite(received[i])) throw std::invalid_argument("non-finite received symbol");
        llr[i] = sigmaSquared == 0.0 ? (received[i] >= 0.0 ? 200.0 : -200.0) : 2.0 * received[i] / sigmaSquared;
    }
    return llr;
}

std::vector<std::uint8_t> deterministicPayload(const std::size_t length,
                                               const std::uint64_t frameIndex,
                                               const std::uint64_t seed) {
    std::vector<std::uint8_t> bits(length);
    std::uint64_t state = mix64(seed ^ frameIndex);
    for (std::size_t i = 0; i < length; ++i) { if ((i & 63U) == 0U) state = mix64(state ^ i); bits[i] = (state >> (i & 63U)) & 1U; }
    return bits;
}

std::vector<double> deterministicStandardNoise(const std::size_t length,
                                               const std::uint64_t frameIndex,
                                               const std::uint64_t seed) {
    std::mt19937_64 engine(mix64(seed ^ frameIndex));
    std::normal_distribution<double> normal(0.0, 1.0);
    std::vector<double> noise(length);
    for (double& value : noise) value = normal(engine);
    return noise;
}

std::size_t bitErrors(const std::vector<std::uint8_t>& a, const std::vector<std::uint8_t>& b) {
    if (a.size() != b.size()) throw std::invalid_argument("bit error length mismatch");
    std::size_t errors = 0; for (std::size_t i = 0; i < a.size(); ++i) errors += a[i] != b[i]; return errors;
}

BchCodecContext::BchCodecContext()
    : syndromeTable(scl::bch::segmented::buildBch15SyndromeTable()) {}

BchFrameResult runBchFrame(const BchCodecContext& context,
                           const std::vector<std::uint8_t>& payload, const Mapping& mapping,
                           const std::vector<double>& standardNoise, const double sigmaSquared,
                           const BurstSpec& burst) {
    if (payload.size() != kBchPayloadBits) throw std::invalid_argument("BCH payload length mismatch");
    const auto encoded = scl::bch::segmented::encodeBch15Segmented(scl::bch::segmented::Bch15SegmentedCase::S200, payload);
    BchFrameResult result; result.encodedBits = encoded.encodedBits;
    const auto interleaveBegin = Clock::now();
    const auto transmittedBits = interleaveBits(result.encodedBits, mapping);
    result.timing.interleaveTimeNs = elapsedNs(interleaveBegin, Clock::now());
    const auto received = applyPolarityReversalAwgn(bpskModulate(transmittedBits), standardNoise, sigmaSquared, burst);
    const auto hard = hardDecision(received);
    const auto deinterleaveBegin = Clock::now();
    const auto decoderBits = deinterleaveBits(hard, mapping);
    result.timing.deinterleaveTimeNs = elapsedNs(deinterleaveBegin, Clock::now());
    for (std::size_t block = 0; block < kBchBlockCount; ++block) {
        std::size_t count = 0;
        for (std::size_t bit = 0; bit < 15; ++bit) count += decoderBits[block * 15 + bit] != result.encodedBits[block * 15 + bit];
        result.affectedBlocks += count != 0; result.maximumErrorsInBlock = std::max(result.maximumErrorsInBlock, count);
    }
    const auto decodeBegin = Clock::now();
    auto decoded = scl::bch::segmented::decodeBch15Segmented(
        scl::bch::segmented::Bch15SegmentedCase::S200, decoderBits, context.syndromeTable);
    scl::bch::segmented::auditBch15SegmentedRecovery(payload, decoded);
    result.correctedBlocks = decoded.frameDetail.correctedBlocks;
    result.lookupMissBlocks = decoded.frameDetail.lookupMissBlocks;
    result.postCheckFailedBlocks = decoded.frameDetail.postCheckFailedBlocks;
    result.miscorrectedBlocks = decoded.frameDetail.miscorrectedBlocks;
    result.decoderDetectedFailure = result.lookupMissBlocks != 0 || result.postCheckFailedBlocks != 0;
    result.decodedPayload = std::move(decoded.recoveredPayload);
    result.timing.decodeTimeNs = elapsedNs(decodeBegin, Clock::now());
    result.bitErrors = bitErrors(payload, result.decodedPayload);
    result.undetectedFrameError = result.bitErrors != 0 && !result.decoderDetectedFailure;
    return result;
}

BchFrameResult runBchFrame(const std::vector<std::uint8_t>& payload, const Mapping& mapping,
                           const std::vector<double>& standardNoise, const double sigmaSquared,
                           const BurstSpec& burst) {
    static const BchCodecContext context;
    return runBchFrame(context, payload, mapping, standardNoise, sigmaSquared, burst);
}

CcFrameResult runCcFrame(const std::vector<std::uint8_t>& payload, const Mapping& mapping,
                         const std::vector<double>& standardNoise, const double sigmaSquared,
                         const BurstSpec& burst) {
    if (payload.size() != kCcPayloadBits) throw std::invalid_argument("CC payload length mismatch");
    scl::cc::Trellis trellis; scl::cc::ConvolutionalEncoder encoder(trellis); scl::cc::SoftViterbiDecoder decoder(trellis);
    const auto encoded = encoder.encode_block(payload, true, 0);
    CcFrameResult result; result.encodedBits = encoded.mother_bits;
    const auto interleaveBegin = Clock::now();
    const auto transmittedBits = interleaveBits(result.encodedBits, mapping);
    result.timing.interleaveTimeNs = elapsedNs(interleaveBegin, Clock::now());
    const auto received = applyPolarityReversalAwgn(bpskModulate(transmittedBits), standardNoise, sigmaSquared, burst);
    const auto llr = llrFromReceived(received, sigmaSquared);
    const auto deinterleaveBegin = Clock::now();
    const auto decoderLlr = deinterleaveValues(llr, mapping);
    result.timing.deinterleaveTimeNs = elapsedNs(deinterleaveBegin, Clock::now());
    std::vector<double> softSymbols(decoderLlr.size());
    const double scale = sigmaSquared == 0.0 ? 0.005 : 0.5;
    std::transform(decoderLlr.begin(), decoderLlr.end(), softSymbols.begin(), [scale](double value) { return value * scale; });
    const auto decodeBegin = Clock::now();
    const auto decoded = decoder.decode_terminated_symbols(softSymbols, kCcTrellisSteps, 6, 0, 0);
    result.timing.decodeTimeNs = elapsedNs(decodeBegin, Clock::now());
    result.decodedPayload = decoded.payload_bits; result.tieCount = decoded.tie_count;
    result.tracebackFinalState = decoded.traceback_final_state; result.bitErrors = bitErrors(payload, result.decodedPayload);
    return result;
}

}  // namespace s7
