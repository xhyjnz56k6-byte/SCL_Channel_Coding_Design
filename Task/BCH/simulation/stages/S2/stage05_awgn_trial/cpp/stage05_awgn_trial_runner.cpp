#include "stage01_foundation_awgn.hpp"
#include "stage02_case_contract.hpp"

#include "bch_block/bch_block.hpp"
#include "bch_segmented/bch15_lookup_table.hpp"
#include "bch_segmented/bch15_segmented_adapter.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

using CaseId = scl::bch::s2::stage02::CaseId;
using CaseContract = scl::bch::s2::stage02::CaseContract;
using Organization = scl::bch::s2::stage02::Organization;

struct Point {
    CaseId id;
    std::string caseId;
    std::size_t ebn0Index;
    double ebn0Db;
};

struct Counters {
    std::uint64_t totalFrames = 0U;
    std::uint64_t totalPayloadBits = 0U;
    std::uint64_t payloadErrorBits = 0U;
    std::uint64_t payloadErrorFrames = 0U;
    std::uint64_t decoderFailureFrames = 0U;
    std::uint64_t miscorrectionFrames = 0U;
    std::uint64_t undetectedErrorFrames = 0U;
    std::uint64_t trueSuccessFrames = 0U;
    std::uint64_t noiseChecksum = 0U;
    std::uint64_t encodeTimeTotalNs = 0U;
    std::uint64_t decodeTimeTotalNs = 0U;
    std::vector<std::uint64_t> decodeTimesNs;
};

struct AuditedDecode {
    scl::common::BitVector payload;
    bool reportedSuccess = false;
    bool anyCorrected = false;
    bool allNoError = false;
};

void require(bool value, const std::string& message) {
    if (!value) throw std::runtime_error(message);
}

CaseId parseCase(const std::string& id) {
    using C = CaseId;
    if (id == "K200_S15") return C::K200_S15;
    if (id == "K200_M255K207") return C::K200_M255K207;
    if (id == "K200_M511K421") return C::K200_M511K421;
    if (id == "K200_M511K385") return C::K200_M511K385;
    if (id == "K300_S15") return C::K300_S15;
    if (id == "K300_M255K207") return C::K300_M255K207;
    if (id == "K300_M511K421") return C::K300_M511K421;
    if (id == "K300_M511K385") return C::K300_M511K385;
    throw std::invalid_argument("unsupported caseId in point CSV");
}

std::vector<Point> readPoints(const fs::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open point CSV");
    std::string line;
    std::getline(input, line);
    require(line == "caseId,ebn0Index,ebn0Db", "point CSV header mismatch");
    std::vector<Point> points;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream row(line);
        std::string id, index, db;
        std::getline(row, id, ',');
        std::getline(row, index, ',');
        std::getline(row, db, ',');
        points.push_back({parseCase(id), id, static_cast<std::size_t>(std::stoull(index)), std::stod(db)});
    }
    require(points.size() == 24U, "trial must contain exactly 24 points");
    return points;
}

scl::common::BitVector payloadFrame(
    const std::string& stage, const std::string& caseId,
    std::size_t ebn0Index, std::uint64_t frameIndex, std::size_t length,
    std::uint64_t seed) {
    const scl::bch::s2::stage01::RandomIdentity identity{
        seed, stage, caseId, ebn0Index, frameIndex};
    const auto source = scl::bch::s2::stage01::payloadFrame(identity, length);
    return scl::common::BitVector(source.begin(), source.end());
}

std::uint64_t hashNoise(const std::vector<double>& noise) {
    std::uint64_t value = 1469598103934665603ULL;
    for (double sample : noise) {
        std::uint64_t bits = 0U;
        std::memcpy(&bits, &sample, sizeof(bits));
        for (unsigned i = 0U; i < 8U; ++i) {
            value ^= (bits >> (i * 8U)) & 0xffU;
            value *= 1099511628211ULL;
        }
    }
    return value;
}

std::uint64_t bitErrors(const scl::common::BitVector& left, const scl::common::BitVector& right) {
    require(left.size() == right.size(), "payload comparison length mismatch");
    std::uint64_t count = 0U;
    for (std::size_t i = 0; i < left.size(); ++i) count += left[i] != right[i];
    return count;
}

