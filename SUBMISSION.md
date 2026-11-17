# GainLock — standalone Intelligent Contract submission

**GainLock is a consensus-backed feedback-control primitive that turns natural-language event subscriptions into a mathematically bounded event-permit network.**

An agent workflow can be safe edge-by-edge and still contain amplifying feedback. GainLock verifies each proposed event→trigger relationship through independent GenLayer validator reasoning, requires consent from both event controllers, and uses exact strongly-connected-component analysis plus finite-horizon event counting to admit or reject the connection. An approved graph is sealed; one-use permits enforce depth, per-edge fanout and run budget inside participating systems.

### Why this is an Intelligent Contract

The event-to-trigger relationship is semantic: a rule such as “on every confirmed payment” can be expressed differently by independently authored services, and exact string matching cannot establish universal entailment. The GenLayer leader and validators independently judge the stable `MATCH / NO_MATCH / UNCERTAIN` classification from the same frozen, signed-by-consent specifications. A leader-only JSON validator would be insufficient. Malformed model output is a separate bounded `MODEL_ERROR` retry state and cannot activate an edge. The workload mathematics, graph admission and permit accounting are fully deterministic.

### What builders can reuse

A standalone opt-in trigger-admission graph, collision-safe exact consent hashes, integer amplification analysis (including unit-fanout branching cycles), sealed graph lineage, one-time event permits, and view interfaces for integrating consumers. No frontend or privileged backend is required.

### Boundaries

The contract does not monitor unregistered real-world side effects. Its safety theorem applies to events generated via the registered permit protocol with their declared upper bounds. Source and trigger declarations are signed by consenting controllers but are not externally verified descriptions of remote services.

### Code and validation

- Source: `contracts/gainlock.py`
- Review: `docs/REVIEWER_DEMO.md`
- Tests: `python -m unittest discover -s tests -v` (40 host tests); official Direct Mode (9 tests) uses `genlayer-test==0.29.2` and SDK v0.2.12; final CI run [44060971598](https://github.com/ometere123/gainlock/actions/runs/44060971598) passed Ubuntu/Windows host tests, Ubuntu Direct Mode and GenVM lint
- Chain: stable StudioNet 61999 only; project-local CLI pin 0.39.1
- Historical V1 contract: `0xD232F889687DBa1128CB03DA1B7bcE157717f226` (unchanged historical source; not the corrected release)
- Corrected-release deployment: [`0x31285A4120a5547E30561F8A8C8B9c30248dDCBF`](https://explorer-studio.genlayer.com/address/0x31285A4120a5547E30561F8A8C8B9c30248dDCBF),
  deployed by transaction [`0x230813…514f6`](https://explorer-studio.genlayer.com/tx/0x230813b21e18ef5d2d80bc55fd3e98d70987deedaae0cfc0e699d011b14514f6).
  The receipt is `FINALIZED`, consensus is `MAJORITY_AGREE`, execution is
  `SUCCESS`, and the committed/transaction/deployed source SHA-256 is
  `43f6c245716f55f2071f430fbdcd667dd65b2344668db9cdd562e3c3aa671560`.
  Live acceptance evidence is recorded in [LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md).

The current release also separates historical IDs from active capacity: closed runs release per-network active capacity, while run and permit IDs remain unique and historical records remain readable. External services must deliberately integrate the permit protocol; GainLock does not control unregistered off-chain side effects.

The final release has 40 passing host tests, 9 passing official Ubuntu Direct
Mode tests, 5/5 executed mutation kills, passing GenVM lint, and finalized live
StudioNet evidence for the acyclic chain, bounded persistent cycle and permit
lifecycle, unit-fanout amplification rejection, semantic retry recovery, and
genuine uncertainty fail-closed behavior. Windows host tests pass; Windows
Direct Mode remains blocked before assertions by the upstream `WinError 32`
temporary-file cleanup defect. No claim is made that GainLock controls
unregistered off-chain side effects.
