#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
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
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr std::uint64_t kSeed = 2026072001ULL;
constexpr std::uint64_t kCheckpointMagic = 0x4343533346573039ULL;
constexpr std::uint64_t kDigestOffset = 1469598103934665603ULL;
constexpr std::uint64_t kDigestPrime = 1099511628211ULL;

struct Options {
    std::filesystem::path runtime;
    std::uint64_t shard_index = 0;
    std::uint64_t shard_count = 1;
    std::uint64_t min_frames = 5000;
    std::uint64_t target_errors = 200;
    std::uint64_t max_frames = 50000;
    std::uint64_t checkpoint_interval = 1000;
    std::int64_t only_unit = -1;
    std::uint64_t interrupt_after_checkpoints = 0;
    bool resume = false;
    bool two_level_coarse = false;
};

struct Rate {
    std::string id;
    scl::cc::PuncturePattern pattern;
    std::uint64_t noise_group = 0;
    int hard_min_tenth = 0;
    int hard_max_tenth = 0;
    int soft_min_tenth = 0;
    int soft_max_tenth = 0;
    int step_tenth = 1;
};

struct WorkUnit {
    std::size_t index = 0;
    Rate rate;
    int snr_tenth = 0;
    bool hard_active = false;
    bool soft_active = false;
};

struct Accumulator {
    std::uint64_t frames = 0;
    std::uint64_t bits = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t frame_digest = kDigestOffset;
    double encode_us = 0;
    double decode_us = 0;
    double max_encode_us = 0;
    double max_decode_us = 0;
    std::vector<double> decode_samples;
};

struct State {
    std::uint64_t next_frame = 0;
    Accumulator hard;
    Accumulator soft;
};

std::uint64_t parse_uint(const std::string& value, const std::string& name) {
    std::size_t used = 0;
    const auto parsed = std::stoull(value, &used);
    if (used != value.size()) {
        throw std::invalid_argument("invalid " + name);
    }
    return parsed;
}

Options parse_options(int argc, char** argv) {
    if (argc < 2) {
        throw std::invalid_argument("expected runtime directory");
    }
    Options options;
    options.runtime = argv[1];
    for (int i = 2; i < argc; ++i) {
        const std::string arg = argv[i];
        auto take = [&](const std::string& name) {
            if (++i >= argc) {
                throw std::invalid_argument("missing value for " + name);
            }
            return std::string(argv[i]);
        };
        if (arg == "--shard-index") options.shard_index = parse_uint(take(arg), arg);
        else if (arg == "--shard-count") options.shard_count = parse_uint(take(arg), arg);
        else if (arg == "--min-frames") options.min_frames = parse_uint(take(arg), arg);
        else if (arg == "--target-frame-errors") options.target_errors = parse_uint(take(arg), arg);
        else if (arg == "--max-frames") options.max_frames = parse_uint(take(arg), arg);
        else if (arg == "--checkpoint-interval") options.checkpoint_interval = parse_uint(take(arg), arg);
        else if (arg == "--unit-index") options.only_unit = static_cast<std::int64_t>(parse_uint(take(arg), arg));
        else if (arg == "--interrupt-after-checkpoints") {
            options.interrupt_after_checkpoints = parse_uint(take(arg), arg);
        } else if (arg == "--grid") {
            const std::string grid = take(arg);
            if (grid == "two-level-coarse") options.two_level_coarse = true;
            else if (grid != "legacy-formal") throw std::invalid_argument("unknown grid: " + grid);
        } else if (arg == "--resume") options.resume = true;
        else throw std::invalid_argument("unknown option: " + arg);
    }
    if (options.shard_count == 0 || options.shard_index >= options.shard_count) {
        throw std::invalid_argument("invalid shard coordinates");
    }
    if (options.min_frames == 0 || options.min_frames > options.max_frames ||
        options.checkpoint_interval == 0 || options.target_errors == 0) {
        throw std::invalid_argument("invalid stopping/checkpoint configuration");
    }
    return options;
}

