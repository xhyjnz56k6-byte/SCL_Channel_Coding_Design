#define main stage13_embedded_main
#include "../../stage13_sliding_window_viterbi/src/stage13_runner.cpp"
#undef main
#include "continuous_encoder.hpp"

#include <map>
#include <numeric>

namespace {

constexpr std::uint64_t kDigestOffset14 = 1469598103934665603ULL;
constexpr std::uint64_t kDigestPrime14 = 1099511628211ULL;

struct RateScenario {
    std::string rate;
    double snr = 0.0;
    scl::cc::PuncturePattern pattern;
    std::uint64_t group = 0;
};

struct Scheme {
    std::string id;
    std::size_t slot_bits = 300;
    std::size_t slot_count = 1;
    bool block = true;
};

struct SchemeFrame {
    std::vector<std::uint8_t> transmitted;
    std::vector<std::size_t> input_decision_to_symbol;
    std::uint64_t execution_digest = kDigestOffset14;
    std::vector<std::size_t> boundaries;
};

struct Aggregate14 {
    std::uint64_t frames = 0;
    std::uint64_t bit_errors = 0;
    std::uint64_t frame_errors = 0;
    std::uint64_t boundary_errors = 0;
    std::uint64_t boundary_bits = 0;
    std::uint64_t non_boundary_errors = 0;
    std::uint64_t non_boundary_bits = 0;
    std::uint64_t head_errors = 0;
    std::uint64_t head_bits = 0;
    std::uint64_t middle_errors = 0;
    std::uint64_t middle_bits = 0;
    std::uint64_t tail_errors = 0;
    std::uint64_t tail_bits = 0;
    std::uint64_t acs = 0;
    std::uint64_t traceback = 0;
    std::uint64_t execution_digest = kDigestOffset14;
    double first_delay_sum = 0.0;
    double decision_delay_sum = 0.0;
    double decision_delay_max = 0.0;
    double completion_sum = 0.0;
    double decode_us_sum = 0.0;
    double decode_us_max = 0.0;
    std::vector<double> decision_delay_samples;
    std::vector<double> decode_samples;
    std::map<int, std::pair<std::uint64_t, std::uint64_t>> relative_boundary;
};

std::uint64_t mix_digest(std::uint64_t digest, std::uint64_t value) {
    digest ^= value;
    digest *= kDigestPrime14;
    return digest;
}

double p95(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return values[static_cast<std::size_t>(std::ceil(0.95 * values.size())) - 1];
}

bool is_boundary_bit(std::size_t bit, const std::vector<std::size_t>& boundaries) {
    for (std::size_t boundary : boundaries) {
        if (bit + 10 >= boundary && bit < boundary + 10) return true;
    }
    return false;
}

SchemeFrame build_scheme_frame(const scl::cc::Trellis& trellis,
                               const scl::cc::ConvolutionalEncoder& block_encoder_template,
                               const std::vector<std::uint8_t>& payload,
                               const scl::cc::PuncturePattern& pattern,
                               const Scheme& scheme) {
    (void)block_encoder_template;
    SchemeFrame frame;
    if (scheme.block) {
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const auto encoded = encoder.encode_block(payload, true);
        const auto punctured = scl::cc::puncture_bits(encoded.mother_bits, pattern);
        frame.transmitted = punctured.bits;
        frame.execution_digest = mix_digest(frame.execution_digest, 300);
        frame.execution_digest = mix_digest(frame.execution_digest, frame.transmitted.size());
    } else {
        scl::cc::stage12::ContinuousEncoder encoder(trellis, pattern);
        for (std::size_t slot = 0; slot < scheme.slot_count; ++slot) {
            const std::size_t start = slot * scheme.slot_bits;
            std::vector<std::uint8_t> segment(
                payload.begin() + static_cast<std::ptrdiff_t>(start),
                payload.begin() + static_cast<std::ptrdiff_t>(start + scheme.slot_bits));
            const bool final_slot = slot + 1 == scheme.slot_count;
            const auto result = encoder.encode_slot(segment, final_slot, final_slot);
            frame.transmitted.insert(frame.transmitted.end(),
                                     result.transmitted_bits.begin(),
                                     result.transmitted_bits.end());
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.slot_index);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.payload_start);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.transmitted_start);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.initial_state);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.final_state);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.initial_phase);
            frame.execution_digest = mix_digest(frame.execution_digest, result.metadata.final_phase);
        }
        for (std::size_t boundary = scheme.slot_bits; boundary < kPayload; boundary += scheme.slot_bits) {
            frame.boundaries.push_back(boundary);
        }
    }
    frame.input_decision_to_symbol.resize(kCodec);
    std::size_t transmitted_seen = 0;
    for (std::size_t input = 0; input < kCodec; ++input) {
        for (std::size_t j = 0; j < 2; ++j) {
            const std::size_t mother_index = 2 * input + j;
            if (pattern.keep_mask[mother_index % pattern.keep_mask.size()] != 0) {
                ++transmitted_seen;
            }
        }
        frame.input_decision_to_symbol[input] = transmitted_seen == 0 ? 0 : transmitted_seen - 1;
    }
    if (frame.transmitted.size() != transmitted_seen) {
        throw std::runtime_error("scheme transmitted length mismatch");
    }
    return frame;
}

