# Test and release status

Verified in [GitHub Actions](https://github.com/ometere123/gainlock/actions):

- **Host tests:** 23/23 pass on Python 3.12 in both Ubuntu and Windows jobs (last fully green three-job run: [43978925936](https://github.com/ometere123/gainlock/actions/runs/43978925936)).
- **Official GenLayer Direct Mode:** 6/6 tests pass using `genlayer-test==0.29.2` / SDK v0.2.12. These include native validator replay, unit-fanout branching-cycle rejection, uncertain-fails-closed, controller rejection and forged leader/validator mismatch.
- **GenVM linter:** pinned `genvm-linter==0.11.0`, `genvm-lint check contracts/gainlock.py` PASS in [run 43979265398](https://github.com/ometere123/gainlock/actions/runs/43979265398).
- **CLI:** project-local `genlayer@0.39.1`; Ubuntu and Windows pipeline installation/version check. Never invoke global 0.40.0rc2.
- **Local release verification:** 23 host tests passed and GenVM lint 0.11.0 passed against v0.2.12. The pinned Direct Mode runner failed locally on Windows before contract assertions with `PermissionError: [WinError 32]` in `gltest/direct/loader.py` while unlinking its stdin temp file. The official Linux Direct Mode job passed for the exact contract revision in [run 43979699693](https://github.com/ometere123/gainlock/actions/runs/43979699693).
- **StudioNet 61999:** Deployment was submitted. See [live evidence](LIVE_EVIDENCE.md) for the recorded RPC status and acceptance tests.

Direct Mode exercises the SDK with controlled semantic outputs. Finalized StudioNet receipts are recorded separately in [live evidence](LIVE_EVIDENCE.md).
