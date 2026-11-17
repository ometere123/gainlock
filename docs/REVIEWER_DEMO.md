# GainLock proof walkthrough

This walkthrough is a **procedure**, not fabricated execution evidence. Replace
IDs with actual readbacks and submit each StudioNet write as a real transaction.
The live runner waits for `FINALIZED` and then checks the leader execution
result. A finalized expected error is recorded as a rejected operation, not as
a successful state transition. Controlled Direct Mode evidence and live
 StudioNet evidence must remain clearly separated.

## Verified final StudioNet run

The corrected release is deployed at
[`0x31285A4120a5547E30561F8A8C8B9c30248dDCBF`](https://explorer-studio.genlayer.com/address/0x31285A4120a5547E30561F8A8C8B9c30248dDCBF).
The deployment transaction is
[`0x230813…514f6`](https://explorer-studio.genlayer.com/tx/0x230813b21e18ef5d2d80bc55fd3e98d70987deedaae0cfc0e699d011b14514f6),
`FINALIZED` / `MAJORITY_AGREE` / `SUCCESS`, with exact committed/deployed
source SHA-256 `43f6c245716f55f2071f430fbdcd667dd65b2344668db9cdd562e3c3aa671560`.

The executed live order was:

1. **A — safe chain:** network 2, nodes 4→5→6, active unit-fanout edges,
   `ACYCLIC`, root totals `[3,2,1]`, max work `3`, budget `25`.
2. **B — persistent cycle:** network 3, nodes 7↔8, `PERSISTENT`, root totals
   `[6,6]`, max work `6`, budget `7`; the graph was sealed and run 1 issued
   permit 1. Permit 1→2→3 was consumed/spawned through depth 2, the run was
   closed, and a second run received distinct IDs. Finalized expected errors
   proved wrong-controller, spawn-before-spend, replay and closed-run checks.
3. **C — amplification:** network 4, nodes 9/10/11, edges 5/6/7 active; edge
   8 (`11→9`, fanout 1) reached semantic `MATCH`, then deterministic
   `AMPLIFYING`, candidate work `13`, status `REJECTED_BUDGET=4`. The active
   graph stayed `PERSISTENT` with root totals `[10,10,1]`.
4. **D — semantic distinction:** network 5, nodes 12/13; the invoice-created /
   payment-may-be-pending source and confirmed-payment target finalized as
   `UNCERTAIN` status 5 and remained outside active adjacency. The graph readback
   remained acyclic with totals `[1,1]`.

Natural model-format recovery was also observed live: edge 2 first recorded
`MODEL_ERROR`/`MALFORMED_RESULT`, then a later committed assessment of the same
proposal became `ACTIVE`; the same pattern occurred on the persistent-cycle
edges. Full hashes and readbacks are in
[`docs/LIVE_EVIDENCE.md`](LIVE_EVIDENCE.md) and the linked JSONL ledgers.

## Case A — harmless chain

Create network `H=6, B=25`, three nodes A/B/C. Different controllers must accept each node's exact spec hash. Add A→B and B→C with fanout 1, each with both endpoint consents. Trigger texts must be stated so each source output **necessarily** satisfies the target's trigger. Call `assess_edge` for each; require status `ACTIVE=2`. Read `get_graph_analysis`: `ACYCLIC`, work <= 25.

## Case B — benign but persistent cycle

Create network `H=5, B=7`. A and B are mutually triggering event types, one unit per edge. After each `assess_edge`, read graph analysis: `PERSISTENT`, every root has six worst-case events. Seal. Start a run from A, read `root_permit_id`, consume it, spawn one B permit, consume it, spawn one A permit. Demonstrate: spawn before parent spend fails, spending the same permit twice fails, wrong controller fails, spawning at max depth fails, and closing the run prevents spending unused permits.

## Case C — an amplifying loop that looks harmless one edge at a time

Create `H=6, B=12`, three active nodes with mutually compatible declared events/triggers. Propose (in order):

```
A→B (fanout=1)
A→C (fanout=1)
B→A (fanout=1)
C→A (fanout=1)
```

All edges have fanout 1. The **fourth** edge produces a strongly connected component with internal branching, and the proposed graph exceeds the 12-event finite-horizon budget. After consenting and running semantic validation, `get_edge(last).status` must be `REJECTED_BUDGET=4`; its `assessed_graph_kind` must be `AMPLIFYING`. `get_graph_analysis` on the still-active graph must remain `PERSISTENT` (the rejected edge cannot enter the active adjacency).

If the natural-language prompts are too ambiguous for validators to agree on `MATCH`, expect a rejected/undetermined transaction instead; this is not a graph-math failure. Use clearly universally entailing example specifications and do not force validators to accept an equivocal edge.

## Case D — adversarial leader or uncertain trigger

A source says "a draft invoice was created" and the destination trigger says "a payment was confirmed". `NO_MATCH` or `UNCERTAIN` must not activate the edge. In official Direct Mode, mock a leader falsely claiming `MATCH` while a validator independently classifies `NO_MATCH`. The validator must disagree so the transaction cannot mutate the adjacency.

## Case E — model-format recovery

In official Direct Mode, return a malformed or oversized model result for a
consented edge. `get_edge` must show `MODEL_ERROR=6`, no active adjacency and an
incremented committed assessment count. Reassess the same edge with the same
proposal hash and endpoint consents; a valid independently agreed `MATCH` may
then proceed to deterministic graph admission. Three committed model errors
become `RETRY_EXHAUSTED=7`. A validator-disagreement transaction aborts before
the counter is committed, so it is not silently charged as an on-chain attempt.
`UNCERTAIN=5` is a substantive terminal result, not a retryable format error.

## Case F — controller and provenance protection

- Network owner cannot impersonate a registered controller accepting its spec.
- Controllers must consent to the exact edge proposal hash.
- Unauthorized addresses cannot consume another controller's permit.
- Graph seal prevents subsequent edge and node additions.
- The public sealed hash identifies precisely the agreed semantic graph and its bounded budget.

## Case G — sustainable capacity lifecycle

Run identifiers and permit identifiers are monotonically increasing historical
identifiers. `MAX_RUNS=1000` and `MAX_PERMITS=100000` are active per-network
capacity limits. Closing a run releases its active run slot and outstanding
permit slots but retains all historical records, so identifiers are never
reused. Direct Mode exercises repeated close/start cycles and two independent
networks; a live demonstration should exercise a representative cycle rather
than issue thousands of unnecessary StudioNet transactions.

## Consumer boundary

A consumer must deliberately check GainLock's actual sealed graph hash and the relevant controller/permit state before treating it as authorization. Don't imply one-use consumption inside GainLock is atomic with a separate contract's outside side effects. A follow-up consumer integration should use the chain's supported asynchronous finalized-message choreography, not a fabricated synchronous cross-contract lock.
