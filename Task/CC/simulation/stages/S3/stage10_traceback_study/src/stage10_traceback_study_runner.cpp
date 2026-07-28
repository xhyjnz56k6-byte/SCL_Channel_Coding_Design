#include "cc/block_encoder.hpp"
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
constexpr std::size_t kCodecInputLength = 306;
constexpr std::size_t kPayloadLength = 300;

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

struct Scenario {
    std::string case_id;
    double snr_db = 0;
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
};

struct DecodeResult {
    std::vector<std::uint8_t> payload;
    std::uint64_t traceback_operations = 0;
};

struct Aggregate {
    std::uint64_t frames = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t mismatch_bits = 0;
    std::uint64_t mismatch_frames = 0;
    std::uint64_t traceback_operations = 0;
    std::uint64_t stable_depth_sum = 0;
    double decode_us_sum = 0;
    double decode_us_max = 0;
    std::vector<double> decode_samples;
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

DecodeResult decode_finite(
    const scl::cc::Trellis& trellis,
    const std::vector<double>& received,
    const std::vector<std::uint8_t>& mask,
    std::size_t depth) {
    if (depth == 0 || depth > kCodecInputLength) {
        throw std::invalid_argument("traceback depth outside [1, 306]");
    }
    if (received.size() != 2 * kCodecInputLength || mask.size() != received.size()) {
        throw std::invalid_argument("finite traceback input length mismatch");
    }
    for (double value : received) {
        if (!std::isfinite(value)) throw std::invalid_argument("non-finite received symbol");
    }
    const double infinity = std::numeric_limits<double>::infinity();
    std::array<double, scl::cc::kStateCount> metrics{};
    std::array<double, scl::cc::kStateCount> next{};
    metrics.fill(infinity);
    metrics[0] = 0;
    std::vector<Survivor> ring(depth * scl::cc::kStateCount);
    std::vector<std::uint8_t> decoded(kCodecInputLength, 0);
    DecodeResult result;

    for (std::size_t time = 0; time < kCodecInputLength; ++time) {
        next.fill(infinity);
        Survivor* step = ring.data() + (time % depth) * scl::cc::kStateCount;
        std::fill(step, step + scl::cc::kStateCount, Survivor{});
        for (std::size_t state = 0; state < scl::cc::kStateCount; ++state) {
            if (!std::isfinite(metrics[state])) continue;
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(static_cast<std::uint8_t>(state), input);
                const double d0 = received[2 * time] - symbol(branch.output_bits[0]);
                const double d1 = received[2 * time + 1] - symbol(branch.output_bits[1]);
                const double candidate = metrics[state] +
                    (mask[2 * time] != 0 ? d0 * d0 : 0.0) +
                    (mask[2 * time + 1] != 0 ? d1 * d1 : 0.0);
                auto& survivor = step[branch.next_state];
                if (better(candidate, static_cast<std::uint8_t>(state), input,
                           next[branch.next_state], survivor)) {
                    next[branch.next_state] = candidate;
                    survivor.predecessor = static_cast<std::uint8_t>(state);
                    survivor.input = input;
                    survivor.valid = true;
                }
            }
        }
        double minimum = infinity;
        for (double value : next) minimum = std::min(minimum, value);
        if (!std::isfinite(minimum)) throw std::runtime_error("no reachable finite state");
        for (double& value : next) {
            if (std::isfinite(value)) value -= minimum;
        }
        metrics = next;

        if (time + 1 >= depth && time + 1 < kCodecInputLength) {
            std::uint8_t state = 0;
            double best_metric = infinity;
            for (std::size_t candidate = 0; candidate < scl::cc::kStateCount; ++candidate) {
                if (metrics[candidate] < best_metric) {
                    best_metric = metrics[candidate];
                    state = static_cast<std::uint8_t>(candidate);
                }
            }
            std::uint8_t emitted = 0;
            for (std::size_t offset = 0; offset < depth; ++offset) {
                const std::size_t trace_time = time - offset;
                const auto& survivor =
                    ring[(trace_time % depth) * scl::cc::kStateCount + state];
                if (!survivor.valid) throw std::runtime_error("invalid finite survivor");
                emitted = survivor.input;
                state = survivor.predecessor;
                ++result.traceback_operations;
            }
            decoded[time + 1 - depth] = emitted;
        }
    }

