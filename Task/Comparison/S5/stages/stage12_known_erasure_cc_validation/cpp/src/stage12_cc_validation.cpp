#include "s5_comparison/s5.hpp"

#include "cc/puncturing.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr std::uint64_t kCppPayloadSeed = 2026080301ULL;
constexpr std::uint64_t kCppNoiseSeed = 2026080302ULL;
constexpr std::uint64_t kNoiseGroup = 0x533531324157474eULL;
constexpr std::uint64_t kStateGroup = 0x5335535441544501ULL;
constexpr std::uint64_t kBlockageTag = 0x424c4f434bULL;
constexpr const char* kConfigHash = "stage12_known_erasure_cc_validation_v2_17x27";
const scl::cc::PuncturePattern kR23{"R23_1101", {1, 1, 0, 1}};

struct ChannelData {
    std::vector<double> before;
    std::vector<double> after;
    std::vector<double> received;
    std::vector<double> llr;
    std::vector<std::uint8_t> mask;
    std::size_t start = 0;
    std::size_t length = 0;
    double sigmaSquared = 0.0;
};

struct DecodeAudit {
    std::vector<std::uint8_t> payload;
    std::vector<std::uint8_t> codecInput;
    std::vector<std::uint8_t> statePath;
};

struct Counts {
    std::uint64_t frames = 0;
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
};

std::vector<std::uint8_t> payload(std::uint64_t frame) {
    const auto bits = scl::common::generatePayloadBits(kCppPayloadSeed, 300, frame);
    return {bits.begin(), bits.end()};
}

double uniformStart(std::uint64_t frame) {
    std::uint64_t value = s5::kNoiseSeed ^ kStateGroup ^ kBlockageTag;
    value ^= frame * 0x9e3779b97f4a7c15ULL;
    const auto word = scl::common::splitmix64(value);
    return (static_cast<double>(word >> 11U) + 0.5) / 9007199254740992.0;
}

std::size_t erasureStart(std::uint64_t frame, std::size_t n, std::size_t length) {
    return static_cast<std::size_t>(std::floor(uniformStart(frame) * static_cast<double>(n - length + 1)));
}

double normal(std::uint64_t frame, std::size_t symbol) {
    return scl::common::standardGaussianSample(
        {kCppNoiseSeed, kNoiseGroup, frame, 2ULL * symbol, 2ULL});
}

std::vector<std::uint8_t> encode(s5::CodecContext& ctx, s5::Scheme scheme,
                                 const std::vector<std::uint8_t>& data,
                                 std::vector<std::uint8_t>* mother = nullptr,
                                 std::vector<std::uint8_t>* codecInput = nullptr) {
    const auto coded = ctx.ccEncoder.encode_block(data, true, 0);
    if (mother) *mother = coded.mother_bits;
    if (codecInput) *codecInput = coded.codec_input_bits;
    if (scheme == s5::Scheme::CcR12) return coded.mother_bits;
    return scl::cc::puncture_bits(coded.mother_bits, kR23).bits;
}

ChannelData channel(const std::vector<std::uint8_t>& tx, double fraction,
                    double esN0Db, std::uint64_t frame, bool addNoise) {
    ChannelData result;
    const std::size_t n = tx.size();
    result.before.resize(n);
    result.after.resize(n);
    result.received.resize(n);
    result.llr.resize(n);
    result.mask.assign(n, 1);
    for (std::size_t i = 0; i < n; ++i) result.before[i] = tx[i] ? -1.0 : 1.0;
    result.after = result.before;
    result.length = static_cast<std::size_t>(std::llround(fraction * static_cast<double>(n)));
    result.start = result.length == 0 ? 0 : erasureStart(frame, n, result.length);
    for (std::size_t i = 0; i < result.length; ++i) {
        result.mask[result.start + i] = 0;
        result.after[result.start + i] = 0.0;
    }
    result.sigmaSquared = addNoise ? s5::sigmaSquaredFromEsN0(esN0Db) : 0.0;
    const double sigma = std::sqrt(result.sigmaSquared);
    for (std::size_t i = 0; i < n; ++i) {
        result.received[i] = result.after[i] + (addNoise ? sigma * normal(frame, i) : 0.0);
        if (result.mask[i] == 0) result.llr[i] = 0.0;
        else if (!addNoise) result.llr[i] = result.received[i] > 0 ? 100.0 : -100.0;
        else result.llr[i] = 2.0 * result.received[i] / result.sigmaSquared;
    }
    return result;
}