scl::bch::block::BlockBchProfile makeProfile(const CaseContract& contract, std::size_t block) {
    scl::bch::block::BlockBchProfile profile;
    if (contract.motherN == 255U) profile = scl::bch::block::makeB200Profile();
    else if (contract.motherK == 421U) profile = scl::bch::block::makeB300Profile();
    else if (contract.motherK == 385U) profile = scl::bch::block::makeB300426Profile();
    else throw std::invalid_argument("unsupported block profile");
    profile.caseName = contract.caseId + "_STAGE05_BLOCK_" + std::to_string(block);
    profile.payloadLength = contract.payloadPerBlock.at(block);
    profile.shorteningLength = contract.shorteningPerBlock.at(block);
    scl::bch::block::validateProfile(profile);
    return profile;
}

const std::vector<scl::bch::block::BlockBchProfile>& profiles(CaseId id) {
    using C = CaseId;
    static const auto a=[] {const auto& c=scl::bch::s2::stage02::caseContract(C::K200_M255K207);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(c,0))};}();
    static const auto b=[] {const auto& c=scl::bch::s2::stage02::caseContract(C::K200_M511K421);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(c,0))};}();
    static const auto c=[] {const auto& x=scl::bch::s2::stage02::caseContract(C::K200_M511K385);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(x,0))};}();
    static const auto d=[] {const auto& c=scl::bch::s2::stage02::caseContract(C::K300_M255K207);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(c,0)),makeProfile(c,1)};}();
    static const auto e=[] {const auto& c=scl::bch::s2::stage02::caseContract(C::K300_M511K421);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(c,0))};}();
    static const auto f=[] {const auto& c=scl::bch::s2::stage02::caseContract(C::K300_M511K385);return std::vector{scl::bch::block::BlockBchProfile(makeProfile(c,0))};}();
    switch (id) {
        case C::K200_M255K207:return a; case C::K200_M511K421:return b;
        case C::K200_M511K385:return c; case C::K300_M255K207:return d;
        case C::K300_M511K421:return e; case C::K300_M511K385:return f;
        default:throw std::invalid_argument("segmented case has no block profiles");
    }
}

const scl::bch::segmented::SyndromeTable& syndromeTable() {
    static const auto table=scl::bch::segmented::buildBch15SyndromeTable();
    return table;
}

AuditedDecode decodeAudited(const CaseContract& contract, const scl::common::BitVector& received) {
    AuditedDecode result;
    std::size_t failed=0U, corrected=0U, noError=0U;
    if (contract.organization == Organization::Segmented15) {
        const auto id=contract.payloadLength==200U?scl::bch::segmented::Bch15SegmentedCase::S200:
            scl::bch::segmented::Bch15SegmentedCase::S300;
        const auto decoded=scl::bch::segmented::decodeBch15Segmented(id,received,syndromeTable());
        result.payload=decoded.recoveredPayload;
        for (const auto& block:decoded.blockDetails) {
            using S=scl::bch::segmented::Bch15DecodeStatus;
            if (block.decoder.status==S::NO_ERROR) ++noError;
            else if (block.decoder.status==S::CORRECTED_SINGLE_ERROR) ++corrected;
            else ++failed;
        }
    } else {
        const auto& cached=profiles(contract.id);
        std::size_t offset=0U;
        for (std::size_t block=0U;block<contract.blockCount;++block) {
            const std::size_t count=contract.encodedLengthPerBlock[block];
            const scl::common::BitVector part(received.begin()+static_cast<std::ptrdiff_t>(offset),
                received.begin()+static_cast<std::ptrdiff_t>(offset+count));
            const auto decoded=scl::bch::block::decodeShortenedNoThrow(cached[block],part);
            using S=scl::bch::block::DecodeStatus;
            if (decoded.status==S::NoError) ++noError;
            else if (decoded.status==S::Corrected) ++corrected;
            else ++failed;
            result.payload.insert(result.payload.end(),decoded.payload.begin(),decoded.payload.end());
            offset+=count;
        }
    }
    result.reportedSuccess=failed==0U;
    result.anyCorrected=corrected>0U;
    result.allNoError=noError==contract.blockCount;
    return result;
}

