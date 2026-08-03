#include "s5_comparison/s5.hpp"

#include <algorithm>
#include <chrono>
#include <cctype>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kFnvOffset = 1469598103934665603ULL;
constexpr std::uint64_t kFnvPrime = 1099511628211ULL;
volatile std::uint64_t gDecodeSink = 0;

struct TimingSeries {
    std::vector<double> impairment;
    std::vector<double> awgn;
    std::vector<double> equalization;
    std::vector<double> projection;
    std::vector<double> llr;
    std::vector<double> channel;
    std::vector<double> decode;
    std::vector<double> receiver;
};

struct Accumulator {
    std::uint64_t frames = 0;
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
    std::uint64_t decoderFailures = 0;
    std::uint64_t undetectedPayloadErrorFrames = 0;
    std::uint64_t successfulDecodedFrames = 0;
    std::uint64_t iterations = 0;
    std::uint64_t maxIterationFrames = 0;
    std::uint64_t payloadSequenceHash = kFnvOffset;
    std::uint64_t codewordSequenceHash = kFnvOffset;
    std::uint64_t channelSequenceHash = kFnvOffset;
    std::uint64_t decoderSequenceHash = kFnvOffset;
    std::vector<double> iterationSamples;
    TimingSeries timing;
};

struct FrameAudit {
    std::uint64_t payloadHash = 0;
    std::uint64_t codewordHash = 0;
    std::uint64_t llrHash = 0;
    std::uint64_t decodedHash = 0;
    std::size_t errors = 0;
    double decodeUs = 0.0;
    s5::ChannelTrace trace;
    s5::DecodeOutcome decoded;
};

std::vector<s5::Channel> fixedChannels() {
    return {s5::Channel::Awgn, s5::Channel::Multipath, s5::Channel::Cfo,
            s5::Channel::Doppler, s5::Channel::Blockage10, s5::Channel::Burst};
}

std::vector<s5::Channel> formalChannels() {
    return {s5::Channel::Awgn, s5::Channel::Multipath, s5::Channel::Cfo,
            s5::Channel::Doppler, s5::Channel::Blockage5, s5::Channel::Burst};
}

s5::Channel parseChannel(const std::string& name) {
    for (const auto channel : {s5::Channel::Awgn, s5::Channel::Multipath, s5::Channel::Cfo,
                               s5::Channel::Doppler, s5::Channel::Blockage10,
                               s5::Channel::Blockage5, s5::Channel::Burst}) {
        if (s5::channelName(channel) == name) return channel;
    }
    throw std::invalid_argument("unknown channel name: " + name);
}

std::vector<std::size_t> groupPair(const std::string& group) {
    if (group == "RATE_NEAR_2_3") return {0, 2};
    if (group == "RATE_NEAR_1_2") return {1, 3};
    throw std::invalid_argument("unknown comparison group: " + group);
}

void ensureOutput(const std::filesystem::path& output) {
    std::filesystem::create_directories(output);
}

std::uint64_t hashBytes(const std::vector<std::uint8_t>& values) {
    std::uint64_t hash = kFnvOffset;
    for (const auto value : values) {
        hash ^= value;
        hash *= kFnvPrime;
    }
    return hash;
}

std::uint64_t hashDoubles(const std::vector<double>& values) {
    std::uint64_t hash = kFnvOffset;
    for (const auto value : values) {
        std::uint64_t bits = 0;
        std::memcpy(&bits, &value, sizeof(bits));
        for (int byte = 0; byte < 8; ++byte) {
            hash ^= (bits >> (8 * byte)) & 0xffU;
            hash *= kFnvPrime;
        }
    }
    return hash;
}

void mix(std::uint64_t& hash, std::uint64_t value) {
    for (int byte = 0; byte < 8; ++byte) {
        hash ^= (value >> (8 * byte)) & 0xffU;
        hash *= kFnvPrime;
    }
}

std::string hex64(std::uint64_t value) {
    std::ostringstream stream;
    stream << std::hex << std::setw(16) << std::setfill('0') << value;
    return stream.str();
}

double mean(const std::vector<double>& values) {
    double total = 0.0;
    for (const auto value : values) total += value;
    return values.empty() ? 0.0 : total / static_cast<double>(values.size());
}

double median(const std::vector<double>& input) {
    if (input.empty()) return 0.0;
    auto values = input;
    std::sort(values.begin(), values.end());
    const auto n = values.size();
    if (n % 2 != 0) return values[n / 2];
    return 0.5 * (values[n / 2 - 1] + values[n / 2]);
}

double p95(const std::vector<double>& input) {
    if (input.empty()) return 0.0;
    auto values = input;
    std::sort(values.begin(), values.end());
    const auto index = static_cast<std::size_t>(std::ceil(0.95 * values.size())) - 1U;
    return values[index];
}

double maximum(const std::vector<double>& values) {
    return values.empty() ? 0.0 : *std::max_element(values.begin(), values.end());
}

std::pair<double, double> wilson(std::uint64_t errors, std::uint64_t trials) {
    if (trials == 0) return {0.0, 0.0};
    constexpr double z = 1.959963984540054;
    const double n = static_cast<double>(trials);
    const double p = static_cast<double>(errors) / n;
    const double denominator = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / denominator;
    const double half = z * std::sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator;
    return {std::max(0.0, center - half), std::min(1.0, center + half)};
}

FrameAudit evaluateFrame(s5::CodecContext& context,
                         const s5::SchemeSpec& scheme,
                         s5::Channel channel,
                         double snr,
                         std::uint64_t frame) {
    FrameAudit audit;
    const auto payload = s5::payloadForFrame(frame);
    const auto codeword = s5::encodeFrame(context, scheme.scheme, payload);
    audit.trace = s5::runChannel(channel, codeword, snr, frame, true, true);
    const auto before = Clock::now();
    audit.decoded = s5::decodeFrame(context, scheme.scheme, audit.trace.llr);
    const auto after = Clock::now();
    audit.decodeUs = std::chrono::duration<double, std::micro>(after - before).count();
    audit.errors = s5::bitErrors(payload, audit.decoded.payload);
    audit.payloadHash = hashBytes(payload);
    audit.codewordHash = hashBytes(codeword);
    audit.llrHash = hashDoubles(audit.trace.llr);
    audit.decodedHash = hashBytes(audit.decoded.payload);
    gDecodeSink ^= audit.decodedHash ^ static_cast<std::uint64_t>(audit.decoded.usedIterations);
    return audit;
}

