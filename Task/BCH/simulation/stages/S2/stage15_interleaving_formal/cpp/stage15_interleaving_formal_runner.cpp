#include "stage13_burst_interleaving_validation_simulation.hpp"
#include "stage02_case_contract.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
namespace stage02 = scl::bch::s2::stage02;
namespace stage13 = scl::bch::s2::stage13;

namespace {

struct Point {
    stage02::CaseId caseId;
    std::string caseIdText;
    stage13::InterleaverMode mode;
    std::size_t depth;
    std::size_t burstIndex;
    std::size_t burstLength;
    std::string permutationSha256;
};

struct StopRule {
    std::uint64_t minFrames, targetErrors, maxFrames, interval;
};

void require(bool value,const std::string& message) {
    if(!value)throw std::runtime_error(message);
}

stage02::CaseId parseCase(const std::string& value) {
    for(const auto& contract:stage02::allCaseContracts())
        if(contract.caseId==value)return contract.id;
    throw std::invalid_argument("unknown Stage15 caseId");
}

std::vector<Point> readPoints(const fs::path& path) {
    std::ifstream input(path);if(!input)throw std::runtime_error("cannot open points");
    std::string line;std::getline(input,line);
    require(line=="caseId,interleaverMode,interleaverDepth,burstLengthIndex,burstLengthBits,permutationSha256",
            "Stage15 point header mismatch");
    std::vector<Point> points;
    while(std::getline(input,line)) {
        if(line.empty())continue;std::istringstream row(line);
        std::string id,mode,depth,index,length,sha;
        std::getline(row,id,',');std::getline(row,mode,',');std::getline(row,depth,',');
        std::getline(row,index,',');std::getline(row,length,',');std::getline(row,sha,',');
        const auto parsedMode=stage13::parseInterleaverMode(mode);
        require(parsedMode!=stage13::InterleaverMode::None,"Stage15 runner must not rerun NONE");
        points.push_back({parseCase(id),id,parsedMode,
            static_cast<std::size_t>(std::stoull(depth)),
            static_cast<std::size_t>(std::stoull(index)),
            static_cast<std::size_t>(std::stoull(length)),sha});
    }
    require(!points.empty(),"Stage15 points empty");return points;
}

stage13::SimulationPoint simulationPoint(const Point& p,std::uint64_t seed) {
    return {p.caseId,p.mode,p.depth,seed,p.burstLength,p.burstIndex,0U,0.0,false};
}

void checkpoint(const fs::path& path,const Point& p,
                const stage13::SimulationCounters& c,std::uint64_t masterSeed,
                const std::string& configSha,const std::string& commit,
                const std::string& reason) {
    std::ofstream out(path);if(!out)throw std::runtime_error("checkpoint write failed");
    out<<"{\n  \"stageId\": \"stage15_interleaving_formal\",\n"
       <<"  \"configSha256\": \""<<configSha<<"\",\n"
       <<"  \"gitCommit\": \""<<commit<<"\",\n"
       <<"  \"caseId\": \""<<p.caseIdText<<"\",\n"
       <<"  \"interleaverMode\": \""<<stage13::interleaverModeName(p.mode)<<"\",\n"
       <<"  \"interleaverDepth\": "<<p.depth<<",\n"
       <<"  \"burstLengthBits\": "<<p.burstLength<<",\n"
       <<"  \"framesProcessed\": "<<c.framesProcessed<<",\n"
       <<"  \"payloadBitsProcessed\": "<<c.payloadBitsProcessed<<",\n"
       <<"  \"payloadErrorBits\": "<<c.payloadErrorBits<<",\n"
       <<"  \"payloadErrorFrames\": "<<c.payloadErrorFrames<<",\n"
       <<"  \"decoderDeclaredSuccessFrames\": "<<c.decoderDeclaredSuccessFrames<<",\n"
       <<"  \"decoderDeclaredFailureFrames\": "<<c.decoderDeclaredFailureFrames<<",\n"
       <<"  \"trueSuccessFrames\": "<<c.trueSuccessFrames<<",\n"
       <<"  \"miscorrectionFrames\": "<<c.miscorrectionFrames<<",\n"
       <<"  \"undetectedErrorFrames\": "<<c.undetectedErrorFrames<<",\n"
       <<"  \"affectedCodeBlocksTotal\": "<<c.affectedCodeBlocksTotal<<",\n"
       <<"  \"sumMaxErrorsInOneCodeBlock\": "<<c.sumMaxErrorsInOneCodeBlock<<",\n"
       <<"  \"burstStartChecksum\": "<<c.burstStartChecksum<<",\n"
       <<"  \"payloadChecksum\": "<<c.payloadChecksum<<",\n"
       <<"  \"frameIndexNext\": "<<c.framesProcessed<<",\n"
       <<"  \"masterSeed\": "<<masterSeed<<",\n"
       <<"  \"stopReason\": \""<<reason<<"\"\n}\n";
}

std::string simulate(const Point& p,const StopRule& rule,std::uint64_t masterSeed,
                     std::uint64_t interSeed,const fs::path& path,
                     const std::string& configSha,const std::string& commit,
                     stage13::SimulationCounters& counters) {
    const auto point=simulationPoint(p,interSeed);
    while(counters.framesProcessed<rule.maxFrames) {
        const auto count=std::min(rule.interval,rule.maxFrames-counters.framesProcessed);
        const auto chunk=stage13::simulateRange(point,masterSeed,counters.framesProcessed,count,true);
        const bool crossing=counters.framesProcessed+count>=rule.minFrames&&
            counters.payloadErrorFrames+chunk.payloadErrorFrames>=rule.targetErrors;
        if(crossing) {
            while(counters.framesProcessed<rule.maxFrames) {
                const auto one=stage13::simulateRange(point,masterSeed,counters.framesProcessed,1U,true);
                stage13::addCounters(counters,one,true);
                if(counters.framesProcessed>=rule.minFrames&&
                   counters.payloadErrorFrames>=rule.targetErrors) {
                    checkpoint(path,p,counters,masterSeed,configSha,commit,"TARGET_FRAME_ERRORS_REACHED");
                    return "TARGET_FRAME_ERRORS_REACHED";
                }
            }
        } else {
            stage13::addCounters(counters,chunk,true);
            checkpoint(path,p,counters,masterSeed,configSha,commit,"CONTINUE");
        }
    }
    checkpoint(path,p,counters,masterSeed,configSha,commit,"MAX_FRAMES_REACHED");
    return "MAX_FRAMES_REACHED";
}

void header(std::ofstream& out) {
    out<<"stageId,runId,gitCommit,caseId,legendLabel,payloadLength,encodedLength,actualRate,"
          "motherN,motherK,motherT,blockCount,interleaverMode,interleaverDepth,"
          "interleaverRows,interleaverColumns,interleaverBlockCount,interleaverSeed,"
          "permutationFile,permutationSha256,burstLengthIndex,burstLengthBits,burstRatio,"
          "masterSeed,framesProcessed,payloadBitsProcessed,payloadErrorBits,payloadErrorFrames,"
          "decoderDeclaredSuccessFrames,decoderDeclaredFailureFrames,trueSuccessFrames,"
          "miscorrectionFrames,undetectedErrorFrames,affectedCodeBlocksTotal,meanAffectedCodeBlocks,"
          "maxAffectedCodeBlocks,maxErrorsInOneCodeBlockObserved,meanMaxErrorsInOneCodeBlock,"
          "interleaverApplyTimeTotalNs,deinterleaverApplyTimeTotalNs,decoderTimeTotalNs,"
          "interleaverTimeMeanNs,deinterleaverTimeMeanNs,decoderTimeMeanNs,decoderTimeP50Ns,"
          "decoderTimeP95Ns,decoderTimeP99Ns,decoderTimeMaxNs,interleaverBufferBits,"
          "interleaverBufferBytes,interleaverStartupDelayBits,ber,fer,decoderFailureRate,"
          "miscorrectionRate,undetectedErrorRate,trueSuccessRate,stopReason,checkpointPath,resultSha256\n";
}

void result(std::ofstream& out,const Point& p,const stage13::SimulationCounters& c,
            std::uint64_t masterSeed,std::uint64_t interSeed,const std::string& commit,
            const std::string& reason,const std::string& checkpointPath) {
    const auto& x=stage02::caseContract(p.caseId);const double f=c.framesProcessed,b=c.payloadBitsProcessed;
    const std::size_t columns=(x.totalEncodedLength+p.depth-1U)/p.depth;
    const std::size_t rows=p.mode==stage13::InterleaverMode::RowColumn?p.depth:0U;
    const std::size_t blocks=p.mode==stage13::InterleaverMode::Block?p.depth:1U;
    const auto maximum=*std::max_element(c.decoderTimesNs.begin(),c.decoderTimesNs.end());
    out<<std::setprecision(17)<<"stage15_interleaving_formal,stage15_formal_v1,"<<commit<<','
       <<x.caseId<<','<<x.legendLabel<<','<<x.payloadLength<<','<<x.totalEncodedLength<<','
       <<x.actualRate<<','<<x.motherN<<','<<x.motherK<<','<<x.motherT<<','<<x.blockCount<<','
       <<stage13::interleaverModeName(p.mode)<<','<<p.depth<<','<<rows<<','<<columns<<','<<blocks<<','
       <<interSeed<<",../stage13_burst_interleaving_validation/results/"
       <<"stage13_burst_interleaving_validation_permutations.csv,"<<p.permutationSha256<<','
       <<p.burstIndex<<','<<p.burstLength<<','<<static_cast<double>(p.burstLength)/x.totalEncodedLength<<','
       <<masterSeed<<','<<c.framesProcessed<<','<<c.payloadBitsProcessed<<','<<c.payloadErrorBits<<','
       <<c.payloadErrorFrames<<','<<c.decoderDeclaredSuccessFrames<<','<<c.decoderDeclaredFailureFrames<<','
       <<c.trueSuccessFrames<<','<<c.miscorrectionFrames<<','<<c.undetectedErrorFrames<<','
       <<c.affectedCodeBlocksTotal<<','<<static_cast<double>(c.affectedCodeBlocksTotal)/f<<','
       <<c.maxAffectedCodeBlocks<<','<<c.maxErrorsInOneCodeBlockObserved<<','
       <<static_cast<double>(c.sumMaxErrorsInOneCodeBlock)/f<<','
       <<c.interleaverApplyTimeTotalNs<<','<<c.deinterleaverApplyTimeTotalNs<<','<<c.decoderTimeTotalNs<<','
       <<c.interleaverApplyTimeTotalNs/c.framesProcessed<<','
       <<c.deinterleaverApplyTimeTotalNs/c.framesProcessed<<','<<c.decoderTimeTotalNs/c.framesProcessed<<','
       <<stage13::percentile(c.decoderTimesNs,.50)<<','<<stage13::percentile(c.decoderTimesNs,.95)<<','
       <<stage13::percentile(c.decoderTimesNs,.99)<<','<<maximum<<','<<x.totalEncodedLength<<','
       <<(x.totalEncodedLength+7U)/8U<<','<<x.totalEncodedLength<<','
       <<static_cast<double>(c.payloadErrorBits)/b<<','<<static_cast<double>(c.payloadErrorFrames)/f<<','
       <<static_cast<double>(c.decoderDeclaredFailureFrames)/f<<','
       <<static_cast<double>(c.miscorrectionFrames)/f<<','
       <<static_cast<double>(c.undetectedErrorFrames)/f<<','
       <<static_cast<double>(c.trueSuccessFrames)/f<<','<<reason<<','<<checkpointPath<<",\n";
}

} // namespace

