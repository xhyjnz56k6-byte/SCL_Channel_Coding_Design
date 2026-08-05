#include "s7/s7.hpp"

#include "common/sha256.hpp"

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {
struct Candidate { std::string scheme; std::string method; std::size_t parameter; s7::Mapping mapping; };
struct Aggregate {
    std::size_t frames=0, bitErrors=0, frameErrors=0, totalBits=0;
    double interleaveNs=0, deinterleaveNs=0, decodeNs=0;
};
void addHash(scl::common::Sha256& hash, const std::vector<std::uint8_t>& values) { hash.update(values); }
void addHash(scl::common::Sha256& hash, const std::vector<double>& values) {
    hash.update(reinterpret_cast<const std::uint8_t*>(values.data()), values.size()*sizeof(double));
}
}

int main(int argc, char** argv) {
    try {
        if (argc < 2 || argc > 3) throw std::invalid_argument("usage: s7_prescan OUTPUT_DIRECTORY [FRAMES_PER_CASE]");
        const fs::path output=fs::absolute(argv[1]); fs::create_directories(output);
        const std::size_t frames=argc==3 ? std::stoul(argv[2]) : 30;
        if (frames<10 || frames>200) throw std::invalid_argument("prescan frames must be in [10,200]");
        std::vector<Candidate> candidates;
        const s7::BchCodecContext bchContext;
        candidates.push_back({"BCH","NONE",0,s7::makeBchMapping(s7::BchInterleaver::None)});
        for (std::size_t d:{4U,8U,16U,19U}) candidates.push_back({"BCH","BCH_CODEBLOCK",d,s7::makeBchMapping(s7::BchInterleaver::Codeblock,d)});
        for (std::size_t r:{4U,8U,15U,19U}) candidates.push_back({"BCH","ROW_COLUMN",r,s7::makeBchMapping(s7::BchInterleaver::RowColumn,r)});
        candidates.push_back({"BCH","GLOBAL_PSEUDORANDOM",285,s7::makeBchMapping(s7::BchInterleaver::GlobalPseudorandom,285)});
        candidates.push_back({"CC","NONE",0,s7::makeCcMapping(s7::CcInterleaver::None)});
        for (std::size_t d:{4U,8U,16U}) candidates.push_back({"CC","SHORT_DEPTH_BLOCK",d,s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock,d)});
        for (std::size_t span:{32U,64U,128U}) candidates.push_back({"CC","PSEUDORANDOM",span,s7::makeCcMapping(s7::CcInterleaver::Pseudorandom,span)});
        const std::vector<double> snrs{4.0,8.0}, ratios{0.02,0.05,0.10};
        const std::vector<s7::BurstPosition> positions{s7::BurstPosition::Head,s7::BurstPosition::Quarter,s7::BurstPosition::Middle,s7::BurstPosition::ThreeQuarter,s7::BurstPosition::Tail,s7::BurstPosition::Random};
        std::ofstream csv(output/"prescan_raw.csv");
        csv << "scheme,method,parameter,fairnessGroupId,spanBits,spanTrellisSteps,bufferBits,mappingHash,EsN0Db,sigmaSquared,burstRatioRequested,burstLengthBits,burstRatioActual,burstPositionType,framesProcessed,totalBits,bitErrors,frameErrors,BER,FER,interleaveTimeMeanNs,deinterleaveTimeMeanNs,decodeTimeMeanNs,payloadChecksum,noiseChecksum,burstStartChecksum,frameSequenceHash\n" << std::setprecision(17);
        for (const Candidate& candidate:candidates) {
            const std::size_t length=candidate.scheme=="BCH"?s7::kBchEncodedBits:s7::kCcEncodedBits;
            const std::size_t payloadLength=candidate.scheme=="BCH"?s7::kBchPayloadBits:s7::kCcPayloadBits;
            for (double snr:snrs) for (double ratio:ratios) for (auto position:positions) {
                Aggregate agg; scl::common::Sha256 payloadHash,noiseHash,burstHash,frameHash;
                const double variance=s7::sigmaSquaredFromEsN0(snr);
                s7::BurstSpec lastBurst;
                for (std::size_t frame=0;frame<frames;++frame) {
                    const std::uint64_t frameIndex=frame;
                    const auto payload=s7::deterministicPayload(payloadLength,frameIndex);
                    const auto noise=s7::deterministicStandardNoise(length,frameIndex);
                    const auto burst=s7::makeBurstSpec(length,ratio,position,frameIndex);
                    lastBurst=burst; addHash(payloadHash,payload); addHash(noiseHash,noise);
                    const std::string burstText=std::to_string(frameIndex)+":"+std::to_string(burst.start)+":"+std::to_string(burst.lengthBits)+";";
                    burstHash.update(burstText); frameHash.update(std::to_string(frameIndex)+",");
                    std::size_t errors=0; s7::DecodeTiming timing;
                    if (candidate.scheme=="BCH") { const auto r=s7::runBchFrame(bchContext,payload,candidate.mapping,noise,variance,burst); errors=r.bitErrors; timing=r.timing; }
                    else { const auto r=s7::runCcFrame(payload,candidate.mapping,noise,variance,burst); errors=r.bitErrors; timing=r.timing; }
                    ++agg.frames; agg.totalBits+=payloadLength; agg.bitErrors+=errors; agg.frameErrors+=errors!=0;
                    agg.interleaveNs+=timing.interleaveTimeNs; agg.deinterleaveNs+=timing.deinterleaveTimeNs; agg.decodeNs+=timing.decodeTimeNs;
                }
                csv << candidate.scheme << ',' << candidate.method << ',' << candidate.parameter << ',' << candidate.mapping.fairnessGroupId << ','
                    << candidate.mapping.spanBits << ',' << candidate.mapping.spanTrellisSteps << ',' << candidate.mapping.bufferBits << ',' << candidate.mapping.sha256 << ','
                    << snr << ',' << variance << ',' << ratio << ',' << lastBurst.lengthBits << ',' << double(lastBurst.lengthBits)/length << ','
                    << s7::burstPositionName(position) << ',' << agg.frames << ',' << agg.totalBits << ',' << agg.bitErrors << ',' << agg.frameErrors << ','
                    << double(agg.bitErrors)/agg.totalBits << ',' << double(agg.frameErrors)/agg.frames << ',' << agg.interleaveNs/agg.frames << ','
                    << agg.deinterleaveNs/agg.frames << ',' << agg.decodeNs/agg.frames << ',' << payloadHash.finalHex() << ',' << noiseHash.finalHex() << ','
                    << burstHash.finalHex() << ',' << frameHash.finalHex() << '\n';
            }
        }
        std::ofstream checkpoint(output/"checkpoint_recovery_plan.json");
        checkpoint << "{\n  \"schemaVersion\": \"s7-checkpoint-v1\",\n  \"checkpointIntervalFrames\": 1000,\n"
                   << "  \"requiredFields\": [\"configHash\",\"caseKey\",\"nextFrameIndex\",\"counts\",\"timingSamples\",\"frameSequenceHash\"],\n"
                   << "  \"resumeGate\": \"NO_DUPLICATE_OR_SKIPPED_FRAME_AND_HASH_EQUAL\"\n}\n";
        std::ofstream readme(output/"readme.txt");
        readme << "阶段名称：stage09_parameter_prescan\n实验目的：以固定小样本比较参数候选，不生成 Formal 结论。\n"
               << "主要输入：Es/N0={0,4} dB、突发比例={5%,10%}、六位置、每 case " << frames << " 帧。\n"
               << "完成内容：BCH/CC 所有冻结候选的固定帧预扫描。\n主要输出：prescan_raw.csv、checkpoint_recovery_plan.json。\n"
               << "当前结论：必须经排名 checker 后给出候选。\n已知问题：样本量只适合筛选，不能替代 Formal。\n阶段状态：PARTIAL_PASS\n";
        std::cout << "PASS_S7_PRESCAN_RAW " << output.string() << '\n'; return 0;
    } catch (const std::exception& error) { std::cerr << "FAIL_S7_PRESCAN: " << error.what() << '\n'; return 1; }
}