void recordFrame(const s5::SchemeSpec& scheme, const FrameAudit& frame, Accumulator& acc) {
    ++acc.frames;
    acc.bitErrors += frame.errors;
    acc.frameErrors += frame.errors != 0;
    acc.decoderFailures += frame.decoded.decoderFailure;
    if (frame.errors != 0 && !frame.decoded.decoderFailure
        && scheme.scheme != s5::Scheme::CcR12 && scheme.scheme != s5::Scheme::CcR23) {
        ++acc.undetectedPayloadErrorFrames;
    }
    acc.successfulDecodedFrames += frame.errors == 0;
    acc.iterations += static_cast<std::uint64_t>(frame.decoded.usedIterations);
    if (frame.decoded.usedIterations == 32) ++acc.maxIterationFrames;
    if (scheme.scheme == s5::Scheme::LdpcN480 || scheme.scheme == s5::Scheme::LdpcN640) {
        acc.iterationSamples.push_back(static_cast<double>(frame.decoded.usedIterations));
    }
    mix(acc.payloadSequenceHash, frame.payloadHash);
    mix(acc.codewordSequenceHash, frame.codewordHash);
    mix(acc.channelSequenceHash, frame.llrHash);
    mix(acc.decoderSequenceHash, frame.decodedHash);
    auto& t = acc.timing;
    t.impairment.push_back(frame.trace.channelImpairmentTimeUs);
    t.awgn.push_back(frame.trace.awgnTimeUs);
    t.equalization.push_back(frame.trace.equalizationTimeUs);
    t.projection.push_back(frame.trace.projectionTimeUs);
    t.llr.push_back(frame.trace.llrGenerationTimeUs);
    t.channel.push_back(frame.trace.channelProcessingTimeUs);
    t.decode.push_back(frame.decodeUs);
    t.receiver.push_back(frame.trace.channelProcessingTimeUs + frame.decodeUs);
}

void warmup(s5::CodecContext& context,
            const s5::SchemeSpec& scheme,
            s5::Channel channel,
            double snr) {
    for (std::uint64_t frame = 0; frame < 10; ++frame) {
        const auto value = evaluateFrame(context, scheme, channel, snr, frame);
        gDecodeSink ^= value.decodedHash;
    }
}

void writeTrace(std::ofstream& out,
                const s5::SchemeSpec& scheme,
                s5::Channel channel,
                const std::string& mode,
                double snr,
                std::uint64_t frame,
                const s5::ChannelTrace& trace) {
    for (std::size_t i = 0; i < trace.rx.size(); ++i) {
        const auto pick = [i](const auto& v, double fallback) {
            return i < v.size() ? static_cast<double>(v[i]) : fallback;
        };
        const double txr = i < trace.tx.size() ? trace.tx[i].real() : 0.0;
        const double txi = i < trace.tx.size() ? trace.tx[i].imag() : 0.0;
        const double impr = i < trace.impaired.size() ? trace.impaired[i].real() : 0.0;
        const double impi = i < trace.impaired.size() ? trace.impaired[i].imag() : 0.0;
        out << scheme.id << ',' << s5::channelName(channel) << ',' << mode << ',' << snr << ',' << frame << ',' << i
            << ',' << txr << ',' << txi << ',' << impr << ',' << impi
            << ',' << trace.rx[i].real() << ',' << trace.rx[i].imag()
            << ',' << pick(trace.phase, 0.0) << ',' << pick(trace.epsilon, 0.0)
            << ',' << pick(trace.mask, -1.0) << ',' << pick(trace.equalized, 0.0)
            << ',' << pick(trace.gain, 0.0) << ',' << pick(trace.variance, 0.0)
            << ',' << pick(trace.llr, 0.0) << ',' << trace.damageStart << ',' << trace.damageLength
            << ',' << trace.relativeStart << ',' << trace.sigmaSquared << '\n';
    }
}

int fixedSmoke(const std::filesystem::path& output) {
    ensureOutput(output);
    std::ofstream summary(output / "fixed_vector_summary.csv");
    std::ofstream traceOut(output / "fixed_vector_trace.csv");
    std::ofstream codecOut(output / "fixed_codec_bits.csv");
    if (!summary || !traceOut || !codecOut) throw std::runtime_error("cannot open fixed smoke outputs");
    summary << std::setprecision(17);
    traceOut << std::setprecision(17);
    summary << "scheme,group,channel,mode,esN0Db,frameIndex,Ntx,bitErrors,frameError,decoderFailure,iterations,syndrome,damageStart,damageLength,relativeStart,sigmaSquared\n";
    traceOut << "scheme,channel,mode,esN0Db,frameIndex,symbolIndex,txReal,txImag,impairedReal,impairedImag,rxReal,rxImag,phase,epsilon,mask,equalized,gain,variance,llr,damageStart,damageLength,relativeStart,sigmaSquared\n";
    codecOut << "scheme,frameIndex,kind,bitIndex,bit\n";
    const std::vector<double> snrs = {1.0, 3.5, 6.0};
    const std::vector<std::string> modes = {"NO_IMPAIRMENT_NO_NOISE", "IMPAIRMENT_NO_AWGN", "IMPAIRMENT_WITH_AWGN"};
    s5::CodecContext context;
    std::uint64_t failures = 0;
    for (const auto& scheme : s5::schemeSpecs()) {
        for (std::uint64_t frame = 0; frame < 10; ++frame) {
            const auto payload = s5::payloadForFrame(frame);
            const auto codeword = s5::encodeFrame(context, scheme.scheme, payload);
            for (std::size_t i = 0; i < payload.size(); ++i)
                codecOut << scheme.id << ',' << frame << ",payload," << i << ',' << static_cast<int>(payload[i]) << '\n';
            for (std::size_t i = 0; i < codeword.size(); ++i)
                codecOut << scheme.id << ',' << frame << ",transmitted," << i << ',' << static_cast<int>(codeword[i]) << '\n';
        }
        for (const auto channel : fixedChannels()) {
            for (const double snr : snrs) {
                for (std::uint64_t frame = 0; frame < 10; ++frame) {
                    const auto payload = s5::payloadForFrame(frame);
                    const auto codeword = s5::encodeFrame(context, scheme.scheme, payload);
                    for (const auto& mode : modes) {
                        const bool addNoise = mode == "IMPAIRMENT_WITH_AWGN";
                        const bool impairment = mode != "NO_IMPAIRMENT_NO_NOISE";
                        const auto trace = s5::runChannel(channel, codeword, snr, frame, addNoise, impairment);
                        const auto decoded = s5::decodeFrame(context, scheme.scheme, trace.llr);
                        const auto errors = s5::bitErrors(payload, decoded.payload);
                        if (mode == "NO_IMPAIRMENT_NO_NOISE" && errors != 0) ++failures;
                        summary << scheme.id << ',' << scheme.comparisonGroup << ',' << s5::channelName(channel)
                                << ',' << mode << ',' << snr << ',' << frame << ',' << scheme.transmittedLength
                                << ',' << errors << ',' << (errors != 0) << ',' << decoded.decoderFailure
                                << ',' << decoded.usedIterations << ',' << decoded.finalSyndromeWeight
                                << ',' << trace.damageStart << ',' << trace.damageLength << ',' << trace.relativeStart
                                << ',' << trace.sigmaSquared << '\n';
                        writeTrace(traceOut, scheme, channel, mode, snr, frame, trace);
                    }
                }
            }
        }
    }
    std::ofstream gate(output / "fixed_vector_gate.txt");
    gate << (failures == 0 ? "PASS_S5_FIXED_VECTOR" : "FAIL_S5_FIXED_VECTOR") << '\n';
    std::cout << "fixed-vector failures=" << failures << '\n';
    return failures == 0 ? 0 : 2;
}