std::vector<WorkUnit> work_units(bool two_level_coarse) {
    std::vector<Rate> rates;
    if (two_level_coarse) {
        rates = {
            {"R12", {"R12_11", {1, 1}}, 1200, -50, 100, -50, 100, 5},
            {"R23", {"R23_B_1101", {1, 1, 0, 1}}, 2300, -50, 100, -50, 100, 5},
            {"R34", {"R34_B_110110", {1, 1, 0, 1, 1, 0}}, 3400, -50, 100, -50, 100, 5}
        };
    } else {
        rates = {
            {"R12", {"R12_11", {1, 1}}, 1200, 0, 20, -20, 0, 2},
            {"R23", {"R23_B_1101", {1, 1, 0, 1}}, 2300, 10, 40, -5, 20, 1},
            {"R34", {"R34_B_110110", {1, 1, 0, 1, 1, 0}}, 3400, 20, 40, 5, 30, 1}
        };
    }
    std::vector<WorkUnit> units;
    for (const auto& rate : rates) {
        const int low = std::min(rate.hard_min_tenth, rate.soft_min_tenth);
        const int high = std::max(rate.hard_max_tenth, rate.soft_max_tenth);
        for (int snr = low; snr <= high; snr += rate.step_tenth) {
            WorkUnit unit;
            unit.index = units.size();
            unit.rate = rate;
            unit.snr_tenth = snr;
            unit.hard_active = snr >= rate.hard_min_tenth && snr <= rate.hard_max_tenth;
            unit.soft_active = snr >= rate.soft_min_tenth && snr <= rate.soft_max_tenth;
            units.push_back(unit);
        }
    }
    return units;
}

std::string unit_stem(std::size_t index) {
    std::ostringstream out;
    out << "unit_" << std::setw(3) << std::setfill('0') << index;
    return out.str();
}

template <class T>
void write_binary(std::ofstream& out, const T& value) {
    out.write(reinterpret_cast<const char*>(&value), sizeof(value));
    if (!out) throw std::runtime_error("checkpoint write failed");
}

template <class T>
void read_binary(std::ifstream& in, T& value) {
    in.read(reinterpret_cast<char*>(&value), sizeof(value));
    if (!in) throw std::runtime_error("checkpoint read failed");
}

void write_accumulator(std::ofstream& out, const Accumulator& value) {
    write_binary(out, value.frames);
    write_binary(out, value.bits);
    write_binary(out, value.bit_errors);
    write_binary(out, value.frame_errors);
    write_binary(out, value.frame_digest);
    write_binary(out, value.encode_us);
    write_binary(out, value.decode_us);
    write_binary(out, value.max_encode_us);
    write_binary(out, value.max_decode_us);
    const std::uint64_t count = value.decode_samples.size();
    write_binary(out, count);
    out.write(reinterpret_cast<const char*>(value.decode_samples.data()),
              static_cast<std::streamsize>(count * sizeof(double)));
    if (!out) throw std::runtime_error("checkpoint samples write failed");
}

void read_accumulator(std::ifstream& in, Accumulator& value) {
    read_binary(in, value.frames);
    read_binary(in, value.bits);
    read_binary(in, value.bit_errors);
    read_binary(in, value.frame_errors);
    read_binary(in, value.frame_digest);
    read_binary(in, value.encode_us);
    read_binary(in, value.decode_us);
    read_binary(in, value.max_encode_us);
    read_binary(in, value.max_decode_us);
    std::uint64_t count = 0;
    read_binary(in, count);
    if (count > 50000) throw std::runtime_error("checkpoint sample count invalid");
    value.decode_samples.resize(static_cast<std::size_t>(count));
    in.read(reinterpret_cast<char*>(value.decode_samples.data()),
            static_cast<std::streamsize>(count * sizeof(double)));
    if (!in) throw std::runtime_error("checkpoint samples read failed");
}

