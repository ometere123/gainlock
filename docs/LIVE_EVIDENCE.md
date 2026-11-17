# GainLock StudioNet evidence

Release status **deployment verified; live acceptance evidence in progress**.

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
| Safe acyclic chain | Pending |
| Bounded persistent cycle | Pending |
| Unit-fanout branching amplification rejection | Pending |
| Ambiguous semantic trigger rejection | Pending |
| Unauthorized permit rejection | Pending |
| Permit replay rejection | Pending |

Recheck the existing transaction without a signer before running the demo:

```sh
node scripts/verify-deployment.mjs 0x818aa5a81c8e4163cad645c7713d0b9abece57018cd39badad4467432bf07418 0df7bca72c04b8349284323fb61742e164f71055
```

The verifier exits successfully when the GenLayer receipt is finalized with
leader execution `SUCCESS` and the source at the resulting address matches
the committed bytes. Once verified, use the [reviewer procedure](REVIEWER_DEMO.md).
