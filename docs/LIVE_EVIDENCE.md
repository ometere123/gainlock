# GainLock StudioNet evidence

The historical V1 record below is preserved unchanged for comparison. The
corrected release is documented in the final-release section after it.

- Network `studionet`, chain `61999` (`eth_chainId = 0xf22f`), RPC `https://studio.genlayer.com/api`, project-local CLI `0.39.1`.
- Source commit `0df7bca72c04b8349284323fb61742e164f71055`.
- Deployment transaction [0x818aa5a8…bf07418](https://explorer-studio.genlayer.com/tx/0x818aa5a81c8e4163cad645c7713d0b9abece57018cd39badad4467432bf07418).
- Recorded RPC status `FINALIZED`, consensus `MAJORITY_AGREE`, leader execution `SUCCESS`.
- Contract address [0xD232…7f226](https://explorer-studio.genlayer.com/address/0xD232F889687DBa1128CB03DA1B7bcE157717f226).
- The 25,278-byte transaction payload and source returned by `gen_getContractCode` exactly match the committed source. SHA-256 `288f47a975bc859ee1ff7a3ba30a81e916ebb2240ab60bfe549f3fbc27e06475`.

The [RPC snapshot](deployment-receipt.json) includes the Ethereum-compatible receipt. Its `0x1` status alone does not establish GenLayer finality or successful execution.

The initial live run created network 1 (`Review DAG`, six hops, budget 25) with
finalized successful execution. Its first node registration finalized with
execution `ERROR`, decoded as `EXPECTED: invalid label`. The demo had used
a one-character label where the contract requires at least eight characters.
The continuation uses compliant labels and checks that the existing network is
empty before proceeding. The contract source and deployment remain the same.
[Initial run log](live-review.jsonl)

| Live acceptance scenario | Status |
| --- | --- |
| Safe acyclic chain | PASS. Network 1 had two active unit-fanout edges, `ACYCLIC`, and root totals `[3, 2, 1]` under budget 25. [First edge](https://explorer-studio.genlayer.com/tx/0x497672e55786c4f6c5520b0e7e2164873f57bc1c9ff1981ef105ab296d2615a7) · [Second edge](https://explorer-studio.genlayer.com/tx/0x4e6bb5654d2d95d4298dd98f65d0264e753188f5731b49621e087ae47d5677be) |
| Bounded persistent cycle | FAIL. Network 2 remained `ACYCLIC` with root totals `[2, 1]`. Its return edge recorded status 5, `UNCERTAIN / MALFORMED_RESULT`, after finalized successful execution. [Return-edge receipt](https://explorer-studio.genlayer.com/tx/0x110103b8e578d414c5b2c41bc64e7e801e873a8e608a8ca70fd4351cfb52651f) |
| Unit-fanout branching amplification rejection | NOT RUN. The reviewer runner stopped at the cycle assertion. |
| Ambiguous semantic trigger rejection | NOT RUN. The return-edge rejection exercised malformed-result handling. |
| Unauthorized permit rejection | NOT RUN. The cycle never reached the sealed-run setup. |
| Permit replay rejection | NOT RUN. No permit was issued. |

The [continuation log](live-review-continuation.jsonl) records submitted hashes,
27 finalized transaction checks, decoded network and edge readbacks, and the
stopping assertion. Both DAG edge assessments and the cycle return-edge
assessment finalized with leader execution `SUCCESS`. A successful
assessment transaction can still reject an edge.

Recheck the existing transaction without a signer before running the demo:

```sh
node scripts/verify-deployment.mjs 0x818aa5a81c8e4163cad645c7713d0b9abece57018cd39badad4467432bf07418 0df7bca72c04b8349284323fb61742e164f71055
```

The verifier exits successfully when the GenLayer receipt is finalized with
leader execution `SUCCESS` and the source at the resulting address matches
the committed bytes. Once verified, use the [reviewer procedure](REVIEWER_DEMO.md).

## Corrected final release

The corrected source was deployed separately; it is **not** attached to the V1
address above.

- Contract: [`0x31285A4120a5547E30561F8A8C8B9c30248dDCBF`](https://explorer-studio.genlayer.com/address/0x31285A4120a5547E30561F8A8C8B9c30248dDCBF)
- Deployment transaction: [`0x230813…514f6`](https://explorer-studio.genlayer.com/tx/0x230813b21e18ef5d2d80bc55fd3e98d70987deedaae0cfc0e699d011b14514f6)
- Network: `studionet`, chain `61999` / `0xf22f`, RPC `https://studio.genlayer.com/api`
- Finality: `FINALIZED`; consensus: `MAJORITY_AGREE`; execution: `SUCCESS`
- Source commit used for deployment: `28ab4fc213d7c9022b16079553f7fd7120a1c7c9`
- Source bytes: `29108`
- Transaction-payload, Git committed and deployed-source SHA-256: `43f6c245716f55f2071f430fbdcd667dd65b2344668db9cdd562e3c3aa671560`
- Exact parity: **PASS**. Full receipt: [`deployment-receipt-28ab4fc.json`](deployment-receipt-28ab4fc.json)

Final acceptance logs retain submitted hashes, callers, finalized
consensus/execution results and decoded readbacks:

- [`live-review-final-release-continuation.jsonl`](live-review-final-release-continuation.jsonl)
- [`live-review-final-manual.jsonl`](live-review-final-manual.jsonl)
- [`live-uncertain-final-observed.jsonl`](live-uncertain-final-observed.jsonl)

### Scenario A — safe acyclic chain

Final deployment network **2** used nodes **4, 5, 6** and active edges **1, 2**.
The authoritative `get_graph_analysis(2)` readback was:

```json
{"cycle_kind":"ACYCLIC","root_nodes":[4,5,6],"root_totals":[3,2,1],"max_total":3,"admissible":true}
```

The first assessment is [`0x887035…1a505`](https://explorer-studio.genlayer.com/tx/0x88703585711494041f77508a2cb2bd03ef3d8696076fb9f1f3ad26c8cc41a505);
the second, after a committed model-format retry, is [`0xc42eb8…c6a13`](https://explorer-studio.genlayer.com/tx/0xc42eb88ee163fdd78f3087b1e6b3384d42cd5117c1291d79aba1138dd8ac6a13).

### Scenario B — bounded persistent cycle and permits

Final deployment network **3** used nodes **7, 8** and edges **3, 4**, both
fanout `1`. The final readback was:

```json
{"cycle_kind":"PERSISTENT","root_nodes":[7,8],"root_totals":[6,6],"max_total":6,"admissible":true}
```

The network was sealed by [`0x39d4ae…d37525`](https://explorer-studio.genlayer.com/tx/0x39d4ae688320dc4f843ffe433f769b837fcf2cfa41debc20bfac77284dd37525),
with graph hash `8a12ca9052af1e695cb81814bf8b7a3e246582f64f2640538ebe3c34f25bc4b2`.
Run **1** started by [`0x6ef281…25d6f`](https://explorer-studio.genlayer.com/tx/0x6ef2814276c9247a97bbedfd84fca6bc7c277ba3f76b8a79673f600a75b25d6f),
returned root permit **1**, then consumed permit 1, spawned/consumed permit **2**
at depth 1, spawned/consumed permit **3** at depth 2, and closed by
[`0x75ed1a…6ec56`](https://explorer-studio.genlayer.com/tx/0x75ed1afab602fe9a5702b9927f38f3c87b94440c0d08bd23de3df4278a86ec56).
The final run readback was inactive with `permits_issued=3` and
`outstanding_permits=0`. A second run received run ID **2** and root permit **4**;
it was closed, and consuming permit 4 finalized with the expected
`EXPECTED: run closed` error, leaving the permit unspent.

The same live flow also recorded finalized expected errors for wrong-controller
consumption, spawn-before-parent-consumption and repeated consumption. These are
rejected operations, not successful execution.

### Scenario C — unit-fanout branching amplification

Final deployment network **4** used nodes **9, 10, 11** and fanout `1` on every
edge. Edges **5, 6, 7** became active. Edge **8** (`11 → 9`) received the same
bilateral consent and a genuine semantic `MATCH`; its deterministic readback was:

```json
{"status":4,"relation":"MATCH","assessed_graph_kind":"AMPLIFYING","assessed_max_work":13}
```

The edge assessment finalized successfully at [`0xee5d19…87712`](https://explorer-studio.genlayer.com/tx/0xee5d19e6b869ade3872bf1a20592a56a7ef414e44382884de5fe3a3ab3387712).
The active graph remained:

```json
{"cycle_kind":"PERSISTENT","root_nodes":[9,10,11],"root_totals":[10,10,1],"max_total":10,"admissible":true}
```

The fourth edge was therefore rejected for the mathematical budget reason,
using budget-plus-one saturation (`13` for budget `12`), and did not enter the
active adjacency. The complete manual continuation is
[`live-review-final-manual.jsonl`](live-review-final-manual.jsonl).

### Scenario D — genuine semantic uncertainty

Final deployment network **5** used nodes **12, 13** with a source saying an
invoice was created but payment *may or may not* have been confirmed and a target
requiring confirmed payment. The finalized assessment transaction
[`0xba6c42…744c`](https://explorer-studio.genlayer.com/tx/0xba6c42cea82e00c5a04569c59d8d28379c80da40f6dd4cfdf3132cf02474744c)
returned:

```json
{"status":5,"relation":"UNCERTAIN","assessment_attempts":1,"source_ok":true,"target_ok":true}
```

The edge remained inactive; `get_graph_analysis(5)` reported an acyclic graph
with active `root_totals=[1,1]`. This is substantive uncertainty, not a model
format error. The complete ledger is [`live-uncertain-final-observed.jsonl`](live-uncertain-final-observed.jsonl).

### Recovery and preserved unexpected outcomes

On the final deployment, edge 2 first finalized as `MODEL_ERROR` with
`MALFORMED_RESULT` and then finalized as `ACTIVE` on the same immutable proposal
and consents. The same natural model-format recovery was observed on persistent
cycle edges 3 and 4. Controlled Direct Mode recovery remains separate evidence.

The first final-deployment attempt encountered a provider non-JSON response while
proposing an edge; authoritative readback showed no edge was created, and the
partial log is preserved in [`live-review-final-release.jsonl`](live-review-final-release.jsonl).
The later continuation used actual next IDs without overwriting those records.
An additional uncertainty run that exhausted three natural format errors is
preserved in [`live-uncertain-final-corrected.jsonl`](live-uncertain-final-corrected.jsonl)
and is not used as an uncertainty pass claim.