std::filesystem::path checkpoint_path(const Options& options,
                                      const WorkUnit& unit,
                                      std::uint64_t next_frame) {
    return options.runtime /
        (unit_stem(unit.index) + "_frame_" + std::to_string(next_frame) + ".chk");
}

void save_checkpoint(const Options& options, const WorkUnit& unit, const State& state) {
    const auto path = checkpoint_path(options, unit, state.next_frame);
    if (std::filesystem::exists(path)) {
        throw std::runtime_error("refusing to overwrite checkpoint: " + path.string());
    }
    std::ofstream out(path, std::ios::binary | std::ios::out);
    if (!out) throw std::runtime_error("cannot create checkpoint");
    write_binary(out, kCheckpointMagic);
    const std::uint64_t unit_index = unit.index;
    write_binary(out, unit_index);
    write_binary(out, options.min_frames);
    write_binary(out, options.target_errors);
    write_binary(out, options.max_frames);
    write_binary(out, options.checkpoint_interval);
    write_binary(out, state.next_frame);
    write_accumulator(out, state.hard);
    write_accumulator(out, state.soft);
}

bool load_latest_checkpoint(const Options& options, const WorkUnit& unit, State& state) {
    const std::string prefix = unit_stem(unit.index) + "_frame_";
    std::uint64_t best = 0;
    std::filesystem::path selected;
    for (const auto& entry : std::filesystem::directory_iterator(options.runtime)) {
        const std::string name = entry.path().filename().string();
        if (name.rfind(prefix, 0) != 0 || entry.path().extension() != ".chk") continue;
        const std::string number = name.substr(prefix.size(), name.size() - prefix.size() - 4);
        const auto frame = parse_uint(number, "checkpoint frame");
        if (selected.empty() || frame > best) {
            best = frame;
            selected = entry.path();
        }
    }
    if (selected.empty()) return false;
    std::ifstream in(selected, std::ios::binary);
    std::uint64_t magic = 0, unit_index = 0, min_frames = 0, target = 0, max_frames = 0, interval = 0;
    read_binary(in, magic);
    read_binary(in, unit_index);
    read_binary(in, min_frames);
    read_binary(in, target);
    read_binary(in, max_frames);
    read_binary(in, interval);
    if (magic != kCheckpointMagic || unit_index != unit.index ||
        min_frames != options.min_frames || target != options.target_errors ||
        max_frames != options.max_frames || interval != options.checkpoint_interval) {
        throw std::runtime_error("checkpoint configuration mismatch");
    }
    read_binary(in, state.next_frame);
    read_accumulator(in, state.hard);
    read_accumulator(in, state.soft);
    if (state.next_frame != best ||
        (unit.hard_active && state.hard.frames > state.next_frame) ||
        (unit.soft_active && state.soft.frames > state.next_frame)) {
        throw std::runtime_error("checkpoint continuity mismatch");
    }
    return true;
}

bool stopped(const Accumulator& value, const Options& options) {
    return (value.frames >= options.min_frames && value.frame_errors >= options.target_errors) ||
           value.frames >= options.max_frames;
}

std::uint64_t count_errors(const std::vector<std::uint8_t>& expected,
                           const std::vector<std::uint8_t>& actual) {
    if (expected.size() != actual.size()) throw std::runtime_error("decoded payload length mismatch");
    std::uint64_t count = 0;
    for (std::size_t i = 0; i < expected.size(); ++i) count += expected[i] != actual[i];
    return count;
}

void update_accumulator(Accumulator& value, std::uint64_t frame_index,
                        std::uint64_t bit_errors, double encode_us, double decode_us) {
    ++value.frames;
    value.bits += 300;
    value.bit_errors += bit_errors;
    value.frame_errors += bit_errors != 0;
    value.frame_digest ^= frame_index;
    value.frame_digest *= kDigestPrime;
    value.encode_us += encode_us;
    value.decode_us += decode_us;
    value.max_encode_us = std::max(value.max_encode_us, encode_us);
    value.max_decode_us = std::max(value.max_decode_us, decode_us);
    value.decode_samples.push_back(decode_us);
}