void writeGridHeader(std::ofstream& out) {
    out << "group,channel,esN0Db,scheme,frames,payloadBitErrors,frameErrors,BER,FER,"
           "decoderFailures,undetectedPayloadErrorFrames,successfulDecodedFrames,"
           "iterationsApplicable,avgIterations,p95Iterations,maxIterations,maxIterationFrames,maxIterationRate,"
           "avgChannelImpairmentTimeUs,medianChannelImpairmentTimeUs,p95ChannelImpairmentTimeUs,maxChannelImpairmentTimeUs,"
           "avgAwgnTimeUs,medianAwgnTimeUs,p95AwgnTimeUs,maxAwgnTimeUs,"
           "avgEqualizationTimeUs,medianEqualizationTimeUs,p95EqualizationTimeUs,maxEqualizationTimeUs,"
           "avgProjectionTimeUs,medianProjectionTimeUs,p95ProjectionTimeUs,maxProjectionTimeUs,"
           "avgLlrGenerationTimeUs,medianLlrGenerationTimeUs,p95LlrGenerationTimeUs,maxLlrGenerationTimeUs,"
           "avgChannelProcessingTimeUs,medianChannelProcessingTimeUs,p95ChannelProcessingTimeUs,maxChannelProcessingTimeUs,"
           "avgDecodeTimeUs,medianDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,"
           "avgTotalReceiverAlgorithmTimeUs,medianTotalReceiverAlgorithmTimeUs,p95TotalReceiverAlgorithmTimeUs,maxTotalReceiverAlgorithmTimeUs,"
           "pairedStopReason,warmupFrames,timingClock,timingScope,resultConsumed\n";
}

void writeFour(std::ofstream& out, const std::vector<double>& values) {
    out << mean(values) << ',' << median(values) << ',' << p95(values) << ',' << maximum(values);
}

void writeGridRow(std::ofstream& out,
                  const s5::SchemeSpec& scheme,
                  s5::Channel channel,
                  double snr,
                  const Accumulator& acc,
                  const std::string& reason) {
    const bool ldpc = scheme.scheme == s5::Scheme::LdpcN480 || scheme.scheme == s5::Scheme::LdpcN640;
    out << std::setprecision(17) << scheme.comparisonGroup << ',' << s5::channelName(channel) << ',' << snr << ',' << scheme.id
        << ',' << acc.frames << ',' << acc.bitErrors << ',' << acc.frameErrors
        << ',' << static_cast<double>(acc.bitErrors) / (acc.frames * s5::kPayloadLength)
        << ',' << static_cast<double>(acc.frameErrors) / acc.frames << ',' << acc.decoderFailures
        << ',' << acc.undetectedPayloadErrorFrames << ',' << acc.successfulDecodedFrames << ','
        << (ldpc ? "true" : "false") << ',';
    if (ldpc) out << mean(acc.iterationSamples) << ',' << p95(acc.iterationSamples) << ',' << maximum(acc.iterationSamples)
                  << ',' << acc.maxIterationFrames << ',' << static_cast<double>(acc.maxIterationFrames) / acc.frames << ',';
    else out << "NA,NA,NA,NA,NA,";
    writeFour(out, acc.timing.impairment); out << ',';
    writeFour(out, acc.timing.awgn); out << ',';
    writeFour(out, acc.timing.equalization); out << ',';
    writeFour(out, acc.timing.projection); out << ',';
    writeFour(out, acc.timing.llr); out << ',';
    writeFour(out, acc.timing.channel); out << ',';
    writeFour(out, acc.timing.decode); out << ',';
    writeFour(out, acc.timing.receiver);
    out << ',' << reason << ",10,steady_clock,LLR_TO_DECODE_PAYLOAD_STATUS,true\n";
}

