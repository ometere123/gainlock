# Test and release status

- Contract Python syntax: checked successfully with local Python 3.13.5.
- Host-side `unittest` suite: 23 tests passed (local SDK stand-in; **not** official GenVM or Direct Mode).
- The tests exercise graph arithmetic, strongly-connected-component classification, saturating upper bounds, owner/controller consent, wrong-party rejection, validator disagreement, sealing, bounded permit issue and consumption, and run closure.
- Official GenVM compatibility/linter/Direct Mode: **not run**; relevant packages cannot be downloaded in the authoring environment (network DNS unavailable).
- StudioNet 61999 deployment and live consensus: **not performed**; this environment does not have a funded/unlocked StudioNet wallet.
- GitHub CI: awaits push and runner execution; do not claim green until observed.

Important: A local stub is not an independent validator or network receipt. The release's final confidence requires live evidence and a matching-source deployment. See `DEPLOYMENT.md` and `REVIEWER_DEMO.md`.