DecodeAudit decodeAudit(const scl::cc::Trellis& trellis, const std::vector<double>& expanded,
                        const std::vector<std::uint8_t>& observed) {
    constexpr std::size_t steps = 306;
    struct Survivor { std::uint8_t predecessor = 0; std::uint8_t input = 0; bool valid = false; };
    const double inf = std::numeric_limits<double>::infinity();
    std::array<double, 64> metric{}, next{};
    metric.fill(inf); metric[0] = 0.0;
    std::vector<Survivor> survivors(steps * 64);
    for (std::size_t t = 0; t < steps; ++t) {
        next.fill(inf);
        for (std::size_t state = 0; state < 64; ++state) {
            if (!std::isfinite(metric[state])) continue;
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(static_cast<std::uint8_t>(state), input);
                double candidate = metric[state];
                for (std::size_t j = 0; j < 2; ++j) if (observed[2 * t + j]) {
                    const double expected = branch.output_bits[j] ? -1.0 : 1.0;
                    const double d = expanded[2 * t + j] - expected;
                    candidate += d * d;
                }
                auto& survivor = survivors[t * 64 + branch.next_state];
                const bool better = !survivor.valid || candidate < next[branch.next_state]
                    || (candidate == next[branch.next_state]
                        && (state < survivor.predecessor
                            || (state == survivor.predecessor && input < survivor.input)));
                if (better) {
                    next[branch.next_state] = candidate;
                    survivor = {static_cast<std::uint8_t>(state), input, true};
                }
            }
        }
        const double minimum = *std::min_element(next.begin(), next.end());
        for (double& value : next) if (std::isfinite(value)) value -= minimum;
        metric = next;
    }
    DecodeAudit result;
    result.codecInput.resize(steps);
    result.statePath.resize(steps + 1);
    std::uint8_t state = 0;
    result.statePath[steps] = state;
    for (std::size_t time = steps; time > 0; --time) {
        const auto& s = survivors[(time - 1) * 64 + state];
        if (!s.valid) throw std::runtime_error("invalid Stage12 traceback");
        result.codecInput[time - 1] = s.input;
        state = s.predecessor;
        result.statePath[time - 1] = state;
    }
    result.payload.assign(result.codecInput.begin(), result.codecInput.begin() + 300);
    return result;
}

DecodeAudit decode(s5::CodecContext& ctx, s5::Scheme scheme, const std::vector<double>& llr) {
    std::vector<double> symbols(llr.size());
    std::transform(llr.begin(), llr.end(), symbols.begin(), [](double x) { return 0.5 * x; });
    if (scheme == s5::Scheme::CcR12) {
        std::vector<std::uint8_t> mask(612, 1);
        const auto audit = decodeAudit(ctx.ccTrellis, symbols, mask);
        const auto production = ctx.ccDecoder.decode_terminated_symbols(symbols, 306, 6, 0, 0);
        if (production.payload_bits != audit.payload) throw std::runtime_error("R12 audit/production decode mismatch");
        return audit;
    }
    const auto dep = scl::cc::depuncture_soft(symbols, 612, kR23);
    const auto audit = decodeAudit(ctx.ccTrellis, dep.expanded_values, dep.observed_mask);
    const auto production = ctx.ccDecoder.decode_terminated_masked_symbols(
        dep.expanded_values, dep.observed_mask, 306, 6, 0, 0);
    if (production.payload_bits != audit.payload) throw std::runtime_error("R23 audit/production decode mismatch");
    return audit;
}

std::size_t errors(const std::vector<std::uint8_t>& a, const std::vector<std::uint8_t>& b) {
    return s5::bitErrors(a, b);
}

void writeBits(const fs::path& path, const std::string& name, const std::vector<std::uint8_t>& bits) {
    std::ofstream out(path); out << "index," << name << "\n";
    for (std::size_t i = 0; i < bits.size(); ++i) out << i << ',' << static_cast<int>(bits[i]) << '\n';
}

void writeValues(const fs::path& path, const std::string& name, const std::vector<double>& values) {
    std::ofstream out(path); out << std::setprecision(17) << "index," << name << "\n";
    for (std::size_t i = 0; i < values.size(); ++i) out << i << ',' << values[i] << '\n';
}