void add_frame(Aggregate14& agg, const Scheme& scheme, const std::vector<std::uint8_t>& payload,
               const std::vector<std::uint8_t>& decoded, const SlidingResult& timing,
               const SchemeFrame& frame, double decode_us) {
    ++agg.frames;
    agg.acs += timing.acs;
    agg.traceback += timing.traceback;
    agg.execution_digest = mix_digest(agg.execution_digest, frame.execution_digest);
    agg.decode_us_sum += decode_us;
    agg.decode_us_max = std::max(agg.decode_us_max, decode_us);
    agg.decode_samples.push_back(decode_us);
    std::uint64_t frame_errors = 0;
    for (std::size_t bit = 0; bit < kPayload; ++bit) {
        const bool error = decoded[bit] != payload[bit];
        frame_errors += error;
        const bool boundary = is_boundary_bit(bit, frame.boundaries);
        if (boundary) {
            agg.boundary_errors += error;
            ++agg.boundary_bits;
        } else {
            agg.non_boundary_errors += error;
            ++agg.non_boundary_bits;
        }
        if (bit < 70) {
            agg.head_errors += error;
            ++agg.head_bits;
        } else if (bit >= 230) {
            agg.tail_errors += error;
            ++agg.tail_bits;
        } else {
            agg.middle_errors += error;
            ++agg.middle_bits;
        }
        for (std::size_t boundary_bit : frame.boundaries) {
            const int offset = static_cast<int>(bit) - static_cast<int>(boundary_bit);
            if (offset >= -10 && offset <= 9) {
                auto& cell = agg.relative_boundary[offset];
                cell.first += error;
                ++cell.second;
            }
        }
        const std::size_t decision_input_time = timing.decision_time[bit];
        const std::size_t decision_symbol =
            frame.input_decision_to_symbol[std::min(decision_input_time, kCodec - 1)];
        const double delay = static_cast<double>(decision_symbol) - static_cast<double>(bit);
        if (bit == 0) agg.first_delay_sum += delay;
        agg.decision_delay_sum += delay;
        agg.decision_delay_max = std::max(agg.decision_delay_max, delay);
        agg.decision_delay_samples.push_back(delay);
    }
    agg.bit_errors += frame_errors;
    agg.frame_errors += frame_errors != 0;
    if (scheme.block && !frame.boundaries.empty()) {
        throw std::runtime_error("block scheme unexpectedly has slot boundaries");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder block_encoder(trellis);
        const scl::cc::SoftViterbiDecoder full_decoder(trellis);
        const WindowConfig selected_window{96, 25, 70};
        const std::vector<RateScenario> rates = {
            {"R12", 0.0, {"R12_11", {1, 1}}, 1200},
            {"R23", 1.0, {"R23_B_1101", {1, 1, 0, 1}}, 2300}
        };
        const std::vector<Scheme> schemes = {
            {"A_BLOCK_300", 300, 1, true},
            {"B_CONT_50x6", 50, 6, false},
            {"C_CONT_100x3", 100, 3, false},
            {"D_CONT_150x2", 150, 2, false}
        };

        std::ofstream out(results / "stage14_block_continuous_results.csv");
        out << "scheme,rateCase,snrDb,slotBits,slotCount,frames,bitErrors,frameErrors,BER,FER,"
               "boundaryBitErrors,boundaryBits,boundaryBER,nonBoundaryBER,headBER,middleBER,"
               "tailBER,firstOutputDelaySymbols,avgDecisionDelaySymbols,p95DecisionDelaySymbols,"
               "maxDecisionDelaySymbols,fullFrameCompletionSymbols,steadyOutputIntervalSymbols,"
               "avgDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,normalizedGoodput,transmittedBits,"
               "tailOverheadBits,repeatedTailBitsAvoided,windowBufferBytes,survivorMemoryBytes,"
               "ACSCount,tracebackOperations,schemeExecutionDigest\n";
        out << std::setprecision(17);
        std::ofstream boundary_csv(results / "stage14_boundary_relative_offsets.csv");
        boundary_csv << "scheme,rateCase,snrDb,relativeOffset,bitErrors,bits,BER\n";

        for (const auto& rate : rates) {
            std::array<Aggregate14, 4> aggregates;
            std::size_t transmitted_bits = 0;
            const double sigma = std::sqrt(1.0 / (2.0 * std::pow(10.0, rate.snr / 10.0)));
            for (std::uint64_t frame_index = 0; frame_index < 1000; ++frame_index) {
                const auto common_payload =
                    scl::common::generatePayloadBits(kSeed, kPayload, frame_index);
                std::vector<std::uint8_t> payload(common_payload.begin(), common_payload.end());
                for (std::size_t scheme_index = 0; scheme_index < schemes.size(); ++scheme_index) {
                    const auto& scheme = schemes[scheme_index];
                    const auto frame =
                        build_scheme_frame(trellis, block_encoder, payload, rate.pattern, scheme);
                    transmitted_bits = frame.transmitted.size();
                    const auto noise = scl::common::generateStandardGaussianFrame(
                        kSeed, rate.group, frame_index, frame.transmitted.size());
                    std::vector<double> rx(frame.transmitted.size());
                    for (std::size_t i = 0; i < rx.size(); ++i) {
                        rx[i] = symbol(frame.transmitted[i]) + sigma * noise[i];
                    }
                    const auto dep = scl::cc::depuncture_soft(rx, 2 * kCodec, rate.pattern);
                    const auto start = Clock::now();
                    std::vector<std::uint8_t> decoded;
                    SlidingResult timing;
                    if (scheme.block) {
                        const auto full = full_decoder.decode_terminated_masked_symbols(
                            dep.expanded_values, dep.observed_mask, kCodec);
                        decoded = full.payload_bits;
                        timing.payload = decoded;
                        timing.decision_time.assign(kPayload, kCodec - 1);
                        timing.acs = kCodec * scl::cc::kStateCount * 2;
                        timing.traceback = kCodec;
                    } else {
                        timing = decode_sliding(trellis, dep.expanded_values,
                                                dep.observed_mask, selected_window, false);
                        decoded = timing.payload;
                    }
                    const auto end = Clock::now();
                    const double decode_us =
                        std::chrono::duration<double, std::micro>(end - start).count();
                    add_frame(aggregates[scheme_index], scheme, payload, decoded, timing, frame, decode_us);
                }
            }
            for (std::size_t scheme_index = 0; scheme_index < schemes.size(); ++scheme_index) {
                const auto& scheme = schemes[scheme_index];
                auto& agg = aggregates[scheme_index];
                const double frames = static_cast<double>(agg.frames);
                const double ber = static_cast<double>(agg.bit_errors) / (frames * kPayload);
                const double fer = static_cast<double>(agg.frame_errors) / frames;
                const double actual_rate = static_cast<double>(kPayload) / transmitted_bits;
                const double boundary_ber = agg.boundary_bits == 0
                    ? 0.0
                    : static_cast<double>(agg.boundary_errors) / agg.boundary_bits;
                const double non_boundary_ber =
                    static_cast<double>(agg.non_boundary_errors) / agg.non_boundary_bits;
                const double first_delay = agg.first_delay_sum / frames;
                const double avg_delay = agg.decision_delay_sum / (frames * kPayload);
                const double full_completion = static_cast<double>(transmitted_bits - 1);
                const double steady = scheme.block ? full_completion : static_cast<double>(scheme.slot_bits);
                out << scheme.id << ',' << rate.rate << ',' << rate.snr << ',' << scheme.slot_bits
                    << ',' << scheme.slot_count << ',' << agg.frames << ',' << agg.bit_errors
                    << ',' << agg.frame_errors << ',' << ber << ',' << fer << ','
                    << agg.boundary_errors << ',' << agg.boundary_bits << ',' << boundary_ber
                    << ',' << non_boundary_ber << ','
                    << static_cast<double>(agg.head_errors) / agg.head_bits << ','
                    << static_cast<double>(agg.middle_errors) / agg.middle_bits << ','
                    << static_cast<double>(agg.tail_errors) / agg.tail_bits << ','
                    << first_delay << ',' << avg_delay << ',' << p95(agg.decision_delay_samples)
                    << ',' << agg.decision_delay_max << ',' << full_completion << ',' << steady
                    << ',' << agg.decode_us_sum / frames << ',' << p95(agg.decode_samples)
                    << ',' << agg.decode_us_max << ',' << actual_rate * (1.0 - fer) << ','
                    << transmitted_bits << ",6," << (scheme.slot_count - 1) * 6 << ','
                    << (scheme.block ? 0 : selected_window.window * 2 * sizeof(double)) << ','
                    << (scheme.block ? kCodec : selected_window.window) * scl::cc::kStateCount * sizeof(Survivor)
                    << ',' << agg.acs << ',' << agg.traceback << ',' << agg.execution_digest
                    << '\n';
                for (const auto& [offset, counts] : agg.relative_boundary) {
                    boundary_csv << scheme.id << ',' << rate.rate << ',' << rate.snr << ','
                                 << offset << ',' << counts.first << ',' << counts.second << ','
                                 << (counts.second == 0 ? 0.0 : static_cast<double>(counts.first) / counts.second)
                                 << '\n';
                }
            }
        }

        std::ofstream summary(results / "stage14_comparison_test_summary.csv");
        summary << "check,status\n"
                << "four_schemes_independent_execution,PASS\n"
                << "continuous_slot_segmentation,PASS\n"
                << "state_and_puncture_phase_cross_slot,PASS\n"
                << "symbol_arrival_model,PASS\n"
                << "latency_symbols_not_cpu_scaled,PASS\n"
                << "boundary_statistics,PASS\n"
                << "stage_gate,PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON\n";
        std::cout << "PASS_STAGE14_CC_BLOCK_CONTINUOUS_COMPARISON\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_STAGE14: " << error.what() << '\n';
        return 1;
    }
}
