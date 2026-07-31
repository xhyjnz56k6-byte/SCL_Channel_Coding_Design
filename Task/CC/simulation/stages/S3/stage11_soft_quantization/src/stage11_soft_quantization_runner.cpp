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
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kPayloadSeed = 2026072001ULL;
constexpr std::uint64_t kNoiseSeed = 2026072902ULL;
constexpr std::size_t kCodec = 306;
constexpr std::size_t kPayload = 300;
constexpr std::int32_t kMetricCap = 1000000000;

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

struct Rate {
    std::string id;
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
};

struct Options {
    std::filesystem::path output;
    std::string mode;
    std::filesystem::path selected_snr;
    std::filesystem::path clip_config;
    std::uint64_t shard_index = 0;
    std::uint64_t shard_count = 1;
    std::uint64_t min_frames = 1000;
    std::uint64_t target_errors = 200;
    std::uint64_t max_frames = 50000;
};

struct QuantResult {
    std::vector<std::uint8_t> payload;
    std::uint64_t true_clip_count = 0;
    std::uint64_t edge_bin_count = 0;
    std::uint64_t integer_overflow_count = 0;
    std::uint64_t path_metric_saturation_count = 0;
};

struct Aggregate {
    std::uint64_t frames = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t mismatch_bits = 0;
    std::uint64_t mismatch_frames = 0;
    std::uint64_t true_clip_count = 0;
    std::uint64_t edge_bin_count = 0;
    std::uint64_t integer_overflow_count = 0;
    std::uint64_t path_metric_saturation_count = 0;
    std::uint64_t observed_samples = 0;
    std::vector<double> decode_samples;
};

double symbol(std::uint8_t bit) {
    return bit == 0 ? 1.0 : -1.0;
}

std::uint64_t parse_uint(const std::string& value) {
    std::size_t consumed = 0;
    const auto parsed = std::stoull(value, &consumed);
    if (consumed != value.size()) {
        throw std::invalid_argument("invalid integer: " + value);
    }
    return parsed;
}

