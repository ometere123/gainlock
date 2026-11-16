# GainLock — standalone Intelligent Contract submission

**GainLock turns natural-language event subscriptions into a mathematically bounded event-permit network.**

An agent workflow can be safe edge-by-edge and still contain amplifying feedback. GainLock verifies each proposed event→trigger relationship through independent GenLayer validator reasoning, requires consent from both event controllers, and uses exact strongly-connected-component analysis plus finite-horizon event counting to admit or reject the connection. An approved graph is sealed; one-use permits enforce depth, per-edge fanout and run budget inside participating systems.

### Why this is an Intelligent Contract

The event-to-trigger relationship is semantic: a rule such as “on every confirmed payment” can be expressed differently by independently authored services, and exact string matching cannot establish entailment. The GenLayer leader and validators independently judge only the stable `MATCH / NO_MATCH / UNCERTAIN` classification from the same frozen signed-by-consent specifications. A leader-only JSON validator would be insufficient. The workload mathematics and permit accounting are fully deterministic.

### What builders can reuse

A standalone opt-in trigger-admission graph, collision-safe exact consent hashes, integer amplification analysis (including unit-fanout branching cycles), sealed graph lineage, one-time event permits, and view interfaces for integrating consumers. No frontend or privileged backend is required.

### Boundaries

The contract does not monitor unregistered real-world side effects. Its safety theorem applies to events generated via the registered permit protocol with their declared upper bounds. Source and trigger declarations are signed by consenting controllers but are not externally verified descriptions of remote services.

### Code and validation

- Source: `contracts/gainlock.py`
- Review: `docs/REVIEWER_DEMO.md`
- Tests: `python -m unittest discover -s tests -v`
- Chain: stable StudioNet 61999 only; project-local CLI pin 0.39.1
- [StudioNet deployment and acceptance status](docs/LIVE_EVIDENCE.md)

No claim of deployed consensus, a source-parity receipt, or any specific GLP score is made without evidence.
