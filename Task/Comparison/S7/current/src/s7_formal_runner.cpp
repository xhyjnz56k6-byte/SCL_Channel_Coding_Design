#include "s7/s7.hpp"

#include "common/sha256.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr std::size_t kMinFrames = 1000;
constexpr std::size_t kTargetFrameErrors = 200;
constexpr std::size_t kMaxFrames = 50000;
constexpr std::size_t kCheckpointInterval = 1000;
const std::string kConfigHash = scl::common::sha256Hex(
    "s7-formal-v2|-5:0.5:10|ratios=0.02,0.05,0.10|positions=6|paired=1000,200,50000|"
    "BCH=NONE,CODEBLOCK19,ROW15,GLOBAL285|CC=NONE,SHORT8,PSEUDO128,SHORT16_CONTROL128");

struct Candidate {
    std::string id;
    std::string method;
    std::size_t parameter = 0;
    std::string role;
    std::string engineeringGroup;
    std::string controlledGroup;
    s7::Mapping mapping;
};

struct Aggregate {
    std::uint64_t frames = 0, totalBits = 0, bitErrors = 0, frameErrors = 0;
    std::uint64_t affectedBlocks = 0, maximumErrorsInBlock = 0, correctedBlocks = 0;
    std::uint64_t detectedFailureFrames = 0, undetectedFrameErrors = 0, miscorrectedBlocks = 0;
    std::vector<double> decodeNs, interleaveNs, deinterleaveNs;
};

template <typename T> void writeValue(std::ofstream& out, const T& value) {
    out.write(reinterpret_cast<const char*>(&value), sizeof(T));
}
template <typename T> void readValue(std::ifstream& in, T& value) {
    in.read(reinterpret_cast<char*>(&value), sizeof(T));
    if (!in) throw std::runtime_error("truncated checkpoint");
}
void writeTimes(std::ofstream& out, const std::vector<double>& values) {
    const std::uint64_t size = values.size(); writeValue(out, size);
    out.write(reinterpret_cast<const char*>(values.data()), static_cast<std::streamsize>(size * sizeof(double)));
}
void readTimes(std::ifstream& in, std::vector<double>& values) {
    std::uint64_t size = 0; readValue(in, size);
    if (size > kMaxFrames) throw std::runtime_error("checkpoint timing vector too large");
    values.resize(static_cast<std::size_t>(size));
    in.read(reinterpret_cast<char*>(values.data()), static_cast<std::streamsize>(size * sizeof(double)));
    if (!in) throw std::runtime_error("truncated checkpoint timing vector");
}

