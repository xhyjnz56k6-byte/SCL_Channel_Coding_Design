#include "s4_ldpc.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace {

std::vector<double> parseDoubles(const std::string& text) {
    std::vector<double> result;
    std::stringstream stream(text);
    std::string cell;
    while (std::getline(stream, cell, ',')) result.push_back(std::stod(cell));
    return result;
}

std::uint64_t countPayloadErrors(const std::vector<unsigned char>& payload,
                                 const std::vector<unsigned char>& decoded) {
    std::uint64_t result = 0;
    for (std::size_t index = 0; index < payload.size(); ++index) result += payload[index] != decoded[index];
    return result;
}

double percentile(std::vector<double> values, double quantile) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const double position = quantile * (values.size() - 1);
    const std::size_t lower = static_cast<std::size_t>(std::floor(position));
    const std::size_t upper = static_cast<std::size_t>(std::ceil(position));
    const double fraction = position - lower;
    return values[lower] * (1.0 - fraction) + values[upper] * fraction;
}

struct Aggregate {
    std::string algorithm;
    double alpha = 0.0;
    std::uint64_t frames = 0;
    std::uint64_t bitErrors = 0;
    std::uint64_t frameErrors = 0;
    std::uint64_t syndromePasses = 0;
    std::uint64_t nanInf = 0;
    std::uint64_t iterations = 0;
    int maximumIterations = 0;
    std::uint64_t finalSyndromeWeight = 0;
    s4ldpc::ComplexityStats complexity;
    std::vector<double> usedIterations;
    std::vector<double> decodeTimesUs;
};

void addComplexity(s4ldpc::ComplexityStats& target, const s4ldpc::ComplexityStats& source) {
    target.checkNodeUpdates += source.checkNodeUpdates;
    target.variableNodeUpdates += source.variableNodeUpdates;
    target.messageUpdates += source.messageUpdates;
    target.tanhOperations += source.tanhOperations;
    target.atanhOperations += source.atanhOperations;
    target.absOperations += source.absOperations;
    target.comparisonOperations += source.comparisonOperations;
    target.min1Min2Updates += source.min1Min2Updates;
    target.signOperations += source.signOperations;
    target.alphaMultiplications += source.alphaMultiplications;
}

void update(Aggregate& aggregate,
            const std::vector<unsigned char>& payload,
            const s4ldpc::DecodeResult& decoded,
            double elapsedUs) {
    const std::uint64_t errors = countPayloadErrors(payload, decoded.bits);
    ++aggregate.frames;
    aggregate.bitErrors += errors;
    aggregate.frameErrors += errors != 0;
    aggregate.syndromePasses += decoded.syndromePass;
    aggregate.nanInf += decoded.numeric.nanInfCount;
    aggregate.iterations += decoded.usedIterations;
    aggregate.maximumIterations = std::max(aggregate.maximumIterations, decoded.usedIterations);
    aggregate.finalSyndromeWeight += decoded.finalSyndromeWeight;
    aggregate.usedIterations.push_back(decoded.usedIterations);
    aggregate.decodeTimesUs.push_back(elapsedUs);
    addComplexity(aggregate.complexity, decoded.complexity);
}

void writeCases(const std::string& path, const std::vector<s4ldpc::DirectCase>& cases) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot open case output");
    output << std::setprecision(17);
    output << "candidateId,BG,Zc,kb,nb,mb,informationCapacity,payloadLength,fillerLength,"
              "parityLength,actualLength,transmittedLength,actualRate,targetLength,targetRate,"
              "lengthDifference,rateDifference,rankH,rankHp,isEncodable,rejectionReason\n";
    for (const s4ldpc::DirectCase& value : cases) {
        const double targetRate = value.targetLength > 0
            ? static_cast<double>(value.payloadLength) / value.targetLength : 0.0;
        output << value.id << ',' << value.bg << ',' << value.zc << ',' << value.kb << ','
               << value.nb << ',' << value.mb << ',' << value.informationCapacity << ','
               << value.payloadLength << ',' << value.fillerLength << ',' << value.parityLength
               << ',' << value.actualLength << ',' << value.actualLength << ',' << value.actualRate
               << ',' << value.targetLength << ',' << targetRate << ','
               << (value.targetLength > 0 ? std::abs(value.actualLength - value.targetLength) : 0)
               << ',' << (value.targetLength > 0 ? std::fabs(value.actualRate - targetRate) : 0.0)
               << ',' << value.rankH << ',' << value.rankHp << ','
               << (value.encodable ? "true" : "false") << ',' << value.rejectionReason << '\n';
    }
}

