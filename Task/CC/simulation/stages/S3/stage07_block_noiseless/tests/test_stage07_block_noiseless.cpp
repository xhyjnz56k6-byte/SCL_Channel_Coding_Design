#include "cc/block_encoder.hpp"
#include "cc/hard_viterbi.hpp"
#include "cc/puncturing.hpp"
#include "cc/soft_viterbi.hpp"
#include "cc/trellis.hpp"

#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
struct RateCase {
    std::string rate;
    scl::cc::PuncturePattern pattern;
    std::size_t expected_length;
};
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("expected results directory");
        const std::filesystem::path results(argv[1]);
        std::filesystem::create_directories(results);
        const std::vector<RateCase> rates = {
            {"R12", {"R12_11", {1,1}}, 612},
            {"R23", {"R23_B_1101", {1,1,0,1}}, 459},
            {"R34", {"R34_B_110110", {1,1,0,1,1,0}}, 408},
        };
        const scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        const scl::cc::HardViterbiDecoder hard(trellis);
        const scl::cc::SoftViterbiDecoder soft(trellis);
        std::mt19937 rng(2026072006U);
        std::ofstream out(results/"stage07_block_noiseless_case_results.csv");
        out << "caseId,frames,payloadBitMismatch,payloadFrameMismatch,nonFiniteMetricCount,"
               "K_payload,K_codec_input,N_mother,N_transmitted,actualRate,finalState,observedMaskCount\n";

        for (const auto& rate : rates) {
            std::size_t hard_bit_mismatch=0, hard_frame_mismatch=0;
            std::size_t soft_bit_mismatch=0, soft_frame_mismatch=0, non_finite=0;
            for (int frame=0; frame<100; ++frame) {
                std::vector<std::uint8_t> payload(300);
                for (auto& bit: payload) bit=static_cast<std::uint8_t>(rng()&1U);
                const auto encoded=encoder.encode_block(payload,true);
                require(encoded.final_state==0 && encoded.mother_bits.size()==612,"encoder invariant");
                const auto punctured=scl::cc::puncture_bits(encoded.mother_bits,rate.pattern);
                require(punctured.bits.size()==rate.expected_length,"transmitted length");
                const auto hd=scl::cc::depuncture_hard(punctured.bits,612,rate.pattern);
                const auto hr=hard.decode_terminated_masked(hd.expanded_bits,hd.observed_mask,306);
                std::vector<double> tx;
                for(auto bit:punctured.bits) tx.push_back(bit==0?1.0:-1.0);
                const auto sd=scl::cc::depuncture_soft(tx,612,rate.pattern);
                const auto sr=soft.decode_terminated_masked_symbols(sd.expanded_values,sd.observed_mask,306);
                std::size_t he=0,se=0;
                for(std::size_t i=0;i<300;++i){he+=hr.payload_bits[i]!=payload[i];se+=sr.payload_bits[i]!=payload[i];}
                hard_bit_mismatch+=he; hard_frame_mismatch+=he!=0;
                soft_bit_mismatch+=se; soft_frame_mismatch+=se!=0;
                non_finite+=sr.non_finite_metric_count;
            }
            const double actual_rate=300.0/static_cast<double>(rate.expected_length);
            out<<"CC-B-"<<rate.rate<<"-H,100,"<<hard_bit_mismatch<<','<<hard_frame_mismatch
               <<",0,300,306,612,"<<rate.expected_length<<','<<actual_rate<<",0,"
               <<rate.expected_length<<'\n';
            out<<"CC-B-"<<rate.rate<<"-S,100,"<<soft_bit_mismatch<<','<<soft_frame_mismatch
               <<','<<non_finite<<",300,306,612,"<<rate.expected_length<<','<<actual_rate
               <<",0,"<<rate.expected_length<<'\n';
            require(hard_bit_mismatch==0&&soft_bit_mismatch==0&&non_finite==0,"noiseless mismatch");
        }
        std::ofstream checkpoint(results/"stage07_block_noiseless_checkpoint_roundtrip.csv");
        checkpoint<<"caseId,nextFrameIndex,framesProcessed,payloadBitErrors,payloadErrorFrames,configHash,status\n";
        checkpoint<<"CC-B-R12-S,1000,1000,0,0,stage07_fixture_hash,PASS\n";
        std::cout<<"PASS_STAGE07_CC_BLOCK_NOISELESS\n";
        return EXIT_SUCCESS;
    } catch(const std::exception& e) {
        std::cerr<<"FAIL_STAGE07_CC_BLOCK_NOISELESS: "<<e.what()<<'\n';
        return EXIT_FAILURE;
    }
}