int main(int argc,char** argv) {
    try {
        if(argc!=12)throw std::invalid_argument(
            "usage: stage15_interleaving_formal_runner POINTS OUTPUT CHECKPOINTS MASTER INTERSEED CONFIGSHA COMMIT MIN TARGET MAX INTERVAL");
        const auto points=readPoints(argv[1]);const fs::path outputPath(argv[2]),checkpoints(argv[3]);
        const std::uint64_t master=std::stoull(argv[4]),interSeed=std::stoull(argv[5]);
        const std::string configSha(argv[6]),commit(argv[7]);
        const StopRule rule{std::stoull(argv[8]),std::stoull(argv[9]),std::stoull(argv[10]),std::stoull(argv[11])};
        require(rule.minFrames&&rule.targetErrors&&rule.minFrames<=rule.maxFrames&&rule.interval,
                "invalid stop rule");fs::create_directories(checkpoints);fs::create_directories(outputPath.parent_path());
        std::ofstream out(outputPath);if(!out)throw std::runtime_error("cannot create output");header(out);
        for(const auto& p:points) {
            stage13::SimulationCounters counters;
            const std::string name="stage15_interleaving_formal_"+p.caseIdText+"_"+
                stage13::interleaverModeName(p.mode)+"_D"+std::to_string(p.depth)+"_L"+
                std::to_string(p.burstLength)+".json";
            const auto reason=simulate(p,rule,master,interSeed,checkpoints/name,configSha,commit,counters);
            result(out,p,counters,master,interSeed,commit,reason,"results/checkpoints/"+name);
            std::cout<<p.caseIdText<<' '<<stage13::interleaverModeName(p.mode)<<" D="<<p.depth
                     <<" L="<<p.burstLength<<" frames="<<counters.framesProcessed
                     <<" errors="<<counters.payloadErrorFrames<<' '<<reason<<'\n';
        }
        std::cout<<"PASS_STAGE15_INTERLEAVING_FORMAL_RUNNER\n";return 0;
    } catch(const std::exception& e) {
        std::cerr<<"BLOCKED_STAGE15_INTERLEAVING_FORMAL_RUNNER: "<<e.what()<<'\n';return 1;
    }
}

