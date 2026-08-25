# C1B official VitalSense reproduction v1

Status: `OFFICIAL_REPRO_TECHNICAL_BLOCKER`

## What was completed

- The official repository was cloned without source modification.
- Fixed official commit: `d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6`.
- The existing C1b Python runner, report and metrics were read and retained as the comparison baseline.
- A six-step implementation difference table was produced.
- The frozen ECG evaluator rule was not changed: ±50/75/100/150 ms, with ±75 ms primary.

## Concrete blocker

No callable MATLAB, MATLAB Runtime or Octave executable is installed or discoverable on this host. The checked paths `C:\Program Files\MATLAB`, `C:\Program Files\MATLAB Runtime`, `C:\Program Files\GNU Octave` and `C:\Program Files\Polyspace` do not exist, and `Get-Command matlab` / `Get-Command octave` return no executable.

Therefore:

- the official `main.m` sample-data run was not executed;
- no official MATLAB console/log or official sample HR/beat output exists;
- the 48-session official MATLAB run was not executed;
- no official MATLAB result is substituted with the current Python AMF result.

## Why the current Python AMF is not equivalent

The difference table marks all six requested stages as `DIFFERENT`: signal input, separation filter, HRestim period estimation, template generation, RWAMF and beat localization. In particular, the current Python implementation is a transparent baseline adapter, not a byte-identical or algorithmically equivalent reproduction of the author's MATLAB implementation.

## Required next action

Run the official repository on a machine with a compatible MATLAB installation and required Signal Processing Toolbox, or provide a licensed MATLAB execution environment. Then run the author sample first, record the console and outputs, and only afterward run the 48 VS_DATASET sessions through an input/output adapter. No algorithm changes or threshold tuning are authorized in this handoff.

No official performance conclusion is made in this report.
