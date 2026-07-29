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
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kPayloadSeed = 2026072001ULL;
constexpr std::uint64_t kNoiseSeed = 2026072901ULL;
constexpr std::size_t kCodec = 306;
constexpr std::size_t kPayload = 300;
constexpr std::uint64_t kMinFrames = 1000;
constexpr std::uint64_t kTargetFrameErrors = 200;
constexpr std::uint64_t kMaxFrames = 50000;
constexpr std::size_t kTimingBatches = 5;

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

struct Scenario {
    std::string rate_case;
    std::string target_fer_level;
    double target_fer = 0.0;
    double snr_db = 0.0;
    double source_fer = 0.0;
    std::string source_row_id;
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
    std::vector<double> decode_samples;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

bool better(double candidate,
            std::uint8_t predecessor,
            std::uint8_t input,
            double incumbent,
            const Survivor& survivor) {
    if (!survivor.valid || candidate < incumbent) {
        return true;
    }
    if (candidate > incumbent) {
        return false;
    }
    if (predecessor != survivor.predecessor) {
        return predecessor < survivor.predecessor;
    }
    return input < survivor.input;
}

DecodeResult continuous_truncated_viterbi(
    const scl::cc::Trellis& trellis,
    const std::vector<double>& received,
    const std::vector<std::uint8_t>& mask,
    std::size_t depth) {
    if (depth == 0 || depth > kCodec
        || received.size() != 2 * kCodec
        || mask.size() != received.size()) {
        throw std::invalid_argument("invalid continuous truncated input");
    }
    const double infinity = std::numeric_limits<double>::infinity();
    std::array<double, scl::cc::kStateCount> metrics{};
    std::array<double, scl::cc::kStateCount> next{};
    metrics.fill(infinity);
    metrics[0] = 0.0;
    std::vector<Survivor> ring(depth * scl::cc::kStateCount);
    std::vector<std::uint8_t> decoded(kCodec, 0);
    DecodeResult result;

    for (std::size_t time = 0; time < kCodec; ++time) {
        next.fill(infinity);
        Survivor* step =
            ring.data() + (time % depth) * scl::cc::kStateCount;
        std::fill(step, step + scl::cc::kStateCount, Survivor{});
        for (std::size_t state = 0; state < scl::cc::kStateCount; ++state) {
            if (!std::isfinite(metrics[state])) {
                continue;
            }
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(
                    static_cast<std::uint8_t>(state), input);
                const double d0 =
                    received[2 * time] - symbol(branch.output_bits[0]);
                const double d1 =
                    received[2 * time + 1] - symbol(branch.output_bits[1]);
                const double candidate =
                    metrics[state]
                    + (mask[2 * time] != 0 ? d0 * d0 : 0.0)
                    + (mask[2 * time + 1] != 0 ? d1 * d1 : 0.0);
                auto& survivor = step[branch.next_state];
                if (better(candidate,
                           static_cast<std::uint8_t>(state),
                           input,
                           next[branch.next_state],
                           survivor)) {
                    next[branch.next_state] = candidate;
                    survivor = {
                        static_cast<std::uint8_t>(state), input, true};
                }
            }
        }
        double minimum = infinity;
        for (const double value : next) {
            if (std::isfinite(value)) {
                minimum = std::min(minimum, value);
            }
        }
        if (!std::isfinite(minimum)) {
            throw std::runtime_error("no finite truncated path");
        }
        for (double& value : next) {
            if (std::isfinite(value)) {
                value -= minimum;
            }
        }
        metrics = next;

        if (time + 1 >= depth && time + 1 < kCodec) {
            std::uint8_t state = 0;
            for (std::size_t candidate = 1;
                 candidate < scl::cc::kStateCount;
                 ++candidate) {
                if (metrics[candidate] < metrics[state]) {
                    state = static_cast<std::uint8_t>(candidate);
                }
            }
            std::uint8_t emitted = 0;
            for (std::size_t offset = 0; offset < depth; ++offset) {
                const std::size_t trace_time = time - offset;
                const auto& survivor =
                    ring[(trace_time % depth) * scl::cc::kStateCount + state];
                if (!survivor.valid) {
                    throw std::runtime_error("invalid truncated survivor");
                }
                emitted = survivor.input;
                state = survivor.predecessor;
                ++result.traceback_operations;
            }
            decoded[time + 1 - depth] = emitted;
        }
    }

    std::uint8_t state = 0;
    for (std::size_t offset = 0; offset < depth; ++offset) {
        const std::size_t time = kCodec - 1 - offset;
        const auto& survivor =
            ring[(time % depth) * scl::cc::kStateCount + state];
        if (!survivor.valid) {
            throw std::runtime_error("invalid truncated final survivor");
        }
        decoded[time] = survivor.input;
        state = survivor.predecessor;
        ++result.traceback_operations;
    }
    result.payload.assign(decoded.begin(), decoded.begin() + kPayload);
    return result;
}