Counters simulateRange(const Point& point, std::uint64_t start, std::uint64_t count,
                       std::uint64_t seed, bool timing) {
    const auto& contract=scl::bch::s2::stage02::caseContract(point.id);
    Counters result;
    if (timing) result.decodeTimesNs.reserve(static_cast<std::size_t>(count));
    const double sigma=std::sqrt(scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db));
    for (std::uint64_t frame=start;frame<start+count;++frame) {
        const auto payload=payloadFrame("stage05_awgn_trial",contract.caseId,point.ebn0Index,
                                        frame,contract.payloadLength,seed);
        const auto encodeStart=std::chrono::steady_clock::now();
        const auto encoded=scl::bch::s2::stage02::encodeFrame(contract.id,payload).encodedBits;
        const auto encodeEnd=std::chrono::steady_clock::now();
        const scl::bch::s2::stage01::RandomIdentity identity{
            seed,"stage05_awgn_trial",contract.caseId,point.ebn0Index,frame};
        const auto z=scl::bch::s2::stage01::standardGaussianFrame(
            identity,scl::bch::s2::stage01::RandomDomain::Awgn,encoded.size());
        scl::common::BitVector hard(encoded.size(),0U);
        for (std::size_t i=0;i<encoded.size();++i) {
            const double received=scl::bch::s2::stage01::bpsk(encoded[i])+sigma*z[i];
            hard[i]=static_cast<scl::common::Bit>(scl::bch::s2::stage01::hardDecision(received));
        }
        const auto decodeStart=std::chrono::steady_clock::now();
        const auto decoded=decodeAudited(contract,hard);
        const auto decodeEnd=std::chrono::steady_clock::now();
        const auto errors=bitErrors(payload,decoded.payload);
        const bool success=errors==0U;
        ++result.totalFrames;
        result.totalPayloadBits+=contract.payloadLength;
        result.payloadErrorBits+=errors;
        result.payloadErrorFrames+=!success;
        result.decoderFailureFrames+=!decoded.reportedSuccess;
        result.miscorrectionFrames+=decoded.reportedSuccess&&!success;
        result.undetectedErrorFrames+=decoded.allNoError&&!success;
        result.trueSuccessFrames+=success;
        result.noiseChecksum+=hashNoise(z);
        if (timing) {
            const auto encodeNs=std::chrono::duration_cast<std::chrono::nanoseconds>(encodeEnd-encodeStart).count();
            const auto decodeNs=std::chrono::duration_cast<std::chrono::nanoseconds>(decodeEnd-decodeStart).count();
            result.encodeTimeTotalNs+=static_cast<std::uint64_t>(encodeNs);
            result.decodeTimeTotalNs+=static_cast<std::uint64_t>(decodeNs);
            result.decodeTimesNs.push_back(static_cast<std::uint64_t>(decodeNs));
        }
    }
    return result;
}

void add(Counters& target,const Counters& source) {
    target.totalFrames+=source.totalFrames; target.totalPayloadBits+=source.totalPayloadBits;
    target.payloadErrorBits+=source.payloadErrorBits; target.payloadErrorFrames+=source.payloadErrorFrames;
    target.decoderFailureFrames+=source.decoderFailureFrames;
    target.miscorrectionFrames+=source.miscorrectionFrames;
    target.undetectedErrorFrames+=source.undetectedErrorFrames;
    target.trueSuccessFrames+=source.trueSuccessFrames; target.noiseChecksum+=source.noiseChecksum;
}

bool sameRaw(const Counters& a,const Counters& b) {
    return a.totalFrames==b.totalFrames&&a.totalPayloadBits==b.totalPayloadBits&&
        a.payloadErrorBits==b.payloadErrorBits&&a.payloadErrorFrames==b.payloadErrorFrames&&
        a.decoderFailureFrames==b.decoderFailureFrames&&a.miscorrectionFrames==b.miscorrectionFrames&&
        a.undetectedErrorFrames==b.undetectedErrorFrames&&a.trueSuccessFrames==b.trueSuccessFrames&&
        a.noiseChecksum==b.noiseChecksum;
}

