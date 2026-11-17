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

- Release-branch CI run [44045309959](https://github.com/ometere123/gainlock/actions/runs/44045309959)
  passed the four required job groups for the corrected contract source:
  Ubuntu/Windows host tests, Ubuntu official Direct Mode, and GenVM lint.
  A final post-evidence workflow is required after the documentation/evidence
  commit and is reported in the release report.
- Corrected StudioNet deployment:
  [`0x31285A4120a5547E30561F8A8C8B9c30248dDCBF`](https://explorer-studio.genlayer.com/address/0x31285A4120a5547E30561F8A8C8B9c30248dDCBF),
  transaction [`0x230813…514f6`](https://explorer-studio.genlayer.com/tx/0x230813b21e18ef5d2d80bc55fd3e98d70987deedaae0cfc0e699d011b14514f6),
  `FINALIZED` / `MAJORITY_AGREE` / `SUCCESS`, exact source parity SHA-256
  `43f6c245716f55f2071f430fbdcd667dd65b2344668db9cdd562e3c3aa671560`.
- Final live acceptance on that address recorded the safe chain, persistent
  cycle and permit lifecycle, natural model-format recovery followed by valid
  MATCH, mathematical branching rejection (`AMPLIFYING`, status 4, candidate
  work 13), and a substantive UNCERTAIN edge (status 5) excluded from active
  graph analysis. The failed provider retry and model-format variance logs are
  preserved rather than overwritten.