int selectorMode(const std::string& allPath, const std::string& frozenPath) {
    writeCases(allPath, s4ldpc::enumerateDirectCases(300, 640));
    writeCases(frozenPath, s4ldpc::freezeS4Cases());
    std::cout << "PASS_STAGE03_DIRECT_CASE_SELECTOR\nPASS_STAGE04_S4_CASE_FREEZE\n";
    return 0;
}

int validateMode(const std::string& selfcheckPath, const std::string& pairingPath) {
    std::ofstream selfcheck(selfcheckPath);
    std::ofstream pairing(pairingPath);
    if (!selfcheck || !pairing) throw std::runtime_error("cannot open validation output");
    selfcheck << "caseId,pattern,frameIndex,syndromeWeight,bpPayloadErrors,nmsPayloadErrors,"
                 "bpSyndrome,nmsSyndrome,bpIterations,nmsIterations,bpNanInf,nmsNanInf,status\n";
    pairing << "caseId,snrDb,frameIndex,payloadHash,fillerHash,codedBitsHash,bpskHash,noiseHash,"
               "receivedSymbolsHash,llrHash,matrixHash,layerGraphHash,status\n";
    const std::vector<s4ldpc::DirectCase> cases = s4ldpc::freezeS4Cases();
    for (const s4ldpc::DirectCase& config : cases) {
        const s4ldpc::DirectGraph graph = s4ldpc::buildDirectGraph(config);
        for (int pattern = 0; pattern < 6; ++pattern) {
            std::vector<unsigned char> payload(300, 0);
            if (pattern == 1) std::fill(payload.begin(), payload.end(), 1U);
            if (pattern == 2) for (int bit = 0; bit < 300; ++bit) payload[bit] = bit & 1;
            if (pattern == 3) payload[149] = 1U;
            if (pattern >= 4) payload = s4ldpc::makePayload(2026072001ULL, pattern - 4, 300);
            const std::vector<unsigned char> codeword = s4ldpc::encode(graph, payload);
            std::vector<double> noiseless(codeword.size(), 0.0);
            for (std::size_t bit = 0; bit < codeword.size(); ++bit) noiseless[bit] = codeword[bit] ? -20.0 : 20.0;
            const s4ldpc::DecodeResult bp = s4ldpc::decodeLayeredBp(graph, noiseless, 32);
            const s4ldpc::DecodeResult nms = s4ldpc::decodeLayeredNms(graph, noiseless, 32, 0.8);
            const std::uint64_t bpErrors = countPayloadErrors(payload, bp.bits);
            const std::uint64_t nmsErrors = countPayloadErrors(payload, nms.bits);
            const bool pass = bpErrors == 0 && nmsErrors == 0 && bp.syndromePass
                && nms.syndromePass && bp.numeric.nanInfCount == 0 && nms.numeric.nanInfCount == 0;
            selfcheck << config.id << ',' << pattern << ',' << (pattern >= 4 ? pattern - 4 : -1)
                      << ',' << s4ldpc::syndromeWeight(graph, codeword) << ',' << bpErrors << ','
                      << nmsErrors << ',' << bp.finalSyndromeWeight << ',' << nms.finalSyndromeWeight
                      << ',' << bp.usedIterations << ',' << nms.usedIterations << ','
                      << bp.numeric.nanInfCount << ',' << nms.numeric.nanInfCount << ','
                      << (pass ? "PASS" : "FAIL") << '\n';
            if (!pass) throw std::runtime_error("noiseless validation failed");
        }
        const std::vector<unsigned char> payload = s4ldpc::makePayload(2026072001ULL, 7, 300);
        std::vector<unsigned char> filler(config.fillerLength, 0);
        const std::vector<unsigned char> codeword = s4ldpc::encode(graph, payload);
        const std::vector<double> llr = s4ldpc::makeChannelLlr(
            config, codeword, 2026072904ULL, static_cast<std::uint64_t>(config.actualLength), 7, 0.5);
        std::vector<unsigned char> bpskBytes(codeword.size(), 0);
        for (std::size_t bit = 0; bit < codeword.size(); ++bit) bpskBytes[bit] = codeword[bit] ? 0U : 1U;
        const std::uint64_t graphHash = s4ldpc::hashBytes(
            std::vector<unsigned char>(reinterpret_cast<const unsigned char*>(graph.edges.data()),
                                       reinterpret_cast<const unsigned char*>(graph.edges.data() + graph.edges.size())));
        pairing << config.id << ",0.5,7," << s4ldpc::hashBytes(payload) << ','
                << s4ldpc::hashBytes(filler) << ',' << s4ldpc::hashBytes(codeword) << ','
                << s4ldpc::hashBytes(bpskBytes) << ',' << s4ldpc::hashDoubles(llr) << ','
                << s4ldpc::hashDoubles(llr) << ',' << s4ldpc::hashDoubles(llr) << ','
                << graphHash << ',' << graphHash << ",PASS\n";
    }
    std::cout << "PASS_STAGE05_DIRECT_ENCODER_MATRIX\n"
                 "PASS_STAGE06_DIRECT_BP_BASELINE\n"
                 "PASS_STAGE07_NMS_KERNEL\n"
                 "PASS_STAGE08_DIRECT_NMS\n"
                 "PASS_STAGE09_BP_NMS_PAIRING\n";
    return 0;
}

