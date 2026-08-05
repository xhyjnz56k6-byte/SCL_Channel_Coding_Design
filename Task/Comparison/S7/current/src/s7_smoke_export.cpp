#include "s7/s7.hpp"

#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <sstream>

namespace fs = std::filesystem;

namespace {
std::string bitsToString(const std::vector<std::uint8_t>& bits) {
    std::string text; text.reserve(bits.size());
    for (std::uint8_t bit : bits) text.push_back(bit == 0 ? '0' : '1');
    return text;
}
}

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("usage: s7_smoke_export OUTPUT_DIRECTORY");
        const fs::path output = fs::absolute(argv[1]);
        fs::create_directories(output);
        std::ofstream mappingFile(output / "mapping_vectors.csv");
        mappingFile << "scheme,method,parameter,output_index,input_index,mapping_sha256,permutation_unit,preserve_pair,span_bits,span_trellis_steps,buffer_bits,fairness_group\n";
        auto writeMapping = [&](const std::string& scheme, std::size_t parameter, const s7::Mapping& mapping) {
            for (std::size_t i = 0; i < mapping.outputToInput.size(); ++i)
                mappingFile << scheme << ',' << mapping.method << ',' << parameter << ',' << i << ',' << mapping.outputToInput[i]
                            << ',' << mapping.sha256 << ',' << mapping.permutationUnit << ',' << (mapping.preserveMotherOutputPair ? 1 : 0)
                            << ',' << mapping.spanBits << ',' << mapping.spanTrellisSteps << ',' << mapping.bufferBits << ',' << mapping.fairnessGroupId << '\n';
        };
        writeMapping("BCH", 0, s7::makeBchMapping(s7::BchInterleaver::None));
        for (std::size_t value : {4U,8U,16U,19U}) writeMapping("BCH", value, s7::makeBchMapping(s7::BchInterleaver::Codeblock, value));
        for (std::size_t value : {4U,8U,15U,19U}) writeMapping("BCH", value, s7::makeBchMapping(s7::BchInterleaver::RowColumn, value));
        writeMapping("BCH", 285, s7::makeBchMapping(s7::BchInterleaver::GlobalPseudorandom, 285));
        writeMapping("CC", 0, s7::makeCcMapping(s7::CcInterleaver::None));
        for (std::size_t value : {4U,8U,16U}) writeMapping("CC", value, s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock, value));
        for (std::size_t value : {32U,64U,128U}) writeMapping("CC", value, s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, value));

        std::ofstream channelFile(output / "channel_vector.csv");
        channelFile << "index,tx_bit,bpsk,burst_mask,standard_noise,received,hard_bit,llr\n";
        const auto bits = s7::deterministicPayload(32, 7);
        const auto noise = s7::deterministicStandardNoise(32, 7);
        const auto burst = s7::makeBurstSpec(32, 0.25, s7::BurstPosition::Middle, 7);
        const auto symbols = s7::bpskModulate(bits);
        const double variance = s7::sigmaSquaredFromEsN0(2.0);
        const auto received = s7::applyPolarityReversalAwgn(symbols, noise, variance, burst);
        const auto hard = s7::hardDecision(received);
        const auto llr = s7::llrFromReceived(received, variance);
        channelFile << std::setprecision(17);
        for (std::size_t i = 0; i < bits.size(); ++i)
            channelFile << i << ',' << unsigned(bits[i]) << ',' << symbols[i] << ','
                        << (i >= burst.start && i < burst.end ? 1 : 0) << ',' << noise[i] << ','
                        << received[i] << ',' << unsigned(hard[i]) << ',' << llr[i] << '\n';

        std::ofstream summary(output / "chain_summary.csv");
        summary << "scheme,method,parameter,payload_bits,encoded_bits,decoded_bits,bit_errors,traceback_final_state,mapping_sha256\n";
        const auto bchPayload = s7::deterministicPayload(s7::kBchPayloadBits, 9);
        const auto bchMap = s7::makeBchMapping(s7::BchInterleaver::Codeblock, 19);
        const auto bchResult = s7::runBchFrame(bchPayload, bchMap, std::vector<double>(s7::kBchEncodedBits, 0.0), 0.0,
                                              s7::makeBurstSpec(s7::kBchEncodedBits, 0.0, s7::BurstPosition::Head, 9));
        summary << "BCH," << bchMap.method << ",19,200,285," << bchResult.decodedPayload.size() << ',' << bchResult.bitErrors << ",NA," << bchMap.sha256 << '\n';
        const auto ccPayload = s7::deterministicPayload(s7::kCcPayloadBits, 9);
        const auto ccMap = s7::makeCcMapping(s7::CcInterleaver::Pseudorandom, 64);
        const auto ccResult = s7::runCcFrame(ccPayload, ccMap, std::vector<double>(s7::kCcEncodedBits, 0.0), 0.0,
                                            s7::makeBurstSpec(s7::kCcEncodedBits, 0.0, s7::BurstPosition::Head, 9));
        summary << "CC," << ccMap.method << ",64,300,612," << ccResult.decodedPayload.size() << ',' << ccResult.bitErrors << ','
                << unsigned(ccResult.tracebackFinalState) << ',' << ccMap.sha256 << '\n';

        const auto bchEncoded = scl::bch::segmented::encodeBch15Segmented(
            scl::bch::segmented::Bch15SegmentedCase::S200, bchPayload);
        std::ofstream bchCodec(output / "bch_codec_vector.csv");
        bchCodec << "vector_id,payload_bits,padded_message_bits,encoded_bits,decoded_payload_bits\n";
        bchCodec << "bch_noiseless," << bitsToString(bchPayload) << ',' << bitsToString(bchEncoded.paddedMessageBits) << ','
                 << bitsToString(bchEncoded.encodedBits) << ',' << bitsToString(bchResult.decodedPayload) << '\n';
        const auto syndromeTable = scl::bch::segmented::buildBch15SyndromeTable();
        std::ofstream syndrome(output / "bch_syndrome_vector.csv");
        syndrome << "error_position,syndrome,lookup_position\n";
        for (std::size_t position = 0; position < 15; ++position) {
            std::vector<std::uint8_t> error(15, 0); error[position] = 1;
            const unsigned value = scl::bch::segmented::syndromeValue(
                scl::bch::segmented::computeBch15Syndrome(error));
            syndrome << position << ',' << value << ',' << scl::bch::segmented::lookupErrorPosition(syndromeTable, value) << '\n';
        }

        scl::cc::Trellis trellis;
        scl::cc::ConvolutionalEncoder encoder(trellis);
        scl::cc::SoftViterbiDecoder decoder(trellis);
        const auto ccEncoded = encoder.encode_block(ccPayload, true, 0);
        std::ofstream ccCodec(output / "cc_codec_vector.csv");
        ccCodec << "vector_id,payload_bits,codec_input_bits,mother_bits,decoded_payload_bits,final_state,traceback_final_state,tie_count\n";
        ccCodec << "cc_noiseless," << bitsToString(ccPayload) << ',' << bitsToString(ccEncoded.codec_input_bits) << ','
                << bitsToString(ccEncoded.mother_bits) << ',' << bitsToString(ccResult.decodedPayload) << ','
                << unsigned(ccEncoded.final_state) << ',' << unsigned(ccResult.tracebackFinalState) << ',' << ccResult.tieCount << '\n';
        const auto tied = decoder.decode_terminated_symbols(std::vector<double>(s7::kCcEncodedBits, 0.0), s7::kCcTrellisSteps, 6, 0, 0);
        ccCodec << "cc_all_zero_metric," << bitsToString(std::vector<std::uint8_t>(s7::kCcPayloadBits, 0)) << ','
                << bitsToString(std::vector<std::uint8_t>(s7::kCcTrellisSteps, 0)) << ','
                << bitsToString(std::vector<std::uint8_t>(s7::kCcEncodedBits, 0)) << ',' << bitsToString(tied.payload_bits)
                << ",0," << unsigned(tied.traceback_final_state) << ',' << tied.tie_count << '\n';
        std::ofstream trellisFile(output / "cc_trellis_vector.csv");
        trellisFile << "state,input_bit,next_state,output_171,output_133,output_decimal\n";
        for (std::size_t state = 0; state < scl::cc::kStateCount; ++state)
            for (std::uint8_t input = 0; input < 2; ++input) {
                const auto& branch = trellis.branch(static_cast<std::uint8_t>(state), input);
                trellisFile << state << ',' << unsigned(input) << ',' << unsigned(branch.next_state) << ','
                            << unsigned(branch.output_bits[0]) << ',' << unsigned(branch.output_bits[1]) << ','
                            << unsigned(2 * branch.output_bits[0] + branch.output_bits[1]) << '\n';
            }
        std::ofstream readme(output / "readme.txt");
        readme << "阶段名称：stage08_cpp_matlab_smoke\n实验目的：导出固定映射、信道和无噪声链路向量。\n"
               << "主要输入：冻结的 S7 Smoke 配置。\n完成内容：C++ 固定向量导出。\n主要输出：mapping、channel、BCH syndrome/codec、CC trellis/codec 和 chain summary CSV。\n"
               << "当前结论：必须经 MATLAB/reference checker 后确定 Gate。\n已知问题：本文件不代表 Formal。\n阶段状态：PARTIAL_PASS\n";
        std::cout << "PASS_S7_SMOKE_EXPORT " << output.string() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S7_SMOKE_EXPORT: " << error.what() << '\n'; return 1;
    }
}