void writeTrace(const fs::path& root, s5::CodecContext& ctx, s5::Scheme scheme,
                std::uint64_t frame, double fraction, double snr, bool addNoise) {
    const std::string schemeName = scheme == s5::Scheme::CcR23 ? "CC_R23" : "CC_R12";
    std::ostringstream label;
    label << schemeName << "__frame_" << frame << "__erasure_" << static_cast<int>(100 * fraction)
          << "__" << (addNoise ? ("snr_" + std::to_string(static_cast<int>(snr))) : "no_awgn");
    const fs::path dir = root / label.str(); fs::create_directories(dir);
    const auto data = payload(frame);
    std::vector<std::uint8_t> mother, codecInput;
    const auto tx = encode(ctx, scheme, data, &mother, &codecInput);
    const auto ch = channel(tx, fraction, snr, frame, addNoise);
    const auto decoded = decode(ctx, scheme, ch.llr);
    std::vector<std::uint8_t> errorMask(300);
    for (std::size_t i = 0; i < 300; ++i) errorMask[i] = data[i] != decoded.payload[i];
    writeBits(dir / "payload_bits.csv", "payloadBit", data);
    writeBits(dir / "encoder_input_with_tail.csv", "codecInputBit", codecInput);
    writeBits(dir / "mother_code_bits.csv", "motherBit", mother);
    writeBits(dir / "punctured_tx_bits.csv", "txBit", tx);
    writeValues(dir / "bpsk_symbols.csv", "symbol", ch.before);
    writeBits(dir / "erasure_mask.csv", "knownMask", ch.mask);
    writeValues(dir / "symbols_before_erasure.csv", "symbol", ch.before);
    writeValues(dir / "symbols_after_erasure.csv", "symbol", ch.after);
    writeValues(dir / "received_symbols.csv", "symbol", ch.received);
    writeValues(dir / "channel_soft_metric.csv", "llr", ch.llr);
    std::vector<double> symbols(ch.llr.size());
    std::transform(ch.llr.begin(), ch.llr.end(), symbols.begin(), [](double x) { return 0.5 * x; });
    if (scheme == s5::Scheme::CcR23) symbols = scl::cc::depuncture_soft(symbols, 612, kR23).expanded_values;
    writeValues(dir / "depunctured_soft_metric.csv", "softSymbol", symbols);
    writeBits(dir / "decoded_payload.csv", "decodedBit", decoded.payload);
    writeBits(dir / "bit_error_mask.csv", "bitError", errorMask);
    writeBits(dir / "traceback_state_path.csv", "state", decoded.statePath);
    std::size_t first = 300, last = 300, bitErrors = 0;
    for (std::size_t i = 0; i < 300; ++i) if (errorMask[i]) { first = std::min(first, i); last = i; ++bitErrors; }
    std::size_t affectedFirst = 300, affectedLast = 0;
    if (ch.length > 0) {
        std::vector<std::size_t> txToMother;
        if (scheme == s5::Scheme::CcR12) {
            txToMother.resize(612);
            for (std::size_t i = 0; i < 612; ++i) txToMother[i] = i;
        } else {
            for (std::size_t i = 0; i < 612; ++i) if (kR23.keep_mask[i % 4]) txToMother.push_back(i);
        }
        affectedFirst = txToMother[ch.start] / 2;
        affectedLast = txToMother[ch.start + ch.length - 1] / 2;
        affectedFirst = std::min<std::size_t>(affectedFirst, 299);
        affectedLast = std::min<std::size_t>(affectedLast, 299);
    }
    std::size_t errorsBefore = 0, errorsInside = 0, errorsAfter = 0;
    for (std::size_t i = 0; i < 300; ++i) if (errorMask[i]) {
        if (ch.length == 0 || i < affectedFirst) ++errorsBefore;
        else if (i <= affectedLast) ++errorsInside;
        else ++errorsAfter;
    }
    std::ofstream summary(dir / "trace_summary.json");
    summary << "{\n  \"scheme\": \"" << schemeName << "\",\n  \"frameIndex\": " << frame
            << ",\n  \"esN0Db\": " << (addNoise ? std::to_string(snr) : "null")
            << ",\n  \"erasureFraction\": " << fraction << ",\n  \"erasureStart\": " << ch.start
            << ",\n  \"erasureLength\": " << ch.length << ",\n  \"payloadBitErrors\": " << bitErrors
            << ",\n  \"frameError\": " << (bitErrors ? "true" : "false")
            << ",\n  \"firstPayloadErrorIndex\": " << (bitErrors ? std::to_string(first) : "null")
            << ",\n  \"lastPayloadErrorIndex\": " << (bitErrors ? std::to_string(last) : "null")
            << ",\n  \"payloadErrorSpan\": " << (bitErrors ? last - first + 1 : 0)
            << ",\n  \"affectedPayloadStart\": " << (ch.length ? std::to_string(affectedFirst) : "null")
            << ",\n  \"affectedPayloadEnd\": " << (ch.length ? std::to_string(affectedLast) : "null")
            << ",\n  \"errorsBeforeAffectedRegion\": " << errorsBefore
            << ",\n  \"errorsInsideAffectedRegion\": " << errorsInside
            << ",\n  \"errorsAfterAffectedRegion\": " << errorsAfter << "\n}\n";
}