double percentile95(std::vector<double> values) {
    if (values.empty()) return 0;
    std::sort(values.begin(), values.end());
    return values[static_cast<std::size_t>(std::ceil(0.95 * values.size())) - 1];
}

std::string stop_reason(const Accumulator& value, const Options& options) {
    if (value.frames >= options.min_frames && value.frame_errors >= options.target_errors) {
        return "TARGET_ERRORS_REACHED";
    }
    if (value.frames >= options.max_frames) return "MAX_FRAMES_REACHED";
    throw std::runtime_error("attempted to write unfinished accumulator");
}

void write_result_row(std::ofstream& out, const WorkUnit& unit, const std::string& decoder,
                      const Accumulator& value, std::size_t transmitted,
                      const Options& options) {
    const double snr = static_cast<double>(unit.snr_tenth) / 10.0;
    const double rate = 300.0 / static_cast<double>(transmitted);
    const double sigma2 = 1.0 / (2.0 * std::pow(10.0, snr / 10.0));
    const double ber = static_cast<double>(value.bit_errors) / value.bits;
    const double fer = static_cast<double>(value.frame_errors) / value.frames;
    const double average_decode = value.decode_us / value.frames;
    const double raw_throughput = 300.0 / average_decode;
    out << "formal,CC-B-" << unit.rate.id << '-' << decoder << ',' << snr << ','
        << snr << ',' << snr - 10.0 * std::log10(rate) << ',' << rate << ',' << sigma2 << ','
        << transmitted << ",0," << value.frames << ',' << value.frames << ','
        << value.frame_digest << ',' << value.bit_errors << ',' << value.frame_errors << ','
        << ber << ',' << fer << ',' << 1.0 - fer << ','
        << value.encode_us / value.frames << ',' << value.max_encode_us << ','
        << average_decode << ',' << percentile95(value.decode_samples) << ','
        << value.max_decode_us << ',' << raw_throughput << ','
        << raw_throughput * (1.0 - fer) << ',' << rate * (1.0 - fer) << ','
        << stop_reason(value, options) << '\n';
}

