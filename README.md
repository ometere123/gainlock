# GainLock

**A bounded semantic feedback-control primitive for GenLayer Intelligent Contracts.**

GainLock prevents event graphs from being *registered as safe* unless their **maximum permitted event work** fits a frozen finite-horizon budget. It uses GenLayer consensus to establish whether one declared event necessarily satisfies another participant's trigger. It then uses exact integer graph algorithms—not an LLM—to detect cycles and calculate worst-case work. Finally, registered controllers can consume one-use permits and issue bounded child-event permits.

**Standalone contract:** `contracts/gainlock.py`  ·  **No frontend, backend, database, Docker, server key or off-chain judge.**

## Why this exists

An autonomous service might turn one alert into two tasks. Those tasks can emit alerts that trigger additional tasks. Every subscription may seem individually harmless, yet four simple unit-fanout edges can create an amplifying network:

```
       ┌──── B ────┐
       │           │
       ▼           ▼
       A           A
       ▲           ▲
       │           │
       └──── C ────┘

A -> B (1)    A -> C (1)
B -> A (1)    C -> A (1)
```

For each A event, B and C can each produce another A. The cycles are more dangerous *together* than either is alone. A simple "any edge has fanout > 1" detector would miss this.

GainLock checks the complete registered adjacency graph and the **entire finite-horizon work budget** before admitting a new edge.

## Core invariant

For a sealed network with `H=max_hops`, `B=budget`, positive integer edge multiplicities `M[u,v]` and exactly one root event `r`, define:

```
layer_0 = unit_vector(r)
layer_(k+1)[v] = sum_u layer_k[u] * M[u,v]
work(r) = sum_{k=0..H} sum_v layer_k[v]
```

A network is admitted only when **`work(r) <= B` for every possible root**. Computation uses exact bounded integers with `B+1` saturation: overflow cannot silently appear safe. The runtime checks permit depth, child fanout and per-run count again.

Cycle classification is independent of work admissibility:

- `ACYCLIC`: no directed cycle;
- `PERSISTENT`: one or more simple unit-fanout cycles (indefinite without an explicit depth bound, but non-expanding per cycle);
- `AMPLIFYING`: at least one strongly connected component has more than one internally generated successor at some node (or a multiplicity >1); a branching closed walk yields growth even when all edges have unit multiplicity.

**An amplifying graph can be admitted if the explicit finite-horizon work bound still fits the budget.** GainLock is not a blanket graph-censorship tool; it is an enforceable ledger for *bounded registered activity*. Acyclic graphs may still be rejected if their finite work is too large.

## Lifecycle

```
network owner creates bounds
    ↓
network owner registers typed event nodes
    ↓
each controller accepts exact immutable node hash
    ↓
network owner proposes typed edge and max fanout
    ↓
source and target controllers consent to exact edge hash
    ↓
GenLayer leader + validators independently classify event→trigger
    ↓
MATCH? → exact graph simulation → ACTIVE or REJECTED_BUDGET
    ↓
network sealed (immutable version + hash)
    ↓
root controller starts one bounded run
    ↓
one-use root permit, child permits only from spent parents
    ↓
per-edge per-parent fanout and max-depth checked on every spawn
```

### Consensus boundary

Leader and validators independently reason over the **same two frozen, signed-by-consent text descriptions**. Allowed findings:

- `MATCH`: every event satisfying the source's declaration necessarily satisfies the destination's trigger, without unstated context;
- `NO_MATCH`: the texts are explicitly mutually exclusive;
- `UNCERTAIN`: only possibly matches, ambiguous wording, or missing conditions.

Only `MATCH` is eligible for graph admission. Validators rerun the semantic evaluation and must agree on the substantive classification. If validators reject the leader, normal GenLayer consensus may rotate the leader or leave the transaction undetermined; no valid new edge is created. Reason prose is illustrative, **never a safety input**.