std::pair<double, double> wilson(std::uint64_t errorsCount, std::uint64_t n) {
    const double z = 1.959963984540054;
    const double p = static_cast<double>(errorsCount) / static_cast<double>(n);
    const double den = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / den;
    const double half = z * std::sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / den;
    return {center - half, center + half};
}

Counts simulate(s5::CodecContext& ctx, s5::Scheme scheme, double fraction, double snr,
                bool interleave, std::uint64_t maxFrames) {
    Counts count;
    for (std::uint64_t frame = 0; frame < maxFrames; ++frame) {
        const auto data = payload(frame + (interleave ? 1000000ULL : 0ULL));
        auto tx = encode(ctx, scheme, data);
        if (interleave) {
            if (tx.size() != 459) throw std::runtime_error("17x27 interleaver requires exactly 459 symbols");
            std::vector<std::uint8_t> permuted(459);
            for (std::size_t r = 0; r < 17; ++r) for (std::size_t c = 0; c < 27; ++c)
                permuted[c * 17 + r] = tx[r * 27 + c];
            tx.swap(permuted);
        }
        auto ch = channel(tx, fraction, snr, frame + (interleave ? 1000000ULL : 0ULL), true);
        if (interleave) {
            std::vector<double> restored(459);
            for (std::size_t r = 0; r < 17; ++r) for (std::size_t c = 0; c < 27; ++c)
                restored[r * 27 + c] = ch.llr[c * 17 + r];
            ch.llr.swap(restored);
        }
        const auto decoded = decode(ctx, scheme, ch.llr);
        const auto bitError = errors(data, decoded.payload);
        ++count.frames; count.bitErrors += bitError; count.frameErrors += bitError != 0;
        if (count.frames >= 1000 && count.frameErrors >= 200) break;
    }
    return count;
}

void fixedVectors(const fs::path& output, s5::CodecContext& ctx) {
    const fs::path fixed = output / "cpp" / "results"; fs::create_directories(fixed);
    const auto data = payload(0);
    std::vector<std::uint8_t> mother;
    const auto tx = encode(ctx, s5::Scheme::CcR23, data, &mother, nullptr);
    writeBits(fixed / "fixed_payload.csv", "payloadBit", data);
    writeBits(fixed / "fixed_mother_code_bits.csv", "motherBit", mother);
    writeBits(fixed / "fixed_punctured_tx_bits.csv", "txBit", tx);
    const auto noNoise = channel(tx, 0.0, 0.0, 0, false);
    const auto decoded = decode(ctx, s5::Scheme::CcR23, noNoise.llr);
    writeBits(fixed / "fixed_noiseless_decoded_payload.csv", "decodedBit", decoded.payload);
    if (decoded.payload != data) throw std::runtime_error("fixed noiseless payload mismatch");
}

void traces(const fs::path& output, s5::CodecContext& ctx) {
    const std::size_t len = static_cast<std::size_t>(std::llround(0.05 * 459.0));
    const auto s0 = erasureStart(0, 459, len), s1 = erasureStart(1, 459, len);
    const std::uint64_t second = std::max(s0, s1) - std::min(s0, s1) < len ? 31 : 1;
    std::ofstream audit(output / "cpp" / "results" / "trace_frame_selection.csv");
    audit << "candidateFrame,start,selected,reason\n0," << s0 << ",true,anchor\n1," << s1 << ','
          << (second == 1 ? "true" : "false") << ",distance_check\n31," << erasureStart(31,459,len) << ','
          << (second == 31 ? "true" : "false") << ",representative_fallback\n";
    const fs::path traceRoot = output / "cpp" / "traces";
    for (auto frame : {0ULL, second}) for (double fraction : {0.0, 0.05}) {
        writeTrace(traceRoot, ctx, s5::Scheme::CcR23, frame, fraction, 0.0, false);
        writeTrace(traceRoot, ctx, s5::Scheme::CcR23, frame, fraction, 4.0, true);
        writeTrace(traceRoot, ctx, s5::Scheme::CcR23, frame, fraction, 8.0, true);
    }
    for (double fraction : {0.0, 0.05}) {
        writeTrace(traceRoot, ctx, s5::Scheme::CcR12, 0, fraction, 0.0, false);
        writeTrace(traceRoot, ctx, s5::Scheme::CcR12, 0, fraction, 4.0, true);
        writeTrace(traceRoot, ctx, s5::Scheme::CcR12, 0, fraction, 8.0, true);
    }
}