    std::uint8_t state = 0;
    for (std::size_t offset = 0; offset < depth; ++offset) {
        const std::size_t time = kCodecInputLength - 1 - offset;
        const auto& survivor = ring[(time % depth) * scl::cc::kStateCount + state];
        if (!survivor.valid) throw std::runtime_error("invalid final finite survivor");
        decoded[time] = survivor.input;
        state = survivor.predecessor;
        ++result.traceback_operations;
    }
    result.payload.assign(decoded.begin(), decoded.begin() + kPayloadLength);
    return result;
}

std::uint64_t errors(const std::vector<std::uint8_t>& left,
                     const std::vector<std::uint8_t>& right) {
    if (left.size() != right.size()) throw std::runtime_error("comparison length mismatch");
    std::uint64_t count = 0;
    for (std::size_t i = 0; i < left.size(); ++i) count += left[i] != right[i];
    return count;
}

double p95(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return values[static_cast<std::size_t>(std::ceil(0.95 * values.size())) - 1];
}

void add(Aggregate& aggregate, const std::vector<std::uint8_t>& payload,
         const std::vector<std::uint8_t>& decoded,
         const std::vector<std::uint8_t>& full,
         double decode_us, std::uint64_t operations, std::size_t stable_depth) {
    const auto bit_errors = errors(payload, decoded);
    const auto mismatch = errors(full, decoded);
    ++aggregate.frames;
    aggregate.bit_errors += bit_errors;
    aggregate.frame_errors += bit_errors != 0;
    aggregate.mismatch_bits += mismatch;
    aggregate.mismatch_frames += mismatch != 0;
    aggregate.traceback_operations += operations;
    aggregate.stable_depth_sum += stable_depth;
    aggregate.decode_us_sum += decode_us;
    aggregate.decode_us_max = std::max(aggregate.decode_us_max, decode_us);
    aggregate.decode_samples.push_back(decode_us);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const std::vector<std::size_t> depths = {35, 49, 70};
        const std::vector<Scenario> scenarios = {
            {"CC-B-R12-S", -0.5, {"R12_11", {1, 1}}, 1200},
            {"CC-B-R12-S", 0.0, {"R12_11", {1, 1}}, 1200},
            {"CC-B-R23-S", 0.5, {"R23_B_1101", {1, 1, 0, 1}}, 2300},
            {"CC-B-R23-S", 1.0, {"R23_B_1101", {1, 1, 0, 1}}, 2300}
        };
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::SoftViterbiDecoder full_decoder(trellis);

        {
            const std::vector<std::uint8_t> zero_payload(kPayloadLength, 0);
            const auto encoded = encoder.encode_block(zero_payload, true);
            for (const auto& scenario : scenarios) {
                const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, scenario.pattern);
                std::vector<double> received(punctured.bits.size());
                for (std::size_t i = 0; i < received.size(); ++i) {
                    received[i] = punctured.bits[i] == 0 ? 1.0 : -1.0;
                }
                const auto depunctured = scl::cc::depuncture_soft(
                    received, 2 * kCodecInputLength, scenario.pattern);
                for (auto depth : depths) {
                    if (decode_finite(trellis, depunctured.expanded_values,
                                      depunctured.observed_mask, depth).payload != zero_payload) {
                        throw std::runtime_error("noiseless finite traceback mismatch");
                    }
                }
            }
        }

        std::ofstream out(results / "stage10_traceback_study_results.csv");
        out << "caseId,snrDb,mode,Dtb,frames,payloadBitErrors,payloadErrorFrames,BER,FER,"
               "fullMismatchBits,fullMismatchFrames,avgDecodeTime_us,p95DecodeTime_us,"
               "maxDecodeTime_us,survivorMemoryBytes,tracebackOperations,"
               "firstStableOutputDepth\n";
        out << std::setprecision(17);
        for (const auto& scenario : scenarios) {
            std::array<Aggregate, 4> aggregates;
            const double sigma = std::sqrt(1.0 / (2.0 * std::pow(10.0, scenario.snr_db / 10.0)));
            for (std::uint64_t frame = 0; frame < 1000; ++frame) {
                const auto common_payload = scl::common::generatePayloadBits(kSeed, kPayloadLength, frame);
                std::vector<std::uint8_t> payload(common_payload.begin(), common_payload.end());
                const auto encoded = encoder.encode_block(payload, true);
                const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, scenario.pattern);
                const auto noise = scl::common::generateStandardGaussianFrame(
                    kSeed, scenario.noise_group, frame, punctured.bits.size());
                std::vector<double> received(punctured.bits.size());
                for (std::size_t i = 0; i < received.size(); ++i) {
                    received[i] = (punctured.bits[i] == 0 ? 1.0 : -1.0) + sigma * noise[i];
                }
                const auto depunctured = scl::cc::depuncture_soft(
                    received, 2 * kCodecInputLength, scenario.pattern);

                const auto full_start = Clock::now();
                const auto full = full_decoder.decode_terminated_masked_symbols(
                    depunctured.expanded_values, depunctured.observed_mask, kCodecInputLength);
                const auto full_end = Clock::now();
                std::array<DecodeResult, 3> finite;
                std::array<double, 3> finite_us{};
                for (std::size_t i = 0; i < depths.size(); ++i) {
                    const auto start = Clock::now();
                    finite[i] = decode_finite(
                        trellis, depunctured.expanded_values, depunctured.observed_mask, depths[i]);
                    const auto end = Clock::now();
                    finite_us[i] =
                        std::chrono::duration<double, std::micro>(end - start).count();
                }
                std::size_t first_stable = kCodecInputLength;
                for (std::size_t i = 0; i < depths.size(); ++i) {
                    if (finite[i].payload == full.payload_bits) {
                        first_stable = depths[i];
                        break;
                    }
                }
                add(aggregates[0], payload, full.payload_bits, full.payload_bits,
                    std::chrono::duration<double, std::micro>(full_end - full_start).count(),
                    kCodecInputLength, first_stable);
                for (std::size_t i = 0; i < depths.size(); ++i) {
                    add(aggregates[i + 1], payload, finite[i].payload, full.payload_bits,
                        finite_us[i], finite[i].traceback_operations, first_stable);
                }
            }

            for (std::size_t mode = 0; mode < aggregates.size(); ++mode) {
                const auto& value = aggregates[mode];
                const bool full = mode == 0;
                const std::size_t depth = full ? kCodecInputLength : depths[mode - 1];
                out << scenario.case_id << ',' << scenario.snr_db << ','
                    << (full ? "FULL_BLOCK_ZERO_TERMINATED" : "FINITE_TRACEBACK") << ','
                    << depth << ',' << value.frames << ',' << value.bit_errors << ','
                    << value.frame_errors << ','
                    << static_cast<double>(value.bit_errors) / (value.frames * kPayloadLength) << ','
                    << static_cast<double>(value.frame_errors) / value.frames << ','
                    << value.mismatch_bits << ',' << value.mismatch_frames << ','
                    << value.decode_us_sum / value.frames << ',' << p95(value.decode_samples) << ','
                    << value.decode_us_max << ','
                    << depth * scl::cc::kStateCount * sizeof(Survivor) << ','
                    << value.traceback_operations << ','
                    << static_cast<double>(value.stable_depth_sum) / value.frames << '\n';
            }
        }
        std::cout << "PASS_STAGE10_CC_TRACEBACK_STUDY_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE10: " << error.what() << '\n';
        return 1;
    }
}
