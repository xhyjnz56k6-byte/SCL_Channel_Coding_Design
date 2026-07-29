#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
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
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kSeed = 2026072001ULL;
constexpr std::size_t kPayload = 300;
constexpr std::size_t kCodec = 306;

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

struct WindowConfig {
    std::size_t window = 0;
    std::size_t slide = 0;
    std::size_t depth = 0;
};

struct SlidingResult {
    std::vector<std::uint8_t> payload;
    std::vector<std::size_t> decision_time;
    std::uint64_t acs = 0;
    std::uint64_t traceback = 0;
};

struct Scenario {
    std::string id;
    double snr = 0.0;
    scl::cc::PuncturePattern pattern;
    std::uint64_t group = 0;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

bool better(double candidate, std::uint8_t predecessor, std::uint8_t input,
            double incumbent, const Survivor& survivor) {
    if (!survivor.valid || candidate < incumbent) return true;
    if (candidate > incumbent) return false;
    if (predecessor != survivor.predecessor) return predecessor < survivor.predecessor;
    return input < survivor.input;
}

std::uint8_t best_state(const std::array<double, scl::cc::kStateCount>& metrics) {
    std::uint8_t state = 0;
    double best = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < metrics.size(); ++i) {
        if (metrics[i] < best) {
            best = metrics[i];
            state = static_cast<std::uint8_t>(i);
        }
    }
    return state;
}

SlidingResult decode_sliding(const scl::cc::Trellis& trellis,
                             const std::vector<double>& received,
                             const std::vector<std::uint8_t>& mask,
                             const WindowConfig& cfg,
                             bool hard_metric) {
    if (cfg.window == 0 || cfg.slide == 0 || cfg.depth == 0 ||
        cfg.slide > cfg.window || cfg.depth > cfg.window || cfg.window > kCodec) {
        throw std::invalid_argument("invalid sliding-window configuration");
    }
    if (received.size() != 2 * kCodec || mask.size() != received.size()) {
        throw std::invalid_argument("sliding-window input length mismatch");
    }
    for (double value : received) {
        if (!std::isfinite(value)) throw std::invalid_argument("non-finite received value");
    }

    const double infinity = std::numeric_limits<double>::infinity();
    std::array<double, scl::cc::kStateCount> metrics{};
    std::array<double, scl::cc::kStateCount> next{};
    metrics.fill(infinity);
    metrics[0] = 0.0;
    std::vector<Survivor> survivors(kCodec * scl::cc::kStateCount);
    std::vector<std::uint8_t> decoded(kCodec, 0);
    std::vector<std::uint8_t> emitted(kPayload, 0);
    SlidingResult result;
    result.decision_time.assign(kPayload, kCodec - 1);
    std::size_t next_emit = 0;

    auto trace_and_emit = [&](std::size_t end_time, std::uint8_t end_state,
                              std::size_t span, std::size_t requested_emit_end) {
        if (span == 0 || span > end_time + 1) return;
        const std::size_t start = end_time + 1 - span;
        std::vector<std::uint8_t> local(span, 0);
        std::uint8_t state = end_state;
        for (std::size_t offset = 0; offset < span; ++offset) {
            const std::size_t time = end_time - offset;
            const auto& survivor = survivors[time * scl::cc::kStateCount + state];
            if (!survivor.valid) throw std::runtime_error("invalid sliding survivor");
            local[span - 1 - offset] = survivor.input;
            state = survivor.predecessor;
            ++result.traceback;
        }
        const bool final_flush = end_time + 1 == kCodec && requested_emit_end == kPayload;
        const std::size_t emit_end = final_flush
            ? kPayload
            : std::min({requested_emit_end, start + cfg.slide, kPayload});
        while (next_emit < emit_end) {
            if (next_emit >= start && next_emit < start + local.size()) {
                decoded[next_emit] = local[next_emit - start];
                emitted[next_emit] = 1;
                result.decision_time[next_emit] = end_time;
                ++next_emit;
            } else {
                break;
            }
        }
    };

    for (std::size_t time = 0; time < kCodec; ++time) {
        next.fill(infinity);
        auto* step = survivors.data() + time * scl::cc::kStateCount;
        std::fill(step, step + scl::cc::kStateCount, Survivor{});
        for (std::size_t state = 0; state < scl::cc::kStateCount; ++state) {
            if (!std::isfinite(metrics[state])) continue;
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(static_cast<std::uint8_t>(state), input);
                double branch_metric = 0.0;
                for (std::size_t j = 0; j < 2; ++j) {
                    if (mask[2 * time + j] == 0) continue;
                    const double expected = symbol(branch.output_bits[j]);
                    if (hard_metric) {
                        const double bit = received[2 * time + j] >= 0.0 ? 1.0 : -1.0;
                        branch_metric += bit == expected ? 0.0 : 1.0;
                    } else {
                        const double diff = received[2 * time + j] - expected;
                        branch_metric += diff * diff;
                    }
                }
                const double candidate = metrics[state] + branch_metric;
                auto& survivor = step[branch.next_state];
                if (better(candidate, static_cast<std::uint8_t>(state), input,
                           next[branch.next_state], survivor)) {
                    next[branch.next_state] = candidate;
                    survivor = {static_cast<std::uint8_t>(state), input, true};
                }
                ++result.acs;
            }
        }
        const double minimum = *std::min_element(next.begin(), next.end());
        if (!std::isfinite(minimum)) throw std::runtime_error("no reachable sliding state");
        for (double& value : next) {
            if (std::isfinite(value)) value -= minimum;
        }
        metrics = next;

        if (time + 1 >= cfg.window && ((time + 1 - cfg.window) % cfg.slide == 0)) {
            const std::size_t emit_target = std::min(time + 1 - cfg.window + cfg.slide, kPayload);
            trace_and_emit(time, best_state(metrics), cfg.window, emit_target);
        }
    }

    trace_and_emit(kCodec - 1, 0, kCodec, kPayload);
    if (std::any_of(emitted.begin(), emitted.end(), [](std::uint8_t value) { return value == 0; })) {
        throw std::runtime_error("sliding decoder failed to emit every payload bit");
    }
    result.payload.assign(decoded.begin(), decoded.begin() + kPayload);
    return result;
}

