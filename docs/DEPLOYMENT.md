# StudioNet 61999 deployment and verification

## Frozen identities

| Setting | Required |
| --- | --- |
| CLI | `genlayer@0.39.1` installed project-locally |
| Alias | `studionet` |
| Chain | `61999` |
| RPC | `https://studio.genlayer.com/api` |
| Explorer | `https://explorer-studio.genlayer.com` |
| Contract | `contracts/gainlock.py` |

**Forbidden for this repository:** `61997`, `studio-dev`, `studionet-dev`, any preview URL, and global CLI 0.40.0rc2. This is not a 0.6 preview deployment.

## Windows PowerShell

See [live evidence](LIVE_EVIDENCE.md) for the submitted transaction and source
hash. Recheck that transaction before considering another deployment.

```powershell
cd gainlock
npm ci --ignore-scripts --no-audit --no-fund
python -m unittest discover -s tests -v
npm run network:studionet
npm run verify:studionet
# Optional: pin the intended public account; the guard compares it before deploy.
$env:GAINLOCK_DEPLOYER_ADDRESS = '0xYourAlreadyConfiguredStudioNetAddress'
# The wallet/keystore must already be configured and funded for StudioNet.
npm run deploy:studionet
```

## Linux/macOS shell

```bash
cd gainlock
npm ci --ignore-scripts --no-audit --no-fund
python -m unittest discover -s tests -v
npm run network:studionet
npm run verify:studionet
npm run deploy:studionet
```

**Stop if `npm run verify:studionet` fails**. No manual substitution of another endpoint. Do not use `npx genlayer` without `--no-install` or invoke a global CLI. The deployment wrapper uses an explicit executable from this repository's `node_modules`.

`verify:studionet` performs an independent `eth_chainId` request and checks the
selected alias, exact RPC, local CLI version and selected account. It also
reports the public address and GEN balance without printing a password or
private key. `GAINLOCK_DEPLOYER_ADDRESS` is an optional exact-address guard;
use it whenever more than one configured account exists.

## Source and receipt proof checklist

1. Record `git rev-parse HEAD`, `python scripts/hash_source.py`, Python/Node
   versions and the project-local CLI version output.
2. Record `npm run verify:studionet` output showing alias, RPC and chain ID.
3. Deploy once; record BOTH the submitted transaction hash and the resulting
   contract address. If a command fails or times out, inspect the original
   transaction before retrying; never broadcast a duplicate blindly.
4. Poll to `FINALIZED`, and require **execution SUCCESS**, not just a finality label. Record the GenLayer consensus outcome and receipt. A finalized ERROR is failure.
5. Independently read deployed `GainLock` source using `genlayer code` or Studio's source view. Compare its *source bytes* to the committed `contracts/gainlock.py` SHA-256. Do not use README SHA or assumed source parity.
6. Execute the honest and malicious flows described in `REVIEWER_DEMO.md` on
   chain. Record readbacks and explorer URLs after each finality receipt. A
   finalized expected error is evidence of a rejected operation, not an
   ordinary successful execution.
7. Publish the real address, transaction hashes and parity proof in `docs/LIVE_EVIDENCE.md` and submit links, never screenshots alone.
8. Do not claim a live pass until the official GenVM checker, Direct Mode tests
   and actual consensus transactions have passed. If a wallet, provider or
   validator blocks a scenario, preserve the partial evidence and document the
   exact blocker instead of substituting Studio Dev or chain 61997.

## Important CLI commands

For the stable CLI, consult the pinned version's actual `genlayer --help`, `genlayer write --help`, `genlayer receipt --help`, `genlayer call --help`. The CLI documentation is [GenLayer CLI Reference](https://docs.genlayer.com/api-references/genlayer-cli).

After deployment, record actual receipts using the CLI and/or `gen_getTransactionReceipt`. Do not fabricate explorer URLs or addresses.

## No third-party publisher authority required

This contract's proof is about semantic entailment between mutually consented event specifications plus exact graph arithmetic. It does not require an independent publisher to sign those descriptions. Conversely, it cannot claim to have independently verified actual endpoint execution behaviour.
