# Stage15 final-delivery commands

- Rebuild from formal CSVs: `python scripts/process_final_delivery.py`
- Substantive checker: `python scripts/check_stage15_revision.py`
- Reproducible entry: `python scripts/run_stage15.py`
- Git checks: `git diff --check`, explicit Stage14/15 staging, remote branch verification.

Stage09, Stage10, Stage11, Stage13 and Stage14 Soft were read only and not rerun.