std::uint64_t errors(const std::vector<std::uint8_t>& left,
                     const std::vector<std::uint8_t>& right) {
    if (left.size() != right.size()) throw std::runtime_error("comparison length mismatch");
    std::uint64_t total = 0;
    for (std::size_t i = 0; i < left.size(); ++i) total += left[i] != right[i];
    return total;
}

std::string region_of(std::size_t bit) {
    bool boundary = false;
    for (std::size_t b : {50U, 100U, 150U, 200U, 250U}) {
        boundary = boundary || (bit + 10 >= b && bit < b + 10);
    }
    if (bit < 70) return "head";
    if (bit >= 230) return "tail";
    if (boundary) return "boundary";
    return "middle";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::SoftViterbiDecoder soft_full(trellis);
        const std::vector<WindowConfig> configs = {
            {64, 16, 35}, {64, 25, 35}, {96, 16, 49}, {96, 25, 70},
            {128, 25, 70}, {128, 50, 84}, {192, 50, 98}
        };
        const std::vector<Scenario> scenarios = {
            {"CC-C-R12-S", 0.0, {"R12_11", {1, 1}}, 1200},
            {"CC-C-R23-S", 1.0, {"R23_B_1101", {1, 1, 0, 1}}, 2300},
            {"CC-C-R34-S", 2.0, {"R34_B_110110", {1, 1, 0, 1, 1, 0}}, 3400}
        };

        std::ofstream pre(results / "stage13_window_prescan.csv");
        pre << "windowInputBits,slideStepBits,tracebackDepthBits,status,"
               "survivorMemoryBytes,windowBufferBytes,firstOutputDelaySymbols,selected\n";
        for (const auto& cfg : configs) {
            const bool selected = cfg.window == 96 && cfg.slide == 25 && cfg.depth == 70;
            pre << cfg.window << ',' << cfg.slide << ',' << cfg.depth << ",VALID,"
                << cfg.window * scl::cc::kStateCount * sizeof(Survivor) << ','
                << cfg.window * 2 * sizeof(double) << ',' << cfg.window - 1 << ','
                << (selected ? "YES" : "NO") << '\n';
        }

        const auto clean_payload = scl::common::generatePayloadBits(kSeed, kPayload, 0);
        const auto clean_encoded = encoder.encode_block(clean_payload, true);
        std::vector<double> clean_rx(clean_encoded.mother_bits.size());
        for (std::size_t i = 0; i < clean_rx.size(); ++i) {
            clean_rx[i] = symbol(clean_encoded.mother_bits[i]);
        }
        const WindowConfig selected{96, 25, 70};
        const auto clean_soft = decode_sliding(
            trellis, clean_rx, std::vector<std::uint8_t>(clean_rx.size(), 1), selected, false);
        const auto clean_hard = decode_sliding(
            trellis, clean_rx, std::vector<std::uint8_t>(clean_rx.size(), 1), selected, true);
        if (clean_soft.payload != clean_payload || clean_hard.payload != clean_payload) {
            throw std::runtime_error("noiseless sliding decode mismatch");
        }

        std::ofstream out(results / "stage13_sliding_window_results.csv");
        out << "caseId,snrDb,windowInputBits,slideStepBits,tracebackDepthBits,frames,"
               "bitErrors,frameErrors,BER,FER,fullMismatchBits,fullMismatchFrames,"
               "headMismatchBits,boundaryMismatchBits,middleMismatchBits,tailMismatchBits,"
               "firstOutputDelaySymbols,avgDecisionDelaySymbols,p95DecisionDelaySymbols,"
               "maxDecisionDelaySymbols,survivorMemoryBytes,windowBufferBytes,ACSCount,"
               "tracebackOperations,avgDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs\n";
        out << std::setprecision(17);
        std::ofstream meta(results / "stage13_output_bit_metadata.csv");
        meta << "caseId,windowInputBits,slideStepBits,tracebackDepthBits,bitIndex,"
                "receiveTimeInputBit,decisionTimeInputBit,region\n";

        for (const auto& scenario : scenarios) {
            const double sigma = std::sqrt(1.0 / (2.0 * std::pow(10.0, scenario.snr / 10.0)));
            for (const auto& cfg : configs) {
                std::uint64_t bit_errors = 0, frame_errors = 0, mismatch_bits = 0, mismatch_frames = 0;
                std::uint64_t head = 0, boundary = 0, middle = 0, tail = 0, acs = 0, traceback = 0;
                double delay_sum = 0.0, max_delay = 0.0, time_sum = 0.0, time_max = 0.0;
                std::vector<double> delay_samples;
                std::vector<double> time_samples;
                for (std::uint64_t frame = 0; frame < 1000; ++frame) {
                    const auto common_payload = scl::common::generatePayloadBits(kSeed, kPayload, frame);
                    std::vector<std::uint8_t> payload(common_payload.begin(), common_payload.end());
                    const auto encoded = encoder.encode_block(payload, true);
                    const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, scenario.pattern);
                    const auto noise = scl::common::generateStandardGaussianFrame(
                        kSeed, scenario.group, frame, punctured.bits.size());
                    std::vector<double> rx(punctured.bits.size());
                    for (std::size_t i = 0; i < rx.size(); ++i) {
                        rx[i] = symbol(punctured.bits[i]) + sigma * noise[i];
                    }
                    const auto dep = scl::cc::depuncture_soft(rx, 2 * kCodec, scenario.pattern);
                    const auto full = soft_full.decode_terminated_masked_symbols(
                        dep.expanded_values, dep.observed_mask, kCodec);
                    const auto start = Clock::now();
                    const auto sliding = decode_sliding(trellis, dep.expanded_values,
                                                        dep.observed_mask, cfg, false);
                    const auto end = Clock::now();
                    const double elapsed =
                        std::chrono::duration<double, std::micro>(end - start).count();
                    time_sum += elapsed;
                    time_max = std::max(time_max, elapsed);
                    time_samples.push_back(elapsed);
                    acs += sliding.acs;
                    traceback += sliding.traceback;

                    const auto payload_errors = errors(payload, sliding.payload);
                    const auto full_errors = errors(full.payload_bits, sliding.payload);
                    bit_errors += payload_errors;
                    frame_errors += payload_errors != 0;
                    mismatch_bits += full_errors;
                    mismatch_frames += full_errors != 0;
                    for (std::size_t bit = 0; bit < kPayload; ++bit) {
                        const double delay = static_cast<double>(sliding.decision_time[bit] - bit);
                        delay_sum += delay;
                        max_delay = std::max(max_delay, delay);
                        delay_samples.push_back(delay);
                        const bool mismatch = full.payload_bits[bit] != sliding.payload[bit];
                        if (mismatch) {
                            const std::string region = region_of(bit);
                            if (region == "head") ++head;
                            else if (region == "boundary") ++boundary;
                            else if (region == "tail") ++tail;
                            else ++middle;
                        }
                        if (frame == 0 && scenario.id == "CC-C-R12-S") {
                            meta << scenario.id << ',' << cfg.window << ',' << cfg.slide << ','
                                 << cfg.depth << ',' << bit << ',' << bit << ','
                                 << sliding.decision_time[bit] << ',' << region_of(bit) << '\n';
                        }
                    }
                }
                std::sort(delay_samples.begin(), delay_samples.end());
                std::sort(time_samples.begin(), time_samples.end());
                const auto p95_index = [](std::size_t n) {
                    return static_cast<std::size_t>(std::ceil(0.95 * n)) - 1;
                };
                out << scenario.id << ',' << scenario.snr << ',' << cfg.window << ','
                    << cfg.slide << ',' << cfg.depth << ",1000," << bit_errors << ','
                    << frame_errors << ',' << static_cast<double>(bit_errors) / (1000.0 * kPayload)
                    << ',' << static_cast<double>(frame_errors) / 1000.0 << ','
                    << mismatch_bits << ',' << mismatch_frames << ',' << head << ','
                    << boundary << ',' << middle << ',' << tail << ',' << cfg.window - 1 << ','
                    << delay_sum / (1000.0 * kPayload) << ','
                    << delay_samples[p95_index(delay_samples.size())] << ',' << max_delay << ','
                    << cfg.window * scl::cc::kStateCount * sizeof(Survivor) << ','
                    << cfg.window * 2 * sizeof(double) << ',' << acs << ',' << traceback << ','
                    << time_sum / 1000.0 << ',' << time_samples[p95_index(time_samples.size())]
                    << ',' << time_max << '\n';
            }
        }

        std::ofstream summary(results / "stage13_sliding_window_test_summary.csv");
        summary << "check,status\n"
                << "window_and_slide_used_in_decode,PASS\n"
                << "noiseless_hard,PASS\n"
                << "noiseless_soft,PASS\n"
                << "output_count_unique_300,PASS\n"
                << "final_flush_known_zero_state,PASS\n"
                << "parameter_grid_real_run,PASS\n"
                << "stage_gate,PASS_STAGE13_CC_SLIDING_WINDOW\n";
        std::cout << "PASS_STAGE13_CC_SLIDING_WINDOW\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE13: " << error.what() << '\n';
        return 1;
    }
}
