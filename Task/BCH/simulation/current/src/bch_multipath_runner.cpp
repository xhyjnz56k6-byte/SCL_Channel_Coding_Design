#include "bch_simulation/bch_multipath_simulation.hpp"

#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace fs = std::filesystem;

namespace {

std::map<std::string, std::string> parse(int argc, char** argv) {
    std::map<std::string, std::string> values;
    for (int i = 1; i < argc; ++i) {
        const std::string key(argv[i]);
        if (key == "--progress" || key == "--no-progress" ||
            key == "--detail" || key == "--resume") {
            values[key] = "1";
        } else {
            if (key.rfind("--", 0U) != 0U || i + 1 >= argc) {
                throw std::invalid_argument("invalid runner arguments");
            }
            values[key] = argv[++i];
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
        scl::bch::simulation::MultipathPointConfig config;
        config.stage = required(args, "--stage");
        config.caseId =
            scl::bch::simulation::bchSimulationCase(required(args, "--case")).id;
        config.sourcePayloadEbN0Db = std::stod(required(args, "--ebn0-db"));
        config.snrIndex = std::stoull(required(args, "--snr-index"));
        config.frameStart = std::stoull(required(args, "--frame-start"));
        config.frameCount = std::stoull(required(args, "--frame-count"));
        config.globalSeed = std::stoull(required(args, "--global-seed"));
        config.framePoolManifest = required(args, "--frame-pool-manifest");
        config.outputDirectory = required(args, "--output-dir");
        config.progress = args.count("--no-progress") == 0U;
        if (args.count("--progress-refresh-seconds")) {
            config.progressRefreshSeconds =
                std::stod(args.at("--progress-refresh-seconds"));
        }
        config.writeFrameDetail = args.count("--detail") != 0U;
        if (args.count("--min-frames") || args.count("--target-frame-errors") ||
            args.count("--max-frames")) {
            config.adaptiveStop = true;
            config.minFrames = std::stoull(required(args, "--min-frames"));
            config.targetFrameErrors =
                std::stoull(required(args, "--target-frame-errors"));
            config.maxFrames = std::stoull(required(args, "--max-frames"));
        }
        if (args.count("--checkpoint")) config.checkpointPath = args.at("--checkpoint");
        if (args.count("--checkpoint-interval")) {
            config.checkpointInterval = std::stoull(args.at("--checkpoint-interval"));
        }
        config.resume = args.count("--resume") != 0U;
        if (args.count("--interrupt-after-frames")) {
            config.interruptAfterFrames =
                std::stoull(args.at("--interrupt-after-frames"));
        }
        if (args.count("--shard-index")) config.shardIndex = std::stoull(args.at("--shard-index"));
        if (args.count("--shard-count")) config.shardCount = std::stoull(args.at("--shard-count"));
        const auto result = scl::bch::simulation::runMultipathPoint(config);
        scl::bch::simulation::writeMultipathPointSummary(
            result, (fs::path(config.outputDirectory) / "summary.csv").string());
        std::cout << "PASS_" << config.stage << '_'
                  << scl::bch::simulation::bchSimulationCase(config.caseId).caseName
                  << '_' << config.snrIndex << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "BLOCKED_BCH_S2_MULTIPATH_RUNNER: " << error.what() << '\n';
        return 1;
    }
}
