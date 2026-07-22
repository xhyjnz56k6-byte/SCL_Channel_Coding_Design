# BCH-14 changed files

The content range minimally extends Common checkpoint serialization, compatibility checks, atomic
replace, and CTest registration; extends the BCH runner with adaptive stop, checkpoint/resume,
config hashing, and shard identity; adds a strict raw-count shard merger and BCH-14 orchestrator;
and adds the frozen Stage records. The repair range changes only progress reporting to emit real
checkpoint and shard state. Generated evidence and audits are outside both functional ranges.