std::uint64_t percentile(std::vector<std::uint64_t> values,double p) {
    if (values.empty()) return 0U;
    std::sort(values.begin(),values.end());
    const auto index=static_cast<std::size_t>(std::ceil(p*values.size())-1.0);
    return values[std::min(index,values.size()-1U)];
}

void writeCheckpoint(const fs::path& path,const Point& point,const Counters& c,std::uint64_t next) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write checkpoint");
    out<<"{\n  \"stageId\": \"stage05_awgn_trial\",\n  \"caseId\": \""<<point.caseId
       <<"\",\n  \"ebn0Index\": "<<point.ebn0Index<<",\n  \"ebn0Db\": "<<point.ebn0Db
       <<",\n  \"nextFrameIndex\": "<<next<<",\n  \"totalFrames\": "<<c.totalFrames
       <<",\n  \"totalPayloadBits\": "<<c.totalPayloadBits
       <<",\n  \"payloadErrorBits\": "<<c.payloadErrorBits
       <<",\n  \"payloadErrorFrames\": "<<c.payloadErrorFrames
       <<",\n  \"decoderFailureFrames\": "<<c.decoderFailureFrames
       <<",\n  \"miscorrectionFrames\": "<<c.miscorrectionFrames
       <<",\n  \"undetectedErrorFrames\": "<<c.undetectedErrorFrames
       <<",\n  \"trueSuccessFrames\": "<<c.trueSuccessFrames
       <<",\n  \"noiseChecksum\": "<<c.noiseChecksum<<"\n}\n";
}

}  // namespace

