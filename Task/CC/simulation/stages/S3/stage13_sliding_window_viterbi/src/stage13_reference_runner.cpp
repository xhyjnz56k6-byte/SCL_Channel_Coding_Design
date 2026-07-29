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
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
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

struct Survivor {
    std::uint8_t predecessor = 0;
    std::uint8_t input = 0;
    bool valid = false;
};

struct DecodeResult {
    std::vector<std::uint8_t> payload;
    std::uint64_t traceback_operations = 0;
};

struct Rate {
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
};

struct Target {
    std::string rate_case;
    double snr_db = 0.0;
    std::uint64_t frames = 0;
};

struct Aggregate {
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t mismatch_bits = 0;
    std::uint64_t mismatch_frames = 0;
    std::uint64_t traceback_operations = 0;
    std::vector<double> timing_us;
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

std::vector<Target> read_targets(const std::string& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open Stage13 formal result");
    }
    std::string line;
    std::getline(input, line);
    const auto header = split(line);
    auto column = [&header](const std::string& name) {
        const auto found = std::find(header.begin(), header.end(), name);
        if (found == header.end()) {
            throw std::runtime_error("missing result column: " + name);
        }
        return static_cast<std::size_t>(found - header.begin());
    };
    const auto rate = column("rateCase");
    const auto snr = column("snrDb");
    const auto frames = column("frames");
    std::map<std::pair<std::string, double>, std::uint64_t> unique;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        const auto fields = split(line);
        const auto key =
            std::make_pair(fields.at(rate), std::stod(fields.at(snr)));
        const auto count = std::stoull(fields.at(frames));
        const auto inserted = unique.emplace(key, count);
        if (!inserted.second && inserted.first->second != count) {
            throw std::runtime_error(
                "candidate frame counts differ within one rate/SNR group");
        }
    }
    std::vector<Target> targets;
    for (const auto& item : unique) {
        targets.push_back({item.first.first, item.first.second, item.second});
    }
    return targets;
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

bool better(double candidate,
            std::uint8_t predecessor,
            std::uint8_t input,
            double incumbent,
            const Survivor& survivor) {
    return !survivor.valid || candidate < incumbent
        || (candidate == incumbent
            && std::tie(predecessor, input)
                < std::tie(survivor.predecessor, survivor.input));
}