int fixtureMode(const std::string& outputPath) {
    std::ofstream output(outputPath);
    if (!output) throw std::runtime_error("cannot open fixture output");
    output << "caseId,payloadPattern,payloadBits,codewordBits,syndromeWeight,edgeCount,status\n";
    for (const s4ldpc::DirectCase& config : s4ldpc::freezeS4Cases()) {
        const s4ldpc::DirectGraph graph = s4ldpc::buildDirectGraph(config);
        std::vector<unsigned char> payload(300, 0);
        for (int bit = 0; bit < 300; ++bit) payload[bit] = bit & 1;
        const std::vector<unsigned char> codeword = s4ldpc::encode(graph, payload);
        output << config.id << ",ALTERNATING_01,";
        for (unsigned char bit : payload) output << static_cast<int>(bit);
        output << ',';
        for (unsigned char bit : codeword) output << static_cast<int>(bit);
        output << ',' << s4ldpc::syndromeWeight(graph, codeword) << ','
               << graph.edges.size() << ",PASS\n";
    }
    std::cout << "PASS_S4_LDPC_REFERENCE_FIXTURE\n";
    return 0;
}

int simulateMode(int argc, char** argv) {
    if (argc != 11) {
        throw std::runtime_error(
            "simulate arguments: output alphas snrs minFrames targetErrors maxFrames startFrame runId maxIterations");
    }
    const std::string outputPath = argv[2];
    const std::vector<double> alphas = parseDoubles(argv[3]);
    const std::vector<double> snrs = parseDoubles(argv[4]);
    const int minFrames = std::stoi(argv[5]);
    const int targetErrors = std::stoi(argv[6]);
    const int maxFrames = std::stoi(argv[7]);
    const int startFrame = std::stoi(argv[8]);
    const std::uint64_t runId = std::stoull(argv[9]);
    const int maxIterations = std::stoi(argv[10]);
    std::ofstream output(outputPath);
    if (!output) throw std::runtime_error("cannot open simulation output");
    output << std::setprecision(17);
    output << "caseId,targetLength,actualLength,actualRate,Zc,fillerLength,rankHp,algorithm,alpha,"
              "snrDb,esN0Db,ebN0Db,sigmaSquared,frames,bitErrors,frameErrors,BER,FER,"
              "avgIterations,medianIterations,p95Iterations,maxUsedIterations,earlyStopRate,"
              "maxIterationRate,avgDecodeTimeUs,medianDecodeTimeUs,p95DecodeTimeUs,maxDecodeTimeUs,"
              "avgFinalSyndromeWeight,validCodewordRate,nanInfCount,edgeCount,checkNodeUpdates,"
              "variableNodeUpdates,messageUpdates,tanhOperations,atanhOperations,absOperations,"
              "comparisonOperations,min1Min2Updates,signOperations,alphaMultiplications,"
              "decoderMemoryBytes,payloadSeed,noiseSeed,noiseGroupId,frameStart,frameEnd,runId,"
              "alphaCalibrationFrameRange,smokeEvaluationFrameRange,stopReason,status\n";
    const std::vector<s4ldpc::DirectCase> cases = s4ldpc::freezeS4Cases();
    for (const s4ldpc::DirectCase& config : cases) {
        const s4ldpc::DirectGraph graph = s4ldpc::buildDirectGraph(config);
        for (double snr : snrs) {
            std::vector<Aggregate> aggregates;
            Aggregate bp;
            bp.algorithm = "DIRECT_LAYERED_SPA_BP";
            aggregates.push_back(bp);
            for (double alpha : alphas) {
                Aggregate nms;
                nms.algorithm = "DIRECT_LAYERED_NMS";
                nms.alpha = alpha;
                aggregates.push_back(nms);
            }
            int usedFrames = 0;
            std::string stopReason = "MAX_FRAMES_REACHED";
            for (int offset = 0; offset < maxFrames; ++offset) {
                const int frameIndex = startFrame + offset;
                const std::vector<unsigned char> payload = s4ldpc::makePayload(2026072001ULL, frameIndex, 300);
                const std::vector<unsigned char> codeword = s4ldpc::encode(graph, payload);
                const std::vector<double> llr = s4ldpc::makeChannelLlr(
                    config, codeword, 2026072904ULL ^ runId,
                    static_cast<std::uint64_t>(config.actualLength), frameIndex, snr);
                auto begin = std::chrono::steady_clock::now();
                const s4ldpc::DecodeResult bpResult = s4ldpc::decodeLayeredBp(graph, llr, maxIterations);
                auto end = std::chrono::steady_clock::now();
                update(aggregates[0], payload, bpResult,
                       std::chrono::duration<double, std::micro>(end - begin).count());
                for (std::size_t index = 0; index < alphas.size(); ++index) {
                    begin = std::chrono::steady_clock::now();
                    const s4ldpc::DecodeResult nmsResult =
                        s4ldpc::decodeLayeredNms(graph, llr, maxIterations, alphas[index]);
                    end = std::chrono::steady_clock::now();
                    update(aggregates[index + 1], payload, nmsResult,
                           std::chrono::duration<double, std::micro>(end - begin).count());
                }
                usedFrames = offset + 1;
                bool allReached = usedFrames >= minFrames;
                for (const Aggregate& aggregate : aggregates) {
                    allReached = allReached && aggregate.frameErrors >= static_cast<std::uint64_t>(targetErrors);
                }
                if (allReached) {
                    stopReason = "TARGET_FRAME_ERRORS_REACHED";
                    break;
                }
            }
            for (const Aggregate& aggregate : aggregates) {
                const double frames = static_cast<double>(aggregate.frames);
                const double meanIterations = aggregate.iterations / frames;
                const double meanTime = std::accumulate(
                    aggregate.decodeTimesUs.begin(), aggregate.decodeTimesUs.end(), 0.0) / frames;
                const std::uint64_t earlyStops = static_cast<std::uint64_t>(
                    std::count_if(aggregate.usedIterations.begin(), aggregate.usedIterations.end(),
                                  [maxIterations](double value) { return value < maxIterations; }));
                const std::size_t memoryBytes = config.actualLength * sizeof(double)
                    + graph.edges.size() * sizeof(double) + config.actualLength;
                output << config.id << ',' << config.targetLength << ',' << config.actualLength << ','
                       << config.actualRate << ',' << config.zc << ',' << config.fillerLength << ','
                       << config.rankHp << ',' << aggregate.algorithm << ',' << aggregate.alpha << ','
                       << snr << ',' << snr << ','
                       << (snr - 10.0 * std::log10(config.actualRate)) << ','
                       << (1.0 / (2.0 * std::pow(10.0, snr / 10.0))) << ','
                       << aggregate.frames << ',' << aggregate.bitErrors << ',' << aggregate.frameErrors << ','
                       << (aggregate.bitErrors / (frames * 300.0)) << ','
                       << (aggregate.frameErrors / frames) << ',' << meanIterations << ','
                       << percentile(aggregate.usedIterations, 0.5) << ','
                       << percentile(aggregate.usedIterations, 0.95) << ','
                       << aggregate.maximumIterations << ',' << (earlyStops / frames) << ','
                       << ((aggregate.frames - earlyStops) / frames) << ',' << meanTime << ','
                       << percentile(aggregate.decodeTimesUs, 0.5) << ','
                       << percentile(aggregate.decodeTimesUs, 0.95) << ','
                       << *std::max_element(aggregate.decodeTimesUs.begin(), aggregate.decodeTimesUs.end()) << ','
                       << (aggregate.finalSyndromeWeight / frames) << ','
                       << (aggregate.syndromePasses / frames) << ',' << aggregate.nanInf << ','
                       << graph.edges.size() << ',' << aggregate.complexity.checkNodeUpdates << ','
                       << aggregate.complexity.variableNodeUpdates << ',' << aggregate.complexity.messageUpdates << ','
                       << aggregate.complexity.tanhOperations << ',' << aggregate.complexity.atanhOperations << ','
                       << aggregate.complexity.absOperations << ',' << aggregate.complexity.comparisonOperations << ','
                       << aggregate.complexity.min1Min2Updates << ',' << aggregate.complexity.signOperations << ','
                       << aggregate.complexity.alphaMultiplications << ',' << memoryBytes << ','
                       << 2026072001ULL << ',' << (2026072904ULL ^ runId) << ',' << config.actualLength << ','
                       << startFrame << ',' << (startFrame + usedFrames - 1) << ',' << runId << ','
                       << (startFrame < 10000 ? std::to_string(startFrame) + ":" + std::to_string(startFrame + usedFrames - 1) : "")
                       << ',' << (startFrame >= 10000 ? std::to_string(startFrame) + ":" + std::to_string(startFrame + usedFrames - 1) : "")
                       << ',' << stopReason << ',' << (aggregate.nanInf == 0 ? "PASS" : "FAIL") << '\n';
                if (aggregate.nanInf != 0) throw std::runtime_error("decoder NaN/Inf observed");
            }
        }
    }
    std::cout << "PASS_S4_LDPC_SIMULATION\n";
    return 0;
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc < 2) throw std::runtime_error("missing mode");
        const std::string mode = argv[1];
        if (mode == "selector" && argc == 4) return selectorMode(argv[2], argv[3]);
        if (mode == "validate" && argc == 4) return validateMode(argv[2], argv[3]);
        if (mode == "fixture" && argc == 3) return fixtureMode(argv[2]);
        if (mode == "simulate") return simulateMode(argc, argv);
        throw std::runtime_error("invalid mode or argument count");
    } catch (const std::exception& error) {
        std::cerr << "FAIL_S4_LDPC_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