There is no live web fetch in this contract. The participants themselves register *immutable, mutually consented semantic specifications*. Agreement on those specifications **does not prove remote services obey them**.

## Main public interface

| Method | Who | Effect |
| --- | --- | --- |
| `create_network(name,max_hops,budget)` | anyone | opens bounded graph |
| `register_node(net,controller,label,output_event,trigger_condition)` | network owner | immutable event/trigger spec |
| `accept_node(node,spec_hash)` | controller | authenticated spec acceptance |
| `propose_edge(net,source,target,fanout)` | network owner | proposes directed bounded subscription |
| `consent_edge(edge,proposal_hash)` | each endpoint controller | consents to exact edge |
| `assess_edge(edge)` | anyone | independently validated semantic match + graph admission |
| `seal_network(net)` | owner | freezes graph hash, preventing mutation |
| `start_run(net,root)` | root controller | allocates one-use root event permit |
| `consume_permit(permit)` | permit node controller | marks event consumed once |
| `spawn_child(parent,edge)` | source controller | creates an allowed child permit |
| `close_run(run)` | original run starter | closes run and disables outstanding permits |

Read-only methods: `get_network`, `get_node`, `get_edge`, `get_graph_analysis`, `get_run`, `get_permit`, `is_permit_spendable`.

`start_run` returns a run ID; inspect `get_run(run_id).root_permit_id` for the event's actual permit ID. Run IDs and permit IDs are separate counters.

## Threat boundary (important)

GainLock **does** prevent its own registered controllers from issuing more GainLock permits than their frozen graph envelope allows. It uses exact source/target hash consent, immutable sealed graphs, validator-independent semantic checks, replay-protected permits, and fixed limits.

GainLock **does not** prevent an uncooperative off-chain service from directly sending events outside its permitted integration. It does not inspect arbitrary unpublished workflows, prove remote publisher identity, provide atomic side-effects inside outside systems, or validate self-declared fanout against external reality. Consumers must deliberately gate their operations on permits; this is an **opt-in protocol**.

A `MATCH` is semantic entailment over frozen descriptions, not real-world evidence that an event happened. No private information belongs in public node specifications. A seal records one particular graph and budgets; changes require a new network. One-use permit consumption on GainLock is not automatically atomic with external actions.

## Installation and tests

Requires Python 3.12+ and Node.js 18+. The project tests require no Docker or GenLayer simulator.

```sh
python -m unittest discover -s tests -v
npm install --no-audit --no-fund
npm run network:studionet
npm run verify:studionet
```

The repository **pins `genlayer` CLI to exactly `0.39.1`** in `package.json`. The `network:studionet` command checks the locally installed binary before selecting `studionet`; it refuses a different CLI version. The deployment command also verifies the active alias, RPC and chain ID. This never uses a globally installed `0.40.0rc2`.

## Deployment (strict network gate)

**Only StudioNet 61999**: `https://studio.genlayer.com/api`, explorer `https://explorer-studio.genlayer.com`.

```sh
npm install --no-audit --no-fund
npm run network:studionet
npm run verify:studionet
npm run deploy:studionet
```

Deploying requires a locally configured/unlocked funded StudioNet wallet. If the CLI's network info does not explicitly show `studionet`, `61999` and `https://studio.genlayer.com/api`, the guard fails without deploying. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`docs/REVIEWER_DEMO.md`](docs/REVIEWER_DEMO.md).

## Current verification state

- Python syntax and dependency-free host-mode protocol/adversarial tests: **run locally for this release**; see the run evidence in `docs/TEST_STATUS.md`.
- Official GenVM/GenLayer Direct Mode, multi-validator live consensus and StudioNet deployment: **not yet run** in this environment. They require the official dependencies and an unlocked funded account. No on-chain address or transaction is claimed.

The repository contains no frontend because this is a standalone Intelligent Contract primitive. It should be submitted under **Intelligent Contracts**, not Projects.