Options parse_options(int argc, char** argv) {
    if (argc < 4) {
        throw std::invalid_argument(
            "output --mode prescan|coarse|dense [options]");
    }
    Options options;
    options.output = argv[1];
    for (int index = 2; index < argc; ++index) {
        const std::string argument = argv[index];
        auto take = [&]() {
            if (++index >= argc) {
                throw std::invalid_argument("missing value for " + argument);
            }
            return std::string(argv[index]);
        };
        if (argument == "--mode") {
            options.mode = take();
        } else if (argument == "--selected-snr") {
            options.selected_snr = take();
        } else if (argument == "--clip-config") {
            options.clip_config = take();
        } else if (argument == "--shard-index") {
            options.shard_index = parse_uint(take());
        } else if (argument == "--shard-count") {
            options.shard_count = parse_uint(take());
        } else if (argument == "--min-frames") {
            options.min_frames = parse_uint(take());
        } else if (argument == "--target-frame-errors") {
            options.target_errors = parse_uint(take());
        } else if (argument == "--max-frames") {
            options.max_frames = parse_uint(take());
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }
    if (options.mode != "prescan" && options.mode != "coarse"
        && options.mode != "dense") {
        throw std::invalid_argument("unknown mode");
    }
    if (options.shard_count == 0
        || options.shard_index >= options.shard_count
        || options.min_frames == 0
        || options.min_frames > options.max_frames
        || options.target_errors == 0) {
        throw std::invalid_argument("invalid shard/stopping configuration");
    }
    return options;
}

bool better(std::int32_t candidate,
            std::uint8_t predecessor,
            std::uint8_t input,
            std::int32_t incumbent,
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

QuantResult decode_quantized(
    const scl::cc::Trellis& trellis,
    const std::vector<double>& received,
    const std::vector<std::uint8_t>& mask,
    int bits,
    double clip) {
    if (bits < 3 || bits > 8 || !(clip > 0.0)
        || received.size() != 2 * kCodec
        || mask.size() != received.size()) {
        throw std::invalid_argument("invalid quantized decoder input");
    }
    const int qmax = (1 << (bits - 1)) - 1;
    const double step = clip / qmax;
    std::vector<std::int16_t> quantized(received.size());
    QuantResult result;
    for (std::size_t index = 0; index < received.size(); ++index) {
        if (!std::isfinite(received[index])) {
            throw std::invalid_argument("non-finite quantizer input");
        }
        long code = std::lround(received[index] / step);
        if (mask[index] != 0
            && (received[index] < -clip || received[index] > clip)) {
            ++result.true_clip_count;
        }
        code = std::max<long>(-qmax, std::min<long>(qmax, code));
        if (mask[index] != 0 && std::abs(code) == qmax) {
            ++result.edge_bin_count;
        }
        quantized[index] = static_cast<std::int16_t>(code);
    }
    const int expected_zero = static_cast<int>(
        std::lround(std::min(clip, 1.0) / step));
    const int expected_one = -expected_zero;
    std::array<std::int32_t, scl::cc::kStateCount> metrics{};
    std::array<std::int32_t, scl::cc::kStateCount> next{};
    metrics.fill(kMetricCap);
    metrics[0] = 0;
    std::vector<Survivor> survivors(kCodec * scl::cc::kStateCount);
    for (std::size_t time = 0; time < kCodec; ++time) {
        next.fill(kMetricCap);
        Survivor* step_survivors =
            survivors.data() + time * scl::cc::kStateCount;
        std::fill(
            step_survivors,
            step_survivors + scl::cc::kStateCount,
            Survivor{});
        for (std::size_t state = 0; state < scl::cc::kStateCount; ++state) {
            if (metrics[state] >= kMetricCap) {
                continue;
            }
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(
                    static_cast<std::uint8_t>(state), input);
                const int d0 = static_cast<int>(quantized[2 * time])
                    - (branch.output_bits[0] != 0
                           ? expected_one
                           : expected_zero);
                const int d1 =
                    static_cast<int>(quantized[2 * time + 1])
                    - (branch.output_bits[1] != 0
                           ? expected_one
                           : expected_zero);
                std::int64_t candidate = metrics[state];
                if (mask[2 * time] != 0) {
                    candidate += static_cast<std::int64_t>(d0) * d0;
                }
                if (mask[2 * time + 1] != 0) {
                    candidate += static_cast<std::int64_t>(d1) * d1;
                }
                if (candidate
                    > std::numeric_limits<std::int32_t>::max()) {
                    ++result.integer_overflow_count;
                    candidate = kMetricCap;
                } else if (candidate > kMetricCap) {
                    ++result.path_metric_saturation_count;
                    candidate = kMetricCap;
                }
                auto& survivor = step_survivors[branch.next_state];
                if (better(
                        static_cast<std::int32_t>(candidate),
                        static_cast<std::uint8_t>(state),
                        input,
                        next[branch.next_state],
                        survivor)) {
                    next[branch.next_state] =
                        static_cast<std::int32_t>(candidate);
                    survivor = {
                        static_cast<std::uint8_t>(state), input, true};
                }
            }
        }
        const std::int32_t minimum =
            *std::min_element(next.begin(), next.end());
        if (minimum >= kMetricCap) {
            throw std::runtime_error("no reachable quantized state");
        }
        for (auto& value : next) {
            if (value < kMetricCap) {
                value -= minimum;
            }
        }
        metrics = next;
    }
    std::vector<std::uint8_t> decoded(kCodec);
    std::uint8_t state = 0;
    for (std::size_t time = kCodec; time > 0; --time) {
        const auto& survivor =
            survivors[(time - 1) * scl::cc::kStateCount + state];
        if (!survivor.valid) {
            throw std::runtime_error("invalid quantized survivor");
        }
        decoded[time - 1] = survivor.input;
        state = survivor.predecessor;
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

void add(
    Aggregate& aggregate,
    const std::vector<std::uint8_t>& payload,
    const std::vector<std::uint8_t>& decoded,
    const std::vector<std::uint8_t>& floating,
    double elapsed,
    std::uint64_t observed,
    const QuantResult* quantized = nullptr) {
    const auto bit_errors = errors(payload, decoded);
    const auto mismatch = errors(floating, decoded);
    ++aggregate.frames;
    aggregate.bit_errors += bit_errors;
    aggregate.frame_errors += bit_errors != 0;
    aggregate.mismatch_bits += mismatch;
    aggregate.mismatch_frames += mismatch != 0;
    aggregate.decode_samples.push_back(elapsed);
    aggregate.observed_samples += observed;
    if (quantized != nullptr) {
        aggregate.true_clip_count += quantized->true_clip_count;
        aggregate.edge_bin_count += quantized->edge_bin_count;
        aggregate.integer_overflow_count +=
            quantized->integer_overflow_count;
        aggregate.path_metric_saturation_count +=
            quantized->path_metric_saturation_count;
    }
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
    return total / values.size();
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

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> fields;
    std::stringstream stream(line);
    std::string field;
    while (std::getline(stream, field, ',')) {
        fields.push_back(field);
    }
    return fields;
}

std::map<std::string, double> read_selected_snr(
    const std::filesystem::path& path) {
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
            throw std::runtime_error("missing column " + name);
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const auto rate_col = column("rateCase");
    const auto target_col = column("targetFer");
    const auto snr_col = column("selectedSnrDb");
    std::map<std::string, double> selected;
    while (std::getline(input, line)) {
        const auto fields = split(line);
        if (!fields.empty()
            && std::abs(std::stod(fields[target_col]) - 0.1) < 1e-12) {
            selected[fields[rate_col]] = std::stod(fields[snr_col]);
        }
    }
    if (selected.size() != 3) {
        throw std::runtime_error("missing three FER=0.1 SNR selections");
    }
    return selected;
}

std::map<int, double> read_clips(
    const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open clip configuration");
    }
    std::string line;
    std::getline(input, line);
    std::map<int, double> clips;
    while (std::getline(input, line)) {
        const auto fields = split(line);
        if (fields.size() >= 2 && fields[0].rfind("Q", 0) == 0) {
            clips[std::stoi(fields[0].substr(1))] =
                std::stod(fields[1]);
        }
    }
    if (clips.size() != 6) {
        throw std::runtime_error("clip config must cover Q3-Q8");
    }
    return clips;
}

const std::vector<Rate>& rates() {
    static const std::vector<Rate> values{
        {"R12", {"R12_11", {1, 1}}, 1200},
        {"R23", {"R23_1101", {1, 1, 0, 1}}, 2300},
        {"R34", {"R34_110110", {1, 1, 0, 1, 1, 0}}, 3400},
    };
    return values;
}

int run_prescan(const Options& options) {
    const auto selected = read_selected_snr(options.selected_snr);
    const std::vector<double> candidates{1.5, 2.0, 2.5, 3.0, 4.0};
    const scl::cc::Trellis trellis;
    scl::cc::ConvolutionalEncoder encoder(trellis);
    const scl::cc::SoftViterbiDecoder floating_decoder(trellis);
    struct Prescan {
        std::uint64_t mismatch_frames = 0;
        std::uint64_t true_clips = 0;
        std::uint64_t edge_bins = 0;
        std::uint64_t overflows = 0;
        std::uint64_t metric_saturations = 0;
        std::uint64_t observed = 0;
    };
    std::map<std::pair<int, double>, Prescan> values;
    for (const auto& rate : rates()) {
        const double snr = selected.at(rate.id);
        const double sigma = std::sqrt(
            1.0 / (2.0 * std::pow(10.0, snr / 10.0)));
        for (std::uint64_t frame = 0; frame < 300; ++frame) {
            const auto common = scl::common::generatePayloadBits(
                kPayloadSeed, kPayload, frame);
            const std::vector<std::uint8_t> payload(
                common.begin(), common.end());
            const auto encoded = encoder.encode_block(payload, true);
            const auto punctured =
                scl::cc::puncture_bits(encoded.mother_bits, rate.pattern);
            const auto noise =
                scl::common::generateStandardGaussianFrame(
                    kNoiseSeed,
                    rate.noise_group + 100,
                    frame,
                    punctured.bits.size());
            std::vector<double> received(punctured.bits.size());
            for (std::size_t index = 0; index < received.size(); ++index) {
                received[index] =
                    symbol(punctured.bits[index]) + sigma * noise[index];
            }
            const auto depunctured = scl::cc::depuncture_soft(
                received, 2 * kCodec, rate.pattern);
            const auto floating =
                floating_decoder.decode_terminated_masked_symbols(
                    depunctured.expanded_values,
                    depunctured.observed_mask,
                    kCodec);
            const auto observed = static_cast<std::uint64_t>(
                std::count(
                    depunctured.observed_mask.begin(),
                    depunctured.observed_mask.end(),
                    1));
            for (int bits = 3; bits <= 8; ++bits) {
                for (const double clip : candidates) {
                    const auto decoded = decode_quantized(
                        trellis,
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        bits,
                        clip);
                    auto& value = values[{bits, clip}];
                    value.mismatch_frames +=
                        decoded.payload != floating.payload_bits;
                    value.true_clips += decoded.true_clip_count;
                    value.edge_bins += decoded.edge_bin_count;
                    value.overflows += decoded.integer_overflow_count;
                    value.metric_saturations +=
                        decoded.path_metric_saturation_count;
                    value.observed += observed;
                }
            }
        }
    }
    std::ofstream output(options.output);
    output << std::setprecision(17);
    output
        << "quantMode,quantBits,clipMax,frames,mismatchFramesVsFloat,"
           "trueClipCount,trueClipRatePercent,edgeBinCount,"
           "edgeBinRatePercent,integerOverflowCount,"
           "pathMetricSaturationCount,selectedPerMode,"
           "globalBalancedClip\n";
    std::map<int, double> best;
    for (int bits = 3; bits <= 8; ++bits) {
        best[bits] = candidates.front();
        for (const double clip : candidates) {
            const auto& candidate = values.at({bits, clip});
            const auto& incumbent = values.at({bits, best[bits]});
            if (candidate.mismatch_frames < incumbent.mismatch_frames
                || (candidate.mismatch_frames
                        == incumbent.mismatch_frames
                    && candidate.true_clips < incumbent.true_clips)) {
                best[bits] = clip;
            }
        }
    }
    std::map<double, int> votes;
    for (const auto& item : best) {
        ++votes[item.second];
    }
    double global = candidates.front();
    for (const auto& vote : votes) {
        if (vote.second > votes[global]
            || (vote.second == votes[global] && vote.first < global)) {
            global = vote.first;
        }
    }
    for (int bits = 3; bits <= 8; ++bits) {
        for (const double clip : candidates) {
            const auto& value = values.at({bits, clip});
            output
                << 'Q' << bits << ',' << bits << ',' << clip << ",900,"
                << value.mismatch_frames << ',' << value.true_clips
                << ','
                << 100.0 * value.true_clips / value.observed << ','
                << value.edge_bins << ','
                << 100.0 * value.edge_bins / value.observed << ','
                << value.overflows << ','
                << value.metric_saturations << ','
                << (clip == best[bits] ? "YES" : "NO") << ','
                << (clip == global ? "YES" : "NO") << '\n';
        }
    }
    std::filesystem::path config = options.output;
    config.replace_filename("stage11_clip_selection.csv");
    std::ofstream selected_output(config);
    selected_output << "quantMode,bestClipPerQuantMode,globalBalancedClip\n";
    for (int bits = 3; bits <= 8; ++bits) {
        selected_output << 'Q' << bits << ',' << best[bits] << ','
                        << global << '\n';
    }
    std::cout << "PASS_STAGE11_CLIP_PRESCAN global=" << global << '\n';
    return 0;
}

struct WorkUnit {
    std::size_t index = 0;
    Rate rate;
    double snr = 0.0;
};

std::vector<WorkUnit> work_units(const std::string& mode) {
    std::vector<WorkUnit> units;
    for (const auto& rate : rates()) {
        double low = -5.0;
        double high = 10.0;
        double step = 0.5;
        if (mode == "dense") {
            step = 0.1;
            if (rate.id == "R12") {
                low = -2.0;
                high = 0.0;
            } else if (rate.id == "R23") {
                low = -0.5;
                high = 2.0;
            } else {
                low = 0.5;
                high = 3.0;
            }
        }
        const int count = static_cast<int>(
            std::llround((high - low) / step));
        for (int index = 0; index <= count; ++index) {
            units.push_back(
                {units.size(), rate, low + step * index});
        }
    }
    return units;
}

std::string stem(std::size_t unit) {
    std::ostringstream output;
    output << "unit_" << std::setw(3) << std::setfill('0') << unit;
    return output.str();
}

int run_unit(
    const Options& options,
    const WorkUnit& unit,
    const std::map<int, double>& clips) {
    const auto path = options.output / (stem(unit.index) + ".csv");
    if (std::filesystem::exists(path)) {
        return 0;
    }
    const std::vector<int> bits =
        options.mode == "dense"
        ? std::vector<int>{5, 6, 7, 8}
        : std::vector<int>{3, 4, 5, 6, 7, 8};
    const scl::cc::Trellis trellis;
    scl::cc::ConvolutionalEncoder encoder(trellis);
    const scl::cc::SoftViterbiDecoder floating_decoder(trellis);
    std::vector<Aggregate> aggregates(bits.size() + 1);
    const double sigma_squared =
        1.0 / (2.0 * std::pow(10.0, unit.snr / 10.0));
    const double sigma = std::sqrt(sigma_squared);
    std::size_t transmitted_bits = 0;
    std::string stop_reason = "ERROR_ABORT";
    for (std::uint64_t frame = 0; frame < options.max_frames; ++frame) {
        const auto common = scl::common::generatePayloadBits(
            kPayloadSeed, kPayload, frame);
        const std::vector<std::uint8_t> payload(
            common.begin(), common.end());
        const auto encoded = encoder.encode_block(payload, true);
        const auto punctured =
            scl::cc::puncture_bits(encoded.mother_bits, unit.rate.pattern);
        transmitted_bits = punctured.bits.size();
        const auto noise = scl::common::generateStandardGaussianFrame(
            kNoiseSeed,
            unit.rate.noise_group,
            frame,
            transmitted_bits);
        std::vector<double> received(transmitted_bits);
        for (std::size_t index = 0; index < received.size(); ++index) {
            received[index] =
                symbol(punctured.bits[index]) + sigma * noise[index];
        }
        const auto depunctured = scl::cc::depuncture_soft(
            received, 2 * kCodec, unit.rate.pattern);
        const auto observed = static_cast<std::uint64_t>(
            std::count(
                depunctured.observed_mask.begin(),
                depunctured.observed_mask.end(),
                1));
        const auto start = Clock::now();
        const auto floating =
            floating_decoder.decode_terminated_masked_symbols(
                depunctured.expanded_values,
                depunctured.observed_mask,
                kCodec);
        add(
            aggregates[0],
            payload,
            floating.payload_bits,
            floating.payload_bits,
            std::chrono::duration<double, std::micro>(
                Clock::now() - start)
                .count(),
            observed);
        for (std::size_t mode = 0; mode < bits.size(); ++mode) {
            const auto quant_start = Clock::now();
            const auto decoded = decode_quantized(
                trellis,
                depunctured.expanded_values,
                depunctured.observed_mask,
                bits[mode],
                clips.at(bits[mode]));
            add(
                aggregates[mode + 1],
                payload,
                decoded.payload,
                floating.payload_bits,
                std::chrono::duration<double, std::micro>(
                    Clock::now() - quant_start)
                    .count(),
                observed,
                &decoded);
        }
        const std::uint64_t frames = frame + 1;
        bool all_reached = frames >= options.min_frames;
        for (const auto& aggregate : aggregates) {
            all_reached =
                all_reached
                && aggregate.frame_errors >= options.target_errors;
        }
        if (all_reached) {
            stop_reason = "TARGET_ERRORS_REACHED";
            break;
        }
        if (frames == options.max_frames) {
            stop_reason = "MAX_FRAMES_REACHED";
        }
    }

    const double actual_rate =
        static_cast<double>(kPayload) / transmitted_bits;
    const double eb_n0 =
        unit.snr - 10.0 * std::log10(actual_rate);
    const double float_ber =
        static_cast<double>(aggregates[0].bit_errors)
        / (aggregates[0].frames * kPayload);
    const double float_fer =
        static_cast<double>(aggregates[0].frame_errors)
        / aggregates[0].frames;
    std::ofstream output(path);
    output << std::setprecision(17);
    output
        << "rateCase,snrDb,esN0Db,ebN0Db,actualRate,sigmaSquared,"
           "quantMode,quantBits,clipMax,quantStep,frames,bitErrors,"
           "frameErrors,BER,FER,berCiLow,berCiHigh,ferCiLow,ferCiHigh,"
           "avgDecodeTimeUs,medianDecodeTimeUs,p95DecodeTimeUs,"
           "maxDecodeTimeUs,inputMemoryBytes,pathMetricMemoryBytes,"
           "survivorMemoryBytes,totalDecoderMemoryBytes,trueClipCount,"
           "trueClipRatePercent,edgeBinCount,edgeBinRatePercent,"
           "integerOverflowCount,pathMetricSaturationCount,"
           "relativeBerIncreaseVsFloat,relativeFerIncreaseVsFloat,"
           "payloadSeed,noiseSeed,frameIndex,caseId,sourceNoiseId,"
           "gridLayer,stopReason,timingBatchCount\n";
    for (std::size_t mode = 0; mode < aggregates.size(); ++mode) {
        const bool floating = mode == 0;
        const int quant_bits = floating ? 0 : bits[mode - 1];
        const double clip = floating ? 0.0 : clips.at(quant_bits);
        const double step = floating
            ? 0.0
            : clip / ((1 << (quant_bits - 1)) - 1);
        const auto& aggregate = aggregates[mode];
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
        const std::size_t input_memory = floating
            ? transmitted_bits * sizeof(double)
            : (transmitted_bits * quant_bits + 7) / 8;
        const std::size_t metric_memory =
            2 * scl::cc::kStateCount
            * (floating ? sizeof(double) : sizeof(std::int32_t));
        const std::size_t survivor_memory =
            kCodec * scl::cc::kStateCount * sizeof(Survivor);
        output
            << unit.rate.id << ',' << unit.snr << ',' << unit.snr
            << ',' << eb_n0 << ',' << actual_rate << ','
            << sigma_squared << ','
            << (floating ? "Float" : "Q" + std::to_string(quant_bits))
            << ',' << quant_bits << ',' << clip << ',' << step << ','
            << aggregate.frames << ',' << aggregate.bit_errors << ','
            << aggregate.frame_errors << ',' << ber << ',' << fer
            << ',' << ber_ci.first << ',' << ber_ci.second << ','
            << fer_ci.first << ',' << fer_ci.second << ','
            << mean(aggregate.decode_samples) << ','
            << percentile(aggregate.decode_samples, 0.5) << ','
            << percentile(aggregate.decode_samples, 0.95) << ','
            << *std::max_element(
                   aggregate.decode_samples.begin(),
                   aggregate.decode_samples.end())
            << ',' << input_memory << ',' << metric_memory << ','
            << survivor_memory << ','
            << input_memory + metric_memory + survivor_memory << ','
            << aggregate.true_clip_count << ','
            << (aggregate.observed_samples == 0
                    ? 0.0
                    : 100.0 * aggregate.true_clip_count
                          / aggregate.observed_samples)
            << ',' << aggregate.edge_bin_count << ','
            << (aggregate.observed_samples == 0
                    ? 0.0
                    : 100.0 * aggregate.edge_bin_count
                          / aggregate.observed_samples)
            << ',' << aggregate.integer_overflow_count << ','
            << aggregate.path_metric_saturation_count << ','
            << (float_ber > 0.0
                    ? (ber - float_ber) / float_ber
                    : (ber == 0.0 ? 0.0 : 1.0))
            << ','
            << (float_fer > 0.0
                    ? (fer - float_fer) / float_fer
                    : (fer == 0.0 ? 0.0 : 1.0))
            << ',' << kPayloadSeed << ',' << kNoiseSeed << ",0-"
            << aggregate.frames - 1 << ",CC-B-" << unit.rate.id
            << "-S-" << (floating
                              ? "Float"
                              : "Q" + std::to_string(quant_bits))
            << ",STAGE11-" << unit.rate.noise_group << ','
            << options.mode << ',' << stop_reason << ",5\n";
    }
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto options = parse_options(argc, argv);
        if (options.mode == "prescan") {
            return run_prescan(options);
        }
        std::filesystem::create_directories(options.output);
        const auto clips = read_clips(options.clip_config);
        const auto units = work_units(options.mode);
        for (const auto& unit : units) {
            if (unit.index % options.shard_count
                != options.shard_index) {
                continue;
            }
            run_unit(options, unit, clips);
        }
        std::cout << "PASS_STAGE11_" << options.mode << "_SHARD "
                  << options.shard_index << '/' << options.shard_count
                  << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE11: " << error.what() << '\n';
        return 1;
    }
}
