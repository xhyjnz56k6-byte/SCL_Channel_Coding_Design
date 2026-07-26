#include "bch_simulation/bch_impairment_simulation.hpp"

#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

std::map<std::string, std::string> parse(int argc, char** argv) {
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; ++index) {
        const std::string key(argv[index]);
        if (key == "--progress" || key == "--no-progress" ||
            key == "--resume" || key == "--complete-blockage" ||
            key == "--perfect-compensation") {
            values[key] = "1";
        } else {
            if (key.rfind("--", 0U) != 0U || index + 1 >= argc) {
                throw std::invalid_argument("invalid runner arguments");
            }
            values[key] = argv[++index];
        }
    }
    return values;
}

std::string required(
    const std::map<std::string, std::string>& values, const std::string& key) {
    const auto found = values.find(key);
    if (found == values.end()) throw std::invalid_argument("missing argument " + key);
    return found->second;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto args = parse(argc, argv);
        scl::bch::simulation::ImpairmentPointConfig config;
        config.stage = required(args, "--stage");
        config.channel = scl::bch::simulation::parseImpairmentChannel(
            required(args, "--channel"));
        config.caseId =
            scl::bch::simulation::bchSimulationCase(required(args, "--case")).id;
        config.sourcePayloadEbN0Db = std::stod(required(args, "--ebn0-db"));
        config.frameStart = std::stoull(required(args, "--frame-start"));
        config.frameCount = std::stoull(required(args, "--frame-count"));
        if (args.count("--logical-frame-count")) {
            config.logicalFrameCount =
                std::stoull(args.at("--logical-frame-count"));
        }
        config.globalSeed = std::stoull(required(args, "--global-seed"));
        config.framePoolManifest = required(args, "--frame-pool-manifest");
        config.outputDirectory = required(args, "--output-dir");
        config.progress = args.count("--no-progress") == 0U;
        if (args.count("--progress-refresh-seconds")) {
            config.progressRefreshSeconds =
                std::stod(args.at("--progress-refresh-seconds"));
        }
        if (args.count("--noise-policy-version")) {
            config.noisePolicyVersion =
                std::stoull(args.at("--noise-policy-version"));
        }
        if (args.count("--initial-phase-deg")) {
            config.initialPhaseDeg = std::stod(args.at("--initial-phase-deg"));
        }
        if (args.count("--frame-rotation-deg")) {
            config.frameRotationDeg = std::stod(args.at("--frame-rotation-deg"));
        }
        config.compensationMode = args.count("--perfect-compensation")
            ? scl::bch::simulation::CfoCompensationMode::Perfect
            : scl::bch::simulation::CfoCompensationMode::None;
        if (args.count("--attenuation-db")) {
            config.attenuationDb = std::stod(args.at("--attenuation-db"));
        }
        config.completeBlockage = args.count("--complete-blockage") != 0U;
        if (args.count("--blockage-length")) {
            config.blockageLength = std::stoull(args.at("--blockage-length"));
        }
        if (args.count("--blockage-start-policy")) {
            config.blockageStartPolicy = scl::bch::simulation::parseStartPolicy(
                args.at("--blockage-start-policy"));
        }
        if (args.count("--burst-mode")) {
            config.burstMode =
                scl::bch::simulation::parseBurstMode(args.at("--burst-mode"));
        }
        if (args.count("--burst-length")) {
            config.burstLength = std::stoull(args.at("--burst-length"));
        }
        if (args.count("--burst-start-policy")) {
            config.burstStartPolicy = scl::bch::simulation::parseStartPolicy(
                args.at("--burst-start-policy"));
        }
        if (args.count("--checkpoint")) config.checkpointPath = args.at("--checkpoint");
        if (args.count("--checkpoint-interval")) {
            config.checkpointInterval =
                std::stoull(args.at("--checkpoint-interval"));
        }
        config.resume = args.count("--resume") != 0U;
        if (args.count("--interrupt-after-frames")) {
            config.interruptAfterFrames =
                std::stoull(args.at("--interrupt-after-frames"));
        }
        if (args.count("--min-frames") || args.count("--target-frame-errors") ||
            args.count("--max-frames")) {
            config.adaptiveStop = true;
            config.minFrames = std::stoull(required(args, "--min-frames"));
            config.targetFrameErrors =
                std::stoull(required(args, "--target-frame-errors"));
            config.maxFrames = std::stoull(required(args, "--max-frames"));
            config.frameCount = config.maxFrames;
        }
        if (args.count("--shard-index")) {
            config.shardIndex = std::stoull(args.at("--shard-index"));
        }
        if (args.count("--shard-count")) {
            config.shardCount = std::stoull(args.at("--shard-count"));
        }
        const auto result = scl::bch::simulation::runImpairmentPoint(config);
        scl::bch::simulation::writeImpairmentPointSummary(
            result, (fs::path(config.outputDirectory) / "summary.csv").string());
        std::cout << "PASS_" << config.stage << '_'
                  << scl::bch::simulation::bchSimulationCase(config.caseId).caseName
                  << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_IMPAIRMENT_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