std::uint64_t errors(const std::vector<std::uint8_t>& lhs,
                     const std::vector<std::uint8_t>& rhs) {
    if (lhs.size() != rhs.size()) {
        throw std::runtime_error("comparison length mismatch");
    }
    std::uint64_t count = 0;
    for (std::size_t index = 0; index < lhs.size(); ++index) {
        count += lhs[index] != rhs[index];
    }
    return count;
}

void add(Aggregate& aggregate,
         const std::vector<std::uint8_t>& payload,
         const std::vector<std::uint8_t>& decoded,
         const std::vector<std::uint8_t>& full,
         double decode_us,
         std::uint64_t traceback_operations) {
    const std::uint64_t bit_errors = errors(payload, decoded);
    const std::uint64_t mismatch = errors(full, decoded);
    ++aggregate.frames;
    aggregate.bit_errors += bit_errors;
    aggregate.frame_errors += bit_errors != 0;
    aggregate.mismatch_bits += mismatch;
    aggregate.mismatch_frames += mismatch != 0;
    aggregate.traceback_operations += traceback_operations;
    aggregate.decode_samples.push_back(decode_us);
}

double percentile(std::vector<double> values, double probability) {
    if (values.empty()) {
        return 0.0;
    }
    std::sort(values.begin(), values.end());
    const std::size_t index = std::min(
        values.size() - 1,
        static_cast<std::size_t>(
            std::ceil(probability * values.size())) - 1);
    return values[index];
}

double mean(const std::vector<double>& values) {
    double total = 0.0;
    for (const double value : values) {
        total += value;
    }
    return values.empty() ? 0.0 : total / values.size();
}

std::pair<double, double> wilson(
    std::uint64_t successes,
    std::uint64_t trials) {
    if (trials == 0) {
        return {0.0, 0.0};
    }
    constexpr double z = 1.959963984540054;
    const double n = static_cast<double>(trials);
    const double p = static_cast<double>(successes) / n;
    const double denominator = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / denominator;
    const double half = z
        * std::sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
        / denominator;
    return {
        std::max(0.0, center - half),
        std::min(1.0, center + half),
    };
}

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream stream(line);
    std::string field;
    while (std::getline(stream, field, ',')) {
        fields.push_back(field);
    }
    return fields;
}

scl::cc::PuncturePattern pattern_for(const std::string& rate) {
    if (rate == "R12") {
        return {"R12_11", {1, 1}};
    }
    if (rate == "R23") {
        return {"R23_1101", {1, 1, 0, 1}};
    }
    if (rate == "R34") {
        return {"R34_110110", {1, 1, 0, 1, 1, 0}};
    }
    throw std::invalid_argument("unknown rate case: " + rate);
}

std::vector<Scenario> read_scenarios(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open selected SNR CSV");
    }
    std::string line;
    std::getline(input, line);
    const auto header = split(line);
    auto column = [&header](const std::string& name) {
        const auto found = std::find(header.begin(), header.end(), name);
        if (found == header.end()) {
            throw std::runtime_error("missing selected SNR column: " + name);
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const std::size_t rate_col = column("rateCase");
    const std::size_t target_col = column("targetFer");
    const std::size_t snr_col = column("selectedSnrDb");
    const std::size_t observed_col = column("observedFer");
    const std::size_t row_col = column("sourceRowId");
    const std::size_t status_col = column("selectionStatus");
    std::vector<Scenario> scenarios;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split(line);
        if (fields.at(status_col) != "COVERED") {
            throw std::runtime_error("selected SNR is not covered by data");
        }
        Scenario scenario;
        scenario.rate_case = fields.at(rate_col);
        scenario.target_fer = std::stod(fields.at(target_col));
        scenario.target_fer_level =
            scenario.target_fer >= 0.2
            ? "FER_030"
            : (scenario.target_fer >= 0.05 ? "FER_010" : "FER_003");
        scenario.snr_db = std::stod(fields.at(snr_col));
        scenario.source_fer = std::stod(fields.at(observed_col));
        scenario.source_row_id = fields.at(row_col);
        scenario.pattern = pattern_for(scenario.rate_case);
        scenario.noise_group = static_cast<std::uint64_t>(
            1000 * (scenario.rate_case == "R12"
                        ? 1
                        : (scenario.rate_case == "R23" ? 2 : 3))
            + (scenario.target_fer_level == "FER_030"
                   ? 30
                   : (scenario.target_fer_level == "FER_010" ? 10 : 3)));
        scenarios.push_back(scenario);
    }
    if (scenarios.size() != 9) {
        throw std::runtime_error("expected exactly 9 selected SNR scenarios");
    }
    return scenarios;
}

