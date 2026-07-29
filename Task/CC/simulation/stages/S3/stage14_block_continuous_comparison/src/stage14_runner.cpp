#include "continuous_encoder.hpp"
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
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kPayloadSeed = 2026072001ULL;
constexpr std::uint64_t kNoiseSeed = 2026072904ULL;
constexpr std::size_t kPayload = 300;
constexpr std::size_t kCodec = 306;
constexpr std::size_t kBoundaryRadius = 10;

struct Rate {
    std::string id;
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
};

struct Scheme {
    std::string id;
    std::size_t slot_bits = 300;
    std::vector<std::size_t> arrivals;
    bool block = false;
};

struct FrameScheme {
    std::vector<std::uint8_t> transmitted;
    std::vector<std::size_t> boundaries;
    std::uint64_t execution_digest = 1469598103934665603ULL;
};

struct Aggregate {
    std::uint64_t frames = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t boundary_errors = 0;
    std::uint64_t boundary_bits = 0;
    std::uint64_t non_boundary_errors = 0;
    std::uint64_t non_boundary_bits = 0;
    std::uint64_t acs_count = 0;
    std::uint64_t traceback_operations = 0;
    std::uint64_t output_batch_count = 0;
    std::uint64_t slot_trigger_count = 0;
    std::uint64_t window_trigger_count = 0;
    std::uint64_t peak_rx_buffer_symbols = 0;
    double rx_buffer_symbols_sum = 0.0;
    std::uint64_t rx_buffer_observations = 0;
    std::uint64_t execution_digest = 1469598103934665603ULL;
    std::vector<double> first_delays;
    std::vector<double> decision_delays;
    std::vector<double> full_frame_last_decisions;
    std::vector<double> steady_intervals;
    std::vector<double> decode_times;
    std::map<int, std::pair<std::uint64_t, std::uint64_t>> offsets;
};