void scan(const fs::path& output, s5::CodecContext& ctx) {
    std::ofstream out(output / "cpp" / "results" / "cpp_erasure_fraction_summary.csv");
    out << "scheme,erasureFraction,esN0Db,processedFrames,payloadBitErrors,frameErrors,BER,FER,ferWilsonLow,ferWilsonHigh,stopReason,configHash\n";
    out << std::setprecision(17);
    for (double fraction : {0.0, 0.01, 0.02, 0.03, 0.05}) for (double snr : {0.0, 4.0, 8.0, 10.0}) {
        const auto c = simulate(ctx, s5::Scheme::CcR23, fraction, snr, false, 10000);
        const auto ci = wilson(c.frameErrors, c.frames);
        out << "CC_R23," << fraction << ',' << snr << ',' << c.frames << ',' << c.bitErrors << ',' << c.frameErrors
            << ',' << static_cast<double>(c.bitErrors)/(300.0*c.frames) << ',' << static_cast<double>(c.frameErrors)/c.frames
            << ',' << ci.first << ',' << ci.second << ',' << (c.frameErrors >= 200 ? "TARGET_FRAME_ERRORS" : "MAX_FRAMES")
            << ',' << kConfigHash << '\n';
        std::cout << "scan R23 f=" << fraction << " snr=" << snr << " frames=" << c.frames << " fe=" << c.frameErrors << std::endl;
    }
    for (double snr : {4.0, 8.0, 10.0}) {
        const auto c = simulate(ctx, s5::Scheme::CcR12, 0.05, snr, false, 10000);
        const auto ci = wilson(c.frameErrors, c.frames);
        out << "CC_R12,0.05," << snr << ',' << c.frames << ',' << c.bitErrors << ',' << c.frameErrors
            << ',' << static_cast<double>(c.bitErrors)/(300.0*c.frames) << ',' << static_cast<double>(c.frameErrors)/c.frames
            << ',' << ci.first << ',' << ci.second << ',' << (c.frameErrors >= 200 ? "TARGET_FRAME_ERRORS" : "MAX_FRAMES")
            << ',' << kConfigHash << '\n';
    }
}

void interleaver(const fs::path& output, s5::CodecContext& ctx) {
    std::ofstream out(output / "cpp" / "results" / "interleaver_diagnostic_summary.csv");
    out << "scheme,erasureFraction,esN0Db,interleaver,rows,columns,processedFrames,payloadBitErrors,frameErrors,BER,FER,status\n";
    out << std::setprecision(17);
    const auto data = payload(9000000);
    auto tx = encode(ctx, s5::Scheme::CcR23, data);
    std::vector<std::uint8_t> permuted(459), restored(459);
    for (std::size_t r=0;r<17;++r) for(std::size_t c=0;c<27;++c) permuted[c*17+r]=tx[r*27+c];
    for (std::size_t r=0;r<17;++r) for(std::size_t c=0;c<27;++c) restored[r*27+c]=permuted[c*17+r];
    if (restored != tx) throw std::runtime_error("17x27 interleaver roundtrip mismatch");
    for (double snr : {4.0, 8.0, 10.0}) for (bool enabled : {false, true}) {
        const auto c = simulate(ctx, s5::Scheme::CcR23, 0.05, snr, enabled, 5000);
        out << "CC_R23,0.05," << snr << ',' << (enabled ? "BLOCK_17X27" : "NONE") << ",17,27,"
            << c.frames << ',' << c.bitErrors << ',' << c.frameErrors << ','
            << static_cast<double>(c.bitErrors)/(300.0*c.frames) << ',' << static_cast<double>(c.frameErrors)/c.frames
            << ",diagnostic_only\n";
    }
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) { std::cerr << "usage: s5_stage12_cc_validation OUTPUT_DIR\n"; return 2; }
        const fs::path output = fs::absolute(argv[1]);
        fs::create_directories(output / "cpp" / "results");
        fs::create_directories(output / "cpp" / "traces");
        s5::CodecContext ctx;
        fixedVectors(output, ctx);
        traces(output, ctx);
        scan(output, ctx);
        interleaver(output, ctx);
        std::cout << "PASS_STAGE12_CPP_EXECUTION\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "BLOCKED_STAGE12_CPP_EXECUTION: " << e.what() << '\n';
        return 1;
    }
}
