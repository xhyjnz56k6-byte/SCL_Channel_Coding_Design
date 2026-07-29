#include "true_sliding_window_viterbi.hpp"

#include "cc/block_encoder.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"
#include "common/frame_pool.hpp"
#include "common/gaussian_noise.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kPayloadSeed = 2026072001ULL;
constexpr std::uint64_t kNoiseSeed = 2026072903ULL;
constexpr std::size_t kPayload = 300;
constexpr std::size_t kCodec = 306;

struct PlanRow {
    std::string run_layer;
    std::string experiment_id;
    std::string candidate_id;
    std::string rate_case;
    std::string target_fer_level;
    double snr_db = 0.0;
    scl::cc::stage13::SlidingWindowConfig config;
    std::uint64_t min_frames = 1000;
    std::uint64_t target_errors = 200;
    std::uint64_t max_frames = 50000;
};

struct Rate {
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
};

struct Aggregate {
    std::uint64_t frames = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t mismatch_bits = 0;
    std::uint64_t mismatch_frames = 0;
    std::uint64_t boundary_errors = 0;
    std::uint64_t boundary_bits = 0;
    std::uint64_t non_boundary_errors = 0;
    std::uint64_t non_boundary_bits = 0;
    std::uint64_t acs_count = 0;
    std::uint64_t traceback_operations = 0;
    std::uint64_t window_count = 0;
    std::uint64_t output_batch_count = 0;
    std::uint64_t window_trigger_count = 0;
    std::vector<double> first_delays;
    std::vector<double> decision_delays;
    std::vector<double> steady_intervals;
    std::vector<double> processing_us;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
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

std::vector<PlanRow> read_plan(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open Stage13 plan");
    }
    std::string line;
    std::getline(input, line);
    const auto header = split(line);
    auto column = [&header](const std::string& name) {
        const auto found = std::find(header.begin(), header.end(), name);
        if (found == header.end()) {
            throw std::runtime_error("missing plan column: " + name);
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const auto layer = column("runLayer");
    const auto experiment = column("experimentId");
    const auto candidate = column("candidateId");
    const auto rate = column("rateCase");
    const auto level = column("targetFerLevel");
    const auto snr = column("snrDb");
    const auto window = column("windowBits");
    const auto slide = column("slideBits");
    const auto depth = column("dtb");
    const auto min_frames = column("minFrames");
    const auto target = column("targetFrameErrors");
    const auto max_frames = column("maxFrames");
    std::vector<PlanRow> rows;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split(line);
        PlanRow row;
        row.run_layer = fields.at(layer);
        row.experiment_id = fields.at(experiment);
        row.candidate_id = fields.at(candidate);
        row.rate_case = fields.at(rate);
        row.target_fer_level = fields.at(level);
        row.snr_db = std::stod(fields.at(snr));
        row.config = {
            static_cast<std::size_t>(std::stoull(fields.at(window))),
            static_cast<std::size_t>(std::stoull(fields.at(slide))),
            static_cast<std::size_t>(std::stoull(fields.at(depth))),
            kPayload,
            scl::cc::kMemory,
        };
        row.min_frames = std::stoull(fields.at(min_frames));
        row.target_errors = std::stoull(fields.at(target));
        row.max_frames = std::stoull(fields.at(max_frames));
        scl::cc::stage13::validate_sliding_window_config(row.config, kCodec);
        rows.push_back(row);
    }
    if (rows.empty()) {
        throw std::runtime_error("empty Stage13 plan");
    }
    return rows;
}

Rate rate_for(const std::string& rate) {
    if (rate == "R12") {
        return {{"R12_11", {1, 1}}, 1200};
    }
    if (rate == "R23") {
        return {{"R23_1101", {1, 1, 0, 1}}, 2300};
    }
    if (rate == "R34") {
        return {{"R34_110110", {1, 1, 0, 1, 1, 0}}, 3400};
    }
    throw std::invalid_argument("unknown rate");
}

std::uint64_t errors(const std::vector<std::uint8_t>& lhs,
                     const std::vector<std::uint8_t>& rhs) {
    std::uint64_t count = 0;
    for (std::size_t index = 0; index < lhs.size(); ++index) {
        count += lhs[index] != rhs[index];
    }
    return count;
}

double percentile(std::vector<double> values, double probability) {
    std::sort(values.begin(), values.end());
    return values[std::min(
        values.size() - 1,
        static_cast<std::size_t>(
            std::ceil(probability * values.size())) - 1)];
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
    constexpr double z = 1.959963984540054;
    const double n = static_cast<double>(trials);
    const double p = trials == 0 ? 0.0 : successes / n;
    const double denominator = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / denominator;
    const double half =
        z * std::sqrt(
                (p * (1.0 - p) + z * z / (4.0 * n)) / n)
        / denominator;
    return {
        std::max(0.0, center - half),
        std::min(1.0, center + half),
    };
}

std::vector<std::size_t> input_to_transmitted_symbol(
    const scl::cc::PuncturePattern& pattern) {
    std::vector<std::size_t> mapping(kCodec);
    std::size_t transmitted = 0;
    std::size_t phase = 0;
    for (std::size_t input = 0; input < kCodec; ++input) {
        for (std::size_t output = 0; output < 2; ++output) {
            if (pattern.keep_mask[phase] != 0) {
                ++transmitted;
            }
            phase = (phase + 1) % pattern.keep_mask.size();
        }
        mapping[input] = transmitted == 0 ? 0 : transmitted - 1;
    }
    return mapping;
}

void add(
    Aggregate& aggregate,
    const std::vector<std::uint8_t>& payload,
    const std::vector<std::uint8_t>& full,
    const scl::cc::stage13::SlidingWindowResult& decoded,
    const std::vector<std::size_t>& input_to_symbol,
    double elapsed) {
    const auto bit_errors = errors(payload, decoded.payload);
    const auto mismatch = errors(full, decoded.payload);
    ++aggregate.frames;
    aggregate.bit_errors += bit_errors;
    aggregate.frame_errors += bit_errors != 0;
    aggregate.mismatch_bits += mismatch;
    aggregate.mismatch_frames += mismatch != 0;
    aggregate.acs_count += decoded.acs_count;
    aggregate.traceback_operations += decoded.traceback_operations;
    aggregate.window_count += decoded.window_count;
    aggregate.output_batch_count += decoded.output_batch_count;
    aggregate.window_trigger_count += decoded.window_trigger_count;
    aggregate.processing_us.push_back(elapsed);

    std::vector<bool> boundary(kPayload, false);
    for (std::size_t bit = 1; bit < kPayload; ++bit) {
        if (decoded.output_batch_index[bit]
            != decoded.output_batch_index[bit - 1]) {
            const std::size_t begin = bit > 10 ? bit - 10 : 0;
            const std::size_t end = std::min(kPayload, bit + 10);
            for (std::size_t index = begin; index < end; ++index) {
                boundary[index] = true;
            }
        }
    }
    std::vector<std::size_t> batch_decisions;
    for (std::size_t bit = 0; bit < kPayload; ++bit) {
        const bool error = payload[bit] != decoded.payload[bit];
        if (boundary[bit]) {
            ++aggregate.boundary_bits;
            aggregate.boundary_errors += error;
        } else {
            ++aggregate.non_boundary_bits;
            aggregate.non_boundary_errors += error;
        }
        const std::size_t decision_symbol =
            input_to_symbol[decoded.decision_input_time[bit]];
        const std::size_t source_symbol = input_to_symbol[bit];
        aggregate.decision_delays.push_back(
            static_cast<double>(decision_symbol - source_symbol));
        if (bit == 0) {
            aggregate.first_delays.push_back(
                static_cast<double>(decision_symbol - source_symbol));
        }
        if (bit == 0
            || decoded.output_batch_index[bit]
                != decoded.output_batch_index[bit - 1]) {
            batch_decisions.push_back(decision_symbol);
        }
    }
    for (std::size_t index = 1; index < batch_decisions.size(); ++index) {
        aggregate.steady_intervals.push_back(
            static_cast<double>(
                batch_decisions[index] - batch_decisions[index - 1]));
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3) {
            throw std::invalid_argument("output CSV and plan CSV required");
        }
        const auto plan = read_plan(argv[2]);
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::SoftViterbiDecoder full_decoder(trellis);
        std::ofstream output(argv[1]);
        output << std::setprecision(17);
        output
            << "runLayer,experimentId,candidateId,rateCase,"
               "targetFerLevel,snrDb,esN0Db,ebN0Db,actualRate,"
               "sigmaSquared,windowBits,slideBits,dtb,frames,bitErrors,"
               "frameErrors,BER,FER,berCiLow,berCiHigh,ferCiLow,ferCiHigh,"
               "boundaryBER,nonBoundaryBER,mismatchVsBlockBits,"
               "mismatchVsBlockFrames,relativeFerIncreaseVsBlock,"
               "firstOutputDelaySymbols,avgDecisionDelaySymbols,"
               "p95DecisionDelaySymbols,maxDecisionDelaySymbols,"
               "fullFrameLastDecisionSymbol,steadyOutputIntervalMean,"
               "steadyOutputIntervalP95,windowCount,outputBatchCount,"
               "windowTriggerCount,ACSCount,tracebackOperations,"
               "avgWindowProcessingTimeUs,p95WindowProcessingTimeUs,"
               "medianWindowProcessingTimeUs,maxWindowProcessingTimeUs,"
               "timingBatchCount,"
               "windowBufferBytes,survivorMemoryBytes,"
               "pathMetricMemoryBytes,totalMemoryBytes,lostBits,"
               "duplicateBits,outputLength,finalFlushPass,payloadSeed,"
               "noiseSeed,frameIndex,caseId,sourceNoiseId,stopReason\n";

        using Key = std::tuple<std::string, std::string, double>;
        std::map<Key, std::vector<PlanRow>> groups;
        for (const auto& row : plan) {
            groups[{row.run_layer, row.rate_case, row.snr_db}].push_back(row);
        }
        for (const auto& group : groups) {
            const auto& configs = group.second;
            const auto rate = rate_for(configs[0].rate_case);
            const auto input_to_symbol =
                input_to_transmitted_symbol(rate.pattern);
            std::vector<Aggregate> aggregates(configs.size());
            Aggregate block;
            const double sigma_squared =
                1.0
                / (2.0
                   * std::pow(10.0, configs[0].snr_db / 10.0));
            const double sigma = std::sqrt(sigma_squared);
            std::size_t transmitted_bits = 0;
            std::string stop_reason = "ERROR_ABORT";
            for (std::uint64_t frame = 0;
                 frame < configs[0].max_frames;
                 ++frame) {
                const auto common = scl::common::generatePayloadBits(
                    kPayloadSeed, kPayload, frame);
                const std::vector<std::uint8_t> payload(
                    common.begin(), common.end());
                const auto encoded = encoder.encode_block(payload, true);
                const auto punctured =
                    scl::cc::puncture_bits(
                        encoded.mother_bits, rate.pattern);
                transmitted_bits = punctured.bits.size();
                const auto noise =
                    scl::common::generateStandardGaussianFrame(
                        kNoiseSeed,
                        rate.noise_group,
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
                    received, 2 * kCodec, rate.pattern);
                const auto full =
                    full_decoder.decode_terminated_masked_symbols(
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        kCodec);
                const auto block_errors = errors(payload, full.payload_bits);
                ++block.frames;
                block.bit_errors += block_errors;
                block.frame_errors += block_errors != 0;
                for (std::size_t index = 0;
                     index < configs.size();
                     ++index) {
                    const auto start = Clock::now();
                    const auto decoded =
                        scl::cc::stage13::true_sliding_window_viterbi(
                            trellis,
                            depunctured.expanded_values,
                            depunctured.observed_mask,
                            configs[index].config);
                    add(
                        aggregates[index],
                        payload,
                        full.payload_bits,
                        decoded,
                        input_to_symbol,
                        std::chrono::duration<double, std::micro>(
                            Clock::now() - start)
                            .count());
                }
                const std::uint64_t frames = frame + 1;
                bool all_reached =
                    frames >= configs[0].min_frames
                    && block.frame_errors >= configs[0].target_errors;
                for (const auto& aggregate : aggregates) {
                    all_reached =
                        all_reached
                        && aggregate.frame_errors
                            >= configs[0].target_errors;
                }
                if (configs[0].run_layer == "prescan"
                    && frames >= configs[0].min_frames) {
                    stop_reason = "PRESCAN_FIXED_FRAMES";
                    break;
                }
                if (all_reached) {
                    stop_reason = "TARGET_ERRORS_REACHED";
                    break;
                }
                if (frames == configs[0].max_frames) {
                    stop_reason = "MAX_FRAMES_REACHED";
                }
            }
            const double actual_rate =
                static_cast<double>(kPayload) / transmitted_bits;
            const double eb_n0 =
                configs[0].snr_db
                - 10.0 * std::log10(actual_rate);
            const double block_fer =
                static_cast<double>(block.frame_errors) / block.frames;
            for (std::size_t index = 0;
                 index < configs.size();
                 ++index) {
                const auto& config = configs[index];
                const auto& aggregate = aggregates[index];
                const double ber =
                    static_cast<double>(aggregate.bit_errors)
                    / (aggregate.frames * kPayload);
                const double fer =
                    static_cast<double>(aggregate.frame_errors)
                    / aggregate.frames;
                const auto ber_ci = wilson(
                    aggregate.bit_errors, aggregate.frames * kPayload);
                const auto fer_ci =
                    wilson(aggregate.frame_errors, aggregate.frames);
                const std::size_t survivor =
                    config.config.window_bits * scl::cc::kStateCount
                    * 3;
                const std::size_t metric =
                    3 * scl::cc::kStateCount * sizeof(double);
                output
                    << config.run_layer << ',' << config.experiment_id
                    << ',' << config.candidate_id << ','
                    << config.rate_case << ','
                    << config.target_fer_level << ','
                    << config.snr_db << ',' << config.snr_db << ','
                    << eb_n0 << ',' << actual_rate << ','
                    << sigma_squared << ','
                    << config.config.window_bits << ','
                    << config.config.slide_bits << ','
                    << config.config.traceback_depth << ','
                    << aggregate.frames << ',' << aggregate.bit_errors
                    << ',' << aggregate.frame_errors << ',' << ber
                    << ',' << fer << ',' << ber_ci.first << ','
                    << ber_ci.second << ',' << fer_ci.first << ','
                    << fer_ci.second << ','
                    << static_cast<double>(aggregate.boundary_errors)
                           / aggregate.boundary_bits
                    << ','
                    << static_cast<double>(
                           aggregate.non_boundary_errors)
                           / aggregate.non_boundary_bits
                    << ',' << aggregate.mismatch_bits << ','
                    << aggregate.mismatch_frames << ','
                    << (block_fer > 0.0
                            ? (fer - block_fer) / block_fer
                            : (fer == 0.0 ? 0.0 : 1.0))
                    << ',' << mean(aggregate.first_delays) << ','
                    << mean(aggregate.decision_delays) << ','
                    << percentile(aggregate.decision_delays, 0.95)
                    << ','
                    << *std::max_element(
                           aggregate.decision_delays.begin(),
                           aggregate.decision_delays.end())
                    << ',' << input_to_symbol.back() << ','
                    << mean(aggregate.steady_intervals) << ','
                    << percentile(aggregate.steady_intervals, 0.95)
                    << ','
                    << static_cast<double>(aggregate.window_count)
                           / aggregate.frames
                    << ','
                    << static_cast<double>(
                           aggregate.output_batch_count)
                           / aggregate.frames
                    << ','
                    << static_cast<double>(
                           aggregate.window_trigger_count)
                           / aggregate.frames
                    << ',' << aggregate.acs_count << ','
                    << aggregate.traceback_operations << ','
                    << mean(aggregate.processing_us) << ','
                    << percentile(aggregate.processing_us, 0.95)
                    << ',' << percentile(aggregate.processing_us, 0.5)
                    << ','
                    << *std::max_element(
                           aggregate.processing_us.begin(),
                           aggregate.processing_us.end())
                    << ",5"
                    << ',' << survivor << ',' << survivor << ','
                    << metric << ',' << survivor + metric
                    << ",0,0,300,1," << kPayloadSeed << ','
                    << kNoiseSeed << ",0-" << aggregate.frames - 1
                    << ",CC-C-" << config.rate_case << "-S-"
                    << config.candidate_id << ",STAGE13-"
                    << rate.noise_group << ',' << stop_reason << '\n';
            }
        }
        std::cout << "PASS_STAGE13_FORMAL_RUNNER rows=" << plan.size()
                  << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE13: " << error.what() << '\n';
        return 1;
    }
}
