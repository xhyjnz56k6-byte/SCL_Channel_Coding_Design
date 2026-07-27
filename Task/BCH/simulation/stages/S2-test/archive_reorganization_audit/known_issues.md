# Audit known issues

- Historical Stage manifests retain their original commit ranges; the
  standard historical checker reports a functional-range mismatch until a
  dedicated archive commit is created.
- The working tree contains the migration changes and is therefore not yet
  a clean, remotely verified final archive.
- MATLAB `checkcode` reports two formatting warnings in the existing reference
  function; no syntax failure was reported.
