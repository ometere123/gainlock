# GainLock proof walkthrough

This walkthrough is a **procedure**, not fabricated execution evidence. Replace IDs with actual readbacks and submit each StudioNet write as a real transaction. Wait for `FINALIZED + SUCCESS` each time.

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

## Case E — controller and provenance protection

- Network owner cannot impersonate a registered controller accepting its spec.
- Controllers must consent to the exact edge proposal hash.
- Unauthorized addresses cannot consume another controller's permit.
- Graph seal prevents subsequent edge and node additions.
- The public sealed hash identifies precisely the agreed semantic graph and its bounded budget.

## Consumer boundary

A consumer must deliberately check GainLock's actual sealed graph hash and the relevant controller/permit state before treating it as authorization. Don't imply one-use consumption inside GainLock is atomic with a separate contract's outside side effects. A follow-up consumer integration should use the chain's supported asynchronous finalized-message choreography, not a fabricated synchronous cross-contract lock.