void saveCheckpoint(const fs::path& path, const std::string& scheme, std::uint64_t groupIndex,
                    std::uint64_t nextFrame, const std::vector<Aggregate>& aggregates) {
    const fs::path temporary = path.string() + ".tmp";
    std::ofstream out(temporary, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot write checkpoint");
    const std::string magic = "S7CPV2__"; out.write(magic.data(), 8);
    const std::uint64_t schemeCode = scheme == "BCH" ? 1 : 2;
    writeValue(out, schemeCode); writeValue(out, groupIndex); writeValue(out, nextFrame);
    const std::uint64_t count = aggregates.size(); writeValue(out, count);
    out.write(kConfigHash.data(), static_cast<std::streamsize>(kConfigHash.size()));
    for (const Aggregate& value : aggregates) {
        writeValue(out,value.frames); writeValue(out,value.totalBits); writeValue(out,value.bitErrors); writeValue(out,value.frameErrors);
        writeValue(out,value.affectedBlocks); writeValue(out,value.maximumErrorsInBlock); writeValue(out,value.correctedBlocks);
        writeValue(out,value.detectedFailureFrames); writeValue(out,value.undetectedFrameErrors); writeValue(out,value.miscorrectedBlocks);
        writeTimes(out,value.decodeNs); writeTimes(out,value.interleaveNs); writeTimes(out,value.deinterleaveNs);
    }
    out.close();
    if (!out) throw std::runtime_error("checkpoint write failed");
    const fs::path previous = path.string() + ".prev";
    std::error_code error;
    fs::remove(previous,error); error.clear();
    if (fs::exists(path)) { fs::rename(path,previous,error); if (error) throw std::runtime_error("cannot rotate checkpoint"); }
    fs::rename(temporary,path,error); if (error) throw std::runtime_error("cannot activate checkpoint");
}

bool loadCheckpoint(const fs::path& path, const std::string& scheme, std::uint64_t& groupIndex,
                    std::uint64_t& nextFrame, std::vector<Aggregate>& aggregates) {
    if (!fs::exists(path)) return false;
    std::ifstream in(path,std::ios::binary); char magic[8]{}; in.read(magic,8);
    if (std::string(magic,8)!="S7CPV2__") throw std::runtime_error("checkpoint magic mismatch");
    std::uint64_t schemeCode=0,count=0; readValue(in,schemeCode); readValue(in,groupIndex); readValue(in,nextFrame); readValue(in,count);
    if (schemeCode!=(scheme=="BCH"?1U:2U) || count!=aggregates.size()) throw std::runtime_error("checkpoint scheme/config mismatch");
    std::string hash(64,'\0'); in.read(hash.data(),64); if (hash!=kConfigHash) throw std::runtime_error("checkpoint config hash mismatch");
    for (Aggregate& value:aggregates) {
        readValue(in,value.frames); readValue(in,value.totalBits); readValue(in,value.bitErrors); readValue(in,value.frameErrors);
        readValue(in,value.affectedBlocks); readValue(in,value.maximumErrorsInBlock); readValue(in,value.correctedBlocks);
        readValue(in,value.detectedFailureFrames); readValue(in,value.undetectedFrameErrors); readValue(in,value.miscorrectedBlocks);
        readTimes(in,value.decodeNs); readTimes(in,value.interleaveNs); readTimes(in,value.deinterleaveNs);
    }
    return true;
}

double mean(const std::vector<double>& values) {
    double total=0.0; for(double value:values) total+=value; return values.empty()?0.0:total/values.size();
}
double percentile(std::vector<double> values,double p) {
    if(values.empty()) return 0.0; std::sort(values.begin(),values.end());
    const std::size_t index=static_cast<std::size_t>(std::ceil(p*values.size()))-1;
    return values[std::min(index,values.size()-1)];
}
double maximum(const std::vector<double>& values) { return values.empty()?0.0:*std::max_element(values.begin(),values.end()); }

std::vector<Candidate> candidatesFor(const std::string& scheme) {
    if (scheme=="BCH") return {
        {"BCH_NONE","NONE",0,"BASELINE","","",s7::makeBchMapping(s7::BchInterleaver::None)},
        {"BCH_CODEBLOCK_D19","BCH_CODEBLOCK",19,"FORMAL_METHOD","","BCH_EQUAL_SPAN_285",s7::makeBchMapping(s7::BchInterleaver::Codeblock,19)},
        {"BCH_ROW_COLUMN_R15","ROW_COLUMN",15,"FORMAL_METHOD","","BCH_EQUAL_SPAN_285",s7::makeBchMapping(s7::BchInterleaver::RowColumn,15)},
        {"BCH_GLOBAL_PSEUDO_285","GLOBAL_PSEUDORANDOM",285,"FORMAL_METHOD","","BCH_EQUAL_SPAN_285",s7::makeBchMapping(s7::BchInterleaver::GlobalPseudorandom,285)}};
    return {
        {"CC_NONE","NONE",0,"BASELINE","","",s7::makeCcMapping(s7::CcInterleaver::None)},
        {"CC_SHORT_D8_RECOMMENDED","SHORT_DEPTH_BLOCK",8,"RECOMMENDED_ENGINEERING_CONFIGURATION","CC_RECOMMENDED_ENGINEERING_CONFIG","",s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock,8)},
        {"CC_PSEUDO_128_RECOMMENDED","PSEUDORANDOM",128,"RECOMMENDED_ENGINEERING_CONFIGURATION","CC_RECOMMENDED_ENGINEERING_CONFIG","CC_EQUAL_SPAN_128",s7::makeCcMapping(s7::CcInterleaver::Pseudorandom,128)},
        {"CC_SHORT_D16_CONTROL_128","SHORT_DEPTH_BLOCK",16,"CONTROLLED_EQUAL_SPAN_128","","CC_EQUAL_SPAN_128",s7::makeCcMapping(s7::CcInterleaver::ShortDepthBlock,16)}};
}