struct Options {
    std::filesystem::path runtime;
    std::filesystem::path recommendation;
    std::filesystem::path organization_selection;
    std::string grid = "coarse";
    std::uint64_t shard_index = 0;
    std::uint64_t shard_count = 1;
    std::uint64_t min_frames = 1000;
    std::uint64_t target_errors = 200;
    std::uint64_t max_frames = 50000;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

std::uint64_t mix(std::uint64_t digest, std::uint64_t value) {
    digest ^= value;
    return digest * 1099511628211ULL;
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

Options parse_options(int argc, char** argv) {
    if (argc < 3) {
        throw std::invalid_argument("runtime and recommendation CSV required");
    }
    Options options;
    options.runtime = argv[1];
    options.recommendation = argv[2];
    for (int index = 3; index < argc; ++index) {
        const std::string argument = argv[index];
        auto take = [&]() {
            if (++index >= argc) {
                throw std::invalid_argument("missing option value");
            }
            return std::string(argv[index]);
        };
        if (argument == "--shard-index") {
            options.shard_index = std::stoull(take());
        } else if (argument == "--shard-count") {
            options.shard_count = std::stoull(take());
        } else if (argument == "--min-frames") {
            options.min_frames = std::stoull(take());
        } else if (argument == "--target-frame-errors") {
            options.target_errors = std::stoull(take());
        } else if (argument == "--max-frames") {
            options.max_frames = std::stoull(take());
        } else if (argument == "--grid") {
            options.grid = take();
        } else if (argument == "--organization-selection") {
            options.organization_selection = take();
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }
    if (options.shard_count == 0
        || options.shard_index >= options.shard_count
        || (options.grid != "coarse" && options.grid != "dense")
        || (options.grid == "dense"
            && options.organization_selection.empty())) {
        throw std::invalid_argument("invalid shard coordinates");
    }
    return options;
}

std::map<std::string, std::string> read_organization_selection(
    const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open organization selection");
    }
    std::string line;
    std::getline(input, line);
    const auto header = split(line);
    auto column = [&header](const std::string& name) {
        const auto found = std::find(header.begin(), header.end(), name);
        if (found == header.end()) {
            throw std::runtime_error(
                "missing organization selection column");
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const auto rate = column("rateCase");
    const auto organization = column("organization");
    const auto selected = column("selectedBalanced");
    std::map<std::string, std::string> result;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split(line);
        if (fields.at(selected) == "1") {
            result[fields.at(rate)] = fields.at(organization);
        }
    }
    if (result.size() != 3) {
        throw std::runtime_error(
            "organization selection must cover three rates");
    }
    return result;
}

std::vector<double> snr_grid(const std::string& rate,
                             const std::string& grid) {
    if (grid == "coarse") {
        std::vector<double> values;
        for (int index = 0; index < 31; ++index) {
            values.push_back(-5.0 + 0.5 * index);
        }
        return values;
    }
    const auto limits = rate == "R12"
        ? std::make_pair(-2.0, 0.0)
        : (rate == "R23"
               ? std::make_pair(-0.5, 2.0)
               : std::make_pair(0.5, 3.0));
    std::vector<double> values;
    const int count =
        static_cast<int>(std::lround((limits.second - limits.first) / 0.1));
    for (int index = 0; index <= count; ++index) {
        values.push_back(limits.first + 0.1 * index);
    }
    return values;
}

const std::vector<Rate>& rates() {
    static const std::vector<Rate> values{
        {"R12", {"R12_11", {1, 1}}, 1200},
        {"R23", {"R23_1101", {1, 1, 0, 1}}, 2300},
        {"R34", {"R34_110110", {1, 1, 0, 1, 1, 0}}, 3400},
    };
    return values;
}

const std::vector<Scheme>& schemes() {
    static const std::vector<Scheme> values{
        {"A_BLOCK_300", 300, {306}, true},
        {"B_CONT_50x6", 50, {50, 100, 150, 200, 250, 306}, false},
        {"C_CONT_100x3", 100, {100, 200, 306}, false},
        {"D_CONT_150x2", 150, {150, 306}, false},
    };
    return values;
}

std::map<std::string, scl::cc::stage13::SlidingWindowConfig>
read_recommendations(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open Stage13 recommendations");
    }
    std::string line;
    std::getline(input, line);
    const auto header = split(line);
    auto column = [&header](const std::string& name) {
        const auto found = std::find(header.begin(), header.end(), name);
        if (found == header.end()) {
            throw std::runtime_error("missing recommendation column");
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const auto rate_col = column("rateCase");
    const auto type_col = column("recommendationType");
    const auto window_col = column("windowBits");
    const auto slide_col = column("slideBits");
    const auto depth_col = column("dtb");
    std::map<std::string, scl::cc::stage13::SlidingWindowConfig> result;
    while (std::getline(input, line)) {
        const auto fields = split(line);
        if (!fields.empty() && fields[type_col] == "balanced") {
            result[fields[rate_col]] = {
                static_cast<std::size_t>(std::stoull(fields[window_col])),
                static_cast<std::size_t>(std::stoull(fields[slide_col])),
                static_cast<std::size_t>(std::stoull(fields[depth_col])),
                kPayload,
                scl::cc::kMemory,
            };
        }
    }
    if (result.size() != 3) {
        throw std::runtime_error("balanced recommendation missing a rate");
    }
    return result;
}

FrameScheme build_frame(
    const scl::cc::Trellis& trellis,
    const std::vector<std::uint8_t>& payload,
    const scl::cc::PuncturePattern& pattern,
    const Scheme& scheme) {
    FrameScheme frame;
    if (scheme.block) {
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const auto encoded = encoder.encode_block(payload, true);
        frame.transmitted =
            scl::cc::puncture_bits(encoded.mother_bits, pattern).bits;
        frame.execution_digest = mix(frame.execution_digest, 300);
    } else {
        scl::cc::stage12::ContinuousEncoder encoder(trellis, pattern);
        for (std::size_t start = 0; start < kPayload;
             start += scheme.slot_bits) {
            const bool final = start + scheme.slot_bits == kPayload;
            const std::vector<std::uint8_t> part(
                payload.begin() + static_cast<std::ptrdiff_t>(start),
                payload.begin()
                    + static_cast<std::ptrdiff_t>(start + scheme.slot_bits));
            const auto encoded = encoder.encode_slot(part, final, final);
            frame.transmitted.insert(
                frame.transmitted.end(),
                encoded.transmitted_bits.begin(),
                encoded.transmitted_bits.end());
            frame.execution_digest =
                mix(frame.execution_digest, encoded.metadata.slot_index);
            frame.execution_digest =
                mix(frame.execution_digest, encoded.metadata.initial_state);
            frame.execution_digest =
                mix(frame.execution_digest, encoded.metadata.final_state);
            frame.execution_digest =
                mix(frame.execution_digest, encoded.metadata.initial_phase);
            frame.execution_digest =
                mix(frame.execution_digest, encoded.metadata.final_phase);
        }
        for (std::size_t boundary = scheme.slot_bits;
             boundary < kPayload;
             boundary += scheme.slot_bits) {
            frame.boundaries.push_back(boundary);
        }
    }
    frame.execution_digest =
        mix(frame.execution_digest, frame.transmitted.size());
    return frame;
}

std::vector<std::size_t> input_to_symbol(
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
        mapping[input] = transmitted - 1;
    }
    return mapping;
}

bool boundary_bit(
    std::size_t bit,
    const std::vector<std::size_t>& boundaries) {
    for (const std::size_t boundary : boundaries) {
        if (bit + kBoundaryRadius >= boundary
            && bit < boundary + kBoundaryRadius) {
            return true;
        }
    }
    return false;
}

double percentile(std::vector<double> values, double probability) {
    if (values.empty()) {
        return 0.0;
    }
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

void add(
    Aggregate& aggregate,
    const Scheme& scheme,
    const std::vector<std::uint8_t>& payload,
    const std::vector<std::uint8_t>& decoded,
    const std::vector<std::size_t>& decision_symbols,
    const std::vector<std::size_t>& source_symbols,
    const FrameScheme& frame,
    double decode_us,
    std::size_t acs,
    std::size_t traceback,
    std::size_t output_batches,
    std::size_t slot_triggers,
    std::size_t window_triggers,
    std::size_t peak_buffer,
    double average_buffer) {
    ++aggregate.frames;
    const bool record_deterministic_schedule = aggregate.frames == 1;
    aggregate.acs_count += acs;
    aggregate.traceback_operations += traceback;
    aggregate.output_batch_count += output_batches;
    aggregate.slot_trigger_count += slot_triggers;
    aggregate.window_trigger_count += window_triggers;
    aggregate.peak_rx_buffer_symbols =
        std::max(aggregate.peak_rx_buffer_symbols, peak_buffer);
    aggregate.rx_buffer_symbols_sum += average_buffer;
    ++aggregate.rx_buffer_observations;
    aggregate.decode_times.push_back(decode_us);
    aggregate.execution_digest =
        mix(aggregate.execution_digest, frame.execution_digest);
    std::uint64_t frame_errors = 0;
    for (std::size_t bit = 0; bit < kPayload; ++bit) {
        const bool error = payload[bit] != decoded[bit];
        frame_errors += error;
        if (boundary_bit(bit, frame.boundaries)) {
            ++aggregate.boundary_bits;
            aggregate.boundary_errors += error;
        } else {
            ++aggregate.non_boundary_bits;
            aggregate.non_boundary_errors += error;
        }
        for (const std::size_t boundary : frame.boundaries) {
            const int offset =
                static_cast<int>(bit) - static_cast<int>(boundary);
            if (offset >= -10 && offset <= 9) {
                auto& cell = aggregate.offsets[offset];
                cell.first += error;
                ++cell.second;
            }
        }
        if (record_deterministic_schedule) {
            aggregate.decision_delays.push_back(
                static_cast<double>(
                    decision_symbols[bit] - source_symbols[bit]));
        }
    }
    if (record_deterministic_schedule) {
        aggregate.first_delays.push_back(
            static_cast<double>(
                decision_symbols.front() - source_symbols.front()));
        aggregate.full_frame_last_decisions.push_back(
            static_cast<double>(
                *std::max_element(
                    decision_symbols.begin(), decision_symbols.end())));
        std::vector<std::size_t> unique_decisions;
        for (const std::size_t decision : decision_symbols) {
            if (unique_decisions.empty()
                || unique_decisions.back() != decision) {
                unique_decisions.push_back(decision);
            }
        }
        for (std::size_t index = 1;
             index < unique_decisions.size();
             ++index) {
            aggregate.steady_intervals.push_back(
                static_cast<double>(
                    unique_decisions[index]
                    - unique_decisions[index - 1]));
        }
    }
    aggregate.bit_errors += frame_errors;
    aggregate.frame_errors += frame_errors != 0;
    if (scheme.block && !frame.boundaries.empty()) {
        throw std::logic_error("block scheme has boundaries");
    }
}

std::string stem(std::size_t unit) {
    std::ostringstream output;
    output << "unit_" << std::setw(3) << std::setfill('0') << unit;
    return output.str();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        std::filesystem::create_directories(options.runtime);
        const auto recommendations =
            read_recommendations(options.recommendation);
        const auto selected_organizations =
            options.grid == "dense"
            ? read_organization_selection(options.organization_selection)
            : std::map<std::string, std::string>{};
        const scl::cc::Trellis trellis;
        const scl::cc::SoftViterbiDecoder full_decoder(trellis);
        std::size_t unit_index = 0;
        for (const auto& rate : rates()) {
            const auto mapping = input_to_symbol(rate.pattern);
            std::vector<std::size_t> active_scheme_indices;
            for (std::size_t index = 0; index < schemes().size(); ++index) {
                if (options.grid == "coarse"
                    || schemes()[index].block
                    || schemes()[index].id
                        == selected_organizations.at(rate.id)) {
                    active_scheme_indices.push_back(index);
                }
            }
            if (active_scheme_indices.size()
                != (options.grid == "coarse" ? 4 : 2)) {
                throw std::runtime_error("active organization count mismatch");
            }
            for (const double snr : snr_grid(rate.id, options.grid)) {
                const std::size_t current_unit = unit_index++;
                if (current_unit % options.shard_count
                    != options.shard_index) {
                    continue;
                }
                const auto output_path =
                    options.runtime / (stem(current_unit) + ".csv");
                const auto offset_path =
                    options.runtime / (stem(current_unit) + "_offsets.csv");
                if (std::filesystem::exists(output_path)
                    && std::filesystem::exists(offset_path)) {
                    continue;
                }
                const double sigma_squared =
                    1.0 / (2.0 * std::pow(10.0, snr / 10.0));
                const double sigma = std::sqrt(sigma_squared);
                std::vector<Aggregate> aggregates(schemes().size());
                std::size_t transmitted_bits = 0;
                std::string stop_reason = "ERROR_ABORT";
                for (std::uint64_t frame_index = 0;
                     frame_index < options.max_frames;
                     ++frame_index) {
                    const auto common = scl::common::generatePayloadBits(
                        kPayloadSeed, kPayload, frame_index);
                    const std::vector<std::uint8_t> payload(
                        common.begin(), common.end());
                    std::vector<FrameScheme> frames;
                    for (const auto& scheme : schemes()) {
                        frames.push_back(
                            build_frame(
                                trellis, payload, rate.pattern, scheme));
                    }
                    for (std::size_t index = 1;
                         index < frames.size();
                         ++index) {
                        if (frames[index].transmitted
                            != frames[0].transmitted) {
                            throw std::runtime_error(
                                "slot organization changed encoded stream");
                        }
                    }
                    transmitted_bits = frames[0].transmitted.size();
                    const auto noise =
                        scl::common::generateStandardGaussianFrame(
                            kNoiseSeed,
                            rate.noise_group,
                            frame_index,
                            transmitted_bits);
                    std::vector<double> received(transmitted_bits);
                    for (std::size_t index = 0;
                         index < transmitted_bits;
                         ++index) {
                        received[index] =
                            symbol(frames[0].transmitted[index])
                            + sigma * noise[index];
                    }
                    const auto depunctured = scl::cc::depuncture_soft(
                        received, 2 * kCodec, rate.pattern);
                    for (const std::size_t scheme_index :
                         active_scheme_indices) {
                        const auto& scheme = schemes()[scheme_index];
                        std::vector<std::uint8_t> decoded;
                        std::vector<std::size_t> decisions(kPayload);
                        std::size_t acs = 0;
                        std::size_t traceback = 0;
                        std::size_t output_batches = 0;
                        std::size_t slot_triggers = 0;
                        std::size_t window_triggers = 0;
                        std::size_t peak_buffer = 0;
                        double average_buffer = 0.0;
                        const auto start = Clock::now();
                        if (scheme.block) {
                            const auto full =
                                full_decoder
                                    .decode_terminated_masked_symbols(
                                        depunctured.expanded_values,
                                        depunctured.observed_mask,
                                        kCodec);
                            decoded = full.payload_bits;
                            std::fill(
                                decisions.begin(),
                                decisions.end(),
                                transmitted_bits - 1);
                            acs =
                                kCodec * scl::cc::kStateCount * 2;
                            traceback = kCodec;
                            output_batches = 1;
                            slot_triggers = 1;
                            window_triggers = 0;
                            peak_buffer = transmitted_bits;
                            average_buffer = transmitted_bits;
                        } else {
                            const auto online =
                                scl::cc::stage13::
                                    true_sliding_window_viterbi_scheduled(
                                        trellis,
                                        depunctured.expanded_values,
                                        depunctured.observed_mask,
                                        recommendations.at(rate.id),
                                        scheme.arrivals);
                            decoded = online.payload;
                            for (std::size_t bit = 0;
                                 bit < kPayload;
                                 ++bit) {
                                const auto batch =
                                    online.output_batch_index[bit];
                                decisions[bit] = mapping[
                                    online
                                        .output_batch_available_input_time[
                                            batch]];
                            }
                            acs = online.acs_count;
                            traceback = online.traceback_operations;
                            output_batches = online.output_batch_count;
                            slot_triggers = online.slot_trigger_count;
                            window_triggers =
                                online.window_trigger_count;
                            peak_buffer = mapping[std::min(
                                              kCodec - 1,
                                              online
                                                  .peak_buffered_input_steps
                                                  - 1)]
                                + 1;
                            average_buffer =
                                online.buffer_observations == 0
                                ? 0.0
                                : static_cast<double>(
                                      online.buffered_input_step_sum)
                                      / online.buffer_observations
                                      * transmitted_bits / kCodec;
                        }
                        const double decode_us =
                            std::chrono::duration<double, std::micro>(
                                Clock::now() - start)
                                .count();
                        add(
                            aggregates[scheme_index],
                            scheme,
                            payload,
                            decoded,
                            decisions,
                            mapping,
                            frames[scheme_index],
                            decode_us,
                            acs,
                            traceback,
                            output_batches,
                            slot_triggers,
                            window_triggers,
                            peak_buffer,
                            average_buffer);
                    }
                    const std::uint64_t count = frame_index + 1;
                    bool reached = count >= options.min_frames;
                    for (const std::size_t scheme_index :
                         active_scheme_indices) {
                        const auto& aggregate = aggregates[scheme_index];
                        reached =
                            reached
                            && aggregate.frame_errors
                                >= options.target_errors;
                    }
                    if (reached) {
                        stop_reason = "TARGET_ERRORS_REACHED";
                        break;
                    }
                    if (count == options.max_frames) {
                        stop_reason = "MAX_FRAMES_REACHED";
                    }
                }
                const double actual_rate =
                    static_cast<double>(kPayload) / transmitted_bits;
                const double eb_n0 =
                    snr - 10.0 * std::log10(actual_rate);
                std::ofstream output(output_path);
                output << std::setprecision(17);
                output
                    << "organization,rateCase,snrDb,esN0Db,ebN0Db,"
                       "actualRate,sigmaSquared,slotBits,slotCount,frames,"
                       "bitErrors,frameErrors,BER,FER,berCiLow,berCiHigh,"
                       "ferCiLow,ferCiHigh,boundaryBER,nonBoundaryBER,"
                       "boundaryToNonBoundaryRatio,"
                       "firstOutputDelaySymbols,avgDecisionDelaySymbols,"
                       "medianDecisionDelaySymbols,p95DecisionDelaySymbols,"
                       "maxDecisionDelaySymbols,fullFrameLastDecisionSymbol,"
                       "steadyOutputIntervalMean,steadyOutputIntervalP95,"
                       "outputBatchCount,slotTriggerCount,windowTriggerCount,"
                       "peakRxBufferSymbols,avgRxBufferSymbols,"
                       "avgDecodeTimeUs,medianDecodeTimeUs,p95DecodeTimeUs,"
                       "maxDecodeTimeUs,timingBatchCount,normalizedGoodput,"
                       "transmittedBits,totalMemoryBytes,ACSCount,"
                       "tracebackOperations,schemeExecutionDigest,"
                       "payloadSeed,noiseSeed,frameIndex,caseId,"
                       "sourceNoiseId,boundaryStatus,gridLayer,stopReason\n";
                std::ofstream offsets(offset_path);
                offsets
                    << "organization,rateCase,snrDb,relativeOffset,"
                       "bitErrors,bits,BER,berCiLow,berCiHigh,gridLayer\n";
                for (const std::size_t scheme_index :
                     active_scheme_indices) {
                    const auto& scheme = schemes()[scheme_index];
                    const auto& aggregate = aggregates[scheme_index];
                    const double ber =
                        static_cast<double>(aggregate.bit_errors)
                        / (aggregate.frames * kPayload);
                    const double fer =
                        static_cast<double>(aggregate.frame_errors)
                        / aggregate.frames;
                    const auto ber_ci = wilson(
                        aggregate.bit_errors,
                        aggregate.frames * kPayload);
                    const auto fer_ci = wilson(
                        aggregate.frame_errors, aggregate.frames);
                    const double boundary_ber =
                        aggregate.boundary_bits == 0
                        ? 0.0
                        : static_cast<double>(
                              aggregate.boundary_errors)
                              / aggregate.boundary_bits;
                    const double non_boundary_ber =
                        static_cast<double>(
                            aggregate.non_boundary_errors)
                        / aggregate.non_boundary_bits;
                    const auto config = recommendations.at(rate.id);
                    const std::size_t decoder_memory = scheme.block
                        ? kCodec * scl::cc::kStateCount * 3
                              + 2 * scl::cc::kStateCount
                                    * sizeof(double)
                        : config.window_bits * scl::cc::kStateCount * 3
                              + 3 * scl::cc::kStateCount
                                    * sizeof(double);
                    output
                        << scheme.id << ',' << rate.id << ',' << snr
                        << ',' << snr << ',' << eb_n0 << ','
                        << actual_rate << ',' << sigma_squared << ','
                        << scheme.slot_bits << ','
                        << scheme.arrivals.size() << ','
                        << aggregate.frames << ','
                        << aggregate.bit_errors << ','
                        << aggregate.frame_errors << ',' << ber << ','
                        << fer << ',' << ber_ci.first << ','
                        << ber_ci.second << ',' << fer_ci.first << ','
                        << fer_ci.second << ',';
                    if (scheme.block) {
                        output << "NOT_APPLICABLE,NOT_APPLICABLE,"
                                  "NOT_APPLICABLE,";
                    } else {
                        output
                            << boundary_ber << ',' << non_boundary_ber
                            << ','
                            << (non_boundary_ber > 0.0
                                    ? boundary_ber / non_boundary_ber
                                    : 0.0)
                            << ',';
                    }
                    output
                        << mean(aggregate.first_delays) << ','
                        << mean(aggregate.decision_delays) << ','
                        << percentile(aggregate.decision_delays, 0.5)
                        << ','
                        << percentile(aggregate.decision_delays, 0.95)
                        << ','
                        << *std::max_element(
                               aggregate.decision_delays.begin(),
                               aggregate.decision_delays.end())
                        << ','
                        << mean(aggregate.full_frame_last_decisions)
                        << ',' << mean(aggregate.steady_intervals) << ','
                        << percentile(aggregate.steady_intervals, 0.95)
                        << ','
                        << static_cast<double>(
                               aggregate.output_batch_count)
                               / aggregate.frames
                        << ','
                        << static_cast<double>(
                               aggregate.slot_trigger_count)
                               / aggregate.frames
                        << ','
                        << static_cast<double>(
                               aggregate.window_trigger_count)
                               / aggregate.frames
                        << ',' << aggregate.peak_rx_buffer_symbols << ','
                        << aggregate.rx_buffer_symbols_sum
                               / aggregate.rx_buffer_observations
                        << ',' << mean(aggregate.decode_times) << ','
                        << percentile(aggregate.decode_times, 0.5) << ','
                        << percentile(aggregate.decode_times, 0.95) << ','
                        << *std::max_element(
                               aggregate.decode_times.begin(),
                               aggregate.decode_times.end())
                        << ",5"
                        << ',' << actual_rate * (1.0 - fer) << ','
                        << transmitted_bits << ',' << decoder_memory
                        << ',' << aggregate.acs_count << ','
                        << aggregate.traceback_operations << ','
                        << aggregate.execution_digest << ','
                        << kPayloadSeed << ',' << kNoiseSeed << ",0-"
                        << aggregate.frames - 1 << ",CC-O-"
                        << rate.id << '-' << scheme.id << ",STAGE14-"
                        << rate.noise_group << ','
                        << (scheme.block ? "NOT_APPLICABLE" : "APPLICABLE")
                        << ',' << options.grid << ',' << stop_reason << '\n';
                    if (!scheme.block) {
                        for (const auto& cell : aggregate.offsets) {
                            const auto ci =
                                wilson(cell.second.first, cell.second.second);
                            offsets
                                << scheme.id << ',' << rate.id << ','
                                << snr << ',' << cell.first << ','
                                << cell.second.first << ','
                                << cell.second.second << ','
                                << static_cast<double>(cell.second.first)
                                       / cell.second.second
                                << ',' << ci.first << ',' << ci.second
                                << ',' << options.grid << '\n';
                        }
                    }
                }
            }
        }
        std::cout << "PASS_STAGE14_ONLINE_SHARD "
                  << options.shard_index << '/' << options.shard_count
                  << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE14: " << error.what() << '\n';
        return 1;
    }
}