int gridRun(const std::filesystem::path& output,
            std::uint64_t minFrames,
            std::uint64_t targetErrors,
            std::uint64_t maxFrames,
            std::uint64_t shardIndex,
            std::uint64_t shardCount,
            const std::vector<s5::Channel>& selectedChannels,
            const std::vector<double>& snrs) {
    if (minFrames == 0 || minFrames > maxFrames || targetErrors == 0) throw std::invalid_argument("invalid stopping rule");
    if (shardCount == 0 || shardIndex >= shardCount) throw std::invalid_argument("invalid shard coordinates");
    ensureOutput(output);
    std::ofstream summary(output / "grid_smoke_summary.csv");
    if (!summary) throw std::runtime_error("cannot open grid summary");
    writeGridHeader(summary);
    s5::CodecContext context;
    const std::vector<std::vector<std::size_t>> groups = {{0, 2}, {1, 3}};
    std::uint64_t workUnit = 0;
    for (const auto& pair : groups) {
        for (const auto channel : selectedChannels) {
            for (const double snr : snrs) {
                const bool selected = workUnit % shardCount == shardIndex;
                ++workUnit;
                if (!selected) continue;
                warmup(context, s5::schemeSpecs()[pair[0]], channel, snr);
                warmup(context, s5::schemeSpecs()[pair[1]], channel, snr);
                Accumulator acc[2];
                std::uint64_t frame = 0;
                std::string reason = "PAIRED_MAX_FRAMES_REACHED";
                for (; frame < maxFrames; ++frame) {
                    for (int side = 0; side < 2; ++side) {
                        const auto audit = evaluateFrame(context, s5::schemeSpecs()[pair[side]], channel, snr, frame);
                        recordFrame(s5::schemeSpecs()[pair[side]], audit, acc[side]);
                    }
                    if (frame + 1 >= minFrames && acc[0].frameErrors >= targetErrors && acc[1].frameErrors >= targetErrors) {
                        reason = "PAIRED_TARGET_FRAME_ERRORS_REACHED";
                        ++frame;
                        break;
                    }
                }
                for (int side = 0; side < 2; ++side)
                    writeGridRow(summary, s5::schemeSpecs()[pair[side]], channel, snr, acc[side], reason);
                summary.flush();
                std::cout << s5::schemeSpecs()[pair[0]].comparisonGroup << ' ' << s5::channelName(channel)
                          << " EsN0=" << snr << " frames=" << frame << " FER="
                          << static_cast<double>(acc[0].frameErrors) / acc[0].frames << ','
                          << static_cast<double>(acc[1].frameErrors) / acc[1].frames << '\n';
            }
        }
    }
    std::ofstream gate(output / "grid_smoke_gate.txt");
    gate << "PASS_S5_GRID_EXECUTION\n";
    return 0;
}

std::string checkpointText(const std::string& taskKey,
                           const std::string& runId,
                           const std::string& group,
                           s5::Channel channel,
                           double snr,
                           std::uint64_t nextFrame,
                           std::uint64_t minFrames,
                           std::uint64_t targetErrors,
                           std::uint64_t maxFrames,
                           const std::string& configHash,
                           std::uint64_t sequence,
                           bool complete,
                           bool resumed,
                           const std::string& stopReason,
                           const Accumulator acc[2]) {
    std::ostringstream out;
    out << std::setprecision(17);
    out << "{\n  \"schemaVersion\": \"s5.formal_checkpoint.v1\",\n"
        << "  \"runId\": \"" << runId << "\",\n  \"taskKey\": \"" << taskKey << "\",\n"
        << "  \"group\": \"" << group << "\",\n  \"channel\": \"" << s5::channelName(channel) << "\",\n"
        << "  \"snrDb\": " << snr << ",\n  \"K\": 300,\n  \"frameStart\": 0,\n"
        << "  \"nextFrame\": " << nextFrame << ",\n  \"minFrames\": " << minFrames
        << ",\n  \"targetFrameErrors\": " << targetErrors << ",\n  \"maxFrames\": " << maxFrames << ",\n"
        << "  \"checkpointIntervalFrames\": 1000,\n  \"payloadSeed\": " << s5::kPayloadSeed
        << ",\n  \"noiseSeed\": " << s5::kNoiseSeed << ",\n  \"noisePolicy\": \"" << s5::kComplexNoisePolicy << "\",\n"
        << "  \"configHash\": \"" << configHash << "\",\n  \"codeVersion\": \"S5_FORMAL_READINESS_V1\",\n"
        << "  \"checkpointSequence\": " << sequence << ",\n  \"resumeCount\": " << (resumed ? 1 : 0)
        << ",\n  \"complete\": " << (complete ? "true" : "false")
        << ",\n  \"stopReason\": \"" << stopReason << "\",\n  \"schemes\": [\n";
    for (int side = 0; side < 2; ++side) {
        const auto& scheme = s5::schemeSpecs()[groupPair(group)[side]];
        const auto& a = acc[side];
        out << "    {\"scheme\": \"" << scheme.id << "\", \"N\": " << scheme.transmittedLength
            << ", \"actualRate\": " << scheme.actualRate << ", \"frames\": " << a.frames
            << ", \"payloadBitErrors\": " << a.bitErrors << ", \"frameErrors\": " << a.frameErrors
            << ", \"decoderFailures\": " << a.decoderFailures
            << ", \"undetectedPayloadErrorFrames\": " << a.undetectedPayloadErrorFrames
            << ", \"successfulDecodedFrames\": " << a.successfulDecodedFrames
            << ", \"iterationSum\": " << a.iterations << ", \"maxIterationFrames\": " << a.maxIterationFrames
            << ", \"timingSampleCount\": " << a.timing.decode.size()
            << ", \"decodeTimeSumUs\": " << mean(a.timing.decode) * a.timing.decode.size()
            << ", \"channelTimeSumUs\": " << mean(a.timing.channel) * a.timing.channel.size()
            << ", \"receiverTimeSumUs\": " << mean(a.timing.receiver) * a.timing.receiver.size()
            << ", \"payloadSequenceHash\": \"" << hex64(a.payloadSequenceHash)
            << "\", \"codewordSequenceHash\": \"" << hex64(a.codewordSequenceHash)
            << "\", \"channelSequenceHash\": \"" << hex64(a.channelSequenceHash)
            << "\", \"decoderSequenceHash\": \"" << hex64(a.decoderSequenceHash) << "\"}"
            << (side == 0 ? "," : "") << "\n";
    }
    out << "  ]\n}\n";
    return out.str();
}

std::string jsonString(const std::string& text, const std::string& key) {
    const auto marker = "\"" + key + "\":";
    auto pos = text.find(marker);
    if (pos == std::string::npos) throw std::runtime_error("checkpoint key missing: " + key);
    pos = text.find('"', pos + marker.size());
    const auto end = text.find('"', pos + 1);
    if (pos == std::string::npos || end == std::string::npos) throw std::runtime_error("invalid checkpoint string: " + key);
    return text.substr(pos + 1, end - pos - 1);
}