std::tuple<std::string,std::string,std::string,std::string> sharedHashes(
    std::size_t payloadLength,std::size_t encodedLength,std::size_t frames,double ratio,s7::BurstPosition position) {
    scl::common::Sha256 payloadHash,noiseHash,burstHash,frameHash;
    for(std::size_t frame=0;frame<frames;++frame) {
        const auto payload=s7::deterministicPayload(payloadLength,frame); payloadHash.update(payload);
        const auto noise=s7::deterministicStandardNoise(encodedLength,frame);
        noiseHash.update(reinterpret_cast<const std::uint8_t*>(noise.data()),noise.size()*sizeof(double));
        const auto burst=s7::makeBurstSpec(encodedLength,ratio,position,frame);
        burstHash.update(std::to_string(frame)+":"+std::to_string(burst.start)+":"+std::to_string(burst.lengthBits)+";");
        frameHash.update(std::to_string(frame)+",");
    }
    return {payloadHash.finalHex(),noiseHash.finalHex(),burstHash.finalHex(),frameHash.finalHex()};
}

void writeHeader(std::ofstream& out) {
    out << "scheme,configurationId,method,parameter,comparisonRole,engineeringComparisonGroup,controlledComparisonGroup,pureMethodDifferenceAllowed,fairnessGroupId,spanBits,spanTrellisSteps,bufferBits,mappingHash,EsN0Db,sigmaSquared,burstRatioRequested,burstLengthBits,burstRatioActual,burstPositionType,framesProcessed,totalBits,bitErrors,frameErrors,BER,FER,berZeroUpperBound,ferZeroUpperBound,affectedBlocksMean,maximumErrorsInBlock,correctedBlocksMean,detectedFailureFrames,undetectedFrameErrors,miscorrectedBlocks,decodeTimeMeanNs,decodeTimeMedianNs,decodeTimeP95Ns,decodeTimeP99Ns,decodeTimeMaxNs,interleaveTimeMeanNs,interleaveTimeP95Ns,interleaveTimeMaxNs,deinterleaveTimeMeanNs,deinterleaveTimeP95Ns,deinterleaveTimeMaxNs,payloadChecksum,noiseChecksum,burstStartChecksum,frameSequenceHash,configHash\n";
}

} // namespace

