#include "common/checkpoint.hpp"
#include "common/result_schema.hpp"
#include "common/simulation_pipeline.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
std::string valueFor(int argc, char** argv, const std::string& name) {
    for (int index = 1; index + 1 < argc; ++index) {
        if (argv[index] == name) {
            return argv[index + 1];
        }
    }
    throw std::invalid_argument("missing argument: " + name);
}

bool hasFlag(int argc, char** argv, const std::string& name) {
    for (int index = 1; index < argc; ++index) {
        if (argv[index] == name) {
            return true;
        }
    }
    return false;
}
}

int main(int argc, char** argv) {
    try {
        scl::common::IdentitySimulationConfig config;
        config.experimentId = valueFor(argc, argv, "--experiment");
        config.caseName = valueFor(argc, argv, "--case");
        config.framePoolManifestPath = valueFor(argc, argv, "--frame-manifest");
        config.noisePoolManifestPath = valueFor(argc, argv, "--noise-manifest");
        config.payloadLength = static_cast<scl::common::Length>(std::stoull(valueFor(argc, argv, "--payload-length")));
        config.encodedLength = config.payloadLength;
        config.frameStart = static_cast<scl::common::FrameIndex>(std::stoull(valueFor(argc, argv, "--frame-start")));
        config.frameCount = std::stoull(valueFor(argc, argv, "--frame-count"));
        config.ebN0_dB = std::stod(valueFor(argc, argv, "--ebn0"));
        config.snrIndex = static_cast<scl::common::SnrIndex>(std::stoull(valueFor(argc, argv, "--snr-index")));
        config.decisionMode = valueFor(argc, argv, "--decision") == "HARD" ? scl::common::DecisionMode::Hard :
                                                                                scl::common::DecisionMode::LlrSign;
        config.inputMode = scl::common::SimulationInputMode::PoolBacked;
        config.stopConfig = {0U, config.frameCount, 0U, false};

        scl::common::IdentitySimulationRunOptions options;
        if (hasFlag(argc, argv, "--resume")) {
            options.resumeCheckpoint = scl::common::readCheckpointFile(valueFor(argc, argv, "--resume"));
        }
        if (hasFlag(argc, argv, "--checkpoint")) {
            options.checkpointOutputPath = valueFor(argc, argv, "--checkpoint");
            options.checkpointIntervalFrames = config.frameCount;
        }
        const auto result = scl::common::runIdentitySimulation(config, options);
        const std::filesystem::path csvPath(valueFor(argc, argv, "--summary"));
        const std::filesystem::path metadataPath(valueFor(argc, argv, "--metadata"));
        std::filesystem::create_directories(csvPath.parent_path());
        std::filesystem::create_directories(metadataPath.parent_path());
        const bool newCsv = !std::filesystem::exists(csvPath);
        std::ofstream csv(csvPath, std::ios::app);
        if (!csv) {
            throw std::runtime_error("failed to open summary output");
        }
        if (newCsv) {
            csv << scl::common::summaryCsvHeader() << '\n';
        }
        csv << scl::common::summaryRowToCsv(result.summary) << '\n';
        std::ofstream metadata(metadataPath, std::ios::binary | std::ios::trunc);
        metadata << scl::common::metadataJson(result.summary, "runtime_metadata_only");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