std::uint64_t jsonUint(const std::string& text, const std::string& key) {
    const auto marker = "\"" + key + "\":";
    auto pos = text.find(marker);
    if (pos == std::string::npos) throw std::runtime_error("checkpoint key missing: " + key);
    pos += marker.size();
    while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos;
    std::size_t used = 0;
    const auto value = std::stoull(text.substr(pos), &used);
    if (used == 0) throw std::runtime_error("invalid checkpoint integer: " + key);
    return value;
}

bool jsonBool(const std::string& text, const std::string& key) {
    const auto marker = "\"" + key + "\":";
    auto pos = text.find(marker);
    if (pos == std::string::npos) throw std::runtime_error("checkpoint key missing: " + key);
    pos += marker.size();
    while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) ++pos;
    if (text.compare(pos, 4, "true") == 0) return true;
    if (text.compare(pos, 5, "false") == 0) return false;
    throw std::runtime_error("invalid checkpoint boolean: " + key);
}

std::string readText(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot read " + path.string());
    return std::string(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
}

void replaceFile(const std::filesystem::path& source, const std::filesystem::path& target) {
#ifdef _WIN32
    if (!MoveFileExW(source.wstring().c_str(), target.wstring().c_str(),
                     MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        throw std::runtime_error("atomic checkpoint rename failed");
    }
#else
    std::filesystem::rename(source, target);
#endif
}

void writeCheckpointAtomic(const std::filesystem::path& path, const std::string& content) {
    const auto temporary = path.string() + ".tmp";
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output) throw std::runtime_error("cannot create checkpoint temporary");
        output << content;
        output.flush();
        if (!output) throw std::runtime_error("checkpoint temporary flush failed");
    }
    const auto reread = readText(temporary);
    if (reread != content || jsonString(reread, "schemaVersion") != "s5.formal_checkpoint.v1")
        throw std::runtime_error("checkpoint temporary re-read validation failed");
    replaceFile(temporary, path);
    const auto final = readText(path);
    if (final != content) throw std::runtime_error("checkpoint post-rename validation failed");
}

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> values;
    std::stringstream stream(line);
    std::string value;
    while (std::getline(stream, value, ',')) values.push_back(value);
    return values;
}

void loadTimingSamples(const std::filesystem::path& path,
                       std::uint64_t nextFrame,
                       Accumulator acc[2]) {
    if (nextFrame == 0) return;
    std::ifstream input(path);
    if (!input) throw std::runtime_error("checkpoint exists but timing samples are missing");
    std::string line;
    std::getline(input, line);
    std::uint64_t accepted = 0;
    while (std::getline(input, line)) {
        const auto v = split(line);
        if (v.size() != 18) throw std::runtime_error("invalid timing sample row");
        const auto frame = std::stoull(v[0]);
        if (frame >= nextFrame) continue;
        const int side = std::stoi(v[1]);
        if (side < 0 || side > 1) throw std::runtime_error("invalid timing sample side");
        auto& a = acc[side];
        const double iteration = std::stod(v[6]);
        if (iteration > 0.0) a.iterationSamples.push_back(iteration);
        a.timing.impairment.push_back(std::stod(v[8]));
        a.timing.awgn.push_back(std::stod(v[9]));
        a.timing.equalization.push_back(std::stod(v[10]));
        a.timing.projection.push_back(std::stod(v[11]));
        a.timing.llr.push_back(std::stod(v[12]));
        a.timing.channel.push_back(std::stod(v[13]));
        a.timing.decode.push_back(std::stod(v[14]));
        a.timing.receiver.push_back(std::stod(v[15]));
        ++accepted;
    }
    if (accepted != 2 * nextFrame) throw std::runtime_error("timing sample count differs from checkpoint nextFrame");
}

void restoreCheckpoint(const std::string& text, Accumulator acc[2]) {
    for (int side = 0; side < 2; ++side) {
        const auto schemePos = side == 0 ? text.find("{\"scheme\"") : text.find("{\"scheme\"", text.find("{\"scheme\"") + 1);
        if (schemePos == std::string::npos) throw std::runtime_error("checkpoint scheme state missing");
        const auto end = text.find('}', schemePos);
        const auto block = text.substr(schemePos, end - schemePos + 1);
        auto& a = acc[side];
        a.frames = jsonUint(block, "frames");
        a.bitErrors = jsonUint(block, "payloadBitErrors");
        a.frameErrors = jsonUint(block, "frameErrors");
        a.decoderFailures = jsonUint(block, "decoderFailures");
        a.undetectedPayloadErrorFrames = jsonUint(block, "undetectedPayloadErrorFrames");
        a.successfulDecodedFrames = jsonUint(block, "successfulDecodedFrames");
        a.iterations = jsonUint(block, "iterationSum");
        a.maxIterationFrames = jsonUint(block, "maxIterationFrames");
        a.payloadSequenceHash = std::stoull(jsonString(block, "payloadSequenceHash"), nullptr, 16);
        a.codewordSequenceHash = std::stoull(jsonString(block, "codewordSequenceHash"), nullptr, 16);
        a.channelSequenceHash = std::stoull(jsonString(block, "channelSequenceHash"), nullptr, 16);
        a.decoderSequenceHash = std::stoull(jsonString(block, "decoderSequenceHash"), nullptr, 16);
    }
}

void writeTimingSample(std::ofstream& out,
                       std::uint64_t frame,
                       int side,
                       const s5::SchemeSpec& scheme,
                       const FrameAudit& value) {
    out << std::setprecision(17) << frame << ',' << side << ',' << scheme.id << ',' << value.errors << ','
        << (value.errors != 0) << ',' << value.decoded.decoderFailure << ',' << value.decoded.usedIterations << ','
        << value.decoded.finalSyndromeWeight << ',' << value.trace.channelImpairmentTimeUs << ','
        << value.trace.awgnTimeUs << ',' << value.trace.equalizationTimeUs << ',' << value.trace.projectionTimeUs << ','
        << value.trace.llrGenerationTimeUs << ',' << value.trace.channelProcessingTimeUs << ',' << value.decodeUs << ','
        << (value.trace.channelProcessingTimeUs + value.decodeUs) << ',' << hex64(value.llrHash) << ',' << hex64(value.decodedHash) << '\n';
}