int main(int argc,char** argv) {
    try {
        if(argc<3) throw std::invalid_argument("usage: s7_formal_runner BCH|CC OUTPUT_DIR [--group-limit N] [--interrupt-after-checkpoint]");
        const std::string scheme=argv[1]; if(scheme!="BCH"&&scheme!="CC") throw std::invalid_argument("scheme must be BCH or CC");
        std::size_t groupLimit=31*3*6; bool interruptAfterCheckpoint=false;
        for(int i=3;i<argc;++i) {
            const std::string option=argv[i];
            if(option=="--group-limit"&&i+1<argc) groupLimit=std::stoul(argv[++i]);
            else if(option=="--interrupt-after-checkpoint") interruptAfterCheckpoint=true;
            else throw std::invalid_argument("unknown formal runner option");
        }
        const fs::path output=fs::absolute(argv[2]); fs::create_directories(output);
        const fs::path csvPath=output/"formal_results.csv", checkpointPath=output/"checkpoint.bin";
        const auto candidates=candidatesFor(scheme); std::vector<Aggregate> aggregates(candidates.size());
        std::uint64_t groupIndex=0,nextFrame=0; const bool resumed=loadCheckpoint(checkpointPath,scheme,groupIndex,nextFrame,aggregates);
        if(!resumed&&fs::exists(csvPath)) throw std::runtime_error("results exist without resumable checkpoint");
        std::ofstream csv(csvPath,resumed?std::ios::app:std::ios::trunc); if(!csv) throw std::runtime_error("cannot open formal CSV");
        if(!resumed) writeHeader(csv);
        const std::vector<double> ratios{0.02,0.05,0.10};
        const std::vector<s7::BurstPosition> positions{s7::BurstPosition::Head,s7::BurstPosition::Quarter,s7::BurstPosition::Middle,s7::BurstPosition::ThreeQuarter,s7::BurstPosition::Tail,s7::BurstPosition::Random};
        const std::size_t totalGroups=31*ratios.size()*positions.size(); groupLimit=std::min(groupLimit,totalGroups);
        const std::size_t payloadLength=scheme=="BCH"?s7::kBchPayloadBits:s7::kCcPayloadBits;
        const std::size_t encodedLength=scheme=="BCH"?s7::kBchEncodedBits:s7::kCcEncodedBits;
        const s7::BchCodecContext bchContext;
        bool checkpointWrittenThisRun=false;
        while(groupIndex<groupLimit) {
            const std::size_t snrIndex=groupIndex/(ratios.size()*positions.size());
            const std::size_t remainder=groupIndex%(ratios.size()*positions.size());
            const double snr=-5.0+0.5*snrIndex, ratio=ratios[remainder/positions.size()];
            const auto position=positions[remainder%positions.size()]; const double variance=s7::sigmaSquaredFromEsN0(snr);
            bool done=false;
            while(!done) {
                const auto payload=s7::deterministicPayload(payloadLength,nextFrame);
                const auto noise=s7::deterministicStandardNoise(encodedLength,nextFrame);
                const auto burst=s7::makeBurstSpec(encodedLength,ratio,position,nextFrame);
                for(std::size_t c=0;c<candidates.size();++c) {
                    Aggregate& a=aggregates[c]; std::size_t errors=0; s7::DecodeTiming timing;
                    if(scheme=="BCH") {
                        const auto result=s7::runBchFrame(bchContext,payload,candidates[c].mapping,noise,variance,burst);
                        errors=result.bitErrors; timing=result.timing; a.affectedBlocks+=result.affectedBlocks;
                        a.maximumErrorsInBlock=std::max<std::uint64_t>(a.maximumErrorsInBlock,result.maximumErrorsInBlock);
                        a.correctedBlocks+=result.correctedBlocks; a.detectedFailureFrames+=result.decoderDetectedFailure;
                        a.undetectedFrameErrors+=result.undetectedFrameError; a.miscorrectedBlocks+=result.miscorrectedBlocks;
                    } else { const auto result=s7::runCcFrame(payload,candidates[c].mapping,noise,variance,burst); errors=result.bitErrors; timing=result.timing; }
                    ++a.frames; a.totalBits+=payloadLength; a.bitErrors+=errors; a.frameErrors+=errors!=0;
                    a.decodeNs.push_back(timing.decodeTimeNs); a.interleaveNs.push_back(timing.interleaveTimeNs); a.deinterleaveNs.push_back(timing.deinterleaveTimeNs);
                }
                ++nextFrame;
                const bool minimumReached=nextFrame>=kMinFrames;
                const bool allTargets=std::all_of(aggregates.begin(),aggregates.end(),[](const Aggregate& a){return a.frameErrors>=kTargetFrameErrors;});
                done=(minimumReached&&allTargets)||nextFrame>=kMaxFrames;
                if(nextFrame%kCheckpointInterval==0&&!done) {
                    saveCheckpoint(checkpointPath,scheme,groupIndex,nextFrame,aggregates); checkpointWrittenThisRun=true;
                    if(interruptAfterCheckpoint) { std::cout<<"INTERRUPTED_AFTER_CHECKPOINT group="<<groupIndex<<" nextFrame="<<nextFrame<<'\n'; return 75; }
                }
            }
            const auto hashes=sharedHashes(payloadLength,encodedLength,nextFrame,ratio,position);
            const auto representativeBurst=s7::makeBurstSpec(encodedLength,ratio,position,0);
            csv<<std::setprecision(17);
            for(std::size_t c=0;c<candidates.size();++c) {
                const Candidate& candidate=candidates[c]; const Aggregate& a=aggregates[c];
                const double ber=double(a.bitErrors)/a.totalBits,fer=double(a.frameErrors)/a.frames;
                csv<<scheme<<','<<candidate.id<<','<<candidate.method<<','<<candidate.parameter<<','<<candidate.role<<','
                   <<candidate.engineeringGroup<<','<<candidate.controlledGroup<<",false,"<<candidate.mapping.fairnessGroupId<<','
                   <<candidate.mapping.spanBits<<','<<candidate.mapping.spanTrellisSteps<<','<<candidate.mapping.bufferBits<<','<<candidate.mapping.sha256<<','
                   <<snr<<','<<variance<<','<<ratio<<','<<representativeBurst.lengthBits<<','<<double(representativeBurst.lengthBits)/encodedLength<<','
                   <<s7::burstPositionName(position)<<','<<a.frames<<','<<a.totalBits<<','<<a.bitErrors<<','<<a.frameErrors<<','<<ber<<','<<fer<<','
                   <<(a.bitErrors==0?3.0/a.totalBits:0.0)<<','<<(a.frameErrors==0?3.0/a.frames:0.0)<<','
                   <<double(a.affectedBlocks)/a.frames<<','<<a.maximumErrorsInBlock<<','<<double(a.correctedBlocks)/a.frames<<','
                   <<a.detectedFailureFrames<<','<<a.undetectedFrameErrors<<','<<a.miscorrectedBlocks<<','
                   <<mean(a.decodeNs)<<','<<percentile(a.decodeNs,0.5)<<','<<percentile(a.decodeNs,0.95)<<','<<percentile(a.decodeNs,0.99)<<','<<maximum(a.decodeNs)<<','
                   <<mean(a.interleaveNs)<<','<<percentile(a.interleaveNs,0.95)<<','<<maximum(a.interleaveNs)<<','
                   <<mean(a.deinterleaveNs)<<','<<percentile(a.deinterleaveNs,0.95)<<','<<maximum(a.deinterleaveNs)<<','
                   <<std::get<0>(hashes)<<','<<std::get<1>(hashes)<<','<<std::get<2>(hashes)<<','<<std::get<3>(hashes)<<','<<kConfigHash<<'\n';
            }
            csv.flush(); if(!csv) throw std::runtime_error("formal CSV write failed");
            ++groupIndex; nextFrame=0; aggregates.assign(candidates.size(),Aggregate{});
            saveCheckpoint(checkpointPath,scheme,groupIndex,nextFrame,aggregates); checkpointWrittenThisRun=true;
            std::cout<<"FORMAL_PROGRESS scheme="<<scheme<<" groups="<<groupIndex<<'/'<<groupLimit<<'\n';
            if(interruptAfterCheckpoint&&checkpointWrittenThisRun) { std::cout<<"INTERRUPTED_AFTER_CHECKPOINT_BOUNDARY\n"; return 75; }
        }
        std::ofstream manifest(output/"checkpoint_manifest.json");
        manifest<<"{\n  \"status\": \"COMPLETE\",\n  \"scheme\": \""<<scheme<<"\",\n  \"configHash\": \""<<kConfigHash<<"\",\n"
                <<"  \"completedGroups\": "<<groupIndex<<",\n  \"checkpointIntervalFrames\": 1000,\n  \"mergeStatus\": \"NOT_MERGED\"\n}\n";
        std::ofstream readme(output/"readme.txt");
        readme<<"阶段名称："<<(scheme=="BCH"?"stage10_bch_formal":"stage11_cc_formal")<<"\n实验目的：执行 S7 配对停止 Formal 网格。\n"
              <<"主要输入：31 Es/N0、3 突发比例、6 位置、"<<candidates.size()<<" 配置。\n完成内容：Formal CSV 与 checkpoint。\n"
              <<"主要输出：formal_results.csv、checkpoint.bin、checkpoint_manifest.json。\n当前结论：必须经 Formal checker 后确定。\n"
              <<"已知问题：CPU 时延依赖本机环境。\n阶段状态：PARTIAL_PASS\n";
        std::cout<<"PASS_S7_FORMAL_RUNNER scheme="<<scheme<<" groups="<<groupIndex<<'\n'; return 0;
    } catch(const std::exception& error) { std::cerr<<"FAIL_S7_FORMAL_RUNNER: "<<error.what()<<'\n'; return 1; }
}