int main(int argc,char** argv) {
    try {
        if (argc!=4) throw std::invalid_argument("usage: stage05_awgn_trial_runner POINTS_CSV OUTPUT_DIR MASTER_SEED");
        const auto points=readPoints(argv[1]);
        const fs::path output(argv[2]);
        const std::uint64_t seed=std::stoull(argv[3]);
        fs::create_directories(output/"checkpoints");
        std::ofstream results(output/"stage05_awgn_trial_results.csv");
        std::ofstream resume(output/"stage05_awgn_trial_resume_compare.csv");
        std::ofstream shards(output/"stage05_awgn_trial_shard_merge_compare.csv");
        std::ofstream runtime(output/"stage05_awgn_trial_runtime_estimate.csv");
        std::ofstream shardManifest(output/"stage05_awgn_trial_shard_manifest.csv");
        if(!results||!resume||!shards||!runtime||!shardManifest)throw std::runtime_error("cannot open outputs");
        results<<"stageId,caseId,displayName,legendLabel,styleId,payloadLength,motherN,motherK,motherT,"
                 "blockCount,encodedLength,actualRate,ebn0Index,ebn0Db,snrLinear,snrDb,sigma2,masterSeed,"
                 "totalFrames,totalPayloadBits,payloadErrorBits,payloadErrorFrames,decoderFailureFrames,"
                 "miscorrectionFrames,undetectedErrorFrames,trueSuccessFrames,ber,fer,encodeTimeTotalNs,"
                 "decodeTimeTotalNs,encodeTimeMeanNs,decodeTimeMeanNs,decodeTimeP50Ns,decodeTimeP95Ns,"
                 "decodeTimeP99Ns,decodeTimeMaxNs,noiseChecksum,stopReason\n";
        resume<<"caseId,ebn0Index,continuousFrames,resumedFrames,continuousNoiseChecksum,resumedNoiseChecksum,allIntegerCountsEqual,passed\n";
        shards<<"caseId,ebn0Index,continuousFrames,mergedFrames,continuousNoiseChecksum,mergedNoiseChecksum,allIntegerCountsEqual,passed\n";
        runtime<<"caseId,ebn0Index,trialFrames,elapsedSeconds,framesPerSecond,estimated50000FramesSeconds\n";
        shardManifest<<"caseId,ebn0Index,shardId,frameStart,frameCount\n";
        results<<std::setprecision(17);
        std::vector<Counters> continuous;
        continuous.reserve(points.size());
        for(const auto& point:points) {
            const auto started=std::chrono::steady_clock::now();
            auto c=simulateRange(point,0U,500U,seed,true);
            const auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
            continuous.push_back(c);
            const auto& contract=scl::bch::s2::stage02::caseContract(point.id);
            const double sigma2=scl::bch::s2::stage01::awgnSigma2(contract.actualRate,point.ebn0Db);
            const double ber=static_cast<double>(c.payloadErrorBits)/c.totalPayloadBits;
            const double fer=static_cast<double>(c.payloadErrorFrames)/c.totalFrames;
            const std::string display=contract.displayName;
            results<<"stage05_awgn_trial,"<<contract.caseId<<','<<display<<','<<contract.legendLabel<<','
                   <<contract.plotStyle.id<<','<<contract.payloadLength<<','<<contract.motherN<<','
                   <<contract.motherK<<','<<contract.motherT<<','<<contract.blockCount<<','
                   <<contract.totalEncodedLength<<','<<contract.actualRate<<','<<point.ebn0Index<<','
                   <<point.ebn0Db<<','<<1.0/sigma2<<','
                   <<scl::bch::s2::stage01::snrDb(contract.actualRate,point.ebn0Db)<<','<<sigma2<<','
                   <<seed<<','<<c.totalFrames<<','<<c.totalPayloadBits<<','<<c.payloadErrorBits<<','
                   <<c.payloadErrorFrames<<','<<c.decoderFailureFrames<<','<<c.miscorrectionFrames<<','
                   <<c.undetectedErrorFrames<<','<<c.trueSuccessFrames<<','<<ber<<','<<fer<<','
                   <<c.encodeTimeTotalNs<<','<<c.decodeTimeTotalNs<<','
                   <<c.encodeTimeTotalNs/c.totalFrames<<','<<c.decodeTimeTotalNs/c.totalFrames<<','
                   <<percentile(c.decodeTimesNs,0.50)<<','<<percentile(c.decodeTimesNs,0.95)<<','
                   <<percentile(c.decodeTimesNs,0.99)<<','
                   <<*std::max_element(c.decodeTimesNs.begin(),c.decodeTimesNs.end())<<','
                   <<c.noiseChecksum<<",SMOKE_FIXED_FRAMES\n";
            runtime<<point.caseId<<','<<point.ebn0Index<<",500,"<<elapsed<<','<<500.0/elapsed<<','
                   <<elapsed*100.0<<'\n';
        }
        for(std::size_t caseIndex=0U;caseIndex<8U;++caseIndex) {
            const std::size_t pointIndex=caseIndex*3U+1U;
            const auto& point=points[pointIndex];
            const auto& expected=continuous[pointIndex];
            auto prefix=simulateRange(point,0U,211U,seed,false);
            writeCheckpoint(output/"checkpoints"/("stage05_awgn_trial_"+point.caseId+"_checkpoint.json"),
                            point,prefix,211U);
            auto resumed=prefix;
            add(resumed,simulateRange(point,211U,289U,seed,false));
            const bool resumePass=sameRaw(expected,resumed);
            resume<<point.caseId<<','<<point.ebn0Index<<','<<expected.totalFrames<<','
                  <<resumed.totalFrames<<','<<expected.noiseChecksum<<','<<resumed.noiseChecksum<<','
                  <<resumePass<<','<<resumePass<<'\n';
            Counters merged;
            const std::uint64_t starts[]={0U,167U,334U};
            const std::uint64_t counts[]={167U,167U,166U};
            for(std::size_t shard=0U;shard<3U;++shard) {
                add(merged,simulateRange(point,starts[shard],counts[shard],seed,false));
                shardManifest<<point.caseId<<','<<point.ebn0Index<<','<<shard<<','
                             <<starts[shard]<<','<<counts[shard]<<'\n';
            }
            const bool shardPass=sameRaw(expected,merged);
            shards<<point.caseId<<','<<point.ebn0Index<<','<<expected.totalFrames<<','
                  <<merged.totalFrames<<','<<expected.noiseChecksum<<','<<merged.noiseChecksum<<','
                  <<shardPass<<','<<shardPass<<'\n';
            require(resumePass&&shardPass,"resume or shard equivalence failed");
        }
        std::cout<<"PASS_STAGE05_AWGN_TRIAL_RUNNER\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr<<"BLOCKED_STAGE05_AWGN_TRIAL_RUNNER: "<<error.what()<<'\n';
        return 1;
    }
}