std::string taskResultHash(const Accumulator acc[2], std::uint64_t frames, const std::string& stopReason) {
    std::uint64_t hash = kFnvOffset;
    mix(hash, frames);
    for (int side = 0; side < 2; ++side) {
        mix(hash, acc[side].bitErrors);
        mix(hash, acc[side].frameErrors);
        mix(hash, acc[side].decoderFailures);
        mix(hash, acc[side].iterations);
        mix(hash, acc[side].payloadSequenceHash);
        mix(hash, acc[side].codewordSequenceHash);
        mix(hash, acc[side].channelSequenceHash);
        mix(hash, acc[side].decoderSequenceHash);
    }
    for (const char c : stopReason) mix(hash, static_cast<unsigned char>(c));
    return hex64(hash);
}

void writeFormalHeader(std::ofstream& out) {
    out << "runId,taskKey,shardId,group,channel,scheme,decoder,K,N,actualRate,esN0Db,ebN0Db,sigmaSquared,"
           "frames,payloadBitErrors,frameErrors,BER,FER,berCiLow,berCiHigh,ferCiLow,ferCiHigh,"
           "decoderFailureFrames,undetectedPayloadErrorFrames,successfulDecodedFrames,"
           "iterationsApplicable,avgIterations,medianIterations,p95Iterations,maxIterations,maxIterationFrames,maxIterationRate,"
           "avgChannelImpairmentTimeUs,medianChannelImpairmentTimeUs,p95ChannelImpairmentTimeUs,maxChannelImpairmentTimeUs,"
           "avgAwgnTimeUs,medianAwgnTimeUs,p95AwgnTimeUs,maxAwgnTimeUs,"
           "avgEqualizationTimeUs,medianEqualizationTimeUs,p95EqualizationTimeUs,maxEqualizationTimeUs,"
           "avgProjectionTimeUs,medianProjectionTimeUs,p95ProjectionTimeUs,maxProjectionTimeUs,"
           "avgLlrGenerationTimeUs,medianLlrGenerationTimeUs,p95LlrGenerationTimeUs,maxLlrGenerationTimeUs,"
           "avgChannelProcessingTimeUs,medianChannelProcessingTimeUs,p95ChannelProcessingTimeUs,maxChannelProcessingTimeUs,"
           "avgDecodeTimeUs,medianDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,"
           "avgTotalReceiverAlgorithmTimeUs,medianTotalReceiverAlgorithmTimeUs,p95TotalReceiverAlgorithmTimeUs,maxTotalReceiverAlgorithmTimeUs,"
           "stopReason,frameStart,nextFrame,payloadSequenceHash,codewordSequenceHash,channelSequenceHash,decoderSequenceHash,"
           "noisePolicy,payloadPolicy,blockagePolicy,burstPolicy,timingClock,timingScope,warmupFrames,configHash,codeVersion,taskResultHash\n";
}

void writeFormalRow(std::ofstream& out,
                    const std::string& runId,
                    const std::string& taskKey,
                    const std::string& group,
                    s5::Channel channel,
                    double snr,
                    const std::string& configHash,
                    const std::string& stopReason,
                    const std::string& resultHash,
                    const s5::SchemeSpec& scheme,
                    const Accumulator& acc) {
    const bool ldpc = scheme.scheme == s5::Scheme::LdpcN480 || scheme.scheme == s5::Scheme::LdpcN640;
    const auto berCi = wilson(acc.bitErrors, acc.frames * s5::kPayloadLength);
    const auto ferCi = wilson(acc.frameErrors, acc.frames);
    out << std::setprecision(17) << runId << ',' << taskKey << ",NA," << group << ',' << s5::channelName(channel) << ','
        << scheme.id << ',' << (ldpc ? "DIRECT_LAYERED_NMS" : "SOFT_VITERBI_FULL_BLOCK") << ",300,"
        << scheme.transmittedLength << ',' << scheme.actualRate << ',' << snr << ','
        << s5::ebN0FromEsN0(snr, scheme.actualRate) << ',' << s5::sigmaSquaredFromEsN0(snr) << ','
        << acc.frames << ',' << acc.bitErrors << ',' << acc.frameErrors << ','
        << static_cast<double>(acc.bitErrors) / (acc.frames * s5::kPayloadLength) << ','
        << static_cast<double>(acc.frameErrors) / acc.frames << ',' << berCi.first << ',' << berCi.second << ','
        << ferCi.first << ',' << ferCi.second << ',' << acc.decoderFailures << ','
        << acc.undetectedPayloadErrorFrames << ',' << acc.successfulDecodedFrames << ','
        << (ldpc ? "true" : "false") << ',';
    if (ldpc) out << mean(acc.iterationSamples) << ',' << median(acc.iterationSamples) << ',' << p95(acc.iterationSamples)
                  << ',' << maximum(acc.iterationSamples) << ',' << acc.maxIterationFrames << ','
                  << static_cast<double>(acc.maxIterationFrames) / acc.frames << ',';
    else out << "NA,NA,NA,NA,NA,NA,";
    writeFour(out, acc.timing.impairment); out << ',';
    writeFour(out, acc.timing.awgn); out << ',';
    writeFour(out, acc.timing.equalization); out << ',';
    writeFour(out, acc.timing.projection); out << ',';
    writeFour(out, acc.timing.llr); out << ',';
    writeFour(out, acc.timing.channel); out << ',';
    writeFour(out, acc.timing.decode); out << ',';
    writeFour(out, acc.timing.receiver);
    out << ',' << stopReason << ",0," << acc.frames << ',' << hex64(acc.payloadSequenceHash) << ','
        << hex64(acc.codewordSequenceHash) << ',' << hex64(acc.channelSequenceHash) << ',' << hex64(acc.decoderSequenceHash)
        << ',' << s5::kComplexNoisePolicy << ",COMMON_FRAME_POOL_K300_V1,"
        << "KNOWN_CONTIGUOUS_ERASURE_5_PERCENT_LLR_ZERO,UNKNOWN_CONTIGUOUS_BURST_5_PERCENT_ISR_10DB_NOMINAL_AWGN_LLR,"
        << "steady_clock,LLR_TO_DECODE_PAYLOAD_STATUS,10," << configHash << ",S5_FORMAL_READINESS_V1," << resultHash << '\n';
}

