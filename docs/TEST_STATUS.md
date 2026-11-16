# Test and release status

Verified in [GitHub Actions](https://github.com/ometere123/gainlock/actions):

- **Host tests:** 23/23 pass on Python 3.12 in both Ubuntu and Windows jobs (last fully green three-job run: [43978925936](https://github.com/ometere123/gainlock/actions/runs/43978925936)).
- **Official GenLayer Direct Mode:** 6/6 tests pass using `genlayer-test==0.29.2` / SDK v0.2.12. These include native validator replay, unit-fanout branching-cycle rejection, uncertain-fails-closed, controller rejection and forged leader/validator mismatch.
- **GenVM linter:** pinned `genvm-linter==0.11.0`, `genvm-lint check contracts/gainlock.py` PASS in [run 43979265398](https://github.com/ometere123/gainlock/actions/runs/43979265398).
- **CLI:** project-local `genlayer@0.39.1`; Ubuntu and Windows pipeline installation/version check. Never invoke global 0.40.0rc2.
- **StudioNet 61999 deployment:** **NOT PERFORMED** here. This runtime has no unlocked funded wallet, so there is no verified deployed contract address, source parity, or FINALIZED+SUCCESS receipt.

Direct Mode is stronger than the host stub but is **not proof of a live StudioNet consensus transaction**. The project is ready for a wallet-bearing agent to carry out the final steps in [DEPLOYMENT.md](DEPLOYMENT.md) and [REVIEWER_DEMO.md](REVIEWER_DEMO.md). Do not claim an on-chain release before those proofs exist.