int run_unit(const Options& options, const WorkUnit& unit, std::uint64_t& checkpoint_count) {
    const auto result_path = options.runtime / (unit_stem(unit.index) + ".csv");
    if (std::filesystem::exists(result_path)) {
        if (options.resume) return 0;
        throw std::runtime_error("refusing to overwrite unit result: " + result_path.string());
    }

    State state;
    if (options.resume) load_latest_checkpoint(options, unit, state);
    const scl::cc::Trellis trellis;
    scl::cc::ConvolutionalEncoder encoder(trellis);
    const scl::cc::HardViterbiDecoder hard_decoder(trellis);
    const scl::cc::SoftViterbiDecoder soft_decoder(trellis);
    const double snr = static_cast<double>(unit.snr_tenth) / 10.0;
    const double sigma = std::sqrt(1.0 / (2.0 * std::pow(10.0, snr / 10.0)));
    std::size_t transmitted = 0;

    while ((!unit.hard_active || stopped(state.hard, options)) == false ||
           (!unit.soft_active || stopped(state.soft, options)) == false) {
        const std::uint64_t frame = state.next_frame;
        const auto common_payload = scl::common::generatePayloadBits(kSeed, 300, frame);
        std::vector<std::uint8_t> payload(common_payload.begin(), common_payload.end());
        const auto encode_start = Clock::now();
        const auto encoded = encoder.encode_block(payload, true);
        const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, unit.rate.pattern);
        const auto encode_end = Clock::now();
        transmitted = punctured.bits.size();
        const auto noise = scl::common::generateStandardGaussianFrame(
            kSeed, unit.rate.noise_group, frame, transmitted);
        std::vector<double> received(transmitted);
        std::vector<std::uint8_t> hard_bits(transmitted);
        for (std::size_t i = 0; i < transmitted; ++i) {
            received[i] = (punctured.bits[i] == 0 ? 1.0 : -1.0) + sigma * noise[i];
            hard_bits[i] = received[i] >= 0 ? 0 : 1;
        }
        const double encode_us =
            std::chrono::duration<double, std::micro>(encode_end - encode_start).count();

        if (unit.hard_active && !stopped(state.hard, options)) {
            const auto depunctured = scl::cc::depuncture_hard(hard_bits, 612, unit.rate.pattern);
            const auto start = Clock::now();
            const auto decoded = hard_decoder.decode_terminated_masked(
                depunctured.expanded_bits, depunctured.observed_mask, 306);
            const auto end = Clock::now();
            update_accumulator(
                state.hard, frame, count_errors(payload, decoded.payload_bits), encode_us,
                std::chrono::duration<double, std::micro>(end - start).count());
        }
        if (unit.soft_active && !stopped(state.soft, options)) {
            const auto depunctured = scl::cc::depuncture_soft(received, 612, unit.rate.pattern);
            const auto start = Clock::now();
            const auto decoded = soft_decoder.decode_terminated_masked_symbols(
                depunctured.expanded_values, depunctured.observed_mask, 306);
            const auto end = Clock::now();
            update_accumulator(
                state.soft, frame, count_errors(payload, decoded.payload_bits), encode_us,
                std::chrono::duration<double, std::micro>(end - start).count());
        }
        ++state.next_frame;
        if (state.next_frame % options.checkpoint_interval == 0) {
            save_checkpoint(options, unit, state);
            ++checkpoint_count;
            if (options.interrupt_after_checkpoints != 0 &&
                checkpoint_count >= options.interrupt_after_checkpoints) {
                return 75;
            }
        }
    }

    if (transmitted == 0) {
        const auto encoded = encoder.encode_block(std::vector<std::uint8_t>(300, 0), true);
        transmitted = scl::cc::puncture_bits(encoded.mother_bits, unit.rate.pattern).bits.size();
    }
    std::ofstream out(result_path, std::ios::out);
    if (!out) throw std::runtime_error("cannot create unit result");
    out << "phase,caseId,snrDb,esN0Db,ebN0Db,actualRate,sigmaSquared,N_transmitted,"
           "frameStart,frameEndExclusive,framesProcessed,frameSequenceDigest,"
           "payloadBitErrors,payloadErrorFrames,BER,FER,payloadSuccessRate,"
           "avgEncodeTime_us,maxEncodeTime_us,avgDecodeTime_us,p95DecodeTime_us,"
           "maxDecodeTime_us,rawDecodeThroughput_Mbps,successfulDecodeThroughput_Mbps,"
           "normalizedGoodput,stopReason\n";
    out << std::setprecision(17);
    if (unit.hard_active) write_result_row(out, unit, "H", state.hard, transmitted, options);
    if (unit.soft_active) write_result_row(out, unit, "S", state.soft, transmitted, options);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        std::filesystem::create_directories(options.runtime);
        const auto units = work_units(options.two_level_coarse);
        if (options.only_unit >= static_cast<std::int64_t>(units.size())) {
            throw std::invalid_argument("unit index outside work list");
        }
        std::uint64_t checkpoint_count = 0;
        for (const auto& unit : units) {
            if (options.only_unit >= 0 && static_cast<std::size_t>(options.only_unit) != unit.index) continue;
            if (unit.index % options.shard_count != options.shard_index) continue;
            const int status = run_unit(options, unit, checkpoint_count);
            if (status == 75) {
                std::cout << "INTERRUPTED_AFTER_CHECKPOINT unit=" << unit.index << '\n';
                return 75;
            }
        }
        std::cout << "PASS_STAGE09_CC_AWGN_FORMAL_SHARD " << options.shard_index << '/'
                  << options.shard_count << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE09: " << error.what() << '\n';
        return 1;
    }
}