int formalTask(const std::filesystem::path& output,
               const std::string& group,
               s5::Channel channel,
               double snr,
               std::uint64_t minFrames,
               std::uint64_t targetErrors,
               std::uint64_t maxFrames,
               const std::string& configHash,
               const std::string& runId,
               std::uint64_t interruptAfter) {
    if (minFrames == 0 || minFrames > maxFrames || targetErrors == 0 || maxFrames % 1000 != 0)
        throw std::invalid_argument("invalid formal stopping rule");
    const auto frozenChannels = formalChannels();
    if (std::find(frozenChannels.begin(), frozenChannels.end(), channel) == frozenChannels.end())
        throw std::invalid_argument("channel is not in the frozen Formal set");
    ensureOutput(output);
    const auto checkpointPath = output / "checkpoint.json";
    const auto samplesPath = output / "timing_samples.csv";
    const auto finalPath = output / "final_result.csv";
    std::ostringstream key;
    key << group << '_' << s5::channelName(channel) << '_' << std::fixed << std::setprecision(1) << snr;
    const std::string taskKey = key.str();
    Accumulator acc[2];
    std::uint64_t nextFrame = 0;
    std::uint64_t checkpointSequence = 0;
    bool resumed = false;
    if (std::filesystem::exists(checkpointPath)) {
        const auto text = readText(checkpointPath);
        if (jsonString(text, "taskKey") != taskKey || jsonString(text, "configHash") != configHash
            || jsonUint(text, "maxFrames") != maxFrames || jsonUint(text, "minFrames") != minFrames
            || jsonUint(text, "targetFrameErrors") != targetErrors) {
            throw std::runtime_error("checkpoint fingerprint/config mismatch");
        }
        nextFrame = jsonUint(text, "nextFrame");
        checkpointSequence = jsonUint(text, "checkpointSequence");
        restoreCheckpoint(text, acc);
        loadTimingSamples(samplesPath, nextFrame, acc);
        for (int side = 0; side < 2; ++side) {
            if (acc[side].frames != nextFrame || acc[side].timing.decode.size() != nextFrame)
                throw std::runtime_error("checkpoint frame/timing accumulator mismatch");
        }
        if (jsonBool(text, "complete")) {
            if (!std::filesystem::exists(finalPath)) throw std::runtime_error("complete checkpoint missing final result");
            const auto finalText = readText(finalPath);
            if (finalText.find(configHash) == std::string::npos
                || finalText.find(taskResultHash(acc, nextFrame, jsonString(text, "stopReason"))) == std::string::npos)
                throw std::runtime_error("completed result hash/config audit failed");
            std::cout << "SKIPPED_ALREADY_COMPLETE taskKey=" << taskKey << '\n';
            return 0;
        }
        resumed = nextFrame > 0;
    }

    const auto pair = groupPair(group);
    s5::CodecContext context;
    warmup(context, s5::schemeSpecs()[pair[0]], channel, snr);
    warmup(context, s5::schemeSpecs()[pair[1]], channel, snr);
    std::ofstream samples;
    if (nextFrame == 0) {
        samples.open(samplesPath, std::ios::trunc);
        samples << "frameIndex,side,scheme,bitErrors,frameError,decoderFailure,iterations,finalSyndromeWeight,"
                   "channelImpairmentTimeUs,awgnTimeUs,equalizationTimeUs,projectionTimeUs,llrGenerationTimeUs,"
                   "channelProcessingTimeUs,decodeTimeUs,totalReceiverAlgorithmTimeUs,llrHash,decodedHash\n";
    } else samples.open(samplesPath, std::ios::app);
    if (!samples) throw std::runtime_error("cannot open formal timing samples");

    std::string stopReason;
    for (std::uint64_t frame = nextFrame; frame < maxFrames; ++frame) {
        for (int side = 0; side < 2; ++side) {
            const auto audit = evaluateFrame(context, s5::schemeSpecs()[pair[side]], channel, snr, frame);
            recordFrame(s5::schemeSpecs()[pair[side]], audit, acc[side]);
            writeTimingSample(samples, frame, side, s5::schemeSpecs()[pair[side]], audit);
        }
        nextFrame = frame + 1;
        const bool targetReached = nextFrame >= minFrames
            && acc[0].frameErrors >= targetErrors && acc[1].frameErrors >= targetErrors;
        const bool maxReached = nextFrame == maxFrames;
        const bool checkpointDue = nextFrame % 1000 == 0;
        if (checkpointDue || targetReached || maxReached) {
            samples.flush();
            if (!samples) throw std::runtime_error("timing samples flush failed");
            ++checkpointSequence;
            const std::string provisionalReason = targetReached
                ? "PAIRED_TARGET_FRAME_ERRORS_REACHED"
                : (maxReached ? "PAIRED_MAX_FRAMES_REACHED" : "CHECKPOINT_IN_PROGRESS");
            writeCheckpointAtomic(checkpointPath, checkpointText(taskKey, runId, group, channel, snr, nextFrame,
                minFrames, targetErrors, maxFrames, configHash, checkpointSequence,
                targetReached || maxReached, resumed, provisionalReason, acc));
        }
        if (interruptAfter > 0 && nextFrame >= interruptAfter) {
            if (nextFrame % 1000 != 0) throw std::runtime_error("intentional interruption must align to checkpoint interval");
            std::cout << "INTENTIONAL_CHECKPOINT_INTERRUPT nextFrame=" << nextFrame << '\n';
            return 3;
        }
        if (targetReached) {
            stopReason = "PAIRED_TARGET_FRAME_ERRORS_REACHED";
            break;
        }
        if (maxReached) {
            stopReason = "PAIRED_MAX_FRAMES_REACHED";
            break;
        }
    }
    samples.close();
    if (stopReason.empty()) throw std::runtime_error("formal task ended without a permitted stop reason");
    const auto resultHash = taskResultHash(acc, nextFrame, stopReason);
    std::ofstream final(finalPath, std::ios::trunc);
    if (!final) throw std::runtime_error("cannot create formal final result");
    writeFormalHeader(final);
    writeFormalRow(final, runId, taskKey, group, channel, snr, configHash, stopReason, resultHash,
                   s5::schemeSpecs()[pair[0]], acc[0]);
    writeFormalRow(final, runId, taskKey, group, channel, snr, configHash, stopReason, resultHash,
                   s5::schemeSpecs()[pair[1]], acc[1]);
    final.close();
    if (readText(finalPath).find(resultHash) == std::string::npos) throw std::runtime_error("final result re-read hash audit failed");
    writeCheckpointAtomic(checkpointPath, checkpointText(taskKey, runId, group, channel, snr, nextFrame,
        minFrames, targetErrors, maxFrames, configHash, checkpointSequence, true, resumed, stopReason, acc));
    std::cout << "PASS_S5_FORMAL_TASK taskKey=" << taskKey << " frames=" << nextFrame << " resultHash=" << resultHash << '\n';
    return 0;
}