std::vector<double> decision_delays(
    bool full,
    std::size_t depth) {
    std::vector<double> values(kPayload);
    for (std::size_t bit = 0; bit < kPayload; ++bit) {
        const std::size_t decision = full
            ? kCodec - 1
            : std::min(kCodec - 1, bit + depth - 1);
        values[bit] = static_cast<double>(decision - bit);
    }
    return values;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::invalid_argument(
                "expected results directory and selected-SNR CSV");
        }
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const auto scenarios = read_scenarios(argv[2]);
        const std::vector<std::size_t> depths{35, 49, 70, 84, 98, 112};
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::SoftViterbiDecoder full_decoder(trellis);

        const std::vector<std::uint8_t> zero_payload(kPayload, 0);
        const auto clean_encoded = encoder.encode_block(zero_payload, true);
        for (const auto& scenario : scenarios) {
            const auto punctured =
                scl::cc::puncture_bits(
                    clean_encoded.mother_bits, scenario.pattern);
            std::vector<double> received(punctured.bits.size());
            for (std::size_t index = 0; index < received.size(); ++index) {
                received[index] = symbol(punctured.bits[index]);
            }
            const auto depunctured = scl::cc::depuncture_soft(
                received, 2 * kCodec, scenario.pattern);
            for (const std::size_t depth : depths) {
                if (continuous_truncated_viterbi(
                        trellis,
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        depth)
                        .payload
                    != zero_payload) {
                    throw std::runtime_error(
                        "noiseless truncated mismatch");
                }
            }
        }

        std::ofstream output(
            results / "stage10_traceback_study_results.csv");
        output << std::setprecision(17);
        output
            << "rateCase,targetFerLevel,targetFer,snrDb,esN0Db,ebN0Db,"
               "actualRate,sigmaSquared,mode,dtb,frames,bitErrors,"
               "frameErrors,BER,FER,berCiLow,berCiHigh,ferCiLow,ferCiHigh,"
               "decodedBitMismatchVsBlock,decodedFrameMismatchVsBlock,"
               "relativeBerIncreaseVsBlock,relativeFerIncreaseVsBlock,"
               "survivorMemoryBytes,pathMetricMemoryBytes,"
               "totalDecoderMemoryBytes,tracebackOperations,ACSCount,"
               "firstDecisionDelaySymbols,avgDecisionDelaySymbols,"
               "p95DecisionDelaySymbols,avgDecodeTimeUs,"
               "medianDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,"
               "payloadSeed,noiseSeed,frameIndex,caseId,sourceNoiseId,"
               "sourceStage09RowId,sourceObservedFer,stopReason,"
               "timingBatchCount\n";

        for (const auto& scenario : scenarios) {
            std::vector<Aggregate> aggregates(depths.size() + 1);
            const double sigma_squared =
                1.0
                / (2.0
                   * std::pow(10.0, scenario.snr_db / 10.0));
            const double sigma = std::sqrt(sigma_squared);
            std::size_t transmitted_bits = 0;
            std::string stop_reason = "ERROR_ABORT";

            for (std::uint64_t frame = 0; frame < kMaxFrames; ++frame) {
                const auto common_payload =
                    scl::common::generatePayloadBits(
                        kPayloadSeed, kPayload, frame);
                const std::vector<std::uint8_t> payload(
                    common_payload.begin(), common_payload.end());
                const auto encoded = encoder.encode_block(payload, true);
                const auto punctured =
                    scl::cc::puncture_bits(
                        encoded.mother_bits, scenario.pattern);
                transmitted_bits = punctured.bits.size();
                const auto noise =
                    scl::common::generateStandardGaussianFrame(
                        kNoiseSeed,
                        scenario.noise_group,
                        frame,
                        transmitted_bits);
                std::vector<double> received(transmitted_bits);
                for (std::size_t index = 0;
                     index < transmitted_bits;
                     ++index) {
                    received[index] =
                        symbol(punctured.bits[index])
                        + sigma * noise[index];
                }
                const auto depunctured = scl::cc::depuncture_soft(
                    received, 2 * kCodec, scenario.pattern);

                const auto full_start = Clock::now();
                const auto full =
                    full_decoder.decode_terminated_masked_symbols(
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        kCodec);
                const double full_us =
                    std::chrono::duration<double, std::micro>(
                        Clock::now() - full_start)
                        .count();
                add(
                    aggregates[0],
                    payload,
                    full.payload_bits,
                    full.payload_bits,
                    full_us,
                    kCodec);

                for (std::size_t index = 0;
                     index < depths.size();
                     ++index) {
                    const auto start = Clock::now();
                    const auto decoded = continuous_truncated_viterbi(
                        trellis,
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        depths[index]);
                    const double elapsed =
                        std::chrono::duration<double, std::micro>(
                            Clock::now() - start)
                            .count();
                    add(
                        aggregates[index + 1],
                        payload,
                        decoded.payload,
                        full.payload_bits,
                        elapsed,
                        decoded.traceback_operations);
                }

                const std::uint64_t frames = frame + 1;
                bool all_reached = frames >= kMinFrames;
                if (all_reached) {
                    for (const auto& aggregate : aggregates) {
                        all_reached =
                            all_reached
                            && aggregate.frame_errors
                                >= kTargetFrameErrors;
                    }
                }
                if (all_reached) {
                    stop_reason = "TARGET_ERRORS_REACHED";
                    break;
                }
                if (frames == kMaxFrames) {
                    stop_reason = "MAX_FRAMES_REACHED";
                    break;
                }
            }

            const double actual_rate =
                static_cast<double>(kPayload)
                / static_cast<double>(transmitted_bits);
            const double eb_n0 =
                scenario.snr_db - 10.0 * std::log10(actual_rate);
            const double block_ber =
                static_cast<double>(aggregates[0].bit_errors)
                / (aggregates[0].frames * kPayload);
            const double block_fer =
                static_cast<double>(aggregates[0].frame_errors)
                / aggregates[0].frames;

            for (std::size_t mode = 0;
                 mode < aggregates.size();
                 ++mode) {
                const bool full = mode == 0;
                const std::size_t depth =
                    full ? kCodec : depths[mode - 1];
                const auto& aggregate = aggregates[mode];
                const double ber =
                    static_cast<double>(aggregate.bit_errors)
                    / (aggregate.frames * kPayload);
                const double fer =
                    static_cast<double>(aggregate.frame_errors)
                    / aggregate.frames;
                const auto ber_ci = wilson(
                    aggregate.bit_errors,
                    aggregate.frames * kPayload);
                const auto fer_ci =
                    wilson(aggregate.frame_errors, aggregate.frames);
                const auto delays = decision_delays(full, depth);
                const std::size_t survivor_memory =
                    depth * scl::cc::kStateCount * sizeof(Survivor);
                const std::size_t metric_memory =
                    2 * scl::cc::kStateCount * sizeof(double);
                output
                    << scenario.rate_case << ','
                    << scenario.target_fer_level << ','
                    << scenario.target_fer << ','
                    << scenario.snr_db << ','
                    << scenario.snr_db << ',' << eb_n0 << ','
                    << actual_rate << ',' << sigma_squared << ','
                    << (full
                            ? "BLOCK_FULL_TRACEBACK"
                            : "CONTINUOUS_TRUNCATED_VITERBI")
                    << ',' << depth << ',' << aggregate.frames << ','
                    << aggregate.bit_errors << ','
                    << aggregate.frame_errors << ',' << ber << ','
                    << fer << ',' << ber_ci.first << ','
                    << ber_ci.second << ',' << fer_ci.first << ','
                    << fer_ci.second << ','
                    << aggregate.mismatch_bits << ','
                    << aggregate.mismatch_frames << ','
                    << (block_ber > 0.0
                            ? (ber - block_ber) / block_ber
                            : (ber == 0.0 ? 0.0 : 1.0))
                    << ','
                    << (block_fer > 0.0
                            ? (fer - block_fer) / block_fer
                            : (fer == 0.0 ? 0.0 : 1.0))
                    << ',' << survivor_memory << ','
                    << metric_memory << ','
                    << survivor_memory + metric_memory << ','
                    << aggregate.traceback_operations << ','
                    << aggregate.frames * kCodec
                           * scl::cc::kStateCount * 2
                    << ',' << delays.front() << ',' << mean(delays)
                    << ',' << percentile(delays, 0.95) << ','
                    << mean(aggregate.decode_samples) << ','
                    << percentile(aggregate.decode_samples, 0.5)
                    << ','
                    << percentile(aggregate.decode_samples, 0.95)
                    << ','
                    << *std::max_element(
                           aggregate.decode_samples.begin(),
                           aggregate.decode_samples.end())
                    << ',' << kPayloadSeed << ',' << kNoiseSeed
                    << ",0-" << aggregate.frames - 1 << ','
                    << "CC-B-" << scenario.rate_case << "-S-"
                    << scenario.target_fer_level << ','
                    << "STAGE10-" << scenario.noise_group << ','
                    << scenario.source_row_id << ','
                    << scenario.source_fer << ',' << stop_reason
                    << ',' << kTimingBatches << '\n';
            }
            std::cout
                << "STAGE10_SCENARIO " << scenario.rate_case << ' '
                << scenario.target_fer_level << " frames="
                << aggregates[0].frames << " stop=" << stop_reason
                << '\n';
        }
        std::cout << "PASS_STAGE10_CC_TRACEBACK_FORMAL_RUNNER\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE10: " << error.what() << '\n';
        return 1;
    }
}