DecodeResult truncated(const scl::cc::Trellis& trellis,
                       const std::vector<double>& received,
                       const std::vector<std::uint8_t>& mask,
                       std::size_t depth) {
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
                const double candidate = metrics[state]
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
        const double minimum =
            *std::min_element(next.begin(), next.end());
        for (double& value : next) {
            if (std::isfinite(value)) {
                value -= minimum;
            }
        }
        metrics = next;
        if (time + 1 >= depth && time + 1 < kCodec) {
            const auto best =
                std::min_element(metrics.begin(), metrics.end());
            std::uint8_t state =
                static_cast<std::uint8_t>(best - metrics.begin());
            std::uint8_t emitted = 0;
            for (std::size_t offset = 0; offset < depth; ++offset) {
                const auto& survivor =
                    ring[((time - offset) % depth)
                         * scl::cc::kStateCount
                         + state];
                if (!survivor.valid) {
                    throw std::runtime_error("invalid survivor");
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
            throw std::runtime_error("invalid final survivor");
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
    std::uint64_t count = 0;
    for (std::size_t index = 0; index < lhs.size(); ++index) {
        count += lhs[index] != rhs[index];
    }
    return count;
}

void add(Aggregate& aggregate,
         const std::vector<std::uint8_t>& payload,
         const std::vector<std::uint8_t>& decoded,
         const std::vector<std::uint8_t>& block,
         std::uint64_t operations,
         double timing_us) {
    const auto bit_errors = errors(payload, decoded);
    const auto mismatch = errors(block, decoded);
    aggregate.bit_errors += bit_errors;
    aggregate.frame_errors += bit_errors != 0;
    aggregate.mismatch_bits += mismatch;
    aggregate.mismatch_frames += mismatch != 0;
    aggregate.traceback_operations += operations;
    aggregate.timing_us.push_back(timing_us);
}

double percentile(std::vector<double> values, double probability) {
    std::sort(values.begin(), values.end());
    return values[
        std::min(values.size() - 1,
                 static_cast<std::size_t>(
                     std::ceil(probability * values.size())) - 1)];
}

double mean(const std::vector<double>& values) {
    double total = 0.0;
    for (const auto value : values) {
        total += value;
    }
    return total / values.size();
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
        mapping[input] = transmitted - 1;
    }
    return mapping;
}

std::pair<double, double> wilson(std::uint64_t successes,
                                 std::uint64_t trials) {
    constexpr double z = 1.959963984540054;
    const double n = static_cast<double>(trials);
    const double p = successes / n;
    const double denominator = 1.0 + z * z / n;
    const double center = (p + z * z / (2.0 * n)) / denominator;
    const double half =
        z * std::sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
        / denominator;
    return {std::max(0.0, center - half),
            std::min(1.0, center + half)};
}

void write_row(std::ofstream& output,
               const Target& target,
               const std::string& mode,
               std::size_t depth,
               const Aggregate& aggregate,
               const scl::cc::PuncturePattern& pattern,
               double actual_rate,
               double sigma_squared) {
    const auto ber_ci =
        wilson(aggregate.bit_errors, target.frames * kPayload);
    const auto fer_ci =
        wilson(aggregate.frame_errors, target.frames);
    const std::size_t survivor = mode == "BLOCK_FULL_TRACEBACK"
        ? kCodec * scl::cc::kStateCount * 3
        : depth * scl::cc::kStateCount * 3;
    const std::size_t metric =
        3 * scl::cc::kStateCount * sizeof(double);
    const auto mapping = input_to_transmitted_symbol(pattern);
    std::vector<double> decision_delays;
    for (std::size_t bit = 0; bit < kPayload; ++bit) {
        const std::size_t decision_input =
            mode == "BLOCK_FULL_TRACEBACK"
            ? kCodec - 1
            : std::min(kCodec - 1, bit + depth - 1);
        decision_delays.push_back(
            static_cast<double>(
                mapping[decision_input] - mapping[bit]));
    }
    output << target.rate_case << ',' << target.snr_db << ','
           << target.snr_db << ','
           << target.snr_db - 10.0 * std::log10(actual_rate) << ','
           << actual_rate << ',' << sigma_squared << ',' << mode
           << ',' << depth << ',' << target.frames << ','
           << aggregate.bit_errors << ',' << aggregate.frame_errors
           << ','
           << static_cast<double>(aggregate.bit_errors)
                  / (target.frames * kPayload)
           << ','
           << static_cast<double>(aggregate.frame_errors) / target.frames
           << ',' << ber_ci.first << ',' << ber_ci.second << ','
           << fer_ci.first << ',' << fer_ci.second << ','
           << aggregate.mismatch_bits << ','
           << aggregate.mismatch_frames << ',' << survivor << ','
           << metric << ',' << survivor + metric << ','
           << aggregate.traceback_operations << ','
           << 2ULL * kCodec * scl::cc::kStateCount * target.frames
           << ',' << decision_delays.front() << ','
           << mean(decision_delays) << ','
           << percentile(decision_delays, 0.95) << ','
           << mapping.back() << ','
           << mean(aggregate.timing_us) << ','
           << percentile(aggregate.timing_us, 0.5) << ','
           << percentile(aggregate.timing_us, 0.95) << ','
           << *std::max_element(
                  aggregate.timing_us.begin(),
                  aggregate.timing_us.end())
           << ",5"
           << ',' << kPayloadSeed << ',' << kNoiseSeed << ",0-"
           << target.frames - 1 << ",STAGE13-REFERENCE-"
           << target.rate_case << '-' << target.snr_db
           << ",STAGE13-REFERENCE\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 3 && argc != 5) {
            throw std::invalid_argument(
                "output, Stage13 result, optional shard index/count required");
        }
        const auto targets = read_targets(argv[2]);
        const std::size_t shard_index =
            argc == 5 ? std::stoull(argv[3]) : 0;
        const std::size_t shard_count =
            argc == 5 ? std::stoull(argv[4]) : 1;
        if (shard_count == 0 || shard_index >= shard_count) {
            throw std::invalid_argument("invalid reference shard");
        }
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::SoftViterbiDecoder block_decoder(trellis);
        std::ofstream output(argv[1]);
        output << std::setprecision(17)
               << "rateCase,snrDb,esN0Db,ebN0Db,actualRate,"
                  "sigmaSquared,tracebackMode,dtb,frames,bitErrors,"
                  "frameErrors,BER,FER,berCiLow,berCiHigh,ferCiLow,"
                  "ferCiHigh,mismatchVsBlockBits,mismatchVsBlockFrames,"
                  "survivorMemoryBytes,pathMetricMemoryBytes,"
                  "totalMemoryBytes,tracebackOperations,ACSCount,"
                  "firstOutputDelaySymbols,avgDecisionDelaySymbols,"
                  "p95DecisionDelaySymbols,fullFrameLastDecisionSymbol,"
                  "avgDecodeTimeUs,"
                  "medianDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,"
                  "timingBatchCount,"
                  "payloadSeed,noiseSeed,frameIndex,caseId,sourceNoiseId\n";
        std::size_t processed = 0;
        for (std::size_t target_index = 0;
             target_index < targets.size();
             ++target_index) {
            if (target_index % shard_count != shard_index) {
                continue;
            }
            const auto& target = targets[target_index];
            const auto rate = rate_for(target.rate_case);
            const double sigma_squared =
                1.0
                / (2.0 * std::pow(10.0, target.snr_db / 10.0));
            const double sigma = std::sqrt(sigma_squared);
            std::size_t transmitted_bits = 0;
            Aggregate block_aggregate;
            Aggregate d84_aggregate;
            Aggregate d112_aggregate;
            for (std::uint64_t frame = 0; frame < target.frames; ++frame) {
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
                const auto block_start = Clock::now();
                const auto block = block_decoder
                    .decode_terminated_masked_symbols(
                        depunctured.expanded_values,
                        depunctured.observed_mask,
                        kCodec);
                const auto block_us =
                    std::chrono::duration<double, std::micro>(
                        Clock::now() - block_start)
                        .count();
                add(block_aggregate,
                    payload,
                    block.payload_bits,
                    block.payload_bits,
                    kCodec,
                    block_us);
                const auto d84_start = Clock::now();
                const auto d84 = truncated(
                    trellis,
                    depunctured.expanded_values,
                    depunctured.observed_mask,
                    84);
                const auto d84_us =
                    std::chrono::duration<double, std::micro>(
                        Clock::now() - d84_start)
                        .count();
                add(d84_aggregate,
                    payload,
                    d84.payload,
                    block.payload_bits,
                    d84.traceback_operations,
                    d84_us);
                const auto d112_start = Clock::now();
                const auto d112 = truncated(
                    trellis,
                    depunctured.expanded_values,
                    depunctured.observed_mask,
                    112);
                const auto d112_us =
                    std::chrono::duration<double, std::micro>(
                        Clock::now() - d112_start)
                        .count();
                add(d112_aggregate,
                    payload,
                    d112.payload,
                    block.payload_bits,
                    d112.traceback_operations,
                    d112_us);
            }
            const double actual_rate =
                static_cast<double>(kPayload) / transmitted_bits;
            write_row(output,
                      target,
                      "BLOCK_FULL_TRACEBACK",
                      kCodec,
                      block_aggregate,
                      rate.pattern,
                      actual_rate,
                      sigma_squared);
            write_row(output,
                      target,
                      "CONTINUOUS_TRUNCATED_D84",
                      84,
                      d84_aggregate,
                      rate.pattern,
                      actual_rate,
                      sigma_squared);
            write_row(output,
                      target,
                      "CONTINUOUS_TRUNCATED_D112",
                      112,
                      d112_aggregate,
                      rate.pattern,
                      actual_rate,
                      sigma_squared);
            std::cout << "reference " << target.rate_case << ' '
                      << target.snr_db << " frames=" << target.frames
                      << '\n';
            ++processed;
        }
        std::cout << "PASS_STAGE13_REFERENCE_REPLAY rows="
                  << processed * 3 << " shard=" << shard_index << '/'
                  << shard_count << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE13_REFERENCE: " << error.what() << '\n';
        return 1;
    }
}