int s4AwgnExtensionProbe(const std::filesystem::path& output, std::uint64_t frames) {
    if (frames < 1000 || frames > 50000) throw std::invalid_argument("S4 extension frames outside [1000,50000]");
    ensureOutput(output);
    const auto cases = s4ldpc::freezeS4Cases();
    const auto found = std::find_if(cases.begin(), cases.end(), [](const auto& value) {
        return value.actualLength == 480;
    });
    if (found == cases.end()) throw std::runtime_error("S4 N480 case missing");
    const auto graph = s4ldpc::buildDirectGraph(*found);
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
    std::uint64_t firstBitErrors = 0;
    std::uint64_t firstFrameErrors = 0;
    for (std::uint64_t offset = 0; offset < frames; ++offset) {
        const int frameIndex = 100000 + static_cast<int>(offset);
        const auto payload = s4ldpc::makePayload(2026072001ULL, frameIndex, 300);
        const auto codeword = s4ldpc::encode(graph, payload);
        const auto llr = s4ldpc::makeChannelLlr(*found, codeword,
            2026073001ULL ^ 140001ULL, 480ULL, frameIndex, 2.5);
        const auto decoded = s4ldpc::decodeLayeredNms(graph, llr, 32, 0.95,
            s4ldpc::EarlyStopPolicy::SyndromeAfterFullIteration);
        std::uint64_t errors = 0;
        for (std::size_t i = 0; i < 300; ++i) errors += payload[i] != decoded.bits[i];
        bitErrors += errors;
        frameErrors += errors != 0;
        if (offset == 999) {
            firstBitErrors = bitErrors;
            firstFrameErrors = frameErrors;
        }
    }
    std::ofstream result(output / "s4_n480_2p5db_extension.csv");
    if (!result) throw std::runtime_error("cannot create S4 extension result");
    result << std::setprecision(17)
           << "range,frameStart,frameEnd,frames,bitErrors,frameErrors,BER,FER,payloadSeed,noiseSeed,noiseGroupId,runId,alpha,maxIterations\n"
           << "historical_reproduction,100000,100999,1000," << firstBitErrors << ',' << firstFrameErrors << ','
           << static_cast<double>(firstBitErrors) / 300000.0 << ',' << static_cast<double>(firstFrameErrors) / 1000.0
           << ",2026072001,2026073001,480,140001,0.95,32\n"
           << "extended,100000," << (99999 + frames) << ',' << frames << ',' << bitErrors << ',' << frameErrors << ','
           << static_cast<double>(bitErrors) / (frames * 300.0) << ',' << static_cast<double>(frameErrors) / frames
           << ",2026072001,2026073001,480,140001,0.95,32\n";
    const bool reproduce = firstBitErrors == 2891 && firstFrameErrors == 846;
    std::cout << (reproduce ? "PASS_S4_HISTORICAL_REPRODUCTION" : "FAIL_S4_HISTORICAL_REPRODUCTION")
              << " extendedFrames=" << frames << " FER=" << static_cast<double>(frameErrors) / frames << '\n';
    return reproduce ? 0 : 2;
}

std::uint64_t parseUint(const char* value) {
    std::size_t used = 0;
    const auto result = std::stoull(value, &used);
    if (used != std::string(value).size()) throw std::invalid_argument("invalid integer option");
    return result;
}

std::vector<double> smokeSnrs() {
    std::vector<double> values;
    for (int tenth = 10; tenth <= 60; tenth += 5) values.push_back(tenth / 10.0);
    return values;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 3) throw std::invalid_argument("usage: s5_runner MODE OUTPUT [options]");
        const std::string mode = argv[1];
        if (mode == "fixed") return fixedSmoke(argv[2]);
        if (mode == "grid" || mode == "blockage5_grid" || mode == "awgn_grid" || mode == "timing") {
            const std::uint64_t minFrames = argc > 3 ? parseUint(argv[3]) : 1000;
            const std::uint64_t targetErrors = argc > 4 ? parseUint(argv[4]) : 200;
            const std::uint64_t maxFrames = argc > 5 ? parseUint(argv[5]) : 50000;
            const std::uint64_t shardIndex = argc > 6 ? parseUint(argv[6]) : 0;
            const std::uint64_t shardCount = argc > 7 ? parseUint(argv[7]) : 1;
            const auto selectedChannels = mode == "blockage5_grid" ? std::vector<s5::Channel>{s5::Channel::Blockage5}
                : ((mode == "timing" || mode == "awgn_grid") ? std::vector<s5::Channel>{s5::Channel::Awgn} : fixedChannels());
            const auto selectedSnrs = mode == "timing" ? std::vector<double>{1.0, 3.5, 6.0} : smokeSnrs();
            return gridRun(argv[2], minFrames, targetErrors, maxFrames, shardIndex, shardCount,
                           selectedChannels, selectedSnrs);
        }
        if (mode == "formal_task") {
            if (argc < 11 || argc > 12) throw std::invalid_argument(
                "formal_task OUTPUT GROUP CHANNEL SNR MIN TARGET MAX CONFIG_HASH RUN_ID [INTERRUPT_AFTER]");
            return formalTask(argv[2], argv[3], parseChannel(argv[4]), std::stod(argv[5]),
                              parseUint(argv[6]), parseUint(argv[7]), parseUint(argv[8]),
                              argv[9], argv[10], argc == 12 ? parseUint(argv[11]) : 0);
        }
        if (mode == "s4_awgn_extension") {
            return s4AwgnExtensionProbe(argv[2], argc > 3 ? parseUint(argv[3]) : 50000);
        }
        throw std::invalid_argument("unknown runner mode");
    } catch (const std::exception& error) {
        std::cerr << "S5 ERROR: " << error.what() << '\n';
        return 1;
    }
}
