# Test and release status

## Historical V1 evidence

- Published baseline: 23 host tests and 6 official Direct Mode tests passed on
  the historical source. Those results remain historical and do not certify the
  corrected release.
- Historical Windows Direct Mode failed before contract assertions with
  `PermissionError: [WinError 32]` while `genlayer-test==0.29.2` removed its
  stdin tempfile. This is a runner cleanup defect, not graph evidence.

## Corrected release worktree

- Host protocol tests: **40/40 passed** on Python 3.12.10, including exact
  limits, independent graph reference totals, semantic retry transitions,
  per-network active-capacity reuse and cross-network isolation.
- Mutation checks: **5/5 killed**. The focused suite executes mutations for
  root omission, skipped depth, ignored graph work, budget bypass and format
  error misclassification.
- Official Direct Mode: **9/9 passed** on Ubuntu Python 3.12.3 with
  `genlayer-test==0.29.2` and contract SDK `v0.2.12`. This includes the two
  retry cases, native validator replay, unit-fanout amplification rejection,
  uncertain fail-closed behavior and capacity reuse. Direct Mode uses controlled
  semantic responses; it is not a live StudioNet consensus proof.
- Windows host tests: **passed locally** on Python 3.12.10. Windows Direct Mode
  remains **blocked before contract assertions** by the upstream
  `gltest/direct/loader.py` tempfile unlink (`WinError 32`).
- GenVM linter: **passed** with `genvm-linter==0.11.0`, `GENVM_VERSION=v0.2.12`
  and UTF-8 output. ABI extraction reports 18 methods: 11 writes and 7 views.
- Project-local CLI: `genlayer@0.39.1`; npm lockfile resolves exactly 0.39.1.
- Network guard: **passed** independently against StudioNet RPC
  `https://studio.genlayer.com/api`, with `eth_chainId=0xf22f` / decimal
  `61999`. The selected local account was inspected without exposing secrets.

## CI and deployment status

The release branch CI result is recorded only after the workflow for the final
commit completes. The corrected source must receive its own finalized StudioNet
deployment and source-parity evidence; the V1 address and V1 receipt are not
reused for the corrected bytes.
